"""CLI: run the model verification gate on a workbook.

Recomputes the workbook with LibreOffice (the authoritative engine) and runs the
integrity gates configured in ``clients/<client>/model_gates.yaml``: no error
cells, BS check ~0, statements tie, subtotals foot.

Exit codes: 0 = PASS, 1 = violations found, 2 = setup error (missing gates yaml,
workbook, or LibreOffice).

Usage:
    python scripts/check_model.py <client> <path/to/workbook.xlsx>
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.model.integrity import load_gates, run_all
from core.model.recalc import SofficeNotFound, recalc

_MAX_SHOWN = 40


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the model verification gate.")
    ap.add_argument("client")
    ap.add_argument("workbook", help="path to the model .xlsx")
    args = ap.parse_args()

    wb_path = Path(args.workbook)
    if not wb_path.exists():
        print(f"error: no workbook at {wb_path}", file=sys.stderr)
        return 2
    try:
        gates = load_gates(args.client)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    try:
        wb = recalc(wb_path)
    except SofficeNotFound as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    violations = run_all(wb, gates)
    print(f"check_model {args.client} {wb_path.name}")
    if not violations:
        print("  PASS — no gate violations")
        return 0

    for v in violations[:_MAX_SHOWN]:
        print(f"  FAIL [{v.check}] {v.sheet}!{v.cell}: {v.detail}")
    if len(violations) > _MAX_SHOWN:
        print(f"  ... and {len(violations) - _MAX_SHOWN} more")
    by_check = dict(Counter(v.check for v in violations))
    print(f"  {len(violations)} violation(s): {by_check}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
