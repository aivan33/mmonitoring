# Implementation Plan: Monthly Monitoring — Stage 1 (Data Layer) + Stage 2 (Chart Inventory)

This supersedes the earlier Stage-1-only plan. New context dropped: a second client (**Almacena**) with **two tracked entities**, an explicit Stage 2 goal (chart inventory + JSON spec per chart), and reference PowerPoint decks for both clients.

## Goal (recap from user)

> Optimize the creation of charts that are outside the platform's scope. Previously assembled in random dashboards (Almacena) and PowerBI (Cupffee). Platform charts (e.g., "Revenue Dynamics") are exported directly and should not be recreated. Each generated chart needs a JSON sidecar so another AI can reproduce it.
>
> Secondary use case: quick data look-ups, with eventual GL-account → invoice drill-down (out of scope for now).

## Repo state survey

```
clients/
├── cupffee/
│   ├── Cupffee Monthly Report - Dec 2025_internal.pptx  ← reference deliverable, 17 slides
│   ├── Taxonomy_Actuals_12.xlsx       full-year 2025 actuals  (BGN)
│   ├── Taxonomy_Actuals_03.xlsx       YTD-Mar 2026 actuals    (currency TBD — likely EUR)
│   ├── Taxonomy_budget_q2.xlsx        Q2 2026 budget, 3 scenarios × 4 statements (EUR)
│   ├── Top_6_Countries_Invoiced_-_LTM_May.csv   country revenue LTM-May (BGN)
│   ├── Top_6_Countries_Invoiced_MTD_May.xlsx    country revenue MTD-May (currency TBD)
│   ├── main.xlsx, main_v2.xlsx        existing manual working files (replace targets)
└── almacena/
    ├── Almacena Management Report Dec.pptx       reference deliverable, 9 slides
    ├── taxonomi_act_12.xlsx        consolidated, full-year 2025         (currency TBD)
    ├── taxonomi_act_q1.xlsx        consolidated, YTD-Mar 2026           ← duplicate of `_1`?
    ├── taxonomi_act_1.xlsx         consolidated, YTD-Mar 2026           ← duplicate of `_q1`?
    ├── ap_12_act.xlsx              AP Foundation, full-year 2025
    ├── foundation_q1 .xlsx         AP Foundation, YTD-Mar 2026 (note trailing space)
    ├── export-2026-36.xlsx         AP Foundation, all-NULL template export — skip
    ├── Profitabilit Report Q126.xlsx   GMV / Funded Amount / Days Outstanding — Q1 2026
    └── main_almacena.xlsx          existing manual working file, sheets `*_cons` & `*_ap`
```

## Architecture changes vs the earlier plan

### 1. Schema gets an `entity` dimension

```sql
CREATE TABLE financials (
    period_date  DATE NOT NULL,
    entity       TEXT NOT NULL,          -- NEW: 'cupffee' | 'consolidated' | 'ap_foundation' | …
    scenario     TEXT NOT NULL CHECK (scenario IN ('actual','pessimistic','realistic','optimistic')),
    statement    TEXT NOT NULL CHECK (statement IN ('IS','CF','BS')),
    data         TEXT NOT NULL,
    grp          TEXT NOT NULL,
    subgroup     TEXT NOT NULL,
    display_order INTEGER NOT NULL,       -- NEW: source row order, see OQ4
    value        REAL,
    PRIMARY KEY (period_date, entity, scenario, statement, data, grp, subgroup)
);
```

Cupffee uses `entity='cupffee'` for every row (single-entity client). Almacena uses `consolidated` and `ap_foundation`. Adding more entities is config-only.

The existing operational tables (`cup_volumes`, `country_revenue`) gain the same `entity` column for consistency, even though they're single-entity today.

### 2. Source-file layout under each client

```
clients/<client>/
├── config.yaml
├── raw/                 ← user drops sources here (gitignored)
│   ├── *.xlsx
│   └── *.csv
├── data/
│   └── <client>.db      ← SQLite output (gitignored)
└── charts/              ← Stage 2 output (gitignored)
    └── <YYYY-MM>/
        ├── <chart_id>.png
        └── <chart_id>.json
```

