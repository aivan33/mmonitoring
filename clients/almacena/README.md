# Almacena

**Use case:** `charts` — investor-deck chart inventory.
**Cadence:** quarterly (currently Q1 2026; Dec 2025 deck is the visual benchmark).
**Currency:** EUR (financial taxonomies). Operational platform KPIs are
USD; the loader converts at the rate in `config.yaml`.

> **Currency on Profitability Q1 needs sign-off.** The USD→EUR rate
> (`0.92` in `config.yaml > currencies > USD`) was carried forward from
> the archived config. Verify with the team before chart numbers ship.

Two tracked entities: `consolidated` and `ap_foundation`. Charts can
target either or compare both side-by-side.

## What goes in

Each period, the following land in `clients/almacena/raw/`:

| File | What it is | Source |
|---|---|---|
| `taxonomi_act_<MM/QN>.xlsx` | Consolidated YTD actuals through period, canonical taxonomi format | Provided by client / re-keyed from accounting |
| `<entity>_q<N>.xlsx` (e.g. `foundation_q1.xlsx`, `ap_12_act.xlsx`) | Per-entity actuals in canonical taxonomi format | Same |
| `profitability_q<N>.xlsx` | Platform KPIs by month (GMV, Funded Amount, Avg Days Outstanding, # Invoices, # Boxes, % GMV Insured, Arrangement Fees) — wide layout, rows = KPIs, columns = months | Internal platform export (USD) |

The reference deck (the `.pptx` used as the visual benchmark) lives in
`clients/almacena/reference/`.

## What happens

1. **Load** all financial source files into a SQLite database
   (`clients/almacena/data/almacena.db`). Each file is stamped to its
   entity (`consolidated` or `ap_foundation`).
2. **Load operational KPIs** from the `operational_sources` block —
   *Phase 2.5 work in progress*. KPIs become a separate table queried
   by chart specs that need platform metrics.
3. **Render** every chart in the inventory by reading its spec
   (`chart_specs/*.json`), pulling the underlying data, and producing
   a PNG + a JSON sidecar that snapshots the resolved numbers.
4. **Index** the rendered charts in a single HTML page for review.

## What comes out

`clients/almacena/charts/<YYYY-MM>/`:

- One `.png` per chart in the inventory
- One `.json` sidecar per chart — captures the input spec plus the
  resolved numbers (so another tool could redraw the chart from
  scratch and reach the same picture)
- `index.html` — contact-sheet view of every chart on one page

## What to sanity-check each period

- **USD → EUR conversion sanity.** Profitability KPIs land in USD;
  charts render in EUR. A rate mistake shifts every USD-derived number
  by the same factor — easy to spot if a known KPI is ~10% off the
  expected magnitude.
- **Multi-entity sanity.** Per-entity charts must filter to the right
  entity; `consolidated` aggregates both, `ap_foundation` is one
  entity only. A chart that accidentally drops the entity filter will
  show double or wrong numbers.
- **Numbers reconcile with the prior period's deck.** A moved KPI is a
  data error, not a chart error.
- **`reference/Almacena Management Report Dec.pptx`** is the canonical
  layout reference for the deck. New chart variants should match its
  visual style.

## Status & gaps

- [ ] **Currency on `profitability_q1.xlsx` needs team confirmation**
  (USD assumed, rate 0.92).
- [ ] **Operational KPIs loader not yet built** — `operational_sources`
  declares the file but nothing reads it until Phase 2.5 step 2 ships.
- [ ] No chart specs authored yet — chart inventory brainstorm is the
  next step (Phase 2.5 step 4).
- [ ] No assertions in `scripts/validate.py` yet — add once Q1
  numbers are signed off.

## Running what works today

```bash
# Build the financials DB (works now — operational KPIs come later)
uv run python scripts/build_db.py almacena
```
