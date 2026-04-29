"""CLI: render every spec in ``specs/<client>/`` for a given anchor month.

Usage:
    python scripts/build_charts.py <client> <YYYY-MM> [--only chart_id]

Outputs land in ``clients/<client>/charts/<YYYY-MM>/``.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import yaml

# Make the repo root importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.charts.render import render
from core.charts.spec import SpecValidationError, load_spec


_REPO = Path(__file__).resolve().parent.parent


def _parse_anchor(s: str) -> dt.date:
    parts = s.split("-")
    if len(parts) != 2:
        raise ValueError(f"period must be YYYY-MM, got {s!r}")
    year, month = int(parts[0]), int(parts[1])
    return dt.date(year, month, 1)


def _client_brand(client: str) -> dict:
    config_path = _REPO / "clients" / client / "config.yaml"
    if not config_path.exists():
        return {}
    cfg = yaml.safe_load(config_path.read_text())
    return cfg.get("brand", {}) or {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Render charts for a client.")
    parser.add_argument("client")
    parser.add_argument("period", help="anchor month, YYYY-MM")
    parser.add_argument("--only", dest="only", default=None,
                        help="render only the spec with this chart_id")
    args = parser.parse_args()

    try:
        anchor = _parse_anchor(args.period)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    spec_dir = _REPO / "specs" / args.client
    if not spec_dir.exists():
        print(f"error: no specs directory for client {args.client!r}",
              file=sys.stderr)
        return 1

    spec_files = sorted(spec_dir.glob("*.json"))
    if args.only:
        spec_files = [p for p in spec_files if p.stem == args.only]
        if not spec_files:
            print(f"error: no spec named {args.only!r} in {spec_dir}",
                  file=sys.stderr)
            return 1

    out_dir = _REPO / "clients" / args.client / "charts" / args.period
    brand = _client_brand(args.client)

    rendered = 0
    failed = 0
    for spec_path in spec_files:
        try:
            spec = load_spec(spec_path)
        except SpecValidationError as exc:
            print(f"  ✗ {spec_path.name}: {exc}", file=sys.stderr)
            failed += 1
            continue
        try:
            png, sidecar = render(spec, anchor=anchor, brand=brand, out_dir=out_dir)
            tag = "[platform]" if spec.is_platform else ""
            print(f"  ✓ {spec.chart_id} {tag} → {png.relative_to(_REPO)}")
            rendered += 1
        except NotImplementedError as exc:
            print(f"  - {spec.chart_id}: skipped ({exc})", file=sys.stderr)
        except Exception as exc:
            print(f"  ✗ {spec.chart_id}: {type(exc).__name__}: {exc}",
                  file=sys.stderr)
            failed += 1

    print(f"\n{args.client} {args.period}: rendered {rendered}, failed {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
