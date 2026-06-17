# Undelucram — MRR Schedule + Retention build (workstream B)

Status: **PLAN — awaiting approval before build.** Authored 2026-06-17.

## Overview
Automate the monthly **MRR Schedule** and **Retention Analysis** Excel files
from Costin's **Categorization** file, per `clients/unde/reference/Undelucram
reporting process.docx`. Deliverables are real `.xlsx` workbooks with formulas
extended one month (so Excel recalculates on open), built incrementally on the
prior month's workbook. This is workstream B — separate from the taxonomi
(workstream A, already automated).

## Confirmed scope (this effort)
- **In:** MRR Schedule (MRR-calc half) + Retention Analysis for **May 2026**.
- **Out (later, needs the May management report ~20th):** the IS/CF/BS half of
  the MRR Schedule, the Operating Cash Flows table, and the Reporting/Monitoring
  deck (stage 3, "the most important task").
- Recipient of the final pack: **Costin** (client = accountant; one party).

## Inputs
- `clients/unde/raw/Undelucram Categorization May 2026.xlsx` — cumulative invoice DB.
- `clients/unde/raw/04/MRR_Schedule_Undelucram April 2026.xlsx` — roll base.
- `clients/unde/raw/04/Retention_Analysis_Undelucram April 2026.xlsx` — roll base.
- FX (ECB monthly averages, fetched 2026-06-17): **May RON/EUR = 5.229615**,
  **May USD/EUR = 1.1673**. Convert: RON ÷ 5.2296, USD ÷ 1.1673, EUR as-is.

## Architecture decisions
1. **Extend the real workbook with formulas intact** (translate prior-column
   formulas) + **annotate** every manual/QC step. Excel recalcs on open.
2. **Reproduction gate** = the trust mechanism: rebuild **April** from the
   *March* schedule + *April* Categorization and match the real April workbook
   (structure + formulas; values after an Excel recalc). Only then trust May.
3. **Restatement** [docx ¶13,18]: last 2 months stay formulas, earlier months
   pasted as values; the figure from 2 months ago is restated. We roll forward
   and leave prior published columns as the base file has them.
4. **Headless limitation:** openpyxl cannot recalc. Final acceptance requires
   opening in Excel once and confirming **`4 Unique MRR Schedule` row 5 = 0**.

## Decoded architecture (Phase 2.1, 2026-06-17)
The MRR-calc half is a formula chain, NOT independent sheets:

```
1.1 Source Data  (append raw invoices; cols: FX-cur, amount, Client, Valoare,
                  Start, End=EDATE, Period=COUNTIF, Country, MRR, Monthly=D/G,
                  Produs, + legacy month spread $D/$G ending 2024-10)
   | per-row formula mirror, PRE-ALLOCATED to row 2563 (must extend for May)
1.2 Source Data  (Customer, Country[VLOOKUP], MRR, Service, Total=E, Period=F,
                  MRR=E/F, ARR=G*12, Start, End=EDATE(I,F)) — refs '1.1'!rowN
   | 3 MRR Data data-row N  ==  1.2 row (N-12)
3 MRR Data  (row13 hdr; rows14+ ref '1.2 Source Data'; Begin=DATE(start),
             End=Begin+period; month col = IF(AND(Begin<=monthStart,
             End>=monthEnd), MRR, 0) — forward run-out to latest End;
             header r6=monthStart r7=EOMONTH r8=EDATE-chain;
             totals r10 SUM, r11 SUMIF by MRR flag)
   |
4 Unique MRR Schedule  (+1 month col/drag-right; dedup to unique clients;
                        QC row5 = SUM(col) - '3 MRR Data'!totals  == 0)
