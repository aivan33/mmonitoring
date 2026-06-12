# Design & Plan: Repo Restructure — Pillars, Shared Builders, Skills

**Date:** 2026-06-12
**Status:** Approved design → task breakdown (pending user review of this doc)

## Overview

The `monitoring` repo began as a three-use-case tool (`charts`, `text`, `report`)
over one shared data layer. It has since grown ad-hoc consolidation, budgeting,
modeling, and analysis with no clear setup. This redesign keeps the **single
repo and shared `core/data`** (the management-data ↔ budget link is the whole
value), formalizes the use cases that have sprawled, kills orphaned modules, and
wraps each pillar's setup in a version-controlled skill so onboarding a use case
is "read one skill," not "copy the last client's one_off and mutate."

We are **not** splitting into separate tools. None of the user's pains
("fear of breaking," "setup friction," "can't find things") is caused by the
shared data layer; splitting would worsen the one link that is invaluable.

## Diagnosis (what "out of control" actually is)

Grounded in the current tree, not the README's aspiration:

1. **The committed `core/` is only three real modules:** `data`, `charts`,
   `report`. `core/text` is an empty `__init__.py` stub.
2. **Ghost modules.** `core/model`, `core/bronze`, `core/cli`, `core/config`
   have **zero tracked `.py` source** — only stale `.pyc` bytecode. The "model
   pillar" does not exist in `core/`. They make the tree lie about what's real.
3. **The real daily work is untracked and duplicated.** `clients/cupffee/one_offs/`,
   `clients/farada/one_offs/`, `clients/scaleflex/` are entirely untracked
   (`build_rolling_budget.py`, `build_taxonomi.py`, `build_budget_taxonomi.py`,
   `build_budget_apr.py`, …). Each client reinvents its own taxonomi/budget
   builder, none version-controlled.

Decoded to the three pains:
- **Fear of breaking** → highest-value logic (taxonomi build, budget engine) is
  uncommitted and duplicated; there is no safe baseline to change against.
- **Setup friction** → no shared builder to start from.
- **Can't find things** → ghosts make `core/model` look real; real code hides in
  `clients/*/one_offs/` and `clients/*/reports/<month>/`.

**Therefore the work is not "invent new pillar folders." It is: make the current
state safe and legible first, then promote the duplicated builders into shared
`core/` capabilities incrementally, behind reproduction tests, and document each
pillar as a skill.**

## Architecture Decisions

- **AD1 — One repo, shared `core/data`.** No split. The budget ↔ management-data
  link is the moat; splitting adds a copy-paste seam across repos.
- **AD2 — Four pillars** (each = a stable `input contract → deliverable contract`
  pair, with one skill):
  | Pillar | Input | Deliverable | Direction |
  |---|---|---|---|
  | `charts` | taxonomi DB + chart_specs | PNG + JSON sidecars | backward |
  | `text` | taxonomi DB + source PPTX structure | slides.md (plain) + analysis.md | backward |
  | `report` | MR workbook + taxonomi + mapping | reconcile / variance / commentary / checklist | backward |
  | `model` | drivers/assumptions (+ actuals in *budget* mode) | scenario workbook; budget mode emits a plan the report consumes | forward |

  The `model` pillar also carries a diagnostic capability (a *broken-budget
  analysis* skill — balance-sheet imbalance matching: when a budget/model fails
  to balance, locate the plug/mismatch). Deferred — see Task 11.
- **AD3 — Budget = model, one engine, two modes.** A budget is the projection
  engine anchored to actuals and reforecast monthly; a fundraising model is the
  same engine run greenfield. One `core/model`, not two pillars.
- **AD4 — Consolidation is a `core/data` capability, not a pillar.** It produces
  a consolidated dataset + consolidation-check report consumed by the other
  pillars (`core/data/consolidate.py`).
- **AD5 — New shared `core/taxonomi/`.** The single "source workbook → taxonomi"
  builder spine, replacing N copies in `one_offs/`. Per-client divergence
  (almacena CROSSED filenames, scaleflex missing sheets, cupffee 45-row format)
  is handled by thin per-client adapters; only the genuinely shared spine is
  unified.
- **AD6 — Opportunistic migration.** Build the shared spine, but migrate each
  client into it only when next touched for real work, gated by its golden test.
  No big-bang.
