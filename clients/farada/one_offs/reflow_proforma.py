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
Inputs reflow (build_model_v7 calls it). Rewrites farada_model_v7.xlsx in place.
"""
from __future__ import annotations

import re
from copy import copy

from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.formula import ArrayFormula

SHEET = "ProForma"
STMTS = ("IS", "CF", "BS", "IS_Y", "CF_Y", "BS_Y")
NCOLS = 62  # A..BJ (months)

# DRIVERS reordered (D2): header · sensors · run-rate · CoS/sensor (spw,yield,chip,pkg,sensor-test,
# final-test,ASIC) · measurements · secondary (blended ASP/cost, capacity, util, clients, expansion)
DRIVERS = [63, 64, 65, 66, 67, 82, 83, 69, 70, 71, 72, 73, 68, 74, 75, 76, 77, 78, 79, 80, 81]
# block order: HEAD · DRIVERS · REVENUE · COGS · OPEX · BELOW · ROLLS (ranges as (s,e); lists kept verbatim)
BLOCKS = [(1, 2), DRIVERS, (4, 22), (24, 41), (85, 114), (120, 139), (143, 155)]

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
    for i, blk in enumerate(BLOCKS):
        if i:
            nr += 1; plan.append((nr, None))
        rows = range(blk[0], blk[1] + 1) if isinstance(blk, tuple) else blk
        for old in rows:
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


PF_SECTIONS = [
    ("WC DRIVERS & RATIOS", ["Receivable days (DSO)", "Payable days (DPO)",
                             "Current ratio", "Quick ratio", "Cash ratio"]),
    ("CASH FLOW", ["Operating activities", "Investing activities", "Financing activities"]),
    ("TAXATION", ["Tax expense (P&L)", "Tax payable (BS)"]),
    ("FUNDING", ["Equity round", "Debt draw", "Grants"]),
]


def add_proforma_sections(wb):
    """Complete the ProForma's skill-outline lower sections. The existing rolls ARE the balance
    sheet → relabel that header 'BALANCE SHEET (rolls)', then APPEND the remaining named sections
    (WC drivers & ratios · Cash Flow · Taxation · Funding) as blank-but-defined placeholders. Append
    only — no row-shift, no remap (nothing references rows past the rolls)."""
    pf = wb[SHEET]
    band_st = label_st = None
    for r in range(1, pf.max_row + 1):
        v = pf.cell(r, 1).value
        if isinstance(v, str) and "WORKING CAPITAL & FINANCING ROLLS" in v:
            band_st = pf.cell(r, 1)._style
            label_st = pf.cell(r + 1, 1)._style
            pf.cell(r, 1, "BALANCE SHEET (rolls)")._style = band_st
    nr = max(r for r in range(1, pf.max_row + 1) if pf.cell(r, 1).value is not None)
    for title, lines in PF_SECTIONS:
        nr += 2                                       # blank spacer + header
        pf.cell(nr, 1, title)._style = band_st
        for ln in lines:
            nr += 1
            pf.cell(nr, 1, "  " + ln)._style = label_st
    print("  PF sections: BALANCE SHEET + appended WC / Cash Flow / Taxation / Funding (blank-but-defined)")


def fix_run_rate(wb, FIRST=3, LAST=62):
    """D1 — replace the frozen `Total run-rate (sensors/yr) = SUM(C5:N7)` (identical in every column)
    with a real **LTM trailing-12-months** run-rate: for month m, Σ of the 3 sensor rows over the
    window [max(first, m-11) … m]. Drives the 6-point cost curve off realised scale (early months
    partial → lower volume → higher unit cost, which is correct). Label-based (survives the reorder)."""
    pf = wb[SHEET]
    L = {pf.cell(r, 1).value.strip(): r for r in range(1, pf.max_row + 1)
         if isinstance(pf.cell(r, 1).value, str) and pf.cell(r, 1).value.strip()}
    rr = L["Total run-rate (sensors/yr)"]
    s1, s3 = L["Sensors Line 1 (monthly)"], L["Sensors Line 3 (monthly)"]
    for c in range(FIRST, LAST + 1):
        a, x = get_column_letter(max(FIRST, c - 11)), get_column_letter(c)
        pf.cell(rr, c, f"=SUM({a}{s1}:{x}{s3})")
    print(f"  D1: run-rate → LTM trailing-12 over sensor rows {s1}-{s3}")


def style_subtotals(wb, LAST=62):
    """Bold the ProForma sum/subtotal lines (a row whose formula is purely +-joined internal cell
    refs or a SUM range) so totals stand out from their indented leaf children — readability (E)."""
    pf = wb[SHEET]
    sub = re.compile(r"^=(SUM\([A-Z]+\d+:[A-Z]+\d+\)|[A-Z]+\d+(\+[A-Z]+\d+)+)$")
    n = 0
    for r in range(1, pf.max_row + 1):
        f = _ft(pf.cell(r, 3))
        if isinstance(f, str) and sub.match(f.replace(" ", "")):
            for c in [1] + list(range(3, LAST + 1)):
                cell = pf.cell(r, c)
                fo = cell.font
                cell.font = Font(name=fo.name, size=fo.size, bold=True, color=fo.color,
                                 italic=fo.italic)
            n += 1
    print(f"  style: bolded {n} ProForma subtotal lines")


def add_measurement_children(wb, FIRST=3, LAST=62):
    """Split 'Measurements Line 3 (monthly)' into two children — Included (subscription) and Overage
    (beyond subscription) — keeping the total (= their sum). Each column's total has one $J$71 (avg
    meas/sensor/yr) per bundle S/M/L; the Included child swaps each for the bundle's included-meas
    input (J58/59/60), the Overage child for MAX(0, J71 − included). Inserts 2 rows + shifts refs."""
    pf = wb[SHEET]
    R = next(r for r in range(1, pf.max_row + 1)
             if isinstance(pf.cell(r, 1).value, str) and "Measurements Line 3" in pf.cell(r, 1).value)
    totals = {c: _ft(pf.cell(R, c)) for c in range(FIRST, LAST + 1)}
    lbl_st = pf.cell(R, 1)._style
    val_st = {c: pf.cell(R, c)._style for c in range(FIRST, LAST + 1)}

    pf.insert_rows(R + 1, 2)
    o2n = {r: (r if r <= R else r + 2) for r in range(1, pf.max_row + 3)}
    for row in pf.iter_rows():
        for cell in row:
            t = _ft(cell)
            if isinstance(t, str) and t.startswith("="):
                cell.value = _remap_internal(t, o2n)
    for sn in STMTS:
        for row in wb[sn].iter_rows():
            for cell in row:
                t = _ft(cell)
                if isinstance(t, str) and "ProForma!" in t:
                    cell.value = _remap_pfrefs(t, o2n)

    def nth_sub(f, repls):
        it = iter(repls)
        return re.sub(r"' Inputs'!\$J\$71", lambda m: next(it), f)

    def reaccum(f, child):
        # the source total self-accumulates off '={prevcol}{R}+...' (cumulative installed base);
        # pasted into a child it must accumulate off the CHILD'S own prior column, not the total row
        # (D4 — else the total double-counts the prior month every step).
        return re.sub(rf"^=([A-Z]+){R}\+", rf"=\g<1>{child}+", f)

    INCL = ["' Inputs'!$J$58", "' Inputs'!$J$59", "' Inputs'!$J$60"]
    OVER = ["MAX(0,' Inputs'!$J$71-' Inputs'!$J$58)",
            "MAX(0,' Inputs'!$J$71-' Inputs'!$J$59)",
            "MAX(0,' Inputs'!$J$71-' Inputs'!$J$60)"]
    pf.cell(R + 1, 1, "    Included (subscription)")._style = lbl_st
    pf.cell(R + 2, 1, "    Overage (beyond subscription)")._style = lbl_st
    for c in range(FIRST, LAST + 1):
        x = get_column_letter(c)
        pf.cell(R + 1, c, reaccum(nth_sub(totals[c], INCL), R + 1))._style = val_st[c]
        pf.cell(R + 2, c, reaccum(nth_sub(totals[c], OVER), R + 2))._style = val_st[c]
        pf.cell(R, c, f"={x}{R + 1}+{x}{R + 2}")._style = val_st[c]   # total = Included + Overage
    print(f"  measurements: added Included + Overage children under row {R}")


def _phase(c, brow, FIRST=3):
    """Quarter-bookings phasing for ProForma column c and a Revenue_Inputs bundle row — the same
    INT/MOD spread the hardware/overage lines use (col C → quarter B, threshold 1; +1 per month)."""
    q = get_column_letter(2 + (c - FIRST) // 3)          # Revenue_Inputs quarter column (B = 2026 Q3)
    k = (c - FIRST) % 3 + 1                               # month-in-quarter threshold
    return f"(INT(Revenue_Inputs!{q}${brow}/3)+IF(MOD(Revenue_Inputs!{q}${brow},3)>={k},1,0))"


def add_subscription_lines(wb, FIRST=3, LAST=62):
    """D5b — add the Subscription (recurring) revenue block + a billings memo to the SaaS #3 group.
    Subscription accrues on the cumulative installed base at the discounted plan rate
    (included × list × (1−tier_discount)/12, per bundle) — like overage, but on the included quota.
    Billings is the per-period ANNUAL amount collected upfront (drives the deferred-revenue roll, D5e).
    SaaS #3 = Hardware + Subscription + Overage; the billings memo is excluded. Inserts 5 rows + remaps.
    Bundle inputs: sensors J53/54/55 · included J58/59/60 · list(=overage) J63/64/65 · discount J68/69/70."""
    pf = wb[SHEET]
    saas = next(r for r in range(1, pf.max_row + 1) if isinstance(pf.cell(r, 1).value, str)
                and "Hardware-enabled SaaS" in pf.cell(r, 1).value)
    overage = next(r for r in range(1, pf.max_row + 1) if isinstance(pf.cell(r, 1).value, str)
                   and "SaaS (overage" in pf.cell(r, 1).value)
    hw = saas + 1                                         # hardware subtotal (directly under SaaS #3)
    sub_st = pf.cell(overage, 1)._style                  # overage subtotal label style
    kid_st = pf.cell(overage + 1, 1)._style              # overage child label style
    sv = {c: pf.cell(overage, c)._style for c in range(FIRST, LAST + 1)}
    kv = {c: pf.cell(overage + 1, c)._style for c in range(FIRST, LAST + 1)}

    N = 5
    pf.insert_rows(overage, N)                           # insert the subscription block BEFORE overage
    o2n = {r: (r if r < overage else r + N) for r in range(1, pf.max_row + N + 1)}
    for row in pf.iter_rows():
        for cell in row:
            t = _ft(cell)
            if isinstance(t, str) and t.startswith("="):
                cell.value = _remap_internal(t, o2n)
    for sn in STMTS:
        for row in wb[sn].iter_rows():
            for cell in row:
                t = _ft(cell)
                if isinstance(t, str) and "ProForma!" in t:
                    cell.value = _remap_pfrefs(t, o2n)

    SUB, S_S, S_M, S_L, BILL = overage, overage + 1, overage + 2, overage + 3, overage + 4
    OVER = overage + N                                   # overage subtotal, shifted down
    pf.cell(SUB, 1, "  Subscription (recurring)")._style = sub_st
    pf.cell(S_S, 1, "    Bundle S")._style = kid_st
    pf.cell(S_M, 1, "    Bundle M")._style = kid_st
    pf.cell(S_L, 1, "    Bundle L")._style = kid_st
    pf.cell(BILL, 1, "  Subscription billings (annual, upfront — memo)")._style = sub_st
    BUNDLES = [(S_S, 12, 53, 58, 63, 68), (S_M, 13, 54, 59, 64, 69), (S_L, 14, 55, 60, 65, 70)]
    rate = lambda ir, pr, dr: f"' Inputs'!$J${ir}*' Inputs'!$J${pr}*(1-' Inputs'!$J${dr})"
    for c in range(FIRST, LAST + 1):
        x, p = get_column_letter(c), get_column_letter(c - 1)
        for (row, brow, sr, ir, pr, dr) in BUNDLES:      # subscription children — cumulative installed base
            add = f"{_phase(c, brow, FIRST)}*' Inputs'!$J${sr}*{rate(ir, pr, dr)}/12"
            pf.cell(row, c, f"={add}" if c == FIRST else f"={p}{row}+{add}")._style = kv[c]
        pf.cell(SUB, c, f"={x}{S_S}+{x}{S_M}+{x}{S_L}")._style = sv[c]
        bill = "+".join(f"{_phase(c, brow, FIRST)}*' Inputs'!$J${sr}*{rate(ir, pr, dr)}"
                        for (_, brow, sr, ir, pr, dr) in BUNDLES)        # per-period annual (upfront)
        pf.cell(BILL, c, f"={bill}")._style = sv[c]
        pf.cell(saas, c, f"={x}{hw}+{x}{SUB}+{x}{OVER}")._style = pf.cell(saas, c)._style
    print(f"  D5b: subscription block (rev {SUB}, children {S_S}-{S_L}, billings {BILL}); SaaS#3 = HW+Sub+Overage")


def cloud_cogs_measurement_driven(wb, FIRST=3, LAST=62):
    """D5d — replace the SaaS-COGS gross-margin plug (overage × (1−GM-target)) with a real
    measurement-driven cost: cloud COGS = total Line-3 measurements × cloud_cost/measurement. The
    measurements total already equals installed_base × avg/12 (D4), so this = installed × avg × cloud/12.
    GM becomes an OUTPUT (subscription + overage − cloud), not a plug. Supersedes the placeholder."""
    pf, inp = wb[SHEET], wb[" Inputs"]
    L = {pf.cell(r, 1).value.strip(): r for r in range(1, pf.max_row + 1)
         if isinstance(pf.cell(r, 1).value, str) and pf.cell(r, 1).value.strip()}
    usage, meas = L["Usage (cloud / compute)"], L["Measurements Line 3 (monthly)"]
    inrow = lambda pfx: next(r for r in range(1, inp.max_row + 1) if isinstance(inp.cell(r, 3).value, str)
                             and inp.cell(r, 3).value.strip().startswith(pfx))
    cloud, gm = inrow("Cloud / compute per measurement"), inrow("SaaS gross margin target")
    for c in range(FIRST, LAST + 1):
        pf.cell(usage, c, f"={get_column_letter(c)}{meas}*' Inputs'!$J${cloud}")
    inp.cell(cloud, 15, "← drives SaaS/cloud COGS = total measurements × this (SaaS GM is an output)")
    inp.cell(gm, 15, "← SUPERSEDED by measurement-driven cloud COGS (D5d); kept for reference")
    print(f"  D5d: cloud COGS = measurements(row {meas}) × cloud_cost(J{cloud}); 80% GM plug retired")


def rework_wc_rolls(wb, FIRST=3, LAST=62):
    """D5e — re-wire the working-capital rolls to the split SaaS streams (the 3-statement seam):
      • Trade receivables = (components + hardware) × (1−prepay) + overage, spread over DSO.
        Subscription is EXCLUDED (billed annually upfront → deferred, no receivable).
      • Deferred revenue = running balance: prior + subscription billings − subscription revenue
        (replaces the =overage×SAAS_ANN×6 proxy). The CF Δ-deferred then resolves subscription cash to
        the upfront billings. AP is unchanged (COGS TOTAL already includes the cloud COGS)."""
    pf, inp = wb[SHEET], wb[" Inputs"]
    L = {pf.cell(r, 1).value.strip(): r for r in range(1, pf.max_row + 1)
         if isinstance(pf.cell(r, 1).value, str) and pf.cell(r, 1).value.strip()}
    ar, dfr = L["Trade receivables (AR)"], L["Deferred revenue (SaaS annual)"]
    comp1, comp2, hwdev = (L["Components #1 - Low Volume"], L["Components #2 - High Volume"],
                           L["Hardware (device, cost + markup)"])
    sub, bill, ov = (L["Subscription (recurring)"],
                     L["Subscription billings (annual, upfront — memo)"], L["SaaS (overage, recurring)"])
    jrow = lambda pfx: next(r for r in range(1, inp.max_row + 1) if isinstance(inp.cell(r, 3).value, str)
                            and inp.cell(r, 3).value.strip().startswith(pfx))
    PREPAY, DSO, OBDEF = jrow("Hardware prepayment"), jrow("Receivable days"), jrow("Opening deferred revenue")
    for c in range(FIRST, LAST + 1):
        x, p = get_column_letter(c), get_column_letter(c - 1)
        pf.cell(ar, c, f"=(({x}{comp1}+{x}{comp2}+{x}{hwdev})*(1-' Inputs'!$J${PREPAY})"
                       f"+{x}{ov})/30*' Inputs'!$J${DSO}")
        pf.cell(dfr, c, (f"=' Inputs'!$J${OBDEF}+{x}{bill}-{x}{sub}" if c == FIRST
                         else f"={p}{dfr}+{x}{bill}-{x}{sub}"))
    print(f"  D5e: AR=(comp+hw)(1−prepay)+overage; deferred=running(billings−subscription)")
