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
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from dateutil.relativedelta import relativedelta

from core.charts.spec import ChartSpec, DataSeries
from core.data.query import (
    get_aggregation, get_kpi, get_kpi_trend, get_trend, get_value,
)


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
        # grp / subgroup may be a single string or a list of strings
        # (sum across all listed groups). None = no filter.
        grp_arg = query.get("grp")
        if isinstance(grp_arg, list):
            grp_list = grp_arg
        else:
            grp_list = [grp_arg]
        subgroup = query.get("subgroup")

        year_override = query.get("year")
        if year_override is not None:
            q_start = dt.date(year_override, 1, 1)
            q_end = dt.date(year_override, 12, 1)
        else:
            q_start, q_end = start, end

        fallback_scenario = query.get("fallback_scenario")
        total: pd.Series | None = None
        for d, s in zip(data_list, signs):
            for g in grp_list:
                series = get_trend(
                    d, grp=g, subgroup=subgroup, scenario=scenario,
                    start_date=q_start, end_date=q_end,
                    fallback_scenario=fallback_scenario,
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

    if kind == "kpi_trend":
        # Operational KPI series across the period. No scenario fan-out —
        # KPIs are observed values, not budget/actual variants.
        return get_kpi_trend(
            query["kpi"], start_date=start, end_date=end,
            client=client, entity=entity,
        )

    if kind == "kpi_value":
        # Spot-period KPI; ``start`` is the target period for single-month
        # kinds like ``current_month`` / ``explicit``.
        return get_kpi(
            query["kpi"], start, client=client, entity=entity,
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


# Visual constants — single source of truth for the "premium" look.
TEXT_INK = "#2D2D2D"
TEXT_MUTED = "#6E6E6E"
GRID_INK = "#E5DBD5"
LABEL_FONTSIZE_TICK = 10.5
LABEL_FONTSIZE_DATA = 9.0
LABEL_FONTSIZE_LEGEND = 10.5
LABEL_FONTSIZE_DONUT_CENTER = 26


def apply_brand(brand: dict[str, Any]) -> list[str]:
    """Apply matplotlib rcParams from the brand dict and return the palette
    that drawing routines should iterate over for series colors."""
    fallbacks = ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"]
    fonts: list[str] = []
    requested = brand.get("font_body")
    if requested and _font_installed(requested):
        fonts.append(requested)
    fonts.extend(fallbacks)
    plt.rcParams["font.family"] = fonts
    plt.rcParams["text.color"] = TEXT_INK
    plt.rcParams["axes.labelcolor"] = TEXT_INK
    plt.rcParams["xtick.color"] = TEXT_MUTED
    plt.rcParams["ytick.color"] = TEXT_MUTED
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.spines.right"] = False
    plt.rcParams["axes.spines.left"] = False
    plt.rcParams["axes.spines.bottom"] = False
    plt.rcParams["axes.grid"] = False  # we draw the grid explicitly per-axes

    palette = [
        brand.get("primary"),
        brand.get("accent"),
        brand.get("budget"),
    ]
    palette = [c for c in palette if c]
    return palette + _DEFAULT_PALETTE


def _resolve_palette(spec: ChartSpec, brand_palette: list[str]) -> list[str]:
    """Per-spec colour override via spec.style.colors; else brand palette."""
    overrides = (spec.style or {}).get("colors")
    if overrides:
        return list(overrides) + brand_palette
    return brand_palette


def _style_axes(ax) -> None:
    """Apply the deck-style axis chrome: light dotted y-grid, no spines,
    horizontal tick labels, capped tick density."""
    from matplotlib.ticker import MaxNLocator
    ax.grid(True, axis="y", linestyle=":", color=GRID_INK,
            linewidth=0.8, alpha=1.0, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", labelsize=LABEL_FONTSIZE_TICK, length=0, pad=8)
    ax.tick_params(axis="y", labelsize=LABEL_FONTSIZE_TICK, length=0, pad=6)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6, prune="upper"))
    for spine in ax.spines.values():
        spine.set_visible(False)
    # Modest headroom above the data so labels aren't clipped.
    ax.margins(y=0.10)


def _dot_legend(ax, labels: list[str], colors: list[str]) -> None:
    """Bottom-centred legend with coloured dots before each label, outside
    the plotting area. Matches the Dec 2025 deck legend style."""
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], marker="o", linestyle="None",
               markersize=9, markerfacecolor=c, markeredgecolor=c, label=l)
        for l, c in zip(labels, colors)
    ]
    ax.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.09),
        ncol=min(len(handles), 6),
        frameon=False,
        handletextpad=0.5,
        columnspacing=2.2,
        fontsize=LABEL_FONTSIZE_LEGEND,
        labelcolor=TEXT_INK,
    )


