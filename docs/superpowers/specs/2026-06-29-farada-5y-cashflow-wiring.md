# Implementation Plan: Farada 5Y Plan — Wire WC Drivers & Cash Flows (v1)

**Source model:** `clients/farada/modeling/FaradaIC - 5Y plan - WIP.xlsx`
**Reference:** `clients/farada/modeling/FaradaIC_ 2026 (Rolling Budget_v2).xlsx` (Pro Forma layout & cash-in-by-line structure)
**Build target:** `clients/farada/modeling/farada_5y_v1.xlsx` (first version in the new series)

## Overview
The WIP ProForma is fully wired through Volumes → Revenue → COGS → OpEx → Taxation. Two
sections are blank and need formulas: **WORKING CAPITAL DRIVERS** (rows 164–182) and
**CASH FLOW** (rows 184–220). Cash collects/pays the month *after* the invoice, driven by
day inputs already present on the Inputs sheet (DSO 30, DPO 30, Payroll 14). We wire the
balances, derive cash as `accrual − Δ(WC balance)`, then connect those cash lines into the
CF statement and repair the BS links so the model ties and balances.

## Architecture Decisions
- **Balance-driven cash, not a raw column shift.** Each WC line holds a *closing balance*
  (`days/30 × monthly accrual`); each cash line = `accrual ∓ Δbalance`. At 30 days this is a
  clean one-month lag; at 14 days (personnel) it splits ~16/30 this month, 14/30 next. This
  is the only convention that makes the CF tie to the BS movement. *(Decision D1 — confirm.)*
- **Day inputs already exist** on ` Inputs` rows 184/187/188 with scenario columns L/M and an
  `OFFSET($D$2)` selector at J. We change Payroll payable days (188) L&M from 30 → 14 and
  otherwise reuse the scaffold. No new input rows needed.
