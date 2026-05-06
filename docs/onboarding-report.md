# Onboarding a `report` client

Step-by-step for adding a new client whose deliverable is a monthly
reporting pack — a multi-document Markdown bundle covering reconcile,
variance, commentary, and discussion checklist. Farada is the worked
example.

The expected outcome: each month, one command (`build_report.py
<client> <YYYY-MM> --all`) produces every artefact, ready to hand to
the management meeting.

## Prerequisites

- The client provides a master accounting workbook each month (e.g.
  Farada's DATEV-derived MR file). Layout is bespoke per client.
- A prior-period taxonomi-actual file exists or can be authored from
  scratch — this is what the new month's column will be appended to.
- A prior-period deliverable (PDF or Markdown) showing the report's
  structure. The commentary scaffolding mirrors it.

If the client's source is already in canonical taxonomi format and
the deliverable is a slide deck rather than a Markdown pack, you're
onboarding a `charts` client instead — see
[`onboarding-charts.md`](onboarding-charts.md).

## Setup checklist (one-time)

### 1. Create the client tree

```
clients/<client>/
├── config.yaml
├── mapping.yaml          ← tracked
├── <SOURCE>_LAYOUT.md    ← tracked: documents the master workbook's shape
├── onboarding.md         ← tracked: this client's setup notes + monthly runbook
├── README.md             ← tracked: colleague-facing
├── raw/                  ← gitignored
├── data/                 ← gitignored
├── reference/            ← gitignored
└── reports/              ← gitignored
```

Drop the master workbook + the prior taxonomi-actual into `raw/`,
the prior-period deliverable into `reference/`.

### 2. Document the master workbook's shape

Write `clients/<client>/<SOURCE>_LAYOUT.md` (e.g.
`MR_LAYOUT.md` for Farada). Cover every sheet:

- Header row, label column(s), data row range, monthly column
  positions
- Section structure (which row range is which P&L/CF/BS section)
- Whether the sheet is **consumed** by the pipeline today, or
  **parked** for a future deeper-mapping iteration

This document is the contract between you and the accountant. When
the workbook layout changes, this is the file that gets updated
first.

### 3. Author the mapping

`clients/<client>/mapping.yaml` maps each row in the master workbook
to a `(statement, data, grp, subgroup)` key in the canonical
taxonomi.

```yaml
mapping_is:
  - { mr_row: 6, mr_label: "<exact label>", data: "Sales", grp: "<grp>", subgroup: "<subgroup>" }
  # ...

mapping_cf:
  - ...

mapping_bs:
  - ...

known_discrepancies:
  - period: <YYYY-MM>
    statement: IS
    taxonomi_key: ["<data>", "<grp>", "<subgroup>"]
    reason: |
      <explanation of why this prior-period delta is expected and shouldn't re-flag>
```

Conventions:

- `mr_row` is 1-indexed.
- `mr_label` is the exact label at that row, including trailing
  whitespace. The loader matches by label first, falling back to
  `mr_row` and warning if they disagree — catches accountant-side row
  reorders.
- `mr_row: null` means there's no source for that row (computed
  rows, derived KPIs, budget-only fields).
- A row can carry `sign: -1` if the master workbook stores the value
  with the opposite sign convention from the taxonomi.

See `clients/farada/mapping.yaml` for the full example.

### 4. Sign off on the mapping

**Sign-off step.** Walk the mapping with the accountant or finance
lead before locking. Ambiguities here become weeks of debugging
later. Confirm:

- Every row in the master workbook is either mapped or explicitly
  parked.
- Sign conventions match expectations.
- Known prior-period discrepancies are whitelisted with reasons.

### 5. Author `config.yaml`

```yaml
client_name: <Client>
fiscal_year_start_month: 1
currency: EUR
as_of_date: <YYYY-MM-DD>

use_cases: [report]

entities:
  - <client>

financial_sources:
  - { file: raw/<prior_taxonomi>.xlsx, year: <YYYY>, entity: <client>, currency: EUR }
  - { file: raw/<budget>.xlsx,         year: <YYYY>, entity: <client>, currency: EUR }

reporting:
  mr_source: raw/<master_workbook>.xlsx
  mapping: mapping.yaml
  reference_pdf: reference/<prior>.pdf
  carryover_topics:
    - <standing topic 1>
    - <standing topic 2>
  variance_thresholds:
    flag_pct: 20             # |variance %| > flag_pct → flag for discussion
    flag_eur: 10000          # OR |variance €| > flag_eur
    reconcile_eur: 5         # MR-vs-taxonomi delta > reconcile_eur → list in reconcile.md
```