The `raw/` directory matches the original spec; the `charts/` directory is new for Stage 2.

### 3. Per-source `entity` and `currency` in config

```yaml
client_name: Almacena
fiscal_year_start_month: 1
currency: EUR                     # DB target currency
bgn_to_eur_rate: 1.95583
usd_to_eur_rate: 0.92             # used for the USD profitability file
as_of_date: 2026-03-01

entities:                         # declared up front for validation
  - consolidated
  - ap_foundation

financial_sources:
  - { file: raw/taxonomi_act_12.xlsx, year: 2025, entity: consolidated, currency: EUR }
  - { file: raw/taxonomi_act_q1.xlsx, year: 2026, entity: consolidated, currency: EUR }
  - { file: raw/ap_12_act.xlsx,       year: 2025, entity: ap_foundation, currency: EUR }
  - { file: raw/foundation_q1.xlsx,   year: 2026, entity: ap_foundation, currency: EUR }

operational_sources:
  platform_kpis:
    file: raw/Profitabilit Report Q126.xlsx
    currency: USD                 # the only USD source — converted via usd_to_eur_rate
    entity: consolidated
  country_revenue_ltm: null
  country_revenue_monthly: null
  cup_volumes: null
```

Cupffee's config keeps `entity: cupffee` on every source.

### 4. Stage 2: chart inventory model

A "chart" is identified by a stable `chart_id` (`cupffee.kpi_revenue_monthly`, `almacena.cf_ap_operating_activities`, …). Each chart has:

- A **spec** (input): JSON file under `specs/<client>/<chart_id>.json` checked into the repo. Defines title, type, data queries, styling, **and its own period semantics**. Stable, hand-curated from the reference PPT.
- A **rendered output** (per period): `clients/<client>/charts/<YYYY-MM>/<chart_id>.png` plus a generated `<chart_id>.json` sidecar that snapshots the spec + the resolved data values used to produce the image, so another AI can reproduce the exact chart deterministically.

**Per-chart period semantics.** The CLI takes an *anchor month* (e.g., `2026-03`) — every chart computes its own window from that anchor:

```json
"period": {
  "kind": "current_month"           // pie charts, MTD country bar
  // OR
  "kind": "ytd"                     // most P&L analysis
  // OR
  "kind": "ltm"                     // most P&L analysis
  // OR
  "kind": "month_offset", "offset": -3   // "3 months back" reference
  // OR
  "kind": "full_year", "year": 2025      // appendix yearly statements
  // OR
  "kind": "explicit", "year": 2025, "month": 12   // historical reference
  // OR
  "kind": "range", "start": "current_month-11", "end": "current_month"  // 12-month trend
}
```

The renderer resolves these into concrete date(s) before calling `core.query`.

Renderer pipeline:

```
specs/<client>/<chart_id>.json   ─┐
                                  ├─►  core.query(...)  ─►  matplotlib  ─►  PNG
core.config (period, brand) ─────┘                                         │
                                                                            ├─►  resolved-spec.json
                                                                            (input spec + data + period)
```

