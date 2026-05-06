# FaradaIC Onboarding — Task List

Companion to `plan.md`. Phases F1–F4 mirror the slices in the plan. F5 (deeper mapping) is parked for the next iteration. Tasks are sized for one focused session.

---

## Phase F1 — Onboard FaradaIC into the existing data layer

### Task 1: Reorganize `clients/farada/` into the standard layout

**Description:** Move the four source files into the conventional per-client layout (mirrors `clients/cupffee/`). Rename to canonical filenames so naming is consistent across clients. Original prompt and Feb PDF go under `reference/`.

**Acceptance criteria:**
- [ ] `clients/farada/raw/mr_2026-03.xlsx` — moved from `mr-fd-mar26.xlsx`.
- [ ] `clients/farada/raw/taxonomi_act_2026-02.xlsx` — moved from `taxonomi-fd-act-feb26.xlsx`.
- [ ] `clients/farada/raw/taxonomi_bp_2026.xlsx` — moved from `taxonomi-fd-bp-26v1.xlsx`.
- [ ] `clients/farada/reference/mm-fd-feb26.pdf` — moved from `mm-fd-feb26.pdf`.
- [ ] `clients/farada/reference/prompt-mm-mar26.md` — moved from `prompt-mm-mar26.md`.
- [ ] `clients/farada/data/` and `clients/farada/reports/` exist (empty). **No `charts/` subdir.**
- [ ] `.gitignore` covers `clients/*/raw/`, `clients/*/data/`, `clients/*/reports/` (add the last if missing).

**Verification:**
- [ ] `ls clients/farada/raw/` lists the three xlsx files with new names.
- [ ] `ls clients/farada/reference/` lists the PDF and the prompt.
- [ ] `git status` shows no surprise untracked artifacts.

**Dependencies:** None.

**Files:** filesystem reorg only.

**Scope:** XS.

---

### Task 2: Author `clients/farada/config.yaml`

**Description:** Create the FaradaIC config in the same shape as Cupffee/Almacena, plus a new `reporting:` block. Single entity = `farada`. EUR throughout. **No `brand:` block** (no charts).

