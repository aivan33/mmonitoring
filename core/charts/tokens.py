"""Design-system tokens for the chart renderer.

A ``Tokens`` instance captures the visual-design knobs the matplotlib
renderer reads when drawing a chart: palette, text/grid colours, font
sizes, KPI-card chrome. Two presets ship in-tree:

- ``DEFAULT`` mirrors the constants currently hard-coded in
  ``core.charts.render`` so clients without an explicit preset get
  unchanged output.
- ``ALMACENA_ARCHIVE`` mirrors the design from
  ``_archive/dashboard/tokens.json`` plus the JS values that actually
  render in that bundle. Opt in by setting ``brand.tokens_preset:
  almacena_archive`` in a client's ``config.yaml``.

The renderer is wired in ``core.charts.render.apply_brand`` — see Task
1.2. Tokens objects are frozen so a presets array can't be mutated by
accident.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Tokens:
    palette: tuple[str, ...]
    text_ink: str
    text_muted: str
    grid_color: str
    font_size_tick: float
    font_size_data: float
    font_size_legend: float
    font_size_donut_center: float
    kpi_border_color: str
    kpi_border_width: float
    kpi_value_color: str
    kpi_title_color: str
    kpi_trend_up_color: str
    kpi_trend_down_color: str


# Default = the values currently inlined in render.py. Tests pin these to
# the module constants so DEFAULT stays in sync if those ever move.
DEFAULT = Tokens(
    palette=("#2A625E", "#E67D5A", "#D4A24C", "#5A8AB8", "#7E6BA1", "#3D8F5C"),
    text_ink="#2D2D2D",
    text_muted="#6E6E6E",
    grid_color="#E5DBD5",
    font_size_tick=10.5,
    font_size_data=9.0,
    font_size_legend=10.5,
    font_size_donut_center=26,
    # KPI chrome under DEFAULT keeps the renderer's current behaviour:
    # no explicit border (matplotlib axis-off cards), brand-primary value
    # colour, neutral title colour, render.py's hard-coded delta arrow
    # colours (#2E7A56 up / #C24C44 down).
    kpi_border_color="#2D2D2D",
    kpi_border_width=0.0,
    kpi_value_color="#2D2D2D",
    kpi_title_color="#6E6E6E",
    kpi_trend_up_color="#2E7A56",
    kpi_trend_down_color="#C24C44",
)


# Archive preset — tokens.json + dashboard/src/css/main.css + charts.js.
# The palette comes from color.chart.series; the KPI colours from
# .kpi-trend.{trend-up,trend-down} in main.css (the JS source of truth,
# which is slightly different from tokens.json's semantic.success/error).
ALMACENA_ARCHIVE = Tokens(
    palette=("#013E3F", "#006768", "#009091", "#20D9DC", "#E1AA12", "#F98F45"),
    text_ink="#222222",
    text_muted="#666666",
    grid_color="#E5DBD5",
    font_size_tick=10.5,
    font_size_data=9.0,
    font_size_legend=10.5,
    font_size_donut_center=26,
    kpi_border_color="#013E3F",
    kpi_border_width=2.0,
    kpi_value_color="#222222",
    kpi_title_color="#666666",
    kpi_trend_up_color="#10b981",
    kpi_trend_down_color="#F4845F",
)


_PRESETS: dict[str, Tokens] = {
    "default": DEFAULT,
    "almacena_archive": ALMACENA_ARCHIVE,
}


def resolve(name: str | None) -> Tokens:
    """Look up a preset by name. ``None`` and ``"default"`` both return DEFAULT.

    Raises ``ValueError`` for an unknown name so a typo in
    ``config.yaml`` fails loudly instead of silently rendering the wrong
    design.
    """
    if name is None:
        return DEFAULT
    try:
        return _PRESETS[name]
    except KeyError as e:
        raise ValueError(
            f"unknown tokens preset {name!r}; "
            f"valid presets: {sorted(_PRESETS)}"
        ) from e
