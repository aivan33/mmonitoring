"""End-to-end gate test: a real LibreOffice recalc + integrity checks on a tiny
in-memory 3-statement model. Skipped when LibreOffice is unavailable.
"""

from __future__ import annotations

import openpyxl
import pytest

from core.model.integrity import run_all
from core.model.recalc import recalc, soffice_available

pytestmark = pytest.mark.skipif(
    not soffice_available(), reason="LibreOffice not installed")


# Gate targets for the mini model (2 month columns: C, D).
GATES = {
    "error_scan": {"sheets": "all"},
    "balance_checks": [
        {"name": "BS check", "sheet": "BS", "row": 5,
         "cols": {"start": 3, "end": 4}}],
    "ties": [
        {"name": "CF ending == BS cash", "a": {"sheet": "CF", "row": 24},
         "b": {"sheet": "BS", "row": 10}, "cols": {"start": 3, "end": 4}}],
    "subtotals": [
        {"name": "CFF", "sheet": "CF", "parent": 20, "children": [15, 16],
         "cols": {"start": 3, "end": 4}}],
}


def _build(tmp_path, mutate=None):
    """A balanced mini model wired with real formulas (so recalc has work to do)."""
    wb = openpyxl.Workbook()
    bs = wb.active
    bs.title = "BS"
    cf = wb.create_sheet("CF")
    for c in ("C", "D"):
        bs[f"{c}3"] = 100          # assets
        bs[f"{c}4"] = 100          # equity + liabilities
        bs[f"{c}5"] = f"={c}3-{c}4"  # check = 0
        bs[f"{c}10"] = 500         # cash
        cf[f"{c}15"] = 300
        cf[f"{c}16"] = 200
        cf[f"{c}20"] = f"={c}15+{c}16"  # CFF = children
        cf[f"{c}24"] = 500              # ending cash == BS cash
    if mutate:
        mutate(wb)
    wb.calculation.fullCalcOnLoad = True
    path = tmp_path / "mini.xlsx"
    wb.save(path)
    return path


def test_gate_passes_balanced_model(tmp_path) -> None:
    assert run_all(recalc(_build(tmp_path)), GATES) == []


def test_gate_fails_unbalanced_bs(tmp_path) -> None:
    path = _build(tmp_path, mutate=lambda wb: wb["BS"].__setitem__("D4", 250))
    v = run_all(recalc(path), GATES)
    assert any(x.check == "bs_balance" for x in v)


def test_gate_fails_on_error_cell(tmp_path) -> None:
    path = _build(tmp_path, mutate=lambda wb: wb["CF"].__setitem__("C24", "=1/0"))
    v = run_all(recalc(path), GATES)
    assert any(x.check == "error_cell" for x in v)
