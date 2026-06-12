"""Verify the generated rolling-budget workbook by *evaluating its real
formulas* (via the `formulas` library) — not a Python re-implementation.

Checks, for every month column E:P on the Pro Forma sheet:
  * Balance Check (R.BAL_CHECK) ≈ 0  (|x| ≤ tol)
  * Error cells (R.ERR_COUNT)   = 0

Usage:
  uv run python clients/farada/one_offs/verify_rolling_budget.py [--build]

  --build : rebuild farada.db + regenerate the workbook first.

Exits non-zero if any check fails — usable as a gate in the build loop.
"""

from __future__ import annotations

import argparse
import importlib.util
import logging
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKBOOK = HERE.parent / "reference" / "rolling_budget_v3.xlsx"
SHEET = "PRO FORMA"
TOL = 1.5  # €1 DB-rounding tolerance


def _load_generator_module():
    """Import build_rolling_budget.py by path (it lives in gitignored one_offs)."""
    spec = importlib.util.spec_from_file_location(
        "build_rolling_budget", HERE / "build_rolling_budget.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def recalc(path: Path) -> dict[str, object]:
    import formulas
    logging.getLogger("formulas").setLevel(logging.ERROR)
    xl = formulas.ExcelModel().loads(str(path)).finish()
    return xl.calculate()


def cell(sol: dict, col: str, row: int, sheet: str = SHEET):
    suffix = f"{sheet}'!{col}{row}".upper()
    for k, v in sol.items():
        if k.upper().endswith(suffix):
            try:
                return float(v.value[0, 0])
            except Exception:
                try:
                    return float(v.value)
                except Exception:
                    return v.value
    return None


PERIOD_COLS = ["E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true",
                    help="rebuild DB + regenerate workbook first")
    args = ap.parse_args()

    gen = _load_generator_module()
    bal_row = gen.R.BAL_CHECK
    err_row = gen.R.ERR_COUNT
    # CF tie row only exists pre-v3; tolerate absence.
    cf_tie_row = getattr(gen.R, "CF_TIE", None)

    if args.build:
        from core.data.build import build_db
        build_db("farada", ".")
        gen.main()

    if not WORKBOOK.exists():
        print(f"workbook not found: {WORKBOOK}", file=sys.stderr)
        return 2

    sol = recalc(WORKBOOK)

    print(f"{'mon':4} {'BAL_CHECK':>12} {'ERR':>5}" +
          (f" {'CF_TIE':>12}" if cf_tie_row else ""))
    failures = []
    for col, mon in zip(PERIOD_COLS, MONTHS):
        bal = cell(sol, col, bal_row)
        err = cell(sol, col, err_row)
        line = f"{mon:4} {bal:>12,.1f} {err:>5.0f}"
        if cf_tie_row:
            line += f" {cell(sol, col, cf_tie_row):>12,.1f}"
        print(line)
        if bal is None or abs(bal) > TOL:
            failures.append(f"{mon}: BAL_CHECK={bal}")
        if err is None or err != 0:
            failures.append(f"{mon}: ERR_COUNT={err}")

    if failures:
        print("\nFAIL:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"\nOK — balance ≤ €{TOL} and zero error cells for all 12 months.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
