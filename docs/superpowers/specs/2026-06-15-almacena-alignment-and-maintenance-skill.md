# Implementation Plan: Almacena budget↔management-data alignment + the model-maintenance skill

**Date:** 2026-06-15
**Status:** Task breakdown — pending user review
**Relates to:** `2026-06-15-modeling-pillar-plan.md` (operationalizes its deferred M1/M2),
`2026-06-12-repo-restructure-design.md` (T8 skills)

## Overview

Do the live task — **align the Almacena budget with the management (actuals) data so the
budget reflects reality *before* we ask the client for new inputs** — and **distill the
process into a reusable skill while doing it**. The skill is battle-tested, not theoretical:
the April findings already in `clients/almacena/budget/APR_BUDGET_VS_ACTUAL.md` become its
worked example, and the act of aligning produces the workflow the skill encodes.

The alignment is the reforecast discipline from that doc: compare **budget taxonomi**
(`is_cons_taxonomi`/`is_found_taxonomi`) vs **management data** (actuals taxonomi →
`almacena.db` via `core/data/query.py`), trace each material variance to a **driver
(INPUT · LOAN · ACCOUNT)**, then **fix what we can internally** from management data and
**ask the client only for what's genuinely external** (notably the stale loan schedule).

## Scope: period & actuals window

- **Focus period: FY2026.** The model extends beyond 2026, but the alignment targets 2026.
- **Actuals window:** **2025 (full year)** and **2026 Jan–Apr** are actual data; **2026
  May–Dec** is the forecast being reforecast.
- **Where budget meets actual:** the variance is computed on the **elapsed actual months
  (2026 Jan–Apr)** — YTD plus the April spot view already in `APR_BUDGET_VS_ACTUAL.md`. Those
  variances drive driver updates that reshape the **May–Dec 2026** forecast.
- **Two kinds of fix (the "boundary"):** *backward facts* in the elapsed months (book size,
  realized rates) are corrected unconditionally; *forward assumptions* for May–Dec are set
  from realized economics by default, logged transparently, and only escalated to the client
  when not inferable (see AD6).

## Architecture Decisions

