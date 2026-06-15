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

> **STATUS: scaffold.** Filled in after the first real run (Almacena alignment).
> The body below is the intended shape; `references/almacena.md` carries the
> client-specific contract, drivers, and worked example.

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

## How it works (the reforecast loop)

1. **Read the model contract** (`core/model.read_contract`) to locate, per entity,
   the budget taxonomi tabs, the actuals sheets, and the driver sheets.
2. **Verify the actuals** reconcile to source for the elapsed months.
3. **Budget vs actual** per entity over the elapsed months.
4. **Trace each material variance to its driver** with `core/model.trace_precedents`
   — walk the budget output cell back to the INPUT · LOAN · ACCOUNT leaf that
   drives it. **Fix the driver, never the formula-derived output line.**
5. **Classify** each variance: INTERNAL-FIXABLE (set from management data) vs
   NEEDS-CLIENT (not inferable).
6. **Apply** the internal fixes to the driver cells (operate on the xlsx; back up;
   re-verify). **Align internally before asking the client.**
7. **Draft the client request** — only the NEEDS-CLIENT items.

## Cardinal rules

- Trace to the **driver**, not the output line (outputs are formula-derived).
- **Backward facts** (elapsed actuals) are corrected unconditionally; **forward
  assumptions** are set from realized economics by default and logged.
- **Align internally before asking the client.**

For the client-specific contract, drivers, quirks, and worked example, read
`references/almacena.md`.
