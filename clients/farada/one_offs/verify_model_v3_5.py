"""Verify farada_model_v3.5.xlsx — Phase 1 (HR payroll wiring + salary indexation).

v3.5 is the hand-built source of truth (HR sheet + grouped inputs); we PATCH it in place
(patch_model_v3_5.py). No recalc engine, so this is safe-by-construction + structural checks.

Run from repo root:  .venv/bin/python clients/farada/one_offs/verify_model_v3_5.py
"""
from __future__ import annotations

import openpyxl
from openpyxl.worksheet.formula import ArrayFormula

P = "clients/farada/modeling/farada_model_v3.5.xlsx"
SAL_IDX_ROW = 137          # salary indexation input (end of OPEX group)


def ft(cell):
    v = cell.value
    return (v.text if isinstance(v, ArrayFormula) else v) or "" if v is not None else None


def main() -> None:
    wb = openpyxl.load_workbook(P)
    ws, inp, hr = wb["ProForma"], wb[" Inputs"], wb["HR"]
    fails: list[str] = []

    def ck(cond, msg):
        print(f"  {'✅' if cond else '❌'} {msg}")
        if not cond:
            fails.append(msg)

    print("\n[T3] HR payroll wired into ProForma OPEX (HR-total-row convention)")
    expect = {"C88": "=HR!O16", "C97": "=HR!O48", "C109": "=HR!O67", "C110": "=HR!O66"}
    for coord, f in expect.items():
        ck(ft(ws[coord]) == f, f"{coord} = {f}")
    ck(ft(ws["D88"]) == "=HR!P16", "fill-right aligns (D88=HR!P16, calendar offset C↔O)")
    # the OPEX payroll subtotals must roll into Operating expenses -> EBITDA
    ck(ft(ws["C108"]) == "=C109+C110", "R&D Total Payroll = Germany+Serbia")

    print("\n[T2] Salary indexation input present, in the OPEX group, wired to HR")
    lbl = ft(inp.cell(SAL_IDX_ROW, 3))
    ck(isinstance(lbl, str) and "indexation" in lbl.lower(), f"Inputs r{SAL_IDX_ROW} label = salary indexation ({lbl!r})")
    ck(ft(inp.cell(SAL_IDX_ROW, 10)) == f"=OFFSET(K{SAL_IDX_ROW},0,$D$2)", "uses the scenario OFFSET pattern")
    ck(isinstance(inp.cell(SAL_IDX_ROW, 12).value, (int, float)), "has a Realistic value in L")
    n_old = sum(1 for row in hr.iter_rows() for c in row if isinstance(ft(c), str) and "$J$250" in ft(c))
    n_new = sum(1 for row in hr.iter_rows() for c in row if isinstance(ft(c), str) and f"$J${SAL_IDX_ROW}" in ft(c))
    ck(n_old == 0, f"HR no longer references the empty J250 (found {n_old})")
    ck(n_new > 2000, f"HR salary-escalation cells now reference J{SAL_IDX_ROW} ({n_new} cells)")

    print("\n[struct] no NEW #REF! (pre-existing capacity row 78 only)")
    ref_rows = {cell.row for row in ws.iter_rows() for cell in row
                if isinstance(ft(cell), str) and "#REF!" in ft(cell)}
    ck(ref_rows <= {78}, f"#REF! rows ⊆ {{78}} (got {sorted(ref_rows)})")

    print("\n[flag] HR subtotal labels (informational, not changed — format is a given):")
    print(f"     HR r39 {hr.cell(39,1).value!r} sums R&D engineers; HR r48 {hr.cell(48,1).value!r} sums G&A people")
    print("     → labels look swapped, but ProForma pulls the correct CONTENT. Flagged for the user.")

    print()
    if fails:
        print(f"FAILED {len(fails)} check(s):")
        for f in fails:
            print(f"  - {f}")
        raise SystemExit(1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
