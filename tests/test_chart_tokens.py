"""Tests for core.charts.tokens — design-system tokens for the chart renderer.

The tokens module captures the values the renderer reads to style charts:
palette, text/grid colours, font sizes, KPI card chrome. One preset ships
in-tree: ALMACENA_ARCHIVE, mirroring the design from
_archive/dashboard/tokens.json + the JS values that actually render in that
bundle.

Existing renderer constants are preserved as the default preset so
clients without an explicit override keep their current output.
"""

from __future__ import annotations

import pytest

from core.charts.tokens import ALMACENA_ARCHIVE, DEFAULT, Tokens


class TestTokensDataclass:
    def test_is_frozen(self) -> None:
        with pytest.raises(Exception):  # FrozenInstanceError under dataclass
            DEFAULT.text_ink = "#000000"  # type: ignore[misc]

    def test_palette_is_list_of_hex_strings(self) -> None:
        assert isinstance(DEFAULT.palette, tuple)  # frozen → tuple
        assert all(isinstance(c, str) and c.startswith("#") for c in DEFAULT.palette)
        assert len(DEFAULT.palette) >= 3

    def test_line_fidelity_fields_exist(self) -> None:
        # Line/area visual knobs surfaced as tokens so presets can swap them.
        for field in (
            "line_width", "line_fill_alpha", "marker_size",
            "tick_color",
        ):
            assert hasattr(DEFAULT, field), f"DEFAULT missing token field {field!r}"
            assert hasattr(ALMACENA_ARCHIVE, field)


class TestDefaultPresetMatchesCurrentRenderer:
    """The DEFAULT preset must equal the constants used today so existing
    output is unchanged when a client doesn't pick a preset."""

    def test_default_text_ink_matches_render_constant(self) -> None:
        from core.charts import render
        assert DEFAULT.text_ink == render.TEXT_INK

    def test_default_text_muted_matches_render_constant(self) -> None:
        from core.charts import render
        assert DEFAULT.text_muted == render.TEXT_MUTED

    def test_default_grid_color_matches_render_constant(self) -> None:
        from core.charts import render
        assert DEFAULT.grid_color == render.GRID_INK

    def test_default_font_sizes_match_render_constants(self) -> None:
        from core.charts import render
        assert DEFAULT.font_size_tick == render.LABEL_FONTSIZE_TICK
        assert DEFAULT.font_size_data == render.LABEL_FONTSIZE_DATA
        assert DEFAULT.font_size_legend == render.LABEL_FONTSIZE_LEGEND
        assert DEFAULT.font_size_donut_center == render.LABEL_FONTSIZE_DONUT_CENTER

    def test_default_fallback_palette_matches_render_constant(self) -> None:
        from core.charts import render
        assert list(DEFAULT.palette) == render._DEFAULT_PALETTE


