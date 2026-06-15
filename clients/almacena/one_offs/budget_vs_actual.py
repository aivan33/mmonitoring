"""Budget-vs-actual for the Almacena FY2026 alignment (IS, Jan-Apr).

Compares the stale budget (`budget-q126.xlsx` taxonomi tabs) against the
management actuals (`raw/taxonomi_*_04.xlsx`) for the elapsed months, per entity,
and flags material lines. Rows align by POSITION (both files share one taxonomi
template; the 'Other' subgroup repeats, so label-keying is ambiguous) — the script
asserts the labels match position-for-position, never silently misaligning.

Usage:  python clients/almacena/one_offs/budget_vs_actual.py

This is analysis scaffolding for ALIGNMENT_LEDGER.md, not a deliverable itself.
"""

from __future__ import annotations

from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[3]
BUDGET = ROOT / "clients/almacena/budget/budget-q126.xlsx"
ACT_CONS = ROOT / "clients/almacena/raw/taxonomi_consolidated_04.xlsx"
ACT_FOUND = ROOT / "clients/almacena/raw/taxonomi_ap_foundation_04.xlsx"

N = 4  # elapsed months Jan-Apr
FLAG_YTD = 10_000.0
FLAG_APR = 5_000.0

# entity -> (budget sheet, actuals file, actuals sheet)  [IS only here]
ENTITIES = {
    "consolidated": ("is_cons_taxonomi", ACT_CONS, "IS (Actual)"),
    "foundation": ("is_found_taxonomi", ACT_FOUND, "IS (Actual)"),
}


def _read(path: Path, sheet: str) -> list[tuple[str, str, str, list[float]]]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb[sheet]
        rows = []
        for r in ws.iter_rows(min_row=2, values_only=True):
            if r[1] is None and r[2] is None:
                continue
            data = (r[0] or "").strip() if isinstance(r[0], str) else ""
            group = (r[1] or "").strip() if isinstance(r[1], str) else str(r[1] or "")
            sub = (r[2] or "").strip() if isinstance(r[2], str) else str(r[2] or "")
            vals = [float(r[3 + i] or 0.0) for i in range(N)]
            rows.append((data, group, sub, vals))
        return rows
    finally:
        wb.close()


def compare(entity: str, budget_sheet: str, act_file: Path, act_sheet: str):
    b = _read(BUDGET, budget_sheet)
    a = _read(act_file, act_sheet)
    assert len(b) == len(a), f"{entity}: row count differs {len(b)} vs {len(a)}"
    print(f"\n{'='*88}\n{entity.upper()} — IS budget vs actual (Jan-Apr 2026)\n{'='*88}")
    print(f"{'Section / line':40} {'B YTD':>11} {'A YTD':>11} {'Δ YTD':>11} {'Δ Apr':>10}")
    flagged = []
    for (bd, bg, bs, bv), (ad, ag, asb, av) in zip(b, a):
        assert (bg, bs) == (ag, asb), f"{entity}: label drift {bg}/{bs} vs {ag}/{asb}"
        b_ytd, a_ytd = sum(bv), sum(av)
        d_ytd, d_apr = a_ytd - b_ytd, av[3] - bv[3]
        material = abs(d_ytd) > FLAG_YTD or abs(d_apr) > FLAG_APR
        mark = " *" if material else "  "
        label = f"{bd[:10]:11}{bg[:27]}"
        print(f"{label[:40]:40} {b_ytd:11,.0f} {a_ytd:11,.0f} {d_ytd:11,.0f} {d_apr:10,.0f}{mark}")
        if material:
            flagged.append((entity, bd, bg, bs, b_ytd, a_ytd, d_ytd, bv[3], av[3], d_apr))
    return flagged


def main() -> int:
    flagged = []
    for ent, (bsheet, afile, asheet) in ENTITIES.items():
        flagged += compare(ent, bsheet, afile, asheet)

    # self-check against documented ties
    cons_nir_apr = next(f for f in flagged if f[0] == "consolidated" and "Net Interest" in f[2])
    assert abs(cons_nir_apr[8] - 29284.39) < 1, f"NIR Apr actual tie failed: {cons_nir_apr[8]}"

    print(f"\n{'='*88}\nMATERIAL LINES ({len(flagged)}) — |Δ YTD|>{FLAG_YTD:,.0f} or |Δ Apr|>{FLAG_APR:,.0f}\n{'='*88}")
    for ent, d, g, s, by, ay, dy, ba, aa, da in flagged:
        print(f"  [{ent:12}] {d:10} {g[:30]:30} ΔYTD {dy:+11,.0f}  ΔApr {da:+10,.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
