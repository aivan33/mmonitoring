# Architecture Report & Roadmap — Current State, Separation of Concerns, Path Forward

**Date:** 2026-06-20
**Status:** Report + roadmap (report-only; no code changes in this pass)
**Decisions locked (2026-06-20 update):** (1) **one repo + enforced boundary guard** — §4 Option A + Middle path; the split is closed. (2) Phase 0 expands with a **living-docs workflow** (doc-map + path guard) and a **git workflow + learning track** (level: basics-shakily → branches / undoing mistakes / reading history).
**Supersedes the *roadmap* of:** [2026-06-12 repo-restructure design](2026-06-12-repo-restructure-design.md) — that design's decisions (AD1–AD9) still stand; this doc reconciles them against what actually shipped and re-plans the remaining work.

---

## 1. Why this report

The 2026-06-12 design diagnosed the repo as "out of control" and laid out a Phase 0–3
roadmap. Eight days of real client work have happened since (model parser, variance,
unde onboarding, ~380 tests). The tree has moved, but **the README and `architecture.md`
still describe the pre-2026-06-12 world**, and some Phase 0 safety work was skipped while
new untracked drift accumulated.

This report does three things:
1. **Current-state inventory** — what the use cases actually are *today*, grounded in the tree.
2. **Separation-of-concerns assessment** — where boundaries are clean, where they're tangled,
   plus the **one-repo vs split tradeoff** (the open decision).
3. **Updated roadmap** — reconciled against 2026-06-12: done / outstanding / newly-needed.

Everything below is grounded in the committed tree at `chore/restructure-safety` (HEAD
`700ee5e`), `git ls-files`, the import graph, and a green `uv run pytest -q` (**379 passed**).

---

## 2. Current-state use-case inventory

The repo is one Python package (`core/`) + thin CLI scripts + per-client folders. There is
**one shared data layer** (`core/data`, SQLite over a canonical taxonomi format) and a set of
use-case pillars that read from it.

| Pillar | Tracked source | Reality today | README/arch says |
|---|---|---|---|
| **`core/data`** | 10 modules (schema, build, query, validation, integrity, aggregate_formulas, loaders/financials, loaders/kpis) | **Real & central.** The moat. Canonical `(Data,Group,Subgroup)×month` → SQLite, query API. | ✓ accurate |
| **`core/charts`** | 4 modules (spec, render, tokens) | **Real.** Spec→matplotlib→PNG+JSON sidecar. Imports `core.data.query`. | ✓ accurate |
| **`core/report`** | 4 modules (mr, mr_to_taxonomi, variance) | **Real, and variance is no longer stubbed** — `compute_variance` + 449-line test exist. | ✗ **stale** — arch says "variance + commentary stubbed / `NotImplementedError`" |
| **`core/model`** | 6 modules (contract, cells, flow, formula, mapview) | **Real, but it's a model-*workbook parser*** (structure→cells→flow→formula→human-readable map), **not** the "projection/budget engine" the 2026-06-12 plan named. **Standalone — imports nothing from `core.data`.** | ✗ **absent** — neither README nor arch mentions `model` at all |
| **`core/text`** | 1 file (`__init__.py`, **0 lines**) | **Still a stub.** | ✓ ("planned") but the deck-text deliverable format is already in use via one_offs |
| **`core/bronze`, `core/cli`, `core/config`** | **0 tracked `.py`** — `__pycache__` only | **Ghosts.** Phase-0 Task 2 (delete) was never executed. The tree still lies. | not mentioned |

### Capabilities that exist but live *outside* `core/` (untracked or in one_offs)
- **Rolling-budget / projection engine** — `clients/farada/one_offs/build_rolling_budget.py`
  (+ v3 audit, freeze/validate, verify). This is the *actual* budget engine. So **"model" names
  two different things**: the parser in `core/model`, and the projection engine in Farada's one_offs.
- **Taxonomi builders** — `clients/{almacena,scaleflex,unde}/one_offs/build_taxonomi.py`,
  three independent copies. No shared `core/taxonomi/` spine (Task 4 not done).
- **Consolidation + consolidation-check** — Farada logic, not yet a `core/data/consolidate.py`
  capability (Task 6 not done).
- **Model diagnostics / unit economics / leverage** — new untracked Farada one_offs
  (`build_model_v3.py`, `build_unit_economics*.py`, `build_leverage_ratio.py`).