- **AD7 — Skills in `.claude/skills/`.** One project skill per pillar,
  version-controlled, encoding input → command → deliverable → gotchas.
- **AD8 — Sanctioned scratch.** `clients/<c>/one_offs/` stays as tracked scratch
  with a README and a "graduate when it recurs" rule. `_archive/` is removed or
  gitignored.
- **AD9 — Boundary rule.** Pillars import `core/data` only through its query API;
  `core/data` never imports a pillar.

## Target Structure

```
core/
  data/        ✓ schema, build, query, validation, loaders
               + consolidate.py        (AD4)
  taxonomi/    NEW  shared source→taxonomi builder spine (AD5)
  charts/      ✓
  text/        stub → real (AD2)
  report/      ✓ reconcile / variance / commentary
  model/       NEW real source — projection engine; budget mode (AD3)
clients/<c>/
  config.yaml  ✓
  one_offs/    sanctioned scratch, TRACKED, README + graduation rule (AD8)
  reports/, charts/   outputs
.claude/skills/  one skill per pillar (AD7)
docs/superpowers/specs/  this doc
```

## Dependency Graph

```
Phase 0 — Safety (no behavior change)
  T1 commit untracked one_offs (baseline)
  T2 delete ghost .pyc modules + gitignore __pycache__
  T3 golden reproduction tests (depends T1)        ← safety net for everything
Phase 1 — Shared spine (additive, no client behavior change)
  T4 core/taxonomi spine + adapter hook (depends T3)
  T5 core/model engine + budget mode (depends T3)
  T6 core/data/consolidate.py (depends T3)
Phase 2 — Pillars & skills
  T7 promote core/text stub → real (depends T3)
  T8 one skill per pillar (depends T4,T5,T6,T7)
  T9 one_offs scratch convention + archive cleanup (depends T1)
Phase 3 — Reconcile the story
  T10 rewrite README + architecture.md (depends all)
```

---

## Task List

### Phase 0 — Safety & Legibility (no behavior change)

#### Task 1: Commit the untracked working scripts as a baseline
**Description:** Bring the untracked per-client work into version control unchanged,
so there is a safe baseline before any refactor. No logic changes.
**Acceptance criteria:**
- [ ] `clients/cupffee/one_offs/`, `clients/farada/one_offs/`, `clients/scaleflex/`
      (and any other untracked working scripts) are committed as-is.
- [ ] `git status` shows no untracked working `.py` under `clients/`.
- [ ] Genuinely transient/data files remain gitignored (verify against `.gitignore`).
**Verification:**
- [ ] `git status --porcelain` clean of `??` under `clients/*/one_offs`.
- [ ] `uv run pytest -q` still passes (no behavior touched).
**Dependencies:** None
**Files likely touched:** `clients/*/one_offs/*.py`, possibly `.gitignore`
**Estimated scope:** Small

#### Task 2: Delete ghost bytecode modules
**Description:** Remove orphaned `.pyc`-only modules (`core/model`, `core/bronze`,
`core/cli`, `core/config`) that have no tracked source, and stop tracking
`__pycache__`. (Real `core/model` source is created later in T5; this only clears
the lie.)
**Acceptance criteria:**
- [ ] `core/bronze`, `core/cli`, `core/config` removed; `core/model` emptied of
      stale bytecode (folder may remain as a placeholder for T5 or be recreated).
- [ ] `__pycache__/` is gitignored repo-wide.
- [ ] No import in tracked source references the deleted modules (grep clean).
**Verification:**
- [ ] `uv run pytest -q` passes.
- [ ] `git grep -nE 'core\.(bronze|cli|config)'` returns nothing in tracked `.py`.
**Dependencies:** None
**Files likely touched:** `core/bronze/`, `core/cli/`, `core/config/`, `.gitignore`
**Estimated scope:** Small

#### Task 3: Golden-output reproduction tests for each active builder
**Description:** Pin the current output of each client's taxonomi/budget builder
with a reproduction test (the almacena Q1-gate / scaleflex CF-guard pattern), so
later promotion cannot silently change numbers.
**Acceptance criteria:**
- [ ] Each active client's taxonomi/budget build has a test asserting its current
      output (totals reconcile to source subtotals; key lines match a frozen snapshot).
