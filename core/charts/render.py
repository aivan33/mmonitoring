"""Chart renderer: spec + anchor period → PNG + sidecar JSON.

The renderer is intentionally narrow:
- ``resolve_period`` translates the spec's period block into a concrete
  (start, end) date pair anchored at the chart's anchor month.
- ``resolve_query`` calls ``core.query`` to materialize the data series
  (single-data trend, multi-data signed sum, value, aggregation).
- ``render`` dispatches on chart_type to a matplotlib drawing routine,
  applies brand styling, writes the PNG, and emits a sidecar JSON
  snapshot of the spec + the resolved values used to produce it.

Brand styling reads from the client's ``config.yaml`` ``brand:`` block.
The sidecar JSON is the canonical "AI-reproducible" record of a chart —
it captures content + values, not rendering instructions.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import matplotlib

# Use Agg backend so rendering works without a display server (CI, headless).
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from dateutil.relativedelta import relativedelta

from core.charts.spec import ChartSpec, DataSeries
from core.query import get_aggregation, get_trend, get_value


# ---------------------------------------------------------------------------
# Period resolution
# ---------------------------------------------------------------------------

def resolve_period(period: dict[str, Any], anchor: dt.date) -> tuple[dt.date, dt.date]:
    """Resolve the spec's period block to a (start, end) date pair."""
    kind = period["kind"]
    if kind == "current_month":
        return (anchor, anchor)
    if kind == "ytd":
        return (dt.date(anchor.year, 1, 1), anchor)
    if kind == "ltm":
        months = period.get("months", 12)
        start = anchor - relativedelta(months=months - 1)
        return (start, anchor)
    if kind == "month_offset":
        target = anchor + relativedelta(months=period["offset"])
        return (target, target)
    if kind == "full_year":
        year = period["year"]
        return (dt.date(year, 1, 1), dt.date(year, 12, 1))
    if kind == "explicit":
        d = dt.date(period["year"], period["month"], 1)
        return (d, d)
    if kind == "range":
        start = dt.date.fromisoformat(period["start"])
        end = dt.date.fromisoformat(period["end"])
        return (start, end)
    raise ValueError(f"unknown period kind {kind!r}")


# ---------------------------------------------------------------------------
# Query resolution
# ---------------------------------------------------------------------------

def resolve_query(
    query: dict[str, Any],
    *,
    client: str,
    entity: str | None,
    start: dt.date,
    end: dt.date,
) -> Any:
    """Materialize one data series via core.query.

    Returns:
        - kind=trend: pd.Series indexed by date.
        - kind=value: scalar (float or None).
        - kind=aggregation: pd.Series.
    """
    kind = query["kind"]
    scenario = query.get("scenario", "actual")

    if kind == "trend":
        data_arg = query["data"]
        if isinstance(data_arg, str):
            data_list = [data_arg]
        else:
            data_list = list(data_arg)
        signs = query.get("signs", [1.0] * len(data_list))
        if len(signs) != len(data_list):
            raise ValueError(
                f"trend query: signs length {len(signs)} != data length {len(data_list)}"
            )
        grp = query.get("grp")
        subgroup = query.get("subgroup")

        # `year` override: pin this series to a specific full year, ignoring
        # the chart's start/end. Used for prior-period comparisons.
        year_override = query.get("year")
        if year_override is not None:
            q_start = dt.date(year_override, 1, 1)
            q_end = dt.date(year_override, 12, 1)
        else:
            q_start, q_end = start, end

        total: pd.Series | None = None
        for d, s in zip(data_list, signs):
            series = get_trend(
                d, grp=grp, subgroup=subgroup, scenario=scenario,
                start_date=q_start, end_date=q_end,
                client=client, entity=entity,
            )
            weighted = series * s
            if total is None:
                total = weighted
            else:
                total = total.add(weighted, fill_value=0)
        return total if total is not None else pd.Series(dtype=float)

    if kind == "value":
        return get_value(
            query["data"], query.get("grp"), query.get("subgroup"),
            start, scenario=scenario,
            client=client, entity=entity,
        )

    if kind == "aggregation":
        level = query.get("level", "data")
        window = query.get("window", "current")
        if window == "current":
            return get_aggregation(
                query["data"], start, scenario=scenario, level=level,
                client=client, entity=entity,
            )
        if window == "ytd":
            # Sum get_aggregation across Jan..anchor of anchor's year.
            anchor = end
            year = anchor.year
            total: pd.Series | None = None
            for m in range(1, anchor.month + 1):
                month_start = dt.date(year, m, 1)
                s = get_aggregation(
                    query["data"], month_start, scenario=scenario, level=level,
                    client=client, entity=entity,
                )
                total = s if total is None else total.add(s, fill_value=0)
            return total if total is not None else pd.Series(dtype=float)
        raise ValueError(f"unknown aggregation window {window!r}")

    if kind == "projection":
        # Projection: actual values up to anchor (= start..end if no future
        # months), then project forward by cumulatively adding deltas in
        # the projection scenario. Returns a (Series, anchor_date) pair so
        # the renderer can color actual vs projected separately.
        return _resolve_projection(
            query, client=client, entity=entity, start=start, end=end,
        )

    raise ValueError(f"unknown query kind {kind!r}")


