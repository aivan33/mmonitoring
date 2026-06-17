# Undelucram "Reporting sheet" (Monitoring) — transcript, commentary & process-overhaul proposal

Scope: the docx step **"Preparing the Reporting sheet (THE MOST IMPORTANT TASK)"**
(¶11–18 of `clients/unde/reference/Undelucram reporting process.docx`). This is
the front end of the Monitoring deck — the investor-facing tables/charts built on
top of the MRR Schedule + Retention. Grounded in the real tabs `Reporting (1)/(2)/(3)`
of `MRR_Schedule_Undelucram <month> 2026.xlsx`. Companion to the MRR-schedule build
spec (`2026-06-17-unde-mrr-schedule-build.md`).

Format mirrors the Farada ad-hoc consolidation write-up: **verbatim transcript →
per-step commentary → overhaul proposal.**

---

## 1. Transcript + commentary

> **¶11 — "Preparing the Reporting sheet (THE MOST IMPORTANT TASK):"**

The most business-critical step is also the most manual and the most error-prone —
i.e. the highest automation ROI and the highest current risk. Everything below is
hand-done in Excel each month.

> **¶12 —** *"All tables and charts must be manually updated… add a new column between
> P & Q and drag the formulas from column P to column Q. The total YTD would move in
> column R… change the formulas for YTD to include all months… Where there are YoY or
> MoM % variances, simply move the cells… Some data must be taken from the Retention
> file, namely Revenue breakdown (New, Expansion, Contraction, Churn), LTV:CAC (% churn,
> unique and new clients), Unique clients table."*

Concretely this is **manual column-insertion surgery** on the `Reporting (1)`/`(2)`
tables (MRR by market & services, `# of clients`, `MRR per client`, `Market share`,
`Services share`, `MRR per market`, `Revenue breakdown` r45, `Cost of ARR`, `Marketing
spent/efficiency`, `Profitability`, `Unique clients`, `YoY Growth`). Each month you
insert a column, drag formulas right, and **manually re-extend every YTD formula**.
The Retention-sourced tables are cross-pulled by hand. Failure modes: a mis-placed
insert shifts every downstream reference (exactly the "rows shifted" problem we hit
on `4 Unique MRR Schedule`); a YTD formula that isn't re-extended silently drops the
new month.

> **¶13 —** *"…pay attention to the formulas and which cells are used. Usually the last
> 2 months are formulas, while the previous months should be pasted as values, so that
> they are fixed. Compare with the previous MRR Schedule file from last month to fix
> the values for the data 2 months ago (doing June → fix April)."*

This is the **freeze-by-copy-paste / restatement** convention. Only the last two
months stay live; older months are hardcoded ("paste as values"). This is *why* the
schedule restates prior months between versions (the same pattern seen in
[ahaplay]) — and it is the **root cause of the entire class of bugs this session
chased**: once values are frozen by paste, provenance is lost, and any drift (a
mixed-MRR client, a stale cache, a shifted row) shows up as an unexplained number
with no formula trail. The "−824 / +50" hunt was a direct consequence.

> **¶14 —** *"The main revenue table… PM and Actual, as well as Actual YTD columns
> formulas must be changed to take the right cells… Plan for the month and YTD, as
> well as the % changes should be fine."*

Manual re-pointing of the headline revenue table's Actual / Actual-YTD formulas every
month; only the Plan columns are stable. Pure mechanical cell-selection, high
fat-finger risk.

> **¶15 —** *"The charts must be updated to select the most recent 12 months… go in the
> chart and Select Data."*

Each chart's source range is hand-edited monthly to roll the 12-month window.

> **¶16 —** *"The table Operating Cash Flows must be changed… select the correct months
> for the current and previous month and fix the values for the data in 2 months ago…"*

`Reporting (2)!r147 Operating Cash Flows, EUR` — same freeze-2-months-ago pattern as
¶13, cross-checked against last month's file / the Monitoring report.

> **¶17 —** *"The summary tables from row 171 to 202 should be fine with no need for
> changes, but double check."*

The `KPIs` / `LinkedIn Learning` / `Cash related KPIs` / `Metrics` block
(`Reporting (1)` r150–196). Mostly stable, manual double-check.

