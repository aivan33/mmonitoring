# Implementation Plan: Modeling Pillar — core + skill (Almacena-referenced)

**Date:** 2026-06-15
**Status:** Task breakdown — pending user review
**Derives from:** `2026-06-12-repo-restructure-design.md` (T5 + T8, the `model` pillar)
**Supersedes:** the Farada-centric budgeting-pillar plan (Farada rolling budget is ad-hoc, not the reference).

## Overview

Stand up the `model` pillar's foundation using the **Almacena model**
(`clients/almacena/budget/Almacena-26_AprActuals.xlsx`) as the reference — a real,
sophisticated, multi-entity financial model with Apr actuals folded in. The first
capability is a **structural contract**: a `core/model` reader that parses the model
workbook into a typed contract (entities, statements, engine, drivers), operating on
the xlsx in place (Excel remains the source of truth). On top of that we author the
modeling **skill**. The maintain (fold actuals + variance-to-driver) and generate
(scaffold) capabilities are deferred — the contract pass makes the right boundary explicit.

## Reference model: what Almacena teaches

- **Multi-entity:** Consolidated, AP Foundation, BG, BV/NV, Holding — each with
  per-statement Actuals → taxonomi (IS/CF/BS) → consolidation (elimination columns) →
  yearly rollups (`*_Yearly`).
- **Forward engine:** ` Inputs` + `Inputs_Foundation` → `Pro Forma` (451×55) → projected statements.
- **Driver sub-engines:** `HR` (headcount→payroll), `Loans Database` (loan schedule →
  interest/funding cost — **currently stale, loan schedule not yet updated**),
  `Investor Payment Schedule`, `KPIs` (pricing/rate drivers).
- **Reforecast discipline** (`APR_BUDGET_VS_ACTUAL.md`): compare budget-taxonomi vs
  actuals-taxonomi, then **trace every variance to a driver (INPUT · LOAN · ACCOUNT),
  never the formula-derived output line.**
- **Known quirks to tolerate, not fix:** crossed raw filenames, mislabeled CF/BS header
  years (builder keys by column position), accountant typos, intentionally-unmapped lines.

## Architecture Decisions

- **AD3 (inherited, corrected):** budget = model, one engine, two modes. The **budget-mode
  reference is now Almacena** (actuals folded into a full model); the **greenfield-mode
  reference remains the Farada fundraising model** (`scripts/build_model_*` lineage). The
  Farada *rolling budget* is ad-hoc and is **not** a reference for either.
