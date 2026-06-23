# Spec — overage ramp delay (clients don't overuse from month 1)

A new client doesn't start consuming overage immediately — there's a ramp before usage exceeds the
included quota. Add an **input** for the delay (X months) and apply it to the overage stream so a
cohort booked in month *t* contributes overage only from month *t + X*.

## Architecture decision — global column-shift = exact per-cohort delay
The overage line is already a **cumulative cohort accumulation** (each month adds the new cohort's
overage MRR; it persists). A *uniform* per-cohort delay of X months is therefore identical to shifting
the whole aggregate line right by X months:

```
overage_delayed(c) = overage_undelayed(c − X)         # exact, because the delay is uniform & the op is linear
```

A cohort booked in month *t* is active from *t+X*; at month *c* the active cohorts are those with
*t ≤ c−X*, whose summed MRR = the undelayed cumulative at *c−X*. So no per-cohort tracking is needed.

**Implement with OFFSET** (already used for the scenario selector `J=OFFSET(K,0,$D$2)`), guarded to
avoid `#REF!` in the first X months:
```
delayed(c) = IF( (COLUMN() − firstcol) < delay , 0 , OFFSET( undelayed_thiscol , 0 , −delay ) )
```
`delay` reads the live input cell, so changing X in Excel re-shifts the curve (no rebuild needed).

## Scope — what the delay touches
Overage is consumed in three revenue places (SaaS #3 r38, AR roll r125, IS r19) and the overage
**measurement** child (r18 → measurement total r16 → cloud COGS r70). The ramp delays **both**:
- **Overage revenue** — so SaaS #3 / AR / IS all see the delayed overage (single delayed source row).
- **Overage measurements** — so cloud COGS for the overage portion is also delayed (no usage → no cost).
**Unaffected:** Hardware (one-time at sale) and Subscription/Included (the plan starts month 1).

## Layout (keep the undelayed cumulative as the engine; expose the delayed value where consumed)
- **Revenue:** children 49–51 stay undelayed cumulative (engine). Move their `=Σ children` to a helper
  "Overage (undelayed, gross)" row; the named **"SaaS (overage, recurring)"** (r48) becomes the
  *delayed* value `=IF(...<delay,0,OFFSET(helper,0,−delay))`. Consumers (SaaS #3/AR/IS) unchanged.
- **Measurements:** keep the Overage child (r18) undelayed; the measurement **total** (r16) applies the
  delay inline to the overage term: `=C17 + IF(...<delay,0,OFFSET(C18,0,−delay))`. Cloud COGS (r70)
  reads the total, so it follows automatically. (Exact row mechanics finalised at build.)

## Input
New input in **II. REVENUE** (sub-group 2.7, after pricing parameters): **"Overage ramp delay
(months)"**, unit `months`, default **3** (flagged placeholder). One global value (per-bundle can come
later if needed).

## Tasks
- [ ] **OD1 — input.** Add "Overage ramp delay (months)" to `reflow_inputs` LAYOUT (II. REVENUE) +
  value via `set_d5_inputs`. *Verify:* input present, ordered in REVENUE, unit `months`, value 3.
- [ ] **OD2 — overage revenue delay.** Helper undelayed-sum row; r48 = delayed OFFSET (guarded);
  consumers unchanged. *Verify:* r48 = `IF(...<delay,0,OFFSET(helper,0,−delay))`; SaaS#3/AR/IS still
  reference r48; no `#REF!`.
- [ ] **OD3 — overage measurements delay.** Measurement total (r16) delays the overage term inline;
  cloud COGS follows. *Verify:* total = Included + delayed-Overage; cloud COGS tracks it.
- [ ] **OD4 — verify.** Balance oracle BS check=0 (overage shift is value-only; balance is structural),
  no `#REF!`, schema broken=0, full pytest. Eyeball: overage = 0 for the first X months, then ramps to
  the undelayed curve shifted right by X.

### Checkpoint — overage starts X months in, input is live, model still balances.

## Risks
| Risk | Mitigation |
|---|---|
| OFFSET reaches before col C → `#REF!` in first X months | the `IF((COLUMN()−firstcol)<delay,0,…)` guard; oracle's no-#REF check |
| Revenue & COGS use inconsistent delay → distorted GM | both read the SAME delay input; OD2/OD3 verified together |
| Shift changes AR/revenue/COGS magnitudes | intended; balance is structural (check=0 holds) — confirm via oracle |

## DECISIONS (2026-06-23, confirmed)
1. Delay applies to **both** overage revenue **and** measurements/cloud COGS.
2. **One global** delay input.
3. **Hard cliff** at month X (exact column-shift).
4. Default **3 months** (flagged placeholder).