### Client/use-case matrix (who uses what)
- **charts:** cupffee (primary), ahaplay/scaleflex (text-mode KPIs feed)
- **report:** farada (primary, consolidated), unde (in onboarding now), almacena, scaleflex
- **text:** ahaplay, scaleflex, cupffee — delivered via one_offs + skills, **not** `core/text`
- **model/budget:** farada (rolling budget + fundraising model), almacena (model diagnostic, deferred)

---

## 3. Separation-of-concerns assessment

### 3.1 What is clean (keep)
- **Layering is sound.** Import graph inside `core/`:
  - `charts/render` → `core.data.query` (+ own spec/tokens)
  - `data/build` → own internals (loaders, schema, integrity, aggregate_formulas)
  - **No pillar imports another pillar.** AD9 ("pillars depend on `core/data` only; `core/data`
    never imports a pillar") is *already holding* — without enforcement.
- **`core/model` is fully decoupled** (zero `core.data` imports) — easiest thing in the repo to
  reason about or move.
- **The data layer is the genuine moat.** Charts and report both bottleneck through the canonical
  taxonomi + query API. This is the budget↔actuals link the 2026-06-12 design protected.

### 3.2 What is tangled / drifting (fix)
1. **Ghost modules** (`bronze`, `cli`, `config`) — still present, still `.pyc`-only. The #1 "can't
   find things" cause from the original diagnosis is unaddressed.
2. **Untracked drift re-emerged** — the Phase-0 promise ("no untracked `.py` under `clients/`") has
   already broken:
   - The **entire `unde` client** is untracked: `config.yaml`, `mapping.yaml`, `onboarding.md`,
     `MR_LAYOUT.md`, `README.md`, and 3 one_offs (`build_taxonomi.py`, `gen_mapping.py`, `repro_gate.py`).
   - 4 new untracked Farada one_offs.
   - **Root cause:** Task 1 was a one-time commit, but no *convention* (Task 9) was ever put in
     place to stop re-accumulation. The problem is structural, not incidental.
3. **Duplicated taxonomi builders** — three independent `build_taxonomi.py` copies; no shared spine.
   The "setup friction" pain persists.
4. **"Model" is overloaded** — a parser in `core/model` and a projection engine in Farada one_offs
   share a name and a mental model but no code. A reader can't tell which is "the model pillar."
5. **Docs describe a repo that no longer exists** — README ("Three use cases", "text planned",
   model absent) and `architecture.md` ("variance stubbed") are factually wrong now. This is itself a
   separation-of-concerns failure: the *story* and the *code* have diverged.

### 3.3 Scorecard vs the 2026-06-12 roadmap

| Task | Intent | Status (2026-06-20) |
|---|---|---|
| T1 commit untracked baseline | one-time | ⚠️ **regressed** — unde + farada untracked again |
| T2 delete ghost modules | bronze/cli/config | ❌ **not done** |
| T3 golden reproduction tests | pin builder outputs | 🟡 **partial** — ~380 tests incl. model/variance/integrity; per-client *builder* golden gates patchy (unde has `repro_gate.py`, untracked) |
| T4 `core/taxonomi` spine | unify builders | ❌ not done |
| T5 `core/model` engine + budget mode | projection engine | 🟡 **diverged** — a *parser* shipped instead; the projection engine is still in one_offs |
| T6 `core/data/consolidate.py` | consolidation capability | ❌ not done |
| T7 `core/text` real | stub → real | ❌ not done (still 0 lines) |
| T8 one skill per pillar | discoverability | 🟡 partial — `legacy-reporting` + `model-maintenance` skills exist; no charts/text/report/taxonomi skills |
| T9 scratch convention + archive | stop drift | ❌ **not done** ← this is why §3.2.2 regressed |
| T10 rewrite README/architecture | honest docs | ❌ not done (now actively wrong) |

**Net:** real capability grew (model parser, variance, big test suite), but **none of the
"legibility & safety" tasks landed**, and two of them (T1, T9) regressed. The repo is *more
capable* and *less legible* than on 2026-06-12.

---

## 4. The open decision: one repo vs split

You flagged this as a live tradeoff. Here is the honest overview.

### The link that matters
The strategic value is **budget/model ↔ actuals reforecasting**: align a client's model to their
management actuals, then ask for new inputs. That link runs *through `core/data`*. Today
`charts` and `report` both depend on `core.data.query`; `model` (the parser) does not yet, and the
budget engine (in one_offs) consumes actuals informally.

### Option A — One repo, shared `core/data` (current design, AD1)
- **For:** Zero cross-repo seam on the moat. One `pytest`, one dependency set, atomic refactors,
  one place to onboard. The pillars are *already* cleanly layered (§3.1) — the benefit a split
  would buy (enforced boundaries) is ~80% already present.
- **Against:** Nothing enforces AD9 except discipline; a careless import could couple pillars.
  One repo means one blast radius if `core/data`'s schema changes.
- **Cost to adopt:** ~0 (status quo).

### Option B — Split into separate repos/packages (charts / text / report / model + a shared `core-data` package)
- **For:** Hard, enforced boundaries; each pillar versioned and released independently; smaller
  mental surface per repo.
- **Against:**
  - **Puts a published-package seam directly on the moat.** Every pillar repo pins a version of
    `core-data`; a schema change becomes a multi-repo, version-bump migration instead of one commit.
    This is exactly the copy-paste/lag seam AD1 was written to avoid.
  - **The budget↔actuals loop spans `model` + `data` + `report`** — the highest-value workflow would
    be the *most* fragmented.
  - Client folders (`clients/<c>/`) mix charts specs, report mappings, model inputs, and one_offs —
    they don't split cleanly along pillar lines, so you'd either duplicate client config across repos
    or invent a shared client-config package too.
  - Operational tax: N repos, N CI configs, N dependency bumps, for a single-maintainer tool.
- **Cost to adopt:** High; mostly upfront and irreversible-ish.

### Middle path — One repo, **enforced** internal boundaries (recommended)
Keep one repo, but stop relying on discipline:
- An **import-linter / test guard** that fails CI if a pillar imports another pillar, or if
  `core/data` imports any pillar (mechanizes AD9 — cheap, ~1 test file).
- Treat each pillar as if it had a published contract (stable input→deliverable pair) *without*
  paying the multi-repo tax.
- If a pillar ever genuinely needs independent release (e.g. `charts` becomes a product), the clean
  internal boundary makes a later extraction a lift-and-shift, not a rewrite.

**Recommendation:** **Stay one repo (Option A) + add the boundary guard (Middle path).** The split's
only real win — enforced separation — is buyable for one test file, while the split's cost lands
squarely on the budget↔actuals moat. Revisit only if a pillar needs to ship to a third party on its
own cadence. This re-affirms AD1 with teeth, rather than reopening it.

> **DECISION (2026-06-20): LOCKED — one repo + boundary guard.** The split is closed and will not be
> reopened unless a pillar needs independent third-party release. AD1 stands; the guard (R4) makes it
> enforced rather than disciplinary. This unblocks all of Phase 0.

---

## 5. Updated target architecture

```
core/
  data/          ✓ schema, build, query, validation, integrity, loaders
                 + consolidate.py        (T6 — formalize Farada consolidation)
  taxonomi/      NEW shared source→taxonomi spine + per-client adapters (T4)
  charts/        ✓
  report/        ✓ reconcile / variance (real) / commentary
  model/         ✓ workbook PARSER (contract/flow/formula/cells/mapview)
                 + project/  NEW home for the rolling-budget engine (graduated from farada/one_offs)
                 + diagnose.py  (deferred — model-doctor)
  text/          stub → real (T7) — slides.md (plain) + analysis.md
clients/<c>/
  config.yaml, mapping.yaml, chart_specs/ ...   (tracked inputs)
  one_offs/      TRACKED sanctioned scratch + README + graduation rule (T9)
  raw/ data/ reports/ charts/                   (gitignored outputs)
.claude/skills/  one skill per pillar (T8) + existing legacy-reporting/model-maintenance
docs/            architecture.md (rewritten, T10) + onboarding-* + specs/
tests/           per-module + per-client builder golden gates (T3) + boundary guard (NEW)
```

**Naming fix (new):** disambiguate "model". `core/model` = the **parser/reader** (analyzes an
existing model workbook). The **projection engine** graduates to `core/model/project/` (or
`core/budget/`). Decide the name in §8.

### 5.1 Document taxonomy (the living-docs model)

Docs went stale because there was no rule for *which doc owns what* and *when it must change*. The
fix is a small taxonomy with one update rule per tier. Every doc in the repo belongs to exactly one
tier:

| Tier | Examples | Update rule | Allowed to go stale? |
|---|---|---|---|
| **① Canonical** (how it works *now*) | `README.md`, `docs/architecture.md`, `docs/onboarding-*.md`, `clients/<c>/onboarding.md`, `clients/<c>/README.md` | **Update in the same change that alters the behavior it describes.** A pillar change that lands without touching its canonical doc is incomplete. | **No** — guarded |
| **② Dated decisions** (point-in-time) | `docs/superpowers/specs/<date>-*.md` (incl. this file) | **Append-only.** Never rewrite history; supersede with a *new* dated doc that links back (as this one supersedes the 2026-06-12 roadmap). | N/A — frozen by design |
| **③ Skills** (process/runbook) | `.claude/skills/*/SKILL.md` | Update when the pillar/process it encodes changes; must reference real paths. | No — guarded (R4 already lints skill refs) |
| **④ Scratch** (working notes) | `clients/<c>/one_offs/*.md` | None. Ephemeral by definition; graduate to a Canonical doc when the work recurs (R3 rule). | **Yes** — explicitly |
| **⑤ Agent memory** (separate system) | `MEMORY.md`, `memory/*.md` | Maintained by Claude across sessions; not part of repo docs but mirrors tiers ①/② facts. | Self-corrected on recall |

**The rule that keeps Canonical docs alive:** *the doc-map lists, per pillar, its owning Canonical
doc; a behavior change to a pillar updates that doc in the same commit.* The light guard (R5) makes
the cheap half of this enforceable: a test that fails if any Canonical/Skill doc references a path
that no longer exists — the most common and most misleading form of drift.

---

## 6. Roadmap (re-planned)

Ordered for safety-first, each phase leaves the tree green. Sizes: S/M/L per the planning skill.
**Phase 0 now carries the two locked additions** (living-docs workflow R5; git track R6) alongside the
original safety tasks.

### Phase 0 — Stop the bleeding + foundations (legibility, safety, workflow) — do this first

- **R1 — Re-baseline untracked work** *(S)* — **also git hands-on exercise #1**. Commit the `unde`
  client and the 4 Farada one_offs as-is. Run as a *guided* commit: you drive the commands, Claude
  coaches (this is the first live rep for R6).
  *AC:* `git status --porcelain` shows no `??` `.py`/config under `clients/`; `pytest` still green.
  *Files:* `clients/unde/**`, `clients/farada/one_offs/*.py`, maybe `.gitignore`.

- **R2 — Delete ghost modules** *(S)*. Remove `core/bronze`, `core/cli`, `core/config`; confirm
  `__pycache__` is gitignored.
  *AC:* `git grep -nE 'core\.(bronze|cli|config)'` empty; the three dirs gone; `pytest` green.
  *Files:* `core/bronze/`, `core/cli/`, `core/config/`, `.gitignore`.

- **R3 — Scratch convention + archive rule** *(S)*. Add `clients/README.md` stating what belongs in
  `one_offs/` (Tier ④) vs `core/` and the "graduate when it recurs / appears in a 2nd client" trigger.
  **This is the fix for the §3.2.2 regression — without it R1 just rots again.**
  *AC:* convention doc exists and is linked from the doc-map (R5); `_archive/` confirmed gitignored.
  *Files:* `clients/README.md`, `.gitignore`.

- **R4 — Boundary guard (LOCKED decision)** *(S)*. One test asserting no pillar imports another
  pillar and `core/data` imports no pillar — mechanizes AD9 and the §4 lock. Model it on the existing
  `tests/test_skill_references.py` / `test_spec_lint.py`.
  *AC:* guard passes on current tree; fails on a deliberately-added `core/charts → core/report` import.
  *Files:* `tests/test_boundaries.py`.

- **R5 — Living-docs workflow: doc-map + path guard** *(S→M)* — **NEW**. Write `docs/doc-map.md`
  encoding the §5.1 taxonomy: every tracked doc → its tier, and for Tier-① docs the pillar it owns and
  its "update when X changes" trigger. Add a path-guard test that scans Tier-①/③ docs for path-like
  references and asserts each exists (extend the `test_skill_references.py` pattern to README +
  `architecture.md` + onboarding + per-client docs). Fix any existing dead refs surfaced.
  *AC:* (a) `docs/doc-map.md` lists every tracked doc with tier + owner; (b) path-guard test green on
  the current tree; (c) breaking a path in a Tier-① doc turns it red.
  *Files:* `docs/doc-map.md`, `tests/test_doc_paths.py`.
  *Depends:* R1, R2 (clean tree before pinning paths).

- **R6 — Git workflow + learning track** *(M — time is learning, not code)* — **NEW**. Level:
  *basics, shakily*. Produce `docs/git-workflow.md` (Tier-① doc, added to R5 map) covering, with
  **this repo's real examples**:
  1. **Mental model** — the three trees (working tree → staging → commit) + remote; what a branch *is*.
  2. **Daily loop** — `status → diff → add → commit → push`, and the conventional-commit message style
     already in use (`feat(scope): …`, `docs(scope): …`).
  3. **Branches** — why we branch per workstream (e.g. `chore/restructure-safety`), switching, and
     merge-vs-PR — including the standing rule to branch off `main` rather than commit to it directly.
  4. **Undoing mistakes** (your stated gap) — a cheatsheet: unstage a file, discard a change, amend the
     last commit message, revert a pushed commit, recover with `reflog`.
  5. **Reading history** — `log --oneline`, `show`, `diff`, `blame` to answer "what changed and why".
  6. **Agreed collaboration workflow** — branch naming, commit cadence (one logical change per commit),
     and the you-vs-Claude division of labour for commits.

  Learn by doing: R1 is exercise #1; then 3 short practice reps on a throwaway branch — (a) stage then
  discard, (b) commit then amend the message, (c) branch → small change → merge back.
  *AC (capability, verified live):* unaided, you can — branch + commit a logical change + push; read
  `git log --oneline`/`git show` and explain a commit; recover from the three common mistakes
  (amend / unstage / discard). The guide documents each.
  *Verification:* live walkthrough on a scratch branch — you perform each capability, Claude observes.
  *Depends:* guide is independent; the first live rep rides on R1.

> **Checkpoint A (review before structural work):** tree has no ghosts, no untracked client `.py`;
> drift is structurally prevented (R3) and boundaries enforced (R4); docs have an owner-map + path guard
> (R5); you can run the daily git loop and recover from mistakes unaided (R6). `pytest` green.

### Phase 1 — Tell the truth (docs reconcile) — cheap, high-leverage
- **R7 — Rewrite README + `architecture.md`** *(S→M)*. Reflect 4 real pillars (data/charts/report/model),
  mark variance as shipped, add the model parser, drop the "cleanup in progress" caveat, fix the layout
  block. **Now governed by the R5 doc-map** (these are its first Tier-① docs to bring current).
  *AC:* every path named exists (path guard green); model + real variance described; caveat gone.

> **Checkpoint B:** a new reader can trust the docs. Highest "fixes 'can't find things'" per unit effort.

### Phase 2 — Shared spine (additive; no client behavior change), gated by golden tests
- **R8 — Per-client builder golden gates** *(M)*. Promote the unde `repro_gate.py` pattern to a
  tracked, deterministic golden test per active taxonomi/budget builder (almacena Q1 gate, scaleflex
  CF guard, unde reproduction, farada rolling-budget snapshot). *Precondition for R9/R10/R11.*
- **R9 — `core/taxonomi/` spine + 1 reference adapter** *(M)*. Extract the shared source→taxonomi
  spine; migrate exactly one client through it, proving the adapter seam, gated by its R8 test. No
  other client migrated (AD6 opportunistic).
- **R10 — `core/data/consolidate.py`** *(M)*. Formalize Farada consolidation + consolidation-check;
  gated by a reproduction test of current consolidated numbers.

> **Checkpoint C:** shared spine exists and is tested; no client's numbers changed (all golden gates green).

### Phase 3 — Pillar completion
- **R11 — Graduate the projection engine** *(M)*. Move `build_rolling_budget.py` from Farada one_offs
  into `core/budget/` (or `core/model/project/` — §8 Q2), reproduction-gated against its R8 snapshot.
  Resolves the "two models" overload.
- **R12 — `core/text` stub → real** *(M)*. Implement the documented deck-text format (slides.md plain +
  analysis.md formatted) for one client from taxonomi + source PPTX structure.
- **R13 — One skill per pillar** *(M)*. Author `.claude/skills/` for charts, text, report, taxonomi,
  model — input contract → command → deliverable → gotchas. (legacy-reporting + model-maintenance stay.)

> **Checkpoint D:** every pillar real + documented + skilled; scratch sanctioned; docs honest and guarded.

### Deferred backlog
- **R14 — Model-doctor / broken-budget diagnostic** *(M)*. Balance-sheet imbalance matching (was T11;
  tied to the almacena M4 diagnostic). Schedule after Phase 3.

### Dependency graph
```
Phase 0
  R1 ──┬── R5 (doc-map needs clean tree)
  R2 ──┘
  R3            (independent; feeds R5 link)
  R4            (independent — LOCKED guard)
  R6  git guide independent; first live rep rides on R1

Phase 1
  R5 ── R7  (README/arch are R5's first Tier-① docs)

Phase 2
  R8 ──┬── R9
       └── R10
Phase 3
  R8 ── R11   (needs farada budget gate)
  R12          (independent)
  R9,R11,R12 ── R13  (skills describe real paths)
  R11 ── R14   (deferred)
```

---

## 7. Risks & mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| R1 re-baseline then drift returns again | High | R3 convention + R4 guard make it structural, not a one-time cleanup |
| Promoting a builder silently changes client numbers | High | R8 golden gates precede R9/R10/R11; nothing moves before its test exists |
| "Two models" confusion persists | Med | R11 graduates the engine + §5 naming decision; one skill (R13) names the boundary |
| Docs drift again after R7 | Low→Med | R5 doc-map (owner + update trigger per doc) + path-guard test; Tier-② specs are append-only so can't rot |
| Git mistakes lose work during learning | Med | R6 practice reps happen on throwaway branches; `reflog` recovery is in the cheatsheet; nothing destructive run on `main` |
| Scope creep into big-bang unification | Med | AD6 opportunistic migration reaffirmed; R9 migrates exactly one client |

## 8. Open questions (need your call)
1. ~~**Repo strategy**~~ — **RESOLVED 2026-06-20: one repo + boundary guard (LOCKED, §4).**
2. ~~**"Model" naming**~~ — **RESOLVED 2026-06-20: `core/budget/`** for the projection engine (R11),
   keeping `core/model/` as the parser. Not built until Phase 3.
3. ~~**Phase 0 execution**~~ — **RESOLVED: execute now.**
4. ~~**Git pacing**~~ — **RESOLVED: spread** the practice reps across R1/R2/R3.

## 9. Execution mode (2026-06-20)

Agreed working contract for Phase 0:
- **Claude executes autonomously** all non-git work (writing tests/docs, deleting ghosts) and verifies
  with `pytest` before each commit point.
- **The user drives every `git` command** for R1–R3 (the spread git reps), via `! <cmd>` so output
  lands in the session and Claude can coach. Claude does **not** run `add`/`commit`/`push` for these.
- After R3, the user is fluent enough that Claude may commit R4/R5 directly (or the user continues —
  their call at Checkpoint A).
- Each rep teaches a slice: **R1** = status → staging → first commit(s) + message convention;
  **R2** = reading a diff before committing + why we're on a branch; **R3** = amend / fixing a commit.
```

---

## Summary

The 2026-06-12 *design* still holds — the problem is that its *safety/legibility tasks never landed*
while real capability (model parser, variance, ~380 tests) grew on top. The repo is **more capable
and less legible** than it was. The fix is small and front-loaded: kill the ghosts, re-baseline +
*prevent* untracked drift, mechanize the boundary you already mostly respect, and make the docs honest
— then resume the shared-spine work behind golden gates. Stay one repo; buy enforced separation for the
price of one test file rather than the price of N repos on top of your moat.

**Locked 2026-06-20:** one repo + boundary guard. Phase 0 now also installs a **living-docs workflow**
(a doc-map that gives every doc an owner + update trigger, plus a path guard) and a **git learning
track** that turns the real Phase-0 commits (R1–R3) into your first guided git reps — so you learn
branches, undoing mistakes, and reading history on safe, real changes rather than toy examples.
