"""Verify farada_model_v4.5.xlsx — CF re-architecture R1–R3.

R1 ProForma stripped of profitability subtotals; R2 IS computes GP/EBITDA/EBIT/PBT/tax/NP from
its own leaves; R3 ProForma WC + financing rolls (tax-payable & RE reference the IS). No recalc
engine → structural + logic checks.

Run:  .venv/bin/python clients/farada/one_offs/verify_model_v4_5.py
"""
from __future__ import annotations

import openpyxl
from openpyxl.worksheet.formula import ArrayFormula

P = "clients/farada/modeling/farada_model_v4.5.xlsx"


def ft(cell):
    v = cell.value
    return (v.text if isinstance(v, ArrayFormula) else v)


def labels(ws):
    out = {}
    for r in range(1, ws.max_row + 1):
        v = ws.cell(r, 1).value
        if isinstance(v, str) and v.strip():
            out.setdefault(v.strip(), r)
    return out


def main():
    wb = openpyxl.load_workbook(P)
    ws, inp, iss = wb["ProForma"], wb[" Inputs"], wb["IS"]
    L = labels(iss)
    fails = []

    def ck(cond, msg):
        print(f"  {'✅' if cond else '❌'} {msg}")
        if not cond:
            fails.append(msg)

    print("\n[R1] ProForma profitability subtotals stripped")
    for r in (44, 116, 125, 130, 131, 132):
        ck(ws.cell(r, 3).value is None and ws.cell(r, 1).value is None, f"ProForma row {r} blank")

    print("\n[R2] IS computes subtotals from its own leaves (not ProForma pulls)")
    ck(ft(iss.cell(L["Gross profit TOTAL (€)"], 3)) == f"=C{L['Revenue']}-C{L['COGS TOTAL']}", "GP = Rev − COGS")
    ck(ft(iss.cell(L["EBITDA"], 3)) == f"=C{L['Gross profit TOTAL (€)']}-C{L['Operating expenses']}", "EBITDA = GP − OPEX")
    ck(ft(iss.cell(L["EBIT"], 3)) == f"=C{L['EBITDA']}+C{L['Grant financing']}-C{L['Depreciation & amortisation']}", "EBIT = EBITDA + grant − D&A")
    ck(ft(iss.cell(L["Income tax (expense)"], 3)) == f"=-MAX(0,C{L['Profit / (loss) before income tax']})*' Inputs'!$J$158", "Tax = −MAX(0,PBT)×rate (on IS)")
    ck(ft(iss.cell(L["Net profit / (loss) for the period"], 3)) == f"=C{L['Profit / (loss) before income tax']}+C{L['Income tax (expense)']}", "NP = PBT + tax")
    # per-bundle GP dropped
    hwgp = L["Hardware GP (€)"]
    ck(all(iss.cell(hwgp + i, 3).value is None for i in (1, 2, 3)), "per-bundle GP rows dropped")

    print("\n[R3] ProForma rolls; tax-payable & RE reference the IS")
    Lp = labels(ws)
    ck(ft(ws.cell(Lp["Trade receivables (AR)"], 3)).startswith("=((C5+C9+C15)*(1-"), "AR roll present")
    ck(ft(ws.cell(Lp["Trade payables (total)"], 3)).startswith("=C145+C146+C147+C148"), "AP total = Σ buckets")
    tp = Lp["Tax payable"]
    ck(ft(ws.cell(tp, 3)) == f"=-IS!C{L['Income tax (expense)']}*IF(' Inputs'!$J$167>=1,1,0)", "Tax-payable roll → IS tax")
    re = Lp["Retained earnings"]
    ck(ft(ws.cell(re, 3)) == f"=' Inputs'!$J$182+IS!C{L['Net profit / (loss) for the period']}", "RE roll → opening + IS net profit")
    ck(ft(ws.cell(re, 4)) == f"=C{re}+IS!D{L['Net profit / (loss) for the period']}", "RE roll month 2 = prior + IS NP")

    print("\n[inputs] CF groups present")
    Li = labels_col3 = {}
    for r in range(155, 185):
        v = inp.cell(r, 3).value
        if isinstance(v, str):
            labels_col3[v.strip()] = r
    for kw in ("Receivable days (DSO)", "Payable days (DPO)", "Equity round amount",
               "Opening cash", "Opening retained earnings"):
        ck(any(kw in k for k in labels_col3), f"input: {kw}")

    print("\n[struct] no naked rows; no new #REF!")
    naked = [f"C{r}" for r in (Lp["Trade receivables (AR)"], re, L["EBITDA"])
             if ws.cell(r, 3).value is not None and ws.cell(r, 3).number_format == "General"
             or (iss.cell(L["EBITDA"], 3).number_format == "General")]
    ck(iss.cell(L["EBITDA"], 3).number_format != "General", "IS EBITDA styled (not General)")
    refrows = {(sn, c.row) for sn in wb.sheetnames for row in wb[sn].iter_rows() for c in row
               if isinstance(ft(c), str) and "#REF!" in ft(c)}
    ck(refrows <= {("ProForma", 78)}, f"no new #REF! (got {sorted(refrows)})")
    # blanked cells read as 0 (not #REF!), so explicitly assert nothing still pulls a stripped row
    import re
    strip = set(range(44, 56)) | {116, 125, 130, 131, 132}
    dangling = []
    for sn in wb.sheetnames:
        for row in wb[sn].iter_rows():
            for cell in row:
                t = ft(cell)
                if isinstance(t, str) and any(int(m) in strip for m in re.findall(r"ProForma!\$?[A-Z]{1,2}\$?(\d+)", t)):
                    dangling.append(f"{sn}!{cell.coordinate}")
    ck(not dangling, f"no cell still references a stripped ProForma row (found {dangling[:5]})")

    print()
    if fails:
        print(f"FAILED {len(fails)} check(s):")
        for f in fails:
            print(f"  - {f}")
        raise SystemExit(1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