class TestAlmacenaArchivePreset:
    """ALMACENA_ARCHIVE encodes the values from _archive/dashboard/tokens.json
    (and the JS that actually renders them). It should differ from DEFAULT —
    that's the whole point — and use the deep-teal palette."""

    def test_palette_is_archive_brand(self) -> None:
        # From tokens.json color.chart.series — deep teal → mid teal → bright
        # teal → gold → orange (6-step monochrome-plus-accents).
        assert ALMACENA_ARCHIVE.palette[0] == "#013E3F"
        assert ALMACENA_ARCHIVE.palette[1] == "#006768"
        assert ALMACENA_ARCHIVE.palette[2] == "#009091"
        assert ALMACENA_ARCHIVE.palette[3] == "#20D9DC"
        assert "#E1AA12" in ALMACENA_ARCHIVE.palette
        assert "#F98F45" in ALMACENA_ARCHIVE.palette

    def test_text_colors_match_archive_tokens(self) -> None:
        # color.text.primary / secondary in tokens.json
        assert ALMACENA_ARCHIVE.text_ink == "#222222"
        assert ALMACENA_ARCHIVE.text_muted == "#666666"

    def test_line_fidelity_matches_archive(self) -> None:
        # Legacy charts.js GMV trend: borderWidth 3, fill: true (alpha ~0.1),
        # pointRadius 5. Grid rgba(0,0,0,0.04). Tick color #9ca3af.
        assert ALMACENA_ARCHIVE.line_width == 3.0
        assert ALMACENA_ARCHIVE.line_fill_alpha == 0.10
        assert ALMACENA_ARCHIVE.marker_size == 5.0
        assert ALMACENA_ARCHIVE.tick_color == "#9ca3af"
        # Lighter grid than DEFAULT.
        assert ALMACENA_ARCHIVE.grid_color == "rgba(0,0,0,0.04)"

    def test_line_fidelity_defaults_preserve_legacy(self) -> None:
        # DEFAULT keeps the existing line look so Cupffee renders unchanged.
        assert DEFAULT.line_width == 1.8
        assert DEFAULT.line_fill_alpha == 0.0
        assert DEFAULT.marker_size == 4.0
        # DEFAULT tick colour matches the renderer's TEXT_MUTED constant.
        from core.charts import render
        assert DEFAULT.tick_color == render.TEXT_MUTED

    def test_kpi_chrome_matches_archive(self) -> None:
        # KPI card border: 2px deep-teal, per tokens.json components.kpi.container
        assert ALMACENA_ARCHIVE.kpi_border_color == "#013E3F"
        assert ALMACENA_ARCHIVE.kpi_border_width == 2.0
        # KPI value styling: 28px bold #222222 (tokens.json components.kpi.value).
        # We store the px value verbatim; the renderer translates px→pt.
        assert ALMACENA_ARCHIVE.kpi_value_color == "#222222"
        # Trend arrow colours come from the archive's CSS (kpi-trend.trend-up /
        # trend-down classes in dashboard/src/css/main.css).
        assert ALMACENA_ARCHIVE.kpi_trend_up_color == "#10b981"
        assert ALMACENA_ARCHIVE.kpi_trend_down_color == "#F4845F"

    def test_differs_from_default(self) -> None:
        # Sanity: if this is the same as DEFAULT, the preset doesn't do its job.
        assert ALMACENA_ARCHIVE.palette != DEFAULT.palette
        assert ALMACENA_ARCHIVE.text_ink != DEFAULT.text_ink


class TestLookupByName:
    """Brand configs reference presets by string name. The module must
    expose a single resolver that maps preset names to Tokens instances."""

    def test_resolve_default(self) -> None:
        from core.charts.tokens import resolve

        assert resolve(None) is DEFAULT
        assert resolve("default") is DEFAULT

    def test_resolve_almacena_archive(self) -> None:
        from core.charts.tokens import resolve

        assert resolve("almacena_archive") is ALMACENA_ARCHIVE

    def test_resolve_unknown_raises(self) -> None:
        from core.charts.tokens import resolve

        with pytest.raises(ValueError, match="unknown tokens preset"):
            resolve("rainbow_dash")


# ---------------------------------------------------------------------------
# Task 1.2 — apply_brand integration
# ---------------------------------------------------------------------------

