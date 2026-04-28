# Monitoring Tool — Task List (Stage 1 + Stage 2)

Companion to `plan.md`. Tasks are sized for one focused session. Phases A–F mirror the checkpoints in the plan.

---

## Phase 1 — Foundation

### Task 1: Project skeleton + dependencies

**Description:** Stand up the package layout, pin Python ≥3.11 with `uv`, declare runtime deps, gitignore raw data + DB output + chart output.

**Acceptance criteria:**
- [ ] `pyproject.toml` declares `requires-python = ">=3.11"` and dependencies: `openpyxl`, `pandas`, `pyyaml`, `python-dateutil`, `matplotlib`, `jsonschema`, `python-pptx` (for slide-text extraction in Task 12).
- [ ] Empty `__init__.py` files: `core/`, `core/loaders/`, `core/charts/`.
- [ ] `.gitignore` excludes `clients/*/raw/`, `clients/*/data/`, `clients/*/charts/`, `.venv/`, `__pycache__/`, `*.pyc`.
- [ ] `uv lock` produces `uv.lock`; `uv sync` succeeds.

**Verification:**
- [ ] `uv run python -c "import openpyxl, pandas, yaml, dateutil, matplotlib, jsonschema, pptx; print('ok')"` prints `ok`.

**Dependencies:** None.

**Files:** `pyproject.toml`, `uv.lock`, `.gitignore`, `core/__init__.py`, `core/loaders/__init__.py`, `core/charts/__init__.py`.

**Scope:** XS.

---

### Task 2: Schema + DB-bootstrap

**Description:** `core/schema.py` with the three-table DDL. `entity` and `display_order` columns added per the new plan. Idempotent `apply()` and destructive `wipe_and_create()` helpers.

**Acceptance criteria:**
- [ ] `financials` PK = `(period_date, entity, scenario, statement, data, grp, subgroup)`. Has `display_order INTEGER NOT NULL`. CHECK on `scenario` and `statement` per spec.
- [ ] `cup_volumes` and `country_revenue` gain an `entity TEXT NOT NULL` column. PKs include `entity`.
- [ ] Indexes on `(period_date)`, `(scenario)`, `(data)`, `(entity)`.
- [ ] `apply(path)` uses `CREATE TABLE IF NOT EXISTS` and is idempotent.
- [ ] `wipe_and_create(path)` deletes the file (if present), then `apply()`.

**Verification:**
- [ ] `wipe_and_create('/tmp/test.db')` produces a file with all three tables; `sqlite3 /tmp/test.db ".schema"` shows the CHECK + PK clauses.

**Dependencies:** Task 1.

**Files:** `core/schema.py`.

**Scope:** XS.

---

## Checkpoint A — Foundation green
- [ ] `uv sync` clean.
- [ ] Schema bootstrap runs.

---

## Phase 2 — Cupffee end-to-end

### Task 3: Financial loader

**Description:** Single canonical loader. Sheet/row parser + per-source `currency` and `entity` args. BGN→EUR division when `currency='BGN'`. Captures `display_order` per source row.

**Acceptance criteria:**
- [ ] Signature: `load_taxonomy_xlsx(path: Path, *, year: int, entity: str, currency: str = 'EUR', fx_rate: float | None = None, emit_null_cells: bool = False) -> Iterable[FinancialRow]`. Raises if `currency != 'EUR'` and `fx_rate` is None. (Generic `fx_rate` covers BGN, USD, future others.)
- [ ] When `currency != 'EUR'`, every numeric cell divided by `fx_rate`. `currency='EUR'` is pass-through.
- [ ] `FinancialRow` is a `NamedTuple` with fields matching the DB columns including `entity` and `display_order`.
- [ ] Sheet name parser: `IS (Realistic)`, `CF Indirect (Realistic)`, `CF (Realistic)`. Whitespace-tolerant. Scenario lowercased.
- [ ] Unknown scenario raises `ValueError` naming the offending sheet.
- [ ] Empty sheet (no row has any non-null monthly value) skipped silently.
- [ ] Row skipped if all 12 monthly cells are null.
- [ ] Default behaviour: skip cells with NULL values (no row emitted for them). Per-source `emit_null_cells: bool = False` flag opts into emitting NULL rows for empty cells.
- [ ] `data` / `grp` / `subgroup` whitespace-stripped.
- [ ] `display_order` = source row index within the sheet; reset per sheet (each statement gets its own ordering, which is what `get_statement` needs).
- [ ] Idempotent: same args → same iteration order.