- **Net (ex-VAT) cash in v1.** WIP ProForma carries no VAT section; cash in = net revenue,
  cash out = net cost. (Reference grossed by `(1+VAT)`; we don't, pending a VAT build.) *(D4 — stated assumption.)*
- **SaaS subscription billed annually in advance (D2 = confirmed).** The recurring SaaS
  Subscription lines (ProForma 61–63) are billed 12 months upfront when installed base is added
  (Inputs 186 = 100%): cash collected in the add-month, revenue recognized 1/12 monthly, the
  unrecognized portion sits in a **deferred-revenue balance** feeding BS row 30. **Hardware device
  sales (57–59) carry NO prepayment** (Inputs 185 stays 0) and follow the normal DSO lag. SaaS
  overage (65–67), Components #1/#2, and the hardware device all use plain day-lag.
- **Versioned output.** Write to `farada_5y_v1.xlsx`; leave the WIP file untouched as the input.

## Inputs (already on ` Inputs`, section 5.2 / 5.3)
| Row | Driver | v1 value |
|----|--------|---------|
| 184 | Receivable days (DSO) | 30 |
| 187 | Payable days (DPO) | 30 |
| 188 | Payroll payable days | **14** (change from 30) |
| 192–196 | Opening cash / AR / AP / payroll payable / deferred rev | as set (cash 2,000,000; rest 0) |
| 185/186 | Hardware prepayment % / SaaS billed annually in advance | see D2 |

## Row map (ProForma WIP)
**Accrual → WC balance → cash line.** Cash-in lines mirror revenue rows 45–67; supplier/
personnel cash mirror COGS (69–86) and OpEx (89–117).

- AR balance (166) = DSO/30 × Revenue (45). Cash in from clients (186) = Revenue − ΔAR,
  split by line 187–208 against revenue rows 47/48/49, 51/52/53, 57/58/59, 61/62/63, 65/66/67.
- Payables excl. payroll (170/172/174/176) = DPO/30 × bucket non-payroll spend
  (S&M 92:98, G&A G&A-ex-payroll, CoS = COGS 69, R&D R&D-ex-payroll). Trade payables (168) = sum.
  Cash paid to suppliers (210) split 211–214 = bucket cost − Δbucket payable.
- Personnel payable (178) buckets 179–182 = 14/30 × payroll (CoS/S&M 91 / G&A 100 / R&D 111).
  Payments to personnel (216) split 217–220 = payroll − Δpersonnel payable.

## Task List

### Phase 1: Inputs & WC balances (foundation)
- [ ] **Task 1 — Set the day driver.** Change ` Inputs` row 188 (Payroll payable days) L & M
  from 30 → 14. Confirm DSO/DPO stay 30; J-selector resolves via `OFFSET($D$2)`.
  *Accept:* `ProForma` can read Payroll days = 14, DSO/DPO = 30 for the active scenario.
  *Verify:* read-back of evaluated `J188=14`, `J184=J187=30`. Scope: XS (1 sheet).
- [ ] **Task 2 — Wire AR balance + receivables cash-in.** ProForma 166 = `DSO/30 × Revenue`
  (opening from Inputs 193, col C). Rows 187–208 cash-in = matching revenue row − its ΔAR
  share; 186 = sum. First month uses opening AR.
  *Accept:* row 186 = prior-month revenue once steady; col C honours opening AR; 187–208 sum to 186.
  *Verify:* recompute with LibreOffice headless; cash-in[m] ≈ revenue[m−1] for a mid-year month.
  Scope: M (1 sheet, ~25 rows).
- [ ] **Task 3 — Wire supplier payables + cash paid to suppliers.** ProForma 170/172/174/176 =
  `DPO/30 × bucket cost`; 168 = sum; 211–214 = bucket cost − Δpayable; 210 = sum. Opening AP from Inputs 194.
  *Accept:* 211–214 sum to 210; cash-out[m] ≈ cost[m−1] mid-year; opening AP honoured in col C.
  *Verify:* headless recompute, spot-check one bucket. Scope: M.
- [ ] **Task 4 — Wire personnel payables + payments to personnel.** ProForma 179–182 =
  `14/30 × payroll bucket`; 178 = sum; 217–220 = payroll − Δpayable; 216 = sum. Opening from Inputs 195.
  *Accept:* personnel cash[m] = 16/30·payroll[m] + 14/30·payroll[m−1] for a steady month; sums tie.
  *Verify:* headless recompute, hand-check the 16/30 split on one month. Scope: S–M.

- [ ] **Task 4b — SaaS annual-in-advance + deferred revenue.** For Subscription lines 61–63:
  when installed base (25–27) increments by Δ, bill `Δ × annual subscription` as cash in the
  add-month (cash rows 202–204); recognize 1/12 monthly in revenue (already accrued at 61–63);
  track the unrecognized remainder as a deferred-revenue balance (opening from Inputs 196) that
  feeds `BS!` Deferred revenue (row 30). Gated on Inputs 186 = 100% (so the toggle can disable it).
  *Accept:* Σ cash from subscriptions over a contract year = Σ recognized subscription revenue;
  deferred-rev balance ≥ 0 and unwinds to ~0 at steady state; BS deferred-rev row populated.
  *Verify:* headless recompute; hand-check one cohort's 12-month unwind. Scope: M. *(D2.)*

### Checkpoint A (after Tasks 1–4b)
- [ ] All WC balances ≥ 0 and equal `days/30 × accrual` each month.
- [ ] Every cash subtotal equals the sum of its child lines.
- [ ] Σ(cash in) − Σ(cash out) over the horizon = Σ(revenue) − Σ(cost) ∓ Σ(closing WC). **Review with user.**

### Phase 2: Statement wiring & tie-out
- [ ] **Task 5 — Wire the CF statement sheet.** `CF!` row 3 (cash from customers) ← ProForma 186;
  row 4 (suppliers) ← 210; row 5 (personnel) ← 216; keep existing tax/VAT/financing rows. Ending
  cash chains from Inputs 192 opening.
  *Accept:* CF!24 Ending Cash computes for all months; no `#REF!` introduced. Scope: S.
- [ ] **Task 6 — Repair BS links to the WC balances + tie-out.** Re-point the stale `BS!`
  references (Trade receivables, Trade payables, Personnel payables, Cash, Deferred revenue) to the
  correct post-reorder ProForma rows (166/168/178/…); confirm `BS!34 check ≈ 0` each month.
  *Accept:* BS balances (Assets − E&L) to < €1 every month; cash on BS = CF ending cash.
  *Verify:* headless recompute, read the check row across all 60 months. Scope: M. *(In scope per D3.)*

### Checkpoint B (Complete)
- [ ] CF ending cash is sensible (no implausible negatives from a wiring error).
- [ ] BS check ≈ 0 across the full 60-month horizon.
- [ ] Saved as `farada_5y_v1.xlsx`; WIP input untouched. **Review with user.**

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| openpyxl writes formulas but can't evaluate → can't self-verify | High | Recompute with LibreOffice headless and read `data_only` values |
| Stale BS/IS links beyond the ones spotted | Med | Audit all cross-sheet refs into ProForma after reorder; list before fixing |
| Deferred-rev / prepayment inputs exist but unused → cash overstated for SaaS | Med | D2 decides; if deferred, model SaaS-annual-advance + deferred revenue balance |
| Personnel "Payroll CoS" bucket has no COGS payroll source | Low | Confirm source row; default to 0 if no production payroll exists |

## Decisions (resolved)
- **D1 — Cash convention:** ✅ balance-driven `accrual − Δ(days/30 × accrual)`.
- **D2 — Deferred revenue / prepayment:** ✅ Model SaaS Subscription (61–63) as billed
  annually in advance with a deferred-revenue balance (Task 4b). Do NOT model hardware prepayment
  (Inputs 185 stays 0). *Assumption to flag: "annual billing for the hardware" = the recurring
  SaaS subscription within Product Line #3, not the hardware device itself.*
- **D3 — Downstream scope:** ✅ Full tie-out — wire CF statement (Task 5) and repair BS links (Task 6).
- **D4 — VAT:** net cash, no `(1+VAT)` gross-up in v1. Stated assumption.
