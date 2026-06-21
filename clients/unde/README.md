# Undelucram

Monthly taxonomi build for the Undelucram (undelucram.ro) management reporting.

## What this produces
Each month, the **taxonomi-actual** workbook (`IS`, `CF`, `BS` by month) that gets
uploaded to the Platform — built automatically from the client's files instead of
re-typed by hand.

## Inputs → output
```
Management report (Undelucram - Monthly reports 2026.xlsx)  ──┐
   IS / BS / CF, already in EUR                                ├─►  taxonomi_act_<YYYY-MM>.xlsx
MRR Schedule (Reporting (1) → MRR headline)                 ──┘     (new month's column added)
```

- The **management report** supplies the income statement (revenue by market &
  service), balance sheet and cash flow.
- The **MRR schedule** supplies the single MRR headline figure (the MRR-classified
  revenue), which differs from total sales.

The build copies last month's taxonomi and fills in only the new month's column, so
formatting and prior months are preserved.

## How it's verified
A "reproduction gate" rebuilds a month that's already published and checks every
figure matches to within €1 before we trust the mapping. Differences that are
expected by design (e.g. MRR coming from the schedule) are documented and not
re-flagged each month.

## Not included here
The MRR Schedule calculation, Retention analysis, and the investor Monitoring deck
(PPT/PDF) remain a separate, manual workstream.

See `onboarding.md` for the runbook and `MR_LAYOUT.md` for the source-file map.