**Verification:**
- [ ] `list(load_taxonomy_xlsx('clients/cupffee/raw/Taxonomy_Actuals_12.xlsx', year=2025, entity='cupffee', currency='BGN', bgn_to_eur_rate=1.95583))` returns ≥ 100 rows.
- [ ] Spot check: row for `('IS', 'actual', 'Sales', 'Distributors', 'Cupffee 220 ml', 2025-12-01)` has value within 1 EUR of 81,551.52 (proves BGN conversion).
- [ ] No row has `statement='CF'` originating from `CF (Actual)` (empty-sheet skip works).
- [ ] Loading `Taxonomy_Actuals_03.xlsx` with `year=2026, currency='EUR'` produces values for Jan–Mar and (per OQ2 outcome) zero rows or NULL rows for Apr–Dec.
- [ ] Mis-spelling a scenario in a renamed test sheet raises `ValueError`.

**Dependencies:** Task 2.

**Files:** `core/loaders/financials.py`.

**Scope:** M.

---

### Task 4: Cupffee config + build script

**Description:** Move Cupffee source files into `clients/cupffee/raw/`. Write `config.yaml`. Wire `scripts/build_db.py <client>` to drive everything.

**Acceptance criteria:**
- [ ] `clients/cupffee/raw/` contains the three Cupffee taxonomy files.
- [ ] `config.yaml` matches the plan template:
    - `entities: [cupffee]`
    - `financial_sources` lists `Taxonomy_Actuals_12.xlsx` (year=2025, currency=BGN), `Taxonomy_Actuals_03.xlsx` (year=2026, currency=EUR), `Taxonomy_budget_q2.xlsx` (year=2026, currency=EUR), in that order.
- [ ] `currency` defaults to `EUR` when omitted in a source.
- [ ] `python scripts/build_db.py cupffee` resolves `clients/cupffee/`, wipes + recreates `clients/cupffee/data/cupffee.db`.
- [ ] Script validates that every source's `entity` is in the `entities` list; otherwise exits non-zero.
- [ ] Bulk insert uses `INSERT OR REPLACE INTO financials VALUES (...)` so "last loaded wins".
- [ ] Summary printed: rows per table, sheets skipped (with reason), duration.
- [ ] Re-running produces identical row counts.

**Verification:**
- [ ] `sqlite3 clients/cupffee/data/cupffee.db "SELECT COUNT(*) FROM financials WHERE entity='cupffee'"` matches the script's printed count.
- [ ] Re-running yields the same count.
- [ ] Spot-check a known cell.

**Dependencies:** Task 3.

**Files:** `clients/cupffee/raw/<files>` (move), `clients/cupffee/config.yaml`, `scripts/build_db.py`.

**Scope:** S.

---

### Task 5: Query helpers

**Description:** The seven public helpers from the spec, entity-aware. They are the only surface Stage 2 imports.