- [ ] Tests are deterministic and run from committed inputs/fixtures.
**Verification:**
- [ ] `uv run pytest -q tests/` passes; new tests visible and green.
- [ ] Deliberately perturbing one builder output fails its test (sanity).
**Dependencies:** T1
**Files likely touched:** `tests/<client>_repro_*.py`, `tests/fixtures/`
**Estimated scope:** Medium

### Checkpoint: After Phase 0
- [ ] `uv run pytest -q` green; tree legible (no ghosts); every builder pinned.
- [ ] Review with user before structural work.

### Phase 1 — Shared spine (additive; no client behavior change)

#### Task 4: Create `core/taxonomi/` shared builder spine
**Description:** Extract the common "source workbook → taxonomi" spine into a
shared module with a thin per-client adapter hook. Do **not** migrate any client
yet (AD6) — this only establishes the shared path.
**Acceptance criteria:**
- [ ] `core/taxonomi/` exposes a documented build interface + adapter seam for
      per-client divergence (filename crossing, missing sheets, row-count variants).
- [ ] A reference adapter reproduces one client's golden output through the shared
      spine, proving the seam works.
**Verification:**
- [ ] That client's T3 golden test passes when run through `core/taxonomi`.
- [ ] `uv run pytest -q` green; other clients untouched.
**Dependencies:** T3
**Files likely touched:** `core/taxonomi/__init__.py`, `core/taxonomi/build.py`, one adapter, tests
**Estimated scope:** Medium

#### Task 5: Create real `core/model/` engine with budget mode
**Description:** Build the projection engine (inputs-first) from the existing
untracked Farada rolling-budget / model work; expose a *budget mode* anchored to
actuals (cash-as-plug, indirect CF) and a *model mode* run greenfield.
Reproduction-gated against the current Farada rolling budget.
**Acceptance criteria:**
- [ ] `core/model` reproduces the current Farada rolling-budget output (budget mode).
- [ ] Model mode runs from drivers without an actuals anchor.
- [ ] Budget-mode output is consumable by `core/report` variance.
**Verification:**
- [ ] Farada budget reproduction test passes via `core/model`.
- [ ] `uv run pytest -q` green.
**Dependencies:** T3
**Files likely touched:** `core/model/*.py`, `tests/farada_model_repro.py`
**Estimated scope:** Medium

#### Task 6: `core/data/consolidate.py` capability
**Description:** Formalize the Farada consolidation + consolidation-check logic as
a data-layer capability producing a consolidated entity and a check report.
**Acceptance criteria:**
- [ ] `core/data/consolidate.py` produces a consolidated dataset from per-entity
      taxonomies + intercompany rules.
- [ ] Emits the consolidation-check report (P&L / CF residual flags) Farada already needs.
**Verification:**
- [ ] Reproduction test against the current Farada consolidated numbers passes.
- [ ] `uv run pytest -q` green.
**Dependencies:** T3
**Files likely touched:** `core/data/consolidate.py`, `tests/farada_consolidate_repro.py`
**Estimated scope:** Medium

### Checkpoint: After Phase 1
- [ ] Shared spine (`taxonomi`, `model`, `consolidate`) exists and is tested.
- [ ] No client's existing behavior changed; all golden tests green.

### Phase 2 — Pillars & skills

#### Task 7: Promote `core/text` from stub to real
**Description:** Implement the text pillar to the established deliverable format
(slides.md = plain text, analysis.md = formatted companion), mirroring source PPTX
structure.
**Acceptance criteria:**
- [ ] `core/text` produces slides.md + analysis.md for one client from taxonomi + source structure.
- [ ] Output matches the documented deck-text format (no markup in slides.md).
**Verification:**
- [ ] Test renders the two files for a sample; structural assertions pass.
- [ ] `uv run pytest -q` green.
**Dependencies:** T3
**Files likely touched:** `core/text/*.py`, `tests/text_*.py`
**Estimated scope:** Medium

