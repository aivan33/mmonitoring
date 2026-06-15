"""CLI: dump a model workbook's contract (entities, seams, drivers, month-axis),
optionally tracing a budget output cell back to its driver leaves.

Usage:
    python scripts/model_map.py <workbook.xlsx> <model_rules.yaml> [--trace SHEET!COORD]

Example:
    python scripts/model_map.py \\
        clients/almacena/budget/Almacena-26_AprActuals.xlsx \\
        clients/almacena/model_rules.yaml \\
        --trace 'is_cons_taxonomi!D2'
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make the repo root importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.model.cells import read_cells          # noqa: E402
from core.model.contract import load_rules, read_contract  # noqa: E402
from core.model.flow import build_flow            # noqa: E402
from core.model.mapview import format_contract    # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("workbook", help="path to the model .xlsx")
    ap.add_argument("rules", help="path to the client's model_rules.yaml")
    ap.add_argument("--trace", metavar="SHEET!COORD", help="trace a cell to its driver leaves")
    args = ap.parse_args()

    rules = load_rules(args.rules)
    contract = read_contract(args.workbook, rules)
    print(format_contract(contract))

    if args.trace:
        sheet, _, coord = args.trace.partition("!")
        flow = build_flow(read_cells(args.workbook))
        result = flow.trace_precedents(sheet, coord)
        leaf_sheets = sorted({s for s, _ in result.leaves})
        print()
        print(f"Trace {args.trace} -> {len(result.leaves)} driver leaves on: {', '.join(leaf_sheets) or '(none)'}")
        if result.dynamic:
            print(f"  ({len(result.dynamic)} cells with dynamic/unresolved refs — trace incomplete there)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