def _resolve_projection(
    query: dict[str, Any],
    *,
    client: str,
    entity: str | None,
    start: dt.date,
    end: dt.date,
) -> dict[str, Any]:
    """Resolve a projection query.

    The projection's anchor is the last date in [start, end] for which the
    'actual' query has a real value. Up to and including that date we use
    actual values; beyond it we cumsum the delta query under the projection
    scenario, starting from the actual baseline.

    Returns a dict ``{"series": pd.Series, "actual_through": date}`` so the
    bar_projection renderer can colour actual months differently from
    projected months.
    """
    actual_q = query["actual"]
    delta_q = query["projection_delta"]

    # Pull the actual trend for the whole window (will be NaN/missing
    # past the last actual month).
    actual_trend = resolve_query(
        {**actual_q, "kind": "trend"},
        client=client, entity=entity, start=start, end=end,
    )

    # Find the last date with a non-null actual value.
    if isinstance(actual_trend, pd.Series) and len(actual_trend.dropna()):
        anchor = actual_trend.dropna().index[-1]
        baseline = float(actual_trend.dropna().iloc[-1])
    else:
        anchor = start - relativedelta(months=1)
        baseline = 0.0

    if anchor >= end:
        return {"series": actual_trend, "actual_through": anchor}

    # Project the rest of the window via cumsum of deltas from the projection
    # scenario, starting at baseline.
    proj_start = anchor + relativedelta(months=1)
    deltas = resolve_query(
        {**delta_q, "kind": "trend"},
        client=client, entity=entity, start=proj_start, end=end,
    )
    if isinstance(deltas, pd.Series) and len(deltas):
        projected = baseline + deltas.fillna(0).cumsum()
    else:
        projected = pd.Series(dtype=float)

    actual_part = actual_trend.dropna()
    combined = pd.concat([actual_part, projected])
    return {"series": combined, "actual_through": anchor}


# ---------------------------------------------------------------------------
# Brand application
# ---------------------------------------------------------------------------

_DEFAULT_PALETTE = ["#2A625E", "#E67D5A", "#D4A24C", "#5A8AB8", "#7E6BA1", "#3D8F5C"]


def _font_installed(name: str) -> bool:
    """Cheap check: is ``name`` resolvable by matplotlib's font manager?"""
    from matplotlib import font_manager
    available = {f.name for f in font_manager.fontManager.ttflist}
    return name in available


def apply_brand(brand: dict[str, Any]) -> list[str]:
    """Apply matplotlib rcParams from the brand dict and return the palette
    that drawing routines should iterate over for series colors."""
    fallbacks = ["Helvetica", "Arial", "DejaVu Sans"]
    fonts: list[str] = []
    requested = brand.get("font_body")
    if requested and _font_installed(requested):
        fonts.append(requested)
    fonts.extend(fallbacks)
    plt.rcParams["font.family"] = fonts
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.spines.right"] = False
    plt.rcParams["axes.grid"] = True
    plt.rcParams["grid.alpha"] = 0.3

    palette = [
        brand.get("primary"),
        brand.get("accent"),
        brand.get("budget"),
    ]
    palette = [c for c in palette if c]
    return palette + _DEFAULT_PALETTE