**Acceptance criteria:**
- [ ] `client_name: FaradaIC`, `currency: EUR`, `as_of_date: 2026-03-01`, `entities: [farada]`.
- [ ] `financial_sources` lists the Feb taxonomi-actual + the realistic-scenario budget. (We'll generate `taxonomi_act_2026-03.xlsx` in Phase F2; for now point at Feb only.) Last loaded wins for overlapping cells.
- [ ] `reporting:` block with `mr_source`, `mapping`, `reference_pdf`, `carryover_topics` (the four topics from the prompt), `variance_thresholds` (`flag_pct: 20`, `flag_eur: 10000`, `reconcile_eur: 5`).
- [ ] No `brand:` block — charts are not part of FaradaIC's pipeline.

**Verification:**
- [ ] `python -c "import yaml; print(yaml.safe_load(open('clients/farada/config.yaml')))"` parses without error.
- [ ] All file paths under `financial_sources` and `reporting.*` resolve to existing files.

**Dependencies:** Task 1.

**Files:** `clients/farada/config.yaml`.

**Scope:** XS.

---

### Task 3: Build & validate the FaradaIC DB against known cells

**Description:** Run `build_db.py farada` against the Feb taxonomi + 2026 budget. Pick 5–8 reference cells (cherry-picked from the Feb PDF + the taxonomi-actual file) and add to `scripts/validate.py` as FaradaIC assertions.

**Acceptance criteria:**
- [ ] `python scripts/build_db.py farada` exits 0 and prints row counts.
- [ ] `clients/farada/data/farada.db` exists.
- [ ] `scripts/validate.py` has a FaradaIC assertion list with 5–8 entries spanning IS / BS / CF Indirect, both `actual` (Jan/Feb) and `realistic` (Mar–Dec).
- [ ] Each chosen cell value matches the underlying xlsx within €1.

**Verification:**
- [ ] `python scripts/validate.py farada` exits 0.
- [ ] `python -c "from core.query import get_statement; print(get_statement('IS', '2026-02-01', client='farada', entity='farada').head())"` prints expected line items.

**Dependencies:** Task 2.

**Files:** `scripts/validate.py` (extension only).

**Scope:** S.

---

## Checkpoint F1 — Existing pipeline carries FaradaIC
- [ ] `build_db.py farada` clean.
- [ ] `validate.py farada` exits 0.
- [ ] Spot-query returns expected IS for Feb 2026.
- [ ] **Review with user before proceeding to F2.**

---

## Phase F2 — MR-to-Taxonomi bridge

### Task 4: Document all 10 MR sheets in `MR_LAYOUT.md`

**Description:** Open the MR workbook. For each of the 10 sheets, record name, shape (rows × cols), header row index, label column, monthly column layout, and **role**: either `consumed` (the loader reads it directly — `P&L`, `CF`, `BS`) or `parked` (carries upstream consolidation / FX / DATEV-mapping logic — handled in Phase F5 next iteration). Verify the prompt's claimed column indices (P&L Mar 2026 = col 15, CF Mar 2026 = col 4, BS Mar 2026 = col 16) against the actual file. Write `clients/farada/MR_LAYOUT.md`.

**Acceptance criteria:**
- [ ] All 10 sheets listed: `P&L`, `CF`, `BS`, `BWA`, `ControllingReport BWA`, `CR-Upload`, `Trial balance`, `Balance Sheet`, `Serbia`, `P&L Mapping`.
- [ ] Each sheet has a one-line description of role and a `consumed`/`parked` tag.
- [ ] `consumed` sheets (`P&L`, `CF`, `BS`) have full row/col layout details: header row, label column, first data row, last data row, monthly columns for 2025 and 2026, datatype (decimal vs integer).
- [ ] `parked` sheets each have a one-line note on why they're relevant (e.g., `P&L Mapping` = DATEV account → taxonomi-line mapping → drives Phase F5 deeper-mapping work).
- [ ] Prompt's claimed column indices verified by inspection — discrepancies (if any) are flagged.

**Verification:**
- [ ] Open the MR file, sample 3 cells from `P&L` Mar 2026 column; values match what `MR_LAYOUT.md`'s coordinates predict.
- [ ] Same for `CF` and `BS`.

**Dependencies:** Task 1.

**Files:** `clients/farada/MR_LAYOUT.md`.

**Scope:** S.

---

### Task 5: Author `mapping.yaml` (with user sign-off)

**Description:** Translate the prompt's mapping table into structured YAML. Each row carries: MR sheet, MR row index, MR label (for label-vs-row-index fallback), taxonomi `data` / `grp` / `subgroup`. Include `known_discrepancies:` block for the two prompt-flagged items (COGS Jan, Other receivables Feb). **Pause for user sign-off before locking in.**

**Acceptance criteria:**
- [ ] `mr_pnl_to_taxonomi_is` covers all 56 rows of `IS (Actual)` (subtotal/header rows have explicit `null` mappings, not omitted).
- [ ] `mr_cf_to_taxonomi` covers all 22 rows of `CF Indirect (Actual)`.
- [ ] `mr_bs_to_taxonomi` covers all 21 rows of `BS (Actual)`.
- [ ] Each entry includes `mr_label` for fallback verification.
- [ ] `known_discrepancies:` lists the COGS-Jan and Other-receivables-Feb cases with reason text.
- [ ] **User has reviewed and signed off** on the YAML before this task is marked done. Sign-off recorded in commit message.

**Verification:**
- [ ] `python -c "import yaml; m = yaml.safe_load(open('clients/farada/mapping.yaml'))"` parses; spot-check 3 mapped rows against the prompt mapping table.
- [ ] User has confirmed in writing.

**Dependencies:** Task 4.

**Files:** `clients/farada/mapping.yaml`.

**Scope:** M.

---

### Task 6: `core/loaders/mr.py` — extract one month per statement

**Description:** Function `extract_month(mr_path, mapping_yaml, year, month, statement) -> dict[(data, grp, subgroup), float]`. Reads the appropriate sheet, picks the column for `(year, month)`, applies the mapping, returns the dict. **Label-match first, MR-row-index as fallback** (warn when they disagree).

**Acceptance criteria:**
- [ ] Signature: `extract_month(mr_path: Path, mapping: dict, year: int, month: int, statement: str) -> dict[tuple[str, str, str], float | None]`.
- [ ] `statement` ∈ `{'IS', 'CF', 'BS'}`. Raises `ValueError` otherwise.
- [ ] Returns float values (no rounding here — Task 7 rounds for the xlsx output).
- [ ] Label-fallback: for each mapping entry, read the label at the configured row; if it doesn't match `mr_label`, search the sheet for `mr_label` and use that row instead. Emit a `logging.warning` with both row indices.
- [ ] Idempotent: same inputs → identical output dict.

**Verification:**
- [ ] `extract_month('clients/farada/raw/mr_2026-03.xlsx', mapping, 2026, 3, 'IS')` returns a dict whose values, summed for Sales subgroups, match the MR `P&L` row 4 (Sales total) for Mar 2026 — within €1.
- [ ] Same total-vs-sum check for CF (Beginning Cash + sum of activities = Ending Cash) and BS (Total Assets = Total Equity + Total Liabilities).
- [ ] 3 unit tests covering: (a) happy path, (b) label-mismatch fallback, (c) unknown statement raises.

**Dependencies:** Task 5.

**Files:** `core/loaders/mr.py`, `tests/test_mr_loader.py`.

**Scope:** M.

---

### Task 7: `core/mr_to_taxonomi.py` — populate the new month into a copied taxonomi xlsx

**Description:** Read the previous month's `taxonomi_act_<YYYY-MM>.xlsx`, **load and modify in place** (preserves cell styles, column widths, sheet order, formula links — anything the source file carries), overwrite the new month's column with the values from `extract_month`, save as `taxonomi_act_<YYYY-MM>.xlsx` for the new month. Round to integers (matches Jan/Feb convention). Sheets handled: `IS (Actual)`, `CF Indirect (Actual)`, `BS (Actual)`. The empty `CF (Actual)` sheet is left untouched.

**Acceptance criteria:**
- [ ] Signature: `populate_taxonomi(prev_taxonomi: Path, mr_extracts: dict[str, dict], year: int, month: int, out_path: Path) -> None`.
- [ ] Out file has the same sheet structure and **the same cell formatting** as the input. Verified by opening both files side-by-side.
- [ ] Previous months' columns are byte-equivalent to the input (no value drift).
- [ ] New month's column is populated for every taxonomi row that has a non-null mapping; rows without a mapping stay null (matching the existing convention for empty cells).
- [ ] Integer rounding: `round(value)` matches the convention of Jan/Feb cells.
- [ ] If a taxonomi row has no corresponding MR mapping (e.g., row was added in the taxonomi but not yet mapped in the MR), the new month's cell is left as `None` and a `logging.warning` is emitted listing the unmapped row.
- [ ] Idempotent: re-running with the same inputs produces a file with identical content (compare cell-by-cell, ignoring openpyxl metadata).

**Verification:**
- [ ] Open the generated `taxonomi_act_2026-03.xlsx`, navigate to `IS (Actual)`, column "Mar"; spot-check 5 cells against the MR `P&L` Mar 2026 column directly. Each matches within €1 after rounding.
- [ ] Diff Jan/Feb columns against the prior month's file → no changes.
- [ ] Re-run twice → cell-by-cell content identical.
- [ ] Open in Excel: column widths, header styling, row heights match the prior month's file.

**Dependencies:** Task 6.

**Files:** `core/mr_to_taxonomi.py`, `tests/test_mr_to_taxonomi.py`.

**Scope:** M.

---

### Task 8: `core/reporting/reconcile.py` — prior-month deviation report

**Description:** Compare prior months (Jan, Feb) between MR and the existing taxonomi-actual. For each line item, compute the absolute delta. Group results by `known_discrepancies` (whitelisted in `mapping.yaml`) vs new. Threshold from `config.reporting.variance_thresholds.reconcile_eur`. Write Markdown to `reports/<YYYY-MM>/reconcile.md`.

**Acceptance criteria:**
- [ ] Signature: `reconcile(mr_path, taxonomi_path, mapping, prior_months: list[date], threshold_eur: float = 5.0) -> ReconcileReport`.
- [ ] Output Markdown has three sections:
  - **Match summary** — counts (matched / known-discrepancy / new-deviation).
  - **Known discrepancies** — collapsed list with the reason text from `mapping.yaml`.
  - **New deviations** — table: `Statement | Line item | Period | Taxonomi | MR | Δ`. Empty section says "None — all line items match within €X."
- [ ] Threshold is configurable via function arg (default = `config.reporting.variance_thresholds.reconcile_eur`).
- [ ] Idempotent.

**Verification:**
- [ ] Running against the actual Feb taxonomi + Mar MR surfaces exactly the two prompt-known discrepancies (COGS Jan, Other receivables Feb) under "Known", and **nothing** under "New".
- [ ] If the user introduces a synthetic perturbation (e.g., changes one taxonomi cell by €100), reconcile flags it under "New".

**Dependencies:** Tasks 6, 7.

**Files:** `core/reporting/reconcile.py`, `tests/test_reconcile.py`.

**Scope:** S.

---

## Checkpoint F2 — Bridge produces a clean monthly taxonomi
- [ ] `python scripts/build_report.py farada 2026-03 --extract-only` writes `raw/taxonomi_act_2026-03.xlsx` and `reports/2026-03/reconcile.md`.
- [ ] Manual eyeball: March column matches the MR for 5+ spot-checked rows.
- [ ] `reconcile.md` flags the two known discrepancies, no false positives.
- [ ] Re-run is idempotent.
- [ ] **Review with user before proceeding to F3.**

---

## Phase F3 — Variance analysis

### Task 9: `core/reporting/variance.py` — variance computation

**Description:** Given `(client, entity, statement, period, scenario_actual='actual', scenario_budget='realistic')`, return a Pandas DataFrame with one row per `(data, grp, subgroup)` and columns: `actual`, `prior_month`, `mom_eur`, `mom_pct`, `budget`, `vs_plan_eur`, `vs_plan_pct`, `ytd_actual`, `ytd_budget`, `ytd_vs_plan_pct`. **No YoY columns** — out of scope per user. Pure function over the existing `core.query` helpers — no direct DB access.

**Acceptance criteria:**
- [ ] Signature: `variance(statement, period, *, client, entity, scenario_actual='actual', scenario_budget='realistic') -> pd.DataFrame`.
- [ ] Uses `core.query.get_statement` / `get_aggregation` / `ytd` only.
- [ ] Divide-by-zero handling: when budget = 0, `vs_plan_pct = NaN` (not Inf).
- [ ] No `py` / `vs_py_pct` columns. YoY explicitly out of scope.
- [ ] Idempotent.

**Verification:**
- [ ] `variance('IS', date(2026,3,1), client='farada', entity='farada')` returns a DataFrame with the expected columns and ≥ 25 rows (matches IS taxonomi rows that have non-null cells).
- [ ] Sales row's `actual` matches `get_aggregation('Sales', '2026-03-01', client='farada')` directly.
- [ ] YTD Sales = Jan + Feb + Mar values from the DB, cross-checked with `query.ytd('Sales', 2026)`.
- [ ] 3 unit tests covering: happy path, divide-by-zero (budget=0 → NaN), missing budget row.

**Dependencies:** Task 7 (taxonomi-act-mar must exist for end-to-end test).

**Files:** `core/reporting/variance.py`, `tests/test_variance.py`.

**Scope:** M.

---

### Task 10: `scripts/build_report.py` — top-level orchestrator

**Description:** Single CLI entry point that runs the monthly pipeline. Sub-flags allow partial runs.

**Acceptance criteria:**
- [ ] Usage: `python scripts/build_report.py <client> <YYYY-MM> [--extract-only|--variance-only|--commentary-only|--all]`. Default = `--all`.
- [ ] `--extract-only`: MR → taxonomi-actual + reconcile.md.
- [ ] `--variance-only`: rebuild DB (calls `build_db.py` internally or imports its `main`) → variance.md + variance.csv.
- [ ] `--commentary-only`: assumes variance has run; writes commentary.md + checklist.md.
- [ ] `--all`: extract → rebuild-DB → variance → commentary, in order. Stops on first error with a clear message naming the failing phase.
- [ ] All outputs land under `clients/<client>/reports/<YYYY-MM>/`.
- [ ] Re-run is idempotent.

**Verification:**
- [ ] `python scripts/build_report.py farada 2026-03 --variance-only` produces `reports/2026-03/variance.{md,csv}` (assuming F2 has been run).
- [ ] `variance.csv` opens cleanly in Excel.
- [ ] `python scripts/build_report.py farada 2026-03 --all` runs end-to-end without manual intervention.
- [ ] Smoke test in `tests/test_build_report.py` covers `--extract-only` and `--all` paths.

**Dependencies:** Tasks 8, 9.

**Files:** `scripts/build_report.py`, `tests/test_build_report.py`.

**Scope:** S.

---

## Checkpoint F3 — Variance numbers exist and are auditable
- [ ] `python scripts/build_report.py farada 2026-03 --variance-only` produces `variance.{md,csv}`.
- [ ] Spot-checks against direct `core.query` calls reconcile within €1.
- [ ] Feb numbers regenerated from this pipeline match the published Feb PDF within €1.
- [ ] **Review with user before proceeding to F4.**

---

## Phase F4 — Commentary + checklist

### Task 11: `core/reporting/commentary.py` — structured Markdown outline

**Description:** Walk the variance DataFrame, emit `reports/<YYYY-MM>/commentary.md` mirroring the Feb PDF's main sections: **Page 2 highlights & recommendations**, **Page 3 IS analysis** (folds in Page 4 chart-commentary since we don't render charts), **Page 5 CF analysis**, **Page 6 BS + KPIs**. Each section gets: a heading, key MTD/YTD figures interpolated and bolded, bullet placeholders for the user to fill in prose, flagged discussion items per `config.reporting.variance_thresholds`.