# ---------------------------------------------------------------------------
# Drawing routines per chart_type
# ---------------------------------------------------------------------------

def _draw_line(ax, spec: ChartSpec, resolved: list[dict], palette: list[str]) -> None:
    labels: list[str] = []
    colors: list[str] = []
    plotted: list[tuple[pd.Series, str]] = []
    for i, series in enumerate(resolved):
        s = series["raw"]
        if not (isinstance(s, pd.Series) and not s.empty):
            continue
        c = palette[i % len(palette)]
        # Smoothed line via Catmull-Rom spline through the data points.
        # Dates are converted to ordinal numbers for splining; matplotlib
        # renders them along the date axis once the formatter is set below.
        x_nums = (
            [mdates.date2num(d) for d in s.index]
            if any(isinstance(d, dt.date) for d in s.index)
            else list(range(len(s.index)))
        )
        smooth_x, smooth_y = _catmull_rom_smooth(x_nums, list(s.values))
        if smooth_x:
            ax.plot(
                smooth_x, smooth_y, linewidth=1.8, color=c,
                solid_capstyle="round", solid_joinstyle="round", zorder=3,
            )
        ax.plot(
            s.index, s.values,
            linestyle="None", marker="o", markersize=4.0,
            color=c, label=series["label"],
            markerfacecolor=c, markeredgecolor=c,
            zorder=4,
        )
        plotted.append((s, c))
        labels.append(series["label"])
        colors.append(c)

    # Per-x label placement: when multiple series have a value at the same x,
    # the highest-value series' label goes above and the lowest goes below
    # so the labels don't stack on top of each other.
    for s, c in plotted:
        for x, y in zip(s.index, s.values):
            if y is None or pd.isna(y):
                continue
            others = []
            for other_s, _ in plotted:
                if other_s is s:
                    continue
                ov = other_s.get(x) if x in other_s.index else None
                if ov is not None and not pd.isna(ov):
                    others.append(float(ov))
            above = True
            if others:
                if y < min(others):
                    above = False
                elif y > max(others):
                    above = True
                else:
                    above = y >= 0
            else:
                above = y >= 0
            ax.annotate(
                format_value(y, spec.value_format), xy=(x, y),
                xytext=(0, 10 if above else -10),
                textcoords="offset points",
                ha="center", va="bottom" if above else "top",
                fontsize=LABEL_FONTSIZE_DATA,
                color=c, fontweight="medium",
            )

    _style_axes(ax)
    _apply_axis_format(ax, spec)
    if plotted and any(
        len(s) > 0 and isinstance(s.index[0], dt.date) for s, _ in plotted
    ):
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=8))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%y"))
    if labels:
        _dot_legend(ax, labels, colors)


def _draw_bar(ax, spec: ChartSpec, resolved: list[dict], palette: list[str]) -> None:
    if len(resolved) == 0:
        return
    s = resolved[0]["raw"]
    if isinstance(s, pd.Series):
        bars = ax.bar(range(len(s)), s.values, color=palette[0],
                      width=0.62, zorder=3, linewidth=0)
        ax.set_xticks(range(len(s)))
        ax.set_xticklabels(_month_labels(list(s.index)), rotation=0, ha="center")
        ax.bar_label(
            bars,
            labels=[format_value(v, spec.value_format)
                    for v in s.values],
            padding=4, fontsize=LABEL_FONTSIZE_DATA, color=TEXT_INK,
            fontweight="medium",
        )
    _style_axes(ax)
    _apply_axis_format(ax, spec)


