"""Integrity engine — runs R3, R4, R5 against a loaded financials DB.

R3 — total-lookalike scan
    Rows whose grp/subgroup label matches a Total/Subtotal/Net pattern but
    aren't registered as aggregates. Warn-only: hint to register them or
    rename the row.

R4 — registered aggregate recompute
    For every registry entry, recompute Σ(leaf × sign) and compare to the
    parsed aggregate value. Fail above tolerance — this is the canonical
    "hardcoded value drifted from its formula" trip-wire.

R5 — source-cell type audit
    For every registry entry with ``source_cell`` set, open the workbook
    and verify the cell is an Excel formula (data_type='f'). Hardcoded
    values warn — they're correct today but will silently drift.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from openpyxl import load_workbook

from core.data.aggregate_formulas import AggregateFormula


@dataclass(frozen=True)
class Finding:
    rule: str       # "R3" | "R4" | "R5" | "R6"
    severity: str   # "fail" | "warn"
    name: str       # aggregate name or row identifier
    message: str


@dataclass(frozen=True)
class IntegrityReport:
    findings: tuple[Finding, ...] = ()

    @property
    def failures(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity == "fail")

    @property
    def warnings(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity == "warn")

    def has_failures(self) -> bool:
        return any(f.severity == "fail" for f in self.findings)


# Matches "Total", "Subtotal", "Sum of …", "Net Income / Net Burn / Net …".
# Plain "Net" (no following word) is NOT flagged — too generic.
_TOTAL_PATTERN = re.compile(
    r"^\s*(total|subtotal|sum|net\s+\S)", re.IGNORECASE,
)


def check_integrity(
    conn: sqlite3.Connection,
    registry: dict[str, AggregateFormula],
    *,
    workbook_paths: Iterable[Path] | None = None,
    tolerance: float = 1.0,
) -> IntegrityReport:
    findings: list[Finding] = []
    findings.extend(_run_r4(conn, registry, tolerance))
    findings.extend(_run_r3(conn, registry))
    if workbook_paths is not None:
        findings.extend(_run_r5(registry, list(workbook_paths)))
    return IntegrityReport(findings=tuple(findings))


# ---------------------------------------------------------------------------
# R4
# ---------------------------------------------------------------------------

def _run_r4(
    conn: sqlite3.Connection,
    registry: dict[str, AggregateFormula],
    tolerance: float,
) -> Iterable[Finding]:
    for name, formula in registry.items():
        rows = conn.execute(
            "SELECT period_date, scenario, entity, value FROM financials "
            "WHERE data=? AND grp=? AND subgroup=? AND value IS NOT NULL",
            (formula.data, formula.grp, formula.subgroup),
        ).fetchall()
        for period, scenario, entity, parsed in rows:
            recomputed = _recompute(conn, formula, period, scenario, entity)
            if recomputed is None:
                continue
            delta = parsed - recomputed
            if abs(delta) > tolerance:
                yield Finding(
                    rule="R4",
                    severity="fail",
                    name=name,
                    message=(
                        f"{name} at {period} ({scenario}/{entity}): "
                        f"parsed {parsed:.2f}, recomputed {recomputed:.2f}, "
                        f"delta {delta:+.2f} (tolerance {tolerance:.2f})"
                    ),
                )


def _recompute(
    conn: sqlite3.Connection,
    formula: AggregateFormula,
    period: str,
    scenario: str,
    entity: str,
) -> float | None:
    """Return Σ(leaf × sign) over leaves only (is_aggregate=0). Returns None
    if no leaf data was found at all — caller skips rather than fails."""
    total = 0.0
    saw_any = False
    for leaf in formula.leaves:
        sql = (
            "SELECT SUM(value) FROM financials "
            "WHERE data=? AND period_date=? AND scenario=? AND entity=? "
            "AND is_aggregate=0"
        )
        args: list = [leaf.data, period, scenario, entity]
        if leaf.grp is not None:
            sql += " AND grp=?"
            args.append(leaf.grp)
        if leaf.subgroup is not None:
            sql += " AND subgroup=?"
            args.append(leaf.subgroup)
        row = conn.execute(sql, args).fetchone()
        v = row[0] if row else None
        if v is None:
            continue
        saw_any = True
        total += leaf.sign * v
    return total if saw_any else None


# ---------------------------------------------------------------------------
# R3
# ---------------------------------------------------------------------------

def _run_r3(
    conn: sqlite3.Connection,
    registry: dict[str, AggregateFormula],
) -> Iterable[Finding]:
    registered = {(f.data, f.grp, f.subgroup) for f in registry.values()}
    rows = conn.execute(
        "SELECT DISTINCT data, grp, subgroup FROM financials "
        "WHERE is_aggregate=0"
    ).fetchall()
    for data, grp, subgroup in rows:
        if (data, grp, subgroup) in registered:
            continue  # registered → already covered by R4
        for label in (subgroup, grp):
            if label and _TOTAL_PATTERN.match(str(label)):
                yield Finding(
                    rule="R3",
                    severity="warn",
                    name=f"{data} / {grp} / {subgroup}",
                    message=(
                        f"row labelled like a total but not registered: "
                        f"({data!r}, {grp!r}, {subgroup!r})"
                    ),
                )
                break  # one finding per row, even if both grp+subgroup match


# ---------------------------------------------------------------------------
# R5
# ---------------------------------------------------------------------------

def _run_r5(
    registry: dict[str, AggregateFormula],
    workbook_paths: list[Path],
) -> Iterable[Finding]:
    cache: dict[Path, "Workbook"] = {}  # noqa: F821
    try:
        for name, formula in registry.items():
            yield from _audit_one_cell(name, formula, workbook_paths, cache)
    finally:
        for wb in cache.values():
            wb.close()


def _audit_one_cell(
    name: str,
    formula: AggregateFormula,
    workbook_paths: list[Path],
    cache: dict,
) -> Iterable[Finding]:
    if formula.source_cell is None:
        return
    if "!" not in formula.source_cell:
        yield Finding(
            rule="R5", severity="warn", name=name,
            message=(
                f"{name}: source_cell={formula.source_cell!r} is not in "
                f"'Sheet!Cell' form; skipping cell-type audit"
            ),
        )
        return
    sheet_name, cell_ref = formula.source_cell.split("!", 1)

    for path in workbook_paths:
        path = Path(path)
        if path not in cache:
            cache[path] = load_workbook(path, data_only=False, read_only=False)
        wb = cache[path]
        if sheet_name not in wb.sheetnames:
            continue
        try:
            cell = wb[sheet_name][cell_ref]
        except (ValueError, KeyError) as exc:
            yield Finding(
                rule="R5", severity="warn", name=name,
                message=(
                    f"{name}: could not read cell {formula.source_cell!r} "
                    f"in {path.name}: {exc}"
                ),
            )
            return
        if cell.data_type != "f":
            yield Finding(
                rule="R5", severity="warn", name=name,
                message=(
                    f"{name}: source_cell {formula.source_cell!r} is "
                    f"hardcoded (data_type={cell.data_type!r}), expected formula. "
                    f"Will silently drift when upstream cells change."
                ),
            )
        return  # found the sheet; done

    yield Finding(
        rule="R5", severity="warn", name=name,
        message=(
            f"{name}: sheet {sheet_name!r} (from source_cell="
            f"{formula.source_cell!r}) not found in any provided workbook"
        ),
    )
