"""Build farada_model_v4.5 from v4 — cash flow Phase 1: input groups + ProForma WC/financing rolls.

Direct-method CF (house convention across the Farada rolling budget / Cupffee / Almacena): a
ProForma working-capital engine of balance rolls (balances = flow/30 × days), AP bucketed by cost
category, cash-as-plug; NO inventory (build-to-order). Phase 1 lays the input drivers + the balance
rolls; the CF/BS statements come in Phase 2. v4.5 is a DRAFT; the confirmed final build = v5.

Reads v4 (preserved), writes v4.5. Idempotent. Run:
  .venv/bin/python clients/farada/one_offs/build_model_v4_5.py
"""
from __future__ import annotations

from copy import copy
from datetime import datetime

import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.formula import ArrayFormula

SRC = "clients/farada/modeling/farada_model_v4.xlsx"
DST = "clients/farada/modeling/farada_model_v4.5.xlsx"
FIRST, LAST = 3, 62

# ---- Inputs: new CF groups (appended after the BELOW-EBITDA group, no row-shift) ----
I = dict(WC_HDR=161, DSO=162, PREPAY=163, SAAS_ANN=164, DPO=165, PAYDAYS=166, TAXLAG=167,
         FIN_HDR=169, EQ_AMT=170, EQ_DATE=171, DEBT_AMT=172, DEBT_DATE=173, DEBT_INT=174,
         OB_CASH=175, OB_AR=176, OB_AP=177, OB_PAYROLL=178, OB_DEFERRED=179, OB_DEBT=180,
         OB_SC=181, OB_RE=182)
# ---- ProForma: new balance-roll block (appended after the capex schedule) ----
R = dict(HDR=143, AR=144, AP_COGS=145, AP_SM=146, AP_GA=147, AP_RD=148, AP_TOT=149,
         PAYROLL=150, DEFERRED=151, TAXPAY=152, SC=153, DEBT=154, RE=155)


def _ft(c):
    v = c.value
    return v.text if isinstance(v, ArrayFormula) else v


def add_cf_inputs(wb):
    inp = wb[" Inputs"]
    s_hdr = inp.cell(152, 3)._style
    s_lbl, s_unit = inp.cell(154, 3)._style, inp.cell(154, 4)._style
    s_j, s_l = inp.cell(154, 10)._style, inp.cell(154, 12)._style

    def hdr(r, text):
        inp.cell(r, 3, text)._style = copy(s_hdr)

    def put(r, label, unit, value, numfmt):
        inp.cell(r, 3, label)._style = copy(s_lbl)
        inp.cell(r, 4, unit)._style = copy(s_unit)
        inp.cell(r, 10, f"=OFFSET(K{r},0,$D$2)")._style = copy(s_j)
        c = inp.cell(r, 12, value)
        c._style = copy(s_l)
        c.number_format = numfmt

    hdr(I["WC_HDR"], "WORKING CAPITAL (payment terms)  (mockup ← confirm)")
    put(I["DSO"], "Receivable days (DSO)", "days", 30, "#,##0")
    put(I["PREPAY"], "Hardware prepayment % (large orders)", "%", 0.5, "0.0%")
    put(I["SAAS_ANN"], "SaaS billed annually in advance", "%", 0.0, "0.0%")
    put(I["DPO"], "Payable days (DPO)", "days", 30, "#,##0")
    put(I["PAYDAYS"], "Payroll payable days", "days", 30, "#,##0")
    put(I["TAXLAG"], "Tax payment lag", "months", 0, "#,##0")
    hdr(I["FIN_HDR"], "FINANCING & OPENING BALANCES (Jul-2026)  (mockup ← confirm)")
    put(I["EQ_AMT"], "Equity round amount", "EUR", 5_000_000, "€#,##0")
    put(I["EQ_DATE"], "Equity round date", "date", datetime(2027, 7, 1), "mmm-yyyy")
    put(I["DEBT_AMT"], "Debt draw amount", "EUR", 0, "€#,##0")
    put(I["DEBT_DATE"], "Debt draw date", "date", datetime(2026, 7, 1), "mmm-yyyy")
    put(I["DEBT_INT"], "Debt annual interest", "%", 0.0, "0.0%")
    put(I["OB_CASH"], "Opening cash", "EUR", 2_000_000, "€#,##0")
    put(I["OB_AR"], "Opening AR", "EUR", 0, "€#,##0")
    put(I["OB_AP"], "Opening AP", "EUR", 0, "€#,##0")
    put(I["OB_PAYROLL"], "Opening payroll payable", "EUR", 0, "€#,##0")
    put(I["OB_DEFERRED"], "Opening deferred revenue", "EUR", 0, "€#,##0")
    put(I["OB_DEBT"], "Opening debt", "EUR", 0, "€#,##0")
    put(I["OB_SC"], "Opening share capital", "EUR", 5_000_000, "€#,##0")
    put(I["OB_RE"], "Opening retained earnings", "EUR", -3_000_000, "€#,##0")


