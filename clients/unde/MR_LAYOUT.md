# Undelucram source layout

Two source workbooks feed the taxonomi.

## 1. Management report — `raw/<MM>/Undelucram - Monthly reports 2026.xlsx`

Already in EUR (carries the RON FX rate in row 3 but values are pre-converted).
Consumed sheets:

| Statement | Sheet | header row | label col | period format | notes |
|---|---|---|---|---|---|
| IS | `Income Statement` | 2 | **B (2)** | month names (cols E..P, Jan=E) | revenue per market × service keyed by cost-center code in col C |
| BS | `Balance Sheet` | 2 | A (1) | month names (cols C..N, Jan=C) | |
| CF | `Cash Flow Statement` | 2 | A (1) | month names | direct-method; maps 1:1 to taxonomi `CF Indirect (Actual)` rows |

The taxonomi's three months columns are Jan=D … Dec=O (Data/Group/Subgroup = A/B/C).

### Service relabeling (IS revenue)
The MR keys revenue by cost-center code (`R001`..`R009`, market letter + suffix).
The taxonomi renamed several services — decoded by value-matching March:

| MR label | suffix | → taxonomi subgroup |
|---|---|---|
| Employer branding | 001 | Employer branding |
| Jobbing | 002 | Jobbing |
| Salary report | 003 | Industry Benchmarking Tool (Basic) |
| Brand perception | 004 | Industry Benchmarking Tool (Enterprise) |
| Advertising | 005 | Advertising |
| Linkedin learning | 009 | Linkedin Learning |
| *(none yet)* | — | HR Vendor Marketplace, Integration with InterviewsUp → null |

Market letters (Sales): Romania=R, Greece=G, Hungary=H, Moldova=M, Bulgaria=B,
Czech Republic=C, MENA=X, Poland=P, Other markets=O.
**Trap:** in the S&M *Payroll* block the accountant swaps Poland=`O007` /
Other markets=`P007` (only there; Marketing/Events are not swapped). The mapping
resolves these by row + label, so the swap is handled — but if rows are reordered,
re-verify.

`mr_label` in `mapping.yaml` keeps the exact MR label (incl. trailing spaces like
`"Infrastructure "`, `"Software & Tools "`) so the loader's label-vs-row fallback
catches reorders.

## 2. MRR schedule — `raw/<MM>/MRR_Schedule_Undelucram <Month> 2026.xlsx`

Source for the **MRR headline only** (taxonomi `IS!MRR`). Read from sheet
`Reporting (1)`, row labelled `MRR`, column matched by the date header in row 2.

- The schedule's own `IS`/`CF`/`BS` tabs are a manually-rolled 2-month summary and
  are often **stale** (the April file's `IS` tab still shows March). Do **not** use
  them — `Reporting (1)` is the live, formula-driven source.
- The schedule **restates prior months** between versions (e.g. March MRR =
  106,353.4 in the March file → 107,190.1 in the April file). Use the report
  month's column from the report month's file.

## Parked (not consumed)
`Categorization`, `Retention_Analysis`, `Churned clients`, and the rest of the MRR
schedule belong to the Monitoring-deck workstream, not the taxonomi.