class TestApplyBrandIntegration:
    """apply_brand reads brand['tokens_preset'] and uses the resolved Tokens
    instance for matplotlib rcParams and the returned palette. An absent
    or 'default' preset must reproduce the renderer's pre-tokens behaviour
    so existing client output stays byte-for-byte identical."""

    def test_returns_render_context_with_palette_and_tokens(self) -> None:
        from core.charts.render import apply_brand

        ctx = apply_brand({})
        # Bundles both the colour list and the resolved design tokens.
        assert hasattr(ctx, "palette")
        assert hasattr(ctx, "tokens")
        assert ctx.tokens is DEFAULT

    def test_absent_preset_returns_default_tokens(self) -> None:
        from core.charts.render import apply_brand

        ctx = apply_brand({"primary": "#1F4D4D", "accent": "#D4A024"})
        assert ctx.tokens is DEFAULT

    def test_named_preset_returns_resolved_tokens(self) -> None:
        from core.charts.render import apply_brand

        ctx = apply_brand({"tokens_preset": "almacena_archive"})
        assert ctx.tokens is ALMACENA_ARCHIVE

    def test_palette_keeps_brand_overrides_first(self) -> None:
        """primary/accent/budget brand colours still win over the preset
        palette so per-client identity overrides the design-system fallback."""
        from core.charts.render import apply_brand

        ctx = apply_brand({
            "primary": "#1F4D4D", "accent": "#D4A024",
            "tokens_preset": "almacena_archive",
        })
        assert ctx.palette[0] == "#1F4D4D"
        assert ctx.palette[1] == "#D4A024"
        # Then the archive palette fills the remainder.
        assert "#013E3F" in ctx.palette
        assert "#20D9DC" in ctx.palette

    def test_default_preset_palette_matches_legacy_constant(self) -> None:
        """Byte-for-byte invariant: with no brand colours and no preset,
        the returned palette equals the legacy _DEFAULT_PALETTE constant."""
        from core.charts.render import _DEFAULT_PALETTE, apply_brand

        ctx = apply_brand({})
        assert ctx.palette == _DEFAULT_PALETTE

    def test_archive_preset_sets_archive_text_ink_rcparam(self) -> None:
        """Under the archive preset, matplotlib's default text colour is
        the archive's #222222, not the renderer's legacy #2D2D2D."""
        import matplotlib.pyplot as plt

        from core.charts.render import apply_brand

        apply_brand({"tokens_preset": "almacena_archive"})
        assert plt.rcParams["text.color"] == ALMACENA_ARCHIVE.text_ink

        # Reset back to DEFAULT for any test that runs after.
        apply_brand({})

    def test_unknown_preset_raises(self) -> None:
        from core.charts.render import apply_brand

        with pytest.raises(ValueError, match="unknown tokens preset"):
            apply_brand({"tokens_preset": "rainbow_dash"})


# ---------------------------------------------------------------------------
# Task 1.3 — _draw_kpi_card consumes tokens
# ---------------------------------------------------------------------------

