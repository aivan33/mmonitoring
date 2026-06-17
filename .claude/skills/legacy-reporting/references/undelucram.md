# Undelucram — legacy reporting file map & inconsistency catalogue

Folders `clients/unde/raw/03/` (March cycle) and `clients/unde/raw/04/` (April
cycle). Built by the colleague, not us — kept as reference. Catalogue current as
of 2026-06-17.

## File map

| File | Key sheets | Notes |
|---|---|---|
| `Undelucram Categorization <Month>.xlsx` | `Income Invoices`, `Expense Invoices` | cumulative invoice DB back to 2024-01; LEI/EUR/USD; **column layout differs between March & April versions** (April adds a Commercial-name col; old rows use combined "RO - X", newer rows split Country/Product). Has a stray `3036` invoice-date typo (PORSCHE). |
| `MRR_Schedule_… <Month>.xlsx` | `1.1 Source Data` → `1.2 Source Data` → `2 Unique ID` → `3 MRR Data` → `4 Unique MRR Schedule` → `Reporting (1/2/3)` → `IS/CF/BS` | formula chain (see build spec). `4 Unique MRR Schedule` **row 5** is the QC (`Σ Unique − '3 MRR Data' MRR total`, must be 0). `Reporting (1)` row `MRR` = the headline MRR series. The in-workbook `IS` tab is a manually-rolled 2-month summary and is often **stale** (April file's IS tab still showed March). |
| `Retention_Analysis_… <Month>.xlsx` | `MRR Retention` (summary rows BoP/New/Expansion/Contraction/Churn/EoP near top; per-client paste rows 65+), `For Rev E Tab` | EoP = the MRR series; pasted from the MRR schedule's Unique sheet. |
| `Undelucram - Monthly reports 2026.xlsx` | `Income Statement` (hdr row 2, label col B, months E..P), `Balance Sheet`/`Cash Flow Statement` (label col A, months C..N) | the **accountant's** management report; already EUR; source for the taxonomi. |

Canonical month axis: MRR Schedule `Reporting (1)` row 2 = monthly dates; `3 MRR
Data` headers in rows 6/7/8; `4 Unique MRR Schedule` month header in row 10.

## Catalogued inconsistencies (signalled, NOT fixed)

1. **Prior-month restatement (March MRR 106,353 → 107,190, +€837).**
   Between the 03 and 04 cycles, March EoP MRR was restated in BOTH the MRR
   schedule (`Reporting`) and Retention (`MRR Retention` EoP), driven by March
   **Churn +€983** and **Contraction −€147**. Consequence: the published March
   taxonomi MRR (106,353, from the March file) is now **stale** vs the restated
   107,190. Class: restatement (the colleague pastes prior months as values and
   revises 2-months-ago, per docx ¶13). Decide per-period whether the
   taxonomi/Platform should carry the restated series.

2. **Management report: BS cash exceeds bank/CF cash by ~€8.2k every month.**
   `Balance Sheet` "Cash & equivalents" − `Cash Flow Statement` "Ending Cash
   Balance" (= "Bank statement balances") = **+8,161 / +8,083 / +8,183 / +8,378**
   for Jan/Feb/Mar/Apr. Persistent, same-sign, slowly growing → a structural
   reconciling item (cash-in-hand / a third account / cash-in-transit) or a
   carried error. Cause unconfirmed — verify with the accountant; do not assume.

3. **Management report: IS-vs-BS profit drift (small, growing).**
   BS "Profit (loss) for the period" is cumulative ≈ cumulative IS net profit,
   but drifts: Feb **−€113**, Mar **+€50**, Apr **+€566**. Small but compounding
   gap between the income statement and the balance-sheet profit line.

4. **MRR Schedule QC bug — mixed MRR/Non-MRR clients (structural).**
   `4 Unique MRR Schedule`'s month formula sums `3 MRR Data` by client NAME only
   (no MRR-flag filter), so any client flagged MRR there that also has a Non-MRR
   invoice pulls the Non-MRR amount in the month it's active. Confirmed: HUDSON
   EDGE (Non-MRR €50 active 2025-05) and MACROMATOR (Non-MRR €49.99 active
   2025-11). Plus new-month clients sometimes missing from the Unique list
   (UNICREDIT SERVICES / CYCLON TECH / MATECO drove the May −824 QC). Robust fix:
   add `,'3 MRR Data'!$B:$B,"MRR"` to the Unique `SUMIFS` (model-wide) + sync the
   Unique client list from `3 MRR Data`.

## Ties that DO hold (sanity baseline)
- Retention EoP == MRR Schedule `Reporting` MRR (Jan-Apr 2026).
- Management report BS: Total Assets == Total Equity & Liabilities (≈0).
- Management report Jan-Mar figures are IDENTICAL between the 03 and 04
  management-report files (the accountant's report itself does not drift; only
  the analyst's MRR/Retention restate).
