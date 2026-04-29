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

        total: pd.Series | None = None
        for d, s in zip(data_list, signs):
            series = get_trend(
                d, grp=grp, subgroup=subgroup, scenario=scenario,
                start_date=start, end_date=end,
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
        return get_aggregation(
            query["data"], start, scenario=scenario, level=level,
            client=client, entity=entity,
        )

    raise ValueError(f"unknown query kind {kind!r}")


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
        ax.set_xticklabels([str(i) for i in s.index], rotation=45, ha="right")
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
    x_labels: list[str] | None = None
    for i, series in enumerate(resolved):
        s = series["raw"]
        if not isinstance(s, pd.Series):
            continue
        if x_labels is None:
            x_labels = [str(idx) for idx in s.index]
        ax.bar(
            range(len(s)), s.values,
            bottom=bottom,
            color=palette[i % len(palette)],
            label=series["label"],
        )
        bottom = s.values if bottom is None else bottom + s.values
    if x_labels:
        ax.set_xticks(range(len(x_labels)))
        ax.set_xticklabels(x_labels, rotation=45, ha="right")
    ax.set_title(spec.title, loc="left", fontsize=12, fontweight="bold")
    ax.legend(loc="best", frameon=False)
    _apply_axis_format(ax, spec)


_DRAW: dict[str, Any] = {
    "line": _draw_line,
    "bar": _draw_bar,
    "stacked_bar": _draw_stacked_bar,
    "donut": _draw_donut,
    "kpi_card": _draw_kpi_card,
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
