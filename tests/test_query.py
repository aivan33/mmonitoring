"""Tests for core.data.query — the public surface that Stage 2 will import."""

from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path

import pandas as pd
import pytest
import yaml

from core.data import schema
from core.data import query as query_module
from core.data.query import (
    get_aggregation, get_kpi, get_kpi_trend, get_line, get_statement,
    get_trend, get_value, to_csv, ytd,
)


# ---------------------------------------------------------------------------
# get_value
# ---------------------------------------------------------------------------

class TestGetValue:
    def test_returns_value_for_known_row(self, cupffee_test_db: Path) -> None:
        v = get_value("Sales", "Distributors", "220 ml", "2025-01-01",
                      client="cupffee")
        assert v == 100.0

    def test_returns_none_for_missing_row(self, cupffee_test_db: Path) -> None:
        v = get_value("Sales", "Distributors", "999 ml", "2025-01-01",
                      client="cupffee")
        assert v is None

    def test_accepts_date_object(self, cupffee_test_db: Path) -> None:
        v = get_value("Sales", "Distributors", "220 ml",
                      dt.date(2025, 1, 1), client="cupffee")
        assert v == 100.0

    def test_explicit_entity_filters(self, almacena_test_db: Path) -> None:
        v = get_value("Sales", "Group", "SG", "2025-01-01",
                      client="almacena", entity="consolidated")
        assert v == 1000.0
        v2 = get_value("Net Interest Revenue", "Group", "SG", "2025-01-01",
                       client="almacena", entity="ap_foundation")
        assert v2 == -100.0

    def test_multi_entity_without_explicit_entity_raises(
        self, almacena_test_db: Path
    ) -> None:
        with pytest.raises(ValueError, match="entity"):
            get_value("Sales", "Group", "SG", "2025-01-01", client="almacena")


# ---------------------------------------------------------------------------
# get_statement
# ---------------------------------------------------------------------------

class TestGetStatement:
    def test_returns_dataframe_for_period(self, cupffee_test_db: Path) -> None:
        df = get_statement("IS", "2025-12-01", client="cupffee")
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_first_row_is_first_in_source_order(self, cupffee_test_db: Path) -> None:
        # 'Sales' rows appear before 'Cost of Sales' in the source.
        df = get_statement("IS", "2025-12-01", client="cupffee")
        assert df.iloc[0]["data"] == "Sales"

    def test_orders_by_display_order(self, cupffee_test_db: Path) -> None:
        df = get_statement("IS", "2025-12-01", client="cupffee",
                           scenarios=("actual",))
        # Source order: 220 ml, 110 ml, 220 ml direct, materials
        assert list(df["subgroup"]) == ["220 ml", "110 ml", "220 ml", "Materials"]

    def test_only_returns_requested_statement(self, cupffee_test_db: Path) -> None:
        df = get_statement("IS", "2025-12-01", client="cupffee")
        # No BS rows should sneak in (the test fixture has BS data too).
        assert "Cash and cash equivalents" not in df["data"].values


# ---------------------------------------------------------------------------
# get_aggregation
# ---------------------------------------------------------------------------

class TestGetAggregation:
    def test_level_data_returns_one_element_series(
        self, cupffee_test_db: Path
    ) -> None:
        s = get_aggregation("Sales", "2025-01-01", client="cupffee", level="data")
        assert isinstance(s, pd.Series)
        assert len(s) == 1
        # 100 + 50 + 20 = 170
        assert s.loc["Sales"] == pytest.approx(170.0)

    def test_level_grp_returns_grp_indexed_series(
        self, cupffee_test_db: Path
    ) -> None:
        s = get_aggregation("Sales", "2025-01-01", client="cupffee", level="grp")
        assert isinstance(s, pd.Series)
        assert set(s.index) == {"Distributors", "Direct Sales"}
        assert s.loc["Distributors"] == pytest.approx(150.0)  # 100 + 50
        assert s.loc["Direct Sales"] == pytest.approx(20.0)

    def test_level_subgroup_returns_multiindex_series(
        self, cupffee_test_db: Path
    ) -> None:
        s = get_aggregation("Sales", "2025-01-01", client="cupffee",
                            level="subgroup")
        assert isinstance(s, pd.Series)
        assert isinstance(s.index, pd.MultiIndex)
        assert s.loc[("Distributors", "220 ml")] == 100.0

    def test_unknown_level_raises(self, cupffee_test_db: Path) -> None:
        with pytest.raises(ValueError, match="level"):
            get_aggregation("Sales", "2025-01-01", client="cupffee",
                            level="invalid")


# ---------------------------------------------------------------------------
# get_trend
# ---------------------------------------------------------------------------