#### Task 8: Author one project skill per pillar
**Description:** Write `.claude/skills/` skills for `taxonomi`, `charts`, `text`,
`report`, `model`, each encoding input contract → build command → deliverable →
gotchas, referencing the relevant `docs/onboarding-*.md`.
**Acceptance criteria:**
- [ ] One skill per pillar exists, discoverable, with a worked example command.
- [ ] Each skill states its input shape, the exact build command, and the deliverable path.
**Verification:**
- [ ] Following a skill end-to-end for one client produces the expected deliverable.
- [ ] Skills reference real, current paths (no ghost modules).
**Dependencies:** T4, T5, T6, T7
**Files likely touched:** `.claude/skills/monitoring-*/SKILL.md`
**Estimated scope:** Medium

#### Task 9: Sanctioned scratch convention + archive cleanup
**Description:** Add a README to the `one_offs/` convention with a "graduate when
it recurs" rule; remove or gitignore `_archive/`.
**Acceptance criteria:**
- [ ] A short convention doc explains what belongs in `one_offs/` vs `core/` and the graduation trigger.
- [ ] `_archive/` removed or gitignored; tree has no pretend-structure.
**Verification:**
- [ ] `git status` clean; `_archive/` no longer tracked.
**Dependencies:** T1
**Files likely touched:** `clients/README` or `docs/`, `.gitignore`, `_archive/`
**Estimated scope:** Small

### Checkpoint: After Phase 2
- [ ] Every pillar has a skill; scratch space is sanctioned and documented.

### Phase 3 — Reconcile the story

#### Task 10: Rewrite README + `docs/architecture.md`
**Description:** Update the README and architecture doc to describe the real
structure: 4 pillars + `consolidate` capability + `taxonomi` spine + scratch
convention. Remove the "mid-migration" caveat.
**Acceptance criteria:**
- [ ] README use-case table matches the 4 real pillars and their entry points.
- [ ] "Cleanup in progress" caveat removed; layout section matches the tree.
**Verification:**
- [ ] Every path mentioned in README exists (`git ls-files` spot-check).
**Dependencies:** T1–T9
**Files likely touched:** `README.md`, `docs/architecture.md`
**Estimated scope:** Small

### Checkpoint: Complete
- [ ] All acceptance criteria met; `uv run pytest -q` green; README matches reality.

### Deferred (post-restructure backlog)

#### Task 11: Broken-budget analysis (balance-sheet imbalance matching) — DEFERRED
**Description:** A diagnostic capability + skill for the `model` pillar: when a
budget or model fails to balance, locate the source of the imbalance (which
account/period the plug absorbs, where assets ≠ liabilities + equity, BS-vs-CF-vs-IS
mismatch). Distinct from *building* a model — this *diagnoses* a broken one.
**Acceptance criteria:**
- [ ] Given an out-of-balance model/budget workbook, the tool reports the imbalance
      by statement and period and traces it to the originating line(s).
- [ ] A `model`-pillar skill documents the diagnostic workflow (input: a model
      workbook; deliverable: an imbalance report).
**Verification:**
- [ ] On a known-broken fixture, the tool pinpoints the seeded imbalance.
- [ ] `uv run pytest -q` green.
**Dependencies:** T5 (the model engine must exist first)
**Files likely touched:** `core/model/diagnose.py`, `.claude/skills/monitoring-model-diagnose/SKILL.md`, `tests/`
**Estimated scope:** Medium
**Status:** Deferred — schedule after the restructure (Phases 0–3) lands; not on the critical path.

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Per-client builders too divergent to unify cleanly | Med | AD5 thin adapters — unify only the spine; golden tests prevent silent drift; opportunistic migration (AD6) |
| Promoting a builder silently changes numbers | High | T3 reproduction tests gate every promotion; nothing moves before its test exists |
| Untracked work lost before baseline | High | T1 first, before anything else |
| Skills drift from code over time | Low | Skills reference real paths; T10 keeps README honest; review on pillar change |
| Scope creep into big-bang unification | Med | Opportunistic migration is explicit non-goal of this plan |

## Non-Goals (this plan)
- Migrating all existing clients into the shared builders now (happens
  opportunistically, per-client, during normal monthly cycles).
- Building a unified CLI surface (the old `core/cli` ghost) — out of scope unless
  it re-emerges as a real need.

## Open Questions
- None blocking. Skill naming convention (`monitoring-<pillar>` vs `<pillar>`)
  to be settled in T8.
