# `clients/` — per-client work & the scratch convention

Each `clients/<client>/` folder holds one client's config, inputs, outputs, and
working scripts. This file defines **what belongs where**, and the **graduation
rule** that keeps daily scratch from silently becoming untracked load-bearing code
(the drift that the 2026-06-20 restructure is undoing).

## Layout of a client folder

```
clients/<client>/
  config.yaml        declares use cases, source files, brand/voice overrides   [tracked]
  mapping.yaml       MR → taxonomi mapping (report use case)                    [tracked]
  README.md          colleague-facing: input → pipeline → output               [tracked]
  onboarding.md      engineer-facing setup + runbook                           [tracked]
  chart_specs/       chart definitions (charts use case)                       [tracked]
  one_offs/          sanctioned scratch — see below                            [tracked]
  raw/               source workbooks/files                                    [gitignored]
  reference/         source decks / PDFs / templates                           [gitignored]
  data/              generated SQLite DB                                       [gitignored]
  charts/  reports/  generated output                                          [gitignored]
```

Inputs and the *definitions* of work are tracked; **raw client data and generated
output are gitignored** (see the repo `.gitignore`).

## `one_offs/` — sanctioned scratch (Tier ④)

`one_offs/` is the **explicitly allowed** home for working scripts and notes that
are specific to one client and one moment: a month's build script, an ad-hoc
analysis, a reproduction gate, investigation notes.

**It is tracked** — commit your scratch. "Scratch" means *narrow in scope*, not
*untracked*. Untracked working code is the exact failure the restructure is fixing:
it can't be reviewed, tested in CI, or recovered if lost.

Belongs in `one_offs/`:
- A one-client, one-purpose build/analysis script (`build_taxonomi.py`,
  `build_unit_economics.py`, `repro_gate.py`).
- Working notes / audit logs for a specific month or investigation (`*.md`).

Does **not** belong in `one_offs/`:
- Anything imported by another client or by `core/` (that's shared code → `core/`).
- Generated data or output (gitignored folders above).
- Secrets or raw client data (gitignored).

## The graduation rule

Promote a `one_offs/` script into a shared `core/` capability **when either is true**:

1. **It recurs** — you've run essentially the same logic for the same client across
   multiple months and copy-paste-tweak it each time, **or**
2. **It appears in a 2nd client** — you're about to copy it into another client's
   `one_offs/`. The copy is the trigger: unify the shared spine in `core/` (with a
   thin per-client adapter) instead of forking it.

Graduation is **gated by a reproduction test** (the almacena Q1-gate / scaleflex
CF-guard / unde repro pattern): pin the current output first, then move the logic,
then prove the test still passes. Nothing moves before its golden test exists. This
is the opportunistic-migration rule (AD6) — promote when next touched for real work,
not in a big bang.

## See also

- Document taxonomy & living-docs workflow — `docs/doc-map.md`
- Architecture & roadmap — `docs/superpowers/specs/2026-06-20-architecture-report-and-roadmap.md`
- Git workflow & undo cheatsheet — `docs/git-workflow.md`
