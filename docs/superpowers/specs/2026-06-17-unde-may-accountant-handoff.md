# Undelucram — May 2026 reporting handoff to the accountant

Purpose: send the accountant (Costin) everything needed to finalize the **May
management report** (IS/BS/CF), per the docx flow, while parking the known issues
as flags rather than blocking the send. Authored 2026-06-17.

## What to send (per docx ¶20 + the accountant's needs)
1. **`MRR_Schedule_Undelucram May 2026.xlsx`** — with the May column populated.
2. **`Retention_Analysis_Undelucram May 2026.xlsx`** — built from the May Unique
   MRR Schedule (pasted per docx ¶10).
3. **Monitoring (PPT + PDF)** — the Reporting tables/charts rolled to May.

The accountant uses these to finalize the management report's **revenue** lines
(the rest — costs, BS — is theirs).

## The May revenue figures the accountant needs (headline)
- **May MRR ≈ €105,400** (Reporting/Retention EoP series). Point-in-time MRR-Data
  sum ≈ €104,365 — see flag **F6** for the ~€1k basis gap.
- **By market:** Romania €96.3k · Greece €3.5k · Bulgaria €2.1k · Hungary €1.8k ·
  Moldova €0.6k.
- **By service:** Employer Branding €52.5k · Advertising €38.6k · Corporate
  Jobbing €7.9k · LinkedIn Learning €5.3k · IBT(Basic) €0.03k.
- New May contracts: the 29 confirmed candidates (incl. the CAPGEMINI
  reversal+rebill); net new monthly MRR ≈ €9.9k.

## Flags accompanying the send (parked — do NOT block finalization)
Full register: `.claude/skills/legacy-reporting/references/outstanding-flags.md`.
The ones the accountant should be told about up front:

- **QC (Unique MRR Schedule row 5) carries 2 immaterial mixed-client items**
  (HUDSON EDGE €50, MACROMATOR €49.99 — flag F4). Net ~€100, does not move the
  headline. Structural model fix is scoped separately.
- **Reporting growth-% cells show #DIV/0! on zero-base segments** (MENA, Poland,
  Czech Republic, Other markets, SME Jobbing, LinkedIn Learning — flag F5).
  Cosmetic; some chain off last month's frozen cells that the previous colleague
  filled incorrectly. Being revisited; **does not affect the revenue totals**.
- **Prior-month (March) MRR was restated** 106,353 → 107,190 (flag F2) — relevant
  if the accountant cross-checks against earlier figures.
- **A ~€8.2k BS-cash vs bank-cash gap exists in prior months** (flag F1) — an
  open question for the accountant to explain on their side.

## Acceptance (what "ready to send" means here)
- [ ] May column present in `1.1 Source Data` → `3 MRR Data` → `4 Unique MRR Schedule`.
- [ ] Headline May MRR and the by-market/service split are stated (above).
- [ ] The 4 flags above are listed in the cover note to the accountant.
- [ ] Outstanding-flags register updated (done).
- [ ] NOT required for send: zeroing QC row 5, fixing #DIV/0! cells, resolving F1/F6
      (all explicitly deferred).

## Cover-note draft (to the accountant)
> Attached: May MRR Schedule, Retention, and the Monitoring (PPT/PDF) for the May
> close. Headline May MRR €105,400 (Romania-led; Employer Branding + Advertising
> ≈ 87%). A few caveats we're already chasing and that don't affect the revenue
> totals: (1) two immaterial mixed-MRR client items (~€100) in the schedule QC;
> (2) some growth-% cells show #DIV/0! on markets with no revenue, partly from
> last month's frozen-cell fills we're correcting; (3) March MRR was restated to
> €107,190. Separately, please confirm the ~€8.2k difference between balance-sheet
> cash and the bank-statement cash carried in prior months. Happy to walk through
> any of these.