def _draw_donut(ax, spec: ChartSpec, resolved: list[dict], palette: list[str]) -> None:
    if not resolved:
        return
    s = resolved[0]["raw"]
    if not isinstance(s, pd.Series):
        return
    s = s.dropna()
    s = s[s != 0]
    color_map = (spec.style or {}).get("color_map") or {}
    labels = list(s.index.astype(str))
    colors = _slice_colors(labels, color_map, palette)
    wedges, _ = ax.pie(
        s.values, labels=None, colors=colors,
        wedgeprops=dict(width=0.36, edgecolor="white", linewidth=2.5),
        startangle=90, counterclock=False,
    )
    _annotate_donut_slices(ax, wedges, s.values, labels, s.sum(), colors)
    total = s.sum()
    center_color = color_map.get("__center__", palette[0])
    ax.text(0, 0, _format_eur(total), ha="center", va="center",
            fontsize=LABEL_FONTSIZE_DONUT_CENTER,
            fontweight="bold", color=center_color)
    # Generous radial limits so external labels never get clipped.
    ax.set_xlim(-1.7, 1.7)
    ax.set_ylim(-1.4, 1.4)


def _annotate_donut_slices(ax, wedges, values, labels, total, colors) -> None:
    """Donut labelling: each slice gets an outside label of the form
    ``name\\n€XK (YY%)`` with a subtle gray leader. Slices below 2%
    are skipped to avoid leader-line clutter (their share still counts
    in the centre total). Same-side labels are nudged apart vertically
    to avoid overlap.
    """
    import math
    OUTSIDE_PCT_THRESHOLD = 2.0
    LEADER_GRAY = "#9A8F88"

    placed: list[tuple[float, float]] = []
    for wedge, value, label, _color in zip(wedges, values, labels, colors):
        pct = (value / total) * 100 if total else 0
        if pct < OUTSIDE_PCT_THRESHOLD:
            continue
        ang = (wedge.theta1 + wedge.theta2) / 2
        rad = math.radians(ang)
        x, y = math.cos(rad), math.sin(rad)

        outside_text = f"{label}\n{_format_eur(value)} ({pct:.0f}%)"

        x_outer, y_outer = x * 1.02, y * 1.02
        x_text, y_text = x * 1.30, y * 1.30
        for prev_x, prev_y in placed:
            if (prev_x >= 0) == (x_text >= 0) and abs(prev_y - y_text) < 0.20:
                y_text = prev_y + (0.20 if y_text >= prev_y else -0.20)
        placed.append((x_text, y_text))
        ha = "left" if x_text >= 0 else "right"
        ax.annotate(
            outside_text,
            xy=(x_outer, y_outer), xytext=(x_text, y_text),
            ha=ha, va="center",
            fontsize=LABEL_FONTSIZE_DATA + 0.5,
            color=TEXT_INK, fontweight="medium", linespacing=1.45,
            arrowprops=dict(arrowstyle="-", color=LEADER_GRAY,
                            lw=0.7, connectionstyle="arc3,rad=0",
                            shrinkA=0, shrinkB=4),
        )


def _slice_colors(
    labels: list[str], color_map: dict[str, str], palette: list[str],
) -> list[str]:
    """Resolve per-slice colours: prefer label→colour map, else positional."""
    out: list[str] = []
    for i, lbl in enumerate(labels):
        out.append(color_map.get(lbl) or palette[i % len(palette)])
    return out


def _draw_kpi_card(ax, spec: ChartSpec, resolved: list[dict], palette: list[str]) -> None:
    ax.set_axis_off()
    ax.text(0.5, 0.78, spec.title, ha="center", va="center",
            fontsize=12, fontweight="bold", color=TEXT_MUTED)
    if resolved:
        v = resolved[0]["raw"]
        if isinstance(v, pd.Series):
            v = v.iloc[0] if len(v) else None
        if v is not None:
            ax.text(0.5, 0.40, format_value(v, spec.value_format),
                    ha="center", va="center",
                    fontsize=32, fontweight="bold",
                    color=palette[0])
        # If a second series is supplied, treat it as the prior-period
        # baseline and render a small delta arrow + percent change.
        if len(resolved) > 1:
            prev_raw = resolved[1]["raw"]
            if isinstance(prev_raw, pd.Series):
                prev_raw = prev_raw.iloc[0] if len(prev_raw) else None
            if (prev_raw is not None and v is not None
                    and isinstance(prev_raw, (int, float)) and prev_raw != 0):
                delta = (float(v) - float(prev_raw)) / abs(float(prev_raw))
                arrow = "▲" if delta >= 0 else "▼"
                color = "#2E7A56" if delta >= 0 else "#C24C44"
                ax.text(0.5, 0.12,
                        f"{arrow} {delta * 100:+.1f}% vs last period",
                        ha="center", va="center",
                        fontsize=10, color=color, fontweight="medium")


