"""CLI: render every spec in ``clients/<client>/chart_specs/`` for a given anchor month.

Usage:
    python scripts/build_charts.py <client> <YYYY-MM> [--only chart_id]

Outputs land in ``clients/<client>/charts/<YYYY-MM>/``.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
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


def _load_client_config(client: str) -> dict:
    config_path = _REPO / "clients" / client / "config.yaml"
    if not config_path.exists():
        raise SystemExit(f"error: no config.yaml for client {client!r}")
    return yaml.safe_load(config_path.read_text()) or {}


def _require_use_case(cfg: dict, client: str, required: str) -> None:
    use_cases = cfg.get("use_cases") or []
    if required not in use_cases:
        raise SystemExit(
            f"error: client {client!r} doesn't subscribe to use_case "
            f"{required!r} (use_cases={use_cases}). Add it to "
            f"clients/{client}/config.yaml or run a different script."
        )


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

    cfg = _load_client_config(args.client)
    _require_use_case(cfg, args.client, "charts")

    spec_dir = _REPO / "clients" / args.client / "chart_specs"
    if not spec_dir.exists():
        print(f"error: no chart_specs directory at {spec_dir.relative_to(_REPO)}",
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
    brand = cfg.get("brand", {}) or {}

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

    # Build index.html browsing the rendered charts.
    if rendered:
        _write_index_html(out_dir, args.client, args.period)
        print(f"  index: {(out_dir / 'index.html').relative_to(_REPO)}")

    return 1 if failed else 0


def _write_index_html(out_dir: Path, client: str, period: str) -> None:
    """Contact-sheet view: just the rendered PNGs in a clean responsive grid.
    No titles, no metadata, no badges — designed for visual review and
    drag-and-drop into a slide deck."""
    pngs = sorted(out_dir.glob("*.png"))
    cards = "\n".join(
        f'    <a href="{html.escape(p.name)}" class="card">'
        f'<img src="{html.escape(p.name)}" alt=""></a>'
        for p in pngs
    )
    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(client)} {html.escape(period)}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, "Helvetica Neue", Helvetica, Arial, sans-serif;
      background: #F5F2ED;
      padding: 32px;
      min-height: 100vh;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(560px, 1fr));
      gap: 24px;
      max-width: 1600px;
      margin: 0 auto;
    }}
    .card {{
      display: block;
      background: #fff;
      border-radius: 8px;
      padding: 16px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05),
                  0 4px 16px rgba(0, 0, 0, 0.04);
      transition: box-shadow 0.15s ease;
    }}
    .card:hover {{
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08),
                  0 8px 24px rgba(0, 0, 0, 0.06);
    }}
    .card img {{
      display: block;
      width: 100%;
      height: auto;
    }}
  </style>
</head>
<body>
  <div class="grid">
{cards}
  </div>
</body>
</html>
"""
    (out_dir / "index.html").write_text(page)


if __name__ == "__main__":
    sys.exit(main())