**Acceptance criteria:**
- [ ] All helpers accept `client: str` (no default — explicit) and `entity: str | None` (default = client's single entity if `len(entities)==1`, else required).
- [ ] Helpers: `get_value`, `get_line`, `get_statement`, `get_aggregation`, `get_trend`, `ytd`, `to_csv`. Signatures match the spec, plus `client` and `entity`.
- [ ] `get_statement` orders by `display_order ASC`.
- [ ] `get_aggregation` always returns `pd.Series`. `level='data'` → 1-element Series indexed by the `data` value. `level='grp'` → Series indexed by Group. `level='subgroup'` → Series with `(Group, Subgroup)` MultiIndex. NULLs excluded from sums.
- [ ] Period args accept `datetime.date | str ('YYYY-MM-DD')`.
- [ ] `to_csv` writes via `pandas.DataFrame.to_csv`; wraps scalars/dicts into a 1-row DataFrame.
- [ ] Connection lifecycle: open/close per call; no module-level state.

**Verification:**
- [ ] `get_statement('IS', '2025-12-01', client='cupffee')` returns ordered rows; first `data` value = `Sales`.
- [ ] `get_aggregation('Sales', '2025-12-01', client='cupffee', level='grp')` returns dict including `Distributors`, `Direct Sales`, `Retail`.
- [ ] `get_trend('Sales', client='cupffee', start_date='2025-01-01', end_date='2025-12-01')` returns 12-element series.
- [ ] `ytd('Sales', 2025, client='cupffee')` matches `sum(get_trend(...))`.

**Dependencies:** Task 4.

**Files:** `core/query.py`.

**Scope:** M.

---

### Task 6: Cupffee validation

**Description:** Implement `scripts/validate.py`. The 8 actuals assertions from the spec table are used verbatim. Add 3–5 budget cells from `Taxonomy_budget_q2.xlsx` against `realistic`. Tolerance 1 EUR.

**Acceptance criteria:**
- [ ] CLI: `python scripts/validate.py cupffee`. Reads same config as build_db.
- [ ] Hard-codes the 8 actuals assertions.
- [ ] 3–5 budget assertions sourced by inspecting raw cells, copied verbatim into the script.
- [ ] On failure: print query, expected, observed, delta. Exit non-zero.

**Verification:**
- [ ] `python scripts/validate.py cupffee && echo OK` prints `OK`.

**Dependencies:** Task 5.

**Files:** `scripts/validate.py`.

**Scope:** S.

---

## Checkpoint B — Cupffee data layer green
- [ ] `build_db.py cupffee` clean. `validate.py cupffee` exits 0. `get_statement` works end-to-end.

---

## Phase 3 — Almacena multi-entity

### Task 7: Almacena config + currency sanity check

**Description:** Move Almacena sources into `clients/almacena/raw/`. Write `config.yaml` declaring two entities. Sanity-check `taxonomi_act_*` currency by spot-comparing against the reference PPT's narrative numbers.

**Acceptance criteria:**
- [ ] `clients/almacena/raw/` contains the four canonical taxonomy files (consolidated × {full-year, Q1}, AP foundation × {full-year, Q1}). Trailing-space filename `foundation_q1 .xlsx` either renamed or quoted in config.
- [ ] `config.yaml` declares `entities: [consolidated, ap_foundation]`. Each `financial_sources` entry has `entity:` set.
- [ ] Pre-build sanity check (one-shot script or comment in config): pick a number from the PPT (e.g., AP Foundation Net Interest Revenue YTD 2025 ≈ -149K per slide 4) and verify the raw cell from `ap_12_act.xlsx` matches that scale → confirms EUR vs BGN.
- [ ] If currency check passes for EUR, all Almacena sources tagged `currency: EUR`.

**Verification:**
- [ ] `python scripts/build_db.py almacena` clean.
- [ ] `sqlite3 clients/almacena/data/almacena.db "SELECT DISTINCT entity FROM financials"` returns both entities.

**Dependencies:** Tasks 4, 5 (need the build path working first).

**Files:** `clients/almacena/raw/<files>`, `clients/almacena/config.yaml`.

**Scope:** S.

---

### Task 8: Resolve `taxonomi_act_q1.xlsx` vs `taxonomi_act_1.xlsx`

**Description:** The two files look identical from sample rows. Determine canonical and drop or keep both.

**Acceptance criteria:**
- [ ] Run a cell-by-cell diff across all four sheets. If identical, drop one from the config and from `raw/`.
- [ ] If different, surface the diff to the user and ask which is canonical.
- [ ] Outcome documented in `tasks/plan.md` under "Decisions".

**Verification:**
- [ ] Build runs the same after the resolution.

**Dependencies:** Task 7.

**Files:** `clients/almacena/config.yaml`, possibly `clients/almacena/raw/`.

**Scope:** XS.

---

### Task 9: Almacena validation

**Description:** Empirically pick 5–8 cells across both entities. Hard-code as assertions in `validate.py almacena`.

**Acceptance criteria:**
- [ ] Script accepts `cupffee | almacena` and dispatches.
- [ ] Almacena assertions cover both `consolidated` and `ap_foundation`, both 2025-12 and 2026-Q1.
- [ ] Each assertion's expected value picked by reading the raw file and copying into the script (no spec table for Almacena).
- [ ] Tolerance 1 EUR.

**Verification:**
- [ ] `python scripts/validate.py almacena && echo OK` prints `OK`.

**Dependencies:** Tasks 7, 8.

**Files:** `scripts/validate.py`.

**Scope:** S.

---

## Checkpoint C — Almacena data layer green
- [ ] Both clients build + validate clean.
- [ ] `get_statement(..., entity='ap_foundation')` returns AP Foundation rows; `entity='consolidated'` returns Almacena Group rows.

---

## Phase 4 — Chart spec + renderer

### Task 10: Chart spec schema + first hand-written spec

**Description:** Define the JSON schema for chart specs. Write the first spec for Cupffee Net Burn vs Gross Burn (slide 2 — the simplest line chart) so we can test the pipeline.

**Acceptance criteria:**
- [ ] `core/charts/spec.py` defines:
    - JSON schema (validated via `jsonschema`).
    - `ChartSpec` dataclass.
    - `load_spec(path) -> ChartSpec`.
- [ ] Schema fields (proposed):
    - `chart_id` (str, stable id)
    - `client` (str)
    - `title` (str)
    - `chart_type` (`line` | `bar` | `stacked_bar` | `donut` | `waterfall` | `kpi_card` | …)
    - `source` (`custom` | `platform`)
    - `entity` (str | null — null means client default)
    - `period` (object: `{kind: 'current_month'|'ytd'|'ltm'|'month_offset'|'full_year'|'explicit'|'range', …}` — see plan §4 for shape)
    - `data` (list of query dicts: each is `{kind: 'trend'|'value'|'aggregation', args: {...}}`; `args` reference `period` symbolically (e.g. `"period_anchor"`, `"period_anchor-3"`) and the renderer resolves them against the chart's `period` block)
    - `axes` (`x`, `y`, `y2` formatting: currency, suffix `'000`, format string)
    - `style` (overrides for the brand defaults — usually empty)
    - `notes` (free-text shown beneath the chart in the index)
- [ ] First spec written: `specs/cupffee/kpi_net_vs_gross_burn.json`.
- [ ] `load_spec()` validates the spec against the schema and raises a clear error on violations.

**Verification:**
- [ ] `python -c "from core.charts.spec import load_spec; print(load_spec('specs/cupffee/kpi_net_vs_gross_burn.json'))"` prints the parsed spec.
- [ ] Mutating a required field in-memory and re-validating raises.

**Dependencies:** Task 5 (needs query layer).

**Files:** `core/charts/spec.py`, `core/charts/spec_schema.json`, `specs/cupffee/kpi_net_vs_gross_burn.json`.

**Scope:** M.

---

### Task 11: Renderer

**Description:** Reads a spec, calls `core.query` to resolve data, produces PNG + sidecar JSON. Applies brand styling.

**Acceptance criteria:**
- [ ] `core/charts/render.py` exposes `render(spec, period, brand, out_dir) -> (png_path, json_path)`.
- [ ] Resolves each `data` entry via `core.query`.
- [ ] Maps `chart_type` to a matplotlib drawing routine. Initial coverage: `line`, `bar`, `stacked_bar`, `donut`, `kpi_card`. Other types raise `NotImplementedError` until added.
- [ ] Brand applied via a single `apply_brand(fig, brand)` helper sourced from `config.yaml`'s `brand:` block.
- [ ] PNG size, DPI, fonts come from brand config (defaults usable).
- [ ] Sidecar JSON written: `{spec: <input spec>, period: <period>, resolved_data: <data points actually plotted>, generated_at: <timestamp>}`. Sized to be small (≤ 100 KB typically).
- [ ] `scripts/build_charts.py <client> <period> [--only chart_id]` walks `specs/<client>/*.json`, renders each, writes outputs to `clients/<client>/charts/<period>/`. Skips `source: platform` charts and writes a placeholder PNG noting "platform export — see <export_path>".

**Verification:**
- [ ] `python scripts/build_charts.py cupffee 2025-12 --only kpi_net_vs_gross_burn` produces `clients/cupffee/charts/2025-12/kpi_net_vs_gross_burn.{png,json}`.
- [ ] PNG, when viewed, looks plausibly close to slide 2's Net Burn vs Gross Burn chart.
- [ ] Sidecar JSON has the resolved monthly values for both lines plus the spec.

**Dependencies:** Task 10.

**Files:** `core/charts/render.py`, `scripts/build_charts.py`.

**Scope:** M.

---

## Checkpoint D — Single chart end-to-end
- [ ] One chart renders. Visual spot-check vs reference deck. Sidecar JSON readable and complete.

---

## Phase 5 — Cupffee chart catalog

### Task 12: Catalog and write specs for every non-platform Cupffee chart

**Description:** Enumerate every chart in the Cupffee Dec-2025 deck. Tag each as `custom` or `platform`. Write a JSON spec for each `custom` chart. Render all. Build an `index.html` browser.

**Sub-task 12a: catalog & sign-off (review checkpoint)**
- [ ] Produce `specs/cupffee/_catalog.md`: a table of (slide, chart_title, chart_type proposal, source proposal, notes).
- [ ] Pause for user review and sign-off before writing specs.

**Sub-task 12b: write specs for custom charts**
- [ ] One JSON spec per custom chart in `specs/cupffee/`.
- [ ] Cover the chart types from sub-task 12a (line, bar, donut, etc.).

**Sub-task 12c: index.html**
- [ ] `scripts/build_charts.py cupffee 2025-12` also generates `clients/cupffee/charts/2025-12/index.html` with thumbnails, titles, and "platform export — see X" placeholders for the excluded ones.

**Acceptance criteria (whole task):**
- [ ] All non-platform Dec-2025 Cupffee charts render.
- [ ] Each rendered chart has a sidecar JSON.
- [ ] Platform charts represented in the index with a note pointing at the export file.

**Verification:**
- [ ] Side-by-side comparison vs the reference PPT slide-by-slide.

**Dependencies:** Task 11.

**Files:** `specs/cupffee/<many>.json`, `specs/cupffee/_catalog.md`, `scripts/build_charts.py` (index.html generation).

**Scope:** L (sub-divided above).

---

### Task 13: Mark platform-export charts

**Description:** During catalog review (sub-task 12a), mark platform-pattern charts (Revenue Dynamics, etc.) with `source: platform`. Renderer emits placeholder + index entry.

**Acceptance criteria:**
- [ ] Platform charts catalogued with `source: platform` and a `platform_export: <relative path>` field.
- [ ] Renderer's placeholder PNG is consistent across platform charts (1 helper).

**Dependencies:** Subsumed by Task 12.

**Scope:** XS (within Task 12).

---

## Phase 6 — Almacena chart catalog

### Task 14: Catalog + specs for Almacena

**Description:** Same shape as Task 12 for Almacena's 9-slide deck. Each spec carries an `entity` field (`consolidated` or `ap_foundation`).

**Acceptance criteria:**
- [ ] `specs/almacena/_catalog.md` produced and signed off.
- [ ] Specs written for all custom charts; entity tagged correctly per slide (slides 5–6 use `consolidated`, slide 7 uses `ap_foundation`, slide 4 may mix).
- [ ] `python scripts/build_charts.py almacena 2025-12` renders all custom charts.

**Verification:**
- [ ] Side-by-side comparison vs reference PPT.

**Dependencies:** Tasks 11, 12.

**Files:** `specs/almacena/<many>.json`, `specs/almacena/_catalog.md`.

**Scope:** M.

---

## Checkpoint E — Chart inventory complete
- [ ] Both clients' decks reproducible from raw → DB → charts.
- [ ] Visual sign-off for both decks.

---

## Phase 7 — Operational data

### Task 15: Cupffee country-revenue loader

**Description:** Read `Top_6_Countries_Invoiced_-_LTM_May.csv` (BGN, prefixed) and `Top_6_Countries_Invoiced_MTD_May.xlsx` (currency TBD per OQ7). Convert to EUR. Stamp `period_date` and `period_type`.

**Acceptance criteria:**
- [ ] `core/loaders/country.py` exposes `load_country_csv(path, period_type, period_date, currency, bgn_to_eur_rate)` and `load_country_xlsx(...)`.
- [ ] LTM `period_date` = `(as_of_date - 12 months).replace(day=1)`.
- [ ] Monthly `period_date` = `as_of_date.replace(day=1)`.
- [ ] BGN values: strip `BGN ` prefix, parse number, divide by `bgn_to_eur_rate`.
- [ ] Wired into `build_db.py` behind config keys; no-op when null.

**Verification:**
- [ ] With both keys configured for Cupffee, `country_revenue` table has > 0 rows after build.
- [ ] Spot-check one country's EUR value.

**Dependencies:** Tasks 4, 11 (chart catalog drives the format need).

**Files:** `core/loaders/country.py`, `scripts/build_db.py`, `clients/cupffee/config.yaml`.

**Scope:** S.

---

### Task 16: Almacena platform-KPIs loader

**Description:** Load `Profitabilit Report Q126.xlsx` (GMV, Funded Amount, Average Days Outstanding) into a new `platform_kpis` table, parallel to `cup_volumes`. **File is in USD** — convert to EUR via `usd_to_eur_rate` from config. Note: `Average Days Outstanding` is unitless — do NOT convert; only currency-typed metrics get FX'd.

**Acceptance criteria:**
- [ ] New table in `core/schema.py`:

  ```sql
  CREATE TABLE platform_kpis (
      period_date DATE NOT NULL,
      entity TEXT NOT NULL,
      metric TEXT NOT NULL,         -- 'gmv' | 'funded_amount' | 'avg_days_outstanding' | …
      unit TEXT,                    -- 'EUR' for currency metrics, NULL for unitless
      value REAL,
      PRIMARY KEY (period_date, entity, metric)
  );
  ```
- [ ] Currency metrics (`gmv`, `funded_amount`) are converted USD→EUR and stored with `unit='EUR'`. Unitless metrics (`avg_days_outstanding`) are stored as-is with `unit=NULL`.
- [ ] `core/loaders/platform_kpis.py` reads a wide xlsx (months across columns, metrics down rows), pivots to long format.
- [ ] Wired into Almacena build only.
- [ ] Query helper `get_platform_kpi(metric, period_date, client, entity)` added to `core/query.py`.

**Verification:**
- [ ] `sqlite3 clients/almacena/data/almacena.db "SELECT * FROM platform_kpis WHERE period_date='2026-01-01'"` returns the 3 metrics.

**Dependencies:** Tasks 7, 11.

**Files:** `core/schema.py` (additive), `core/loaders/platform_kpis.py`, `scripts/build_db.py`, `core/query.py`.

**Scope:** S.

---

### Task 17: Cup-volumes stub

**Description:** Placeholder loader matching the operational-loader interface; no-op when null.

**Acceptance criteria:**
- [ ] `core/loaders/cup_volumes.py` exposes `load_cup_volumes(path) -> Iterable[tuple]`.
- [ ] Empty/null → empty iterator. Non-empty → `NotImplementedError` with TODO message.

**Verification:**
- [ ] Build script summary: "cup_volumes: not configured".

**Dependencies:** Task 4.

**Files:** `core/loaders/cup_volumes.py`.

**Scope:** XS.

---

## Phase 8 — Documentation

### Task 18: README

**Description:** Document operator workflows for both clients.

**Acceptance criteria:**
- [ ] Quickstart per client: `uv sync` → drop sources in `raw/` → `python scripts/build_db.py <client>` → `python scripts/validate.py <client>` → `python scripts/build_charts.py <client> <period>`.
- [ ] "Add a new month of data": replace the year file in `raw/`, rerun build + charts.
- [ ] "Add a new entity": append to `entities`, add `entity:` to each new source.
- [ ] "Onboard a new client": copy `clients/<existing>/config.yaml`, edit, drop sources, run.
- [ ] "Add a new chart": write a spec JSON, drop into `specs/<client>/`, rerun `build_charts`.
- [ ] "Mid-year budget revision": append the new file *after* the old one in `financial_sources`, rerun.
- [ ] Sign convention: stored as in source. Costs positive in IS. Cash outflows negative in CF.
- [ ] Note `display_order` quirk and "last loaded wins" rule.

**Verification:**
- [ ] A second person reading the README can run both client pipelines cold.

**Dependencies:** Tasks 1–17.

**Files:** `README.md`.

**Scope:** S.

---

## Checkpoint F — All deliverables met
- [ ] Both client decks reproducible end-to-end.
- [ ] Validation green for both.
- [ ] Quick-check use case demonstrated: a one-liner like `python -c "from core.query import get_value; print(get_value('Cash and cash equivalents', 'Cash and cash equivalents', 'Cash and cash equivalents', '2025-12-01', client='cupffee'))"` returns the value.
- [ ] All open questions resolved and documented.
- [ ] Plan signed off.
