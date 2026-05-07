# FaradaIC — engineer onboarding & monthly runbook

Engineer-facing notes for working with FaradaIC's monthly reporting
pipeline. The colleague-facing overview is in [`README.md`](README.md);
the generic onboarding guide for any `report` client is in
[`docs/onboarding-report.md`](../../docs/onboarding-report.md).

## How this client is wired

| Aspect | Decision |
|---|---|
| Use case | `report` — Markdown reporting pack, no charts |
| Entities | Single `farada` (Germany + Serbia consolidated upstream in MR; BS is German-only — note it in commentary, don't model as a separate entity) |
| Currency | EUR everywhere; FX handled upstream of the MR |
| Master workbook | The DATEV-derived **MR** file. Layout: [`MR_LAYOUT.md`](MR_LAYOUT.md) |
| Mapping | [`mapping.yaml`](mapping.yaml) — sign-off completed 2026-04-30 |
| Variance thresholds | `flag_pct: 20`, `flag_eur: 10000`, `reconcile_eur: 5` (in `config.yaml`) |
| Carry-over topics | In `config.yaml.reporting.carryover_topics` — prune/extend as topics resolve |
| 2025 actuals | Not loaded — no source file exists yet. PY columns in variance reports are NaN. |

### Files the pipeline reads each month

- `raw/mr_<YYYY-MM>.xlsx` — set in `config.yaml.reporting.mr_source`
- `raw/taxonomi_act_<previous-YYYY-MM>.xlsx` — listed in `financial_sources`
- `raw/taxonomi_bp_2026.xlsx` — also in `financial_sources`

### Files in `raw/` the pipeline does **not** read (parked)

- `bookkeeping_<YYYY-MM>.xls` — raw bookkeeping export, available for
  manual inspection but not consumed
- `model_no_cap_<YYYY-MM>.xlsx` — internal projection model
- `taxonomi_bp_26nocap.xlsx` — budget without capitalization
  adjustments (sensitivity reference)

These exist because the user uploads the full bookkeeper bundle each
month; the pipeline picks out what it needs and ignores the rest.

## Initial setup (already done — kept as reference)

This was completed during the F1/F2 onboarding work. Documented here
so a future engineer can re-trace the steps if anything needs
re-doing or if the layout changes.

1. ✅ Created `clients/farada/{config.yaml, mapping.yaml,
   MR_LAYOUT.md}` and `raw/`, `data/`, `reference/`, `reports/` dirs.
2. ✅ Authored `MR_LAYOUT.md` — documents which of the MR's 10 sheets
   are consumed (P&L, CF, BS) and which are parked for the deeper-
   mapping iteration (BWA, ControllingReport BWA, CR-Upload, Trial
   balance, Balance Sheet, Serbia, P&L Mapping).
3. ✅ Authored `mapping.yaml` from the prompt's mapping table; verified
   row indices against the actual MR by inspection. Sign-off with
   user 2026-04-30.
4. ✅ Whitelisted two known prior-period MR-vs-taxonomi discrepancies
   under `known_discrepancies`:
   - 2026-01 IS COGS: MR €2,403 vs taxonomi €52,403 (intentional
     aggregation difference)
   - 2026-02 BS Other receivables: MR €83,072 vs taxonomi €33,072
     (€50K reclassification)
5. ✅ Added 8 cell-level validation assertions to `scripts/validate.py`
   covering IS/CF/BS Feb-2026 actuals.
6. ✅ Smoke-tested `build_report.py farada 2026-03 --extract-only` —
   produces a clean `taxonomi_act_2026-03.xlsx`, idempotent.

## Monthly runbook

Each month, when the bookkeeper sends the new MR file:

### 1. Drop the new files

Place into `raw/`:
- `mr_<YYYY-MM>.xlsx` — the new MR
- (optionally) `bookkeeping_<YYYY-MM>.xls`, `model_no_cap_<YYYY-MM>.xlsx`
  — these aren't consumed but the user uploads them as part of the bundle

### 2. Update `config.yaml`

```yaml
as_of_date: <YYYY-MM-01>      # → first-of-month for the new period

reporting:
  mr_source: raw/mr_<YYYY-MM>.xlsx    # → new file path

financial_sources:
  - { file: raw/taxonomi_act_<YYYY-(MM-1)>.xlsx, year: <YYYY>, entity: farada, currency: EUR }
  # ↑ swap to the previous month's taxonomi (extract phase will write the new month after this)
  - { file: raw/taxonomi_bp_2026.xlsx, year: 2026, entity: farada, currency: EUR }
```

### 3. Run the extract phase

```bash
uv run python scripts/build_report.py farada <YYYY-MM> --extract-only
```

Outputs:
- `raw/taxonomi_act_<YYYY-MM>.xlsx` — the new structured monthly file
- `reports/<YYYY-MM>/reconcile.md` — prior-month delta report

### 4. Review `reconcile.md`

- "Known" section: should match the two whitelisted discrepancies.
  No action needed.
- "New" section: should be empty.
  - If non-empty and the deltas are real bookkeeping errors → ask the
    bookkeeper to fix the MR, restart from step 1.
  - If non-empty but the deltas are intentional accounting changes →
    add to `mapping.yaml`'s `known_discrepancies` with a reason, then
    re-run the extract.

### 5. Spot-check the new taxonomi

Open `raw/taxonomi_act_<YYYY-MM>.xlsx`. Pick 5+ rows across IS / CF /
BS and confirm the new month's column matches the corresponding row
in the MR. If any disagree → check `mapping.yaml` (most likely an
mr_row drift after a bookkeeper-side row reorder).

If the loader logged a `label-row mismatch` warning, the MR rows
moved. Update `mapping.yaml`'s `mr_row` indices and re-run.

### 6. Append the new taxonomi to `financial_sources`

```yaml
financial_sources:
  - { file: raw/taxonomi_act_<YYYY-(MM-1)>.xlsx, ... }   # prior, kept
  - { file: raw/taxonomi_act_<YYYY-MM>.xlsx,     year: <YYYY>, entity: farada, currency: EUR }   # NEW
  - { file: raw/taxonomi_bp_2026.xlsx, ... }
```

Order matters — last loaded wins. Append the new taxonomi after the
prior one.

### 7. Rebuild the DB

```bash
uv run python scripts/build_db.py farada
uv run python scripts/validate.py farada
```

The validation assertions are still pinned to Feb-2026 — all 8 must
still pass even after appending new actuals.

### 8. Run variance & commentary *(once F3/F4 ship)*

```bash
uv run python scripts/build_report.py farada <YYYY-MM> --variance-only
uv run python scripts/build_report.py farada <YYYY-MM> --commentary-only
# or just:
uv run python scripts/build_report.py farada <YYYY-MM> --all
```

Variance and commentary phases currently raise `NotImplementedError`
with a clear message — they're tracked in the F3 + F4 plans.

### 9. Hand the artefacts to the team

`reports/<YYYY-MM>/{reconcile,variance,commentary,checklist}.md` are
the deliverables. The user adds prose to `commentary.md` (the pipeline
produces the outline + key figures, not the prose itself).

## Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `error: client 'farada' doesn't subscribe to use_case 'charts'` | Ran `build_charts.py` instead of `build_report.py` | Use `build_report.py`. FaradaIC is `report`-only. |
| `label-row mismatch` warning during extract | Bookkeeper reordered MR rows | Update `mr_row` in `mapping.yaml`; `mr_label` keeps the loader honest |
| Reconcile flags lots of "New" deltas | Bookkeeping changed in a prior period (e.g. a reclassification) | Whitelist intentional ones in `known_discrepancies`; ask bookkeeper to fix unintentional ones |
| Variance % is huge but € is small | Small denominator (e.g. variance against a near-zero budget) | Thresholds are AND-of-`flag_pct` OR `flag_eur` — small-€ variances should already suppress. If they don't, retune `variance_thresholds` in `config.yaml`. |
| New month's taxonomi column is all zeros | Wrong year passed to the loader, or the wrong MR file targeted | Check `as_of_date` and `reporting.mr_source` in `config.yaml` |
| `validate.py farada` fails after rebuild | The 8 pinned assertions are against Feb-2026 actuals which shouldn't change. If they do, an upstream source for Feb has been re-keyed. | Investigate; the assertions are deliberately rigid — failure means a real change. |