def _draw_stacked_bar(
    ax, spec: ChartSpec, resolved: list[dict], palette: list[str],
) -> None:
    """Stacked bars with positive segments going up and negative going down.
    EUR labels are placed inside each segment, but suppressed for segments
    smaller than 7% of the total y-axis span to avoid overlap."""
    if not resolved:
        return
    # Build the union x-axis from all series so misaligned periods stack correctly.
    all_dates: list = []
    seen = set()
    for series in resolved:
        s = series["raw"]
        if not isinstance(s, pd.Series):
            continue
        for d in s.index:
            if d not in seen:
                seen.add(d)
                all_dates.append(d)
    all_dates = sorted(all_dates)
    if not all_dates:
        return
    x = list(range(len(all_dates)))
    n_dates = len(x)

    # Estimate a visual-significance threshold: any segment smaller than
    # this is dropped entirely (no draw, no stack advance) so it doesn't
    # appear as a thin "ghost" sliver splitting the visible segments.
    # Use the largest single absolute value across all series as the
    # reference span — gives a stable threshold even when one column has
    # an outlier.
    max_abs = 0.0
    for series in resolved:
        s = series["raw"]
        if isinstance(s, pd.Series):
            for v in s.dropna().values:
                if abs(float(v)) > max_abs:
                    max_abs = abs(float(v))
    skip_threshold = max(max_abs * 0.06, 10000.0)

    # In matplotlib, ax.bar(height, bottom) draws from y=bottom to
    # y=bottom+height. For NEGATIVE height the bar extends downward, so
    # `bottom` is the UPPER edge of the visible rectangle. For each
    # negative segment we therefore pass the current cumulative
    # neg_bottom (the upper edge for this segment) as bottom, then the
    # negative height extends the bar down to neg_bottom + v.
    pos_bottom = [0.0] * n_dates
    neg_bottom = [0.0] * n_dates
    labels: list[str] = []
    colors: list[str] = []
    drawn: list[tuple[Any, list[float]]] = []  # (BarContainer, values)

    for i, series in enumerate(resolved):
        s = series["raw"]
        if not isinstance(s, pd.Series):
            continue
        c = palette[i % len(palette)]
        values = []
        bottoms = []
        for j, d in enumerate(all_dates):
            v = s.get(d) if d in s.index else None
            if v is None or pd.isna(v) or abs(float(v)) < skip_threshold:
                values.append(0.0)
                bottoms.append(0.0)
                continue
            v = float(v)
            if v >= 0:
                bottoms.append(pos_bottom[j])
                pos_bottom[j] += v
            else:
                bottoms.append(neg_bottom[j])
                neg_bottom[j] += v
            values.append(v)
        bars = ax.bar(x, values, bottom=bottoms, color=c, width=0.68,
                      zorder=3, linewidth=0)
        drawn.append((bars, values))
        labels.append(series["label"])
        colors.append(c)

    # Label suppression: a segment is labelled only if its absolute value
    # would fit a label visibly. Use the median (not max) of stack tops/
    # bottoms so a single outlier month doesn't strip labels from
    # everything else. Floor at €8K so trivial slices stay clean.
    pos_for_span = sorted(pos_bottom)
    neg_for_span = sorted(neg_bottom)
    typical_pos = pos_for_span[len(pos_for_span) // 2] if pos_for_span else 0.0
    typical_neg = neg_for_span[len(neg_for_span) // 2] if neg_for_span else 0.0
    typical_span = max(typical_pos - typical_neg, 1.0)
    threshold = max(typical_span * 0.08, 8000.0)

    for bars, values in drawn:
        ax.bar_label(
            bars,
            labels=[
                format_value(v, spec.value_format) if abs(v) >= threshold and v != 0 else ""
                for v in values
            ],
            label_type="center", fontsize=LABEL_FONTSIZE_DATA - 1,
            color="white", fontweight="bold",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(_month_labels(all_dates), rotation=0, ha="center")
    _style_axes(ax)
    _apply_axis_format(ax, spec)
    if labels:
        _dot_legend(ax, labels, colors)


def _month_labels(dates: list) -> list[str]:
    """Render dates as 'Mon-YY' (e.g., 'Jan-25')."""
    return [d.strftime("%b-%y") if isinstance(d, dt.date) else str(d) for d in dates]


_MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _label_clustered_bars(
    ax, bars, values: list, label_inside_top: bool,
    value_format: str = "eur",
) -> None:
    formatted = [
        format_value(v, value_format)
        for v in values
    ]
    if not label_inside_top:
        ax.bar_label(
            bars, labels=formatted,
            padding=4, fontsize=LABEL_FONTSIZE_DATA - 1.5, color=TEXT_INK,
            fontweight="medium",
        )
        return

    max_v = max(
        (abs(float(v)) for v in values if v is not None and not pd.isna(v)),
        default=0.0,
    )
    inside_threshold = max_v * 0.18
    inside_labels = [
        lbl if (v is not None and not pd.isna(v) and abs(float(v)) >= inside_threshold) else ""
        for lbl, v in zip(formatted, values)
    ]
    outside_labels = [
        lbl if (v is not None and not pd.isna(v) and abs(float(v)) < inside_threshold) else ""
        for lbl, v in zip(formatted, values)
    ]
    ax.bar_label(
        bars, labels=inside_labels,
        padding=-13, fontsize=LABEL_FONTSIZE_DATA - 1.5, color="white",
        fontweight="bold",
    )
    ax.bar_label(
        bars, labels=outside_labels,
        padding=4, fontsize=LABEL_FONTSIZE_DATA - 1.5, color=TEXT_INK,
        fontweight="medium",
    )


def _draw_clustered_bar(
    ax, spec: ChartSpec, resolved: list[dict], palette: list[str],
    label_inside_top: bool = False,
) -> None:
    """Multiple bar series side-by-side per x category.

    If series span multiple years, x = month-of-year (1..12) so series
    align by month for prior-period / multi-year comparisons. Otherwise
    x = the union of date indices in chronological order.

    When ``label_inside_top`` is True, value labels are drawn inside the
    bar near the top edge in white (used by ``_draw_bar_with_line`` so
    the line overlay does not cross outside-above labels). Bars too
    short to legibly fit an inside label fall back to outside-above.
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

    labels_legend: list[str] = []
    colors_legend: list[str] = []

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
            c = palette[i % len(palette)]
            bars = ax.bar(offsets, values, width=bar_width, color=c,
                          zorder=3, linewidth=0)
            _label_clustered_bars(ax, bars, values, label_inside_top,
                                  value_format=spec.value_format)
            labels_legend.append(entry["label"])
            colors_legend.append(c)
        ax.set_xticks(x)
        ax.set_xticklabels(x_labels, rotation=0, ha="center")
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
            c = palette[i % len(palette)]
            bars = ax.bar(offsets, values, width=bar_width, color=c,
                          zorder=3, linewidth=0)
            _label_clustered_bars(ax, bars, values, label_inside_top,
                                  value_format=spec.value_format)
            labels_legend.append(entry["label"])
            colors_legend.append(c)
        ax.set_xticks(x)
        ax.set_xticklabels(_month_labels(all_idx), rotation=0, ha="center")

    _style_axes(ax)
    _apply_axis_format(ax, spec)
    if labels_legend:
        _dot_legend(ax, labels_legend, colors_legend)


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

    _draw_clustered_bar(ax, spec, bar_resolved, palette, label_inside_top=True)

    s = line_entry["raw"]
    if not isinstance(s, pd.Series):
        return

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
    smooth_x, smooth_y = _catmull_rom_smooth(x, values)
    ax.plot(smooth_x, smooth_y, linewidth=1.8,
            color=line_color, zorder=4,
            solid_capstyle="round", solid_joinstyle="round")
    ax.plot(x, values, linestyle="None", marker="o", markersize=4.0,
            color=line_color, zorder=5,
            markerfacecolor=line_color, markeredgecolor=line_color)
    # Decide above/below per point: if the line value is below the max bar
    # at that x, place the line label below the marker (avoids overlapping
    # the bar value label sitting just above the bar top).
    bar_max_per_x: list[float | None] = []
    for xi in range(len(values)):
        bar_vals_at_x: list[float] = []
        for bs in bar_series:
            if multi_year:
                m = xi + 1
                cells = [
                    bv for bd, bv in bs.items()
                    if isinstance(bd, dt.date) and bd.month == m
                       and bv is not None and not pd.isna(bv)
                ]
                if cells:
                    bar_vals_at_x.append(float(sum(cells)))
            else:
                d = all_idx[xi]
                bv = bs.get(d) if d in bs.index else None
                if bv is not None and not pd.isna(bv):
                    bar_vals_at_x.append(float(bv))
        bar_max_per_x.append(max(bar_vals_at_x) if bar_vals_at_x else None)

    for xi, v in zip(x, values):
        if v is None or pd.isna(v):
            continue
        bar_max = bar_max_per_x[xi]
        below = bar_max is not None and v < bar_max
        ax.annotate(
            format_value(v, spec.value_format), xy=(xi, v),
            xytext=(0, -14 if below else 11),
            textcoords="offset points", ha="center",
            va="top" if below else "bottom",
            fontsize=LABEL_FONTSIZE_DATA, color=line_color, fontweight="bold",
            bbox=dict(facecolor="white", edgecolor="none",
                      pad=1.5, alpha=0.85),
        )

    # Re-issue the legend including the line entry.
    bar_labels = [r["label"] for r in bar_resolved]
    bar_colors = [palette[i % len(palette)] for i in range(len(bar_resolved))]
    _dot_legend(
        ax,
        bar_labels + [line_entry["label"]],
        bar_colors + [line_color],
    )


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
    ax.set_xlim(-1.15, 1.15)
    ax.set_ylim(-0.18, 1.05)
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

    # Actual value sits at the centroid of the open half-disk inside the
    # arc (≈ y = 4·r_inner / 3π ≈ 0.29 for r_inner = 0.68) so it reads as
    # centred within the donut rather than tucked under the apex.
    ax.text(0, 0.30, _format_eur(actual), ha="center", va="center",
            fontsize=24, fontweight="bold", color=fill_color)
    # Start / target labels right under the arc endpoints, top-aligned so
    # they sit immediately below the diameter line. ha="left"/"right" keeps
    # them inside x=[-1, +1] so bbox-tight crops symmetrically.
    ax.text(-1.0, -0.04, _format_eur(start), ha="left", va="top",
            fontsize=10, color=TEXT_MUTED)
    ax.text(1.0, -0.04, _format_eur(target), ha="right", va="top",
            fontsize=10, color=TEXT_MUTED)


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
    bars = ax.bar(x, values, color=colors, width=0.62, zorder=3, linewidth=0)
    ax.set_xticks(x)
    ax.set_xticklabels(_month_labels(labels), rotation=0, ha="center")
    ax.bar_label(
        bars,
        labels=[_format_eur(v) if v is not None and not pd.isna(v) else ""
                for v in values],
        padding=4, fontsize=LABEL_FONTSIZE_DATA, color=TEXT_INK,
        fontweight="medium",
    )

    legend_labels = [
        resolved[0]["label"] if resolved else "Actual",
        resolved[1]["label"] if len(resolved) > 1 else "Rolling budget",
    ]
    _style_axes(ax)
    _apply_axis_format(ax, spec)
    _dot_legend(ax, legend_labels, [actual_color, projected_color])


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

    color_map = (spec.style or {}).get("color_map") or {}
    for sub_ax, entry in [(axL, resolved[0]), (axR, resolved[1])]:
        s = entry["raw"]
        if not isinstance(s, pd.Series):
            continue
        s = s.dropna()
        s = s[s != 0]
        if s.empty:
            continue
        colors = _slice_colors(list(s.index.astype(str)), color_map, palette)
        labels = list(s.index.astype(str))
        wedges, _ = sub_ax.pie(
            s.values, labels=None, colors=colors,
            wedgeprops=dict(width=0.36, edgecolor="white", linewidth=2.5),
            startangle=90, counterclock=False,
        )
        _annotate_donut_slices(sub_ax, wedges, s.values, labels, s.sum(), colors)
        center_color = color_map.get("__center__", palette[0])
        sub_ax.text(0, 0, _format_eur(s.sum()), ha="center", va="center",
                    fontsize=LABEL_FONTSIZE_DONUT_CENTER - 4,
                    fontweight="bold", color=center_color)
        sub_ax.set_xlim(-1.7, 1.7)
        sub_ax.set_ylim(-1.4, 1.4)


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


_FIGSIZE_BY_TYPE: dict[str, tuple[float, float]] = {
    "line": (13, 4.6),
    "bar": (13, 4.2),
    "stacked_bar": (13, 4.6),
    "clustered_bar": (13, 4.6),
    "bar_with_line": (13, 4.6),
    "bar_projection": (13, 4.2),
    "donut": (8.5, 6.0),
    "donut_pair": (13, 6.0),
    "kpi_card": (4, 2.5),
    "gauge": (4, 3),
    "table": (12, 6),
    "waterfall": (13, 4.6),
}


def _figsize_for(chart_type: str) -> tuple[float, float]:
    return _FIGSIZE_BY_TYPE.get(chart_type, (10, 4.5))


def _apply_axis_format(ax, spec: ChartSpec) -> None:
    yfmt = spec.axes.get("y", {}).get("format") if spec.axes else None
    if yfmt == "EUR_thousands":
        ax.yaxis.set_major_formatter(
            plt.FuncFormatter(
                lambda v, _: f"€{v / 1000:,.0f}K" if v != 0 else "€0"
            )
        )
        ax.set_ylabel("")
    elif yfmt == "count":
        ax.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda v, _: f"{int(v):,}")
        )
        ax.set_ylabel("")
    elif yfmt == "percent_decimal":
        # Storage 0.15 → axis label 15%.
        ax.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda v, _: f"{v * 100:.0f}%")
        )
        ax.set_ylabel("")
    elif yfmt == "days":
        ax.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda v, _: f"{v:.0f}d")
        )
        ax.set_ylabel("")
    elif yfmt == "ratio":
        ax.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda v, _: f"{v:.2f}")
        )
        ax.set_ylabel("")


def _catmull_rom_smooth(
    xs: list, ys: list, samples_per_segment: int = 24,
) -> tuple[list[float], list[float]]:
    """Smooth a polyline through (xs, ys) with a Catmull-Rom spline.

    Drops NaN points before splining. Falls back to the raw polyline
    if there are fewer than 3 valid points.
    """
    import numpy as np
    pts = [
        (float(x), float(y)) for x, y in zip(xs, ys)
        if y is not None and not pd.isna(y)
    ]
    if len(pts) < 3:
        return [p[0] for p in pts], [p[1] for p in pts]
    arr = np.array(pts, dtype=float)
    extended = np.vstack([arr[0:1], arr, arr[-1:]])
    out_x: list[float] = []
    out_y: list[float] = []
    n_seg = len(arr) - 1
    for i in range(n_seg):
        p0, p1, p2, p3 = extended[i], extended[i+1], extended[i+2], extended[i+3]
        ts = np.linspace(0.0, 1.0, samples_per_segment,
                         endpoint=(i == n_seg - 1))
        for t in ts:
            t2, t3 = t * t, t * t * t
            point = 0.5 * (
                (2 * p1)
                + (-p0 + p2) * t
                + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                + (-p0 + 3 * p1 - 3 * p2 + p3) * t3
            )
            out_x.append(float(point[0]))
            out_y.append(float(point[1]))
    return out_x, out_y


def _format_eur(v: float) -> str:
    if abs(v) >= 1_000_000:
        return f"€{v / 1_000_000:.1f}M"
    if abs(v) >= 1_000:
        return f"€{v / 1_000:.0f}K"
    return f"€{v:.0f}"


def _format_count(v: float) -> str:
    return f"{int(round(v)):,}"


def _format_percent_decimal(v: float) -> str:
    """Storage convention: 0.155 → '15.5%'."""
    return f"{v * 100:.1f}%"


def _format_days(v: float) -> str:
    return f"{v:.1f} days"


def _format_ratio(v: float) -> str:
    return f"{v:.2f}"


_VALUE_FORMATTERS = {
    "eur":             _format_eur,
    "count":           _format_count,
    "percent_decimal": _format_percent_decimal,
    "days":            _format_days,
    "ratio":           _format_ratio,
}


def format_value(v: float | None, fmt: str = "eur") -> str:
    """Format a single value per the spec's ``value_format`` (default eur).
    Returns an empty string for missing values."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    formatter = _VALUE_FORMATTERS.get(fmt)
    if formatter is None:
        return _format_eur(float(v))
    return formatter(float(v))


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

    brand_palette = apply_brand(brand)
    palette = _resolve_palette(spec, brand_palette)
    figsize = _figsize_for(spec.chart_type)
    fig, ax = plt.subplots(figsize=figsize, dpi=200)
    _DRAW[spec.chart_type](ax, spec, resolved, palette)
    fig.tight_layout(pad=0.4)
    fig.savefig(png_path, bbox_inches="tight", facecolor="white",
                pad_inches=0.08)
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
