# Architecture

The system has one shared data layer and three downstream use cases. A
client declares which use cases apply to them; each use case is an
independent pipeline that reads from the data layer.

```
       raw client sources                       canonical taxonomi (xlsx)
              │                                          │
              ▼                                          ▼
  ┌───────────────────────────┐               ┌────────────────────┐
  │  per-client ingest        │──────────────▶│   SQLite financials │
  │  (financials.py / mr.py)  │               │   table             │
  └───────────────────────────┘               └────────────────────┘
                                                        │
                ┌───────────────────────────────────────┼─────────────────────────────┐
                ▼                                       ▼                             ▼
       ┌──────────────────┐                   ┌──────────────────┐          ┌──────────────────┐
       │  charts          │                   │  text            │          │  report          │
       │  spec + renderer │                   │  (planned)       │          │  reconcile +     │
       │  → PNG + JSON    │                   │  templates →     │          │  variance +      │
       │                  │                   │  Markdown blocks │          │  commentary →    │
       │                  │                   │                  │          │  Markdown pack   │
       └──────────────────┘                   └──────────────────┘          └──────────────────┘
```

## The shared data layer

### Canonical taxonomi format

All financial data lands as `.xlsx` files in a fixed shape — every
row is keyed by `(Data, Group, Subgroup)` and every column is a month.

| Col 1 | Col 2 | Col 3 | Col 4 | Col 5 | … | Col 15 |
|-------|-------|-------|-------|-------|---|--------|
| `Data` | `Group` | `Subgroup` | `Jan` | `Feb` | … | `Dec` |
| Sales | Distributors | Cupffee 220 ml | 2550 | 4675 | … | 9384 |

- Row 1 is the header. Row 2+ are data rows.
- `Data` / `Group` / `Subgroup` are always non-null on a data row.
  When a category has no further breakdown, `Subgroup` repeats `Group`.
- A row with all-null monthly values is **skipped**.
- A null cell within a row is loaded as **NULL**, not zero.
- The year is **not** in the file. It comes from `config.yaml`'s
  `financial_sources` list, which pairs each file with its year.

A file may contain multiple sheets, one per `(statement, scenario)`
combination, named like `IS (Realistic)`, `BS (Pessimistic)`,
`CF Indirect (Realistic)`. For actuals, single-scenario sheets:
`IS (Actual)`, `BS (Actual)`, `CF Indirect (Actual)`.

Subtotals (Gross Profit, EBITDA, Total Assets, Net Profit, etc.) are
**not** in the source. They are computed downstream at query time.

### SQLite schema

```sql
CREATE TABLE financials (
    period_date    DATE NOT NULL,
    entity         TEXT NOT NULL,
    scenario       TEXT NOT NULL CHECK (scenario IN ('actual','pessimistic','realistic','optimistic')),
    statement      TEXT NOT NULL CHECK (statement IN ('IS','CF','BS')),
    data           TEXT NOT NULL,
    grp            TEXT NOT NULL,
    subgroup       TEXT NOT NULL,
    display_order  INTEGER NOT NULL,
    value          REAL,
    PRIMARY KEY (period_date, entity, scenario, statement, data, grp, subgroup)
);
```

- **Sign convention**: values stored exactly as the source represents
  them. Cash outflows negative in CF, costs positive in IS, etc.
- **Period**: ISO `DATE`, always first-of-month.
- **No accounts taxonomy table**. Hierarchy lives in
  `(data, grp, subgroup)`. Aggregations happen at query time via
  `GROUP BY`.
- **`display_order`** captures the source row index so statements
  read back in their authoring order.
- **`entity`** carries multi-entity clients (e.g. consolidated +
  subsidiary). Single-entity clients use one entity name throughout.
- **Last-loaded-wins**. If two sources cover the same key, the file
  later in `config.yaml`'s `financial_sources` overrides the earlier.
  - **Sharp edge.** Override only happens on cells the later source
    actually writes. Because null cells are skipped by default (see the
    schema notes above), a later source that *blanks* a previously
    populated cell does not clear it — the stale value from the earlier
    source survives. This matters for revision files that intentionally
    zero out or remove a line. To make a source's blanks authoritative,
    set `emit_null_cells: true` on that entry in `financial_sources`; it
    then emits explicit NULLs that overwrite the earlier value.

### Query layer

`core.data.query` exposes the read API. Use cases never touch SQLite
directly — they go through the helpers:

```python
get_value(data, grp, subgroup, period_date, scenario, *, client, entity)
get_line(data, grp, subgroup, scenarios, periods, *, client, entity)
get_statement(statement, period_date, scenarios, *, client, entity)
get_aggregation(data, period_date, scenario, level, *, client, entity)
get_trend(data, grp, subgroup, scenario, start_date, end_date,
          fallback_scenario, *, client, entity)
ytd(data, year, grp, subgroup, scenario, through_month, *, client, entity)
```

`fallback_scenario` lets rolling charts fill forward months from
budget when actuals haven't landed yet — used by Cupffee's
cash-balance and cash-breakdown rolling specs.

## The three use cases

### `charts`

Produces visual artefacts for slide decks.

- **Input:** chart specs in `clients/<client>/chart_specs/*.json`
  (one JSON per chart, schema in `core/charts/spec_schema.json`).
- **Pipeline:** `scripts/build_charts.py <client> <YYYY-MM>` resolves
  each spec's period (current_month / ytd / ltm / explicit / range
  etc.), pulls the data via `core.data.query`, renders via matplotlib,
  emits a PNG + a JSON sidecar.
- **Output:** `clients/<client>/charts/<YYYY-MM>/{*.png, *.json,
  index.html}`. The JSON sidecar snapshots the input spec plus the
  resolved data values, so another tool can reproduce the chart
  deterministically.

The renderer is in `core/charts/render.py`.

### `text` (planned)

Produces narrative blocks (executive summaries, KPI callouts,
commentary paragraphs) from templates with a unified voice and
per-client overrides.

- **Input:** global templates in `config/text.yaml` (planned),
  per-client overrides in `clients/<client>/config.yaml`.
- **Output:** Markdown blocks consumable by either the deck assembly
  step (charts use case) or the report use case.

The package `core/text/` is a stub today; the engine is forward-looking.

### `report`

Produces a full monthly reporting pack from a client's master
accounting workbook. Per-client and bespoke — the input shape and
mapping logic are different for each client.

- **Input:** the client's master workbook (e.g. Farada's DATEV-derived
  MR file) + the prior month's taxonomi-actual file + a mapping in
  `clients/<client>/mapping.yaml`.
- **Pipeline:** `scripts/build_report.py <client> <YYYY-MM>` runs the
  phases in order:
  1. **extract** — read the new month's column from the master
     workbook, write a populated taxonomi-actual file alongside the
     prior month's (preserving formatting via openpyxl
     load-modify-save).
  2. **reconcile** — compare prior months between the master workbook
     and the taxonomi to surface data-prep drift; emit `reconcile.md`.
  3. **variance** — Actual vs Realistic budget, MoM, YTD for IS/CF/BS;
     emit `variance.md` + `variance.csv`.
  4. **commentary** — Markdown outline mirroring the prior period's
     deliverable, with key figures interpolated and material variances
     flagged; emit `commentary.md` + `checklist.md`.
- **Output:** `clients/<client>/reports/<YYYY-MM>/*.md`.

Phases 3 and 4 (variance + commentary) are stubbed pending future work
— the CLI raises `NotImplementedError` for those phases today.

The package is `core/report/`.

## Configuration

### Per-client `config.yaml`

```yaml
client_name: <Client>
fiscal_year_start_month: 1
currency: EUR
as_of_date: <YYYY-MM-DD>           # latest closed month

use_cases: [charts]                # or [report], or [charts, report], ...

entities:
  - <entity_name>

financial_sources:
  - { file: raw/<file>.xlsx, year: <YYYY>, entity: <name>, currency: EUR }
  - ...

# charts use case
brand:
  primary: "#..."
  accent: "#..."
  # ...

# report use case
reporting:
  mr_source: raw/mr_<YYYY-MM>.xlsx
  mapping: mapping.yaml
  reference_pdf: reference/<prior>.pdf
  carryover_topics: [ ... ]
  variance_thresholds: { flag_pct: 20, flag_eur: 10000, reconcile_eur: 5 }
```

### Unified config + per-client overrides (planned)

For `charts` and `text`, the long-term pattern is a global config
with per-client overrides:

- `config/charts.yaml` — global styling defaults (font, axis format,
  EUR '000 formatter, default palette).
- `config/text.yaml` — global voice and structure templates.
- `clients/<client>/config.yaml`'s `brand:` block (or `voice:` block)
  overrides specific keys.

This is forward-looking — Cupffee's full styling currently lives in
its own `brand:` block. A "charts lab" (Phase 4 of the cleanup, see
issue #3) will iterate styling decisions on neutral data before
extracting unified defaults.

The `report` use case does **not** use this pattern. Each client's
report is bespoke enough that a unified config doesn't help; instead,
each report-use-case client gets a `clients/<client>/onboarding.md`
checklist documenting its setup.