class TestGetTrend:
    def test_twelve_element_series_for_full_year(
        self, cupffee_test_db: Path
    ) -> None:
        s = get_trend("Sales", client="cupffee",
                      start_date="2025-01-01", end_date="2025-12-01")
        assert isinstance(s, pd.Series)
        assert len(s) == 12

    def test_aggregates_across_subgroups_when_unspecified(
        self, cupffee_test_db: Path
    ) -> None:
        # All 'Sales' rows: 100 + 50 + 20 = 170 every month.
        s = get_trend("Sales", client="cupffee",
                      start_date="2025-01-01", end_date="2025-12-01")
        assert all(v == pytest.approx(170.0) for v in s)

    def test_filters_by_grp(self, cupffee_test_db: Path) -> None:
        s = get_trend("Sales", grp="Direct Sales", client="cupffee",
                      start_date="2025-01-01", end_date="2025-12-01")
        assert all(v == pytest.approx(20.0) for v in s)

    def test_filters_by_subgroup(self, cupffee_test_db: Path) -> None:
        s = get_trend("Sales", grp="Distributors", subgroup="220 ml",
                      client="cupffee",
                      start_date="2025-01-01", end_date="2025-12-01")
        assert all(v == pytest.approx(100.0) for v in s)


# ---------------------------------------------------------------------------
# ytd
# ---------------------------------------------------------------------------

class TestYtd:
    def test_full_year_matches_sum_of_get_trend(
        self, cupffee_test_db: Path
    ) -> None:
        total = ytd("Sales", 2025, client="cupffee")
        s = get_trend("Sales", client="cupffee",
                      start_date="2025-01-01", end_date="2025-12-01")
        assert total == pytest.approx(s.sum())
        # 170 * 12 = 2040
        assert total == pytest.approx(2040.0)

    def test_through_month_truncates(self, cupffee_test_db: Path) -> None:
        # Q1 only: 170 * 3 = 510
        total = ytd("Sales", 2025, through_month=3, client="cupffee")
        assert total == pytest.approx(510.0)


# ---------------------------------------------------------------------------
# get_line
# ---------------------------------------------------------------------------

class TestGetLine:
    def test_returns_long_dataframe(self, cupffee_test_db: Path) -> None:
        df = get_line("Sales", client="cupffee")
        assert isinstance(df, pd.DataFrame)
        assert {"period_date", "scenario", "data", "grp", "subgroup", "value"} \
            <= set(df.columns)

    def test_filters_by_data(self, cupffee_test_db: Path) -> None:
        df = get_line("Sales", client="cupffee")
        assert (df["data"] == "Sales").all()

    def test_periods_filter(self, cupffee_test_db: Path) -> None:
        df = get_line("Sales", client="cupffee",
                      periods=["2025-01-01", "2025-02-01"])
        assert set(df["period_date"].astype(str)) == {"2025-01-01", "2025-02-01"}


# ---------------------------------------------------------------------------
# to_csv
# ---------------------------------------------------------------------------

class TestToCsv:
    def test_writes_dataframe(self, cupffee_test_db: Path, tmp_path: Path) -> None:
        df = get_statement("IS", "2025-01-01", client="cupffee")
        out = tmp_path / "out.csv"
        to_csv(df, out)
        assert out.exists()
        loaded = pd.read_csv(out)
        assert len(loaded) == len(df)

    def test_writes_series(self, cupffee_test_db: Path, tmp_path: Path) -> None:
        s = get_aggregation("Sales", "2025-01-01", client="cupffee", level="grp")
        out = tmp_path / "out.csv"
        to_csv(s, out)
        assert out.exists()

    def test_writes_scalar(self, tmp_path: Path) -> None:
        out = tmp_path / "scalar.csv"
        to_csv(42.0, out)
        assert out.exists()


# ---------------------------------------------------------------------------
# Connection lifecycle
# ---------------------------------------------------------------------------

class TestConnectionLifecycle:
    def test_no_module_level_connection_state(
        self, cupffee_test_db: Path
    ) -> None:
        # Repeated calls should not leak open connections / file handles.
        for _ in range(5):
            v = get_value("Sales", "Distributors", "220 ml", "2025-01-01",
                          client="cupffee")
            assert v == 100.0


# ---------------------------------------------------------------------------
# Aggregate filtering
# ---------------------------------------------------------------------------