> **¶18 —** *"AGAIN, compare the data in the 2nd-to-last month and the previous month
> with the Monitoring report and the MRR Schedule file from the previous month… seeing
> that you have the same value for 3 months in a row."*

The **entire QC is an eyeball diff** — "is the value the same for 3 months in a row?"
There is no automated check. This is the analogue of the `4 Unique MRR Schedule` row-5
QC, but even weaker (visual, against a prior file the analyst must open by hand).

---

## 2. The pattern

Every paragraph is the same shape: **a hand-maintained presentation layer sitting on
top of formula chains, with history frozen by copy-paste and verified by eye.** Column
inserts, formula drags, range re-selection, paste-as-values, manual cross-file compare.
There is no single source of truth — the "data" lives inside the presentation, frozen
per month. This is precisely the fragility that produced this session's whole arc:
mixed-MRR clients mis-reconciling, rows shifting between uploads, cached values not
matching the live file. Automating the MRR Schedule alone is not enough if the
Monitoring is still rebuilt by hand on top of it.

---

## 3. Proposal — process overhaul

Replace the monthly Excel surgery with a **generated Monitoring layer over a single
canonical dataset**, mirroring the Farada philosophy (programmatic build + automated
checks instead of manual reconciliation), and reusing the repo's existing pillars.

**Target architecture**
1. **Single source of truth (data, not presentation).** The MRR calc (`Source Data →
   MRR Data → Unique`) and Retention become **immutable monthly data outputs** (a
   tidy long table: client × market × service × month × MRR/Non-MRR × value), written
   once per period. Prior months are data, never re-typed.
2. **Generated Reporting tables.** Each Monitoring table (MRR by market/service, #
   clients, MRR/client, Revenue breakdown, Marketing KPIs, Operating Cash Flows,
   YTD/YoY/MoM) is a **deterministic transform/query** over that dataset, re-rendered
   in full each month — no column insertion, no drag-right, no paste-as-values. The
   12-month chart windows fall out of the query.
3. **Restatement as an explicit diff, not silent paste.** When a prior month changes
   (the documented restatement), produce a **named diff** (this-month dataset vs
   last-month dataset) so restatements are visible and reviewable — not a hidden
   hardcode.
4. **Automated QC guards replacing the eyeball checks** (the immediate, standalone win):
   - **Per-client MRR reconciliation** — reproduce row-5 in code, per month *and* per
     client, fail loudly with names (this caught −824 = UNICREDIT/CYCLON/MATECO/HUDSON
     EDGE, and +50 = MACROMATOR).
   - **MRR/Non-MRR flag consistency** — flag any invoice whose flag disagrees with the
     same client's prior identical invoices, and any client with *mixed* flags (the
     HUDSON EDGE / MACROMATOR structural bug). Bake the `SUMIFS … ,B,"MRR"` flag filter
     into the model so mixed clients always reconcile.
   - **3-months-in-a-row / restatement check** — automate ¶18: diff the 2-months-ago
     and prior-month figures vs last period's file, report any unexpected movement.

**Phasing**
- **Phase A (now, highest ROI, low risk): QC guards as a standalone tool.** Run against
  the existing hand-built workbook; ends the whack-a-mole immediately without changing
  the colleague's process. (Already prototyped this session.)
- **Phase B: canonical dataset.** Emit the long-table MRR/Retention data from the
  Categorization (the transform is built + gate-validated; selection is the
  human-confirmed candidate list).
- **Phase C: generated Monitoring tables** over the dataset, then the deck (charts
  pillar), retiring the manual column surgery.

**Why this order:** Phase A pays for itself the first month (no more hunting unexplained
deviations) and is independent of B/C. B/C are the larger build and can follow once the
MRR-schedule engine (Phase 2.2 of the build spec) lands.

## Risks
| Risk | Mitigation |
|---|---|
| Colleague's process is Excel-native; full generation is a big change | Phase A adds guards without changing their workflow; B/C opt-in |
| openpyxl drops charts on save | generate the deck via the charts pillar, not by editing the live xlsx |
| Restatement semantics (what the Platform expects) unconfirmed | make restatement an explicit, reviewable diff; confirm policy with Costin |

## Open questions
- Does the Platform/Costin want the **restated** series each month, or frozen-as-published?
- Is the Monitoring deck in scope for generation (Phase C), or only the data + QC (A/B)?
