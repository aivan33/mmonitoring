# Implementation Plan: Farada May 2026 MR — Programmatic Build

**Date:** 2026-06-28
**Deliverable:** `clients/farada/raw/mr_2026-05.xlsx` (the master accounting workbook the user updates monthly)
**Method chosen:** Programmatic populate (openpyxl fills the May column from raw sources; formulas left intact for Excel to recompute on open; reconciliation replicated in Python — no LibreOffice)

## Overview

The MR is a formula-heavy Excel workbook. Each month's job is to fill the **May
column** across all sheets from the raw German (DATEV) + Serbian accounting
files, then let the front statements recompute. We build it programmatically:
copy `mr_2026-04.xlsx` → `mr_2026-05.xlsx`, populate the May column on every
sheet, recalc, and gate on the consolidation reconciliation checks.

## How the workbook actually consolidates (verified against mr_04)

- **CF** front sheet auto-derives via `SUMIF('ControllingReport BWA'!…)` keyed on
  a mapping code → fill the ControllingReport BWA May column and CF recomputes.
- **P&L / BS** front sheets sum *within themselves* (`=SUM(C27:C33)`); their
  **leaf rows are hand-keyed** from the German BWA mapping + the **Serbia** sheet.
  Germany + Serbia merge *here* — there is no separate consolidation step.
- April's check failure (acct 49092 S&M dropped from a P&L leaf) lived in exactly
  this manual leaf-mapping step → it is the highest-risk part of the script and
  the reconciliation checks exist to catch it.

## Source → MR sheet mapping (to confirm in Task 2)

| Raw source (05) | MR sheet | Fills |
|---|---|---|
| `BWA - Jahresübersicht 05-2026.xlsx` | `BWA` | German P&L data, May col |
| `Controlling-BWA Jahresübersicht 05-2026.xlsx` | `ControllingReport BWA` + `CR-Upload` | German controlling/CF data → drives CF front |
| `Susa_Jahresübersicht 05-2026.xlsx` | `Trial balance` | German trial balance, May col |
| `BS 05-2026.xlsx` | `Balance Sheet` | German interim BS, May col |
| `FaradaIC Serbia …template…20260622.xlsx` | `Serbia` | Serbia monthly cost report, May col |
| `development fixed assets 05-2026.pdf` (**parse PDF — no xlsx**) | feeds CFI_RD / BS R&D | R&D capitalization |
| *(derived)* | `P&L` + `BS` front leaf rows | May col = German BWA mapping + Serbia |

## Architecture Decisions

- **Work on a copy, never the source.** mr_04 stays untouched; all writes land in
  mr_05. The fragile formatting/formulas are preserved by copying, not rebuilding.
- **Golden test before trusting May.** Reproduce April's *April column* from the
  April raw sources with the same extraction logic and diff against the delivered
  mr_04. If the script can't reproduce April, it can't be trusted for May.
- **Reconciliation is the gate, not "looks right".** P&L check, CF check, and
  BS-balances-to-zero must pass (or every break must be explained, as in April).
- **No recalc dependency (no LibreOffice).** The script writes *values* into the
  data + leaf cells and leaves every front-sheet formula untouched; Excel
  recomputes the front P&L/CF/BS automatically when the user opens mr_05. For our
  own gate we don't rely on Excel: we replicate the consolidation arithmetic in
  Python (P&L = Σ leaves, CF = SUMIF on ControllingReport BWA, BS = Σ) and run the
  reconciliation checks on those computed values — same approach as `validate.py`.
- **Inputs are parsed, not retyped.** Excel sources via openpyxl; the
  `development fixed assets` figure parsed from its PDF (no xlsx was delivered).

## Task List

### Phase 0: Safety & layout

#### Task 0: Standardize the raw layout and confirm tooling
**Description:** Move the May raw files into the established `raw/accounting/05-2026/`
structure (German files at root, Serbia files in a `Serbia/` subfolder) and fix the
mojibake filenames (`JahresÅbersicht` → `Jahresübersicht`). Confirm the PDF-parsing
dependency (e.g. `pdfplumber`) is importable for Task 3.
**Acceptance criteria:**
- [ ] German files under `raw/accounting/05-2026/`; Serbia files under `…/Serbia/`
- [ ] Filenames de-mojibaked; no `Å` artifacts
- [ ] A PDF table/text parser imports cleanly (else note install step)
**Verification:** `ls raw/accounting/05-2026/` matches the 04 file inventory shape; `python -c "import pdfplumber"` runs.
**Dependencies:** None
**Files touched:** raw file moves only (no code)
**Scope:** Small