# ---------------------------------------------------------------------------
# Drawing routines per chart_type
# ---------------------------------------------------------------------------

def _draw_line(ax, spec: ChartSpec, resolved: list[dict], palette: list[str]) -> None:
    for i, series in enumerate(resolved):
        s = series["raw"]
        if isinstance(s, pd.Series) and not s.empty:
            ax.plot(
                s.index, s.values,
                marker="o", linewidth=2,
                color=palette[i % len(palette)],
                label=series["label"],
            )
    ax.set_title(spec.title, loc="left", fontsize=12, fontweight="bold")
    ax.legend(loc="best", frameon=False)
    _apply_axis_format(ax, spec)


def _draw_bar(ax, spec: ChartSpec, resolved: list[dict], palette: list[str]) -> None:
    if len(resolved) == 0:
        return
    s = resolved[0]["raw"]
    if isinstance(s, pd.Series):
        ax.bar(range(len(s)), s.values, color=palette[0])
        ax.set_xticks(range(len(s)))
        ax.set_xticklabels(_month_labels(list(s.index)), rotation=45, ha="right")
    ax.set_title(spec.title, loc="left", fontsize=12, fontweight="bold")
    _apply_axis_format(ax, spec)


def _draw_donut(ax, spec: ChartSpec, resolved: list[dict], palette: list[str]) -> None:
    if not resolved:
        return
    s = resolved[0]["raw"]
    if not isinstance(s, pd.Series):
        return
    s = s.dropna()
    s = s[s != 0]  # exclude zero/null slices
    colors = [palette[i % len(palette)] for i in range(len(s))]
    ax.pie(
        s.values, labels=s.index.astype(str), colors=colors,
        autopct="%1.1f%%", pctdistance=0.78,
        wedgeprops=dict(width=0.4, edgecolor="white"),
    )
    ax.set_title(spec.title, loc="left", fontsize=12, fontweight="bold")


def _draw_kpi_card(ax, spec: ChartSpec, resolved: list[dict], palette: list[str]) -> None:
    ax.set_axis_off()
    ax.text(0.5, 0.7, spec.title, ha="center", va="center",
            fontsize=12, fontweight="bold")
    if resolved:
        v = resolved[0]["raw"]
        if isinstance(v, pd.Series):
            v = v.iloc[0] if len(v) else None
        if v is not None:
            ax.text(0.5, 0.35, _format_eur(v), ha="center", va="center",
                    fontsize=24, fontweight="bold",
                    color=palette[0])


def _draw_stacked_bar(
    ax, spec: ChartSpec, resolved: list[dict], palette: list[str],
) -> None:
    if not resolved:
        return
    bottom = None
    x_dates: list | None = None
    for i, series in enumerate(resolved):
        s = series["raw"]
        if not isinstance(s, pd.Series):
            continue
        if x_dates is None:
            x_dates = list(s.index)
        ax.bar(
            range(len(s)), s.values,
            bottom=bottom,
            color=palette[i % len(palette)],
            label=series["label"],
        )
        bottom = s.values if bottom is None else bottom + s.values
    if x_dates:
        ax.set_xticks(range(len(x_dates)))
        ax.set_xticklabels(_month_labels(x_dates), rotation=45, ha="right")
    ax.set_title(spec.title, loc="left", fontsize=12, fontweight="bold")
    ax.legend(loc="best", frameon=False)
    _apply_axis_format(ax, spec)


def _month_labels(dates: list) -> list[str]:
    """Render dates as 'Mon YY' (e.g., 'Jan 25')."""
    return [d.strftime("%b %y") if isinstance(d, dt.date) else str(d) for d in dates]


_MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _draw_clustered_bar(
    ax, spec: ChartSpec, resolved: list[dict], palette: list[str],
) -> None:
    """Multiple bar series side-by-side per x category.

    If series span multiple years, x = month-of-year (1..12) so series
    align by month for prior-period / multi-year comparisons. Otherwise
    x = the union of date indices in chronological order.
    """
    if not resolved:
        return
    series_list: list[pd.Series] = [
        s["raw"] for s in resolved if isinstance(s["raw"], pd.Series)
    ]
    if not series_list:
        return
    n = len(series_list)

    all_years: set[int] = set()
    for s in series_list:
        for d in s.index:
            if isinstance(d, dt.date):
                all_years.add(d.year)
    multi_year = len(all_years) > 1

    if multi_year:
        x_labels = list(_MONTH_NAMES)
        x = list(range(12))
        bar_width = 0.8 / n
        for i, (entry, s) in enumerate(zip(resolved, series_list)):
            values: list[float] = []
            for m in range(1, 13):
                cells = [
                    v for d, v in s.items()
                    if isinstance(d, dt.date) and d.month == m
                       and v is not None and not pd.isna(v)
                ]
                values.append(float(sum(cells)) if cells else float("nan"))
            offsets = [xi + (i - (n - 1) / 2) * bar_width for xi in x]
            ax.bar(
                offsets, values, width=bar_width,
                color=palette[i % len(palette)],
                label=entry["label"],
            )
        ax.set_xticks(x)
        ax.set_xticklabels(x_labels, rotation=45, ha="right")
    else:
        all_idx: list = []
        seen = set()
        for s in series_list:
            for d in s.index:
                if d not in seen:
                    seen.add(d)
                    all_idx.append(d)
        all_idx = sorted(all_idx)
        x = list(range(len(all_idx)))
        bar_width = 0.8 / n
        for i, (entry, s) in enumerate(zip(resolved, series_list)):
            values = [s.get(d, float("nan")) for d in all_idx]
            offsets = [xi + (i - (n - 1) / 2) * bar_width for xi in x]
            ax.bar(
                offsets, values, width=bar_width,
                color=palette[i % len(palette)],
                label=entry["label"],
            )
        ax.set_xticks(x)
        ax.set_xticklabels(_month_labels(all_idx), rotation=45, ha="right")

    ax.set_title(spec.title, loc="left", fontsize=12, fontweight="bold")
    ax.legend(loc="best", frameon=False, ncol=min(n, 4))
    _apply_axis_format(ax, spec)


def _draw_bar_with_line(
    ax, spec: ChartSpec, resolved: list[dict], palette: list[str],
) -> None:
    """Clustered bars for all but the last series; last series rendered as
    line on the same axes. Multi-year alignment is inherited from
    _draw_clustered_bar — the line overlay aligns the same way."""
    if len(resolved) < 2:
        _draw_clustered_bar(ax, spec, resolved, palette)
        return

    bar_resolved = resolved[:-1]
    line_entry = resolved[-1]

    _draw_clustered_bar(ax, spec, bar_resolved, palette)

    s = line_entry["raw"]
    if not isinstance(s, pd.Series):
        return

    # Decide whether to align by month-of-year (multi-year) or by date.
    bar_series = [b["raw"] for b in bar_resolved if isinstance(b["raw"], pd.Series)]
    all_years: set[int] = set()
    for bs in bar_series + [s]:
        for d in bs.index:
            if isinstance(d, dt.date):
                all_years.add(d.year)
    multi_year = len(all_years) > 1

    if multi_year:
        x = list(range(12))
        values = []
        for m in range(1, 13):
            cells = [
                v for d, v in s.items()
                if isinstance(d, dt.date) and d.month == m
                   and v is not None and not pd.isna(v)
            ]
            values.append(float(sum(cells)) if cells else float("nan"))
    else:
        all_idx: list = []
        seen = set()
        for bs in bar_series:
            for d in bs.index:
                if d not in seen:
                    seen.add(d)
                    all_idx.append(d)
        all_idx = sorted(all_idx)
        x = list(range(len(all_idx)))
        values = [s.get(d, float("nan")) for d in all_idx]

    line_color = palette[len(bar_resolved) % len(palette)]
    ax.plot(x, values, marker="o", linewidth=2, color=line_color,
            label=line_entry["label"])
    ax.legend(loc="best", frameon=False, ncol=min(len(resolved), 4))


