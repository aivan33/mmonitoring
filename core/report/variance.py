"""Variance computation for the monthly report use case.

Compares actuals to a configured budget scenario for a target period,
producing per-row spot variance, month-on-month, and (for IS/CF) YTD
totals. Pure over the SQLite financials table — no I/O beyond the read.

The canonical entry point is ``compute_variance(client, period)``.
Output is structured (``VarianceResult``) and consumed by the markdown
and CSV writers in this module.

Configuration (per-client ``config.yaml``):

    reporting:
      variance_scenario: realistic        # optional; defaults to 'realistic'
      variance_thresholds:
        flag_pct: 20                      # |pct_var| > flag_pct → flagged
        flag_eur: 10000                   # OR |abs_var| > flag_eur → flagged
"""

from __future__ import annotations

import csv
import datetime as dt
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import yaml


_DEFAULT_FLAG_PCT = 20.0
_DEFAULT_FLAG_EUR = 10000.0
_DEFAULT_SCENARIO = "realistic"

# YTD only applies to flow statements; BS is balance-at-point-in-time.
_YTD_STATEMENTS = frozenset({"IS", "CF"})

# Tests monkeypatch this to redirect lookups.
_ROOT: Path | None = None


def _root() -> Path:
    return _ROOT if _ROOT is not None else Path(__file__).resolve().parents[2]


def _client_dir(client: str) -> Path:
    return _root() / "clients" / client


def _db_path(client: str) -> Path:
    return _client_dir(client) / "data" / f"{client}.db"


@dataclass(frozen=True)
class VarianceRow:
    """Per-row variance: a single (statement, data, grp, subgroup) tuple
    with current-period actual and budget values plus derived deltas.

    For BS rows, ``actual_ytd`` / ``budget_ytd`` / ``ytd_abs`` / ``ytd_pct``
    are ``None`` (balances don't accumulate)."""

    statement: str
    data: str
    grp: str
    subgroup: str
    display_order: int

    actual: float | None
    budget: float | None
    actual_prior: float | None
    actual_ytd: float | None
    budget_ytd: float | None

    abs_var: float | None       # actual − budget (current month)
    pct_var: float | None       # abs_var / |budget|
    mom_abs: float | None       # actual − actual_prior
    mom_pct: float | None       # mom_abs / |actual_prior|
    ytd_abs: float | None       # actual_ytd − budget_ytd
    ytd_pct: float | None       # ytd_abs / |budget_ytd|

    flagged: bool


@dataclass(frozen=True)
class VarianceResult:
    client: str
    entity: str
    period: dt.date
    scenario: str               # the budget scenario being compared against
    flag_pct: float             # in percent (e.g. 20.0)
    flag_eur: float
    rows: tuple[VarianceRow, ...] = field(default_factory=tuple)

    def flagged(self) -> tuple[VarianceRow, ...]:
        return tuple(r for r in self.rows if r.flagged)


def compute_variance(
    client: str,
    period: dt.date,
    scenario: str | None = None,
    *,
    entity: str | None = None,
) -> VarianceResult:
    """Compute per-row variance for ``client`` at ``period``.

    Args:
        client: client name (resolves to clients/<client>/).
        period: target period (first-of-month date).
        scenario: budget scenario to compare against. ``None`` →
            ``reporting.variance_scenario`` from config, falling back
            to ``'realistic'``.
        entity: entity to query. ``None`` → resolved from config (must
            be a single-entity client or the call raises).
    """
    config = _load_config(client)
    reporting = config.get("reporting") or {}
    if scenario is None:
        scenario = reporting.get("variance_scenario") or _DEFAULT_SCENARIO

    thresholds = reporting.get("variance_thresholds") or {}
    flag_pct = float(thresholds.get("flag_pct", _DEFAULT_FLAG_PCT))
    flag_eur = float(thresholds.get("flag_eur", _DEFAULT_FLAG_EUR))

    entity = _resolve_entity(config, entity, client)

    prior_period = _prior_month(period)

    rows: list[VarianceRow] = []
    with sqlite3.connect(_db_path(client)) as conn:
        for statement in ("IS", "CF", "BS"):
            rows.extend(_compute_statement_rows(
                conn, statement, period, prior_period, scenario, entity,
                flag_pct, flag_eur,
            ))

    return VarianceResult(
        client=client,
        entity=entity,
        period=period,
        scenario=scenario,
        flag_pct=flag_pct,
        flag_eur=flag_eur,
        rows=tuple(rows),
    )


# --- internals -------------------------------------------------------------

def _load_config(client: str) -> dict:
    path = _client_dir(client) / "config.yaml"
    return yaml.safe_load(path.read_text()) or {}


