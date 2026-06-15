# Almacena — budget↔management-data alignment ledger (FY2026, Jan–Apr)

Aligns the stale budget (`budget-q126.xlsx`) with management actuals
(`taxonomi_*_04.xlsx`) so the model reflects reality **before** we ask the client
for inputs. Variances are programmatic (`one_offs/budget_vs_actual.py`, IS,
Jan–Apr YTD + April spot); drivers traced via `core/model` + the GL analysis in
`budget/APR_BUDGET_VS_ACTUAL.md`. EUR.

## Structural finding (changes where fixes land)

In the live model `Almacena-26_AprActuals.xlsx`, the monthly **taxonomi tabs are
wired to the *actuals* sheets** — `core/model.trace_precedents` on a forecast-month
cell (`is_found_taxonomi!H2`, May) walks to `actuals_found` (empty past April), not
to a driver. So the taxonomi tabs are the *actuals view*; the **forecast** lives in
`Pro Forma` fed by **`Inputs_Foundation`, `KPIs`, `Loans Database`**. Aligning the
budget therefore means editing **those driver sheets (+ Pro Forma)** — not the
taxonomi cells.

## Classification key

- **INTERNAL** — set from management data now (backward facts unconditional;
  forward assumptions set from realized economics, logged here).
- **NEEDS-CLIENT** — not inferable from management data.
- **INVESTIGATE** — needs a GL trace before classifying.

## Material variances → drivers

### Foundation (the root — consolidated revenue pulls from here)

| Line | Δ YTD | Δ Apr | Driver | Class | Proposed change |
|---|---:|---:|---|---|---|
| Gross Interest Revenue | +218,888 | +89,898 | `Inputs_Foundation` book size (€8.2M modelled vs ~€13.7M actual) | INTERNAL¹ | scale book to the realized deployed book |
| Funding Cost | −81,817 | −50,256 | funding-cost rate (10% → ~9.08%) + bigger book | INTERNAL¹ | cut rate to realized blended ~9% |
| Flat Fee | +87,256 | +25,105 | flat-fee pricing/volume (`KPIs`) | INTERNAL (fwd) | raise to realized run-rate |
| G&A Professional Services | −16,339 | −773 | over-budgeted advisory/legal | INTERNAL | trim to run-rate |
| Finance Income | −1,885 | −5,438 | FX on USD transfers (accts 9300/9301), not interest | INTERNAL | re-model as FX / non-operating |
| Finance Costs | +16,478 | +12,395 | FX (unbudgeted) | INTERNAL | re-model as FX |

¹ The *aggregate* book size & blended rate are INTERNAL (set from realized economics); the **loan-by-loan schedule** behind them is NEEDS-CLIENT (see below).

### Consolidated

| Line | Δ YTD | Δ Apr | Driver | Class | Proposed change |
|---|---:|---:|---|---|---|
| Net Interest Revenue | +137,071 | +39,642 | foundation book/rate (above) | INTERNAL¹ | flows from foundation fix |
| Flat Fee | +87,256 | +25,105 | `KPIs` flat-fee | INTERNAL (fwd) | realized run-rate |
| Sales — Other | −17,965 | 0 | budgeted "Other services" revenue not realized | INTERNAL | remove/zero the budgeted line |
| Cost of Sales — Other (transport) | +14,048 | −13,592 | acct 7010 Transportation (Suhara, Molenbergnatie) | INTERNAL | align to monthly run-rate (over earlier, under Apr) |
| R&D Contractors | −10,433 | −7,192 | acct 5582 over-budgeted | INTERNAL | trim |
| G&A Professional Services | +38,692 | +7,818 | accts 5580/82/83 (Nua, Strik, Gaviria, CFO Insights) | INTERNAL (fwd) | raise forecast |
| G&A — Other | +47,136 | −503 | **NEW** (Jan–Mar accrual; Apr negligible) | INVESTIGATE | GL-trace the account → then trim/raise |
| Finance income | +16,507 | +16,578 | FX (accts 9300/9301) | INTERNAL | re-model as FX |
| Finance costs | −22,760 | −14,979 | FX | INTERNAL | re-model as FX |
| Other non-operational revenues | −179,790 | 0 | **NEW** large; actual −179,790 vs budget 0 | NEEDS-CLIENT | client must explain (write-off / reclass / clawback) |

## NEEDS-CLIENT summary (the client ask — only what we cannot infer)

1. **Loan schedule rebuild (`Loans Database`) — CLEAN-SLATE approach (decided).**
   Replace the whole schedule with the verified April book rather than reconciling
   row-by-row. Actual outstanding @ 30-Apr-2026 = **€16,209,684 / 25 loans / 15
   lenders @ blended 9.08%** (precise; supersedes the earlier ~€13.7M estimate).
   Founder snapshot to confirm + say what to add: `budget/LOANS_APRIL_SNAPSHOT.md`
   (local, not committed — loan-level detail). Founder asks: confirm completeness;
   full legal names for coded lenders (JSKR, KH, PB, PS, VD, IA, MMB, AI, AS);
   what to add; and whether **Senior Debt €120M / Venture Debt €30M** are committed
   (model separately, NOT in the current book — they inflated the old model to €159M).
2. **Other non-operational revenues −179,790** — what is it?
3. **Sign-off on forward assumptions we set** — flat-fee run-rate sustainability; raised professional-services forecast.

## What we fix internally (no client needed) — to apply at T6

- `Inputs_Foundation`: book size → realized; funding-cost rate 10% → ~9%.
- `KPIs`: populate the blank pricing rows (gross interest, funding cost, net interest, flat fee) from realized economics.
- Account-level forecast trims/raises: transport (7010), R&D contractors (5582), G&A professional services (5580/82/83), zero the un-realized "Other services" revenue.
- Re-model finance income/costs as **FX** (accts 9300/9301), not interest.
- Resolve **G&A Other +47k** via GL trace, then adjust.

> **CHECKPOINT (plan Phase 2):** review this ledger before any model edit (T6).
> Nothing in the workbook has been changed.
