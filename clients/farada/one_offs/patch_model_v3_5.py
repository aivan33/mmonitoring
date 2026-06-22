"""Patch the hand-built farada_model_v3.5.xlsx IN PLACE (idempotent).

v3.5 is the source of truth (user hand-added the HR sheet + re-sorted the inputs into groups;
no builder reproduces it). We extend it by patching only the cells we own, so the user's hand
work is preserved. A one-time pristine backup is written before the first patch (the file is
gitignored — no git safety net). Safe to re-run.

Phase 1 (this file):
  - Salary indexation input — HR escalates every salary by ' Inputs'!$J$250, but that cell is
    empty (=> no indexation). Add the input in its LOGICAL GROUP (end of OPEX, row 137 — a blank
    row, so no row-shift / no $J$NN ref breakage) and repoint HR's 2,340 refs J250 -> J137.
    (Payroll itself is already wired: ProForma OPEX pulls HR subtotal rows O16/O48/O66/O67.)

Run from repo root:  .venv/bin/python clients/farada/one_offs/patch_model_v3_5.py
"""
from __future__ import annotations

import os
import shutil
from copy import copy

import openpyxl
from openpyxl.worksheet.formula import ArrayFormula

P = "clients/farada/modeling/farada_model_v3.5.xlsx"
BAK = "clients/farada/modeling/farada_model_v3.5.prepatch.xlsx"

SAL_IDX_ROW = 137          # salary indexation — blank row at the end of the OPEX group
STYLE_ROW = 33             # "Annual price indexation" (a %-rate input) — style template
SAL_IDX_RATE = 0.03        # 3% default (matches price indexation J33); ← user to confirm


def _ft(cell):
    v = cell.value
    return v.text if isinstance(v, ArrayFormula) else v


def add_salary_indexation(wb) -> None:
    inp, hr = wb[" Inputs"], wb["HR"]
    # 1) the input row, styled like the price-indexation rate input (C/D/J/L, no dates).
    for col in (3, 4, 10, 12):
        inp.cell(SAL_IDX_ROW, col)._style = copy(inp.cell(STYLE_ROW, col)._style)
    inp.cell(SAL_IDX_ROW, 3, "Annual salary indexation  ← confirm (defaulted to 3%)")
    inp.cell(SAL_IDX_ROW, 4, "%")
    inp.cell(SAL_IDX_ROW, 10, f"=OFFSET(K{SAL_IDX_ROW},0,$D$2)")
    inp.cell(SAL_IDX_ROW, 12, SAL_IDX_RATE)
    # 2) repoint HR's salary-escalation refs J250 -> J137 (idempotent: no-op once replaced).
    n = 0
    for row in hr.iter_rows():
        for cell in row:
            t = _ft(cell)
            if isinstance(t, str) and "$J$250" in t:
                cell.value = t.replace("$J$250", f"$J${SAL_IDX_ROW}")
                n += 1
    print(f"  salary indexation: input at Inputs!{openpyxl.utils.get_column_letter(12)}{SAL_IDX_ROW}"
          f" = {SAL_IDX_RATE:.0%}; repointed {n} HR cells J250 -> J{SAL_IDX_ROW}")


def patch() -> None:
    if not os.path.exists(BAK):
        shutil.copy2(P, BAK)
        print(f"  wrote pristine backup -> {BAK}")
    else:
        print(f"  backup already exists ({BAK}) — left untouched")
    wb = openpyxl.load_workbook(P)
    add_salary_indexation(wb)
    wb.save(P)
    print(f"Saved {P}")


if __name__ == "__main__":
    patch()