def _draw_gauge(
    ax, spec: ChartSpec, resolved: list[dict], palette: list[str],
) -> None:
    """Half-donut gauge: actual filled fraction of [start, target]. Center
    text shows the actual value. Expected resolved entries:
        [0] = actual (Series of one period or scalar)
        [1] = target (Series or scalar) — usually budget for the period
    Spec.gauge.start optionally overrides the start point (default 0).
    """
    import math

    actual = _scalar_from(resolved[0]["raw"]) if resolved else None
    target = _scalar_from(resolved[1]["raw"]) if len(resolved) >= 2 else None

    start_cfg = (spec.gauge or {}).get("start", 0)
    if start_cfg == "previous_period":
        start = _scalar_from(resolved[2]["raw"]) if len(resolved) >= 3 else 0.0
    else:
        start = float(start_cfg) if start_cfg is not None else 0.0
    if start is None:
        start = 0.0

    actual = float(actual) if actual is not None else 0.0
    target = float(target) if target is not None else 0.0

    # Fraction filled. Cap at [0, 1] so the arc never overflows the gauge.
    span = target - start
    frac = 0.0 if span == 0 else max(0.0, min(1.0, (actual - start) / span))

    fill_color = palette[1 % len(palette)] if len(palette) > 1 else "#E67D5A"
    rest_color = "#EFEFEF"

    # Half-circle gauge (180° from left to right, drawn upper half).
    ax.set_axis_off()
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-0.3, 1.2)
    ax.set_aspect("equal")

    # Background arc.
    bg = matplotlib.patches.Wedge(
        (0, 0), 1.0, 0, 180, width=0.32, facecolor=rest_color, edgecolor="white",
    )
    ax.add_patch(bg)
    # Filled portion (from left).
    if frac > 0:
        end_angle = 180 - (frac * 180)
        fg = matplotlib.patches.Wedge(
            (0, 0), 1.0, end_angle, 180, width=0.32,
            facecolor=fill_color, edgecolor="white",
        )
        ax.add_patch(fg)

    # Center text — actual value.
    ax.text(0, 0.15, _format_eur(actual), ha="center", va="center",
            fontsize=22, fontweight="bold", color=fill_color)
    # Title above the arc.
    ax.text(0, 1.1, spec.title, ha="center", va="center",
            fontsize=12, fontweight="bold")
    # Start / target labels under the gauge.
    ax.text(-1.0, -0.15, _format_eur(start), ha="center", va="top", fontsize=9)
    ax.text(1.0, -0.15, _format_eur(target), ha="center", va="top", fontsize=9)


def _scalar_from(raw: Any) -> float | None:
    """Coerce a series-or-scalar to a single float (sum if multi-value)."""
    if raw is None:
        return None
    if isinstance(raw, pd.Series):
        s = raw.dropna()
        if len(s) == 0:
            return None
        if len(s) == 1:
            return float(s.iloc[0])
        return float(s.sum())
    return float(raw)


