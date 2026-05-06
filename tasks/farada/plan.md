# Implementation Plan: FaradaIC Onboarding — Monthly Reporting Pack

> Saved here, not at `tasks/plan.md`, because that file documents the in-progress Cupffee/Almacena chart-inventory work and shouldn't be clobbered. Mirror of `tasks/farada/todo.md`.

## Goal (recap from user + downstream prompt)

Onboard **FaradaIC** — a deep-tech sensor company (Germany + Serbia, consolidated upstream in the MR file) — as a third client. Build a **new monthly reporting side** of the project. Each month, given a fresh master accounting workbook (the DATEV-derived "MR" file), produce a **monthly reporting pack**:

1. **Populated taxonomi xlsx** — same shape and formatting as the previous month's taxonomi-actual file, with the new month's column filled in.
2. **Reconcile flags** — Markdown deviation report comparing prior months between the MR and the existing taxonomi (catches data-prep drift).
3. **Variance analysis** — Markdown + CSV tables: Actual vs Realistic budget, MoM, Q1 YTD, for IS / CF / BS. **YoY is out of scope** — no 2025 source data, and the user has confirmed YoY isn't needed for the March 2026 report.
4. **Commentary scaffolding** — Markdown outline mirroring the previous month's PDF structure, with key figures filled in and material variances flagged for discussion.
5. **Discussion checklist** — Markdown bullet list of every line item that warrants management attention, with the numbers and a draft question per item.

**No charts.** The existing `core/charts/` pipeline is not reused for FaradaIC. The deliverable is data + Markdown.

The downstream prompt at `clients/farada/prompt-mm-mar26.md` describes a manual 5-phase workflow for one specific month. This plan systematizes that workflow so it runs by command for every subsequent month, with the user reviewing at checkpoints rather than re-reading 200 lines of prompt each time.

## What's already there vs what's new

### Reusable as-is

| Component | Notes |
|---|---|
| `core/loaders/financials.py` | Already handles `IS (Actual)`, `CF Indirect (Actual)`, `BS (Actual)`, `IS (Realistic)`, etc. The FaradaIC taxonomi files are already in canonical format (verified: 56 IS rows × 15 cols, 22 CF Indirect rows, 21 BS rows, 1 empty CF row). |
| `core/schema.py` | Has `entity` and `display_order` columns; FaradaIC will use a single entity. |
| `core/query.py` | Statement / aggregation / trend / YTD helpers cover the variance tables directly. |
| `scripts/build_db.py`, `scripts/validate.py` | `build_db.py farada` will work once the config exists. |

### New for this side of the project

| Component | Purpose |
|---|---|
| `core/loaders/mr.py` | Reads the MR workbook (P&L + CF + BS sheets), maps DATEV-derived rows → taxonomi `(data, grp, subgroup)` keys using a config-driven mapping table, returns one month's column for each statement. |
| `core/mr_to_taxonomi.py` | Orchestrator: copies the prior taxonomi-actual xlsx, overwrites the new month's column with the MR-extracted values, saves as the new monthly file. **Preserves the source file's formatting** (cell styles, column widths) by load-and-modify rather than write-from-scratch. |
| `core/reporting/reconcile.py` | Compares two parallel sources (MR vs taxonomi-actual) for prior months; emits a deviation report (line-item, source A value, source B value, diff). Whitelists known discrepancies. |
| `core/reporting/variance.py` | Variance computations: Actual vs Budget, MoM, Q1 YTD — for IS / CF / BS. No YoY. Operates against the loaded DB. |
| `core/reporting/commentary.py` | Structured commentary scaffolding: walks the variance results and emits a Markdown outline mirroring the previous month's PDF. Key figures interpolated, material variances flagged. Initially template-driven; LLM-assisted drafting can replace it later. |
| `scripts/build_report.py` | CLI orchestrator: `python scripts/build_report.py farada 2026-03` → MR → taxonomi → reconcile → rebuild DB → variance → commentary → checklist. |
| `clients/farada/{config.yaml, mapping.yaml, raw/, data/, reports/, reference/}` | Per-client layout. **No `charts/` subdir, no `specs/farada/`.** |

## Assumptions (confirmed with user)

