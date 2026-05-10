"""Tests for core.data.schema."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from core.data.schema import apply, wipe_and_create


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


def _table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {row[0] for row in rows}


def _index_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {row[0] for row in rows}


def _pk_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    """Return PK columns in declared order."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    pk_rows = sorted([r for r in rows if r[5] > 0], key=lambda r: r[5])
    return [r[1] for r in pk_rows]


def _column_info(conn: sqlite3.Connection, table: str) -> dict[str, dict]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {
        r[1]: {"type": r[2], "notnull": bool(r[3]), "default": r[4], "pk": r[5]}
        for r in rows
    }


class TestWipeAndCreate:
    def test_creates_file_if_missing(self, db_path: Path) -> None:
        assert not db_path.exists()
        wipe_and_create(db_path)
        assert db_path.exists()

    def test_creates_financials_table(self, db_path: Path) -> None:
        wipe_and_create(db_path)
        with sqlite3.connect(db_path) as conn:
            tables = _table_names(conn)
        assert "financials" in tables

    def test_overwrites_existing_db(self, db_path: Path) -> None:
        wipe_and_create(db_path)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO financials VALUES "
                "('2025-01-01','cupffee','actual','IS','Sales','x','y',1,100.0,0)"
            )
            conn.commit()
        wipe_and_create(db_path)
        with sqlite3.connect(db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM financials").fetchone()[0]
        assert count == 0

    def test_accepts_string_path(self, tmp_path: Path) -> None:
        wipe_and_create(str(tmp_path / "string.db"))
        assert (tmp_path / "string.db").exists()


class TestApplyIdempotent:
    def test_apply_twice_no_error(self, db_path: Path) -> None:
        apply(db_path)
        apply(db_path)
        with sqlite3.connect(db_path) as conn:
            assert "financials" in _table_names(conn)


class TestFinancialsTable:
    def test_pk_contains_entity_and_correct_order(self, db_path: Path) -> None:
        wipe_and_create(db_path)
        with sqlite3.connect(db_path) as conn:
            pk = _pk_columns(conn, "financials")
        assert pk == [
            "period_date",
            "entity",
            "scenario",
            "statement",
            "data",
            "grp",
            "subgroup",
        ]

    def test_has_display_order_not_null(self, db_path: Path) -> None:
        wipe_and_create(db_path)
        with sqlite3.connect(db_path) as conn:
            cols = _column_info(conn, "financials")
        assert "display_order" in cols
        assert cols["display_order"]["type"].upper() == "INTEGER"
        assert cols["display_order"]["notnull"] is True

    def test_value_is_real_and_nullable(self, db_path: Path) -> None:
        wipe_and_create(db_path)
        with sqlite3.connect(db_path) as conn:
            cols = _column_info(conn, "financials")
        assert cols["value"]["type"].upper() == "REAL"
        assert cols["value"]["notnull"] is False

    def test_scenario_check_rejects_unknown(self, db_path: Path) -> None:
        wipe_and_create(db_path)
        with sqlite3.connect(db_path) as conn, pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO financials VALUES "
                "('2025-01-01','cupffee','bogus','IS','Sales','x','y',1,100.0,0)"
            )

    def test_scenario_check_accepts_all_four(self, db_path: Path) -> None:
        wipe_and_create(db_path)
        with sqlite3.connect(db_path) as conn:
            for i, scen in enumerate(["actual", "pessimistic", "realistic", "optimistic"]):
                conn.execute(
                    "INSERT INTO financials VALUES "
                    f"('2025-01-01','cupffee','{scen}','IS','Sales','x','sg{i}',1,100.0,0)"
                )
            conn.commit()
            count = conn.execute("SELECT COUNT(*) FROM financials").fetchone()[0]
        assert count == 4

    def test_statement_check_rejects_unknown(self, db_path: Path) -> None:
        wipe_and_create(db_path)
        with sqlite3.connect(db_path) as conn, pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO financials VALUES "
                "('2025-01-01','cupffee','actual','PL','Sales','x','y',1,100.0,0)"
            )

    def test_statement_check_accepts_is_cf_bs(self, db_path: Path) -> None:
        wipe_and_create(db_path)
        with sqlite3.connect(db_path) as conn:
            for stmt in ["IS", "CF", "BS"]:
                conn.execute(
                    "INSERT INTO financials VALUES "
                    f"('2025-01-01','cupffee','actual','{stmt}','Line','x','y',1,100.0,0)"
                )
            conn.commit()

    def test_has_is_aggregate_column_not_null(self, db_path: Path) -> None:
        wipe_and_create(db_path)
        with sqlite3.connect(db_path) as conn:
            cols = _column_info(conn, "financials")
        assert "is_aggregate" in cols
        assert cols["is_aggregate"]["notnull"] is True

    def test_is_aggregate_defaults_to_false(self, db_path: Path) -> None:
        wipe_and_create(db_path)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO financials "
                "(period_date, entity, scenario, statement, data, grp, "
                " subgroup, display_order, value) "
                "VALUES ('2025-01-01','cupffee','actual','IS','Sales','g','x',1,100.0)"
            )
            conn.commit()
            row = conn.execute(
                "SELECT is_aggregate FROM financials"
            ).fetchone()
        assert row[0] == 0

    def test_is_aggregate_accepts_true_and_false(self, db_path: Path) -> None:
        wipe_and_create(db_path)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO financials VALUES "
                "('2025-01-01','cupffee','actual','IS','Sales','g','leaf',1,100.0,0)"
            )
            conn.execute(
                "INSERT INTO financials VALUES "
                "('2025-01-01','cupffee','actual','IS','Sales','g','aggr',2,100.0,1)"
            )
            conn.commit()
            rows = conn.execute(
                "SELECT subgroup, is_aggregate FROM financials "
                "ORDER BY subgroup"
            ).fetchall()
        assert rows == [("aggr", 1), ("leaf", 0)]

    def test_is_aggregate_not_in_pk(self, db_path: Path) -> None:
        # Adding is_aggregate must not change row identity: a leaf and an
        # aggregate cannot coexist for the same (period, entity, scenario,
        # statement, data, grp, subgroup).
        wipe_and_create(db_path)
        with sqlite3.connect(db_path) as conn:
            pk = _pk_columns(conn, "financials")
        assert "is_aggregate" not in pk


