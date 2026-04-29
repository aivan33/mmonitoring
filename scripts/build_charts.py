"""CLI: render every spec in ``specs/<client>/`` for a given anchor month.

Usage:
    python scripts/build_charts.py <client> <YYYY-MM> [--only chart_id]

Outputs land in ``clients/<client>/charts/<YYYY-MM>/``.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
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

    # Build index.html browsing the rendered charts.
    if rendered:
        _write_index_html(out_dir, args.client, args.period)
        print(f"  index: {(out_dir / 'index.html').relative_to(_REPO)}")

    return 1 if failed else 0


def _write_index_html(out_dir: Path, client: str, period: str) -> None:
    """Generate a static HTML browser for the rendered chart inventory."""
    entries: list[dict] = []
    for png in sorted(out_dir.glob("*.png")):
        sidecar = png.with_suffix(".json")
        meta: dict = {}
        if sidecar.exists():
            try:
                payload = json.loads(sidecar.read_text())
                spec = payload.get("spec", {})
                meta = {
                    "title": spec.get("title", png.stem),
                    "chart_type": spec.get("chart_type", "?"),
                    "source": spec.get("source", "?"),
                    "notes": spec.get("notes", ""),
                    "platform": payload.get("placeholder", False),
                }
            except Exception:
                pass
        entries.append({
            "id": png.stem,
            "png": png.name,
            "json": sidecar.name if sidecar.exists() else None,
            **meta,
        })

    html_body = "\n".join(_render_card(e) for e in entries)

    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(client)} — {html.escape(period)} charts</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: -apple-system, Helvetica, Arial, sans-serif;
           margin: 24px; color: #222; background: #fafafa; }}
    h1 {{ margin: 0 0 4px 0; font-size: 22px; }}
    .meta {{ color: #666; margin-bottom: 24px; font-size: 13px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 18px; }}
    .card {{ background: #fff; border: 1px solid #ddd; border-radius: 6px;
             padding: 14px; }}
    .card h3 {{ margin: 0 0 6px 0; font-size: 15px; }}
    .card .ids {{ font-size: 11px; color: #888; margin-bottom: 10px;
                  font-family: monospace; }}
    .card img {{ width: 100%; height: auto; border: 1px solid #eee; }}
    .card .notes {{ font-size: 12px; color: #555; margin-top: 8px;
                    line-height: 1.4; }}
    .badge {{ display: inline-block; padding: 1px 6px; border-radius: 3px;
              font-size: 10px; font-weight: 600; text-transform: uppercase;
              margin-right: 4px; vertical-align: middle; }}
    .badge.custom {{ background: #2A625E; color: #fff; }}
    .badge.platform {{ background: #888; color: #fff; }}
    .badge.type {{ background: #eee; color: #333; }}
  </style>
</head>
<body>
  <h1>{html.escape(client)} — {html.escape(period)}</h1>
  <p class="meta">{len(entries)} charts &middot;
    <a href=".">files in this directory</a></p>
  <div class="grid">
{html_body}
  </div>
</body>
</html>
"""
    (out_dir / "index.html").write_text(page)


def _render_card(entry: dict) -> str:
    title = html.escape(entry.get("title", entry["id"]))
    cid = html.escape(entry["id"])
    png = html.escape(entry["png"])
    src = entry.get("source", "custom")
    ctype = entry.get("chart_type", "")
    notes = html.escape(entry.get("notes", ""))
    json_link = (
        f' &middot; <a href="{html.escape(entry["json"])}">json</a>'
        if entry.get("json") else ""
    )
    return f"""    <div class="card">
      <h3>{title}</h3>
      <div class="ids">
        <span class="badge {src}">{html.escape(src)}</span>
        <span class="badge type">{html.escape(ctype)}</span>
        {cid}{json_link}
      </div>
      <a href="{png}"><img src="{png}" alt="{title}"></a>
      <p class="notes">{notes}</p>
    </div>"""


if __name__ == "__main__":
    sys.exit(main())
