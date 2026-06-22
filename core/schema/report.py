"""Generate a budget-logic overview (`<client>_model_logic.md`) from a loaded model schema.

The win-condition artifact of the model-building pillar: a clean, no-fluff overview of how a model
is built — its 3 pillars (inputs / proforma / statements), the assumption sections, the line
inventory, the lineage of key outputs back to their driver inputs, and a model-health scan
(orphans / broken refs). Schema-derived, so it reflects exactly what the loader found.
"""
from __future__ import annotations

import sqlite3

from core.schema import trace_input_leaves, validate

# output lines we try to trace back to their drivers (matched case-insensitively, first hit)
KEY_OUTPUTS = ["Net profit", "EBITDA", "Gross profit", "Revenue", "Ending Cash", "TOTAL ASSETS"]


def _q(conn, sql, *a):
    return conn.execute(sql, a).fetchall()


def model_logic_md(conn: sqlite3.Connection) -> str:
    (name, ccy, start, horizon) = _q(conn, "SELECT name, base_ccy, start_date, horizon_months FROM model")[0]
    n = {t: _q(conn, f"SELECT COUNT(*) FROM {t}")[0][0]
         for t in ("section", "input", "line", "line_formula", "line_dependency")}
    by_pillar = dict(_q(conn, "SELECT pillar, COUNT(*) FROM section GROUP BY pillar"))
    out = [f"# {name} — budget logic (schema-derived)", ""]
    out += [f"*Generated from `core/schema`. Currency {ccy}; start {start}; horizon {horizon} months.*", ""]
    out += ["## Structure — 3 pillars",
            f"- **Inputs** (Pillar 1): {by_pillar.get('input', 0)} assumption sections, {n['input']} inputs.",
            f"- **ProForma + calc** (Pillar 2): {by_pillar.get('proforma', 0)} sheet(s), engine lines.",
            f"- **Statements** (Pillar 3): {by_pillar.get('statement', 0)} sheet(s).",
            f"- {n['line']} lines, {n['line_formula']} with formulas, {n['line_dependency']} dependency edges.", ""]

    # Pillar 1 — assumption sections → groups → a few inputs
    out += ["## Pillar 1 — Input assumptions"]
    for (sid, title) in _q(conn, "SELECT section_id, title FROM section WHERE pillar='input' ORDER BY ord"):
        inputs = _q(conn,
                    "SELECT i.label, i.unit, iv.value FROM input i JOIN grp g ON i.group_id=g.group_id "
                    "JOIN input_value iv ON iv.input_id=i.input_id AND iv.scenario_id=1 "
                    "WHERE g.section_id=? ORDER BY i.input_id", sid)
        if not inputs:
            continue
        out.append(f"- **{title}** ({len(inputs)} inputs)")
        for label, unit, val in inputs[:6]:
            v = "" if val is None else f" = {val:g}"
            out.append(f"    - {label}{v} {unit or ''}".rstrip())
        if len(inputs) > 6:
            out.append(f"    - …(+{len(inputs) - 6} more)")
    out.append("")

    # Pillars 2-3 — line inventory per sheet, with the subtotal/total skeleton
    out += ["## Pillars 2-3 — line inventory"]
    for (sid, title, pillar) in _q(conn, "SELECT section_id, title, pillar FROM section "
                                   "WHERE pillar IN ('proforma','statement') ORDER BY ord"):
        lines = _q(conn, "SELECT label, role FROM line WHERE section_id=? ORDER BY ord", sid)
        heads = [lbl for lbl, role in lines if role == 'header'][:8]
        out.append(f"- **{title}** [{pillar}] — {len(lines)} lines"
                   + (f"; sections: {', '.join(heads)}" if heads else ""))
    out.append("")

    # Lineage — trace key outputs back to driver inputs (only where edges connect)
    out += ["## Lineage — key outputs → driver inputs"]
    traced_any = False
    for kw in KEY_OUTPUTS:
        row = _q(conn, "SELECT line_id, label FROM line WHERE label LIKE ? ORDER BY line_id LIMIT 1", f"%{kw}%")
        if not row:
            continue
        lid, label = row[0]
        leaves = trace_input_leaves(conn, lid)
        if not leaves:
            continue
        traced_any = True
        names = [r[0] for r in _q(conn,
                 f"SELECT label FROM input WHERE input_id IN ({','.join('?'*len(leaves))})", *leaves)]
        out.append(f"- **{label}** ← {len(leaves)} driver inputs: " + ", ".join(names[:8])
                   + (f", …(+{len(names)-8})" if len(names) > 8 else ""))
    if not traced_any:
        out.append("- *(lineage not resolvable — this model's input column layout differs from the "
                   "loader's J/F/G/H assumption; structure loads but input-edges don't connect)*")
    out.append("")

    # Validation
    v = validate(conn)
    out += ["## Model health"]
    out.append(f"- Orphaned inputs (no line uses them): **{len(v['orphan_inputs'])}**"
               + (f" — e.g. {', '.join(l for _, l, _ in v['orphan_inputs'][:5])}" if v['orphan_inputs'] else ""))
    out.append(f"- Dead proforma lines (nothing references): **{len(v['orphan_lines'])}**"
               + (f" — e.g. {', '.join(l for _, l, _ in v['orphan_lines'][:5])}" if v['orphan_lines'] else ""))
    out.append(f"- Broken-ref (`#REF!`) lines: **{len(v['broken_formulas'])}**"
               + (f" — e.g. {', '.join(l for _, l, _ in v['broken_formulas'][:5])}" if v['broken_formulas'] else ""))
    out.append("")
    return "\n".join(out)
