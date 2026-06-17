# Undelucram — outstanding flags (living register)

Fluid list of known issues found while reconciling the legacy reporting, parked
to dive into later. **Do not fix in the legacy files** — these are reference;
corrections go in the new pipeline. Update status as items are resolved. Last
touched 2026-06-17.

Severity: 🔴 material / 🟡 small / ⚪ cosmetic.

| # | Flag | Where | Severity | Status |
|---|---|---|---|---|
| F1 | **BS cash exceeds bank/CF cash by ~€8.2k every month** (8,161 / 8,083 / 8,183 / 8,378 Jan–Apr; growing). Cause unconfirmed (cash-in-hand / 3rd account / carried error). | Mgmt report `Balance Sheet` cash vs `Cash Flow Statement` ending/bank balances | 🔴 | open — ask accountant |
| F2 | **March MRR restated 106,353 → 107,190 (+€837)** between 03 and 04 cycles (March Churn +€983 / Contraction −€147), in MRR schedule & Retention. The published **March taxonomi MRR (106,353) is now stale**. | MRR schedule `Reporting`, Retention `MRR Retention` EoP | 🟡 | open — decide restate-vs-frozen policy |
| F3 | **IS-vs-BS profit drift** — BS cumulative profit vs cumulative IS net profit: Feb −€113, Mar +€50, Apr +€566 (growing). | Mgmt report IS vs BS | 🟡 | open |
| F4 | **Mixed MRR/Non-MRR client QC bug** — Unique `SUMIFS` keys by client NAME only (no flag filter), so a client flagged MRR pulls its Non-MRR rows in active months. Confirmed: HUDSON EDGE (€50, 2025-05), MACROMATOR (€49.99, 2025-11). Also new clients missing from the Unique list (drove the May −824 QC). | MRR schedule `4 Unique MRR Schedule` row 5 | 🔴 | open — fix = add `,'3 MRR Data'!$B:$B,"MRR"` model-wide + sync client list |
| F5 | **Broken Reporting growth-ratio cells (#DIV/0!)** on zero-base segments (MENA, Poland, Czech Republic, Other markets, SME Jobbing, LinkedIn Learning) — e.g. `=AM/AL-1` with AL=0. ~45 cells across `Reporting (1/2/3)`. NOT a true circular ref (`iterate=None`); a forward-dependency on **frozen prior-month cells that last month's colleague filled wrong**, propagated into May (e.g. `Reporting (3)`!F65/67/68 chain off `Reporting (1)`!AO72/74/75). | `Reporting (1/2/3)` | ⚪→🟡 | open — last-month-fill error to revisit |
| F6 | **Reporting MRR vs MRR-Data SUMIF gap** — `Reporting (1)` headline May MRR ≈ 105,400 vs `3 MRR Data` MRR total ≈ 104,365 (~€1k). Likely EoP-waterfall vs point-in-time basis; verify. | MRR schedule | 🟡 | open |

Ties that HOLD (baseline — re-confirm if they ever break): Retention EoP == MRR
schedule Reporting MRR (Jan–Apr); BS Total Assets == Total E&L; mgmt report
Jan–Mar identical across 03/04 versions (the accountant's report doesn't drift —
only the analyst's MRR/Retention restate).
