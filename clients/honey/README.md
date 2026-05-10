# Honey

**Use case:** `report` — quarterly monitoring pack (currently Q1 2026).
**Cadence:** quarterly.
**Currency:** EUR.

> **Framework integration is partial.** The financial pipeline can
> already load Honey's two taxonomi files, but the report extract phase
> won't run until `mapping.yaml` is authored. The B2C operational
> charts are produced by a one-off script under `one_offs/` because
> operational subscription data isn't yet modeled in `core/data/`.
> See **Status & gaps** below.

## What goes in

Each period, the following land in `clients/honey/raw/`:

| File | What it is | Source |
|---|---|---|
| `main_26.xlsx` | Master accounting workbook (MR-equivalent), 2026 — quarterly + monthly P&L / CF / BS sheets | Bookkeeper's monthly / quarterly delivery |
| `act_03-26.xlsx` | YTD actuals through March 2026, in canonical taxonomi format | Provided by client / re-keyed from the MR |
| `export-2026-bp.xlsx` | 2026 budget snapshot, Pessimistic + Realistic scenarios, in canonical taxonomi format | Annual budgeting cycle |
| `sales_report/<MM>/B2C SUB *.xlsx` | Per-month B2C subscription roster — one row per subscription with paused-flag and package type | Honey's subscription system export |
| `sales_report/<MM>/B2C Orders *.xlsx` | Per-month B2C orders | Same — currently parked |
| `sales_report/<MM>/B2B Clients *.xlsx` | Per-month B2B clients | Same — currently parked |

The reference deck (the `.pptx` used as the visual benchmark) lives in
`clients/honey/reference/`.

## What happens

1. **Load** the two canonical taxonomi files into SQLite
   (`clients/honey/data/honey.db`) — works today via
   `scripts/build_db.py honey`.
2. **Extract from the MR** — *not yet wired*. Once `mapping.yaml`
   exists, `scripts/build_report.py honey <YYYY-MM> --extract-only` will
   pull the new column from `main_26.xlsx` and append it to the prior
   `taxonomi_act_*.xlsx` (same shape as Farada).
3. **Compute variance** — *future*, lands with the rest of the
   `report` use case (Phase 2 of the cleanup plan).
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

- [ ] `mapping.yaml` not yet authored — blocks `build_report.py honey`.
- [ ] Operational data layer not built — keeps `one_offs/build_slide4.py`
  bespoke. This is option-2 work in the cleanup plan.
- [ ] No assertions in `scripts/validate.py` yet — add once Mar-26
  numbers are signed off.
- [ ] `B2C Orders` and `B2B Clients` sources are present in `raw/` but
  currently unused.

## Running what works today

```bash
# Build the financials DB (works now)
uv run python scripts/build_db.py honey

# Render the slide-4 B2C charts (one-off)
uv run python clients/honey/one_offs/build_slide4.py
```
