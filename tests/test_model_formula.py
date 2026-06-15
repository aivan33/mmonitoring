"""Tests for core.model.formula — parse a formula into its referenced cells.

The parser turns a formula string into the cell/range references it depends on
(its precedents), cross-sheet aware. Dynamic functions (OFFSET/INDEX/INDIRECT)
are *flagged* — their literal operand refs are kept, never silently dropped,
because the cell they ultimately resolve to depends on runtime values.
"""

from __future__ import annotations

from core.model.formula import Ref, parse_refs


def test_local_cell_refs_use_the_current_sheet():
    result = parse_refs("=C6+C7+C8", sheet="ProForma")
    assert result.refs == [
        Ref("ProForma", "C6"),
        Ref("ProForma", "C7"),
        Ref("ProForma", "C8"),
    ]


def test_cross_sheet_ref():
    result = parse_refs("=Actuals!J60", sheet="ProForma")
    assert result.refs == [Ref("Actuals", "J60")]


def test_quoted_sheet_name():
    result = parse_refs("='BG Actuals'!I8", sheet="ProForma")
    assert result.refs == [Ref("BG Actuals", "I8")]


def test_absolute_markers_are_stripped():
    result = parse_refs("=$D$2", sheet="ProForma")
    assert result.refs == [Ref("ProForma", "D2")]


def test_ranges_are_kept_as_range_refs():
    result = parse_refs("=SUMPRODUCT(A1:A3,B1:B3)", sheet="X")
    assert result.refs == [Ref("X", "A1", "A3"), Ref("X", "B1", "B3")]
    assert result.refs[0].is_range is True


def test_range_expands_to_cells():
    (a_range,) = parse_refs("=SUM(A1:A3)", sheet="X").refs
    assert list(a_range.cells()) == [("X", "A1"), ("X", "A2"), ("X", "A3")]


def test_duplicate_refs_are_deduped_in_order():
    assert parse_refs("=A1+A1", sheet="X").refs == [Ref("X", "A1")]


def test_offset_is_flagged_but_operand_refs_kept():
    result = parse_refs("=OFFSET(K9,0,$D$2)", sheet="X")
    assert Ref("X", "K9") in result.refs
    assert Ref("X", "D2") in result.refs
    assert "OFFSET" in result.dynamic


def test_indirect_is_flagged():
    result = parse_refs('=INDIRECT("A"&B1)', sheet="X")
    assert "INDIRECT" in result.dynamic
    assert Ref("X", "B1") in result.refs


def test_literal_only_formula_has_no_refs():
    assert parse_refs("=1+2*3", sheet="X").refs == []


def test_non_coordinate_operand_is_flagged_unresolved_not_dropped():
    result = parse_refs("=MyName*2", sheet="X")
    assert "MyName" in result.unresolved
    assert result.refs == []