def _draw_bar_projection(
    ax, spec: ChartSpec, resolved: list[dict], palette: list[str],
) -> None:
    """Bars colored by actual vs projected. Two modes:

    1. Single series produced by the 'projection' query kind (cumsum):
       returns ``{"series": Series, "actual_through": date}``. Bars
       up to and including ``actual_through`` use the primary colour;
       beyond use the budget colour.

    2. Two trend series (actual + budget) — concat-with-precedence mode:
       at every month, prefer the actual value if non-null, else fall
       back to the budget value. Colour matches which source supplied it.
    """
    if not resolved:
        return

    actual_color = palette[0]
    projected_color = palette[2] if len(palette) >= 3 else palette[1 % len(palette)]

    if len(resolved) == 1:
        raw = resolved[0]["raw"]
        if isinstance(raw, dict) and "series" in raw:
            s = raw["series"]
            anchor = raw.get("actual_through")
        else:
            s = raw if isinstance(raw, pd.Series) else pd.Series(dtype=float)
            anchor = None
        if not isinstance(s, pd.Series) or s.empty:
            return
        colors = [
            actual_color if (anchor is None or d <= anchor) else projected_color
            for d in s.index
        ]
        labels = list(s.index)
        values = list(s.values)
    else:
        # Two trend series: actual + budget. Prefer actual where present,
        # else budget. Colour each bar by which source won.
        actual_s = resolved[0]["raw"] if isinstance(resolved[0]["raw"], pd.Series) else pd.Series(dtype=float)
        budget_s = resolved[1]["raw"] if isinstance(resolved[1]["raw"], pd.Series) else pd.Series(dtype=float)
        all_dates = sorted(set(actual_s.index) | set(budget_s.index))
        values = []
        colors = []
        labels = []
        for d in all_dates:
            a = actual_s.get(d) if d in actual_s.index else None
            b = budget_s.get(d) if d in budget_s.index else None
            if a is not None and not pd.isna(a):
                values.append(float(a))
                colors.append(actual_color)
                labels.append(d)
            elif b is not None and not pd.isna(b):
                values.append(float(b))
                colors.append(projected_color)
                labels.append(d)

    if not values:
        return

    x = list(range(len(values)))
    ax.bar(x, values, color=colors, width=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(_month_labels(labels), rotation=45, ha="right")
    ax.set_title(spec.title, loc="left", fontsize=12, fontweight="bold")

    import matplotlib.patches as mpatches
    handles = [
        mpatches.Patch(color=actual_color, label=resolved[0]["label"] if resolved else "Actual"),
        mpatches.Patch(color=projected_color,
                       label=resolved[1]["label"] if len(resolved) > 1 else "Rolling budget"),
    ]
    ax.legend(handles=handles, loc="best", frameon=False)
    _apply_axis_format(ax, spec)


def _draw_donut_pair(
    ax, spec: ChartSpec, resolved: list[dict], palette: list[str],
) -> None:
    """Two donut charts side-by-side on the same Axes."""
    if len(resolved) < 2:
        _draw_donut(ax, spec, resolved, palette)
        return

    fig = ax.figure
    fig.delaxes(ax)
    axL = fig.add_subplot(1, 2, 1)
    axR = fig.add_subplot(1, 2, 2)

    for sub_ax, entry in [(axL, resolved[0]), (axR, resolved[1])]:
        s = entry["raw"]
        if not isinstance(s, pd.Series):
            continue
        s = s.dropna()
        s = s[s != 0]
        if s.empty:
            continue
        colors = [palette[i % len(palette)] for i in range(len(s))]
        sub_ax.pie(
            s.values, labels=s.index.astype(str), colors=colors,
            autopct="%1.1f%%", pctdistance=0.78,
            wedgeprops=dict(width=0.4, edgecolor="white"),
        )
        sub_ax.set_title(entry["label"], fontsize=11, fontweight="bold")
        sub_ax.text(0, 0, _format_eur(s.sum()), ha="center", va="center",
                    fontsize=18, fontweight="bold", color=palette[0])

    fig.suptitle(spec.title, x=0.05, y=0.98, ha="left",
                 fontsize=12, fontweight="bold")


_DRAW: dict[str, Any] = {
    "line": _draw_line,
    "bar": _draw_bar,
    "stacked_bar": _draw_stacked_bar,
    "donut": _draw_donut,
    "kpi_card": _draw_kpi_card,
    "gauge": _draw_gauge,
    "clustered_bar": _draw_clustered_bar,
    "bar_with_line": _draw_bar_with_line,
    "bar_projection": _draw_bar_projection,
    "donut_pair": _draw_donut_pair,
}


def _apply_axis_format(ax, spec: ChartSpec) -> None:
    yfmt = spec.axes.get("y", {}).get("format") if spec.axes else None
    if yfmt == "EUR_thousands":
        ax.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda v, _: f"{v / 1000:,.0f}")
        )
        ax.set_ylabel("EUR ’000")


def _format_eur(v: float) -> str:
    if abs(v) >= 1_000_000:
        return f"€{v / 1_000_000:.1f}M"
    if abs(v) >= 1_000:
        return f"€{v / 1_000:.0f}K"
    return f"€{v:.0f}"


# ---------------------------------------------------------------------------
# render() — the public entry point
# ---------------------------------------------------------------------------

