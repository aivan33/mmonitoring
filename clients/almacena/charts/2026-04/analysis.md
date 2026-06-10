# Almacena — April 2026 internal analysis companion

Internal companion to `slides.md` (the plain-text deck deliverable). Flags, big
picture, data provenance, and the items that need a human/client decision.

## Metadata

- **Period:** April 2026 (MTD) / Jan–Apr 2026 (YTD); LTM May-25→Apr-26 on trend charts.
- **Branch:** `almacena-april` (based on `cupffee-march-text`, which carries the KPI/charts engine).
- **Financials source:** `taxonomi_consolidated_04.xlsx` + `taxonomi_ap_foundation_04.xlsx`
  (EUR, both entities; reproduce Q1 Jan–Mar to the cent — `build_taxonomi.py --validate`).
- **KPI source:** `raw/04/profitability_main_apr.xlsx` (`kpi_wide`, USD → EUR @ **1.1686**).
- **Context (not in DB):** `raw/04/profitability_apr.xlsx` (deal-level) and
  `raw/04/lender_loans_accrued_interest.xlsx` (lender-level).
- **DB:** rebuilt; `validate.py almacena` → 8/8.

## Big picture (the April read)

The platform cooled off the Q1 volume peak (GMV €15.5M, −14% MoM) but the **economics
inflected the other way**: the interest spread widened decisively (Net Interest €29.3K,
> the entire Q1 combined), so Gross Profit held (~€72K) on a very different mix — interest
now carries the P&L, fees no longer the only engine. The cost is **lengthening tenor**
(Days Outstanding 33.2, two months rising) which is inflating deployed capital (Portfolio
Outstanding €14.9M, fully deployed) and stretching the funding line. Net: quality of
earnings improved, capital efficiency is maxed, watch tenor and the funding maturity wall.

## ⚠️ Flags / decisions needed

1. **Dropped KPIs — `Cash Drag %` and `Gross Profit %`.** The April profitability file
   no longer carries these two rows (Q1 file had them). Consequence: the `efficiency_cash_drag`
   chart shows the 2025 tail then stops at Dec-25; no 2026 line. Handled by (a) flagging in
   the spec `notes`, (b) narrating April deployment from Available Funds vs Outstanding in
   Slide 4, (c) a Slide 10 discussion point. **Not fabricated.** Decision: restore in the
   feed, or compute Cash Drag % internally (e.g. `1 − Outstanding/Available`, which for
   April is ≤0 ⇒ ~0% drag, fully deployed).

2. **FX rate changed 1.087 → 1.1686** (April monthly average, X-Rates). This lowers every
   EUR KPI ~7% vs the March pack *for the same months*. Anyone comparing decks will see
   different EUR figures (e.g. Mar GMV €18.0M here vs €20.5M in the March deck). Reading
   note added at the top of `slides.md`. Decision: single rate per pack (current choice) vs
   per-month rates.

3. **Volume restatement.** `profitability_main_apr` restated Jan–Mar vs the Q1 file
   (e.g. GMV Mar 21.05M vs 22.26M USD; Net Interest / Available Funds recomputed). We use the
   new file as the single source for Jan–Apr, so the deck is internally consistent but
   differs from the March pack on the historical months (FX + restatement combined).

4. **Carried reconciliation items (unchanged in April):** zero Foundation service revenue
   vs small operational service collections; YTD CoS "Other" = transportation €33.3K with no
   service-revenue twin; BG intercompany IT pair not fully eliminating; Jan N.V. write-off
   (€179.8K) and Jan insurance prepay (€44.9K) still distorting reported YTD.

## Granular context (from the two new files)

**Deal-level (`profitability_apr.xlsx`, 106 April financings):** ties exactly to the
summary (Σ GMV Amount = $18.13M = the file's GMV). Origin concentration: **Colombia 38%,
Guatemala 34%** (top-2 = 72%), Panama 13%, Honduras 8%. Counterparty/exporter and
deal-size cuts are available if a concentration chart is ever wanted (currently out of
scope — carry-forward chart set only).

**Lender-level (`lender_loans_accrued_interest.xlsx`, 58 loans):** Σ `AccruedInterestForMonth`
= $116.4K = €99.6K = the month's Cost of Funds (ties to the KPI). **24 loans active in
April**; principal-weighted **blended rate ~9.08%**. Largest active facilities: JSKR €5.0M,
Quizea €3.2M, Godelax €2.0M, AI €1.4M, Nicolas Tjandramaga €1.0M — a concentrated funding
stack. Several large facilities carry repayment dates within the next two quarters → a
**maturity wall** worth a refinancing-plan discussion; recent rolls priced ~9% vs maturing
11–12%, which is what is bringing Cost of Funds down.

## Per-chart status (10 carry-forward charts, all rendered)

| Chart | April status |
|---|---|
| throughput_gmv_funded / _operational / _avg_ticket | OK — April present |
| econ_fee_mix · econ_net_interest_breakdown | OK |
| econ_gross_profit_q1_build | period extended Q1→**YTD**; title updated; April present |
| efficiency_portfolio_outstanding · _days_outstanding | OK |
| cash_position_adjusted | OK (Cash €0.10M + Recv. related €1.29M = €1.39M adj.) |
| **efficiency_cash_drag** | **2025 only** — `Cash Drag %` dropped from feed (flag #1) |

## Open / deferred (needs more source)

- April GL parse → Slide 6 finance lines, Slide 7 operating cash-flow walk.
- Budget/Realistic scenario not loaded → no variance commentary yet.
- Foundation cash-flow detail (Slide 8) from `month-apr-ap` + lender schedule.
