"""Build farada_5y_v1.xlsx from the WIP by wiring the Working-Capital drivers and
Cash-Flow sections of the ProForma (and downstream CF/BS in later phases).

Idempotent: always rebuilds the target from the WIP source, so re-running after a
code change reproduces the workbook exactly. Run from repo root:

    .venv/bin/python scripts/build_farada_5y.py

Plan: docs/superpowers/specs/2026-06-29-farada-5y-cashflow-wiring.md
"""
from __future__ import annotations

from pathlib import Path

import openpyxl
from openpyxl.utils import get_column_letter as gc

MODELING = Path("clients/farada/modeling")
SRC = MODELING / "FaradaIC - 5Y plan - WIP.xlsx"
DST = MODELING / "farada_5y_v1.xlsx"

PF = "ProForma"
INP = " Inputs"  # note leading space

# Month columns on ProForma: C(3) .. BJ(62) = 60 months.
C0, C1 = 3, 62


def col(c: int) -> str:
    return gc(c)


# ---------------------------------------------------------------------------
# Task 1 — set Payroll payable days to 14 (both scenario columns L & M).
# ---------------------------------------------------------------------------
def task1_payroll_days(wb) -> None:
    ws = wb[INP]
    for c in (12, 13):  # L, M
        ws.cell(188, c).value = 14
    # leave Receivable days (184) and Payable days (187) at 30.


def build() -> Path:
    wb = openpyxl.load_workbook(SRC, data_only=False)
    task1_payroll_days(wb)
    # Force Excel/LibreOffice to recompute on open (openpyxl writes no cached values).
    wb.calculation.fullCalcOnLoad = True
    wb.save(DST)
    return DST


if __name__ == "__main__":
    out = build()
    print(f"wrote {out}")
