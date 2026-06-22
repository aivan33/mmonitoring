"""Tests for core.schema — the financial model as a normalized SQLite schema.

The schema captures a model's STRUCTURE (sections/groups/inputs/lines) + the dependency graph
(line_dependency edges = lineage); values stay in Excel. These tests build the schema in an
in-memory SQLite DB and prove (a) it creates cleanly with FK + CHECK constraints, and (b) the
recursive-CTE lineage trace walks a statement line back to its driver-leaf inputs.
"""
from __future__ import annotations

import sqlite3

import pytest

from core.schema import create_db, trace_input_leaves

EXPECTED_TABLES = {
    "client", "model", "scenario", "period", "section", "grp",
    "input", "input_value", "line", "line_formula", "line_dependency",
    "line_value", "kpi",
}


def _seed(conn):
    """A tiny synthetic model: 1 input → a driver line → a statement line."""
    conn.executescript(
        """
        INSERT INTO client VALUES (1, 'Acme');
        INSERT INTO model  VALUES (1, 1, 'Acme 5Y', 'EUR', '2026-07-01', 60);
        INSERT INTO scenario VALUES (1, 1, 'Realistic', 1);
        INSERT INTO section VALUES (1, 1, 'input', 'II', 'REVENUE ASSUMPTIONS', 2),
                                   (2, 1, 'proforma', 'REV', 'Revenue', 2),
                                   (3, 1, 'statement', 'IS', 'Income Statement', 1);
        INSERT INTO grp VALUES (1, 1, '2.1', 'Pricing', 1);
        INSERT INTO input VALUES (1, 1, 'Price @ 1 pc', 'EUR/sensor', 'eur', 1, NULL, NULL, NULL, 1, " Inputs!L16");
        INSERT INTO input_value VALUES (1, 1, 125.0);
        INSERT INTO line VALUES (10, 2, 'Revenue', 'driver', 'EUR', 1, 'ProForma!4'),
                                (20, 3, 'Revenue', 'leaf',   'EUR', 1, 'IS!4');
        INSERT INTO line_formula VALUES (10, '=units*price'), (20, '=ProForma!C4');
        -- statement line 20 depends on proforma line 10; line 10 depends on input 1
        INSERT INTO line_dependency VALUES (20, 'line', 10), (10, 'input', 1);
        """
    )


def test_schema_creates_with_all_tables():
    conn = create_db(":memory:")
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert EXPECTED_TABLES <= names


def test_foreign_keys_and_checks_enforced():
    conn = create_db(":memory:")
    conn.execute("INSERT INTO client VALUES (1, 'Acme')")
    # FK violation: model.client_id -> missing client 99
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO model VALUES (1, 99, 'x', 'EUR', '2026-07-01', 60)")
    conn.execute("INSERT INTO model VALUES (1, 1, 'x', 'EUR', '2026-07-01', 60)")
    # CHECK violation: section.pillar must be input|proforma|statement
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO section VALUES (1, 1, 'bogus', 'X', 'X', 1)")


def test_lineage_trace_walks_statement_line_to_input_leaves():
    conn = create_db(":memory:")
    _seed(conn)
    # tracing the statement line (20) should reach input 1 through proforma line 10
    leaves = trace_input_leaves(conn, 20)
    assert leaves == {1}
    # the driver line (10) traces to the same input directly
    assert trace_input_leaves(conn, 10) == {1}