**Acceptance criteria:**
- [ ] Output Markdown has 4 main sections matching the Feb PDF (Page 2 / Page 3+4 / Page 5 / Page 6).
- [ ] Page 2 KPI table populated with: Sales, Direct Costs, OPEX (R&D + S&M + G&A), EBITDA, Net Profit, Cash Reserves, Net Cash Burn, Gross Cash Burn, Runway. Columns: MTD Actual, vs Prior Period, vs Plan, YTD Actual, vs PY, YTD vs Plan.
- [ ] Material variances flagged with `**[discuss]**` tag and the numbers (actual / budget / variance %). Threshold: `flag_pct` OR `flag_eur` from config.
- [ ] Carry-over topics from `config.reporting.carryover_topics` listed under "Discussion points" at the end of Page 2.
- [ ] Bold formatting on every key figure; underline (`<u>...</u>` or `__...__`) on items needing discussion (matches Feb PDF convention).
- [ ] Idempotent: same inputs → identical Markdown.

**Verification:**
- [ ] `python scripts/build_report.py farada 2026-03 --commentary-only` produces `reports/2026-03/commentary.md`.
- [ ] Open it next to the Feb PDF: 4 sections present, KPI table populated, bold/underline conventions match.
- [ ] Manual: every figure in the KPI table cross-checks against `variance.csv` for the same line item.

