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
        spec = ChartSpec(
            chart_id="x",
            client="cupffee",
            title="x",
            chart_type="waterfall",
            source="custom",
            period={"kind": "current_month"},
            data=[DataSeries(label="x",
                             query={"kind": "trend", "data": "Sales"})],
        )
        with pytest.raises(NotImplementedError, match="waterfall"):
            render(spec, anchor=dt.date(2025, 1, 1), brand={}, out_dir=tmp_path)
