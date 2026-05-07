# Cupffee

**Use case:** `charts` — investor-deck chart inventory.
**Cadence:** monthly.
**Currency:** EUR (with 2025 actuals converted from BGN at the fixed
1.95583 peg).

## What goes in

Each month, the following land in `clients/cupffee/raw/`:

| File | What it is | Source |
|---|---|---|
| `Taxonomy_Actuals_<MM>.xlsx` | YTD actuals through month MM, in canonical taxonomi format | Provided by client / re-keyed from accounting export |
| `Taxonomy_Actuals_12.xlsx` | Full-year 2025 actuals (BGN) | Same — kept as a stable historical anchor |
| `Taxonomy_budget_q2.xlsx` | Q2-2026 budget snapshot, all three scenarios (Pessimistic / Realistic / Optimistic) | Client's budgeting cycle |
| `Top_6_Countries_Invoiced_-_LTM_<month>.csv` | Country revenue, trailing-12-month window (BGN) | Client's BI tool export |
| `Top_6_Countries_Invoiced_MTD_<month>.xlsx` | Country revenue, current month | Same |

The reference deck (the `.pptx` used as the visual benchmark) lives in
`clients/cupffee/reference/`.

## What happens

1. **Load** all source files into a SQLite database
   (`clients/cupffee/data/cupffee.db`). Currency is normalized to EUR
   (BGN sources divided by the fixed peg). Each row in the source
   becomes a row keyed by `(period, statement, line item, scenario)`.
2. **Validate** a fixed set of cells against known-good values from a
   prior published report. If any drift, the build fails — we don't
   ship charts off bad data.
3. **Render** every chart in the inventory by reading its spec
   (`chart_specs/*.json`), pulling the underlying data from the DB,
   and producing a PNG + a JSON sidecar that snapshots the resolved
   numbers. The brand styling (Cupffee greens / orange / gold,
   Calibri, EUR '000 axis formatting) is applied automatically.
4. **Index** the rendered charts in a single HTML page so a reviewer
   can scroll through the whole inventory before drag-and-dropping
   into the deck.

## What comes out

`clients/cupffee/charts/<YYYY-MM>/`:

- One `.png` per chart in the inventory
- One `.json` sidecar per chart — captures the input spec plus the
  resolved numbers (so another tool could redraw the chart from
  scratch and reach the same picture)
- `index.html` — contact-sheet view of every chart on one page

## What to sanity-check each month

- **Numbers reconcile with the prior period's deck.** If a published
  KPI moved unexpectedly, that's a data error, not a chart error.
- **Chart catalog matches the deck.** Recurring decks carry forward
  ~95% unchanged month-to-month — any chart added or removed in the
  inventory should have explicit sign-off.
- **Currency conversion sanity.** For 2025 actuals, EUR values should
  be ~half the BGN equivalent (the peg is 1.95583). If a number looks
  ~2× off from expectation, it's likely a missed conversion.
- **`reference/Cupffee Monthly Report - Dec 2025_internal.pptx`** is
  the canonical layout reference for the deck. New chart variants
  should match its visual style.

## Running the pipeline

See [`docs/onboarding-charts.md`](../../docs/onboarding-charts.md) for
the engineer-facing workflow. TL;DR:

```bash
uv run python scripts/build_db.py cupffee
uv run python scripts/validate.py cupffee
uv run python scripts/build_charts.py cupffee <YYYY-MM>
```
