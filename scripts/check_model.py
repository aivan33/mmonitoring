"""CLI: run the model verification gate on a workbook.

Recomputes the workbook with LibreOffice (the authoritative engine) and runs the
integrity gates configured in ``clients/<client>/model_gates.yaml``: no error
cells, BS check ~0, statements tie, subtotals foot. Optional warn-only passes add
the design-system format lint and the schema health scan.

Only **integrity** violations affect the exit code — format/health are warn-only
until the client models are brought fully to canon.

Exit codes: 0 = PASS (integrity clean), 1 = integrity violations, 2 = setup error.

Usage:
    python scripts/check_model.py <client> <workbook.xlsx> [--format] [--health] [--full]
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import openpyxl

from core.model.format_lint import lint
from core.model.integrity import load_gates, run_all
from core.model.recalc import SofficeNotFound, recalc

_MAX_SHOWN = 40


def _health_scan(client: str, wb_path: Path):
    """Schema health scan (orphans / dead lines / broken refs). Defensive: the
    loader expects a schema-conformant model, so callers treat failure as skip."""
    from core.schema import validate
    from core.schema.load import load_model

    conn = load_model(":memory:", str(wb_path), client, wb_path.stem)
    return validate(conn)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the model verification gate.")
    ap.add_argument("client")
    ap.add_argument("workbook", help="path to the model .xlsx")
    ap.add_argument("--format", action="store_true",
                    help="also run the design-system format lint (warn-only)")
    ap.add_argument("--health", action="store_true",
                    help="also run the schema health scan (warn-only)")
    ap.add_argument("--full", action="store_true", help="run every gate")
    args = ap.parse_args()
    do_format = args.format or args.full
    do_health = args.health or args.full

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

    print(f"check_model {args.client} {wb_path.name}")

    # --- Integrity (hard gate: sets the exit code) ---
    violations = run_all(wb, gates)
    if not violations:
        print("  integrity: PASS — no violations")
    else:
        for v in violations[:_MAX_SHOWN]:
            print(f"  integrity FAIL [{v.check}] {v.sheet}!{v.cell}: {v.detail}")
        if len(violations) > _MAX_SHOWN:
            print(f"  ... and {len(violations) - _MAX_SHOWN} more")
        print(f"  integrity: {len(violations)} violation(s): "
              f"{dict(Counter(v.check for v in violations))}")

    # --- Format lint (warn-only) — needs the source workbook (formulas + styles) ---
    if do_format:
        src = openpyxl.load_workbook(wb_path, data_only=False)
        fviol = lint(src, inputs_sheet=gates.get("inputs_sheet", " Inputs"))
        if not fviol:
            print("  format: clean")
        else:
            for v in fviol[:_MAX_SHOWN]:
                print(f"  format WARN [{v.rule}] {v.sheet}!{v.cell}: {v.detail}")
            if len(fviol) > _MAX_SHOWN:
                print(f"  ... and {len(fviol) - _MAX_SHOWN} more")
            print(f"  format: {len(fviol)} warning(s): "
                  f"{dict(Counter(v.rule for v in fviol))} (warn-only)")

    # --- Health scan (warn-only, defensive) ---
    if do_health:
        try:
            scan = _health_scan(args.client, wb_path)
            counts = {k: len(v) for k, v in scan.items()}
            print(f"  health: {counts} (warn-only)")
        except Exception as exc:  # noqa: BLE001 — the loader is structure-sensitive
            print(f"  health: skipped ({type(exc).__name__}: {exc})")

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
