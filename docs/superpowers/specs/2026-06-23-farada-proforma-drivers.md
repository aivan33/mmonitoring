# Spec — fix & polish the Farada ProForma Volume & Drivers

Review found real logic smells in the driver block. Diagnosis + plan below. Split into **mechanical**
fixes (do now, low-risk) and **economic** fixes (need decisions, tied to the SaaS placeholder).

## Diagnosis
1. **Run-rate is a constant bug.** `Total run-rate (sensors/yr)` is `=SUM(C5:N7)` in *every* column
   (the range never fills-right) → all 60 months get the first-year total, freezing the 6-point cost
   curve at one step. Doubly wrong: it's both forward-looking *and* constant.
2. **Driver order is messy.** Current: Sensors → run-rate → measurements → CoS/sensor → blended →
   capacity/util → clients/expansion → spw/yield. The **CoS/sensor curve is derived from the
   run-rate**, so it belongs *directly below* it; measurements come after; the rest are secondary.
3. **Yield + sensors-per-wafer are hardcoded ProForma rows**, not Inputs — contradicts the cost-
   assumptions slide, which lists yield as an assumption.
4. **Measurements/overage magnitude is wrong (~10M when a bundle lands).** Two causes:
   - **(a) Recurring lines use per-period BOOKINGS phasing, not the cumulative installed base.**
     `Included/Overage = Σ_bundle phased-bookings × sensors/bundle × meas/12` — `phased-bookings`
     counts *new* bundles that quarter, so the line spikes when a bundle is booked then falls to 0,
     instead of accruing on all live sensors. SaaS revenue (overage) has the same defect.
   - **(b) Subscription tiers are off:** included = 10/20/20 meas/sensor/yr vs avg = 1200 ⇒ ~99% is
     overage. One Bundle S = 100k × (1200−10)/12 ≈ 9.9M overage measurements/month.

### The measurement formulas (the detail requested)
```
Included (subscription) = Σ_b  phased(B$12/13/14) · sensors/bundle(J53/54/55) · included_b(J58/59/60) / 12
Overage  (beyond)       = Σ_b  phased(B$12/13/14) · sensors/bundle(J53/54/55) · MAX(0, avg(J71) − included_b)/12
Total                   = Included + Overage  ( = Σ_b phased · sensors · avg/12 )
```
`/12` annualises→monthly; `phased(N)= INT(N/3)+IF(MOD(N,3)>=m,1,0)` spreads a *quarter's bookings*
across its 3 months. **The bug:** for a recurring meter you must multiply by the **cumulative active
sensor base** (running Σ of bundles sold), not this period's new bookings.

## Plan

### Phase 1 — mechanical (low-risk, do now)
- [ ] **D1 — fix the run-rate** to a real per-month value. *(decision: method below.)* Per-column
  formula so it fills correctly. Acceptance: run-rate varies by month; the 6-pt cost curve steps as
  volume grows.
- [ ] **D2 — reorder drivers**: Sensors → **Run-rate → CoS/sensor (chip/pkg/sensor-test/final-test/
  ASIC + sensors-per-wafer + yield)** → Measurements (Total/Included/Overage) → secondary (Blended
  ASP/cost, Capacity, Utilisation, New clients, Expansion). Permutation + ref-remap, equivalence-gated.
- [ ] **D3 — yield + sensors-per-wafer as Inputs**: add to ` Inputs` III. PRODUCTION (cost-of-sales),
  per the cost-assumptions slide; the ProForma chip derivation reads them (replaces the literals).

### Phase 2 — economic (needs decisions; tied to the SaaS placeholder & CODEX review)
- [ ] **D4 — recurring base fix**: drive measurements + SaaS overage off the **cumulative installed
  sensor base** (running Σ of bundle sensors), not per-period bookings. Removes the spike.
- [ ] **D5 — subscription tiers**: re-set included-vs-avg so overage is a sane share (or make avg a
  per-bundle usage input). This is the SaaS-economics redesign CODEX is also asked to weigh in on.

### Checkpoint
Drivers read top-down logically; run-rate is per-month; cost curve steps with volume; yield is an
input; measurements track the installed base at believable magnitudes. Balance oracle + suite green.

## DECISIONS (2026-06-23)
- **Run-rate = LTM (trailing 12 months).** Per-column: `Σ sensors(rows 5-7) over [max(first, m-11) … m]`. *(D1 — done.)*
- **D3 — yield + sensors-per-wafer stay as ProForma calc rows** (not Inputs). `expose_yield` is the
  final form; treat D3 as done.
- **Sequence — D4 first (mechanical, oracle-backed), then D5** (economic redesign on top).
- **D5 = per-measurement (LLM-style) plan pricing, plan-heavy.** See agreed structure below.

## Agreed SaaS structure (D5) — per-measurement plan pricing
The unit of value is a **measurement** (a sensor emits `avg_meas ≈ 1,200`/yr, input 106). The model
already carries per-bundle inputs: sensors/bundle (2.3 · J37-39), included meas/sensor (2.4 · J41-43),
overage price €/meas (2.5 · J45-47), avg_meas (2.6 · J106), and a measurement cloud/usage cost
(3.7 · J102). The defect: the **included quota is billed at €0** (overage-only) — so there is no plan
revenue and ~99% is overage. The LLM analogy fixes this: the **plan** bills the included quota at a
**discounted** €/measurement (cheaper than the on-demand "API" overage rate); usage beyond included is
overage at the full rate. **Plan-heavy:** included is re-set to ≈80% of `avg_meas`, so overage is a
small top-up.