def _resolve_entity(config: dict, entity: str | None, client: str) -> str:
    if entity is not None:
        return entity
    entities = config.get("entities") or []
    if len(entities) == 1:
        return entities[0]
    raise ValueError(
        f"client {client!r} has multiple entities ({entities}); "
        f"pass entity= explicitly"
    )


def _prior_month(period: dt.date) -> dt.date | None:
    """Previous month within the same fiscal year. None if period is January."""
    if period.month == 1:
        return None
    return dt.date(period.year, period.month - 1, 1)


def _compute_statement_rows(
    conn: sqlite3.Connection,
    statement: str,
    period: dt.date,
    prior: dt.date | None,
    scenario: str,
    entity: str,
    flag_pct: float,
    flag_eur: float,
) -> list[VarianceRow]:
    """Pull the year's worth of values for this statement, pivot into per-row
    actual / budget / prior / YTD columns, and emit VarianceRow entries.

    A row is included if it has any non-null value across the three
    measurement points (current actual, current budget, prior actual).
    Rows that are entirely empty contribute no signal and are dropped.
    """
    year = period.year
    do_ytd = statement in _YTD_STATEMENTS

    sql = (
        "SELECT period_date, scenario, data, grp, subgroup, "
        "       display_order, value "
        "FROM financials "
        "WHERE statement=? AND entity=? AND scenario IN (?, ?) "
        "  AND period_date >= ? AND period_date <= ?"
    )
    args = (
        statement, entity, "actual", scenario,
        dt.date(year, 1, 1).isoformat(),
        period.isoformat(),
    )
    raw_rows = conn.execute(sql, args).fetchall()

    # Bucket by row identity. Track the earliest display_order seen per row
    # for stable ordering.
    by_key: dict[tuple[str, str, str], dict] = {}
    for period_str, scen, data, grp, subgroup, display_order, value in raw_rows:
        key = (data, grp, subgroup)
        bucket = by_key.setdefault(key, {
            "display_order": display_order,
            "actual": {},
            "budget": {},
        })
        bucket["display_order"] = min(bucket["display_order"], display_order)
        target = "actual" if scen == "actual" else "budget"
        bucket[target][period_str] = value

    period_iso = period.isoformat()
    prior_iso = prior.isoformat() if prior else None

    out: list[VarianceRow] = []
    for (data, grp, subgroup), bucket in by_key.items():
        actual = bucket["actual"].get(period_iso)
        budget = bucket["budget"].get(period_iso)
        actual_prior = (
            bucket["actual"].get(prior_iso) if prior_iso else None
        )

        if do_ytd:
            actual_ytd = _sum_ytd(bucket["actual"], period)
            budget_ytd = _sum_ytd(bucket["budget"], period)
        else:
            actual_ytd = None
            budget_ytd = None

        # Drop rows that have no signal at any of the measurement points.
        if (actual is None and budget is None and actual_prior is None
                and (actual_ytd is None or actual_ytd == 0)
                and (budget_ytd is None or budget_ytd == 0)):
            continue

        abs_var = _safe_diff(actual, budget)
        pct_var = _safe_pct(abs_var, budget)
        mom_abs = _safe_diff(actual, actual_prior)
        mom_pct = _safe_pct(mom_abs, actual_prior)
        ytd_abs = _safe_diff(actual_ytd, budget_ytd)
        ytd_pct = _safe_pct(ytd_abs, budget_ytd)

        flagged = _is_flagged(abs_var, pct_var, flag_eur, flag_pct)

        out.append(VarianceRow(
            statement=statement,
            data=data, grp=grp, subgroup=subgroup,
            display_order=bucket["display_order"],
            actual=actual, budget=budget,
            actual_prior=actual_prior,
            actual_ytd=actual_ytd, budget_ytd=budget_ytd,
            abs_var=abs_var, pct_var=pct_var,
            mom_abs=mom_abs, mom_pct=mom_pct,
            ytd_abs=ytd_abs, ytd_pct=ytd_pct,
            flagged=flagged,
        ))

    out.sort(key=lambda r: r.display_order)
    return out


def _sum_ytd(monthly: dict[str, float | None], period: dt.date) -> float | None:
    """Sum non-null values from January through ``period`` inclusive.
    Returns ``None`` if no values are present in the range."""
    total = 0.0
    saw_any = False
    for month in range(1, period.month + 1):
        iso = dt.date(period.year, month, 1).isoformat()
        v = monthly.get(iso)
        if v is None:
            continue
        total += v
        saw_any = True
    return total if saw_any else None