### 6. Build the database

```bash
uv run python scripts/build_db.py <client>
uv run python scripts/validate.py <client>
```

Add 5–10 cell-level assertions to `scripts/validate.py` covering
representative actuals from the prior taxonomi. The DB build must
work cleanly and validate must exit 0 before continuing.

### 7. Smoke-test the extract phase

```bash
uv run python scripts/build_report.py <client> <YYYY-MM> --extract-only
```

This:
- Reads one month's column from the master workbook for IS/CF/BS
- Writes a new `raw/taxonomi_act_<YYYY-MM>.xlsx` (load-modify-save
  on the prior taxonomi, preserving formatting)
- Writes `reports/<YYYY-MM>/reconcile.md` flagging prior-month
  deltas between master workbook and taxonomi

Verify by hand:
- Open the new taxonomi-actual `.xlsx` and confirm the new month's
  column matches the master workbook for 5+ spot-checked rows.
- Open `reconcile.md` and confirm the only flagged deltas are
  whitelisted under "Known," nothing under "New."
- Re-run the command. The output must be byte-identical
  (idempotent).

### 8. Wire the rest of the pipeline (when F3/F4 ship)

`--variance-only` and `--commentary-only` are stubbed today. As they
land, smoke-test each phase against this client.

### 9. Write `onboarding.md` and `README.md`

`clients/<client>/onboarding.md` is engineer-facing — the setup
notes you wished you had, plus the monthly cadence runbook (next
section). It's specific to this client.

`clients/<client>/README.md` is colleague-facing — input → pipeline
→ output in plain business language, so reviewers can verify
correctness without reading code.

## Monthly cadence (recurring)

Once onboarded:

1. Drop the new master workbook into `raw/`.
2. Update `config.yaml`:
   - `as_of_date` → first-of-month for the new period
   - `reporting.mr_source` → new file path
   - `financial_sources` → add the about-to-be-generated taxonomi-actual
3. Run the extract phase:
   ```bash
   uv run python scripts/build_report.py <client> <YYYY-MM> --extract-only
   ```
4. Open `reports/<YYYY-MM>/reconcile.md`. Investigate every entry
   under "New" — if any of them are intentional accounting changes,
   add to `mapping.yaml`'s `known_discrepancies` for next month.
5. Rebuild the DB against the new taxonomi:
   ```bash
   uv run python scripts/build_db.py <client>
   ```
6. Run variance:
   ```bash
   uv run python scripts/build_report.py <client> <YYYY-MM> --variance-only
   ```
7. Run commentary:
   ```bash
   uv run python scripts/build_report.py <client> <YYYY-MM> --commentary-only
   ```
8. Or run all phases at once:
   ```bash
   uv run python scripts/build_report.py <client> <YYYY-MM> --all
   ```
9. Review `commentary.md` against the prior period's structure.
   Material variances are flagged automatically; carry-over topics
   from `config.yaml` are pre-populated. Edit/expand the prose as
   needed.
10. Hand the four artefacts (`reconcile.md`, `variance.md`,
    `commentary.md`, `checklist.md`) to the team.

## Failure modes

| Symptom | Likely cause |
|---|---|
| Loader warns "label-row mismatch" | Accountant reordered rows in the master workbook. Update `mapping.yaml`'s `mr_row` to match the new positions; `mr_label` keeps the loader honest. |
| Reconcile flags a "New" discrepancy you recognize | Either a real data-prep error (fix the source) or an intentional accounting change (whitelist in `known_discrepancies` with a reason). |
| Variance % is huge but `€` is small | Small denominator. Variance thresholds in `config.yaml` use AND-of-`flag_pct` OR `flag_eur` to suppress these. Tune thresholds if the report is too noisy/quiet. |
| Generated taxonomi-actual loses formatting | The bridge uses openpyxl load-modify-save; if formatting drifts, check that you're modifying the prior file, not writing a new file from scratch. |
