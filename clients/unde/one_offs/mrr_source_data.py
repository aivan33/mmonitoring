"""Categorization -> MRR Schedule '1.1 Source Data' rows (workstream B, stage 1a).

The Categorization 'Income Invoices' sheet is a cumulative DB. Each month the
NEW invoices (this month's file minus last month's) are appended to Source Data,
EUR-converted and keyed for the downstream MRR calc.

Column indices in 'Income Invoices' (0-based, header on row 7):
  0 Date | 2 Billing start | 3 Billing end | 4 Currency | 5 Amount
  8 Commercial name | 9 Country | 10 Product | 11 Contract length
  12 Subscription type | 14 MRR flag | 15 Start date | 16 End date
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from openpyxl import load_workbook

# Categorization product label -> Source Data 'Produs' label.
PRODUS = {
    "Employer branding": "Employer Branding",
    "Jobbing": "Corporate Jobbing",
    "Advertising": "Advertising",
    "LinkedIn Learning": "LinkedIn Learning",
    "Linkedin Learning": "LinkedIn Learning",
    "LinkedIn": "LinkedIn Learning",
    "Salary report": "Salary report",
    "Brand perception": "Brand perception",
}


def load_invoices(path: str | Path) -> list[dict]:
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb["Income Invoices"]
    out = []
    for r in ws.iter_rows(min_row=8, values_only=True):
        if r[0] is None and r[5] is None:
            continue
        out.append({
            "date": r[0], "billstart": r[2], "currency": r[4], "amount": r[5],
            "commercial": r[8], "country": r[9], "product": r[10],
            "length": r[11], "subtype": r[12], "mrr": r[14],
            "start": r[15], "end": r[16],
        })
    wb.close()
    return out


def new_invoices(curr_path, year: int, month: int) -> list[dict]:
    """Invoices dated in the reporting month (docx: 'all new invoices in the
    month'). Cross-file diffing is NOT viable — the Categorization column schema
    drifts between monthly versions (April added a Commercial-name column and
    split Country/Product), so selection is by invoice Date within one file."""
    out = []
    for inv in load_invoices(curr_path):
        d = inv["date"]
        if isinstance(d, dt.datetime) and d.year == year and d.month == month:
            out.append(inv)
    return out


def to_source_row(inv: dict, fx_ron: float, fx_usd: float) -> dict:
    cur = inv["currency"]
    rate = {"LEI": fx_ron, "RON": fx_ron, "USD": fx_usd, "EUR": 1.0}.get(cur, 1.0)
    amount = inv["amount"] or 0.0
    valoare = amount / rate
    period = inv["length"]
    monthly = valoare / period if isinstance(period, (int, float)) and period else None
    return {
        "currency": cur, "amount": amount, "client": inv["commercial"],
        "valoare": valoare, "start": inv["start"], "period": period,
        "country": inv["country"], "mrr": inv["mrr"], "monthly": monthly,
        "produs": PRODUS.get(inv["product"], inv["product"]),
    }
