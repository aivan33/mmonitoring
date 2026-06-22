# Model pillar

The `model` pillar treats a hand-maintained Excel financial model as the source of
truth. It either **parses** an existing model (`core/model/` — cells → contract →
formula → flow; see `__init__.py`) or **authors/extends** a client model from typed
inputs (the per-client builders under `clients/<client>/one_offs/`).

**Two skills sit on this pillar:** `model-building` (greenfield — build/overhaul a model in
the standardized 3-pillar structure + design system; `.claude/skills/model-building/`) and
`model-maintenance` (align an existing model to actuals). `core/schema` represents a parsed
model as a normalized DB (structure + lineage) and powers the build skill's model-logic
overview + health scan.

## ⚠️ The format of a model is a GIVEN — never change it without explicit approval

**A client's model format/layout is taken as a given. Do NOT change it unless the user
explicitly approves the change.**

This is the single most important rule of the pillar. Concretely, do **not**, on your own
initiative:

- restructure the sheet architecture (which sheets exist, their roles, their order);
- move, insert, delete, or re-order rows/columns of an existing section;
- change styling — fonts, fills, borders, number formats, column widths, merges;
- rename or re-lay-out existing sections, headers, or labels;
- re-shape the input grid (e.g. turn stacked rows into columns or vice-versa).

When asked to change the *numbers/economics* (align values, swap an assumption,
re-wire a driver to a different input), do exactly that and **leave the format
untouched**. Align values, inputs, and the driver formulas that read them; never
renovate the layout as a side effect. "It would be cleaner" is not approval.

If a requested value/economics change *requires* a structural change (e.g. adding a
pricing rung needs a new row, which would shift hard-coded `$J$NN` references),
**stop and get explicit sign-off first**, and prefer the least-shifting implementation
(use blank rows already present; append at the bottom; blank-in-place instead of
deleting). Surface the trade-off; don't silently restructure.

### Why

The models are founder-/investor-facing and hand-perfected. Cruft, lost work, and
off-brand formatting all read as "you broke it." Excel models also reference inputs by
**hard-coded cell address**, so an unsanctioned row insert silently corrupts formulas
across the workbook. Harvest real styles from the reference file; never approximate them.

## Conventions

- **Edit the one builder in place** — do not proliferate `_v2`, `_v3`, … scripts for each
  iteration. (Historical exception: a genuinely new revenue/recognition *engine* warrants a
  fresh builder; a value/format tweak does not.)
- **Never `rm` uncommitted/gitignored work.** Confirm with `git ls-files` first; prefer
  moving to an archive over deleting.
- **Client model data is gitignored** (`clients/*/modeling/*.xlsx`, plan docs). The repo
  tracks only the builder/verify scripts; tests skip when the client sources are absent.
- **No recalc engine** is available for these workbooks (the `formulas` lib lacks `OFFSET`;
  LibreOffice is absent). Correctness is **safe-by-construction + a Python oracle** that
  reimplements the math and checks it, plus structural assertions (sub-rows sum to parent,
  no dangling refs). New formula cells have no cached value to diff — emit expected
  first-month values for the user to eyeball on first open in Excel.

## Instances

- **Farada 5Y investor model** — `clients/farada/one_offs/build_model_v3.py`
  (`farada_model_5y.xlsx` → `farada_model_v3.xlsx`), fed by the unit-economics file
  (`build_unit_economics*.py` → `farada_unit_economics.xlsx`). Tracked scratch in
  `one_offs/`; does **not** graduate to `core/budget/` (restructure Phase 3). Plan:
  `clients/farada/modeling/model_v3_plan.md`.
