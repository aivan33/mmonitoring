---
name: model-building
description: >-
  Builds a client financial model/budget from scratch (greenfield) in the
  standardized 3-pillar structure and house formatting. Use when creating a NEW
  model or budget, scaffolding one, overhauling a model's structure/format to the
  standard, or when you need a clean budget-logic overview of how a model is built.
  Triggers on "build a model", "new budget", "scaffold a model", "model from
  scratch", "overhaul the model to the standard", "design system for the model".
  The GENERATE path; its sibling model-maintenance is the ALIGN-to-actuals path.
  Per-pillar skill; per-client specifics live in references/<client>.md.
---

# Model building — a 3-pillar financial model in the house standard

Build (or overhaul) a client model so its **structure and formatting are standardized** while its
**calculations stay client-specific**. The win condition is a **clean, no-fluff overview of how the
model is built** — a clean budget on target — emitted as `<client>_model_logic.md`.

## When to use

- Building a **new** model/budget from a client config (greenfield).
- **Overhauling** an existing model to the standard structure + design system (e.g. re-ordering
  inputs to the Cupffee skeleton, cleaning orphaned inputs / dead rows / `#REF!`).
- Producing the **budget-logic overview** of a model.

Do **not** use it for the monthly *align-to-actuals* reforecast — that's `model-maintenance`.

## The three pillars (+ KPIs)

1. **INPUT sheets** — one scenario-switchable ` Inputs` sheet, Cupffee skeleton: **I. FUNDING ·
   II. REVENUE · III. PRODUCTION (yield, cost of sales) · IV. OPERATING EXPENSES · V. OTHER**.
   Roman sections (col A), sub-numbers (B), label (C), unit (D), active `=OFFSET(K,0,$D$2)` (J),
   Realistic (L), **notes in col O**. The standard template for every model.
2. **PROFORMA + calc sheets** — the engine, NOT a statement. Section order: **Volume & Drivers**
   (revenue drivers above cost drivers) → Revenue → Cost of Sales → OPEX → Balance Sheet → WC
   drivers & ratios → Cash Flow → Taxation → Funding. *Not all used every time.* **No subtotals/
   margins here.**
3. **FINANCIAL STATEMENTS** — IS/CF/BS, **monthly + yearly**, thin (pull from ProForma; compute
   subtotals + margins). Direct-method CF, cash-as-plug, BS `check = Assets − (E+L) = 0`. A flat
   **taxonomi** tab (Data/Group/Subgroup + month ribbon) is the standardized **review** view.
4. **KPIs** — ad-hoc per business model.

All formatting (typography, palette, the input grammar, the taxonomi shape, number formats) is the
**design system** — see `references/design-system.md`. **Harvest real styles, never approximate.**

## The win condition — `<client>_model_logic.md`

Every build/overhaul emits a clean budget-logic overview: per pillar, the **drivers → calcs →
statements** chain, the client assumptions, and the key economic logic — the artifact a reviewer
reads to understand the model without opening Excel. **Generate it from the schema**, don't
hand-write: `core/schema` (`load_model` → `report.model_logic_md`) renders the 3-pillar structure,
the assumption sections, the line inventory, the lineage of key outputs back to driver inputs, and
a model-health scan (orphaned inputs / dead lines / `#REF!`). That health scan is also the overhaul
worklist.

## How it works

1. **Read the client config** — the economics (pricing, volume drivers, costs, funding) that the
   model must express. Calculations are client-specific; the structure + format are not.
2. **Lay the three pillars** in the standard order, harvesting styles from a reference workbook
   (`copy.copy` — never baked RGB). No naked rows.
3. **Wire the statements thin** — ProForma computes the lines; IS/CF/BS pull and present; build the
   taxonomi review tab; BS must tie (`check = 0`). Wire formulas per
   `references/formula-conventions.md` (cash = accrual − Δ(WC balance row), direct-method CF, …).
4. **Pass the gate** — `scripts/check_model.py <client> <wb> --full` recomputes with LibreOffice
   and asserts no error cells, subtotals foot, BS `check = 0`, statements tie.
5. **Emit `<client>_model_logic.md`** from the schema and **act on the health scan** — clean
   orphaned inputs, dead/duplicate/empty rows, and broken refs it surfaces.

## Workflow & gates

The build is a pipeline with a committed gate: **spec → build → recalc → integrity →
format/lint → model-logic → version/review**.

- **Build** — one idempotent builder per client rebuilds the xlsx from source; set
  `wb.calculation.fullCalcOnLoad = True` so the recalc gate recomputes on open.
- **Recalc gate (authoritative)** — `core/model/recalc.py` recomputes the workbook with
  LibreOffice headless. openpyxl can't evaluate formulas and OFFSET defeats pure-Python
  engines, so this is the source of truth for values.
- **Integrity gate (hard)** — `core/model/integrity.py`: no error cells (`#REF!`/`#NAME?`/…),
  BS `check = 0` per month, statements tie (CF ending cash = BS cash), subtotals foot. Targets
  come from `clients/<client>/model_gates.yaml` (ship one per client; scope out explicitly-
  unbuilt sections there, don't silently pass).
- **Format + health (warn-only for now)** — `core/model/format_lint.py` (Century Gothic, the
  OFFSET selector grammar) + the `core/schema` health scan (orphans / dead lines / broken refs),
  via `--format` / `--health` / `--full`. Warn-only until the client models are brought to canon.

Run it: `scripts/check_model.py <client> <workbook> --full` — exit 1 on any integrity violation.

## Cardinal rules

- **Format is a GIVEN** — never restructure an existing model's layout/styling without explicit
  sign-off (`core/model/README.md`). Overhauls are the *approved* exception.
- **Harvest styles, don't approximate** — baked RGB reads as "you broke the format."
- **Calculations follow the client config; structure + formatting follow the design system.**
- **Edit one builder in place** per client (don't proliferate versioned *scripts*); versioned
  *output* workbooks (`_v1`, `_v2` milestones) are fine — the gate runs the current output. Never
  `rm` uncommitted/gitignored work.
- **The recalc gate is the authority** — verify with LibreOffice headless recompute
  (`scripts/check_model.py <client> <wb> --full`): no error cells, subtotals foot, BS `check = 0`,
  statements tie. A Python oracle over cached accruals is a useful *fast pre-check*, not the gate.

## Tooling

- `core/model` — parse an existing workbook (cells · contract · flow · formula refs);
  `recalc` (LibreOffice) · `integrity` (gate checks) · `format_lint` (design-system conformance).
- `core/schema` — load a model into a normalized SQLite schema (structure + lineage); `report` emits
  the model-logic overview; `validate` is the health scan.
- `scripts/check_model.py` — the gate runner; `clients/<client>/model_gates.yaml` — gate targets.
- Per-client builders live in `clients/<client>/one_offs/`; design system + formula patterns in
  `references/` (`design-system.md`, `formula-conventions.md`).

For the client-specific config, drivers, quirks, and worked example, read `references/<client>.md`
(the reference implementation is Farada — `clients/farada/one_offs/build_model_v4*.py`,
`farada_model_logic.md`, `farada_revenue_cogs_waterfall.md`).
