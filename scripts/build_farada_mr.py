#!/usr/bin/env python3
"""Build Farada's monthly MR workbook by populating a new month column.

The MR (master accounting workbook) is a formula-driven Excel file:
  - `P&L Mapping` VLOOKUPs per-account values out of the `BWA` sheet, tagged
    with a leaf label; the front `P&L` then SUMs that mapping by leaf.
  - The front `CF` SUMIFs the `ControllingReport BWA` sheet by mapping code.
  - The front `BS` builds off the `Balance Sheet` / `Trial balance` sheets.

So the monthly job has two parts:
  1. DATA  — paste the new month's column into the German data sheets (this
     module), keyed by DATEV account number so nothing is dropped.
  2. FRONT — extend the front P&L/CF/BS formula columns one month to the right
     (handled separately; the front lags the data by a month in the source file).

This module does part (1) and self-validates by reproducing a known month
(April) from its raw sources and diffing against the delivered workbook.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import openpyxl

RAW = Path("clients/farada/raw/accounting")
MR_DIR = Path("clients/farada/raw")

# Month index helpers (1=Jan ... 12=Dec) -> column in each sheet.
# Raw German Jahresübersicht sheets: account in col 2, Jan in col 4 (so month m -> col 3+m).
RAW_ACC_COL = 2
def raw_month_col(m: int) -> int:
    return 3 + m

# MR data sheets that are a FAITHFUL account-keyed paste of a raw German export.
# month m -> col (jan_col - 1 + m).
#
# Only BWA qualifies. Deliberately excluded:
#   - ControllingReport BWA : derived, =VLOOKUP(... 'CR-Upload' ...) — extend the
#     formula, never paste values.
#   - CR-Upload (CF data)   : ~93% raw Controlling-BWA but carries MANUAL CF
#     reclassifications each month (e.g. acct 15900 €606k, sign-flipped 14000)
#     that are not mechanically derivable — must be booked by hand.
#   - Trial balance / Balance Sheet : bespoke S/H (Soll/Haben) layouts, not yet
#     validated; treated as manual for now.
DATA_SHEETS = {
    "BWA": dict(
        raw="BWA - Jahresübersicht {mm}-2026.xlsx",
        acc_col=2, jan_col=4,           # Jan=4 ... Apr=7, May=8
    ),
}


def _num(x):
    return float(x) if isinstance(x, (int, float)) else None


def _raw_account_values(raw_path: Path, month: int) -> dict[str, float]:
    """account number -> month value, from a raw German Jahresübersicht."""
    ws = openpyxl.load_workbook(raw_path, data_only=True).worksheets[0]
    col = raw_month_col(month)
    out: dict[str, float] = {}
    for r in range(3, ws.max_row + 1):
        acc = ws.cell(r, RAW_ACC_COL).value
        if acc not in (None, ""):
            out[str(acc).strip()] = _num(ws.cell(r, col).value) or 0.0
    return out


def _mr_account_rows(ws, acc_col: int) -> dict[str, int]:
    """account number -> row, for an MR data sheet (account-level rows only)."""
    out: dict[str, int] = {}
    for r in range(3, ws.max_row + 1):
        acc = ws.cell(r, acc_col).value
        if acc not in (None, ""):
            out.setdefault(str(acc).strip(), r)
    return out


def populate_sheet(wb, sheet: str, spec: dict, month: int, mm: str, write: bool):
    """Fill `sheet`'s month column from its raw source. Returns a report dict."""
    ws = wb[sheet]
    raw_path = RAW / f"{mm}-2026" / spec["raw"].format(mm=mm)
    raw_vals = _raw_account_values(raw_path, month)
    mr_rows = _mr_account_rows(ws, spec["acc_col"])
    mr_col = spec["jan_col"] - 1 + month

    written, unmapped, changed = 0, [], 0
    for acc, val in raw_vals.items():
        row = mr_rows.get(acc)
        if row is None:
            if abs(val) > 0.005:
                unmapped.append((acc, val))
            continue
        if write:
            prev = _num(ws.cell(row, mr_col).value)
            if prev is None or abs((prev or 0) - val) > 0.005:
                changed += 1
            ws.cell(row, mr_col).value = val
        written += 1
    return dict(sheet=sheet, raw=str(raw_path.name), written=written,
               unmapped=unmapped, changed=changed, mr_col=mr_col)


def golden_april(mr_path: Path) -> int:
    """Reproduce April from raw 04 and diff against the delivered workbook.

    Returns the number of account-level mismatches (0 = perfect reproduction).
    """
    wb = openpyxl.load_workbook(mr_path, data_only=True)
    mism = 0
    for sheet, spec in DATA_SHEETS.items():
        ws = wb[sheet]
        raw_vals = _raw_account_values(
            RAW / "04-2026" / spec["raw"].format(mm="04"), month=4)
        mr_rows = _mr_account_rows(ws, spec["acc_col"])
        col = spec["jan_col"] - 1 + 4
        sheet_mism = 0
        for acc, val in raw_vals.items():
            row = mr_rows.get(acc)
            if row is None:
                continue
            cur = _num(ws.cell(row, col).value) or 0.0
            if abs(cur - val) > 0.01:
                sheet_mism += 1
                if sheet_mism <= 5:
                    print(f"    {sheet} acct {acc}: MR={cur} raw04={val}")
        print(f"  {sheet}: {len(raw_vals)} raw accounts, {sheet_mism} April mismatches")
        mism += sheet_mism
    return mism


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--golden", action="store_true", help="reproduce April and diff")
    ap.add_argument("--month", type=int, default=5)
    ap.add_argument("--base", default=str(MR_DIR / "mr_2026-04.xlsx"))
    ap.add_argument("--out", default=str(MR_DIR / "mr_2026-05.xlsx"))
    args = ap.parse_args()

    if args.golden:
        print("GOLDEN: reproducing April data-sheet columns from raw 04...")
        n = golden_april(Path(args.base))
        print(f"\nTotal April account-level mismatches: {n}")
        raise SystemExit(0 if n == 0 else 1)

    mm = f"{args.month:02d}"
    print(f"Building {args.out} — populating month {mm} data columns from raw {mm}...")
    wb = openpyxl.load_workbook(args.base)  # keep formulas
    for sheet, spec in DATA_SHEETS.items():
        rep = populate_sheet(wb, sheet, spec, args.month, mm, write=True)
        print(f"  {sheet}: wrote {rep['written']} accounts into col {rep['mr_col']} "
              f"({rep['changed']} changed); unmapped={len(rep['unmapped'])}")
        for acc, val in rep["unmapped"]:
            print(f"      UNMAPPED account {acc} = {val:.2f}  (raw has it, MR has no row)")
    wb.save(args.out)
    print(f"Saved {args.out}")


if __name__ == "__main__":
    main()
