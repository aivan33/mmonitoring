# MR Workbook Layout — `raw/mr_2026-03.xlsx`

Reference for `core/loaders/mr.py` and the deeper-mapping work in Phase F5.

The MR workbook is the master DATEV-derived report. Its **P&L**, **CF**, **BS** sheets are consolidated views (Germany + Serbia, FX-converted upstream) — these three feed the current pipeline directly. The remaining sheets carry the upstream consolidation, account-level detail, and the DATEV → consolidated mapping logic; they are **parked** for Phase F5 (deeper mapping next iteration).

All amounts are EUR. Header row is **row 2** on every sheet (row 1 holds the title / "Currency: EUR" text).

## Consumed sheets

### P&L
- **Header row:** 2 — col 1 = `"Currency: EUR"`, cols 2–25 = monthly date headers (`2025-01` through `2026-12`+).
- **Label column:** 1 (col A).
- **Data rows:** 4 → 82. Rows 83–84 are blank / `Check` diagnostics.
- **Monthly columns:** col 2 = `2025-01`, col 13 = `2025-12`, col 14 = `2026-01`, **col 16 = `2026-03`**, col 25 = `2026-12`.
- **Section structure:** Sales (header r4 "Sales ", trailing space) → 4 vertical headers each followed by 4 sub-items (Food Logistics r5–9, Industrial IoT r10–14, Consumer Electronics r15–19, Medical Devices r20–24) → Other r25 → DIRECT COSTS header r26 → cost line items r27–33 → Gross profit r34 → Operating expenses r36 → S&M section r37–45 → G&A section r46–57 → R&D section r58–65 → Direct Amortization adjustment r66 → EBITDA r67 → ... → Net profit r81.
- **Datatype:** decimal floats. The taxonomi rounds to integers on save.

> **Prompt vs. reality:** The downstream prompt in `reference/prompt-mm-mar26.md` lists row numbers that are **off by one** for almost every entry (e.g., prompt says "row 26 = COGS" but COGS is at r27; prompt says "row 5 = Food Logistics first sub-item" but r5 is the Food Logistics sub-header and r6 is the first sub-item). Likely cause: the prompt's author started counting at the "Sales" header row but the actual sheet has a leading blank/header row before it. **Don't trust prompt row numbers for P&L.** Use the labels below as the primary key, with row numbers from this file.

### CF (Cash Flow Statement Indirect)
- **Header row:** 2 — col 2 = `"Currency: EUR"`, cols 3–14 = monthly date headers `2026-01` → `2026-12`. **No 2025 data in this sheet.**
- **Label columns:** col 1 = short code (e.g. `Cust`, `Suppl`, `staff`, `CAPEX`, `CFF_1`), col 2 = full label.
- **Data rows:** 4 → 27. Rows 28–29 are blank / `Check`.
- **Monthly columns:** col 3 = `2026-01`, **col 5 = `2026-03`**, col 14 = `2026-12`.
- **Section structure:** Operating r4–10 → CFO subtotal r11 → Investing r12–14 → CFI subtotal r15 → Financing r16–22 → CFF subtotal r23 → Excess cash r24 → Beginning Cash r25 → Ending Cash r26 → % change r27.
- **Datatype:** decimal floats.

### BS (Balance Sheet)
- **Header row:** 2 — col 2 = `"Currency: EUR"`, cols 3–26 = monthly date headers `2025-01` → `2026-12`.
- **Label column:** 2.
- **Data rows:** 4 → 33. Rows 34–35 are `check` / `Check` diagnostics.
- **Monthly columns:** col 3 = `2025-01`, col 14 = `2025-12`, col 15 = `2026-01`, **col 17 = `2026-03`**, col 26 = `2026-12`.
- **Section structure:** ASSETS header r4 → Non-tangible fixed assets r5–6 → Tangible fixed assets r7–9 → Current assets r10–16 → TOTAL ASSETS r17 → EQUITY AND LIABILITIES header r19 → EQUITY r20–22 → Long-term liabilities r23–25 → Current liabilities r26–30 → TOTAL LIABILITIES r31 → TOTAL EQUITY AND LIABILITIES r33.
- **Scope:** German entity only (Serbia BS is not consolidated). Confirmed in row 1 of the CF sheet's note — only CF/PL consolidate.
- **Datatype:** decimal floats.

## Parked sheets (Phase F5)

| Sheet | Approx role (one-liner) | Why parked |
|---|---|---|
| `BWA` | DATEV-format Betriebswirtschaftliche Auswertung — German tax-format P&L with account numbers in col 2, "Row/account name" in col 3, monthly columns starting col 4 (`Jan/2026`). 156 rows. | Carries the account-level detail behind P&L. Wires into Phase F5 (Task 14: drill-down from P&L variance to DATEV accounts). |
| `ControllingReport BWA` | Mapping-aware variant of BWA — col 1 = `Mapping`, then Row/Account/Name/months. 199 rows. | Same domain as BWA + the explicit mapping column. Likely the bridge between BWA and the consolidated P&L. Phase F5. |
| `CR-Upload` | Upload-formatted controlling export — same shape as BWA but the title says "CF data". 199 rows. | Source for the CF Indirect sheet. Phase F5 may use it to extend CF history into 2025 if/when a separate 2025 MR appears. |
| `Trial balance` | GL trial balance with account-level opening + monthly D/C postings. Cols: Account / Name / ob-value / D / C / Jan/2026 / D / C / ... 87 rows. | Lowest-level detail. Phase F5: ties the DATEV chart of accounts to taxonomi line items. |
| `Balance Sheet` | Interim BS accounts — title "Interim balance sheet accounts", Berlin, FaradaIC Sensors GmbH. 169 rows. | Account-level BS (German entity). The consumed `BS` sheet is the consolidated/grouped view; this one has account-level granularity. Phase F5 drill-down. |
| `Serbia` | Pre-consolidation Serbia entity P&L — "Monthly Cost Report FaradaIC Sensors d.o.o.", monthly cols starting Jan. 199 rows. | Holds Serbia data before it's FX-converted and consolidated into the main P&L. Phase F5 task 15: optional `entity='farada_rs'` breakdown. |
| `P&L Mapping` | Account number → balance columns. Row 1: "Account number", "01 balance" through `n balance`. 176 rows. | The DATEV-account ↔ P&L-line mapping itself. **Most relevant of the parked sheets** — wiring this in (Phase F5 Task 14) lets a flagged variance drill down to the DATEV accounts contributing to it. |

## Verification of prompt's column-index claims

| Statement | Period | Prompt's claim (0-indexed) | Verified col (1-indexed) | Match? |
|---|---|---|---|---|
| P&L | 2026-03 | col 15 | **col 16** | ✓ |
| CF  | 2026-01 | col 2  | **col 3**  | ✓ |
| CF  | 2026-03 | col 4  | **col 5**  | ✓ |
| BS  | 2026-01 | col 14 | **col 15** | ✓ |
| BS  | 2026-03 | col 16 | **col 17** | ✓ |

**Column indices match.** Only the **row indices** in the prompt are unreliable — see the prompt-vs-reality note under P&L above. The mapping in `mapping.yaml` (Task 5) uses labels as the primary key and includes the verified row numbers from this file.
