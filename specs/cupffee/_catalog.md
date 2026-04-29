# Cupffee Chart Catalog — Dec 2025 Deck

Source: `clients/cupffee/Cupffee Monthly Report - Dec 2025_internal.pptx` (17 slides).
Reference images extracted to `clients/cupffee/reference/slides/` (gitignored).

**Sign-off needed.** Mark each row's STATUS as **OK** to write a spec for it, **DROP** to skip it, or **EDIT** with a correction.

## Conventions

- **chart_id**: stable identifier; will be the JSON spec filename and the rendered PNG name.
- **type**: `line`, `bar`, `stacked_bar`, `donut`, `kpi_card`, `table`, `waterfall`.
- **source**:
  - `custom` — we render via `core/charts/render.py` → matplotlib.
  - `platform` — sourced from an external BI export; renderer writes a placeholder pointing at the export path. Use `platform` for charts whose visual style or data combination clearly comes from the existing BI tool and can't be reproduced from the taxonomy DB alone.
- **period**: see plan §4. `ltm` = trailing 12 months ending at anchor; `ytd` = Jan–anchor of anchor's year; `current_month` = the anchor month; `month_offset` = relative to anchor.

---

## Slides with no rendered output

| Slide | Title | Reason |
|---|---|---|
| 1  | Cover (title + logo) | Decoration only — no chart. |
| 4  | Executive Summary / Financials | Text-only commentary + decorative icons. **(?)** Could optionally render as `kpi_card` charts for the headline numbers (Gross Profit MTD, EBITDA MTD, Cash, etc.) — same data as the slide 2 gauges. |
| 6  | Gross Profit & Margin Analysis | OLE-linked Excel table (margin breakdown). Could be reproduced as a `table` — TBD. |
| 7  | Income Statement Analysis | OLE-linked Excel IS table (similar to slide 13 appendix). |
| 9  | Cash Flow Analysis | OLE-linked Excel CF table. |
| 10 | Appendixes divider | Section divider only. |
| 17 | Monthly Overview & Discussion points | Text bullets; no chart. |

---

## Slide 2 — Key Performance Indicators – December 2025  (5 images)

| pic | chart_id (proposed) | type | source | title | data approach | notes | STATUS |
|---|---|---|---|---|---|---|---|
| 1 | — | — | — | (logo / decorative cup image) | — | skip | DROP |
| 2 | `kpi_gross_profit_mtd` | kpi_card | custom | Gross Profit MTD vs Budget | Gross Profit (Sales − Cost of Sales − Production Costs) for current_month, actual + realistic. Half-donut gauge style. | Slide shows "79.5K of 155.2K" — actual / budget. | |
| 3 | `revenue_actual_prev_budget` | bar | platform | Sales — Actual vs Previous Period vs Budget 2025 | Two-bar (current_year vs previous_year) clustered + line for budget. 12 months. | Multi-period clustered bar with overlay line — looks like a BI-tool export pattern. **(?)** Could also do as custom if you want. | |
| 4 | `kpi_net_vs_gross_burn` | line | custom | Net Burn vs Gross Burn — Trend Analysis | LTM. Gross Burn = −Σ(opex categories). Net Burn = Sales − opex_sum. **Both negative when burning.** | **EXISTING SPEC NEEDS SIGN FIX** — current spec emits positive values; deck shows negative. | |
| 5 | `kpi_ebitda_mtd` | kpi_card | custom | EBITDA MTD vs Budget | EBITDA = Sales − Cost of Sales − Production − R&D − S&M − G&A. current_month, actual + realistic. | Slide shows "33.4K of 78.9K" — actual / budget. | |

---

## Slide 3 — Cash Balance & Runway  (2 images)

| pic | chart_id | type | source | title | data approach | notes | STATUS |
|---|---|---|---|---|---|---|---|
| 1 | `cash_balance_mtm` | bar | custom | Cash Balances EUR '000 | trend of `Cash and cash equivalents` BS, 12 months ending anchor. | Single-series orange bar chart. | |
| 2 | `cash_breakdown_stacked` | stacked_bar | custom | Cash Breakdown EUR '000 | CF Indirect grouped by category (Cash from Clients, Materials, Other, Financial Inflows, PPE), 12 months. Negative components stack down, positive up. | Cash inflow/outflow decomposition by month. **(?)** Verify category mapping against `Cash Flow from Operating/Investing/Financing` groups. | |