class TestIndexes:
    def test_required_indexes_exist(self, db_path: Path) -> None:
        wipe_and_create(db_path)
        with sqlite3.connect(db_path) as conn:
            idx = _index_names(conn)
        # The plan calls for indexes on period_date, scenario, data, entity.
        # We don't pin the exact names, only that one index covers each column.
        with sqlite3.connect(db_path) as conn:
            covered: set[str] = set()
            for name in idx:
                info = conn.execute(f"PRAGMA index_info({name})").fetchall()
                for col_row in info:
                    covered.add(col_row[2])
        assert {"period_date", "scenario", "data", "entity"} <= covered


class TestOperationalKpisTable:
    def test_table_created(self, db_path: Path) -> None:
        wipe_and_create(db_path)
        with sqlite3.connect(db_path) as conn:
            assert "operational_kpis" in _table_names(conn)

    def test_pk_columns(self, db_path: Path) -> None:
        wipe_and_create(db_path)
        with sqlite3.connect(db_path) as conn:
            pk = _pk_columns(conn, "operational_kpis")
        assert pk == ["period_date", "entity", "kpi"]

    def test_value_is_real_and_nullable(self, db_path: Path) -> None:
        wipe_and_create(db_path)
        with sqlite3.connect(db_path) as conn:
            cols = _column_info(conn, "operational_kpis")
        assert cols["value"]["type"].upper() == "REAL"
        assert cols["value"]["notnull"] is False

    def test_insert_and_query(self, db_path: Path) -> None:
        wipe_and_create(db_path)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO operational_kpis VALUES "
                "('2026-01-01', 'almacena', 'GMV', 17044518.98)"
            )
            conn.commit()
            row = conn.execute(
                "SELECT value FROM operational_kpis WHERE kpi='GMV'"
            ).fetchone()
        assert row[0] == pytest.approx(17044518.98)