1. **Single entity, `farada`.** Germany + Serbia are consolidated upstream in the MR (FX-converted at that step). The reporting pipeline never sees a split. The BS is German-only — in the MR and downstream — but it still rides under `entity='farada'`; we note the BS scope in the commentary, we don't model it as a separate entity.
2. **EUR-only.** All FX happens upstream in the MR. No `fx_rate` config needed for FaradaIC.
3. **The deliverable is the populated taxonomi xlsx + Markdown analysis.** Same row/column layout as the input file, no formatting changes (we copy-and-modify, not write-from-scratch). No PDF assembly, no charts.
4. **Charts are out of scope for FaradaIC.** The existing chart pipeline is not used.
5. **Other MR sheets are mapping context, not noise.** P&L / CF / BS are the only sheets the current pipeline reads. The remaining sheets (`BWA`, `ControllingReport BWA`, `CR-Upload`, `Trial balance`, `Balance Sheet`, `Serbia`, `P&L Mapping`) carry the upstream consolidation, FX conversion, and DATEV-account → taxonomi-line mapping logic. They are part of the mapping problem and will feed a future "deeper mapping" iteration of this plan (see **Phase F5 — Deeper mapping (next iteration)** below). They are explicitly **parked**, not ignored.
6. **Cadence: monthly.** Each new month, the user drops a new MR file in `raw/`, updates `as_of_date` and `reporting.mr_source` in `config.yaml`, runs `build_report.py`. Confirm.

## Architecture decisions

### 1. MR extraction is one-shot per month, written to disk

The MR is alien to the existing loader (different shape: headers in row 2, monthly columns spanning two years, multiple supporting sheets). Rather than teach `core/loaders/financials.py` about it, the new `mr_to_taxonomi.py` reads MR + the prior month's taxonomi-actual file and produces a new taxonomi-actual file on disk. Then the existing loader runs against the new file untouched.

**Why on-disk rather than in-memory?** (a) The user explicitly asks for the file as the primary deliverable. (b) Diff-able artifact: the user can open it and visually compare to the previous month. (c) Survives re-runs without re-reading the heavy MR workbook every time. (d) Preserves the taxonomi formatting (cell styles, column widths) automatically — openpyxl `load_workbook` + targeted overwrites + `save` keeps everything else byte-stable.

### 2. Mapping table lives in `clients/farada/mapping.yaml`

```yaml
# Maps MR sheet+row → taxonomi (statement, data, grp, subgroup).
# `mr_label` is captured for label-vs-row-index fallback (see Task 6).

mr_pnl_to_taxonomi_is:
  - { mr_row: 5,  mr_label: "Food Logistics",      data: Sales,         grp: Food Logistics,        subgroup: <name> }
  - { mr_row: 16, mr_label: "Eval-Kits",           data: Sales,         grp: Consumer Electronics,  subgroup: Eval-Kits }
  - { mr_row: 26, mr_label: "COGS",                data: Cost of Sales, grp: COGS,                  subgroup: COGS }
  # ... ~50 rows total per the prompt mapping table

mr_cf_to_taxonomi:
  - { mr_row: 4, mr_label: "Cash received from customers", data: ..., grp: Cust, subgroup: Cust }
  # ...

mr_bs_to_taxonomi:
  - ...

known_discrepancies:
  - { period: 2026-01, statement: IS, taxonomi_key: ["Cost of Sales","COGS","COGS"],
      reason: "MR aggregates COGS differently from taxonomi (52,403 vs 2,403). Confirm with user." }
  - { period: 2026-02, statement: BS, taxonomi_key: ["Other receivables","Other receivables","Other receivables"],
      reason: "MR shows 83,072; taxonomi 33,072 — investigate." }
```

The user reviews this once at Task 5; afterwards, the loader trusts it. Edits are one-line YAML changes.

### 3. Per-client layout

