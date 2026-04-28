"""Tests for core.loaders.financials.load_taxonomy_xlsx.

Synthetic xlsx fixtures are built per-test via openpyxl so each test stays
self-contained (DAMP) and we don't need binary fixture files in the repo.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Iterable

import pytest
from openpyxl import Workbook

from core.loaders.financials import FinancialRow, load_taxonomy_xlsx


HEADER = ["Data", "Group", "Subgroup", "Jan", "Feb", "Mar", "Apr", "May",
          "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _write_xlsx(path: Path, sheets: dict[str, list[list]]) -> Path:
    """Build an xlsx with the given sheet name -> rows mapping. Each rows
    list should include the header row. Empty list = sheet with no rows."""
    wb = Workbook()
    # Remove the default sheet
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(title=name)
        for row in rows:
            ws.append(row)
    wb.save(path)
    return path


def _sales_row(grp: str, sg: str, *months: float | None) -> list:
    """Build a Sales row with Group/Subgroup and 12 monthly values."""
    if len(months) != 12:
        raise ValueError("expected 12 monthly values")
    return ["Sales", grp, sg, *months]


# ---------------------------------------------------------------------------
# Sheet-name parsing
# ---------------------------------------------------------------------------

class TestSheetNameParsing:
    def test_simple_statement_scenario(self, tmp_path: Path) -> None:
        path = _write_xlsx(tmp_path / "f.xlsx", {
            "IS (Actual)": [HEADER, _sales_row("Distributors", "220 ml", *([100.0] + [None] * 11))],
        })
        rows = list(load_taxonomy_xlsx(path, year=2025, entity="cupffee"))
        assert all(r.statement == "IS" for r in rows)
        assert all(r.scenario == "actual" for r in rows)

    def test_indirect_in_name(self, tmp_path: Path) -> None:
        path = _write_xlsx(tmp_path / "f.xlsx", {
            "CF Indirect (Realistic)": [
                HEADER,
                ["Cash Flow from Operating Activities", "Cash from Sales", "Cash from Sales",
                 *([1000.0] + [None] * 11)],
            ],
        })
        rows = list(load_taxonomy_xlsx(path, year=2025, entity="cupffee"))
        assert all(r.statement == "CF" and r.scenario == "realistic" for r in rows)

    def test_scenario_lowercased(self, tmp_path: Path) -> None:
        path = _write_xlsx(tmp_path / "f.xlsx", {
            "BS (Pessimistic)": [HEADER, _sales_row("g", "sg", *([1.0] + [None] * 11))],
        })
        rows = list(load_taxonomy_xlsx(path, year=2025, entity="cupffee"))
        assert all(r.scenario == "pessimistic" for r in rows)

    def test_unknown_scenario_raises(self, tmp_path: Path) -> None:
        path = _write_xlsx(tmp_path / "f.xlsx", {
            "IS (Bogus)": [HEADER, _sales_row("g", "sg", *([1.0] + [None] * 11))],
        })
        with pytest.raises(ValueError, match=r"IS \(Bogus\)|bogus"):
            list(load_taxonomy_xlsx(path, year=2025, entity="cupffee"))

    def test_whitespace_in_sheet_name_tolerated(self, tmp_path: Path) -> None:
        path = _write_xlsx(tmp_path / "f.xlsx", {
            "IS  (Realistic)": [HEADER, _sales_row("g", "sg", *([1.0] + [None] * 11))],
        })
        rows = list(load_taxonomy_xlsx(path, year=2025, entity="cupffee"))
        assert all(r.statement == "IS" and r.scenario == "realistic" for r in rows)


# ---------------------------------------------------------------------------
# Empty sheet / empty row handling
# ---------------------------------------------------------------------------

class TestEmpty:
    def test_empty_sheet_skipped(self, tmp_path: Path) -> None:
        # The 'CF (Actual)' empty-by-convention sheet
        path = _write_xlsx(tmp_path / "f.xlsx", {
            "CF (Actual)": [HEADER],  # only header, no data rows
            "IS (Actual)": [HEADER, _sales_row("d", "sg", *([10.0] + [None] * 11))],
        })
        rows = list(load_taxonomy_xlsx(path, year=2025, entity="cupffee"))
        # Only the IS sheet should produce rows
        assert {r.statement for r in rows} == {"IS"}
        assert len(rows) == 1

    def test_sheet_with_only_null_rows_skipped(self, tmp_path: Path) -> None:
        # Header + a row of all-Nones (e.g., placeholder where no data was filled in)
        path = _write_xlsx(tmp_path / "f.xlsx", {
            "CF (Actual)": [
                HEADER,
                ["data", "g", "sg", *([None] * 12)],
            ],
            "IS (Actual)": [HEADER, _sales_row("d", "sg", *([10.0] + [None] * 11))],
        })
        rows = list(load_taxonomy_xlsx(path, year=2025, entity="cupffee"))
        assert {r.statement for r in rows} == {"IS"}

    def test_individual_all_null_row_skipped(self, tmp_path: Path) -> None:
        path = _write_xlsx(tmp_path / "f.xlsx", {
            "IS (Actual)": [
                HEADER,
                _sales_row("Distributors", "Cupffee 220 ml", *([100.0] + [None] * 11)),
                ["Sales", "Distributors", "Cupffee 110 ml", *([None] * 12)],   # skipped
                _sales_row("Direct Sales", "Cupffee 220 ml", *([200.0] + [None] * 11)),
            ],
        })
        rows = list(load_taxonomy_xlsx(path, year=2025, entity="cupffee"))
        subgroups = [r.subgroup for r in rows]
        assert "Cupffee 110 ml" not in subgroups
        assert sorted(subgroups) == ["Cupffee 220 ml", "Cupffee 220 ml"]


# ---------------------------------------------------------------------------
# Cell-level NULL handling
# ---------------------------------------------------------------------------

class TestNullCellHandling:
    def test_default_skips_null_cells(self, tmp_path: Path) -> None:
        # Q1-only fill, rest null. Default emit_null_cells=False → 3 rows.
        path = _write_xlsx(tmp_path / "f.xlsx", {
            "IS (Actual)": [
                HEADER,
                _sales_row("d", "sg", 100.0, 200.0, 300.0,
                           None, None, None, None, None, None, None, None, None),
            ],
        })
        rows = list(load_taxonomy_xlsx(path, year=2026, entity="cupffee"))
        assert len(rows) == 3
        assert {r.period_date for r in rows} == {
            dt.date(2026, 1, 1), dt.date(2026, 2, 1), dt.date(2026, 3, 1)
        }
        assert all(r.value is not None for r in rows)

    def test_emit_null_cells_true_emits_all_twelve(self, tmp_path: Path) -> None:
        path = _write_xlsx(tmp_path / "f.xlsx", {
            "IS (Actual)": [
                HEADER,
                _sales_row("d", "sg", 100.0, 200.0, 300.0,
                           None, None, None, None, None, None, None, None, None),
            ],
        })
        rows = list(load_taxonomy_xlsx(path, year=2026, entity="cupffee", emit_null_cells=True))
        assert len(rows) == 12
        nulls = [r for r in rows if r.value is None]
        assert len(nulls) == 9

    def test_zero_is_not_treated_as_null(self, tmp_path: Path) -> None:
        # A real 0.0 value should be emitted, not skipped.
        path = _write_xlsx(tmp_path / "f.xlsx", {
            "IS (Actual)": [
                HEADER,
                _sales_row("d", "sg", 0.0, 5.0, *([None] * 10)),
            ],
        })
        rows = list(load_taxonomy_xlsx(path, year=2026, entity="cupffee"))
        # Both Jan (0.0) and Feb (5.0) should be emitted.
        values_by_month = {r.period_date.month: r.value for r in rows}
        assert values_by_month == {1: 0.0, 2: 5.0}


# ---------------------------------------------------------------------------
# FX conversion
# ---------------------------------------------------------------------------

class TestFXConversion:
    def test_eur_passthrough(self, tmp_path: Path) -> None:
        path = _write_xlsx(tmp_path / "f.xlsx", {
            "IS (Actual)": [HEADER, _sales_row("d", "sg", 1.95583, *([None] * 11))],
        })
        rows = list(load_taxonomy_xlsx(path, year=2025, entity="cupffee", currency="EUR"))
        assert rows[0].value == pytest.approx(1.95583)

    def test_bgn_divides_by_rate(self, tmp_path: Path) -> None:
        path = _write_xlsx(tmp_path / "f.xlsx", {
            "IS (Actual)": [HEADER, _sales_row("d", "sg", 1.95583, *([None] * 11))],
        })
        rows = list(load_taxonomy_xlsx(
            path, year=2025, entity="cupffee", currency="BGN", fx_rate=1.95583,
        ))
        # 1.95583 BGN / 1.95583 = 1.0 EUR
        assert rows[0].value == pytest.approx(1.0)

    def test_non_eur_without_fx_rate_raises(self, tmp_path: Path) -> None:
        path = _write_xlsx(tmp_path / "f.xlsx", {
            "IS (Actual)": [HEADER, _sales_row("d", "sg", 100.0, *([None] * 11))],
        })
        with pytest.raises(ValueError, match="fx_rate"):
            list(load_taxonomy_xlsx(path, year=2025, entity="cupffee", currency="USD"))

    def test_usd_uses_same_fx_rate_param(self, tmp_path: Path) -> None:
        # Generic fx_rate covers BGN, USD, etc.
        path = _write_xlsx(tmp_path / "f.xlsx", {
            "IS (Actual)": [HEADER, _sales_row("d", "sg", 100.0, *([None] * 11))],
        })
        rows = list(load_taxonomy_xlsx(
            path, year=2025, entity="cupffee", currency="USD", fx_rate=1.10,
        ))
        # 100 USD / 1.10 = ~90.91 EUR
        assert rows[0].value == pytest.approx(100.0 / 1.10)

    def test_null_cell_not_divided(self, tmp_path: Path) -> None:
        # NULL stays NULL; FX division must not crash.
        path = _write_xlsx(tmp_path / "f.xlsx", {
            "IS (Actual)": [HEADER, _sales_row("d", "sg", 100.0, *([None] * 11))],
        })
        rows = list(load_taxonomy_xlsx(
            path, year=2025, entity="cupffee", currency="BGN", fx_rate=1.95583,
            emit_null_cells=True,
        ))
        nulls = [r for r in rows if r.value is None]
        assert len(nulls) == 11


# ---------------------------------------------------------------------------
# display_order, period_date, whitespace
# ---------------------------------------------------------------------------

class TestRowMetadata:
    def test_display_order_per_sheet(self, tmp_path: Path) -> None:
        # Two rows in IS, one in BS. Display order resets per sheet.
        path = _write_xlsx(tmp_path / "f.xlsx", {
            "IS (Actual)": [
                HEADER,
                _sales_row("Distributors", "220 ml", 100.0, *([None] * 11)),
                _sales_row("Distributors", "110 ml", 50.0, *([None] * 11)),
            ],
            "BS (Actual)": [
                HEADER,
                ["Cash and cash equivalents", "Cash and cash equivalents",
                 "Cash and cash equivalents", *([1000.0] + [None] * 11)],
            ],
        })
        rows = list(load_taxonomy_xlsx(path, year=2025, entity="cupffee"))
        is_rows = sorted([r for r in rows if r.statement == "IS"], key=lambda r: r.display_order)
        bs_rows = sorted([r for r in rows if r.statement == "BS"], key=lambda r: r.display_order)
        # Sheet-local order — 220 ml first, 110 ml second, both with the same
        # display_order across all 12 months for that row, but distinct between rows.
        assert is_rows[0].subgroup == "220 ml"
        assert is_rows[1].subgroup == "110 ml"
        assert is_rows[0].display_order < is_rows[1].display_order
        # BS resets — its first row should not have a display_order > IS rows.
        assert bs_rows[0].display_order <= is_rows[0].display_order

    def test_period_date_first_of_month(self, tmp_path: Path) -> None:
        path = _write_xlsx(tmp_path / "f.xlsx", {
            "IS (Actual)": [
                HEADER,
                _sales_row("d", "sg", *([10.0] * 12)),
            ],
        })
        rows = list(load_taxonomy_xlsx(path, year=2025, entity="cupffee"))
        assert all(r.period_date.day == 1 for r in rows)
        assert {r.period_date.month for r in rows} == set(range(1, 13))
        assert all(r.period_date.year == 2025 for r in rows)

    def test_whitespace_stripped(self, tmp_path: Path) -> None:
        path = _write_xlsx(tmp_path / "f.xlsx", {
            "IS (Actual)": [
                HEADER,
                ["  Sales  ", "Distributors\t", " 220 ml ", *([10.0] + [None] * 11)],
            ],
        })
        rows = list(load_taxonomy_xlsx(path, year=2025, entity="cupffee"))
        assert rows[0].data == "Sales"
        assert rows[0].grp == "Distributors"
        assert rows[0].subgroup == "220 ml"

    def test_entity_propagated(self, tmp_path: Path) -> None:
        path = _write_xlsx(tmp_path / "f.xlsx", {
            "IS (Actual)": [HEADER, _sales_row("d", "sg", 1.0, *([None] * 11))],
        })
        rows = list(load_taxonomy_xlsx(path, year=2025, entity="ap_foundation"))
        assert all(r.entity == "ap_foundation" for r in rows)


# ---------------------------------------------------------------------------
# FinancialRow shape & idempotence
# ---------------------------------------------------------------------------

class TestRowShape:
    def test_financialrow_fields_match_db_columns(self) -> None:
        # The NamedTuple's fields must map cleanly to a financials INSERT.
        assert FinancialRow._fields == (
            "period_date", "entity", "scenario", "statement",
            "data", "grp", "subgroup", "display_order", "value",
        )

    def test_iteration_idempotent(self, tmp_path: Path) -> None:
        path = _write_xlsx(tmp_path / "f.xlsx", {
            "IS (Actual)": [
                HEADER,
                _sales_row("Distributors", "220 ml", *([100.0] * 12)),
                _sales_row("Distributors", "110 ml", *([50.0] * 12)),
            ],
        })
        kw = dict(year=2025, entity="cupffee")
        a = list(load_taxonomy_xlsx(path, **kw))
        b = list(load_taxonomy_xlsx(path, **kw))
        assert a == b
