# Undelucram — engineer notes & monthly runbook

Deliverable (step 1): the **taxonomi-actual** workbook, uploaded to the Platform.
The MRR Schedule / Retention / Monitoring deck is a separate, still-manual
workstream and is out of scope here.

## Architecture
Standard `report` pipeline (`core/report/mr.py` + `mr_to_taxonomi.py`) driven by
`mapping.yaml`, plus one client-specific seam: **MRR is sourced from the MRR
schedule** (see `MR_LAYOUT.md`), which the shared `extract_month` can't reach
(second file). `one_offs/build_taxonomi.py` wraps the core functions and injects
MRR. Everything else comes from the management report.

Why a one-off and not `scripts/build_report.py --extract-only`: the core pipeline
assumes a single `mr_source`. Undelucram needs a second source for one cell. If a
second client ever needs cross-file sourcing, promote this into the core (per-entry
`source:` override + `reporting.mrr_source`) and retire the one-off.

## Files
- `config.yaml` — `report` use case; `reporting.mr_source`, `mrr_source`, `mrr_sheet`.
- `mapping.yaml` — IS/CF/BS mapping + `mr_layout` + `kpi_derivations` + `known_discrepancies`. **Generated** by `one_offs/gen_mapping.py`; re-run only on layout change.
- `one_offs/gen_mapping.py` — emits `mapping.yaml` (decodes the service relabeling).
- `one_offs/build_taxonomi.py` — builds one month's taxonomi column.
- `one_offs/repro_gate.py` — reproduction gate (rebuild a known month, diff).

## Reproduction gate (trust check)
`python clients/unde/one_offs/repro_gate.py 2026-03` rebuilds March from source and
diffs against the published March taxonomi. PASS = every MR-sourced row < €1. As of
onboarding: PASS (only intentional `known_discrepancies` differ).

## Monthly cadence
1. Drop the new management report + MRR schedule into `raw/<MM>/`.
2. Update `config.yaml`: `as_of_date`, `mr_source`, `mrr_source` → new paths.
3. If the accountant changed the MR layout, re-run `gen_mapping.py` and re-check the
   reproduction gate on the prior month.
4. Build: `python clients/unde/one_offs/build_taxonomi.py <YYYY-MM>`
   → writes `raw/taxonomi_act_<YYYY-MM>.xlsx`.
5. Sanity check: Sales Σ ties to the MR `Sales` subtotal; MRR matches
   `Reporting (1)` MRR for the month; prior columns unchanged.
6. Upload to the Platform.

## Open / known items
- **AP turnover** (BS derived KPI) reproduces ~0.7 vs client 0.4 — opex/personnel
  basis unconfirmed. Best-effort; flagged in `known_discrepancies`.
- **CoS "LinkedIn Learning (share)"** ← MR "Other CoS" (A021) is a best-guess
  mapping (€14,771 in Apr). Confirm vs the chart of accounts.
- **Prior-month restatement:** the MRR schedule restates earlier months. We write
  only the new month's column and leave published columns as-is. If the Platform
  expects the restated series, that's a policy decision to revisit.
- **HR Vendor Marketplace / Integration with InterviewsUp** have no MR source yet.
