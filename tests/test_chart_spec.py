"""Tests for core.charts.spec — JSON Schema validation + ChartSpec loader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.charts.spec import ChartSpec, SpecValidationError, load_spec


VALID_MIN: dict = {
    "chart_id": "demo",
    "client": "cupffee",
    "title": "Demo Chart",
    "chart_type": "line",
    "source": "custom",
    "period": {"kind": "ltm"},
    "data": [
        {
            "label": "Series A",
            "query": {
                "kind": "trend",
                "data": "Sales",
                "scenario": "actual",
            },
        },
    ],
}


def _write(path: Path, obj: dict) -> Path:
    path.write_text(json.dumps(obj, indent=2))
    return path


class TestLoadSpec:
    def test_loads_valid_spec(self, tmp_path: Path) -> None:
        path = _write(tmp_path / "valid.json", VALID_MIN)
        spec = load_spec(path)
        assert isinstance(spec, ChartSpec)
        assert spec.chart_id == "demo"
        assert spec.chart_type == "line"

    def test_missing_required_field_raises(self, tmp_path: Path) -> None:
        bad = {k: v for k, v in VALID_MIN.items() if k != "chart_type"}
        path = _write(tmp_path / "bad.json", bad)
        with pytest.raises(SpecValidationError, match="chart_type"):
            load_spec(path)

    def test_unknown_chart_type_raises(self, tmp_path: Path) -> None:
        bad = {**VALID_MIN, "chart_type": "rainbow"}
        path = _write(tmp_path / "bad.json", bad)
        with pytest.raises(SpecValidationError):
            load_spec(path)

    def test_unknown_source_raises(self, tmp_path: Path) -> None:
        bad = {**VALID_MIN, "source": "magic"}
        path = _write(tmp_path / "bad.json", bad)
        with pytest.raises(SpecValidationError):
            load_spec(path)

    def test_unknown_period_kind_raises(self, tmp_path: Path) -> None:
        bad = {**VALID_MIN, "period": {"kind": "decade"}}
        path = _write(tmp_path / "bad.json", bad)
        with pytest.raises(SpecValidationError):
            load_spec(path)

    def test_period_full_year_requires_year(self, tmp_path: Path) -> None:
        # A schema for `full_year` requires `year`
        good = {**VALID_MIN, "period": {"kind": "full_year", "year": 2025}}
        path = _write(tmp_path / "good.json", good)
        load_spec(path)  # should not raise

    def test_query_kind_aggregation_validates(self, tmp_path: Path) -> None:
        good = dict(VALID_MIN)
        good["data"] = [
            {
                "label": "Sales by channel",
                "query": {
                    "kind": "aggregation",
                    "data": "Sales",
                    "level": "grp",
                    "scenario": "actual",
                },
            },
        ]
        path = _write(tmp_path / "good.json", good)
        spec = load_spec(path)
        assert spec.data[0].query["kind"] == "aggregation"

    def test_unknown_query_kind_raises(self, tmp_path: Path) -> None:
        bad = dict(VALID_MIN)
        bad["data"] = [{"label": "X", "query": {"kind": "magic"}}]
        path = _write(tmp_path / "bad.json", bad)
        with pytest.raises(SpecValidationError):
            load_spec(path)

    def test_platform_source_allows_platform_export_field(
        self, tmp_path: Path
    ) -> None:
        good = {
            **VALID_MIN,
            "source": "platform",
            "platform_export": "exports/revenue_dynamics.png",
        }
        path = _write(tmp_path / "good.json", good)
        spec = load_spec(path)
        assert spec.source == "platform"
        assert spec.platform_export == "exports/revenue_dynamics.png"


class TestChartSpec:
    def test_dataclass_round_trip(self, tmp_path: Path) -> None:
        path = _write(tmp_path / "v.json", VALID_MIN)
        spec = load_spec(path)
        # Required fields surfaced as attributes
        assert spec.title == "Demo Chart"
        assert spec.entity is None  # not provided → None default
        assert spec.notes == ""

    def test_data_entries_typed(self, tmp_path: Path) -> None:
        path = _write(tmp_path / "v.json", VALID_MIN)
        spec = load_spec(path)
        assert len(spec.data) == 1
        assert spec.data[0].label == "Series A"
        assert spec.data[0].query["data"] == "Sales"


class TestRealCupffeeSpec:
    def test_first_cupffee_spec_loads(self) -> None:
        spec = load_spec("specs/cupffee/kpi_net_vs_gross_burn.json")
        assert spec.client == "cupffee"
        assert spec.chart_type == "line"
        assert spec.source == "custom"
