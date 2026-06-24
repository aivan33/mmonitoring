# Spec — v8: clean the revenue section once and for all (no hardcoded magic numbers)

Promote v7→v8 and rebuild the Line‑3 SaaS revenue section to the proper, input‑driven structure
(per `2026-06-24-farada-line3-formula-proposal.md`), and move the **yield curve + sensors‑per‑wafer**
out of hardcoded ProForma literals into **Inputs**. The overage ramp delay is *already* the input
`$J$79` — only its presentation needs un‑confusing.

## What's hardcoded today (to fix)
- **Sensors per wafer** = `4000` (literal in the ProForma yield calc row).
- **Yield** = `=IF(C8>=4000000,0.95,IF(C8>=1000000,0.9,IF(C8>=100000,0.82,IF(C8>=10000,0.73,0.7))))` —
  hardcoded thresholds *and* values. Should cascade off an Input staging table, exactly like the
  cost‑of‑sales curves already do (`IF(run-rate>=' Inputs'!$F$rung,' Inputs'!$J$rung,…)`).
- **Measurements Included = Overage bug** (stale `$J$71`→avg moved to `$J$76`) and the **non‑clean total**.
- The `-3` in the overage‑delay guard `IF((COLUMN()-3)<$J$79,…)` is the **col‑C anchor**, not the delay
  (the delay is `$J$79`) — express it via the month index so it's unambiguous.

## Architecture decisions
- **Installed sensor base is the single accumulator.** Add per‑bundle `Installed base (cumulative
  sensors)` rows; every recurring SaaS line becomes a clean `IB × rate` (subscription, overage,
  measurements) — no per‑line accumulation → removes the bug class (stale ref, double count).
- **Yield staged like the cost curves.** New Input sub‑group `Sensors per wafer` (single) + `Yield
  (staged by run‑rate)` (6 rungs: thresholds col F, values col J), placed in **III. PRODUCTION** near
  the wafer cost. The ProForma yield row cascades off it; chip = wafer ÷ spw ÷ yield (unchanged shape).
- **No value drift.** Seed the yield Input with today's curve (0.70 / 0.73 / 0.82 / 0.90 / 0.95 at
  run‑rate 1 / 10k / 100k / 1M / 4M) and spw=4000 → chip €/sensor identical; revenue rebuild is
  value‑equivalent except the Included≠Overage fix (which corrects cloud COGS, intended).
- **v7 in place until green, then `git mv` → v8.**

## Dependency note (ref renumbering)
Adding yield Inputs in PRODUCTION shifts the `$J$` numbering of rows *below* it (OPEX/OTHER). The SaaS
revenue inputs (`J53–79`) sit *above* PRODUCTION cost rows, so they're unaffected. The Inputs reflow's
`remap_refs` + equivalence gate handle the shift; the revenue rebuild resolves all input rows **by
label** (never hardcoded) so it's robust.

## Tasks
- [ ] **V1 — yield/spw as Inputs.** Add `Sensors per wafer` + `Yield (staged by run‑rate)` rungs to the
  `reflow_inputs` LAYOUT (III. PRODUCTION) + seed values; rebuild the ProForma yield row to cascade off
  the Input rungs and spw to read the Input. *Verify:* yield row references `' Inputs'!$F/$J` (no
  literals); chip €/sensor unchanged vs v7; balance oracle 0.
- [ ] **V2 — installed‑base foundation.** Add per‑bundle `Installed base (cumulative sensors)` rows
  (Φ_b × sensors_b, accumulated). *Verify:* IB cumulative & monotonic; col C = first‑month base.
- [ ] **V3 — subscription + overage off IB.** Subscription = `IB×incl×list×(1−disc)/12`; overage gross
  = `IB×MAX(0,avg−incl)×list/12`; overage displayed = ramp‑delayed (OFFSET `$J$79`, month‑index guard).
  *Verify:* subscription is a level (no double‑accumulate); overage delayed; revenue totals reconcile.
- [ ] **V4 — measurements clean.** Included = `Σ IB×incl/12`; Overage gross helper = `Σ IB×MAX(0,avg−
  incl)/12`; Overage displayed = delayed; **Total = Included + Overage (clean `=C{i}+C{o}`)**; cloud
  COGS = Total×`$J$131`. *Verify:* Included ≠ Overage; total is a literal sum; cloud COGS ≈ avg×cloud
  (not ~2×); SaaS GM ≈ 90%.
- [ ] **V5 — verify + promote.** Balance oracle 0, schema broken=0, no #REF!, full pytest, regenerate
  `model_logic.md`; then `git mv` build/verify → v8, update paths/tests.

### Checkpoint — after V1 (yield) and again after V4 (revenue), before promotion.

## Risks
| Risk | Mitigation |
|---|---|
| Adding Inputs shifts J‑refs and breaks formulas | reflow remap + resolved‑label equivalence gate; revenue rebuild resolves inputs by label |
| Revenue restructure (IB rows) shifts statement refs | insert+remap machinery (proven in D5b/measurement split); label‑based downstream |
| Yield Input seeded wrong → chip €/sensor drifts | seed with today's exact curve; assert chip unchanged vs v7 |
| Big build at once | slice V1→V4 with oracle gate + checkpoint after each |

## Open questions
1. **Installed‑base rows** — add explicit per‑bundle IB rows (recommended; cleanest), or inline the
   accumulation in each line (fewer rows, keeps today's shape)?
2. **Yield curve values** — keep today's 0.70/0.73/0.82/0.90/0.95, or recalibrate while we're here?
3. Promote to **v8** at the end of this pass, or stay on v7 until you've also reworked OPEX/other?
