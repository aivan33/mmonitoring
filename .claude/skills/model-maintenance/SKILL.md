---
name: model-maintenance
description: >-
  Aligns a client's financial MODEL/BUDGET with their management (actuals) data
  before asking the client for new inputs — the monthly reforecast loop. Use
  whenever the task is to update/maintain a budget or model, compare budget vs
  actual, reconcile a model to actuals, reforecast, or decide what to ask a
  client for. Triggers on "align the budget", "budget vs actual", "update the
  model", "reforecast", "the model is stale", even without those exact words.
  Per-pillar skill; per-client specifics live in references/<client>.md.
---

# Model maintenance — align the budget with management data

A model/budget drifts from reality as months close. This skill aligns it to the
management (actuals) data first — fixing every driver we can from the data — so
the only thing left to ask the client is what genuinely cannot be inferred.

## When to use

Use this skill when:
- A month has closed and the model/budget needs to reflect the new actuals.
- You are about to ask a client for fresh inputs (align internally *first*).
- You need a budget-vs-actual with the variances traced to their causes.

Do **not** use it when:
- Building a model from scratch (greenfield) — that's the generate path.
- A pure reporting/variance deck with no model update.

## The parser (`core/model`)

The model is the hand-maintained Excel workbook (Excel stays the source of
truth; we operate on the xlsx in place). `core/model` parses it without
re-implementing its engine:

- `read_contract(path, rules)` → the typed contract: every sheet classified by
  role (statement · taxonomi · yearly · actuals · engine · driver · other) and
  entity, plus the budget↔actuals seams and the month-axis.
- `read_cells(path)` → every cell's cached value + raw formula.
- `build_flow(read_cells(path))` → the precedent/dependent graph. Its
  `Flow.trace_precedents(sheet, coord)` walks a forecast/output cell back to its
  driver-leaf cells — this is what makes variance-to-driver tracing mechanical.
- `load_rules(path)` → the per-client `model_rules.yaml`.

Quick dump + trace from the CLI:

```
python scripts/model_map.py <workbook.xlsx> clients/<client>/model_rules.yaml \
    --trace 'is_found_taxonomi!H2'
```

### What the engine knows vs. what the client config carries

The engine is **general** (validated across Almacena, cupffee, honey, farada):
it detects statements (`IS`/`CF`/`BS`, incl. `_platform` and whitespace
variants), `*_Yearly` rollups, actuals (incl. `Act 2026`-style), the recurring
engine sheets (`Pro Forma`, `Inputs`) and drivers (`HR`, `KPIs`) — all with **no
per-client config**. Each `clients/<client>/model_rules.yaml` carries only the
specifics: entity name patterns, the separator marker, exact-name `role_overrides`
for *bespoke* driver sheets, and the **month-axis** — either positional
(`first_month_col`/`months`/`year`, for a clean single-year taxonomi tab) or
`header_dates: true` (read the real ISO dates from the header row, for models with
no taxonomi tab whose bare IS/CF/BS span several years).

If a client has no `*_taxonomi` tab, the budget side falls back to the bare
IS/CF/BS statement sheets automatically.

## How it works (the reforecast loop)

1. **Read the model contract** (`read_contract`) to locate, per entity, the
   budget taxonomi tabs (or bare statements), the actuals sheets, and the driver
   sheets.
2. **Verify the actuals** reconcile to source for the elapsed months.
3. **Budget vs actual** per entity over the elapsed months.
4. **Trace each material variance to the LIVE driver** with
   `build_flow(...).trace_precedents` — walk the budget output cell back to the
   INPUT · LOAN · ACCOUNT leaf that actually drives it. **Fix the driver, never
   the formula-derived output line.** A sheet *named* like a driver may be an
   orphan (nothing references it) — see the cardinal rules; always confirm with
   the parser before editing.
5. **Classify** each variance: INTERNAL-FIXABLE (set from management data) vs
   NEEDS-CLIENT (not inferable). Record both in an alignment ledger.
6. **Apply** the internal fixes to the driver cells (operate on the xlsx; back
   up; re-verify). **Align internally before asking the client.**
7. **Draft the client request** — only the NEEDS-CLIENT items.

## Cardinal rules

- Trace to the **driver**, not the output line (outputs are formula-derived).
- **Verify the driver is live, not an orphan.** A sheet named `Inputs_Foundation`
  or `KPIs` may have *nothing* referencing it — editing it changes nothing. Use
  `trace_precedents` (or `trace_dependents`) to find the cell the forecast
  actually pulls from before you touch anything.
- **Backward facts** (elapsed actuals) are corrected unconditionally; **forward
  assumptions** are set from realized economics by default and logged.
- **Align internally before asking the client.**

## Output: the alignment ledger

The deliverable of a run is a per-client alignment ledger that tabulates each
material variance → its live driver → INTERNAL/NEEDS-CLIENT class → proposed
change, and ends with the distilled client ask. Review it before any model edit;
nothing in the workbook changes until then. See Almacena's for a worked example:
`clients/almacena/ALIGNMENT_LEDGER.md`.

## Diagnostic (forthcoming)

Beyond aligning to actuals, this skill is growing a **model-doctor** pass: a full
health check that flags **orphaned inputs/drivers** (cells with no dependents —
e.g. Almacena's `Inputs_Foundation`/`KPIs`, and suspected dead blocks inside
`Pro Forma`), **broken/error formulas** and unresolved references, and
**common-sense/logic errors** (statements that don't foot, hardcodes in formula
columns, sign/unit anomalies). It is being built incrementally through real work
cases (starting with the Almacena budget alignment). Scope and checks:
`docs/superpowers/specs/2026-06-15-modeling-pillar-plan.md` (M4). The flow graph
(`build_flow`, `Flow.trace_dependents`) already provides the orphan/precedent
primitives it needs.

For the client-specific contract, drivers, quirks, and worked example, read
`references/almacena.md`.
