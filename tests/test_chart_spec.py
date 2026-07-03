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

    def test_value_query_requires_grp_and_subgroup(self, tmp_path: Path) -> None:
        # kind=value without grp/subgroup would resolve to SQL NULL and render
        # empty — the schema must reject it up front (Fix 3).
        bad = dict(VALID_MIN)
        bad["data"] = [{"label": "X", "query": {"kind": "value", "data": "Cash"}}]
        path = _write(tmp_path / "bad.json", bad)
        with pytest.raises(SpecValidationError, match="grp"):
            load_spec(path)

    def test_value_query_with_grp_and_subgroup_validates(self, tmp_path: Path) -> None:
        good = dict(VALID_MIN)
        good["data"] = [{"label": "X", "query": {
            "kind": "value", "data": "Cash", "grp": "Cash", "subgroup": "Cash"}}]
        path = _write(tmp_path / "good.json", good)
        load_spec(path)  # should not raise

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
        spec = load_spec("clients/cupffee/chart_specs/kpi_net_vs_gross_burn.json")
        assert spec.client == "cupffee"
        assert spec.chart_type == "line"
        assert spec.source == "custom"


# ---------------------------------------------------------------------------
# KPI query kinds (operational_kpis source)
# ---------------------------------------------------------------------------

class TestKPIQueryKinds:
    def test_kpi_trend_accepted(self, tmp_path: Path) -> None:
        spec_dict = {
            **VALID_MIN,
            "data": [{
                "label": "GMV",
                "query": {"kind": "kpi_trend", "kpi": "GMV"},
            }],
        }
        path = _write(tmp_path / "kpi_trend.json", spec_dict)
        spec = load_spec(path)
        assert spec.data[0].query["kind"] == "kpi_trend"
        assert spec.data[0].query["kpi"] == "GMV"

    def test_kpi_value_accepted(self, tmp_path: Path) -> None:
        spec_dict = {
            **VALID_MIN,
            "period": {"kind": "current_month"},
            "data": [{
                "label": "# Invoices",
                "query": {"kind": "kpi_value", "kpi": "# Invoices"},
            }],
        }
        path = _write(tmp_path / "kpi_value.json", spec_dict)
        spec = load_spec(path)
        assert spec.data[0].query["kind"] == "kpi_value"

    def test_kpi_trend_without_kpi_field_raises(self, tmp_path: Path) -> None:
        spec_dict = {
            **VALID_MIN,
            "data": [{
                "label": "GMV",
                "query": {"kind": "kpi_trend"},  # missing kpi
            }],
        }
        path = _write(tmp_path / "missing.json", spec_dict)
        with pytest.raises(SpecValidationError, match="kpi"):
            load_spec(path)

    def test_kpi_value_without_kpi_field_raises(self, tmp_path: Path) -> None:
        spec_dict = {
            **VALID_MIN,
            "data": [{
                "label": "GMV",
                "query": {"kind": "kpi_value"},  # missing kpi
            }],
        }
        path = _write(tmp_path / "missing.json", spec_dict)
        with pytest.raises(SpecValidationError, match="kpi"):
            load_spec(path)

    def test_existing_trend_kinds_still_work(self, tmp_path: Path) -> None:
        """Adding new kinds should not break specs using the old trend kind."""
        path = _write(tmp_path / "trend.json", VALID_MIN)
        spec = load_spec(path)
        assert spec.data[0].query["kind"] == "trend"

