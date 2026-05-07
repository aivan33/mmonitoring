# Onboarding a `charts` client

Step-by-step for adding a new client whose deliverable is a slide-deck
chart inventory. Cupffee is the worked example.

The expected outcome: each month, one command produces every chart in
the client's deck as a PNG plus a JSON sidecar, ready to drop into
slides.

## Prerequisites

- The client's source data is in (or can be re-saved into) the
  canonical taxonomi format. See [`architecture.md`](architecture.md#canonical-taxonomi-format).
- A reference deck (`.pptx` or PDF) showing every chart you intend to
  reproduce. This drives the spec catalog.

If the client's source is a master workbook in a different shape (like
Farada's MR), you're onboarding a `report` client instead — see
[`onboarding-report.md`](onboarding-report.md).

## Steps

### 1. Create the client tree

```
clients/<client>/
├── config.yaml
├── chart_specs/        ← tracked
├── raw/                ← gitignored
├── data/               ← gitignored
├── reference/          ← gitignored
├── charts/             ← gitignored
└── README.md
```

Drop the source taxonomi `.xlsx` files in `raw/`, the reference deck
in `reference/`.

### 2. Author `config.yaml`

```yaml
client_name: <Client>
fiscal_year_start_month: 1
currency: EUR
as_of_date: <YYYY-MM-DD>          # latest closed month

use_cases: [charts]

entities:
  - <client>

# Files load in the order listed. On overlap, last loaded wins.
financial_sources:
  - { file: raw/<actuals_file>.xlsx, year: <YYYY>, entity: <client>, currency: EUR }
  - { file: raw/<budget_file>.xlsx,  year: <YYYY>, entity: <client>, currency: EUR }

brand:
  primary: "#..."
  accent: "#..."
  font_header: "Calibri"
  font_body: "Calibri"
```

If a source uses a non-EUR currency, add a fixed conversion rate
(`<src>_to_eur_rate: <rate>`) and set the source's `currency` field
accordingly. Cupffee's `bgn_to_eur_rate` is the worked example.

### 3. Build and validate the database

```bash
uv run python scripts/build_db.py <client>
```

Expected output:

```
built clients/<client>/data/<client>.db
  financials rows: <N>
  - raw/<source1>.xlsx: <N> rows
  - raw/<source2>.xlsx: <N> rows
  duration: <X>s
```

Add 5–10 cell-level assertions to `scripts/validate.py` covering
representative actuals + budget cells (you'll cross-check these by
hand against the source — pick known-good values from a published
prior-period report). Then:

```bash
uv run python scripts/validate.py <client>
```

This must exit 0 before you continue. A failure here means the data
isn't loading the way you expect — fix it before authoring chart
specs.

### 4. Catalog the charts

Walk the reference deck slide by slide. For each chart, decide:

- Stable `chart_id` (becomes the JSON spec filename and the rendered
  PNG name).
- Type: `line`, `bar`, `stacked_bar`, `donut`, `kpi_card`, `table`,
  `waterfall`.
- `source: custom` if we render it, `platform` if it comes from an
  external BI tool's export and we just point at it.
- Period semantics: `current_month` / `ytd` / `ltm` / `month_offset` /
  `full_year` / `explicit` / `range`.
- Data approach: which `(data, grp, subgroup)` rows feed it, which
  scenario, any aggregation level.

The catalog is a lightweight Markdown table — see
`specs/cupffee/_catalog.md` for the structure (this file moves to
`clients/cupffee/chart_specs/_catalog.md` post-cleanup).

**Sign-off step.** Recurring monthly decks carry forward ~95% unchanged
between months — if you're adding a chart that wasn't in the prior
period's deck, get explicit sign-off before writing the spec.

### 5. Write chart specs

One JSON per chart in `clients/<client>/chart_specs/`. Schema:
`core/charts/spec_schema.json`.

Use existing Cupffee specs as references:

| Pattern | Reference spec |
|---|---|
| KPI half-donut card | `kpi_gross_profit_mtd.json` |
| Line chart with trend | `kpi_net_vs_gross_burn.json` |
| Bar chart with overlay | `revenue_act_pp_bp_2026.json` |
| Stacked bar (rolling) | `cash_breakdown_rolling.json` |
| Donut breakdown | `sales_by_channel_mtd.json` |

Copy the closest match, change the `chart_id`, queries, and styling.

### 6. Render

```bash
uv run python scripts/build_charts.py <client> <YYYY-MM>
```

Output lands in `clients/<client>/charts/<YYYY-MM>/`. Open
`index.html` in a browser to see all charts on one page.

For iteration on a single chart:

```bash
uv run python scripts/build_charts.py <client> <YYYY-MM> --only <chart_id>
```

### 7. Compare to the reference deck

Open each generated PNG next to the corresponding slide in the
reference deck. Look for:

- Same numbers (within rounding)
- Same time period
- Same chart type and orientation
- Reasonable styling match

Iterate on the spec until each chart is "close enough that a human
would accept it as the same chart."

### 8. Write the per-client `README.md`

Colleague-facing — the people who consume the output need to verify
correctness without reading code. Three sections in plain business
language:

- **What goes in** — which source files, where they come from, what
  they represent
- **What happens** — the pipeline in business terms (no code)
- **What comes out** — the artefacts and how to sanity-check them

See `clients/cupffee/README.md` for the worked example.

## Monthly cadence

Once onboarded, each new month:

1. Drop the new taxonomi `.xlsx` into `raw/`.
2. Update `config.yaml`'s `as_of_date` and add the new source to
   `financial_sources` (or replace an existing one — last-loaded wins).
3. `uv run python scripts/build_db.py <client>`
4. `uv run python scripts/validate.py <client>`
5. `uv run python scripts/build_charts.py <client> <YYYY-MM>`
6. Visual check against the prior period's deck — anything that moved
   unexpectedly gets investigated before delivery.