- **AD1 — Skill convention: per-pillar skill + per-client references.**
  `.claude/skills/model-maintenance/SKILL.md` holds the *generic* alignment process;
  `.claude/skills/model-maintenance/references/almacena.md` holds Almacena's contract,
  drivers, quirks, and commands. Reusable for cupffee/farada/scaleflex later (reference #2…).
  This is the `.claude/skills/<name>/SKILL.md` layout the harness auto-discovers — chosen over
  a flat `skills/modelling/*.md` precisely so the skill actually triggers.
- **AD2 — Distill from doing (Q2).** Author the skill from the real alignment run, not ahead
  of it; the reference's worked example is the actual April ledger.
- **AD3 — Operate on the xlsx (inherited).** Apply driver fixes in the model workbook in
  place (Excel = source of truth); back up before mutating; re-verify recompute/balance.
- **AD4 — Internal-first, then ask.** Only variances that cannot be resolved from management
  data become a client request. The loan schedule is stale (per user) → it goes to the client
  request unless derivable from the actual book.
- **AD5 — Built on the `core/model` parser (definite dependency).** The `core/model` parser
  (structure + cells + formulas + flows — see `2026-06-15-modeling-pillar-plan.md` Phase 1) is
  built first and is the engine of this work: the variance step reads budget/actual via the
  cell layer, and driver-tracing (T5) uses `trace_precedents` over the flow graph to walk a
  variance back to its driver leaves — instead of tracing by hand. (Higher-level variance
  *report* automation remains an optional later graduation.)
- **AD6 — Boundary: backward facts unconditional, forward assumptions default-internal.**
  Corrections to the elapsed actual months (2026 Jan–Apr) are applied as fact. Forward
  assumptions for May–Dec 2026 are set from realized economics *by default* and recorded in
  `references/almacena.md`; only items not inferable from management data (the loan-schedule
  specifics) go to the client. Any forward assumption can be flipped to "ask client" per item.

## Dependency Graph

```
Phase 0 — Scaffold the skill home
  T1 skill layout + convention (stubs)
Phase 1 — Establish the two pictures
  T2 refresh + verify management data (actuals)        (depends T1)
  T3 locate the budget side in the model               (depends T1)
Phase 2 — Reconcile + trace (analytical core)
  T4 budget-vs-actual per entity                        (depends T2,T3)
  T5 driver ledger: INTERNAL-FIXABLE vs NEEDS-CLIENT    (depends T4)
Phase 3 — Align the budget
  T6 apply internal-fixable drivers in the workbook     (depends T5)
  T7 client input request (the minimal ask)            (depends T5)
Phase 4 — Anchor in skills (distill)
  T8 references/almacena.md (contract+findings+commands)(depends T6,T7)
  T9 model-maintenance/SKILL.md (generic process)       (depends T8)
  T10 validate the skill end-to-end                     (depends T9)
```

---

## Task List

### Phase 0 — Scaffold the skill home

#### Task 1: Skill layout + convention stubs
**Description:** Create the skill folder so findings land in place as we work, and record the
per-pillar/per-client convention. Stubs only — bodies are filled in Phase 4.
**Acceptance criteria:**
- [ ] `.claude/skills/model-maintenance/SKILL.md` and `references/almacena.md` exist as stubs with headings.
- [ ] A one-paragraph convention note states: per-pillar skill, per-client reference files, `.claude/skills/<name>/SKILL.md` layout.
**Verification:**
- [ ] Files present; `description` frontmatter on SKILL.md is a valid trigger sentence.
**Dependencies:** None
**Files likely touched:** `.claude/skills/model-maintenance/SKILL.md`, `.claude/skills/model-maintenance/references/almacena.md`
**Estimated scope:** Small

### Phase 1 — Establish the two pictures to reconcile

#### Task 2: Refresh + verify the management data (actuals)
**Description:** Ensure the actuals taxonomi covering the actuals window (**2025 full year +
2026 Jan–Apr**) is built and loaded to `almacena.db`, and reconciles to source (the Q1
reproduction gate + the April cash/revenue ties already documented in `APR_BUILD_NOTES.md`).
**Acceptance criteria:**
- [ ] `taxonomi_consolidated_04` / `taxonomi_ap_foundation_04` present and loaded per entity; 2025 actuals present.
- [ ] Q1 reproduction clean; April key lines tie (Sales 79,317.73; ap cash 2,368,594.74; NIR 29,284.39).
**Verification:**
- [ ] `build_taxonomi.py --validate` clean; `core/data/query.py get_statement` returns April per entity.
**Dependencies:** T1
**Files likely touched:** `clients/almacena/raw/*` (regenerated), `clients/almacena/data/almacena.db`
**Estimated scope:** Small

#### Task 3: Locate the budget side in the model
**Description:** Identify, per entity, the model's budget taxonomi tabs and the driver sheets
that feed them (`Inputs_Foundation`/` Inputs`/`KPIs`/`Loans Database`/`HR`), and confirm the
April budget figures match those in `APR_BUDGET_VS_ACTUAL.md`.
**Acceptance criteria:**
- [ ] Budget taxonomi tabs + their upstream driver sheets are enumerated per entity.
- [ ] April budget NIR (−10,358), Flat Fee (24,928), etc. reconcile to the doc.
**Verification:**
- [ ] openpyxl spot-check of 5 budget lines against the doc.
**Dependencies:** T1
**Files likely touched:** (read-only) `clients/almacena/budget/Almacena-26_AprActuals.xlsx`
**Estimated scope:** Small

### Checkpoint: After Phase 1
- [ ] Both sides (management data + budget) verified and addressable. Review with user.

### Phase 2 — Reconcile and trace (analytical core)

#### Task 4: Budget-vs-actual per entity
**Description:** Compute the budget-vs-actual variance per entity (consolidated +
ap_foundation) at the taxonomi-line level over the **elapsed actual months (2026 Jan–Apr:
YTD + the April spot view)**, flagging material lines (reproduce and, where stale, refresh
`APR_BUDGET_VS_ACTUAL.md`).
**Acceptance criteria:**
- [ ] A variance table per entity (YTD Jan–Apr + April spot) with budget / actual / variance and a materiality flag.
- [ ] Headline reproduced: revenue beats, costs under, NIR flips positive.
**Verification:**
- [ ] Numbers tie to T2/T3 sources; consolidated NIR == ap_foundation Gross+Funding.
**Dependencies:** T2, T3
**Files likely touched:** `clients/almacena/budget/APR_BUDGET_VS_ACTUAL.md`, optional `clients/almacena/one_offs/budget_vs_actual.py`
**Estimated scope:** Medium

#### Task 5: Driver ledger — INTERNAL-FIXABLE vs NEEDS-CLIENT
**Description:** Trace each material variance to its driver (INPUT · LOAN · ACCOUNT) using the
`core/model` flow graph (`trace_precedents` from the budget output cell back to its driver
leaves), then classify whether it can be fixed from management data now or needs the client.
This is the decision the whole task turns on.
**Acceptance criteria:**
- [ ] Each material variance has: driver location (the leaf cell/sheet/row or account from the trace), root cause, class (internal/needs-client), proposed change.
- [ ] Known items placed: funding-book scale + blended rate, blank KPI pricing rows, over-provisioned account forecasts → internal; loan-schedule rebuild → client.
**Verification:**
- [ ] Every material line from T4 appears in the ledger with a class and an action; the traced leaf matches the model's actual driver cell.
**Dependencies:** T4, `core/model` parser (modeling-pillar plan Phase 1)
**Files likely touched:** `clients/almacena/budget/ALIGNMENT_LEDGER.md`
**Estimated scope:** Medium

### Checkpoint: After Phase 2
- [ ] Variance + driver ledger reviewed and approved **before** mutating the model. Review with user.

### Phase 3 — Align the budget

#### Task 6: Apply internal-fixable drivers in the workbook
**Description:** Update the model's drivers for the internal-fixable items so the **May–Dec
2026 forecast** is reshaped by the realized economics (e.g. `Inputs_Foundation` book size +
funding-cost 10%→~9%, populate blank `KPIs` pricing rows from realised Jan–Apr economics, trim
over-provisioned account forecasts). Backward facts in Jan–Apr applied unconditionally; forward
assumptions default-internal per AD6. Operate on the xlsx; back up first; re-verify recompute/balance.
**Acceptance criteria:**
- [ ] All ledger items classed "internal" are applied (Jan–Apr facts + May–Dec forward assumptions); loan schedule untouched (deferred to client).
- [ ] Backup kept; post-edit recompute shows no broken formulas / balance holds; 2026 forecast reflects the updated drivers.
**Verification:**
- [ ] Re-run budget-vs-actual (T4): the closed variances shrink; the open ones are exactly the NEEDS-CLIENT set.
**Dependencies:** T5
**Files likely touched:** `clients/almacena/budget/Almacena-26_AprActuals.xlsx` (+ `.bak`)
**Estimated scope:** Medium

#### Task 7: Client input request (the minimal ask)
**Description:** Produce the short list of what still needs the client after internal
alignment — primarily the loan-schedule rebuild (JSKR, Godelax renewal, AI principal, new
lenders VD/KH, blended rate) and any genuinely external assumptions.
**Acceptance criteria:**
- [ ] A client-facing request lists each item, why it's needed, and what we already inferred.
- [ ] Nothing on the list is resolvable from management data (else it belongs in T6).
**Verification:**
- [ ] Cross-check: every NEEDS-CLIENT ledger item appears; no INTERNAL item leaks in.
**Dependencies:** T5
**Files likely touched:** `clients/almacena/budget/CLIENT_INPUT_REQUEST.md`
**Estimated scope:** Small

### Checkpoint: After Phase 3
- [ ] Budget aligned to management data on everything we control; clean client ask drafted. Review with user.

### Phase 4 — Anchor in skills (distill from doing)

#### Task 8: Write `references/almacena.md`
**Description:** Capture the Almacena-specific reference: model contract (entities, budget
taxonomi tabs, driver sheets), the driver map (which variance → which sheet/account), the
quirks (crossed filenames, position-keyed months, stale loan schedule), exact commands, and
the April worked example (the ledger).
**Acceptance criteria:**
- [ ] A new engineer can locate every driver and re-run the alignment from this file.
- [ ] Quirks and the internal-vs-client boundary are explicit.
**Verification:**
- [ ] Every path/command in it exists / runs.
**Dependencies:** T6, T7
**Files likely touched:** `.claude/skills/model-maintenance/references/almacena.md`
**Estimated scope:** Medium

#### Task 9: Write the generic `model-maintenance/SKILL.md`
**Description:** Encode the generic alignment process: when to fire, the loop (build/verify
actuals → compute budget-vs-actual → trace to driver → classify internal/needs-client → fix
internal in the workbook → draft the client ask), and the cardinal rule (fix the driver, not
the formula-derived output line; align internally before asking the client). Point to the
per-client reference.
**Acceptance criteria:**
- [ ] `description` triggers on "align budget", "budget vs actual", "update the model", "reforecast", "before asking the client".
- [ ] Body is client-agnostic; client specifics are deferred to `references/<client>.md`.
**Verification:**
- [ ] Following SKILL.md + references/almacena.md reproduces the April ledger.
**Dependencies:** T8
**Files likely touched:** `.claude/skills/model-maintenance/SKILL.md`
**Estimated scope:** Small

#### Task 10: Validate the skill end-to-end
**Description:** Follow the skill cold (fresh session/subagent) to reproduce the driver ledger
and client request for Almacena April, confirming the doc is sufficient; fold gaps back in.
**Acceptance criteria:**
- [ ] A cold run reproduces the ledger + client ask with no undocumented step.
**Verification:**
- [ ] Artifacts match T5/T7; any gap patched into SKILL.md / reference.
**Dependencies:** T9
**Estimated scope:** Small

### Checkpoint: Complete
- [ ] Almacena budget aligned to management data; minimal client ask drafted; a triggering,
      battle-tested `model-maintenance` skill with an Almacena reference. Review for merge.

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Mutating the hand-tuned model breaks formulas/balance | High | AD3: back up + recompute-verify; checkpoint approves the ledger before any edit |
| Misclassifying a needs-client item as internal (or vice-versa) | Med | T5 ledger is explicit + reviewed at the Phase 2 checkpoint before mutating |
| Loan schedule stale and not client-derivable | Med | AD4: it goes to the client request; not force-fixed |
| Model xlsx is gitignored client data | Low | Skill references it by path; tracked outputs are `.md` (ledger/request/reference), consistent with existing budget docs |
| Skill drifts from the model | Low | AD2 distill-from-doing + T10 validation; reference points at real paths/commands |

## Resolved (was Open Questions)
- **Skill name:** `model-maintenance`. ✓
- **Period:** focus FY2026; actuals = 2025 full + 2026 Jan–Apr; reforecast = 2026 May–Dec; model extends beyond 2026 but 2026 is the target. ✓
- **Boundary judgment:** backward facts (Jan–Apr) unconditional; forward assumptions (May–Dec)
  default-internal from realized economics, logged in `references/almacena.md`, client asked only
  for non-inferable items (loan schedule). Per AD6; any item flippable to "ask client". ✓

## Open Questions
- None blocking.