def render(
    spec: ChartSpec,
    *,
    anchor: dt.date,
    brand: dict[str, Any],
    out_dir: Path,
) -> tuple[Path, Path]:
    """Render ``spec`` for the given anchor month.

    Returns ``(png_path, sidecar_json_path)``. Both files written to
    ``out_dir/{spec.chart_id}.{png,json}``. ``out_dir`` is created if missing.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    png_path = out_dir / f"{spec.chart_id}.png"
    json_path = out_dir / f"{spec.chart_id}.json"

    # Platform charts: write a placeholder PNG + a placeholder sidecar
    # pointing at the export file. Don't query data.
    if spec.is_platform:
        _write_platform_placeholder(spec, anchor, png_path, json_path)
        return png_path, json_path

    if spec.chart_type not in _DRAW:
        raise NotImplementedError(
            f"chart_type {spec.chart_type!r} not yet supported"
        )

    start, end = resolve_period(spec.period, anchor)
    resolved: list[dict[str, Any]] = []
    for d in spec.data:
        raw = resolve_query(
            d.query,
            client=spec.client,
            entity=spec.entity,
            start=start, end=end,
        )
        resolved.append({"label": d.label, "raw": raw})

    palette = apply_brand(brand)
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=120)
    _DRAW[spec.chart_type](ax, spec, resolved, palette)
    fig.tight_layout()
    fig.savefig(png_path, bbox_inches="tight")
    plt.close(fig)

    _write_sidecar(spec, anchor, start, end, resolved, json_path)
    return png_path, json_path


def _serialize_resolved(resolved: list[dict]) -> list[dict]:
    """Convert resolved values into JSON-friendly shapes for the sidecar."""
    out: list[dict] = []
    for entry in resolved:
        raw = entry["raw"]
        rec: dict[str, Any] = {"label": entry["label"]}
        # The projection query returns {"series": Series, "actual_through": date};
        # unwrap so the sidecar has the same shape as a normal trend.
        if isinstance(raw, dict) and "series" in raw:
            actual_through = raw.get("actual_through")
            if isinstance(actual_through, dt.date):
                rec["actual_through"] = actual_through.isoformat()
            raw = raw["series"]
        if isinstance(raw, pd.Series):
            if isinstance(raw.index, pd.MultiIndex):
                rec["values"] = [
                    {"key": list(map(str, k)), "value": _maybe_none(v)}
                    for k, v in raw.items()
                ]
            else:
                rec["values"] = [
                    {"key": k.isoformat() if isinstance(k, dt.date) else str(k),
                     "value": _maybe_none(v)}
                    for k, v in raw.items()
                ]
        elif raw is None:
            rec["value"] = None
        else:
            rec["value"] = float(raw)
        out.append(rec)
    return out


def _maybe_none(v: Any) -> float | None:
    if v is None:
        return None
    if pd.isna(v):
        return None
    return float(v)


def _write_sidecar(
    spec: ChartSpec,
    anchor: dt.date,
    start: dt.date,
    end: dt.date,
    resolved: list[dict],
    path: Path,
) -> None:
    payload = {
        "spec": _spec_to_dict(spec),
        "anchor": anchor.isoformat(),
        "resolved_period": {"start": start.isoformat(), "end": end.isoformat()},
        "data": _serialize_resolved(resolved),
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, indent=2))


def _spec_to_dict(spec: ChartSpec) -> dict[str, Any]:
    """Round-trip the dataclass to a plain dict for JSON serialization."""
    d = asdict(spec)
    # asdict turns DataSeries into nested dicts; nothing else needs special handling.
    return d


def _write_platform_placeholder(
    spec: ChartSpec, anchor: dt.date,
    png_path: Path, json_path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=120)
    ax.set_axis_off()
    ax.text(0.5, 0.6, spec.title, ha="center", va="center",
            fontsize=14, fontweight="bold")
    msg = "Platform export"
    if spec.platform_export:
        msg += f"\nsee: {spec.platform_export}"
    ax.text(0.5, 0.35, msg, ha="center", va="center",
            fontsize=11, color="#666")
    fig.savefig(png_path, bbox_inches="tight")
    plt.close(fig)

    payload = {
        "spec": _spec_to_dict(spec),
        "anchor": anchor.isoformat(),
        "placeholder": True,
        "platform_export": spec.platform_export,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    json_path.write_text(json.dumps(payload, indent=2))
