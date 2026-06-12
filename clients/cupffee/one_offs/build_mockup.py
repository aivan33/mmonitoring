"""Low-fidelity HTML mockup of the Cupffee monthly deck.

Reads the month's `slides.md` (single source of truth for slide text),
embeds the rendered chart PNGs per a slide->charts map, and drops dashed
placeholders for the table / external-BI slides we don't render. Output is
a single scrollable HTML file for review — NOT a production deck.

Usage:  python clients/cupffee/one_offs/build_mockup.py [YYYY-MM]
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

CLIENT_DIR = Path(__file__).resolve().parent.parent  # clients/cupffee

# Which rendered charts sit on which slide (chart-only or chart+caption slides).
# Slides not listed are either text slides or table/external-BI slides
# (rendered elsewhere) -> shown as a dashed placeholder.
SLIDE_CHARTS: dict[int, list[str]] = {
    2: ["kpi_gross_profit_mtd.png", "kpi_cash_balance_mtd.png",
        "revenue_act_pp_bp_2026.png", "kpi_net_vs_gross_burn.png"],
    3: ["cash_breakdown_rolling.png", "cash_balances_rolling.png"],
    5: ["revenue_dynamics_2025_2026.png", "sales_by_channel_ytd.png",
        "sales_by_channel_mtd.png"],
}

# Lines that are production directions, not audience-facing slide content.
_NOTE_PREFIXES = (
    "No body text", "Slide carries", "Body text below", "(Static methodology",
)


def _render_body(lines: list[str]) -> str:
    """Tiny markdown-ish -> HTML for the slide body. Handles bullets,
    muted production notes, sub-labels, and paragraphs."""
    out: list[str] = []
    bullets: list[str] = []

    def flush_bullets() -> None:
        if bullets:
            items = "".join(f"<li>{html.escape(b)}</li>" for b in bullets)
            out.append(f"<ul>{items}</ul>")
            bullets.clear()

    for i, raw in enumerate(lines):
        line = raw.rstrip()
        if not line.strip():
            flush_bullets()
            continue
        if line.lstrip().startswith("- "):
            bullets.append(line.lstrip()[2:])
            continue
        flush_bullets()
        if any(line.startswith(p) for p in _NOTE_PREFIXES):
            out.append(f'<p class="note">{html.escape(line)}</p>')
            continue
        # short, period-less line followed by content -> treat as a sub-label
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        is_sublabel = (
            len(line) <= 60 and not line.endswith(".")
            and (nxt.startswith("- ") or nxt == "" )
            and not line.startswith("Title")
        )
        if is_sublabel:
            out.append(f'<h4 class="sublabel">{html.escape(line)}</h4>')
        else:
            out.append(f"<p>{html.escape(line)}</p>")
    flush_bullets()
    return "\n".join(out)


def _charts_html(num: int, charts_dir: Path) -> str:
    names = SLIDE_CHARTS.get(num, [])
    if names:
        imgs = []
        for n in names:
            if (charts_dir / n).exists():
                rel = f"../../charts/{charts_dir.name}/{n}"
                imgs.append(
                    f'<figure><img src="{rel}" alt="{n}">'
                    f'<figcaption>{n}</figcaption></figure>'
                )
        return f'<div class="charts">{"".join(imgs)}</div>' if imgs else ""
    return ""


def _placeholder_if_needed(num: int, body_lines: list[str]) -> str:
    """Dashed box for chart/table slides that have no rendered PNG of ours."""
    if num in SLIDE_CHARTS:
        return ""
    joined = " ".join(body_lines).lower()
    triggers = ("chart slide", "table", "carries the", "yearly",
                "kpi", "section divider", "divider", "4 charts", "2 charts")
    if any(t in joined for t in triggers):
        return ('<div class="placeholder">chart / table rendered separately '
                '(OLE-linked table or BI export) — shown here as a placeholder</div>')
    return ""


def build(month: str) -> Path:
    report_dir = CLIENT_DIR / "reports" / month
    charts_dir = CLIENT_DIR / "charts" / month
    slides_md = (report_dir / "slides.md").read_text(encoding="utf-8")

    # Split on "## Slide N — Title"
    blocks = re.split(r"^## (Slide [^\n]+)\n", slides_md, flags=re.M)
    # blocks[0] is the preamble; then alternating header, body
    deck_title = slides_md.splitlines()[0].lstrip("# ").strip()
    slides: list[tuple[int, str, list[str]]] = []
    for i in range(1, len(blocks), 2):
        header = blocks[i].strip()
        body = blocks[i + 1] if i + 1 < len(blocks) else ""
        body = body.split("\n---", 1)[0]
        m = re.match(r"Slide (\d+)\s*[—-]\s*(.*)", header)
        num = int(m.group(1)) if m else 0
        title = m.group(2).strip() if m else header
        slides.append((num, title, body.splitlines()))

    cards = []
    for num, title, body_lines in slides:
        charts = _charts_html(num, charts_dir)
        placeholder = _placeholder_if_needed(num, body_lines)
        body = _render_body(body_lines)
        cards.append(f"""
    <section class="slide">
      <header><span class="badge">Slide {num}</span>
        <h2>{html.escape(title)}</h2></header>
      {charts}{placeholder}
      <div class="body">{body}</div>
      <footer>{html.escape(deck_title)} &nbsp;·&nbsp; {num} / {len(slides)}</footer>
    </section>""")

    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(deck_title)} — review mockup</title>
<style>
  :root {{ --teal:#2A625E; --orange:#E67D5A; --ink:#1f2421; --mut:#8a948f; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:#eceae5; color:var(--ink);
         font:15px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; }}
  .topbar {{ background:var(--teal); color:#fff; padding:14px 24px; position:sticky;
            top:0; z-index:5; }}
  .topbar b {{ font-size:17px; }} .topbar span {{ opacity:.8; font-size:13px; }}
  .wrap {{ max-width:1040px; margin:24px auto; padding:0 16px; }}
  .slide {{ background:#fff; border:1px solid #d7d4cd; border-radius:8px;
           margin:0 0 22px; padding:26px 30px; box-shadow:0 1px 3px rgba(0,0,0,.06);
           min-height:540px; display:flex; flex-direction:column; }}
  .slide header {{ display:flex; align-items:center; gap:12px; border-bottom:2px solid var(--teal);
                  padding-bottom:8px; margin-bottom:14px; }}
  .badge {{ background:var(--teal); color:#fff; font-size:11px; font-weight:700;
           padding:3px 9px; border-radius:11px; letter-spacing:.04em; }}
  h2 {{ font-size:20px; margin:0; color:var(--teal); }}
  h4.sublabel {{ font-size:13px; text-transform:uppercase; letter-spacing:.05em;
                color:var(--orange); margin:12px 0 4px; }}
  .body {{ overflow:visible; }}
  .body p {{ margin:6px 0; }} .body ul {{ margin:4px 0 10px; padding-left:20px; }}
  .body li {{ margin:3px 0; }}
  p.note {{ color:var(--mut); font-style:italic; font-size:13px; }}
  .charts {{ display:flex; flex-wrap:wrap; gap:12px; margin-bottom:12px; justify-content:center; }}
  .charts figure {{ margin:0; flex:1 1 280px; max-width:340px; text-align:center; }}
  .charts img {{ width:100%; border:1px solid #e3e0d9; border-radius:4px; }}
  .charts figcaption {{ font-size:10px; color:var(--mut); margin-top:2px; }}
  .placeholder {{ border:2px dashed #c3bfb6; border-radius:6px; color:var(--mut);
                 text-align:center; padding:26px; margin-bottom:12px; font-size:13px;
                 background:#f6f4ef; }}
  footer {{ margin-top:auto; padding-top:8px; font-size:11px; color:var(--mut);
           border-top:1px solid #eee; }}
  @media print {{ body {{ background:#fff; }} .topbar {{ position:static; }}
                 .slide {{ page-break-after:always; box-shadow:none; }} }}
</style></head><body>
  <div class="topbar"><b>{html.escape(deck_title)}</b> &nbsp;
    <span>low-fidelity review mockup · charts are live renders · tables shown as placeholders</span></div>
  <div class="wrap">{''.join(cards)}</div>
</body></html>"""

    out = report_dir / "mockup.html"
    out.write_text(doc, encoding="utf-8")
    return out


if __name__ == "__main__":
    month = sys.argv[1] if len(sys.argv) > 1 else "2026-04"
    path = build(month)
    print(f"wrote {path}")