**Pricing (overage price 2.5 = the list / "API" €/measurement rate):**
- **3 tier discounts** (NEW inputs): S = 10%, M = 15%, L = 20% (bigger bundle → deeper discount).
  Sorted into REVENUE **right after 2.5** in the `LAYOUT` (not appended) — reflow renumbers + remaps,
  equivalence-gated.
- **Bundle (plan) price** (per the user's formula, per bundle):
  `bundle_price = hardware_cos × 1.10  +  included_meas/device × devices_in_bundle × list_price × (1 − tier_discount)`
  — hardware component = production cost × 1.10 (one-time at sale); plan component = the discounted
  included-measurement subscription.

**Recurring lines, all on the cumulative installed sensor base (monthly):**
- **Subscription (plan)** = `installed_base × included_meas × list_price × (1 − tier_discount) / 12`
- **Overage** = `installed_base × MAX(0, avg_meas − included_meas) × list_price / 12`
- **SaaS COGS** = `installed_base × avg_meas × cloud_cost / 12` (J102) — **removes the 80% GM plug**;
  GM = subscription + overage − COGS, an **output**.

Placeholders to calibrate later (flagged): the 3 tier discounts, the re-set `included meas` (2.4),
`cloud_cost` (J102). Keep `list/overage price` (2.5), `avg_meas` (106).

## Resolved questions
1. **Run-rate** → LTM (D1, done).
2. **Measurements/overage** → cumulative installed base (D4), per-measurement plan pricing (D5).
3. **Recognition cadence** (confirm at D5b build): hardware revenue one-time at sale; plan + overage
   recurring on the installed base. The headline `bundle_price` sums both for the pricing view.

## Task breakdown (D4 → D5)

### D4 — measurements driver onto the cumulative installed base  ✅ DONE (852260c)
Rewrite `add_measurement_children` (and the Measurements total) so each column = `installed_base ×
rate/12` (running Σ of bundle sensors × sensors/bundle), not `phased(this-period bookings)`. Revenue
row 20 already does this (oracle ties cohort==stock) — D4 makes the driver match.
- **Accept:** measurements track installed base (monotonic, no book-then-zero spike); total = Included
  + Overage; values reconcile to the SaaS oracle's stock reconstruction.
- **Verify:** `verify_model_v6_5` balances (BS check=0, no #REF!); `verify_saas_revenue` tie still <1e-6; schema broken=0; pytest.
- **Files:** `reflow_proforma.py`, gates `verify_model_v6_5.py` / `verify_saas_revenue.py`.

### D5a — Inputs: tier discounts + plan-heavy included (sorted, not appended)  *(S/M)*
Add a `2.x Line 3 — plan tier discount (%)` sub-group (S/M/L = 10/15/20%) into `LAYOUT` right after
2.5; re-set 2.4 included meas to plan-heavy (~80% of `avg_meas`), flagged placeholder; confirm
`cloud_cost` lives at J102 (3.7) else add it. Reflow renumbers + remaps refs.
- **Accept:** 3 discount inputs present, ordered after overage price; included re-set; refs remapped.
- **Verify:** resolved-target equivalence gate (label match on every remapped ref); balance oracle; schema sections still I–V; pytest.
- **Files:** `reflow_inputs.py` (`LAYOUT`).

### D5b — Subscription (plan) revenue line, on installed base  *(M)*
New ProForma recurring line: `installed_base × included × list_price × (1−discount)/12`, per bundle.
Confirm one-time vs recurring split (decision 3). Bundle-price headline = hardware×1.10 + plan.
- **Accept:** subscription line exists per bundle, on installed base; plan rate = list × (1−discount).
- **Verify:** balance oracle; SaaS oracle extended to include the subscription leg; pytest.
- **Files:** `reflow_proforma.py` / build script revenue block; `verify_saas_revenue.py`.

### D5c — Overage on installed base  *(S/M)*
Overage = `installed_base × MAX(0, avg_meas − included) × list_price / 12`. With plan-heavy included,
overage becomes a small top-up (not ~99%).
- **Accept:** overage ≪ subscription (sane top-up share); on installed base; total SaaS = sub + overage.
- **Verify:** balance oracle; SaaS oracle; eyeball overage share; pytest.

### D5d — SaaS COGS measurement-driven (remove the 80% GM plug)  *(M)*
SaaS COGS = `installed_base × avg_meas × cloud_cost / 12` (J102). Retire `calibrate_saas_placeholder`'s
GM plug; GM becomes an output.
- **Accept:** no 80% GM plug remains; SaaS GM is computed sub+overage−COGS; magnitude believable.
- **Verify:** balance oracle; SaaS oracle reports derived GM; schema broken=0; pytest.
- **Files:** build script COGS block, `calibrate_saas_placeholder` (retire), `verify_saas_revenue.py`.

### Checkpoint — after D4, and again after D5d
- Balance oracle (BS check=0, no #REF!) · SaaS oracle ties · schema broken=0 · pytest green ·
  eyeball revenue/EBITDA/ending-cash. Review with user before promoting v6.5 → v7.

## Risks
| Risk | Mitigation |
|---|---|
| Reorder breaks driver→cost refs | permutation + ref-label equivalence gate (as the prior reflows) |
| Run-rate change shifts cost-curve step → COGS values move | intended (it's a fix); verify curve steps sanely; oracle still balances |
| Phase-2 changes revenue magnitude | gated behind your economic decisions; keep Phase 1 value-neutral where possible |
