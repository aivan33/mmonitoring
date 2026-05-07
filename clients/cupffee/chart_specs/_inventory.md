# Cupffee Dec-2025 Deck — Full Chart Inventory

37 images across 17 slides. Each row below is one extracted image. Mark
the **PICK** column with **Y** (render this) / **N** (skip) / **?** (need
to discuss). Some rows are obvious decorations or duplicates — pre-marked
N as a default.

Reference images live in `clients/cupffee/reference/slides/` (gitignored).
Open the file path to see the actual chart.

| # | Slide | File | Title / what it is | Type | PICK | Notes |
|---|---|---|---|---|---|---|
| 1  | 1  | slide01_pic1.png  | Cupffee cup logo                         | decoration | N | cover image |
| 2  | 2  | slide02_pic1.png  | Cupffee cup logo                         | decoration | N | header image |
| 3  | 2  | slide02_pic2.png  | KPI gauge: **Gross Profit MTD** 79.5K of 155.2K | kpi_card (half-donut) |   | actual vs realistic-budget gauge |
| 4  | 2  | slide02_pic3.png  | **Sales — Actual vs Previous Period vs Budget 2025** | clustered_bar + line |   | Revenue 24 (teal) + Revenue 25 (orange) bars + Budget 25 line |
| 5  | 2  | slide02_pic4.png  | **Net Burn vs Gross Burn — Trend Analysis** | line | Y (DONE) | already rendered: `kpi_net_vs_gross_burn` (signs may need refining vs deck magnitudes) |
| 6  | 2  | slide02_pic5.png  | KPI gauge: **EBITDA MTD** 33.4K of 78.9K | kpi_card (half-donut) |   | actual vs realistic-budget gauge |
| 7  | 3  | slide03_pic1.png  | **Cash Balances EUR '000** (orange bars MTM) | bar |   | Cash and cash equivalents trend, 12 months |
| 8  | 3  | slide03_pic2.png  | **Cash Breakdown EUR '000** (stacked, multi-color) | stacked_bar |   | CF categories stacked: Cash from Clients (teal), Materials/Other (red), Financial Inflows (cyan), PPE (pink) |
| 9  | 4  | slide04_pic1.png  | Cash icon                                 | decoration | N | |
| 10 | 4  | slide04_pic2.png  | Gears icon                                | decoration | N | |
| 11 | 5  | slide05_pic1.png  | Cash Balance + Rolling Budget extension (orange Jan-Oct, teal Nov-Dec) | bar |   | **DUPLICATE of #29** (slide12_pic2) — pick one |
| 12 | 5  | slide05_pic2.png  | Cash flow stacked bars (5 categories)     | stacked_bar |   | **DUPLICATE of #8** (slide03_pic2) — pick one |
| 13 | 5  | slide05_pic3.png  | **Revenue Dynamics — Monthly 2023/24/25** | bar (multi-year) |   | 3 years side by side; this is the classic "platform-export" pattern |
| 14 | 5  | slide05_pic4.png  | **Sales by Channel — YTD + MTD** (two donuts) | donut |   | YTD center=1,044K, MTD center=124K; can be one combined chart or two separate |
| 15 | 6  | (OLE)             | Margin analysis table                     | table     |   | OLE-linked Excel (couldn't extract); could rebuild from DB |
| 16 | 7  | (OLE)             | Income Statement Analysis table           | table     |   | OLE-linked Excel; full IS via `get_statement('IS', ...)` |
| 17 | 8  | slide08_pic1.png  | **OPEX Trend by Department**              | stacked_bar |   | 5 categories (Cost of Sales, Production, S&M, G&A, R&D), 12 months |
| 18 | 8  | slide08_pic2.png  | **P&L Structure Dynamics**                | stacked_bar + line |   | Sales positive stack + opex negative stack + Net profit/loss overlay line |
| 19 | 8  | slide08_pic3.png  | **EBITDA Evolution** (3-series clustered) | clustered_bar |   | Actual / Realistic budget / Previous period (lagged 12mo) |
| 20 | 8  | slide08_pic4.png  | **Revenue Trend Growth Rate (%)**         | bar (color-by-sign) |   | MoM % change in Sales, positive=teal, negative=red |
| 21 | 9  | (OLE)             | Cash Flow Analysis table                  | table     |   | OLE-linked Excel; full CF via `get_statement('CF', ...)` |
| 22 | 11 | slide11_pic1.png  | **Total & Net debt** (current vs prev month) | bar (horizontal) |   | values 1.3M / 1.6M / 1.9M |
| 23 | 11 | slide11_pic2.png  | **AR turnover vs AP turnover** (LTM, Nov 24 - Oct 25) | clustered_bar |   | 12 months LTM |
| 24 | 11 | slide11_pic3.png  | **Working capital ratio** (LTM line, Nov 24 - Oct 25) | line |   | 12 months LTM |
| 25 | 11 | slide11_pic4.png  | **Return on asset** (LTM line, Nov 24 - Oct 25) | line |   | 12 months LTM |
| 26 | 11 | slide11_pic5.png  | **Balance Sheet summary table** with sparklines | table |   | full BS hierarchy + per-row sparkline; complex |
| 27 | 11 | slide11_pic6.png  | **9-KPI grid** (Sales Growth, Gross Margin, OPEX/Sales, EBITDA Margin, Current Ratio, Cash Ratio, Asset Turnover, EBITDA Interest Coverage, Financial Leverage) | kpi grid |   | 9 mini KPIs in a row, each with value + variance + tiny sparkline |
| 28 | 11 | slide11_pic7.png  | CFO Insights logo                         | decoration | N | |
| 29 | 11 | slide11_pic8.png  | **Return on asset** (Jan 25 - Dec 25)     | line |   | calendar-year version of #25 |
| 30 | 11 | slide11_pic9.png  | **AR turnover vs AP turnover** (Jan 25 - Dec 25) | clustered_bar |   | calendar-year version of #23 |
| 31 | 11 | slide11_pic10.png | **Working capital ratio** (Jan 25 - Dec 25) | line |   | calendar-year version of #24 |
| 32 | 11 | slide11_pic11.png | **Total & Net debt** (different values 1.3M/1.4M/1.6M) | bar (horizontal) |   | might be a different snapshot from #22 |
| 33 | 12 | slide12_pic1.png  | **Cash Balance — Actual / Revenue-Rolling / Budget** | clustered_bar |   | last 2 months show Revenue-Rolling and Budget bars in different colors |
| 34 | 12 | slide12_pic2.png  | Cash Balance — same shape as #11 (orange Jan-Oct, teal Nov-Dec) | bar |   | **DUPLICATE of #11** — pick one |
| 35 | 13 | slide13_pic1.png  | CFO Insights logo                         | decoration | N | actual IS table is OLE-linked (entry #16 covers it) |
| 36 | 13 | (OLE)             | **Yearly IS Statement** (full 12 months)  | table     |   | full yearly IS via `get_statement` over `full_year` |
| 37 | 14 | slide14_pic1.png  | CFO Insights logo                         | decoration | N | |
| 38 | 14 | (OLE)             | **Yearly CF Statement** (full 12 months)  | table     |   | full yearly CF |
| 39 | 15 | slide15_pic1.png  | CFO Insights logo                         | decoration | N | |
| 40 | 15 | (OLE)             | **Yearly BS Statement** (full 12 months)  | table     |   | full yearly BS |
| 41 | 16 | slide16_pic1.png  | Pricing table 110 ml (Bulgarian text)     | reference | N | static methodology artifact, not data-driven |
| 42 | 16 | slide16_pic2.png  | Pricing table 220 ml (Bulgarian text)     | reference | N | static methodology artifact |
| 43 | 16 | slide16_pic3.png  | Cupffee cup logo                          | decoration | N | |

---

## Distinct charts (deduplicated, decorations & OLE entries collapsed)

If you skip decorations, dedup the 4 obvious duplicates, and treat OLE-linked statements as their own line items, you have ~22 unique charts to consider:

| Group | Charts | Renderer features needed |
|---|---|---|
| **KPI gauges** | #3 Gross Profit MTD, #6 EBITDA MTD | half-donut gauge style for kpi_card |
| **Burn / Cash trends** | #5 Net vs Gross Burn (DONE), #7 Cash Balance bars | (none beyond shipped) |
| **Revenue charts** | #4 Sales 24/25/Budget, #13 Revenue Dynamics 3yr, #20 Revenue Growth Rate %, #14 Sales by Channel donuts | clustered_bar, color-by-sign |
| **P&L / IS** | #17 OPEX Trend by Dept, #18 P&L Structure Dynamics, #19 EBITDA Evolution | stacked_bar+line overlay, clustered_bar |
| **Cash flow** | #8 Cash Breakdown stacked, #33 Cash Balance Actual/Rolling/Budget | clustered_bar |
| **BS / KPI ratios (slide 11)** | #22 Debt, #23 AR/AP LTM, #24 WC ratio LTM, #25 RoA LTM, #26 BS table, #27 9-KPI grid, #29 RoA calendar, #30 AR/AP calendar, #31 WC ratio calendar, #32 Debt v2 | horizontal bar, clustered_bar, table, KPI-grid layout |
| **Tables** | #15 Margin, #16 IS, #21 CF, #36 Yearly IS, #38 Yearly CF, #40 Yearly BS | table chart_type |

---

## Action

Reply with the **#** numbers you want rendered (e.g. "5, 7, 14, 17, 19, 20, 36, 38, 40"). I'll write specs only for those, render them, and skip everything else.

If a number you pick needs a renderer feature not yet shipped (clustered_bar, table, etc.), I'll add it as part of writing the spec.