### Phase 1: Extraction engine (validated on April)

#### Task 1: Map the May column index per sheet
**Description:** For each sheet in mr_04, locate the header cell for the May/2026
column and the row ranges for leaf accounts, so the writer targets the right cells.
**Acceptance criteria:**
- [ ] A per-sheet `{sheet: (may_col_index, data_row_range)}` map, derived not hard-coded
- [ ] May column confirmed empty in mr_04 for every sheet (we're filling, not overwriting)
**Verification:** Print the map; assert each May cell is currently blank.
**Dependencies:** Task 0
**Files touched:** `scripts/build_farada_mr.py`
**Scope:** Small

#### Task 2: German data-sheet extractor + April golden test
**Description:** Extract the German BWA / Controlling-BWA / SuSa / BS month columns
from the raw files into the `BWA`, `ControllingReport BWA`, `CR-Upload`,
`Trial balance`, `Balance Sheet` sheets. Validate by reproducing April's column
from April raw sources and diffing against delivered mr_04.
**Acceptance criteria:**
- [ ] Each German source maps to its target sheet by account/row key (not by position)
- [ ] April reproduction diff vs mr_04 is zero (or every delta explained)
**Verification:** `python scripts/build_farada_mr.py --golden 04` prints a zero/explained diff.
**Dependencies:** Task 1
**Files touched:** `scripts/build_farada_mr.py`
**Scope:** Medium

#### Task 3: Serbia extractor (+ R&D capitalization input)
**Description:** Extract the Serbia template's month column into the `Serbia` sheet;
parse the `development fixed assets 05-2026.pdf` to get the R&D capitalization
figure and wire it in. Serbia month-only bruto bilans is absent → derive
May = May-cumulative − April-cumulative.
**Acceptance criteria:**
- [ ] Serbia May column populated; reproduces April Serbia column in golden test
- [ ] R&D capitalization parsed from the PDF and reconciled (cross-check vs April's xlsx parse to prove the PDF parser is correct)
- [ ] Derived Serbia month-only figure logged
**Verification:** Golden test covers the Serbia sheet; PDF-parsed April capitalization matches April's dev-assets xlsx value.
**Dependencies:** Task 2
**Files touched:** `scripts/build_farada_mr.py`
**Scope:** Medium

### Checkpoint: Extraction proven on April
- [ ] `--golden 04` reproduces every data sheet + Serbia with zero/explained diff
- [ ] Review with user before running on May

### Phase 2: Consolidation leaf-mapping (highest risk)

#### Task 4: P&L + BS front leaf-row mapping
**Description:** Populate the May leaf rows of the `P&L` and `BS` front sheets from
the German BWA mapping + Serbia — the manual step that dropped acct 49092 in April.
Drive it off the `P&L Mapping` sheet / `Mapping` column so no account is silently
omitted. Validate against April.
**Acceptance criteria:**
- [ ] Every German + Serbia account routes to a P&L/BS leaf (none dropped); unmapped → flagged, not discarded
- [ ] April reproduction of P&L + BS front leaves matches mr_04
**Verification:** `--golden 04` extended to front leaves; unmapped-account report is empty or explained.
**Dependencies:** Task 3
**Files touched:** `scripts/build_farada_mr.py`
**Scope:** Medium

### Phase 3: Build May + reconcile

#### Task 5: Generate mr_2026-05.xlsx (values only, formulas intact)
**Description:** Run the full pipeline on May raw sources → write mr_2026-05.xlsx
from a copy of mr_04, filling May data + leaf cells. Leave every front-sheet
formula untouched so Excel recomputes on open. No LibreOffice.
**Acceptance criteria:**
- [ ] `mr_2026-05.xlsx` produced from a copy of mr_04 with May filled everywhere
- [ ] Front-sheet formulas preserved byte-for-byte (diff formula cells vs mr_04 → only references unchanged, no values hard-written over formulas)
- [ ] Structure diff vs mr_04 shows only May-column value changes (no lost sheets/formatting)
**Verification:** openpyxl reload asserts formula cells still hold `=…`; user opens in Excel and front P&L/CF/BS populate for May.
**Dependencies:** Task 4
**Files touched:** `scripts/build_farada_mr.py`, `clients/farada/raw/mr_2026-05.xlsx`
**Scope:** Small

#### Task 6: Reconciliation checks (the gate) — computed in Python
**Description:** Without relying on Excel recalc, replicate the consolidation
arithmetic in Python (P&L = Σ leaves, CF = SUMIF on ControllingReport BWA,
BS assets = liabilities+equity) and run the checks — surfacing every break with its
cause, mirroring April (dropped account vs intercompany lag vs group residual).
**Acceptance criteria:**
- [ ] P&L check, CF check, BS balance each pass OR have a written explanation
- [ ] No silently dropped source line (carried in "Other" or flagged)
- [ ] Same checks pass on the April golden reproduction (proves the check logic)
**Verification:** `python scripts/validate.py` (extend for May) prints a clean/explained check report for both April (golden) and May.
**Dependencies:** Task 5
**Files touched:** `scripts/validate.py`
**Scope:** Medium

### Checkpoint: Complete
- [ ] May MR built, recalced, all checks pass or are explained
- [ ] Golden April reproduction still green (no regression)
- [ ] Review with user before treating mr_05 as the deliverable

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Front P&L/BS leaf mapping drops an account (April's bug) | High | Mapping-driven routing + unmapped-account report; golden April test (Task 4) |
| openpyxl corrupts formatting/charts on save | Med | Work on a copy; diff mr_05 vs mr_04 structure post-write; keep mr_04 pristine |
| PDF parse of dev-assets returns wrong figure | Med | Cross-check the parser on April's PDF vs April's delivered xlsx (Task 3); fail loud on mismatch |
| Front formulas accidentally overwritten with values | Med | Task 5 asserts formula cells still hold `=…` after write |
| Serbia month-only bruto bilans missing | Low | Derive May = cumulative(May) − cumulative(Apr); note in build log |
| Mojibake filenames break globbing | Low | Rename in Task 0 |

## CURRENT STATUS (2026-06-29) — what's done vs missing

### Done & verified (committed)
- Raw layout standardized; `pdfplumber` added.
- **BWA** May paste (account-keyed, golden April = 0 mismatches).
- **Serbia** May paste (label-matched; restatements flagged, immaterial).
- **Front P&L** extended through **April + May** (formula extension, Translator).
- **New accounts wired** (BWA + P&L Mapping + Check):
  - 83380 → revenue 'Other' (May revenue 4,482).
  - 31004 €54,789 → **capitalised** like 31014 (out of opex, in the Check).
  - 49203 → G&A Office; 46680 → G&A Travel; 46502 → S&M (catch-all sub-line).
- **P&L is complete & reconciled through May.** 395 tests pass.

### Missing — remaining work to a full MR (dependency-ordered)

**Phase A — Cash Flow (biggest gap).** The CF chain is built only through March.
- A1. CR-Upload Apr+May: paste raw Controlling-BWA as a mechanical base, then
  apply the **manual CF reclassifications** (the ~7% of accounts: 15900, 14000,
  9800, …). Blocker = the reclassification rules live with the user. *(S + manual)*
- A2. Extend ControllingReport BWA VLOOKUP cols (Apr=8, May=9). *(XS)*
- A3. Extend front CF formulas (Apr=6, May=7) via Translator. *(XS)*
- A4. Verify CF Check / direct-method residual. *(S)*

**Phase B — Balance Sheet.** MAPPED (2026-06-29). The BS chain mirrors the P&L:

```
raw BS 05-2026.xlsx          ->  'Balance Sheet' data sheet  ->  front BS
(Kontennachweis zur Bilanz)      (account-level, TAGGED in        (SUMIF by tag,
 account | EUR | Gesch.jahr        col A, values PASTED;            summing the EUR +
 | Vorjahr)                        month = 3 cols EUR/FinYr/PY)     FinancialYear cols)
```
- Front BS line = `SUMIF('Balance Sheet'!$A,<tag>,EURcol) + SUMIF(...,FinYrcol)`.
  Month cols on the data sheet: Jan EUR=4,FinYr=5 (+3/month) → **May EUR=16, FinYr=17**.
  Front BS month cols: col3=Jan-2025 → **Mar=17, Apr=18, May=19**.
- The **col-A tag is the manual BS categorisation** (BS analogue of P&L Mapping's
  leaf): 14 tags — R&D, PP&E, Business equipment, Cash, Trade/Other receivables,
  Prepaid, Loans A, Inventory, Share capital, Retained earnings, Loan facility,
  Grants, Trade/Other payables, Payables to personnel, Loans L.
- Like everything else, the data sheet + front BS are built **through March only**.

  - B1. **RECONCILED to within €14,532** (from €57k off). Built: account-keyed
    paste + the manual subtotal rows (now blank-gap-aware, so the VAT block feeds
    Other receivables) + front BS extension to Apr/May. Fixes applied:
      - dedup of repeated raw rows (the "davon …" / zero-first-line trap) — loan
        `1705 1` (€185k), `740 0`, `1790 0` (€61k VAT) now populate
      - `Jahresfehlbetrag` (€90,564 net loss) → Retained earnings; `Saldenvorträge`
        (€3,490,248) already tagged → equity now reconciles **exactly**
      - added 1600 0 (Trade payables €134k), 1780 0, 490 0, 498 0 in the 150-168
        safe zone; re-tagged 1790 0 → Other payables
    - **Remaining €14,532 residual** = a few ambiguous transit/clearing accounts
      whose asset-vs-payable side is an accountant judgement: 1590 0 Durchlaufende
      Posten (€6,513), 1610 0 (€1,166), 1766 0 (€247), 1591 0 (€49) + minor VAT
      netting. The raw BS itself balances (€5,749,175), so it's purely a
      classification call on these pass-through accounts. *(XS, needs sign-off)*
  - B2. Extend front BS `SUMIF` formulas to Apr (col18) + May (col19) via
    Translator (shifts the month-column refs). *(XS)*
  - B3. **Serbia BS — DECISION NEEDED.** The front BS is **Germany-only**; it
    references no Serbia cell, yet the Serbia sheet carries a full BS section
    (rows 19–30: PP&E, Cash, receivables, equity, current liabilities). Either
    (a) keep Germany-only (current behaviour) or (b) consolidate Serbia in
    (add Serbia refs to the front BS rows + eliminate the intercompany
    investment/loans). *(S–M, gated on the decision)*
  - B4. Cross-check: dev-assets register (YTD additions €135,299, deprec €48,026)
    should reconcile to BS PP&E movement; capitalised 31004/31014 land in the R&D
    intangible. The raw BS already reflects these, so B1 captures them — this is a
    reconciliation check, not extra entry. *(S)*
  - B5. Verify front BS check row (Assets − Equity&Liab = 0) for Apr + May. *(XS)*

- Trial balance sheet (from Susa) is **not on the front-BS path** (front SUMIFs
  only 'Balance Sheet'); treat as reference unless a check needs it.

**Phase C — Cleanup / robustness.**
- C1. 37360 (Skonti −4.38) — decide treatment + make COGS-range room. *(XS)*
- C2. **Structural**: several P&L Mapping ranges (COGS 28–30, S&M Travel 52–64)
  have **no spare rows** — new accounts there need row-insertion + range-repair.
  Add buffer rows so future months don't hit this. *(M)*
- C3. Serbia prior-month restatements — decide whether to refresh Jan–Apr. *(XS)*
- C4. Run the full consolidation Check (P&L/CF/BS) for Apr + May → all ≈ 0. *(S)*

### Checkpoint before Phase A
- [ ] User reviews the May P&L in Excel (open → recompute).
- [ ] User provides CF reclassification rules (or confirms mechanical-only first pass).

## Resolved Decisions

- **No LibreOffice.** Write values, leave formulas for Excel to recompute on open;
  run our reconciliation gate via Python-replicated arithmetic (Task 6).
- **dev fixed assets:** parse the PDF (Task 3); validate the parser against April's
  xlsx, which we still have.

## Open Questions

- None blocking. Ready to start at Task 0.