---

## Slide 5 — Revenue Analysis  (4 images)

| pic | chart_id | type | source | title | data approach | notes | STATUS |
|---|---|---|---|---|---|---|---|
| 1 | `cash_balance_mtm_v2` (?) | bar | custom | (orange bar chart Jan-Oct, teal Nov-Dec; Cash Balance shape) | Same chart as slide 12 pic 2? | **(?)** Slide title is "Revenue Analysis" but the chart shape matches Cash Balance with rolling budget. Might be a duplicate from slide 12, or the source data is something else (cumulative revenue?). **NEEDS CLARIFICATION.** | |
| 2 | `cash_flow_decomposition` | stacked_bar | custom | (CF stacked bar, multiple categories) | Same shape as slide 3 pic 2 — duplicate? | **(?)** Possibly duplicated chart vs slide 3. Confirm. | |
| 3 | `revenue_dynamics_3yr` | bar | platform | Revenue Dynamics EUR '000 | Monthly Sales Jan–Dec for 3 years (2023, 2024, 2025) side by side. | Multi-year wide bar chart — characteristic BI export pattern. Tagged platform. | |
| 4 | `sales_by_channel_donuts` | donut | custom | Sales by Channel YTD + MTD | Two donuts: YTD (1,044K total) and MTD (124K). `get_aggregation('Sales', period, level='grp')`. | **(?)** Render as one chart with two donuts side-by-side, or two separate charts (`sales_by_channel_ytd` + `sales_by_channel_mtd`)? Easier to keep them separate. | |

---

## Slide 8 — Income Statement Charts  (4 images)

| pic | chart_id | type | source | title | data approach | notes | STATUS |
|---|---|---|---|---|---|---|---|
| 1 | `opex_trend_by_department` | stacked_bar | custom | OPEX Trend by Department | LTM (12 months ending anchor). 5 stacked categories: Cost of Sales, Production Costs, S&M, G&A, R&D. Each category = `get_trend(data=<cat>)` summed across grp/subgroup. | | |
| 2 | `pl_structure_dynamics` | stacked_bar | custom | P&L Structure Dynamics | LTM. Stack of Sales (positive) on top, opex categories (negative) on bottom. Overlay line for Net profit/loss. **Hybrid stacked_bar + line — needs renderer extension.** | **(?)** Renderer currently doesn't support overlaid line on stacked_bar. Either (a) add the feature, or (b) approximate by separate side-by-side charts. | |
| 3 | `ebitda_evolution` | bar | custom | EBITDA Evolution (clustered) | LTM. 3 clustered bars per month: Actual, Realistic budget, Previous period (lagged 12mo from anchor). | **(?)** Renderer currently renders single-series bar; needs clustered-bar support. Add feature for this chart. | |
| 4 | `revenue_growth_rate` | bar | custom | Revenue Trend Growth Rate (%) | LTM. Bar of MoM % change in Sales. Color-coded: positive=teal, negative=red. | **(?)** Renderer needs colour-by-sign feature for this chart. | |

---

## Slide 11 — Appendix: Balance Sheet Analysis & KPIs  (11 images)

This is the BS deep-dive. Eyeballed a few — they're a mix of horizontal bar charts (debt comparison, current month vs prior month), tables, and small KPI charts.

| pic | chart_id | type | source | title (proposed) | notes | STATUS |
|---|---|---|---|---|---|---|
| 1  | `bs_total_net_debt` | bar (horizontal) | custom | Total & Net Debt (current vs previous month) | Three series: Long-term debt, Net debt, Total liabilities. Two periods. | |
| 2  | `bs_kpi_2`  | ? | ? | (verify against deck) | needs visual sign-off | |
| 3  | `bs_kpi_3`  | ? | ? | | | |
| 4  | `bs_kpi_4`  | ? | ? | | | |
| 5  | `bs_summary_table` | table | custom | Balance Sheet Summary | Full BS hierarchy with current month values + sparklines. **table chart_type — needs renderer support.** | |
| 6  | `bs_kpi_6`  | ? | ? | | | |
| 7  | `bs_kpi_7`  | ? | ? | | | |
| 8  | `bs_kpi_8`  | ? | ? | | | |
| 9  | `bs_ar_vs_ap_turnover` | bar (clustered) | custom | AR turnover vs AP turnover | LTM clustered bars; AR turnover = Sales / Trade receivables (per period); AP turnover = COGS / Trade payables. | |
| 10 | `bs_kpi_10` | ? | ? | | | |
| 11 | `bs_kpi_11` | ? | ? | | | |