**Dependencies:** Tasks 9, 10.

**Files:** `core/reporting/commentary.py`, `tests/test_commentary.py`.

**Scope:** M.

---

### Task 12: `reports/<YYYY-MM>/checklist.md` — line-by-line review prompts

**Description:** For every line item flagged as material variance (per Task 11 thresholds), emit a checklist bullet with the numbers and a draft question. Organize by section (Revenue, Direct Costs, R&D, S&M, G&A, D&A, CF, BS). Append carry-over topics as "Standing items".

**Acceptance criteria:**
- [ ] One bullet per material variance, organized by section.
- [ ] Each bullet includes: line item, MTD actual, budget, MoM Δ, YTD actual, YTD budget, draft question (template-driven, e.g., "What drove the €X / Y% variance vs plan? Was this expected from the timing of <invoice/event>?").
- [ ] Standing items section lists `config.reporting.carryover_topics` verbatim.
- [ ] Idempotent.

**Verification:**
- [ ] `reports/2026-03/checklist.md` is a structured agenda: sections, bullets with numbers, draft questions — not a wall of text.
- [ ] Every bullet's numbers cross-check against `variance.csv`.

**Dependencies:** Task 11.

**Files:** `core/reporting/checklist.py` (or extension of `commentary.py`), `tests/test_checklist.py`.

