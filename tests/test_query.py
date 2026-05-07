"""Tests for core.data.query — the public surface that Stage 2 will import."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
import pytest

from core.data.query import (
    get_aggregation, get_line, get_statement, get_trend,
    get_value, to_csv, ytd,
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