**Why matplotlib over Vega-Lite or Plotly:** the chart sidecar JSON is *not* the plotting engine's input — it's a content + values snapshot. So we don't need Vega-Lite to keep the JSON-native property. Matplotlib gives full control over the brand styling that Cupffee's deck demands (colors, fonts, EUR '000 formatting), is dependency-light, and produces high-quality PNG/SVG. The sidecar JSON we design ourselves to be small and AI-readable — it captures the *what* (numbers, period, scenario) plus a `chart_type` tag, not the rendering instructions. Open Question 5 covers this.

### 5. Platform-chart exclusion

A `source: platform` flag in each spec marks platform-export charts (Cupffee's "Revenue Dynamics", Almacena's KPIs slide if applicable). The renderer skips them; the inventory index notes them as "platform export — sourced from <export_path>".

The chart catalog (Tasks 12 & 13) tags each chart explicitly. We'll review the catalog with you before locking it in.

## Dependency Graph

```
pyproject + skeleton
        │
        ▼
core/schema.py (entity column added)
        │
        ▼
core/loaders/financials.py (entity + currency args)
        │
        ▼                              ┌──► core/loaders/country.py (cupffee)
scripts/build_db.py ◄── config.yaml ◄──┼──► core/loaders/platform_kpis.py (almacena)
        │                              └──► core/loaders/cup_volumes.py (stub)
        ▼
core/query.py (entity-aware)
        │
        ▼
scripts/validate.py
        │
        ▼
core/charts/spec.py (JSON schema + loader)
        │
        ▼
core/charts/render.py (matplotlib + sidecar writer)
        │
        ▼               ┌── specs/cupffee/*.json (per chart)
scripts/build_charts.py ┤
                        └── specs/almacena/*.json (per chart)
```

## Slicing strategy

**Stage 1 critical path** delivers a usable DB + query layer for both clients. Stage 2 builds on top.

- **Slice A — Cupffee end-to-end:** schema → loader (BGN-aware) → cupffee config → build → query → validate → render 1 sample chart end-to-end. After this, the entire pipeline works for one client.
- **Slice B — Almacena multi-entity:** add the second client, prove the entity dimension works, validate against the Almacena PPT.
- **Slice C — Chart inventory expansion:** fill out specs for every non-platform chart in both decks.
- **Slice D — Operational data + docs.**

Slices A and B are the primary risk-reducers — they prove the design end-to-end before we invest in chart catalogs.

## Phased Task List

### Phase 1 — Foundation (Slice A start)

- [ ] **Task 1**: Project skeleton + dependencies (incl. matplotlib, openpyxl, pandas, pyyaml, jsonschema) — XS
- [ ] **Task 2**: Schema with `entity` + `display_order` columns; `wipe_and_create(path)` helper — XS

### Checkpoint A
- `uv sync` clean. `python -c "from core.schema import wipe_and_create; wipe_and_create('/tmp/x.db')"` works.

### Phase 2 — Cupffee end-to-end (Slice A)

- [ ] **Task 3**: Financial loader — sheet/row parsing, entity/currency args, BGN→EUR division — M
- [ ] **Task 4**: Cupffee `config.yaml` + `scripts/build_db.py cupffee` — S
- [ ] **Task 5**: Query helpers (entity-aware; `entity` defaults to client's single entity if there's only one) — M
- [ ] **Task 6**: `scripts/validate.py cupffee` — uses spec's 8 actuals assertions verbatim + 3–5 budget cells from `Taxonomy_budget_q2.xlsx` — S

### Checkpoint B (Cupffee data layer green)
- `python scripts/build_db.py cupffee` clean.
- `python scripts/validate.py cupffee` exits 0.
- `from core.query import get_statement; get_statement('IS', '2025-12-01', client='cupffee')` returns expected shape.

### Phase 3 — Almacena multi-entity (Slice B)

- [ ] **Task 7**: Almacena `config.yaml` with two entities + `entities` list validated against per-source `entity` — S
- [ ] **Task 8**: Resolve `taxonomi_act_q1.xlsx` vs `taxonomi_act_1.xlsx` duplication (open question) — XS
- [ ] **Task 9**: Almacena validation — pick 5–8 cells across both entities from the actuals files, lock as assertions — S

### Checkpoint C (Almacena data layer green)
- `python scripts/build_db.py almacena` clean.
- `get_statement('IS', '2025-12-01', client='almacena', entity='consolidated')` returns rows.
- `get_statement('CF', '2025-12-01', client='almacena', entity='ap_foundation')` returns rows.
- `get_aggregation('Sales', '2025-12-01', client='almacena', entity='consolidated', level='grp')` returns dict including `Net Interest Revenue`, `Flat Fee`, …

### Phase 4 — Chart spec + renderer foundation (Slice A continuation)

- [ ] **Task 10**: Chart spec JSON schema (`core/charts/spec.py`) + a single hand-written spec for Cupffee Net Burn vs Gross Burn (the simplest line chart in the deck) — M
- [ ] **Task 11**: Renderer (`core/charts/render.py`) — reads spec, calls `core.query`, produces PNG + resolved-spec sidecar JSON, applies brand styling — M

### Checkpoint D (single chart end-to-end)
- `python scripts/build_charts.py cupffee 2025-12 --only kpi_net_vs_gross_burn` writes `clients/cupffee/charts/2025-12/kpi_net_vs_gross_burn.{png,json}`.
- Visually compare PNG to slide 2 of the reference PPT — close enough that a human would accept it as the same chart.

### Phase 5 — Cupffee chart catalog (Slice C, part 1)

- [ ] **Task 12**: Catalog every non-platform chart in the Cupffee Dec-2025 deck. For each: write a spec JSON. Render all. Build an `index.html` browser. — L (split into 2-3 sub-tasks if charts > ~10)
- [ ] **Task 13**: Mark platform-export charts (Revenue Dynamics, Sales by Channel etc.) in the catalog with `source: platform` and a note pointing at the platform export — XS

### Phase 6 — Almacena chart catalog (Slice C, part 2)

- [ ] **Task 14**: Same as Task 12 for Almacena Dec-2025 deck (9 slides — fewer charts than Cupffee). Each spec carries an `entity` field. — M

### Checkpoint E (chart inventory complete)
- `python scripts/build_charts.py cupffee 2025-12` produces every non-platform chart from the Dec-2025 deck.
- `python scripts/build_charts.py almacena 2025-12` produces the same for Almacena.
- A human compares each generated chart against the reference deck slide-by-slide and signs off.

### Phase 7 — Operational data (Slice D, part 1)

- [ ] **Task 15**: Cupffee country-revenue loader (BGN→EUR, LTM/MTD) — S
- [ ] **Task 16**: Almacena platform-KPIs loader for `Profitabilit Report Q126.xlsx` (GMV, Funded Amount, Days Outstanding) — S
- [ ] **Task 17**: Cup-volumes stub — XS

### Phase 8 — Documentation (Slice D, part 2)

- [ ] **Task 18**: README — quickstart per client, monthly cadence, mid-period correction, multi-entity onboarding, chart-spec authoring guide — S

### Checkpoint F (all spec pass criteria + Stage-2 deliverable)
- All four original Stage-1 pass criteria.
- Both client decks reproducible from raw → DB → charts in two commands per client.
- Chart-spec authoring guide lets someone add a new chart without reading source code.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| `taxonomi_act_q1.xlsx` and `taxonomi_act_1.xlsx` look identical (same Q1 values, same NULL pattern). Loading both could be a no-op or could mask a data-shape difference. | M | Task 8: byte-compare them; if identical, drop one from the config. If they differ, ask user which is canonical. Surface diff before deciding. |
| `foundation_q1 .xlsx` has a trailing space in its filename. Easy to misconfigure. | L | Config encodes the exact filename; build_db raises a clear error if the path doesn't exist. README notes the trailing space. |
| Cupffee's two country-revenue files use BGN in the LTM CSV but the MTD xlsx is unlabelled — could be either. The MTD values (e.g., Qatar 45,907.32) are plausible as either currency. | M | Task 15 reads currency from a `currency:` field per operational source. Default BGN for the LTM CSV (it's prefixed `BGN`); ask user to confirm MTD currency before writing the assertion. |
| Almacena currency: NL/BG entities probably report in EUR, but `taxonomi_act_*` cells are unlabelled. Misclassifying produces a 1.95583× error. | M | Task 7 includes a sanity-check assertion (a known-EUR cell from the reference PPT — e.g., "Net Interest Revenue YTD ended at -149K" from slide 4). If raw cell ≈ -149K → EUR. If raw cell ≈ -291K → BGN. |
| Reference PPT charts are pasted images, so we can't introspect them programmatically. The chart catalog is hand-curated from text on the slide. Risk: missing or mis-titled charts. | M | Task 12 starts by writing a markdown table of every distinct heading/subheading in each slide (already done in the survey above) and asking user to confirm the catalog before any rendering work. |
| "Revenue Dynamics"-pattern detection: can't programmatically tell platform from custom. | L | Each spec JSON has `source: platform | custom`. User confirms during catalog review. Platform-marked charts emit a stub PNG saying "Platform export — see <path>". |
| Brand styling drift: matplotlib defaults won't match the Cupffee deck (Calibri, specific greens/oranges, "EUR '000" axis formatting). | M | Task 11 builds a single `apply_brand(fig, brand)` helper driven by the YAML brand block. Iterate against the reference deck's KPI slide as the visual benchmark. |
| Resolved-spec JSON could grow large (full data dump per chart). | L | Cap at the data points actually plotted (e.g., 12 monthly values, not the full DB). Sidecar is for AI re-rendering — needs only what's drawn. |
| `display_order` collisions across files (a row appears in different positions in budget vs actuals). | L | Last-loaded-wins, same rule as values. Document in README. |