**Scope:** S.

---

## Checkpoint F4 — End-to-end pipeline complete
- [ ] `python scripts/build_report.py farada 2026-03` runs the full pipeline in one command.
- [ ] `reports/2026-03/` contains: `reconcile.md`, `variance.md`, `variance.csv`, `commentary.md`, `checklist.md`.
- [ ] `raw/taxonomi_act_2026-03.xlsx` exists and matches MR for spot-checks.
- [ ] Re-running is idempotent.
- [ ] **Final review with user. Sign-off on the FaradaIC pipeline.**

---

## Phase F5 — Deeper mapping (next iteration, parked)

The other MR sheets — `BWA`, `ControllingReport BWA`, `CR-Upload`, `Trial balance`, `Balance Sheet`, `Serbia`, `P&L Mapping` — carry the upstream consolidation, FX conversion, and DATEV-account-to-taxonomi-line mapping logic. The current pipeline trusts the consolidated P&L/CF/BS sheets. Deeper mapping work below is captured here so it isn't lost; it is **not** part of the F1–F4 critical path and unlocks once F4 is shipping.

### Task 13 (next iteration): Document each parked sheet's role

**Description:** Confirm with the user the role of each remaining sheet:
- `BWA` — German tax-format report (Betriebswirtschaftliche Auswertung).
- `ControllingReport BWA` — derived KPIs view of BWA.
- `CR-Upload` — upload-formatted controlling export.
- `Trial balance` — GL trial balance with DATEV account numbers.
- `Balance Sheet` — alternate BS view (consolidated? German-only? confirm).
- `Serbia` — pre-consolidation Serbia entity data.
- `P&L Mapping` — DATEV account → P&L line mapping (the link between trial balance and consolidated P&L).

Update `MR_LAYOUT.md` with confirmed roles.

**Scope:** S.

---

### Task 14 (next iteration): Wire `P&L Mapping` into reconcile / commentary

**Description:** When the reconcile or variance reports flag a deviation in a P&L line, surface the underlying DATEV account contributions from the `P&L Mapping` sheet. Lets the user drill from "G&A Accounting variance vs plan" down to "DATEV account 6815 = €X this month".

**Scope:** M.

---

### Task 15 (next iteration): Surface Serbia entity (optional)

**Description:** If the user wants entity-level breakdown, treat the `Serbia` sheet as a separate `entity='farada_rs'` source and add a corresponding mapping. Schema already supports it; this is config + mapping authoring work.

**Scope:** M.

---

## Cumulative verification (skill checklist)

- [x] Every task has acceptance criteria.
- [x] Every task has a verification step.
- [x] Task dependencies identified and ordered.
- [x] No task touches more than ~5 files.
- [x] Checkpoints exist between phases (F1–F4).
- [x] Future work (F5) parked in this file, not referenced to other docs.
- [ ] Human has reviewed and approved the plan.
