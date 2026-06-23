"""Reflow the ProForma into the skill-outline order: VOLUMES & DRIVERS first, then Revenue → COGS
→ OPEX → below-EBITDA → working-capital/financing rolls. Same permutation+remap discipline as the
Inputs reflow, but the ProForma has INTERNAL relative refs (=C5+C9) and is referenced by the
statements (=ProForma!C44), so the remap is context-aware:

  • on ProForma: rewrite BARE internal row-refs (sheet-qualified refs ' Inputs'!/HR!/Revenue_Inputs!
    are left, including sheet-qualified ranges like Revenue_Inputs!$D$2:$D$31);
  • on IS/CF/BS(+_Y): rewrite ProForma!<cell> row-refs only.

Comprehensive gate: every relocated formula must reference the SAME logical rows after the move —
the multiset of referenced-row LABELS is preserved (catches any missed/mis-remapped ref). With no
recalc engine this label-isomorphism + the balance oracle are the value guarantee. Run after the
Inputs reflow (build_model_v5 calls it). Rewrites farada_model_v5.xlsx in place.
"""
from __future__ import annotations

import re

from openpyxl.worksheet.formula import ArrayFormula

SHEET = "ProForma"
STMTS = ("IS", "CF", "BS", "IS_Y", "CF_Y", "BS_Y")
NCOLS = 62  # A..BJ (months)

# new block order (old-sheet inclusive ranges): HEAD · DRIVERS · REVENUE · COGS · OPEX · BELOW · ROLLS
BLOCKS = [(1, 2), (63, 83), (4, 22), (24, 41), (85, 114), (120, 139), (143, 155)]

# a cell or range, optionally sheet-qualified (group 'q' present ⇒ external, leave it)
TOKEN = re.compile(r"(?P<q>'[^']*'!|[A-Za-z_][A-Za-z0-9_]*!)?"
                   r"(?P<ref>\$?[A-Z]{1,3}\$?\d+(?::\$?[A-Z]{1,3}\$?\d+)?)")
PFREF = re.compile(r"ProForma!(\$?[A-Z]{1,3}\$?)(\d+)(?::(\$?[A-Z]{1,3}\$?)(\d+))?")


def _ft(c):
    v = c.value
    return v.text if isinstance(v, ArrayFormula) else v


def _internal_rows(formula):
    """Rows referenced by BARE (ProForma-internal) refs in a formula."""
    out = set()
    if not isinstance(formula, str):
        return out
    for m in TOKEN.finditer(formula):
        if m.group("q") is None:
            out.update(int(d) for d in re.findall(r"\d+", m.group("ref")))
    return out


def _remap_internal(formula, o2n):
    if not isinstance(formula, str):
        return formula
    def repl(m):
        if m.group("q") is not None:
            return m.group(0)                       # external ref — leave
        ref = re.sub(r"\d+", lambda d: str(o2n.get(int(d.group()), int(d.group()))), m.group("ref"))
        return m.group(0)[: -len(m.group("ref"))] + ref
    return TOKEN.sub(repl, formula)


def _remap_pfrefs(formula, o2n):
    if not isinstance(formula, str):
        return formula
    def repl(m):
        s = f"ProForma!{m.group(1)}{o2n.get(int(m.group(2)), int(m.group(2)))}"
        if m.group(3):                              # range end (same sheet, bare col+row)
            s += f":{m.group(3)}{o2n.get(int(m.group(4)), int(m.group(4)))}"
        return s
    return PFREF.sub(repl, formula)


def reflow(wb):
    pf = wb[SHEET]
    snap = {r: [(pf.cell(r, c).value, pf.cell(r, c)._style) for c in range(1, NCOLS + 1)]
            for r in range(1, pf.max_row + 1)}
    label_old = {r: pf.cell(r, 1).value for r in snap}

    # plan: assign new rows block-by-block with a spacer before each (except HEAD)
    o2n, plan, nr = {}, [], 0
    for i, (s, e) in enumerate(BLOCKS):
        if i:
            nr += 1; plan.append((nr, None))
        for old in range(s, e + 1):
            nr += 1; o2n[old] = nr; plan.append((nr, old))
    last = nr

    # gate part 1: every internally-referenced ProForma row must be relocated
    refd = set()
    for r in snap:
        refd |= _internal_rows(_ft(pf.cell(r, 3)))
    for sn in STMTS:
        for row in wb[sn].iter_rows():
            for c in row:
                t = _ft(c)
                if isinstance(t, str):
                    refd |= {int(m.group(2)) for m in PFREF.finditer(t)}
    missing = sorted((refd & set(snap)) - set(o2n))
    assert not missing, f"referenced ProForma rows dropped by the reflow: {missing}"

    # reset the working region clean, then write the plan, remapping each moved formula's internals
    maxr, maxc = pf.max_row, max(NCOLS, pf.max_column)
    for r in range(1, maxr + 1):
        for c in range(1, maxc + 1):
            cell = pf.cell(r, c); cell.value = None; cell.style = "Normal"
    for nr, old in plan:
        if old is None:
            continue
        for c, (val, st) in enumerate(snap[old], start=1):
            cell = pf.cell(nr, c)
            cell.value = _remap_internal(val, o2n) if isinstance(val, str) and val.startswith("=") else val
            cell._style = st
    if maxr > last:
        pf.delete_rows(last + 1, maxr - last)

    # remap ProForma!<cell> refs in the statements
    for sn in STMTS:
        for row in wb[sn].iter_rows():
            for c in row:
                t = _ft(c)
                if isinstance(t, str) and "ProForma!" in t:
                    c.value = _remap_pfrefs(t, o2n)

    # gate part 2: each relocated formula references the same logical rows (by label multiset)
    def labelset(formula, rowlabel):
        return sorted(str(rowlabel.get(r)) for r in _internal_rows(formula))
    label_new = {r: pf.cell(r, 1).value for r in range(1, pf.max_row + 1)}
    bad = []
    for old, new in o2n.items():
        old_f, new_f = _ft_snap(snap, old), _ft(pf.cell(new, 3))
        if isinstance(old_f, str) and old_f.startswith("="):
            if labelset(old_f, label_old) != labelset(new_f, label_new):
                bad.append((old, new, label_old.get(old)))
    assert not bad, f"formula ref-labels changed at: {bad[:6]}"
    print(f"  PF gate ✓ {len(o2n)} rows relocated; ref-label multisets preserved on all formulas")
    return o2n, last


def _ft_snap(snap, row):
    v = snap[row][2][0]  # col C value
    return v.text if isinstance(v, ArrayFormula) else v