class TestKpiCardTokens:
    """The KPI card draws the brand border, value colour, and trend arrows
    from tokens. Under DEFAULT the rendered card matches the renderer's
    pre-tokens output (no visible border, brand-primary value, legacy
    arrow colours). Under ALMACENA_ARCHIVE the deep-teal border, #222222
    value, and #10b981 / #F4845F arrows show up."""

    def _make_spec(self, value_format: str = "eur"):
        from core.charts.spec import ChartSpec, DataSeries
        return ChartSpec(
            chart_id="kpi_test",
            client="cupffee",
            title="Test KPI",
            chart_type="kpi_card",
            source="custom",
            period={"kind": "current_month"},
            data=[DataSeries(label="v", query={"kind": "kpi_value", "kpi": "X"})],
            value_format=value_format,
        )

    def test_default_uses_palette_primary_for_value(self) -> None:
        """Under DEFAULT the KPI value text still uses palette[0] — the
        renderer's pre-tokens behaviour."""
        import matplotlib.pyplot as plt

        from core.charts.render import _draw_kpi_card

        fig, ax = plt.subplots()
        _draw_kpi_card(
            ax, self._make_spec(), [{"label": "v", "raw": 1234.0}],
            palette=["#FF00FF", "#000000"],
            tokens=DEFAULT,
        )
        # Find the big numeric text (fontsize >= 28 by current render)
        large = [t for t in ax.texts if t.get_fontsize() >= 28]
        assert large, "expected a large value text"
        # DEFAULT preset: value colour follows palette[0].
        assert large[0].get_color() == "#FF00FF"
        plt.close(fig)

    def test_archive_uses_kpi_value_color_not_palette(self) -> None:
        """Under ALMACENA_ARCHIVE the value colour is the token's
        kpi_value_color (#222222), independent of the palette so the
        deep-teal border + dark-ink value combo from tokens.json
        renders correctly."""
        import matplotlib.pyplot as plt

        from core.charts.render import _draw_kpi_card

        fig, ax = plt.subplots()
        _draw_kpi_card(
            ax, self._make_spec(), [{"label": "v", "raw": 1234.0}],
            palette=["#FF00FF"],
            tokens=ALMACENA_ARCHIVE,
        )
        large = [t for t in ax.texts if t.get_fontsize() >= 28]
        assert large[0].get_color() == "#222222"
        plt.close(fig)

    def test_archive_trend_up_color(self) -> None:
        """Positive MoM delta uses tokens.kpi_trend_up_color (#10b981)."""
        import matplotlib.pyplot as plt

        from core.charts.render import _draw_kpi_card

        fig, ax = plt.subplots()
        _draw_kpi_card(
            ax, self._make_spec(),
            [{"label": "now", "raw": 200.0}, {"label": "prev", "raw": 100.0}],
            palette=["#000000"],
            tokens=ALMACENA_ARCHIVE,
        )
        trend = [t for t in ax.texts if "vs last period" in t.get_text()]
        assert trend, "expected trend annotation"
        assert trend[0].get_color() == "#10b981"
        plt.close(fig)

    def test_archive_trend_down_color(self) -> None:
        """Negative MoM delta uses tokens.kpi_trend_down_color (#F4845F)."""
        import matplotlib.pyplot as plt

        from core.charts.render import _draw_kpi_card

        fig, ax = plt.subplots()
        _draw_kpi_card(
            ax, self._make_spec(),
            [{"label": "now", "raw": 50.0}, {"label": "prev", "raw": 100.0}],
            palette=["#000000"],
            tokens=ALMACENA_ARCHIVE,
        )
        trend = [t for t in ax.texts if "vs last period" in t.get_text()]
        assert trend[0].get_color() == "#F4845F"
        plt.close(fig)

    def test_archive_draws_brand_border(self) -> None:
        """When tokens.kpi_border_width > 0, the KPI card draws a
        brand-coloured border around the axes (legacy CSS .kpi-card
        border-left). The archive preset has width 2 and colour #013E3F."""
        import matplotlib.pyplot as plt

        from core.charts.render import _draw_kpi_card

        fig, ax = plt.subplots()
        _draw_kpi_card(
            ax, self._make_spec(), [{"label": "v", "raw": 1234.0}],
            palette=["#000000"],
            tokens=ALMACENA_ARCHIVE,
        )
        # The border is a rectangle patch on the axes, coloured #013E3F.
        from matplotlib.patches import Rectangle
        rects = [
            p for p in ax.patches
            if isinstance(p, Rectangle) and p.get_edgecolor() is not None
        ]
        assert any(
            tuple(round(c, 3) for c in p.get_edgecolor()[:3]) ==
            tuple(round(c, 3) for c in (0x01 / 255, 0x3E / 255, 0x3F / 255))
            for p in rects
        ), "expected a deep-teal border rectangle on the KPI card"
        plt.close(fig)

    def test_default_no_visible_border(self) -> None:
        """Under DEFAULT (kpi_border_width=0) no border patch is added."""
        import matplotlib.pyplot as plt

        from core.charts.render import _draw_kpi_card

        fig, ax = plt.subplots()
        _draw_kpi_card(
            ax, self._make_spec(), [{"label": "v", "raw": 1234.0}],
            palette=["#000000"],
            tokens=DEFAULT,
        )
        from matplotlib.patches import Rectangle
        rects = [p for p in ax.patches if isinstance(p, Rectangle)]
        # Either no rectangles at all, or none with a visible edge colour.
        assert not any(
            p.get_linewidth() > 0 and p.get_edgecolor() is not None
            and tuple(p.get_edgecolor()[:3]) != (0, 0, 0, 0)[:3]
            for p in rects
        ), "DEFAULT preset must not draw a visible KPI border"
        plt.close(fig)