```
clients/farada/
├── config.yaml
├── mapping.yaml
├── MR_LAYOUT.md             ← Task 4 output: documents all 10 MR sheets
├── raw/                     ← user drops MR here; we generate the taxonomi here too
│   ├── mr_2026-03.xlsx
│   ├── taxonomi_act_2026-02.xlsx     ← previous month, snapshot
│   ├── taxonomi_act_2026-03.xlsx     ← generated this run
│   └── taxonomi_bp_2026.xlsx         ← budget (realistic scenario)
├── data/
│   └── farada.db
├── reports/
│   └── 2026-03/
│       ├── reconcile.md         ← prior-month deviation table
│       ├── variance.md          ← IS/CF/BS variance tables (Markdown)
│       ├── variance.csv         ← same tables, machine-readable
│       ├── commentary.md        ← drafted bullet points per report section
│       └── checklist.md         ← discussion items, carry-over topics
└── reference/
    ├── mm-fd-feb26.pdf
    └── prompt-mm-mar26.md       ← original prompt (kept for context)
```

No `charts/` subdirectory. No `specs/farada/`.

### 4. Config additions for FaradaIC

```yaml
client_name: FaradaIC
fiscal_year_start_month: 1
currency: EUR
as_of_date: 2026-03-01
entities:
  - farada

financial_sources:
  # Bumped each month to the latest generated taxonomi-actual file.
  - { file: raw/taxonomi_act_2025.xlsx,    year: 2025, entity: farada, currency: EUR }
  - { file: raw/taxonomi_act_2026-03.xlsx, year: 2026, entity: farada, currency: EUR }
  - { file: raw/taxonomi_bp_2026.xlsx,     year: 2026, entity: farada, currency: EUR }

reporting:
  mr_source: raw/mr_2026-03.xlsx
  mapping: mapping.yaml
  reference_pdf: reference/mm-fd-feb26.pdf
  carryover_topics:
    - Capitalization policy
    - Intercompany agreement / transfer pricing
    - KPI dashboard implementation
    - Food Logistics deal progress
  variance_thresholds:
    flag_pct: 20            # variance >20% off budget → flag for discussion
    flag_eur: 10000         # OR variance >€10K absolute
    reconcile_eur: 5        # MR-vs-taxonomi delta >€5 → list in reconcile.md
```

No `brand:` block — no charts, no styling.

## Dependency graph

```
clients/farada/raw/mr_2026-03.xlsx  (user drops)
        │
        ▼
core/loaders/mr.py ──────── mapping.yaml
        │
        ▼
core/mr_to_taxonomi.py
        │
        ▼
clients/farada/raw/taxonomi_act_2026-03.xlsx
        │
        ├──► core/reporting/reconcile.py ──► reports/2026-03/reconcile.md
        │
        └──► (existing) core/loaders/financials.py
                     │
                     ▼
              clients/farada/data/farada.db
                     │
                     ├──► core/reporting/variance.py ──► reports/2026-03/variance.md, variance.csv
                     │                                       │
                     │                                       ▼
                     └──► core/reporting/commentary.py ──► reports/2026-03/commentary.md
                                                              │
                                                              ▼
                                                          reports/2026-03/checklist.md
```

## Slicing strategy (vertical)

Each slice ends in a runnable command + a human checkpoint.

- **Slice F1 — Onboard FaradaIC into the existing data layer.** End state: `python scripts/build_db.py farada` produces `farada.db` with Jan/Feb 2026 actuals + 2026 budget loaded; `validate.py farada` exits 0 against 5–8 known cells. **Proves the existing pipeline carries the new client without code changes.**
- **Slice F2 — MR → Taxonomi extraction for a single month.** End state: `python scripts/build_report.py farada 2026-03 --extract-only` produces `taxonomi_act_2026-03.xlsx` and `reports/2026-03/reconcile.md`. **Proves the bridge from accounting to canonical works.**
- **Slice F3 — Variance analysis end-to-end.** End state: `python scripts/build_report.py farada 2026-03 --variance-only` rebuilds the DB against the new taxonomi and writes `reports/2026-03/variance.{md,csv}`. **Proves the numbers needed for the report are computable.**
- **Slice F4 — Commentary + checklist.** End state: `python scripts/build_report.py farada 2026-03` runs the full pipeline; `reports/2026-03/` contains `reconcile.md`, `variance.{md,csv}`, `commentary.md`, `checklist.md`. **Closes the loop on the manual prompt.**

## Phased task list

