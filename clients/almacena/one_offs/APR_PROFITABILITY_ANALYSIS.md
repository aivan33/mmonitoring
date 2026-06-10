# Almacena — April profitability file analysis (vs Q1)

The April profitability export (`raw/04/profitability_apr.xlsx`) has a **fundamentally
different shape** from the Q1 file. The format changed from a *pre-aggregated monthly
KPI summary* to a *raw deal/loan-level export* that we must aggregate ourselves.

## Side by side

| | Q1 (`profitability_q1.xlsx`) | April (`raw/04/profitability_apr.xlsx`) |
|---|---|---|
| Shape | **1 sheet**, 23 KPIs × 3 months (Jan–Mar) | **5 sheets**, deal/loan-level rows, **April only** |
| Granularity | already summarised per month | one row per financing / loan slice |
| Ready to load? | yes — it's the `kpi_wide` shape the DB ingests | **no** — needs a rollup step first |
| Period | the quarter, pre-built | single month; trend must be stitched onto Q1 |

The Q1 sheet handed us the finished line items (GMV, Funded Amount, Average Days
Outstanding, # Invoices, # Boxes, Arrangement Fees, Logistic/Cargo fees & costs,
Accrued Interest, Available Funds, Cost of Funds, Average Portfolio Outstanding, Net
Interest, Gross Profit, Gross Profit %, Cash Drag %). April hands us the underlying
ledger and expects us to compute them.

## What each April tab is, and how it rolls up

1. **GMV** — 106 financings. Per deal: Country / Exporter / Buyer / Contract /
   Financing & Ledger Id / Lots / disbursement start–end / Invoice / Proforma / APR
   Amount / **GMV Amount** / APR Rate. → **GMV = Σ GMV Amount**; **# Invoices** = row
   count; **# Boxes** ≈ count of Lots; APR-rate and origin breakdowns fall out for free.
2. **Funded Amount** — same 106 deals + a `Closed` flag. → **Funded = Σ |APR Amount|**.
3. **Average Portfolio Outstanding** — 205 deal-slices with `Overlap Start/End` inside
   April. → **time-weighted avg = Σ(|APR Amount| × overlap_days) / days_in_month**.
4. **Accrued Interest** — 205 deal-slices: `APR Amount Abs`, `APR Rate %`, overlap. →
   **Accrued Interest = Σ(APR Amount Abs × rate × overlap_days/365)** (month slice).
5. **Funds (Available & Cost)** — 24 lender loans with Principal, annual rate, overlap,
   and **pre-computed** `Available Funds Contribution` + `Cost of Funds Contribution`. →
   **Available Funds = Σ Available Funds Contribution**; **Cost of Funds = Σ Cost of
   Funds Contribution** (the platform already prorated by overlap days — just sum).

## KPI coverage — what April covers vs what's missing

**Derivable from the April file:** GMV, Funded Amount, # Invoices, # Boxes,
Average Portfolio Outstanding, Accrued Interest, Available Funds, Cost of Funds,
APR Rate, Average Days Outstanding (from disbursement start–end), and origin / counterparty
/ deal-size cuts.

**In the Q1 summary but NOT in the April file (need another source):**
- **Fee lines** — Arrangement Fees, Logistic Fees/Costs, Cargo Insurance Fees/Costs,
  Docs Management Fees, Handling & Warehouse Fees/Costs. These are transaction fees not
  present in any April tab. Likely they live in the financial-statement exports
  (`raw/04/month-apr-ap.xlsx` IS / the ap_foundation P&L) or a separate fee report —
  **needs confirming where April's fee figures come from.**
- **% GMV Insured** — no insurance flag in the April tabs.
- **Derived metrics** — Net Interest (= Accrued Interest − Cost of Funds), Gross Profit,
  Gross Profit %, Cash Drag % — computed from the above + fees, not raw lines.

## April headline numbers (computed from the raw tabs, as a sanity check)

| KPI | April (computed) | March (Q1, for trajectory) |
|---|---:|---:|
| GMV | **€18,132,844** | €22,263,783 |
| Funded Amount | **€15,766,615** (84/106 deals closed) | €18,720,283 |
| # Invoices (deals) | **106** | 101 |
| Lenders (funds) | 24 | — |

Plausible month-on-month (GMV/Funded down ~18% from March). GMV by origin (April):
Colombia €6.88M · Guatemala €6.23M · Panama €2.34M · Honduras €1.40M · Brazil €0.29M ·
Uganda €0.26M · Peru €0.26M · Nicaragua €0.17M.

## Two implications

1. **A rollup step is now required.** The DB's `kpi_wide` loader expects the Q1 summary
   shape. April needs a small aggregator (deal-level → the 23 monthly KPI lines, matching
   Q1 definitions) before it can feed the DB / charts. The Q1 file's own numbers are the
   reproduction target for the rollup formulas (e.g. tune the Accrued-Interest day-count
   until Jan–Mar would reproduce — though Q1 came pre-summed, so cross-check against any
   month where we also have the granular export).
2. **The granularity unlocks new charts** the Q1 summary couldn't support: GMV/funded by
   origin country, exporter & buyer concentration, deal-size distribution, APR-rate
   spread, tenor mix, closed-vs-open. Worth a look when we pick the April chart set.

## Note on the other April exports

`month-apr-{alm,ap}.xlsx` and `year-apr-{alm,ap}.xlsx` are the platform's **IS/CF/BS
statement exports** per entity (`alm` = consolidated, `ap` = ap_foundation), March-vs-April
+YTD and full-year-monthly respectively. They are an independent cut of the same financials
we wired into the taxonomi — usable as a cross-check, or as the going-forward statement
source.