## Decisions (resolved open questions)

1. ~~Validation values~~ — **resolved.** Spec table works once BGN→EUR runs on Cupffee actuals.
2. **Partial-year NULL emission** — **resolved.** Skip null cells by default. Per-source `emit_null_cells: true` flag in `financial_sources` for explicit opt-in.
3. **`get_aggregation` return type** — **resolved.** Always returns `pd.Series`. `level='data'` → 1-element Series indexed by the `data` value. `level='grp'` → Series indexed by Group. `level='subgroup'` → Series with `(Group, Subgroup)` MultiIndex. Diverges from the spec docstring's `float | dict` shape, but uniform return type lets the chart renderer dispatch on `chart_type` only and keeps the public API consistent with the other DataFrame/Series-returning helpers.
4. **`get_statement` source ordering** — **resolved.** `display_order INTEGER NOT NULL` on `financials`, captured at load time as the sheet-local row index. `get_statement` orders by it. Last-loaded-wins on collisions.
5. **Chart engine** — **resolved.** matplotlib + `rcParams` brand styling. Custom JSON sidecar (schema in Task 10). Sidecar is a content snapshot, not the renderer's input.
6. **Almacena currency** — **resolved.** `taxonomi_act_*` files are EUR. `Profitabilit Report Q126.xlsx` is **USD** and needs USD→EUR conversion via a `usd_to_eur_rate` config field. Sanity check still runs at Task 7 for double-confirmation.
7. **MTD country-revenue currency** for Cupffee — *deferred to sanity stage* (Task 15). Will be confirmed against the LTM-prefixed BGN values for the same countries.
8. **Period selection for charts** — **resolved.** Each chart spec declares its own period semantics (`current_month`, `ytd`, `ltm`, `month_offset`, `full_year`, `explicit`). `build_charts.py <client> [<input_month>]` takes an optional anchor month and each chart resolves its window from it. Pie charts → `current_month`. Country bar → `current_month`. Most P&L analysis → `ytd` or `ltm`. Yearly statement appendices → `full_year`.
9. **PowerPoint assembly** — **deferred to Stage 3.** Stage 2 ships PNG + JSON sidecar + `index.html`. Auto-assembled decks come later.

## Stage 3 (deferred)

- Auto-assembled PowerPoint decks: take the rendered chart inventory + a deck template + a `slide_map.yaml` and emit a finished `.pptx`.
- GL-account → invoice drill-down: link each `(data, grp, subgroup)` taxonomy row to its general-ledger account code so invoice-level data can be cross-referenced.

## Verification (skill checklist)

- [x] Every task has acceptance criteria (see `todo.md`)
- [x] Every task has a verification step (see `todo.md`)
- [x] Task dependencies are identified and ordered (graph above)
- [x] No task touches more than ~5 files (Task 12 is L — sub-divided in `todo.md`)
- [x] Checkpoints exist between major phases (A–F)
- [ ] Human has reviewed and approved the plan
