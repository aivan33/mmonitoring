"""Tests for core.charts.render — period/query resolution + end-to-end render."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from core.charts.render import (
    render,
    resolve_period,
    resolve_query,
)
from core.charts.spec import ChartSpec, DataSeries


# ---------------------------------------------------------------------------
# Period resolution — pure logic
# ---------------------------------------------------------------------------

class TestResolvePeriod:
    def test_current_month(self) -> None:
        start, end = resolve_period({"kind": "current_month"}, dt.date(2025, 12, 1))
        assert start == end == dt.date(2025, 12, 1)

    def test_ytd(self) -> None:
        start, end = resolve_period({"kind": "ytd"}, dt.date(2025, 7, 1))
        assert start == dt.date(2025, 1, 1)
        assert end == dt.date(2025, 7, 1)

    def test_ltm_default_12_months(self) -> None:
        start, end = resolve_period({"kind": "ltm"}, dt.date(2025, 12, 1))
        # 12 months ending Dec 2025 → Jan 2025 to Dec 2025
        assert start == dt.date(2025, 1, 1)
        assert end == dt.date(2025, 12, 1)

    def test_ltm_custom_months(self) -> None:
        start, end = resolve_period({"kind": "ltm", "months": 6}, dt.date(2025, 12, 1))
        # 6 months ending Dec 2025 → Jul to Dec
        assert start == dt.date(2025, 7, 1)
        assert end == dt.date(2025, 12, 1)

    def test_ltm_crosses_year_boundary(self) -> None:
        start, end = resolve_period({"kind": "ltm"}, dt.date(2026, 3, 1))
        assert start == dt.date(2025, 4, 1)
        assert end == dt.date(2026, 3, 1)

    def test_month_offset_negative(self) -> None:
        start, end = resolve_period({"kind": "month_offset", "offset": -3},
                                    dt.date(2026, 3, 1))
        assert start == end == dt.date(2025, 12, 1)

    def test_full_year(self) -> None:
        start, end = resolve_period({"kind": "full_year", "year": 2024},
                                    dt.date(2025, 12, 1))
        assert start == dt.date(2024, 1, 1)
        assert end == dt.date(2024, 12, 1)

    def test_explicit(self) -> None:
        start, end = resolve_period({"kind": "explicit", "year": 2023, "month": 7},
                                    dt.date(2025, 12, 1))
        assert start == end == dt.date(2023, 7, 1)

    def test_range(self) -> None:
        start, end = resolve_period(
            {"kind": "range", "start": "2024-06-01", "end": "2025-05-01"},
            dt.date(2025, 12, 1),
        )
        assert start == dt.date(2024, 6, 1)
        assert end == dt.date(2025, 5, 1)


# ---------------------------------------------------------------------------
# Query resolution — needs cupffee_test_db fixture
# ---------------------------------------------------------------------------

class TestResolveQuery:
    def test_trend_single_data(self, cupffee_test_db: Path) -> None:
        result = resolve_query(
            {"kind": "trend", "data": "Sales", "scenario": "actual"},
            client="cupffee", entity="cupffee",
            start=dt.date(2025, 1, 1), end=dt.date(2025, 12, 1),
        )
        # Fixture: Sales = 100 + 50 + 20 = 170 every month
        assert len(result) == 12
        assert all(v == pytest.approx(170.0) for v in result.values)

    def test_trend_multi_data_summed(self, cupffee_test_db: Path) -> None:
        result = resolve_query(
            {"kind": "trend",
             "data": ["Sales", "Cost of Sales"],
             "scenario": "actual"},
            client="cupffee", entity="cupffee",
            start=dt.date(2025, 1, 1), end=dt.date(2025, 12, 1),
        )
        # Sales=170, Cost of Sales=-30 every month → 140
        assert all(v == pytest.approx(140.0) for v in result.values)

    def test_trend_signs_inverts(self, cupffee_test_db: Path) -> None:
        result = resolve_query(
            {"kind": "trend",
             "data": ["Sales", "Cost of Sales"],
             "signs": [1, -1],
             "scenario": "actual"},
            client="cupffee", entity="cupffee",
            start=dt.date(2025, 1, 1), end=dt.date(2025, 12, 1),
        )
        # 170 - (-30) = 200
        assert all(v == pytest.approx(200.0) for v in result.values)

    def test_value_query(self, cupffee_test_db: Path) -> None:
        result = resolve_query(
            {"kind": "value",
             "data": "Sales", "grp": "Distributors", "subgroup": "220 ml",
             "scenario": "actual"},
            client="cupffee", entity="cupffee",
            start=dt.date(2025, 1, 1), end=dt.date(2025, 1, 1),
        )
        assert result == 100.0

    def test_aggregation_query(self, cupffee_test_db: Path) -> None:
        result = resolve_query(
            {"kind": "aggregation",
             "data": "Sales", "level": "grp", "scenario": "actual"},
            client="cupffee", entity="cupffee",
            start=dt.date(2025, 1, 1), end=dt.date(2025, 1, 1),
        )
        assert set(result.index) == {"Distributors", "Direct Sales"}

    def test_signs_length_mismatch_raises(self, cupffee_test_db: Path) -> None:
        with pytest.raises(ValueError, match="signs"):
            resolve_query(
                {"kind": "trend", "data": ["Sales", "Cost of Sales"],
                 "signs": [1], "scenario": "actual"},
                client="cupffee", entity="cupffee",
                start=dt.date(2025, 1, 1), end=dt.date(2025, 12, 1),
            )


# ---------------------------------------------------------------------------
# End-to-end render — line chart
# ---------------------------------------------------------------------------

class TestRenderLine:
    def test_writes_png_and_json_sidecar(
        self, cupffee_test_db: Path, tmp_path: Path
    ) -> None:
        spec = ChartSpec(
            chart_id="trend_test",
            client="cupffee",
            title="Sales Trend",
            chart_type="line",
            source="custom",
            period={"kind": "ltm"},
            data=[DataSeries(
                label="Sales",
                query={"kind": "trend", "data": "Sales", "scenario": "actual"},
            )],
        )
        out_dir = tmp_path / "out"
        png, sidecar = render(spec, anchor=dt.date(2025, 12, 1),
                              brand={}, out_dir=out_dir)
        assert png.exists()
        assert sidecar.exists()
        assert png.suffix == ".png"
        assert sidecar.suffix == ".json"

    def test_sidecar_contains_resolved_data(
        self, cupffee_test_db: Path, tmp_path: Path
    ) -> None:
        spec = ChartSpec(
            chart_id="trend_test",
            client="cupffee",
            title="Sales Trend",
            chart_type="line",
            source="custom",
            period={"kind": "ltm"},
            data=[DataSeries(
                label="Sales",
                query={"kind": "trend", "data": "Sales", "scenario": "actual"},
            )],
        )
        _, sidecar = render(spec, anchor=dt.date(2025, 12, 1),
                            brand={}, out_dir=tmp_path)
        payload = json.loads(sidecar.read_text())
        assert "spec" in payload
        assert "anchor" in payload
        assert "resolved_period" in payload
        assert "data" in payload
        assert "generated_at" in payload
        assert len(payload["data"][0]["values"]) == 12  # 12 months in LTM

    def test_platform_source_writes_placeholder(
        self, cupffee_test_db: Path, tmp_path: Path
    ) -> None:
        spec = ChartSpec(
            chart_id="revenue_dynamics",
            client="cupffee",
            title="Revenue Dynamics",
            chart_type="line",
            source="platform",
            platform_export="exports/revenue_dynamics.png",
            period={"kind": "ltm"},
            data=[DataSeries(label="x", query={"kind": "trend", "data": "Sales"})],
        )
        png, sidecar = render(spec, anchor=dt.date(2025, 12, 1),
                              brand={}, out_dir=tmp_path)
        # Placeholder PNG and sidecar still produced.
        assert png.exists()
        assert sidecar.exists()
        payload = json.loads(sidecar.read_text())
        assert payload.get("placeholder") is True


class TestUnsupportedType:
    def test_raises_for_unimplemented(
        self, cupffee_test_db: Path, tmp_path: Path
    ) -> None:
        # 'table' is in the schema enum but not in _DRAW dispatch yet —
        # use it as the canonical not-yet-implemented type. (waterfall
        # moved from this slot when _draw_waterfall landed.)
        spec = ChartSpec(
            chart_id="x",
            client="cupffee",
            title="x",
            chart_type="table",
            source="custom",
            period={"kind": "current_month"},
            data=[DataSeries(label="x",
                             query={"kind": "trend", "data": "Sales"})],
        )
        with pytest.raises(NotImplementedError, match="table"):
            render(spec, anchor=dt.date(2025, 1, 1), brand={}, out_dir=tmp_path)


class TestClusteredBarAxisOrdering:
    """clustered_bar must show chronological mmm-yy labels for LTM windows.

    A multi-year span without month-of-year collisions (e.g. Apr 25 –
    Mar 26) is a single LTM time-series: the x-axis should run Apr-25 →
    Mar-26 so the latest month sits on the right. The year-over-year
    bucketed view (month names without year) should only kick in when
    the same calendar month appears in more than one year, which is the
    intended use case for prior-period comparisons.
    """

    @staticmethod
    def _draw(series: dict) -> list[str]:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from core.charts import tokens as tokens_mod
        from core.charts.render import _draw_clustered_bar
        from core.charts.spec import ChartSpec, DataSeries

        spec = ChartSpec(
            chart_id="cb", client="x", title="cb",
            chart_type="clustered_bar", source="custom",
            period={"kind": "ltm"},
            data=[DataSeries(label=lbl,
                             query={"kind": "trend", "data": lbl})
                  for lbl in series],
        )
        import pandas as pd
        resolved = [
            {"label": lbl, "raw": pd.Series(vals)} for lbl, vals in series.items()
        ]
        fig, ax = plt.subplots()
        try:
            _draw_clustered_bar(ax, spec, resolved, ["#000", "#111"], tokens_mod.DEFAULT)
            return [t.get_text() for t in ax.get_xticklabels()]
        finally:
            plt.close(fig)

    def test_ltm_uses_chronological_mmm_yy(self) -> None:
        # Apr 2025 – Mar 2026: no calendar month appears twice.
        dates = [dt.date(2025, m, 1) for m in range(4, 13)] + \
                [dt.date(2026, m, 1) for m in (1, 2, 3)]
        series = {"A": {d: 1.0 for d in dates}}
        labels = self._draw(series)
        assert labels == [
            "Apr-25", "May-25", "Jun-25", "Jul-25", "Aug-25", "Sep-25",
            "Oct-25", "Nov-25", "Dec-25", "Jan-26", "Feb-26", "Mar-26",
        ]

    def test_year_over_year_keeps_month_only_buckets(self) -> None:
        # Same months appear in two years — bucketed compare is intended.
        dates_25 = [dt.date(2025, m, 1) for m in range(1, 13)]
        dates_26 = [dt.date(2026, m, 1) for m in range(1, 13)]
        series = {
            "A": {d: 1.0 for d in dates_25},
            "B": {d: 2.0 for d in dates_26},
        }
        labels = self._draw(series)
        assert labels == [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        ]


# ---------------------------------------------------------------------------
# KPI query resolution (operational_kpis source)
# ---------------------------------------------------------------------------

import sqlite3 as _sqlite3
import yaml as _yaml
from core.data import schema as _schema
from core.data import query as _query_module


@pytest.fixture
def kpi_chart_db(tmp_path: Path, monkeypatch) -> Path:
    """Synthetic client with operational_kpis rows for chart-render tests."""
    cdir = tmp_path / "clients" / "almacena"
    (cdir / "data").mkdir(parents=True)
    (cdir / "config.yaml").write_text(_yaml.safe_dump({
        "entities": ["ap_foundation"],
        "brand": {"primary": "#1B3A5C", "accent": "#E89B4B"},
    }))
    db = cdir / "data" / "almacena.db"
    _schema.wipe_and_create(db)
    with _sqlite3.connect(db) as conn:
        conn.executemany(
            "INSERT INTO operational_kpis VALUES (?, ?, ?, ?)",
            [
                ("2026-01-01", "ap_foundation", "GMV", 15_680_330.25),
                ("2026-02-01", "ap_foundation", "GMV", 19_815_603.14),
                ("2026-03-01", "ap_foundation", "GMV", 20_481_861.06),
                ("2026-01-01", "ap_foundation", "# Invoices", 69.0),
                ("2026-02-01", "ap_foundation", "# Invoices", 75.0),
                ("2026-03-01", "ap_foundation", "# Invoices", 101.0),
                ("2026-01-01", "ap_foundation", "Funded Amount", 13_739_974.0),
                ("2026-02-01", "ap_foundation", "Funded Amount", 17_016_568.0),
                ("2026-03-01", "ap_foundation", "Funded Amount", 17_221_971.0),
            ],
        )
        conn.commit()
    monkeypatch.setattr(_query_module, "_ROOT", tmp_path)
    return tmp_path


class TestResolveKPIQueries:
    def test_kpi_trend_returns_series(self, kpi_chart_db: Path) -> None:
        result = resolve_query(
            {"kind": "kpi_trend", "kpi": "GMV"},
            client="almacena", entity="ap_foundation",
            start=dt.date(2026, 1, 1), end=dt.date(2026, 3, 1),
        )
        import pandas as pd
        assert isinstance(result, pd.Series)
        assert list(result.index) == [
            dt.date(2026, 1, 1), dt.date(2026, 2, 1), dt.date(2026, 3, 1),
        ]
        assert result.iloc[-1] == pytest.approx(20_481_861.06)

    def test_kpi_trend_filters_to_window(self, kpi_chart_db: Path) -> None:
        result = resolve_query(
            {"kind": "kpi_trend", "kpi": "GMV"},
            client="almacena", entity="ap_foundation",
            start=dt.date(2026, 2, 1), end=dt.date(2026, 2, 28),
        )
        assert len(result) == 1
        assert result.iloc[0] == pytest.approx(19_815_603.14)

    def test_kpi_value_returns_scalar(self, kpi_chart_db: Path) -> None:
        result = resolve_query(
            {"kind": "kpi_value", "kpi": "# Invoices"},
            client="almacena", entity="ap_foundation",
            start=dt.date(2026, 3, 1), end=dt.date(2026, 3, 1),
        )
        assert result == 101.0

    def test_kpi_value_missing_returns_none(self, kpi_chart_db: Path) -> None:
        result = resolve_query(
            {"kind": "kpi_value", "kpi": "Bogus"},
            client="almacena", entity="ap_foundation",
            start=dt.date(2026, 3, 1), end=dt.date(2026, 3, 1),
        )
        assert result is None

    def test_kpi_diff_subtracts_element_wise(self, kpi_chart_db: Path) -> None:
        # GMV - Funded Amount per month; Mar-26: 20,481,861 - 17,221,971 = 3,259,890
        result = resolve_query(
            {"kind": "kpi_diff",
             "minuend": "GMV",
             "subtrahend": "Funded Amount"},
            client="almacena", entity="ap_foundation",
            start=dt.date(2026, 1, 1), end=dt.date(2026, 3, 1),
        )
        import pandas as pd
        assert isinstance(result, pd.Series)
        assert list(result.index) == [
            dt.date(2026, 1, 1), dt.date(2026, 2, 1), dt.date(2026, 3, 1),
        ]
        assert result.iloc[-1] == pytest.approx(3_259_890.0, rel=1e-4)


def test_render_kpi_chart_end_to_end(kpi_chart_db: Path, tmp_path: Path) -> None:
    """A spec referencing kpi_trend renders to PNG + sidecar without error,
    and the sidecar values match what we inserted."""
    spec = ChartSpec(
        chart_id="almacena_gmv",
        client="almacena",
        title="GMV — Q1 2026",
        chart_type="line",
        source="custom",
        period={"kind": "ltm", "months": 3},
        data=[DataSeries(label="GMV", query={"kind": "kpi_trend", "kpi": "GMV"})],
        entity="ap_foundation",
        axes={"y": {"format": "EUR_thousands"}},
    )
    out_dir = tmp_path / "out"
    png_path, json_path = render(
        spec, anchor=dt.date(2026, 3, 1),
        brand={"primary": "#1B3A5C"}, out_dir=out_dir,
    )
    assert png_path.exists()
    assert png_path.stat().st_size > 1000  # sanity: real PNG content
    sidecar = json.loads(json_path.read_text())
    series = sidecar["data"][0]["values"]
    assert len(series) == 3
    # Last point matches what we inserted (Mar).
    last = series[-1]
    assert last["key"] == "2026-03-01"
    assert last["value"] == pytest.approx(20_481_861.06)

