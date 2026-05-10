"""Build a client's SQLite DB from its config.yaml.

Driven by ``scripts/build_db.py`` but separated so the orchestration is
unit-testable without a CLI shell.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import sqlite3
import time
from pathlib import Path
from typing import Any

import yaml

from core.data.aggregate_formulas import aggregate_keys, load_registry
from core.data.integrity import IntegrityReport, check_integrity
from core.data.loaders.financials import FinancialRow, load_taxonomy_xlsx
from core.data.schema import wipe_and_create


class IntegrityError(RuntimeError):
    """Raised when build_db detects integrity failures.

    The build still emits the load report so the user can inspect the
    findings — read the .load_report.md alongside the DB.
    """

# Python 3.12+ deprecated the default date adapter. Register an explicit
# ISO-format adapter so date values insert cleanly.
sqlite3.register_adapter(dt.date, lambda d: d.isoformat())


def build_db(client: str, base_dir: str | Path) -> dict[str, Any]:
    """Wipe and rebuild ``<base_dir>/clients/<client>/data/<client>.db``.

    Returns a summary dict with per-source row counts and total duration —
    used by the CLI to print a build report.
    """
    base_dir = Path(base_dir)
    client_dir = base_dir / "clients" / client
    config = yaml.safe_load((client_dir / "config.yaml").read_text())

    entities = set(config.get("entities", []))
    if not entities:
        raise ValueError(
            f"clients/{client}/config.yaml: 'entities' must list at least one entity"
        )

    sources = config.get("financial_sources", []) or []
    for src in sources:
        if "entity" not in src:
            raise ValueError(
                f"financial source {src.get('file')!r}: missing 'entity'"
            )
        if src["entity"] not in entities:
            raise ValueError(
                f"financial source {src.get('file')!r}: "
                f"entity {src['entity']!r} not in entities {sorted(entities)}"
            )

    # EUR is the base; per-client `currencies:` block holds rates for any
    # other currency the client's sources use (e.g. {BGN: 1.95583, USD: 1.08}).
    fx_rates: dict[str, float | None] = {"EUR": None}
    fx_rates.update(config.get("currencies") or {})

    db_path = client_dir / "data" / f"{client}.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    wipe_and_create(db_path)

    started = time.perf_counter()
    summary: dict[str, Any] = {
        "client": client,
        "db_path": str(db_path),
        "sources": [],
        "financials_rows": 0,
        "duration_s": 0.0,
    }

    file_paths: list[Path] = []
    with sqlite3.connect(db_path) as conn:
        for src in sources:
            file_path = client_dir / src["file"]
            file_paths.append(file_path)
            currency = src.get("currency", "EUR")
            fx_rate = fx_rates.get(currency)
            if currency != "EUR" and fx_rate is None:
                raise ValueError(
                    f"source {src['file']!r}: currency={currency!r} but "
                    f"config 'currencies:' block has no rate for it"
                )

            rows: list[FinancialRow] = list(load_taxonomy_xlsx(
                file_path,
                year=src["year"],
                entity=src["entity"],
                currency=currency,
                fx_rate=fx_rate,
                emit_null_cells=src.get("emit_null_cells", False),
            ))
            conn.executemany(
                "INSERT OR REPLACE INTO financials VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
            summary["sources"].append({
                "file": src["file"],
                "rows": len(rows),
                **_provenance(file_path),
            })
        _tag_aggregates(conn, client_dir)
        registry = load_registry(client_dir)
        integrity = check_integrity(conn, registry, workbook_paths=file_paths)
        conn.commit()
        summary["financials_rows"] = conn.execute(
            "SELECT COUNT(*) FROM financials"
        ).fetchone()[0]

    summary["duration_s"] = round(time.perf_counter() - started, 3)
    summary["integrity"] = {
        "failures": len(integrity.failures),
        "warnings": len(integrity.warnings),
    }

    report_path = db_path.with_suffix(".load_report.md")
    report_path.write_text(_format_load_report(client, summary, integrity))
    summary["load_report"] = str(report_path)

    if integrity.has_failures():
        raise IntegrityError(
            f"build_db: integrity check failed for {client!r} "
            f"({len(integrity.failures)} failure(s)); see {report_path}"
        )

    return summary


def _format_load_report(
    client: str,
    summary: dict[str, Any],
    integrity: IntegrityReport,
) -> str:
    """Render a markdown report for clients/<client>/data/<client>.load_report.md."""
    lines: list[str] = []
    lines.append(f"# {client} build report")
    lines.append("")
    lines.append(f"- Generated: {dt.datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"- DB: `{summary['db_path']}`")
    lines.append(f"- Total rows: {summary['financials_rows']}")
    lines.append(f"- Duration: {summary['duration_s']}s")
    lines.append("")

    lines.append("## Sources")
    lines.append("")
    lines.append("| File | Rows | sha256 (first 12) | Modified | Size (kB) |")
    lines.append("|---|---:|---|---|---:|")
    for src in summary["sources"]:
        sha = src.get("sha256", "")[:12]
        kb = round(src.get("size_bytes", 0) / 1024, 1)
        lines.append(
            f"| `{src['file']}` | {src['rows']} | `{sha}` "
            f"| {src.get('mtime', '')} | {kb} |"
        )
    lines.append("")

    n_fail = len(integrity.failures)
    n_warn = len(integrity.warnings)
    lines.append("## Integrity")
    lines.append("")
    lines.append(f"**Failures: {n_fail}   Warnings: {n_warn}**")
    lines.append("")

    lines.append("### Failures")
    if not integrity.failures:
        lines.append("")
        lines.append("_none_")
    else:
        lines.append("")
        for f in integrity.failures:
            lines.append(f"- **{f.rule}** `{f.name}`: {f.message}")
    lines.append("")

    lines.append("### Warnings")
    if not integrity.warnings:
        lines.append("")
        lines.append("_none_")
    else:
        lines.append("")
        for f in integrity.warnings:
            lines.append(f"- **{f.rule}** `{f.name}`: {f.message}")
    lines.append("")

    return "\n".join(lines)


def _provenance(path: Path) -> dict[str, Any]:
    """File fingerprint for the build report — staleness is visible at a glance."""
    stat = path.stat()
    return {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "mtime": dt.datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        "size_bytes": stat.st_size,
    }


def _tag_aggregates(conn: sqlite3.Connection, client_dir: Path) -> None:
    """Set ``is_aggregate=1`` on rows whose triplet appears in the client's
    registry. Raises if a registered aggregate is missing from the loaded
    data (R2 — registered-but-not-loaded)."""
    registry = load_registry(client_dir)
    keys = aggregate_keys(registry)
    if not keys:
        return

    for data, grp, subgroup in keys:
        conn.execute(
            "UPDATE financials SET is_aggregate=1 "
            "WHERE data=? AND grp=? AND subgroup=?",
            (data, grp, subgroup),
        )

    found = {
        (d, g, sg)
        for d, g, sg in conn.execute(
            "SELECT DISTINCT data, grp, subgroup FROM financials "
            "WHERE is_aggregate=1"
        ).fetchall()
    }
    missing = keys - found
    if missing:
        names = sorted(
            name for name, f in registry.items()
            if (f.data, f.grp, f.subgroup) in missing
        )
        raise ValueError(
            f"aggregate_formulas.yaml registers aggregates not present in "
            f"the loaded data: {names}. Either add the row to the source "
            f"or remove the entry from the registry."
        )
