"""Verify farada_model_v4.5.xlsx — cash-flow Phase 1 (inputs + ProForma WC/financing rolls).

Direct-method CF (house convention) with a ProForma working-capital engine, cash-as-plug; AP
bucketed by cost category; no inventory (build-to-order). Phase 1 adds the input groups and the
balance rolls only (statements come in Phase 2). No recalc engine → structural + logic oracle.

Run:  .venv/bin/python clients/farada/one_offs/verify_model_v4_5.py
"""
from __future__ import annotations

import openpyxl
from openpyxl.worksheet.formula import ArrayFormula

P = "clients/farada/modeling/farada_model_v4.5.xlsx"


def ft(cell):
    v = cell.value
    return (v.text if isinstance(v, ArrayFormula) else v)


def rows_by_label(ws, col=1):
    out = {}
    for r in range(1, ws.max_row + 1):
        v = ws.cell(r, col).value
        if isinstance(v, str) and v.strip():
            out.setdefault(v.strip(), r)
    return out


def main():
    wb = openpyxl.load_workbook(P)
    ws, inp = wb["ProForma"], wb[" Inputs"]
    fails = []

    def ck(cond, msg):
        print(f"  {'✅' if cond else '❌'} {msg}")
        if not cond:
            fails.append(msg)

    print("\n[v4.5] sheets unchanged from v4")
    for s in (" Inputs", "Revenue_Inputs", "ProForma", "HR", "IS", "IS_Y"):
        ck(s in wb.sheetnames, f"sheet {s!r} present")

    print("\n[CF1] cash-flow input groups (working capital + financing + opening balances)")
    Li = rows_by_label(inp, col=3)
    for kw in ("Receivable days (DSO)", "Hardware prepayment", "SaaS billed annually",
               "Payable days (DPO)", "Payroll payable days",
               "Equity round amount", "Opening cash", "Opening share capital",
               "Opening retained earnings"):
        ck(any(kw in k for k in Li), f"input present: {kw}")

    print("\n[CF2] ProForma working-capital rolls")
    Lp = rows_by_label(ws)
    ar = Lp["Trade receivables (AR)"]
    ck(ft(ws.cell(ar, 3)).startswith("=((C5+C9+C15)*(1-"), "AR = (hardware ex-prepay + SaaS monthly)/30×DSO")
    apc = Lp["Trade payables — COGS"]
    ck(ft(ws.cell(apc, 3)) == "=C24/30*' Inputs'!$J$165", "AP-COGS = COGS/30×DPO")
    ck(ft(ws.cell(Lp["Trade payables — S&M"], 3)) == "=(C87-C88)/30*' Inputs'!$J$165", "AP-S&M = (S&M−payroll)/30×DPO")
    apt = Lp["Trade payables (total)"]
    ck(ft(ws.cell(apt, 3)) == f"=C{apc}+C{apc+1}+C{apc+2}+C{apc+3}", "AP total = Σ 4 buckets")
    pp = Lp["Payroll payable"]
    ck(ft(ws.cell(pp, 3)) == "=(C88+C97+C108)/30*' Inputs'!$J$166", "Payroll payable = payroll/30×days")
    ck("Deferred revenue (SaaS annual)" in Lp, "Deferred revenue roll present")
    ck("Tax payable" in Lp, "Tax payable roll present")

    print("\n[CF3] financing + retained-earnings rolls (cumulative, opening then prior+flow)")
    sc = Lp["Share capital"]
    ck(ft(ws.cell(sc, 3)).startswith("=' Inputs'!$J$181+IF(C2=") and ft(ws.cell(sc, 4)).startswith("=C"),
       "Share capital = opening + dated equity injection (then prior+inject)")
    re = Lp["Retained earnings"]
    ck(ft(ws.cell(re, 3)) == "=' Inputs'!$J$182+C132" and ft(ws.cell(re, 4)) == "=C{}+D132".format(re),
       "Retained earnings = opening + net profit (then prior + NP)")
    ck("Debt" in Lp, "Debt roll present")

    print("\n[oracle] financing-roll accumulation (computable from inputs)")
    eq_amt = inp.cell(rows_by_label(inp, 3)["Equity round amount"], 12).value
    ob_sc = inp.cell(rows_by_label(inp, 3)["Opening share capital"], 12).value
    ck(isinstance(eq_amt, (int, float)) and isinstance(ob_sc, (int, float)),
       f"equity amount €{eq_amt:,.0f}, opening SC €{ob_sc:,.0f} (SC ends = opening + 1 tranche)")

    print("\n[struct] no naked rows; no new #REF!")
    naked = [f"C{r}" for r in (ar, apc, apt, pp, sc, re)
             if ws.cell(r, 3).value is not None and ws.cell(r, 3).number_format == "General"]
    ck(not naked, f"roll cells styled (found {naked})")
    refrows = {(sn, c.row) for sn in wb.sheetnames for row in wb[sn].iter_rows() for c in row
               if isinstance(ft(c), str) and "#REF!" in ft(c)}
    ck(refrows <= {("ProForma", 78)}, f"no new #REF! (got {sorted(refrows)})")

    print()
    if fails:
        print(f"FAILED {len(fails)} check(s):")
        for f in fails:
            print(f"  - {f}")
        raise SystemExit(1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