**(?)** Slide 11 has the most images. **Recommend you eyeball the 11 PNGs in `clients/cupffee/reference/slides/slide11_pic*.png` and tell me which to keep / drop / re-title.** I'll fill in chart_ids and types after sign-off.

---

## Slide 12 — Rolling Budget Projection vs Official Budget  (2 images)

| pic | chart_id | type | source | title | data approach | notes | STATUS |
|---|---|---|---|---|---|---|---|
| 1 | `rolling_budget_actual_vs_official` | bar | custom | Cash Balance — Rolling Budget Projection (Actual / Revenue-Rolling / Budget) | 12 months. 3-series clustered bar, last 2 months show Revenue-Rolling and Budget bars. | needs clustered-bar support (see slide 8 pic 3) | |
| 2 | `cash_balance_rolling` | bar | custom | Cash Balance based on rolling budget EUR '000 | Same shape as slide 5 pic 1 — orange Jan-Oct, teal (budget) Nov-Dec | **(?)** Likely duplicate of slide 5 pic 1. Pick one. | |

---

## Slides 13 / 14 / 15 — Yearly IS / CF / BS appendices  (1 OLE table each)

| Slide | chart_id | type | source | title | data approach | notes | STATUS |
|---|---|---|---|---|---|---|---|
| 13 | `appendix_yearly_is` | table | custom | Yearly IS Statement | `get_statement('IS', anchor, scenarios=('actual',))` over `full_year` period | needs `table` chart_type renderer | |
| 14 | `appendix_yearly_cf` | table | custom | Yearly CF Statement | same shape, statement='CF' | | |
| 15 | `appendix_yearly_bs` | table | custom | Yearly BS Statement | same shape, statement='BS' | | |

---

## Slide 16 — Methodology CoS  (3 images)

| pic | chart_id | type | source | title | data approach | notes | STATUS |
|---|---|---|---|---|---|---|---|
| 1-3 | — | — | — | (methodology diagrams / text) | likely static explanatory artwork | DROP unless you want to recreate them | DROP |

---

## Renderer features needed (from this catalog)

If we want to faithfully reproduce the deck, the renderer needs these new chart_type capabilities **beyond what Task 11 ships**:

1. **clustered_bar** (or extend `bar` with multi-series support) — for slide 8 pic 3 (EBITDA Evolution), slide 12 pic 1, slide 2 pic 3.
2. **stacked_bar with overlaid line** — for slide 8 pic 2 (P&L Structure Dynamics).
3. **bar with colour-by-sign** — for slide 8 pic 4 (Revenue Growth Rate %).
4. **table** chart_type — for slides 13/14/15 + slide 11 BS summary.
5. **kpi_card** is shipped but currently very minimal; the deck's gauges (slide 2 pic 2 / pic 5) use a half-donut "gauge" with actual vs budget — would benefit from a richer renderer.

---

## Summary — counts by status (TBD on sign-off)

- Confirmed custom charts: ~15-18
- Platform-export charts: 1–2 (Revenue Dynamics; possibly the 24 vs 25 vs Budget bar)
- Tables (need new renderer support): 4–5
- Drop: ~5 (logos, decorative icons, methodology art)

---

## Action items for you

1. Mark **STATUS** on each row above (OK / DROP / EDIT).
2. Resolve the duplicates flagged with **(?)** — slide 5 pic 1 vs slide 12 pic 2; slide 5 pic 2 vs slide 3 pic 2.
3. Confirm or correct the `source` (custom vs platform) classification on slide 2 pic 3 (Revenue Actual vs Prev vs Budget).
4. Eyeball slide 11's 11 images and tell me which to render.
5. Decide whether to build the new renderer features (clustered_bar, table, etc.) now in this iteration, or defer them to a follow-up.

After sign-off I'll write the JSON specs in this directory.
