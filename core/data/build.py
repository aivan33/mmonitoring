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
from core.data.loaders.financials import FinancialRow, load_taxonomy_xlsx
from core.data.schema import wipe_and_create

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

    fx_rates: dict[str, float | None] = {
        "EUR": None,
        "BGN": config.get("bgn_to_eur_rate"),
        "USD": config.get("usd_to_eur_rate"),
    }

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

    with sqlite3.connect(db_path) as conn:
        for src in sources:
            file_path = client_dir / src["file"]
            currency = src.get("currency", "EUR")
            fx_rate = fx_rates.get(currency)
            if currency != "EUR" and fx_rate is None:
                raise ValueError(
                    f"source {src['file']!r}: currency={currency!r} but "
                    f"config has no rate for it (e.g. bgn_to_eur_rate / usd_to_eur_rate)"
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
        conn.commit()
        summary["financials_rows"] = conn.execute(
            "SELECT COUNT(*) FROM financials"
        ).fetchone()[0]

    summary["duration_s"] = round(time.perf_counter() - started, 3)
    return summary


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
