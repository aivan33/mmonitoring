"""Tests for the monthly Almacena loans-DB update tool.

The tool reads a month's lender loan ledger, keeps the loans outstanding at
month-end, and maps them to the model's `Loans Database` column schema (lender
abbreviations kept as-is) — a paste-ready snapshot for updating the model.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MOD = ROOT / "clients/almacena/one_offs/build_loans_db_update.py"
APRIL = ROOT / "clients/almacena/raw/04/lender_loans_accrued_interest.xlsx"


@pytest.fixture
def mod():
    spec = importlib.util.spec_from_file_location("build_loans_db_update", MOD)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _rec(lender, start, rep, principal, rate, interest):
    return {
        "lender": lender, "start": start, "repayment": rep,
        "principal": principal, "rate": rate, "total_interest": interest,
    }


def test_keeps_only_loans_outstanding_at_asof(mod):
    recs = [
        _rec("X", dt.datetime(2025, 1, 1), dt.datetime(2026, 3, 1), 100, 0.09, 10),  # matured
        _rec("Y", dt.datetime(2026, 1, 1), dt.datetime(2026, 8, 1), 200, 0.09, 20),  # active
    ]
    rows = mod.to_model_rows(recs, asof=dt.datetime(2026, 4, 30))
    assert [r["Lender Name"] for r in rows] == ["Y"]


def test_excludes_loans_not_yet_drawn_at_asof(mod):
    # a loan that STARTS after month-end is a future draw, not outstanding yet
    recs = [
        _rec("now", dt.datetime(2026, 2, 1), dt.datetime(2026, 9, 1), 100, 0.09, 5),   # live
        _rec("future", dt.datetime(2026, 5, 19), dt.datetime(2026, 8, 1), 200, 0.09, 9),  # starts after Apr-30
    ]
    rows = mod.to_model_rows(recs, asof=dt.datetime(2026, 4, 30))
    assert [r["Lender Name"] for r in rows] == ["now"]


def test_maps_to_model_columns(mod):
    recs = [_rec("JSKR", dt.datetime(2026, 1, 23), dt.datetime(2026, 5, 25), 2_000_000, 0.09, 75_000)]
    r = mod.to_model_rows(recs, asof=dt.datetime(2026, 4, 30))[0]
    assert r["Loan ID"] == "LN-001"
    assert r["Lender Name"] == "JSKR"           # abbreviation kept
    assert r["Principal Amount (EUR)"] == 2_000_000
    assert r["r (% p.a)"] == 0.09
    assert r["Repayment Amount"] == 2_075_000   # principal + total interest
    assert r["Active (T/F)"] == 1


def test_ids_are_sequential(mod):
    recs = [
        _rec("A", dt.datetime(2026, 1, 1), dt.datetime(2026, 9, 1), 500, 0.09, 5),
        _rec("B", dt.datetime(2026, 1, 1), dt.datetime(2026, 9, 1), 300, 0.09, 3),
    ]
    rows = mod.to_model_rows(recs, asof=dt.datetime(2026, 4, 30))
    assert [r["Loan ID"] for r in rows] == ["LN-001", "LN-002"]


@pytest.mark.skipif(not APRIL.exists(), reason="gitignored client data absent")
def test_april_book_reconciles(mod):
    rows = mod.to_model_rows(mod.read_ledger(APRIL), asof=dt.datetime(2026, 4, 30))
    total = sum(r["Principal Amount (EUR)"] for r in rows)
    blended = sum(r["Principal Amount (EUR)"] * r["r (% p.a)"] for r in rows) / total
    assert len(rows) == 21          # outstanding at 30-Apr (excludes 4 future-dated draws)
    assert abs(total - 15_447_201) < 1
    assert abs(blended - 0.0909) < 0.0005