### Phase F1 — Onboard FaradaIC into the existing data layer

- **Task 1** — Reorganize `clients/farada/` into the standard layout (raw/, data/, reports/, reference/). Rename to canonical filenames. **XS.**
- **Task 2** — Author `clients/farada/config.yaml` with `reporting:` block. **XS.**
- **Task 3** — Build `farada.db` and add 5–8 FaradaIC assertions to `scripts/validate.py`. **S.**

### Checkpoint F1 — Existing pipeline carries FaradaIC
- `python scripts/build_db.py farada` clean.
- `python scripts/validate.py farada` exits 0.
- Spot-query returns expected IS for Feb 2026.
- **Review with user before proceeding to F2.**

### Phase F2 — MR-to-Taxonomi bridge

- **Task 4** — Inspect all 10 MR sheets. Document each in `clients/farada/MR_LAYOUT.md`: name, shape, role (whether currently consumed, or parked for the deeper-mapping next iteration). Capture P&L / CF / BS row and column indices the loader will use. **S.**
- **Task 5** — Author the full MR → Taxonomi mapping in `mapping.yaml` from the prompt's mapping table. **Sign-off step with user before locking.** **M.**
- **Task 6** — `core/loaders/mr.py`: extract one month per statement from the MR. Label-match first, MR-row-index as fallback. **M.**
- **Task 7** — `core/mr_to_taxonomi.py`: copy prior taxonomi-actual, overwrite new month's column, save as new file. Preserves formatting via openpyxl load-modify-save. **M.**
- **Task 8** — `core/reporting/reconcile.py`: prior-month deviation report (MR vs taxonomi). **S.**

### Checkpoint F2 — Bridge produces a clean monthly taxonomi
- `python scripts/build_report.py farada 2026-03 --extract-only` writes `raw/taxonomi_act_2026-03.xlsx` and `reports/2026-03/reconcile.md`.
- Manual eyeball: March 2026 column matches the MR for 5+ spot-checked rows.
- `reconcile.md` flags exactly the two known discrepancies under "Known", nothing under "New".
- Re-run is idempotent.
- **Review with user before proceeding to F3.**

### Phase F3 — Variance analysis

- **Task 9** — `core/reporting/variance.py`: per-statement variance DataFrame (actual / prior month / MoM / budget / vs plan / YTD / PY). **M.**
- **Task 10** — `scripts/build_report.py`: top-level CLI with `--extract-only`, `--variance-only`, `--commentary-only`, `--all` flags. Writes `variance.md` + `variance.csv`. **S.**

### Checkpoint F3 — Variance numbers exist and are auditable
- `python scripts/build_report.py farada 2026-03 --variance-only` produces `variance.{md,csv}`.
- Spot-checks against direct `core.query` calls reconcile within €1.
- Feb numbers regenerated from this pipeline match the published Feb PDF within €1.
- **Review with user before proceeding to F4.**

### Phase F4 — Commentary + checklist

- **Task 11** — `core/reporting/commentary.py`: structured Markdown outline mirroring the Feb PDF's 5 main sections (Page 2 highlights, Page 3 IS analysis, Page 5 CF analysis, Page 6 BS + KPIs; Page 4 IS charts is omitted since we don't render charts — its commentary is folded into Page 3). Key figures interpolated, material variances flagged. **M.**
- **Task 12** — `core/reporting/checklist.py` (or extension of commentary.py): one bullet per material variance with numbers + draft question, plus standing carry-over items from config. **S.**

### Checkpoint F4 — End-to-end pipeline complete
- `python scripts/build_report.py farada 2026-03` runs the full pipeline in one command.
- `reports/2026-03/` contains `reconcile.md`, `variance.md`, `variance.csv`, `commentary.md`, `checklist.md`.
- A reviewer can open `commentary.md` next to the Feb PDF and confirm structure mirrors it.
- Re-running the command is idempotent (same inputs → same outputs).
- **Final review with user. Sign-off on the FaradaIC pipeline.**

### Phase F5 — Deeper mapping (next iteration, parked)

