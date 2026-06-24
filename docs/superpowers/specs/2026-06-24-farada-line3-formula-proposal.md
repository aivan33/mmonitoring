# Proposal — proper Line‑3 SaaS formulas (Farada), anchored at col C = Jul‑2026

For manual application. Every formula is given for **col C (Jul‑2026, first month)** plus the **col D→
fill‑right** form. The bug you found: the Included and Overage measurement rows were *identical*
because a hardcoded `$J$71` (old avg row) no longer matched after the discount inputs moved avg to
`$J$76` — so neither got its real rate. Proper versions below.

## Input cells (current)
| Qty | Bundle S | Bundle M | Bundle L |
|---|---|---|---|
| Sensors / bundle | `$J$53` (100k) | `$J$54` (500k) | `$J$55` (1M) |
| Included meas / sensor / yr | `$J$58` (960) | `$J$59` (960) | `$J$60` (960) |
| List (overage) price €/meas | `$J$63` (0.03) | `$J$64` (0.025) | `$J$65` (0.02) |
| Plan tier discount | `$J$68` (10%) | `$J$69` (15%) | `$J$70` (20%) |
- Avg meas/sensor/yr `$J$76` (1200) · Overage ramp delay (months) `$J$79` (3) · Cloud cost €/meas
  `$J$131` (0.0016) · Hardware markup `$J$74` (10%).
- **Bookings:** `Revenue_Inputs` rows **12 (S) / 13 (M) / 14 (L)** = NEW bundles landing each *quarter*;
  col **B = the Jul‑2026 quarter** (currently blank → fill these or SaaS stays €0).

## 0 · Phasing primitive Φ_b — new bundles landing in month c
Spread a quarter's bookings over its 3 months (this is the `INT/MOD` the hardware lines already use).
For bundle b = Revenue_Inputs row N (12/13/14):
- **Col C (Jul‑26):** `=INT(Revenue_Inputs!B$N/3)+IF(MOD(Revenue_Inputs!B$N,3)>=1,1,0)`
- **Col D:** threshold `>=2`; **Col E:** `>=3`; **Col F:** next quarter (RI col **C**), `>=1`; … (the RI
  column advances every 3 months; the `>=k` threshold cycles 1→2→3).
- **Fill‑right one‑liner (optional, same formula every column)** — keys off the column index so you can
  drag it across C→BJ:
  `=INT(OFFSET(Revenue_Inputs!$A$N,0,1+INT((COLUMN()-3)/3))/3)+IF(MOD(OFFSET(Revenue_Inputs!$A$N,0,1+INT((COLUMN()-3)/3)),3)>=MOD(COLUMN()-3,3)+1,1,0)`

## 1 · Installed sensor base IB_b — cumulative (RECOMMENDED: one row per bundle)
This is the key simplification: accumulate sensors **once**, then every recurring line is a clean
`IB × rate` (no per‑line accumulation → no double‑counting, the class of bug you hit).
- **Col C:** `=Φ_S(C)*$J$53`  · (M `*$J$54`, L `*$J$55`)
- **Col D→:** `=C{IB_S}+Φ_S(D)*$J$53`  (prior column + this month's new sensors)

## 2 · Subscription revenue (recurring) — a LEVEL on the installed base
Plan rate €/sensor/yr = included × list × (1−discount). **Do NOT accumulate** (IB already is).
- **Per bundle, any col c:** `=IB_S(c)*$J$58*$J$63*(1-$J$68)/12`  (M: `$J$59,$J$64,$J$69` · L: `$J$60,$J$65,$J$70`)
- **Subtotal:** `=Sub_S+Sub_M+Sub_L`

## 3 · Overage revenue (beyond the included quota) — ramp‑delayed
- **Gross per bundle (undelayed), col c:** `=IB_S(c)*MAX(0,$J$76-$J$58)*$J$63/12`  (M/L analogous)
- **Gross subtotal:** `=OvG_S+OvG_M+OvG_L`
- **Displayed (delayed) subtotal, col c:** `=IF((COLUMN()-3)<$J$79,0,OFFSET({OvG_subtotal cell this col},0,-$J$79))`
  - Cols C…(delay−1): **0** (clients aren't over‑using yet); from month = delay: equals the gross
    subtotal **`$J$79` months earlier** (exact per‑cohort ramp, because IB is cumulative).

## 4 · Measurements (count) — Included + Overage = clean total
- **Included, col c:** `=IB_S(c)*$J$58/12+IB_M(c)*$J$59/12+IB_L(c)*$J$60/12`
- **Overage — gross (helper), col c:** `=IB_S(c)*MAX(0,$J$76-$J$58)/12+IB_M(c)*MAX(0,$J$76-$J$59)/12+IB_L(c)*MAX(0,$J$76-$J$60)/12`
- **Overage — displayed (delayed), col c:** `=IF((COLUMN()-3)<$J$79,0,OFFSET({Overage‑gross cell this col},0,-$J$79))`
- **Total (clean sum):** `=Included + Overage‑displayed`
  - This is the fix for both symptoms: Included ≠ Overage (different rates), and the total is a literal
    `=C{incl}+C{overage}` — the ramp delay lives **inside** the Overage row, not on the total.

## 5 · Cloud COGS (SaaS) — measurement‑driven
- **Col c:** `=Total measurements(c) * $J$131`  → SaaS GM falls out as `(Sub+Overage − Cloud)/(Sub+Overage)`.
  *(With the bug, the total ≈ 2×avg so cloud COGS was ~2× too high — this corrects it.)*

## 6 · Bundle headline price (annual, for the pricing view) — your formula
Hardware (one‑time) + plan (recurring), per bundle:
`= (Σ chip+pkg+test+asic per sensor) × $J$5x × (1+$J$74)  +  $J$5(8/9/0) × $J$5x × $J$6(3/4/5) × (1−$J$6(8/9/0))`
- Bundle S: hardware `(chip…asic)*$J$53*(1+$J$74)` + plan `$J$58*$J$53*$J$63*(1-$J$68)`.

## Minimal‑change alternative (keep the current rows, no IB rows)
If you'd rather patch the existing Included/Overage/total cells in place, inline the cumulative phasing
on each line (accumulate off the row's own prior column):
- **Included (row 17) — Col C:** `=Φ_S(C)*$J$53*$J$58/12+Φ_M(C)*$J$54*$J$59/12+Φ_L(C)*$J$55*$J$60/12`
  · **Col D→:** `=C17+Φ_S(D)*$J$53*$J$58/12+…`
- **Overage‑gross (helper) — Col C:** `=Φ_S(C)*$J$53*MAX(0,$J$76-$J$58)/12+…` · **Col D→:** `=C{gross}+…`
- **Overage‑displayed:** `=IF((COLUMN()-3)<$J$79,0,OFFSET(C{gross},0,-$J$79))`
- **Total (row 16):** `=C17+C{overage‑displayed}`
- The one‑word fix vs today: Included uses **`$J$58`** (included), Overage uses **`MAX(0,$J$76-$J$58)`** —
  not both `$J$76`.

## Notes
- **Anchor at col C, accumulate from D.** Level rows (subscription, gross overage off IB) are identical
  every column; only IB and the cohort accumulators need the C‑vs‑D split.
- **Recognition basis** unchanged: subscription straight‑line over the year (the `/12` on a cumulative
  base), overage monthly as used, both on the installed base; the ramp delay shifts overage right by
  `$J$79` months.
- The IB‑based layout (§1‑5) is the cleaner "new version"; it removes the per‑line accumulation that
  caused the stale‑ref and double‑count bugs.