def _safe_diff(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return a - b


def _safe_pct(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / abs(denominator)


def _is_flagged(
    abs_var: float | None,
    pct_var: float | None,
    flag_eur: float,
    flag_pct: float,
) -> bool:
    """Row is flagged when either threshold is breached. Missing values
    don't trigger; treat them as 'not flagged' rather than guessing."""
    if abs_var is not None and abs(abs_var) > flag_eur:
        return True
    if pct_var is not None and abs(pct_var * 100) > flag_pct:
        return True
    return False


# --- writers ---------------------------------------------------------------

_CSV_COLUMNS = (
    "statement", "data", "grp", "subgroup",
    "actual", "budget", "abs_var", "pct_var",
    "actual_prior", "mom_abs", "mom_pct",
    "actual_ytd", "budget_ytd", "ytd_abs", "ytd_pct",
    "flagged",
)


def write_variance_csv(result: VarianceResult, out_path: str | Path) -> None:
    """Emit one row per VarianceRow with all fields. None → empty string."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(_CSV_COLUMNS)
        for r in result.rows:
            w.writerow([_csv_cell(getattr(r, col)) for col in _CSV_COLUMNS])


def _csv_cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        # Round percentages to 4 decimals; absolute values to 2.
        return f"{v:.4f}" if abs(v) < 10 else f"{v:.2f}"
    return str(v)


def write_variance_md(result: VarianceResult, out_path: str | Path) -> None:
    """Emit a human-readable variance.md with flagged items first, then
    per-statement tables (IS / CF / BS) of every row."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(_render_md(result))


def _render_md(result: VarianceResult) -> str:
    lines: list[str] = []
    lines.append(f"# Variance — {result.client} {result.period:%Y-%m}")
    lines.append("")
    lines.append(f"- Scenario: **{result.scenario}** budget")
    lines.append(f"- Entity: `{result.entity}`")
    lines.append(
        f"- Thresholds: |Δ €| > {_eur(result.flag_eur)} "
        f"OR |Δ %| > {result.flag_pct:.0f}%"
    )
    lines.append("")

    flagged = result.flagged()
    lines.append("## Flagged for discussion")
    lines.append("")
    if not flagged:
        lines.append("_No rows breach the thresholds._")
    else:
        lines.extend(_md_table(flagged, include_statement=True))
    lines.append("")

    for stmt, label in (("IS", "Income Statement"),
                        ("CF", "Cash Flow"),
                        ("BS", "Balance Sheet")):
        rows_for_stmt = [r for r in result.rows if r.statement == stmt]
        if not rows_for_stmt:
            continue
        lines.append(f"## {label} ({stmt}) — all rows")
        lines.append("")
        lines.extend(_md_table(rows_for_stmt, include_statement=False))
        lines.append("")

    return "\n".join(lines)


def _md_table(rows, *, include_statement: bool) -> list[str]:
    """Render rows as a Markdown table. YTD columns omitted if every row
    in the slice is BS (no YTD applies)."""
    show_ytd = any(r.actual_ytd is not None or r.budget_ytd is not None for r in rows)

    headers = []
    if include_statement:
        headers.append("Stmt")
    headers += ["Row", "Actual", "Budget", "Δ €", "Δ %", "MoM €", "MoM %"]
    if show_ytd:
        headers += ["YTD Act", "YTD Bud", "YTD Δ €", "YTD Δ %"]
    headers.append("Flag")

    out = ["| " + " | ".join(headers) + " |"]
    aligns = []
    for h in headers:
        aligns.append("---:" if h not in ("Row", "Stmt", "Flag") else "---")
    out.append("| " + " | ".join(aligns) + " |")

    for r in rows:
        cells: list[str] = []
        if include_statement:
            cells.append(r.statement)
        cells.append(f"{r.data} / {r.grp} / {r.subgroup}")
        cells.append(_eur(r.actual))
        cells.append(_eur(r.budget))
        cells.append(_eur(r.abs_var))
        cells.append(_pct(r.pct_var))
        cells.append(_eur(r.mom_abs))
        cells.append(_pct(r.mom_pct))
        if show_ytd:
            cells.append(_eur(r.actual_ytd))
            cells.append(_eur(r.budget_ytd))
            cells.append(_eur(r.ytd_abs))
            cells.append(_pct(r.ytd_pct))
        cells.append("⚑" if r.flagged else "")
        out.append("| " + " | ".join(cells) + " |")
    return out


def _eur(v: float | None) -> str:
    if v is None:
        return "—"
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    return f"{v:.2f}"


def _pct(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v * 100:+.1f}%"
