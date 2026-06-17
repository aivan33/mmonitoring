---
name: legacy-reporting
description: >-
  Navigate a client's LEGACY monthly-reporting folders — the hand-built Excel
  pack (Categorization → MRR Schedule → Retention → Monitoring) plus the
  accountant's management report — left as-is for reference. Use when reading,
  cross-referencing, or reconciling figures in clients/<client>/raw/<MM>/, when
  a number in one file doesn't match another, or when validating a new
  programmatic build against the legacy source of truth. Per-client file maps and
  known inconsistencies live in references/<client>.md.
---

# Navigating legacy reporting folders

These folders are the colleague's **hand-built** monthly pack, kept as the
reference the new pipeline is validated against. They are formula-heavy,
restate prior months, and contain small known inconsistencies. Read them
carefully — do not assume internal consistency.

## Folder shape

`clients/<client>/raw/<MM>/` holds one month's pack (gitignored). Typical files:

| File | Who builds it | Role |
|---|---|---|
| `… Categorization <Month>.xlsx` | client (Costin) | raw revenue-invoice DB (cumulative); INPUT |
| `MRR_Schedule_… <Month>.xlsx` | analyst | MRR calc + Reporting/Monitoring tabs |
| `Retention_Analysis_… <Month>.xlsx` | analyst | New/Expansion/Contraction/Churn (pasted from the MRR schedule) |
| `… Monthly reports 2026.xlsx` | **accountant** | the management report (IS/BS/CF), produced AFTER the analyst sends the Monitoring |
| `Churned clients <Month>.xlsx` | analyst | churn detail |

Data lineage (one direction):
```
Categorization ─► MRR Schedule (Source→MRR Data→Unique) ─► Retention ─► Monitoring
                                                                            │ sent to accountant
                                                                            ▼
                                                              Management report (IS/BS/CF)
                                                                            │
                                                                            ▼
                                                              Taxonomi (the new pipeline)
```

## Reading rules (hard-won)

1. **openpyxl reads CACHED values.** These files are formula-driven; `data_only=True`
   returns the value Excel last saved. If the colleague is editing live, the
   on-disk cache will NOT match their screen. Always check the file's mtime and,
   when a number is disputed, recompute it yourself from the raw cells rather
   than trusting a cached total. Confirm which version you're holding before
   pointing at a cell.
2. **Column layout DRIFTS between monthly versions** (a column gets inserted, a
   field gets split/combined). Never address columns by fixed index — locate them
   by header label. Same for rows: count by a non-empty key column, never by
   `max_row` (which includes trailing pre-allocated formula rows).
3. **Prior months are RESTATED, not frozen.** The same month's figure differs
   between the `<MM>` and `<MM+1>` versions (the colleague "pastes as values" and
   revises 2-months-ago). When comparing months, always say *which file version*.
4. **The MRR headline ≠ total sales.** The MRR Schedule's MRR is the
   MRR-classified revenue; the management report's "MRR" row is usually total
   Sales. Don't equate them.
5. **Cross-statement ties are approximate.** Expect small residuals (cumulative
   IS profit vs BS profit; CF/bank cash vs BS cash). Treat a persistent,
   same-sign gap as a structural reconciling item, not noise — but verify the
   magnitude before asserting a cause (monthly-vs-cumulative, FX, an extra
   account).

## How to reconcile (the cross-checks that matter)

- **QC row 5 in `4 Unique MRR Schedule`** = `Σ(Unique month) − '3 MRR Data' month MRR total`; must be 0. A non-zero is almost always a new client missing from the Unique list, an unfilled month cell, or a **mixed MRR/Non-MRR client** (the Unique `SUMIFS` matches by client NAME only, so it pulls Non-MRR rows for any client flagged MRR). Reproduce it per-client in code to name the culprit.
- **Retention EoP** per month should equal the MRR Schedule's Reporting MRR series.
- **Management report**: BS Total Assets = Total Equity & Liabilities (ties); CF Ending Cash = "Bank statement balances"; IS cumulative profit ≈ BS "Profit for the period".

## Signalling inconsistencies

When you find one: state the **two figures, the months, the file versions, and
the magnitude**, classify it (restatement / structural reconciling gap / model
bug / data-entry error), and verify before naming a cause. Record it in
`references/<client>.md` so it isn't re-discovered each month. Do not "fix" the
legacy files — they are reference; corrections belong in the new pipeline.

See `references/undelucram.md` for the worked file map + the catalogued
inconsistencies.