The other MR sheets — `BWA`, `ControllingReport BWA`, `CR-Upload`, `Trial balance`, `Balance Sheet`, `Serbia`, `P&L Mapping` — carry the upstream consolidation, FX conversion, and DATEV-account → taxonomi-line mapping logic. The current pipeline trusts the consolidated P&L/CF/BS sheets; the next iteration will go deeper. Captured here so it's not lost:

- **Task 13 (next iteration)** — Document the role of each remaining sheet (`BWA` = German tax-format report; `ControllingReport BWA` = derived KPIs; `CR-Upload` = upload-formatted controlling export; `Trial balance` = GL trial balance with DATEV account numbers; `Balance Sheet` = a separate BS view; `Serbia` = pre-consolidation Serbia entity; `P&L Mapping` = DATEV account → P&L line mapping). Confirm each role with user.
- **Task 14 (next iteration)** — Wire `P&L Mapping` into the reconcile / commentary so a flagged variance can be drilled down to the underlying DATEV accounts.
- **Task 15 (next iteration)** — Optional: surface Serbia entity as a separate `entity='farada_rs'` for entity-level breakdown.

These tasks are **not** part of the F1–F4 critical path. They unlock once the basic monthly reporting pack is shipping.

## Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| The prompt's MR-to-taxonomi mapping table has gaps or errors. The user said "take with a grain of salt." | M | Task 5 is a sign-off step. Mapping is YAML, not code — fixing a row is a one-line edit. Reconcile (Task 8) surfaces mapping mismatches whenever it runs against prior months. |
| Two known prior-period discrepancies (COGS Jan; Other receivables Feb) — these will recur every month if not whitelisted. | M | Reconcile output groups deltas into "known" (whitelisted in `mapping.yaml.known_discrepancies`) vs "new". Only "new" deltas surface for review. Prevents alert fatigue. |
| MR row layout could shift between months (rows added, line items reordered by the accountant). | M | Task 6 reads MR by **label match first, row-index as fallback**, with a `logging.warning` when label and row disagree. User fixes the mapping when this fires. |
| ~~YoY comparison without 2025 actuals~~ | — | **Resolved:** YoY is out of scope per user. No 2025 source build, no PY columns in variance. |
| Variance % becomes noisy on small line items (taxonomi rounds to integers; budget has decimals). | L | Variance % computed against precise values; rounded values only used for display. Documented in `variance.md` header. |
| Commentary scaffolding produces generic text that the user has to heavily rewrite each month. | M | Task 11 deliberately produces an **outline** with key figures filled in, not full prose. The user / a follow-up LLM session writes the prose. Avoids over-promising on auto-drafting. |
| Saving the plan/todo to `tasks/farada/` rather than `tasks/{plan,todo}.md` may surprise the user. | L | Called out at the top of this document. The cupffee/almacena work is still active in the parent files; namespacing avoids collision. |

## Open questions

1. **Cadence**: confirm monthly. Each new month: drop new MR file in `raw/`, update `as_of_date` + `reporting.mr_source` in `config.yaml`, run `build_report.py`.
2. **Discrepancy whitelist**: confirm that "MR COGS Jan = 2,403 vs Taxonomi Jan = 52,403" and "MR BS Other receivables Feb = 83,072 vs Taxonomi Feb = 33,072" are the **only** two known good deviations, not symptoms of a systematic mapping error.
3. ~~**2025 actuals**~~ — **Resolved:** not in scope. No 2025 source build; YoY skipped entirely. Focus is March 2026 + MoM (vs Feb) + Budget (vs Realistic) + Q1 2026 YTD.
4. ~~**Mapping authority**~~ — **Resolved:** the prompt is the source. Sign-off happens at Task 5.
5. **Commentary scope**: is text-templated outline + interpolated figures + flagged discussion items enough for Phase F4, or does the user want full LLM-drafted prose right away? Default = outline only; LLM-drafting is a deliberate Phase-after-F4 enhancement.

## Verification (skill checklist)

- [x] Every task has acceptance criteria (in `todo.md`).
- [x] Every task has a verification step (in `todo.md`).
- [x] Task dependencies identified and ordered (graph above).
- [x] No task touches more than ~5 files.
- [x] Checkpoints exist between phases (F1–F4).
- [ ] Human has reviewed and approved the plan.
