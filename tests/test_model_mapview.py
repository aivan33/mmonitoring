"""Tests for core.model.mapview — the human-readable contract dump."""

from __future__ import annotations

from pathlib import Path

from core.model.contract import ModelContract, Rules, SheetInfo, TaxonomiAxis
from core.model.mapview import format_contract


def _contract():
    sheets = [
        SheetInfo("is_cons_taxonomi", "consolidated", "taxonomi", "IS"),
        SheetInfo("Consolidated Actuals", "consolidated", "actuals", None),
        SheetInfo(" Inputs", None, "engine", None),
        SheetInfo("KPIs", None, "driver", None),
    ]
    rules = Rules(
        entity_patterns={"consolidated": ["cons"]},
        taxonomi_axis=TaxonomiAxis(header_row=1, first_month_col="D", months=12, year=2026),
    )
    return ModelContract(sheets, rules, Path("x.xlsx"))


def test_format_lists_entities_and_seams():
    out = format_contract(_contract())
    assert "consolidated" in out
    assert "is_cons_taxonomi" in out          # budget side
    assert "Consolidated Actuals" in out      # actuals side


def test_format_shows_shared_engine_and_drivers():
    out = format_contract(_contract())
    assert "Inputs" in out
    assert "KPIs" in out


def test_format_shows_month_axis():
    out = format_contract(_contract())
    assert "2026-01" in out and "2026-12" in out
