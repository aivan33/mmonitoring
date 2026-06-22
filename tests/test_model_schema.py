"""Tests for core.schema — the financial model as a normalized SQLite schema.

The schema captures a model's STRUCTURE (sections/groups/inputs/lines) + the dependency graph
(line_dependency edges = lineage); values stay in Excel. These tests build the schema in an
in-memory SQLite DB and prove (a) it creates cleanly with FK + CHECK constraints, and (b) the
recursive-CTE lineage trace walks a statement line back to its driver-leaf inputs.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from core.schema import create_db, trace_input_leaves
from core.schema.load import load_model

FARADA = Path("clients/farada/modeling/farada_model_v4.5.xlsx")

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


@pytest.mark.skipif(not FARADA.exists(), reason="Farada model is gitignored / absent")
def test_load_farada_structure_and_lineage():
    conn = load_model(":memory:", str(FARADA), "Farada", "Farada 5Y v4.5", horizon=60)
    c = lambda t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    # all three pillars represented
    pillars = {p for (p,) in conn.execute("SELECT DISTINCT pillar FROM section")}
    assert pillars == {"input", "proforma", "statement"}
    # structural sanity
    assert c("input") > 50 and c("input_value") == c("input")
    assert c("line") > 100 and c("line_formula") > 50 and c("line_dependency") > 100
    # lineage: the IS Revenue line resolves back to input leaves through the ProForma
    row = conn.execute(
        "SELECT l.line_id FROM line l JOIN section s ON l.section_id = s.section_id "
        "WHERE s.title = 'IS' AND l.label = 'Revenue'"
    ).fetchone()
    assert row is not None
    assert len(trace_input_leaves(conn, row[0])) > 0


def test_model_logic_md_renders_from_synthetic():
    from core.schema.report import model_logic_md
    conn = create_db(":memory:")
    _seed(conn)
    md = model_logic_md(conn)
    for header in ("# Acme 5Y", "## Structure", "## Pillar 1", "## Model health"):
        assert header in md
    # the seed's statement line "Revenue" traces to its input
    assert "Revenue" in md


@pytest.mark.skipif(not FARADA.exists(), reason="Farada model is gitignored / absent")
def test_farada_report_has_lineage():
    from core.schema.report import model_logic_md
    conn = load_model(":memory:", str(FARADA), "Farada", "Farada 5Y v4.5", horizon=60)
    md = model_logic_md(conn)
    assert "← " in md and "driver inputs" in md   # lineage resolved for the standardized layout


@pytest.mark.skipif(not FARADA.exists(), reason="Farada model is gitignored / absent")
def test_validation_flags_known_issues():
    from core.schema import validate
    conn = load_model(":memory:", str(FARADA), "Farada", "v4.5", horizon=60)
    v = validate(conn)
    # orphaned assumptions exist (e.g. the unused Line-3 usage-pricing ladder)
    assert any("meas" in lbl for _, lbl, _ in v["orphan_inputs"])
    # dead proforma display rows (blended ASP) surface as orphan lines
    assert v["orphan_lines"]
    # the capacity #REF! was repaired by the overhaul — no broken formulas remain
    assert not v["broken_formulas"]