2 Unique ID  (unique client names; refresh)
```

Engine steps to extend one month (May):
1. `1.1`: append N invoice rows (values + End/Period/Monthly formulas; the
   legacy month-spread block can stay as the existing pattern).
2. `1.2`: extend the mirror formulas past row 2563 to cover the new `1.1` rows.
3. `3 MRR Data`: add N rows mirroring `1.2`'s new rows; extend month columns to
   the new latest End (EOMONTH/EDATE/IF pattern); widen SUM/SUMIF total ranges.
4. `4 Unique MRR Schedule`: add the new month column AND **sync the unique-client
   list from `3 MRR Data`** — every distinct client (case-insensitive) in MRR
   Data must have a row, and the new month column's formula must be filled down
   EVERY populated row. This is the #1 source of QC drift.
5. `2 Unique ID`: add new commercial names.

QC GUARD (automated, no Excel recalc needed): reproduce row 5 in Python —
`Σ(Unique month col) − (3 MRR Data month MRR total)` must be 0, computed per
month AND per client so the build fails loudly naming offenders. Worked example
(May, manual draft): deviation −824.27 = UNICREDIT SERVICES 640.58 + CYCLON TECH
82.08 + MATECO 51.60 (no Unique row) + HUDSON EDGE 50.00 (Unique row 527, May
cell unfilled). All four are new May clients not propagated into the Unique list.
Row counts are CONSISTENT across all three sheets (count by non-empty key
column, NOT max_row which includes trailing pre-allocated formula rows). April
data-row count = 2522 (Mar) → 2554 (Apr) on 1.1 Client / 1.2 Customer / 3 MRR
Identifier alike. The earlier "+29 on 3 MRR Data" was a max_row artifact.
(Reconciling exact new-row count with the colleague: file shows 32 new rows
2524-2555; confirm vs their count of 31 — DB SCHENKER r2528 has a 2027 start.)

## Per-sheet roll mechanics (from the Mar→Apr diff)
| Sheet | Mechanic |
|---|---|
| `1.1 Source Data` | append new-month invoice rows (EUR-converted, spread formulas); month cols are legacy (end 2024-10), not extended |
| `1.2 Source Data` | static reference — no change |
| `2 Unique ID` | add rows for new commercial names (dedup; alias-aware) |
| `3 MRR Data` | append invoice rows + extend month columns (EDATE chain, forward run-out horizon — **+13 cols Mar→Apr, needs decoding**) |
| `4 Unique MRR Schedule` | add ONE month column (drag right); rows fixed (12–974); QC row 5 |
| Retention `MRR Retention`, `For Rev E Tab` | paste Unique MRR Schedule data (rows 65+), drag formulas right |

## Task breakdown

### Phase 1 — Decode + Categorization→Source-Data mapping
- **1.1** Fully decode `3 MRR Data` month-column behavior (why +13 cols; how the
  current-month MRR is read vs the forward forecast). *(M, read-only)*
- **1.2** Build the Categorization→Source-Data transform: detect the new month's
  invoices, EUR-convert (monthly FX), map `Management Report Category` →
  Country/Produs/MRR-flag/Period; handle USD + the stray `3036` date. *(M)*
- **Checkpoint A (gate part 1):** reproduce April's appended Source-Data rows
  from the April Categorization, row-for-row.

### Phase 2 — Extension engine
- **2.1** Append invoice rows to `1.1 Source Data` with correct spread formulas +
  styles. *(M)*
- **2.2** Extend `3 MRR Data` (rows + month cols) and `4 Unique MRR Schedule`
  (+1 col) by translating prior-column formulas; refresh `2 Unique ID`. *(L)*
- **2.3** Carry the QC row + write annotations (what to check in Excel). *(S)*
- **Checkpoint B (full gate):** rebuild April from March schedule + April
  Categorization; formula/structure match to the real April workbook; open in
  Excel → QC row 5 = 0; current-month MRR matches Reporting(1) (€105,400 basis).

### Phase 3 — Produce May + Retention
- **3.1** Run engine: April schedule + May Categorization → `MRR_Schedule_…May
  2026.xlsx`. *(S)*
- **3.2** Build Retention: paste Unique MRR Schedule → `MRR Retention` rows 65+ /
  `For Rev E Tab`, extend formulas → `Retention_Analysis_…May 2026.xlsx`. *(M)*
- **3.3** Handoff notes + update `clients/unde/onboarding.md` runbook. *(S)*
- **Checkpoint C:** May QC = 0 in Excel; Retention churn/expansion sane vs April.

## Risks
| Risk | Impact | Mitigation |
|---|---|---|
| `3 MRR Data` +13-col forward-horizon logic | High | Phase 1.1 decode before any write; gate on April |
| Formulas can't be verified headlessly | High | reproduction gate + mandatory Excel QC=0 step |
| Client aliases / Unique ID dedup [docx ¶6] | Med | match on commercial name; flag new/ambiguous aliases |
| USD invoices + bad `3036` date (docx only mentions RON) | Med | explicit USD FX; quarantine + flag bad rows |
| openpyxl drops charts/validation on save | Med | only the MRR-calc sheets are in scope; verify no chart loss |

## Phase 1 findings (2026-06-17)
Decode complete; **Checkpoint A PASSED** — `one_offs/test_source_data_repro.py`
reproduces all 32 of April's appended Source-Data rows from the Categorization
(transform in `one_offs/mrr_source_data.py`). What we learned:

- **Field mapping (verified):** Categorization `Income Invoices` →
  `currency, amount, Commercial→Client, Valoare=amount/FX, Start(col15),
  Period=Contract length(col11), Country(col9), Product(col10)→Produs,
  MRR(col14), Monthly=Valoare/Period`. Product labels normalize (e.g. Jobbing→
  Corporate Jobbing, LinkedIn→LinkedIn Learning).
- **FX anomaly (DECISION NEEDED):** April used a uniform **5.0735** for LEI→EUR.
  ECB has no such RON rate in Mar–May 2026 (range 5.09–5.26); it looks like a
  **stale carried FX cell**, contradicting the docx ("ECB monthly average").
  May's correct ECB average is **5.2296**. Need the colleague's true convention
  before producing May numbers.
- **Selection is MANUAL (not a clean rule):** "new invoices this month" is a
  human judgment + data clean-up, not a date filter. Evidence: PORSCHE's 2026
  invoices carry a corrupt invoice Date `3036-04-24` (a typo; their `Start` is
  correct) and were included; ASTREA was April-dated but *excluded* (renewal/
  dedup). → the engine must surface a candidate list for human confirmation,
  not auto-select silently.
- **Schema drift:** the Categorization column layout changes between monthly
  versions (April added a Commercial-name column; old rows use combined
  "RO - X", new rows split Country/Product) — so cross-file diffing is invalid.

## Open questions
- **FX convention for May** (5.2296 ECB vs replicate the colleague's stale-cell
  behavior) — blocks correct May figures.
- **Invoice selection** — confirm the colleague's actual rule for "new this
  month" (incl. how renewals like ASTREA and the `3036` date typo are handled),
  or accept a human-in-the-loop candidate list.