- **D1 — The core is a parser: structure + cells + formulas + flows.** `core/model` parses a
  model workbook into (a) **structure** (the typed contract — entities/statements/engine/
  drivers/month-axis), (b) **cells** (value, formula, number-format, type per cell/range),
  (c) **formulas** (each formula's referenced cells/ranges — precedents, cross-sheet aware),
  and (d) **flows** (the precedent/dependent graph: trace any output cell back to its driver
  leaves, or any driver forward to its impacts). The flow layer is what makes variance-to-driver
  tracing mechanical. Build this before any maintain/generate automation; decide that fork after.
- **D2 — Operate on the xlsx.** `core/model` reads/writes the existing workbook in place
  and harvests its structure; it does **not** reimplement the Inputs→ProForma engine in
  Python (avoids drift from the hand-tuned file). Matches the "patch the perfected file" lesson.
- **D5 — Static graph via openpyxl; recalc is optional.** Build the flow graph statically from
  formula strings (openpyxl's `Tokenizer` + a range/defined-name resolver) over **cached cell
  values** — not a full recompute. Recalc via the `formulas` library (proven in the Farada
  one-off) is an *optional* verification adapter, not the spine: these workbooks are large and
  full recalc is slow/fragile.
- **D6 — Dynamic references handled explicitly.** These models lean on `=OFFSET(K,0,$D$2)`
  scenario selectors and `INDEX`/`INDIRECT`; static ref-parsing can't resolve them blind. The
  flow parser resolves them using the cached value of the selector cell (e.g. `$D$2`), and
  flags any reference it cannot resolve rather than silently dropping the edge.
- **D3 — Pin structure, not financials.** The model xlsx is gitignored client data, so
  golden tests snapshot **structural** facts (sheet inventory, month-axis columns, driver
  row labels) — not financial values — and skip when the workbook is absent.
- **D4 — Per-entity adapters.** Entity divergence (CF method differs by entity, crossed
  filenames) lives behind thin per-entity handling in the contract, not branched core logic.

## Dependency Graph

```
Phase 0 — Pin the reference (read-only)
  T1 model-contract spec (doc)
  T2 clear core/model ghost + real package skeleton
Phase 1 — The parser: structure + cells + formulas + flows (operate on xlsx)
  T3 cells      core/model/cells.py — value/formula/fmt/type per cell   (depends T2)
  T4 structure  core/model/contract.py — typed contract + month-axis    (depends T1,T3)
  T5 seams      actuals/budget/driver seams on the contract             (depends T4)
  T6 formulas   core/model/formula.py — formula → referenced cells      (depends T3)
  T7 flows      core/model/flow.py — precedent/dependent graph + trace  (depends T4,T6)
  T8 golden     structural + flow golden test                           (depends T4,T7)
  T9 model-map  dump structure + a sample driver-trace (validates all)  (depends T5,T7)
Phase 2 — Skill
  T10 author .claude/skills/monitoring-model  (depends T5,T9)
  T11 validate skill end-to-end               (depends T10)
Deferred — decided at the post-parser checkpoint
  M1 maintain (fold actuals)  ·  M2 variance-to-driver (uses flows)  ·  M3 generate/scaffold
```

---

## Task List

### Phase 0 — Pin the reference (no behavior change)

#### Task 1: Write the model-contract spec
**Description:** Document the structural inventory of the Almacena model: each entity, its
statement sheets, taxonomi tabs, the engine sheets, the driver sub-engines, and the
month-axis convention (which column = which period; e.g. col 18 = 2026-04). Note the
actuals-vs-budget seams (which `*Actuals` sheets are filled through which month).
**Acceptance criteria:**
- [ ] Spec lists every entity → its IS/CF/BS/taxonomi/yearly sheets and the shared engine/driver sheets.
- [ ] Month-axis mapping and the actuals/budget seam (filled-through column per entity) are explicit.
**Verification:**
- [ ] Spot-check 5 sheet/column claims against the workbook with openpyxl.
**Dependencies:** None
**Files likely touched:** `clients/almacena/budget/MODEL_CONTRACT.md` (tracked, .md)
**Estimated scope:** Small

#### Task 2: Clear the `core/model` ghost + create the real package skeleton
**Description:** Remove stale `.pyc`-only `core/model` bytecode, ensure `__pycache__` is
gitignored, and create a real `core/model/__init__.py` package (mirrors restructure T2).
**Acceptance criteria:**
- [ ] `core/model` has real tracked source (`__init__.py`); no stale bytecode tracked.
- [ ] `git grep` finds no import of a ghost module.
**Verification:**
- [ ] `uv run pytest -q` green; `import core.model` works.
**Dependencies:** None
**Files likely touched:** `core/model/__init__.py`, `.gitignore`
**Estimated scope:** Small

### Checkpoint: After Phase 0
- [ ] Reference structure documented; `core/model` is real (no ghost). Review with user.

### Phase 1 — The parser: structure + cells + formulas + flows (operate on the xlsx)

#### Task 3: `core/model/cells.py` — cell reader (value · formula · format · type)
**Description:** Read a workbook into addressable cells via openpyxl's dual load
(`data_only=True` for cached values, `data_only=False` for formula strings). Expose a `Cell`
(value, formula, number_format, dtype, sheet, coord) and range/sheet accessors.
**Acceptance criteria:**
- [ ] `read_cells(path)` returns, for any `sheet!coord`, both the cached value and the raw formula string.
- [ ] Handles a cell with no formula (literal) and one with a formula; preserves number_format.
**Verification:**
- [ ] On Almacena, a known formula cell (e.g. a `Pro Forma` `=OFFSET(...)` selector) returns its formula + cached value.
- [ ] `uv run pytest -q` green.
**Dependencies:** T2
**Files likely touched:** `core/model/cells.py`, `tests/test_model_cells.py`
**Estimated scope:** Medium

#### Task 4: `core/model/contract.py` — typed structure contract
**Description:** Classify every non-separator sheet by role + entity (statement / taxonomi /
engine ` Inputs`·`Inputs_Foundation`·`Pro Forma` / driver `HR`·`Loans Database`·`Investor
Payment Schedule`·`KPIs` / yearly rollup) and resolve the month-axis (column → period) by
position so it tolerates mislabeled header years.
**Acceptance criteria:**
- [ ] `read_contract(path) -> ModelContract` classifies every sheet (no "unclassified"); exposes the month-axis.
- [ ] Matches the T1 spec for Almacena's entities and sheets.
**Verification:**
- [ ] Reader output == T1 spec (spot-check); `uv run pytest -q` green.
**Dependencies:** T1, T3
**Files likely touched:** `core/model/contract.py`, `tests/test_model_contract.py`
**Estimated scope:** Medium

#### Task 5: Actuals / budget / driver seams on the contract
**Description:** Extend the contract to expose the hook points later capabilities need: per
entity, the `*Actuals` sheet + last-populated month column; the budget taxonomi tabs; the
driver sheets by role.
**Acceptance criteria:**
- [ ] Contract reports, per entity, the actuals sheet + last populated month, and addresses budget tabs + driver sheets by role.
**Verification:**
- [ ] On Almacena, the Consolidated/AP Foundation seam matches T1 (Apr actuals blank in `budget-q126`, filled in `AprActuals`).
- [ ] `uv run pytest -q` green.
**Dependencies:** T4
**Files likely touched:** `core/model/contract.py`, `tests/test_model_contract.py`
**Estimated scope:** Small

#### Task 6: `core/model/formula.py` — formula → referenced cells (precedents)
**Description:** Parse a formula string into the set of cells/ranges it references, using
openpyxl's `Tokenizer`. Cross-sheet aware (`Sheet!A1`), absolute/relative, named ranges, and
range expansion (`A1:A9`). Resolve dynamic refs (`OFFSET`/`INDEX`/`INDIRECT`) using the cached
value of the driving cell (per D6); flag any ref it cannot resolve.
**Acceptance criteria:**
- [ ] `refs(formula, sheet, cells) -> set[CellRef]` handles `=Actuals!J60`, `=C6+C7+C8`, a `SUMPRODUCT` range, and `=OFFSET(K9,0,$D$2)`.
- [ ] Unresolvable references are returned flagged, not dropped.
**Verification:**
- [ ] Unit tests over the representative formula shapes above; `uv run pytest -q` green.
**Dependencies:** T3
**Files likely touched:** `core/model/formula.py`, `tests/test_model_formula.py`
**Estimated scope:** Medium

#### Task 7: `core/model/flow.py` — precedent/dependent graph + trace
**Description:** Build the workbook-wide dependency graph (edges from each formula cell to its
precedents via T6) and expose `trace_precedents(cell, stop=is_leaf)` → driver leaves and
`trace_dependents(cell)` → impacts. Leaf = a cell with no formula (a literal driver input).
**Acceptance criteria:**
- [ ] `build_flow(cells) -> Flow`; `trace_precedents` on a budget output line returns its driver leaf cells.
- [ ] `trace_dependents` on a driver cell lists the outputs it feeds; cycles are handled (no infinite loop).
**Verification:**
- [ ] On Almacena, a budget taxonomi line (e.g. NIR) traces back to `Inputs_Foundation`/`Loans`/`KPIs` leaves.
- [ ] `uv run pytest -q` green.
**Dependencies:** T4, T6
**Files likely touched:** `core/model/flow.py`, `tests/test_model_flow.py`
**Estimated scope:** Medium

#### Task 8: Golden test — structure + flow
**Description:** Pin the Almacena contract structurally (sheet inventory, month-axis, driver
labels) **and** a representative flow trace (a known output → its driver-leaf set, by coord).
Structural/graph facts only — no financial values; skip when the workbook is absent.
**Acceptance criteria:**
- [ ] Asserts the structural snapshot + one driver-trace; perturbing a sheet role or a traced edge fails it.
- [ ] Skips cleanly without the workbook.
**Verification:**
- [ ] `uv run pytest -q` green with the workbook; skipped without it.
**Dependencies:** T4, T7
**Files likely touched:** `tests/test_model_contract.py`, `tests/fixtures/almacena_contract.json`
**Estimated scope:** Small

#### Task 9: `model-map` dump
**Description:** A function/CLI that prints a workbook's contract (entities, sheets by role,
month axis, seams) plus a sample driver-trace — validates the whole parser on the real file
and doubles as the skill demo.
**Acceptance criteria:**
- [ ] Running it on Almacena prints the contract map + a worked precedent trace for one output line.
**Verification:**
- [ ] Output matches T1 + T7 on a spot-check.
**Dependencies:** T5, T7
**Files likely touched:** `core/model/__init__.py` or `scripts/model_map.py`
**Estimated scope:** Small

### Checkpoint: After Phase 1
- [ ] `core/model` parses the Almacena model into structure + cells + formulas + a flow graph; driver-tracing works and is tested.
- [ ] **Decide the next capability here: maintain (M1/M2, both built on flows) vs generate (M3).** Review with user.

### Phase 2 — Skill

#### Task 10: Author the modeling pillar skill
**Description:** Write `.claude/skills/monitoring-model/SKILL.md`: model architecture
(entities → taxonomi → consolidation → engine → drivers), the reforecast discipline, how to
use the parser (`read_contract` / `trace_precedents`) to go from a variance to its driver, an
Almacena worked example, and the gotchas (crossed filenames, position-keyed months, OFFSET
selectors, stale loan schedule).
**Acceptance criteria:**
- [ ] Skill states input shape, the parser commands, the variance→driver workflow, and references real paths.
- [ ] Discoverable; one worked example (Almacena).
**Verification:**
- [ ] Every path in the skill exists (`git ls-files` / file spot-check).
**Dependencies:** T5, T9
**Files likely touched:** `.claude/skills/monitoring-model/SKILL.md`
**Estimated scope:** Small

#### Task 11: Validate the skill end-to-end
**Description:** Follow the skill cold (fresh session/subagent) to produce a model-map and a
driver-traced variance read for Almacena, confirming the doc is sufficient.
**Acceptance criteria:**
- [ ] Following the skill yields the contract map + a driver-traced variance read with no undocumented step.
**Verification:**
- [ ] Artifacts produced; any gap folded back into the skill.
**Dependencies:** T10
**Estimated scope:** Small

### Checkpoint: Complete
- [ ] Modeling pillar foundation: a parser (structure + cells + formulas + flows) over the real model + a validated skill; next capability chosen.

---

## Deferred (decided at the post-structure checkpoint)

- **M1 — Maintain (fold actuals):** write the month's MR-taxonomi actuals into the model's
  `*Actuals` sheets (operate on xlsx), reproduction-gated against the already-entered Q1 actuals.
- **M2 — Variance-to-driver report:** automate the `APR_BUDGET_VS_ACTUAL.md` output —
  budget-taxonomi vs actuals-taxonomi, mapped to INPUT·LOAN·ACCOUNT drivers.
- **M3 — Generate / scaffold:** author a model of the Almacena shape from drivers/taxonomi.
- **M4 — Diagnostic (model-doctor):** a full health check on a model workbook,
  built on the existing `core/model` flow graph. Surfaced by the Almacena founder
  review (week of 2026-06-16): the model carries **orphaned inputs** (`Inputs_Foundation`,
  `KPIs` — nothing references them) and **potentially orphaned drivers inside
  `Pro Forma`**. The diagnostic should report, at minimum:
  - **Orphans** — input/driver cells (and Pro Forma blocks) with no dependents
    (`trace_dependents` empty) → dead inputs that mislead edits.
  - **Broken/ error formulas** — cells evaluating to `#REF!`/`#DIV0!`/`#VALUE!`,
    and references the flow parser cannot resolve (already flagged as `dynamic`).
  - **Common-sense / logic checks** — e.g. statement cross-ties that don't foot
    (BS balance, CF→cash reconciliation), sign/units anomalies, hardcoded numbers
    inside otherwise-formula columns, stale/forked driver blocks.
  - Output: a per-model diagnostic report (like the alignment ledger), structural
    findings only (no financial values pinned in tests).
  **Build approach:** *not* a standalone push — grow it incrementally while doing
  the **Almacena budget alignment later this week** (the real work case), then
  harvest the reusable checks into `core/model` + the skill. Partly enabled today
  by `flow.trace_dependents` / the `dynamic`-ref flagging.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Model xlsx gitignored → can't fixture it | Med | D3: pin structure not financials; tests skip when absent |
| Hand-tuned engine too complex to reimplement | High | D2: operate on the xlsx, don't port the engine |
| Loan schedule is stale (not yet updated) | Med | Contract tolerates a known-stale sub-engine; flag, don't fix |
| Entity divergence (CF method, crossed filenames) | Med | D4: per-entity handling in the contract |
| Skill drifts from the model over time | Low | Skill references the contract reader + real paths; revalidate on model change |

## Open Questions
- Skill name: `monitoring-model` (budget + model modes documented inside) vs `monitoring-budget`. Leaning `monitoring-model`.
- Contract spec location: `clients/almacena/budget/MODEL_CONTRACT.md` vs `docs/`. Leaning beside the model.
- Next capability after the structure pass: maintain (M1/M2) or generate (M3)?