def add_rolls(wb):
    ws = wb["ProForma"]
    leaf = {c: ws.cell(89, c)._style for c in range(1, LAST + 1)}
    band = {c: ws.cell(85, c)._style for c in range(1, LAST + 1)}
    jp = lambda n: f"' Inputs'!$J${I[n]}"          # inputs J ref

    LABEL = {R["HDR"]: "WORKING CAPITAL & FINANCING ROLLS (balances)",
             R["AR"]: "  Trade receivables (AR)", R["AP_COGS"]: "  Trade payables — COGS",
             R["AP_SM"]: "  Trade payables — S&M", R["AP_GA"]: "  Trade payables — G&A",
             R["AP_RD"]: "  Trade payables — R&D", R["AP_TOT"]: "  Trade payables (total)",
             R["PAYROLL"]: "  Payroll payable", R["DEFERRED"]: "  Deferred revenue (SaaS annual)",
             R["TAXPAY"]: "  Tax payable", R["SC"]: "  Share capital", R["DEBT"]: "  Debt",
             R["RE"]: "  Retained earnings"}

    def fml(rk, L, prev, first):
        if rk == "AR":
            return f"=(({L}5+{L}9+{L}15)*(1-{jp('PREPAY')})+{L}19*(1-{jp('SAAS_ANN')}))/30*{jp('DSO')}"
        if rk == "AP_COGS": return f"={L}24/30*{jp('DPO')}"
        if rk == "AP_SM":   return f"=({L}87-{L}88)/30*{jp('DPO')}"
        if rk == "AP_GA":   return f"=({L}96-{L}97)/30*{jp('DPO')}"
        if rk == "AP_RD":   return f"=({L}107-{L}108)/30*{jp('DPO')}"
        if rk == "AP_TOT":  return f"={L}{R['AP_COGS']}+{L}{R['AP_SM']}+{L}{R['AP_GA']}+{L}{R['AP_RD']}"
        if rk == "PAYROLL": return f"=({L}88+{L}97+{L}108)/30*{jp('PAYDAYS')}"
        if rk == "DEFERRED": return f"={L}19*{jp('SAAS_ANN')}*6"
        if rk == "TAXPAY":  return f"=-{L}131*IF({jp('TAXLAG')}>=1,1,0)"
        if rk == "SC":
            inj = f"IF({L}2={jp('EQ_DATE')},{jp('EQ_AMT')},0)"
            return f"={jp('OB_SC')}+{inj}" if first else f"={prev}{R['SC']}+IF({L}2={jp('EQ_DATE')},{jp('EQ_AMT')},0)"
        if rk == "DEBT":
            dr = f"IF({L}2={jp('DEBT_DATE')},{jp('DEBT_AMT')},0)"
            return f"={jp('OB_DEBT')}+{dr}" if first else f"={prev}{R['DEBT']}+IF({L}2={jp('DEBT_DATE')},{jp('DEBT_AMT')},0)"
        if rk == "RE":
            return f"={jp('OB_RE')}+{L}132" if first else f"={prev}{R['RE']}+{L}132"
        return None

    # header band
    ws.cell(R["HDR"], 1, LABEL[R["HDR"]])._style = copy(band[1])
    for c in range(2, LAST + 1):
        ws.cell(R["HDR"], c)._style = copy(band[c])
    # roll rows
    for rk in ("AR", "AP_COGS", "AP_SM", "AP_GA", "AP_RD", "AP_TOT", "PAYROLL",
               "DEFERRED", "TAXPAY", "SC", "DEBT", "RE"):
        r = R[rk]
        ws.cell(r, 1, LABEL[r])._style = copy(leaf[1])
        for c in range(FIRST, LAST + 1):
            L, prev = get_column_letter(c), get_column_letter(c - 1)
            ws.cell(r, c, fml(rk, L, prev, c == FIRST))._style = copy(leaf[c])
    print(f"  rolls: AR, 4 AP buckets+total, payroll, deferred, tax, SC, debt, RE "
          f"(ProForma {R['HDR']}-{R['RE']}); CF inputs {I['WC_HDR']}-{I['OB_RE']}")


def build():
    wb = openpyxl.load_workbook(SRC)
    add_cf_inputs(wb)
    add_rolls(wb)
    wb.save(DST)
    print(f"Saved {DST}")


if __name__ == "__main__":
    build()
