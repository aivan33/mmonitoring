# Honey

**Use case:** `report` — quarterly monitoring pack (currently Q1 2026).
**Cadence:** quarterly.
**Currency:** EUR.

> **Financial pipeline live; operational charts still bespoke.** The
> report extract + reconcile phases work end-to-end (see
> [`mapping.yaml`](mapping.yaml)). Variance + commentary land in Phase 2.
> The B2C subscription charts on slide 4 still come from a one-off
> renderer under [`one_offs/`](one_offs/) because operational data isn't
> yet modeled in `core/data/`. See **Status & gaps** below.

## What goes in

Each period, the following land in `clients/honey/raw/`:

| File | What it is | Source |
|---|---|---|
| `main_26.xlsx` | Master accounting workbook (MR-equivalent), 2026 — quarterly + monthly P&L / CF / BS sheets | Bookkeeper's monthly / quarterly delivery |
| `taxonomi_act_<YYYY-MM>.xlsx` | YTD actuals through month MM, in canonical taxonomi format. The first one was supplied by the client; subsequent months are produced by the framework's extract phase. | Client / extract pipeline |
| `export-2026-bp.xlsx` | 2026 budget snapshot, Pessimistic + Realistic scenarios, in canonical taxonomi format | Annual budgeting cycle |
| `sales_report/<MM>/B2C SUB *.xlsx` | Per-month B2C subscription roster — one row per subscription with paused-flag and package type | Honey's subscription system export |
| `sales_report/<MM>/B2C Orders *.xlsx` | Per-month B2C orders | Same — currently parked |
| `sales_report/<MM>/B2B Clients *.xlsx` | Per-month B2B clients | Same — currently parked |

The reference deck (the `.pptx` used as the visual benchmark) lives in
`clients/honey/reference/`.

## What happens

1. **Load** the two canonical taxonomi files into SQLite
   (`clients/honey/data/honey.db`) via `scripts/build_db.py honey`.
2. **Extract from the MR** — `scripts/build_report.py honey <YYYY-MM>
   --extract-only` pulls the new month from `main_26.xlsx` (sheets
   `is - yearly26` / `cf - yearly26` / `bs - yearly26`) and appends it
   to the prior `taxonomi_act_*.xlsx`. Mapping is in
   [`mapping.yaml`](mapping.yaml) with an `mr_layout:` block that
   describes Honey's row-1 / month-name-string headers.
3. **Compute variance** — *Phase 2 work in progress*.
4. **Render slide-4 B2C charts** — produced today by the one-off
   `clients/honey/one_offs/build_slide4.py`. This bypasses the SQLite
   layer because the subscription data is operational, not financial.

## What comes out

`clients/honey/one_offs/_out/`:

- `slide4_active_b2c.png` — Active subscriptions by package, stacked
- `slide4_flow_b2c.png` — Subscription flow (New / Resumed / Cancelled / Paused)

`clients/honey/reports/<YYYY-Qn>/`:

- `slides.md` — narrative for the deck (currently hand-written;
  will be generated once the `text` use case lands)

`clients/honey/raw/taxonomi_act_<YYYY-MM>.xlsx` — *future*, once
`mapping.yaml` and the report pipeline are wired.

## What to sanity-check each period

- **Subscription file column shape.** The one-off reads col 6 (`На пауза`)
  and col 11 (`Тип на абонамента`) — if the export schema changes,
  the script silently miscounts. Diff against a known-good month before
  trusting the chart.
- **Latin AM vs Cyrillic АМ.** Both mean "Subscription"; the script
  merges them. New package codes are dropped with no warning — check
  the per-month totals printed by the script for a sudden gap.
- **Numbers reconcile with the prior period's deck.** Same discipline
  as Cupffee: a moved KPI is a data error, not a chart error.

## Status & gaps

- [ ] `kpi_derivations` block in `mapping.yaml` is empty pending
  accounting confirmation of the formulas for Working Capital,
  AR/AP Turnover, and Gross Fixed Assets. Until populated, those rows
  in the new month's taxonomi will be empty — fill manually or wait.
- [ ] Operational data layer not built — keeps `one_offs/build_slide4.py`
  bespoke. This is option-2 work in the cleanup plan.
- [ ] No assertions in `scripts/validate.py` yet — add once Mar-26
  numbers are signed off.
- [ ] `B2C Orders` and `B2B Clients` sources in `raw/sales_report/` are
  currently unused.

## Running what works today

```bash
# Build the financials DB
uv run python scripts/build_db.py honey

# Extract a new month from the MR into a fresh canonical taxonomi
uv run python scripts/build_report.py honey 2026-04 --extract-only

# Render the slide-4 B2C charts (one-off)
uv run python clients/honey/one_offs/build_slide4.py
```