class TestAggregationExcludesAggregates:
    """get_aggregation must filter is_aggregate=1 rows so we don't
    double-count when the source's own derived rows are also stored."""

    HEADER = ["Data", "Group", "Subgroup", "Jan", "Feb", "Mar", "Apr", "May",
              "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    def test_excludes_registered_aggregate_at_data_level(
        self, make_test_client,
    ) -> None:
        tmp = make_test_client(
            name="demo",
            config={"entities": ["demo"], "financial_sources": [
                {"file": "raw/a.xlsx", "year": 2025, "entity": "demo"},
            ]},
            files={"a.xlsx": {"IS (Actual)": [
                self.HEADER,
                ["Sales", "g", "leaf_a", *([100.0] * 12)],
                ["Sales", "g", "leaf_b", *([50.0] * 12)],
                ["Sales", "g", "Total",  *([150.0] * 12)],
            ]}},
        )
        (tmp / "clients/demo/aggregate_formulas.yaml").write_text("""
total_sales:
  taxonomi: ["Sales", "g", "Total"]
  leaves:
    - {data: "Sales", grp: "g", subgroup: "leaf_a"}
    - {data: "Sales", grp: "g", subgroup: "leaf_b"}
""")
        from core.data.build import build_db
        build_db("demo", tmp)

        agg = get_aggregation("Sales", "2025-01-01", client="demo", level="data")
        assert agg.iloc[0] == 150.0  # 100 + 50, NOT 300

    def test_excludes_aggregate_at_grp_level(
        self, make_test_client,
    ) -> None:
        tmp = make_test_client(
            name="demo",
            config={"entities": ["demo"], "financial_sources": [
                {"file": "raw/a.xlsx", "year": 2025, "entity": "demo"},
            ]},
            files={"a.xlsx": {"IS (Actual)": [
                self.HEADER,
                ["Sales", "Distributors", "220",   *([100.0] * 12)],
                ["Sales", "Distributors", "Total", *([100.0] * 12)],  # aggregate
                ["Sales", "Direct",       "220",   *([20.0] * 12)],
            ]}},
        )
        (tmp / "clients/demo/aggregate_formulas.yaml").write_text("""
distrib_total:
  taxonomi: ["Sales", "Distributors", "Total"]
  leaves:
    - {data: "Sales", grp: "Distributors", subgroup: "220"}
""")
        from core.data.build import build_db
        build_db("demo", tmp)

        agg = get_aggregation("Sales", "2025-01-01", client="demo", level="grp")
        # Two groups, each summed from leaves only:
        assert agg.to_dict() == {"Distributors": 100.0, "Direct": 20.0}


# ---------------------------------------------------------------------------
# get_kpi / get_kpi_trend
# ---------------------------------------------------------------------------

@pytest.fixture
def kpi_test_db(tmp_path: Path, monkeypatch) -> Path:
    """Build a synthetic client DB with operational_kpis rows."""
    cdir = tmp_path / "clients" / "demo"
    (cdir / "data").mkdir(parents=True)
    (cdir / "config.yaml").write_text(yaml.safe_dump({"entities": ["e1"]}))
    db = cdir / "data" / "demo.db"
    schema.wipe_and_create(db)
    rows = [
        ("2026-01-01", "e1", "GMV", 100.0),
        ("2026-02-01", "e1", "GMV", 200.0),
        ("2026-03-01", "e1", "GMV", 300.0),
        ("2026-01-01", "e1", "Funded Amount", 90.0),
        ("2026-01-01", "e1", "% GMV Insured", 0.0),
        # Different entity (e2) — should be filtered out by entity arg.
        ("2026-01-01", "e2", "GMV", 999.0),
    ]
    with sqlite3.connect(db) as conn:
        conn.executemany(
            "INSERT INTO operational_kpis VALUES (?, ?, ?, ?)", rows,
        )
        conn.commit()
    monkeypatch.setattr(query_module, "_ROOT", tmp_path)
    return tmp_path


class TestGetKPI:
    def test_returns_value_for_known_kpi(self, kpi_test_db):
        assert get_kpi("GMV", "2026-01-01", client="demo", entity="e1") == 100.0
        assert get_kpi("GMV", "2026-03-01", client="demo", entity="e1") == 300.0

    def test_returns_none_for_missing_kpi(self, kpi_test_db):
        assert get_kpi("Nonexistent", "2026-01-01", client="demo", entity="e1") is None

    def test_returns_none_for_missing_period(self, kpi_test_db):
        assert get_kpi("GMV", "2026-12-01", client="demo", entity="e1") is None

    def test_zero_value_returns_zero_not_none(self, kpi_test_db):
        v = get_kpi("% GMV Insured", "2026-01-01", client="demo", entity="e1")
        assert v == 0.0

    def test_explicit_entity_filters(self, kpi_test_db):
        # e1 GMV at Jan = 100; e2 GMV at Jan = 999.
        assert get_kpi("GMV", "2026-01-01", client="demo", entity="e1") == 100.0
        assert get_kpi("GMV", "2026-01-01", client="demo", entity="e2") == 999.0


class TestGetKPITrend:
    def test_returns_full_series(self, kpi_test_db):
        s = get_kpi_trend("GMV", client="demo", entity="e1")
        assert isinstance(s, pd.Series)
        assert s.name == "GMV"
        assert s.index.tolist() == [
            dt.date(2026, 1, 1), dt.date(2026, 2, 1), dt.date(2026, 3, 1),
        ]
        assert s.tolist() == [100.0, 200.0, 300.0]

    def test_date_range_filters(self, kpi_test_db):
        s = get_kpi_trend("GMV",
                          start_date="2026-02-01", end_date="2026-02-28",
                          client="demo", entity="e1")
        assert len(s) == 1
        assert s.iloc[0] == 200.0

    def test_missing_kpi_returns_empty(self, kpi_test_db):
        s = get_kpi_trend("Nonexistent", client="demo", entity="e1")
        assert s.empty

