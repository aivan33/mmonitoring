"""Tests for core.model.flow — the dependency graph + tracing.

trace_precedents walks a formula cell back to its driver *leaves* (cells with no
formula — the literal inputs); trace_dependents walks the reverse (every cell a
driver feeds). This is the mechanic behind variance->driver tracing.
"""

from __future__ import annotations

import pytest
from openpyxl import Workbook

from core.model.cells import read_cells
from core.model.flow import build_flow


@pytest.fixture
def flow(tmp_path):
    wb = Workbook()
    pf = wb.active
    pf.title = "PF"
    pf["C1"] = 10               # leaf (driver input)
    pf["C2"] = 5                # leaf (driver input)
    pf["C3"] = "=C1+C2"        # intermediate
    pf["C4"] = "=C3*2"         # output
    pf["C5"] = "=Drivers!A1"   # cross-sheet output
    pf["C6"] = "=C7"           # cycle
    pf["C7"] = "=C6"           # cycle
    pf["C8"] = "=SUM(C1:C2)"   # range output
    pf["C9"] = "=OFFSET(C1,0,0)"  # dynamic
    dr = wb.create_sheet("Drivers")
    dr["A1"] = 7                # leaf
    path = tmp_path / "m.xlsx"
    wb.save(path)
    return build_flow(read_cells(path))


def test_trace_precedents_reaches_driver_leaves(flow):
    result = flow.trace_precedents("PF", "C4")
    assert result.leaves == {("PF", "C1"), ("PF", "C2")}


def test_trace_precedents_follows_cross_sheet_refs(flow):
    result = flow.trace_precedents("PF", "C5")
    assert result.leaves == {("Drivers", "A1")}


def test_trace_precedents_expands_ranges(flow):
    result = flow.trace_precedents("PF", "C8")
    assert result.leaves == {("PF", "C1"), ("PF", "C2")}


def test_trace_precedents_terminates_on_cycles(flow):
    result = flow.trace_precedents("PF", "C6")  # C6<->C7, no leaves
    assert result.leaves == set()


def test_dynamic_function_is_recorded_on_the_trace(flow):
    result = flow.trace_precedents("PF", "C9")
    assert ("PF", "C9") in result.dynamic
    assert result.leaves == {("PF", "C1")}  # anchor still captured


def test_trace_dependents_is_transitive(flow):
    # C1 feeds C3(=C1+C2)->C4(=C3*2), C8(=SUM(C1:C2)), and C9(=OFFSET(C1,...)) anchor.
    assert flow.trace_dependents("PF", "C1") == {
        ("PF", "C3"),
        ("PF", "C4"),
        ("PF", "C8"),
        ("PF", "C9"),
    }


def test_trace_dependents_crosses_sheets(flow):
    assert flow.trace_dependents("Drivers", "A1") == {("PF", "C5")}


def test_precedents_of_a_leaf_is_empty(flow):
    assert flow.precedents("PF", "C1") == []
