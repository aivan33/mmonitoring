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


# Inputs driver scalars (resolved via OFFSET on the Inputs sheet).
DSO = f"' Inputs'!$J$184/30"
DPO = f"' Inputs'!$J$187/30"
PAYDAYS = f"' Inputs'!$J$188/30"

# Arrears-billed revenue/recognised row -> cash-in row (ProForma). Each cash line
# lags its RECOGNISED revenue by DSO. Subscription (202-204) is billed annually in
# advance => Task 4b. Overage is lagged at the subtotal off the recognised total
# (row 64), whose own formula already handles the ramp delay (Inputs J78).
CASHIN_MAP = {
    188: 47, 189: 48, 190: 49,        # Components #1
    192: 51, 193: 52, 194: 53,        # Components #2
    198: 57, 199: 58, 200: 59,        # SaaS #3 — Hardware (device, billed in arrears)
    205: 64,                          # SaaS #3 — Overage (recognised total, lagged)
}


def _lag(ws, cash_row: int, src_row: int, ratio: str) -> None:
    """cash[m] = accrual[m] - ratio*(accrual[m] - accrual[m-1]); month-1 prior = 0."""
    for c in range(C0, C1 + 1):
        cur = f"{col(c)}{src_row}"
        if c == C0:
            f = f"={cur}-{ratio}*{cur}"
        else:
            prev = f"{col(c - 1)}{src_row}"
            f = f"={cur}-{ratio}*({cur}-{prev})"
        ws.cell(cash_row, c).value = f


def _lag_expr(ws, cash_row: int, expr_fn, ratio: str) -> None:
    """Like _lag but the accrual is an arbitrary per-column expression (e.g. C90-C91)."""
    for c in range(C0, C1 + 1):
        cur = expr_fn(c)
        if c == C0:
            f = f"={cur}-{ratio}*{cur}"
        else:
            f = f"={cur}-{ratio}*({cur}-{expr_fn(c - 1)})"
        ws.cell(cash_row, c).value = f


def _balance(ws, bal_row: int, expr_fn, ratio: str) -> None:
    """Closing payable/receivable balance = ratio * accrual expression."""
    for c in range(C0, C1 + 1):
        ws.cell(bal_row, c).value = f"={ratio}*{expr_fn(c)}"


def _sum(ws, row: int, lo: int, hi: int) -> None:
    for c in range(C0, C1 + 1):
        ws.cell(row, c).value = f"=SUM({col(c)}{lo}:{col(c)}{hi})"


def _add(ws, row: int, parts: list[int]) -> None:
    for c in range(C0, C1 + 1):
        ws.cell(row, c).value = "=" + "+".join(f"{col(c)}{p}" for p in parts)


# ---------------------------------------------------------------------------
# Task 2 — AR balance (166) + cash in from clients (186-208).
# ---------------------------------------------------------------------------
def task2_ar_cashin(wb) -> None:
    ws = wb[PF]
    # AR closing balance = DSO/30 * arrears-billed revenue (Revenue 45 minus the
    # annually-prepaid Subscription 60, which is deferred revenue, not a receivable).
    for c in range(C0, C1 + 1):
        ws.cell(166, c).value = f"={DSO}*({col(c)}45-{col(c)}60)"
    # Cash-in rows lag their matching recognised revenue line (incl. overage subtotal 205).
    for cash_row, src_row in CASHIN_MAP.items():
        _lag(ws, cash_row, src_row, DSO)
    # Clear stray leftovers in the Subscription (202-204) and Overage bundle (206-208)
    # detail rows — they carry a `=-#REF!` / junk in the tail months. Subscription is
    # repopulated in Task 4b; overage is summarised at the 205 subtotal (no bundle split).
    for r in (202, 203, 204, 206, 207, 208):
        for c in range(C0, C1 + 1):
            ws.cell(r, c).value = None
    # Subtotals and totals. Subscription (201<-202:204) stays blank until Task 4b.
    _sum(ws, 187, 188, 190)   # Components #1
    _sum(ws, 191, 192, 194)   # Components #2
    _sum(ws, 197, 198, 200)   # Hardware
    _sum(ws, 201, 202, 204)   # Subscription (0 until Task 4b)
    _add(ws, 196, [197, 201, 205])  # SaaS #3 (205 overage set above)
    _add(ws, 186, [187, 191, 196])  # Total cash in from clients


# Supplier (non-payroll) cost buckets: (payable-balance row, cash-paid row, cost expr).
# Payroll lives in the personnel section (Task 4), so these are all "excl. Payroll".
def _cost_cos(c):  return f"{col(c)}69"
def _cost_sm(c):   return f"({col(c)}90-{col(c)}91)"
def _cost_ga(c):   return f"({col(c)}99-{col(c)}100)"
def _cost_rd(c):   return f"({col(c)}110-{col(c)}111)"

SUPPLIERS = [
    (174, 211, _cost_cos),  # CoS
    (170, 212, _cost_sm),   # S&M excl. payroll
    (172, 213, _cost_ga),   # G&A excl. payroll
    (176, 214, _cost_rd),   # R&D excl. payroll
]


# ---------------------------------------------------------------------------
# Task 3 — supplier payables (168-176) + cash paid to suppliers (210-214).
# ---------------------------------------------------------------------------
def task3_supplier_payables(wb) -> None:
    ws = wb[PF]
    for bal_row, cash_row, expr in SUPPLIERS:
        _balance(ws, bal_row, expr, DPO)     # closing payable = DPO/30 * cost
        _lag_expr(ws, cash_row, expr, DPO)   # cash paid = cost - Δpayable
    _add(ws, 168, [170, 172, 174, 176])      # Trade payables (excl. payroll)
    _sum(ws, 210, 211, 214)                  # Cash Paid to Suppliers


def build() -> Path:
    wb = openpyxl.load_workbook(SRC, data_only=False)
    task1_payroll_days(wb)
    task2_ar_cashin(wb)
    task3_supplier_payables(wb)
    # Force Excel/LibreOffice to recompute on open (openpyxl writes no cached values).
    wb.calculation.fullCalcOnLoad = True
    wb.save(DST)
    return DST


if __name__ == "__main__":
    out = build()
    print(f"wrote {out}")
