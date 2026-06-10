# Almacena — April 2026 internal analysis companion

Internal companion to `slides.md` (the plain-text deck deliverable). Flags, big
picture, data provenance, and the items that need a human/client decision.

## Metadata

- **Period:** April 2026 (MTD) / Jan–Apr 2026 (YTD); LTM May-25→Apr-26 on trend charts.
- **Branch:** `almacena-april` (based on `cupffee-march-text`, which carries the KPI/charts engine).
- **Financials source:** `taxonomi_consolidated_04.xlsx` + `taxonomi_ap_foundation_04.xlsx`
  (EUR, both entities; reproduce Q1 Jan–Mar to the cent — `build_taxonomi.py --validate`).
- **KPI source:** `raw/04/profitability_main_apr.xlsx` (`kpi_wide`, USD → EUR @ **1.087**, held; see flag #2).
- **Context (not in DB):** `raw/04/profitability_apr.xlsx` (deal-level) and
  `raw/04/lender_loans_accrued_interest.xlsx` (lender-level).
- **DB:** rebuilt; `validate.py almacena` → 8/8.

## Big picture (the April read)

The platform cooled off the Q1 volume peak (GMV €16.7M, −14% MoM) but the **economics
inflected the other way**: the interest spread widened decisively (Net Interest €31.5K,
> the entire Q1 combined), so Gross Profit held (~€78K) on a very different mix — interest
now carries the P&L, fees no longer the only engine. The cost is **lengthening tenor**
(Days Outstanding 33.2, two months rising) which is inflating deployed capital (Portfolio
Outstanding €16.0M, fully deployed) and stretching the funding line. Net: quality of
earnings improved, capital efficiency is maxed, watch tenor and the funding maturity wall.

## ⚠️ Flags / decisions needed

1. **Dropped KPIs — `Cash Drag %` and `Gross Profit %`; cash-drag chart REMOVED this cycle.**
   The April file no longer carries these rows. I tested reconstructing Cash Drag % from
   `(Available − Outstanding)/Available`: it reproduces January (0.155 vs platform 0.155) but
   **not** Feb (0.123 vs 0.131) or Mar (0.019 vs 0.008), and goes **negative** for April
   (−0.118, since Avg Portfolio Outstanding €16.0M > Available Funds €14.3M). Not reliable →
   per direction, the `efficiency_cash_drag` spec was deleted and Slide 4 narrates deployment
   directly. **Not fabricated.** Decision: provide the platform input, or agree a computable
   definition.

2. **FX held at 1.087 (NOT 1.1686).** The April monthly average was ~1.1686, but applying it
   to April alone (history at 1.087) distorted the GMV trend: real April MoM is −13.9% (USD),
   which would have read −19.9% — a ~6pp pure-FX step. Per direction, the prior 1.087 is held
   across the whole series so history is unchanged and the trend stays comparable (April is
   thus ~7% overstated in EUR vs spot reality — an accepted, flagged trade-off). Decision:
   adopt per-month FX in future (would restate history) or keep a held rate.

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
= $116.4K = €107.1K (@1.087) = the month's Cost of Funds (ties to the KPI). **24 loans active
in April**; principal-weighted **blended rate ~9.08%**. Largest active facilities (EUR @1.087):
JSKR €4.6M, Quizea €2.9M, Godelax €1.8M, AI €1.3M, Nicolas Tjandramaga €0.9M — a concentrated
funding stack. Several large facilities carry repayment dates within the next two quarters → a
**maturity wall** worth a refinancing-plan discussion; recent rolls priced ~9% vs maturing
11–12%, which is what is bringing Cost of Funds down.

## Per-chart status (9 carry-forward charts rendered; cash-drag removed)

| Chart | April status |
|---|---|
| throughput_gmv_funded / _operational / _avg_ticket | OK — April present |
| econ_fee_mix · econ_net_interest_breakdown | OK |
| econ_gross_profit_q1_build | period extended Q1→**YTD**; title updated; April present |
| efficiency_portfolio_outstanding · _days_outstanding | OK |
| cash_position_adjusted | OK (Cash €0.10M + Recv. related €1.29M = €1.39M adj.) |
| ~~efficiency_cash_drag~~ | **REMOVED** — `Cash Drag %` dropped from feed, not reconstructable (flag #1) |

## Open / deferred (needs more source)

- April GL parse → Slide 6 finance lines, Slide 7 operating cash-flow walk.
- Budget/Realistic scenario not loaded → no variance commentary yet.
- Foundation cash-flow detail (Slide 8) from `month-apr-ap` + lender schedule.
