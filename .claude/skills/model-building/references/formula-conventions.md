# Model formula conventions

How the ProForma engine and statements are *wired*. Calculations are client-specific;
*these patterns* are house standard. They exist because reviewers caught real errors —
each rule below is a scar. Worked examples are from the Farada 5Y builder
(`scripts/build_farada_5y.py`); the verification gate is `scripts/check_model.py`.

## Cash flow is driven by the WC balances, never by the P&L

The single most-repeated correction: **cash = accrual − Δ(working-capital balance
ROW)**. Do NOT recompute the timing deviation from the P&L line and a ratio inline.
The WC driver row (Receivables / Payables / Deferred revenue) is the single source of
truth for timing, so the cash line and the balance sheet move together.

- Wrong (P&L-derived deviation):
  `cash = D47 - $J$184/30*(D47-C47)`   ← recomputes ΔAR from the revenue line
- Right (balance-driven):
  `cash = D45 - (D166-C166) + (D183-C183)`   ← Revenue − ΔReceivables + ΔDeferred
- Per-bucket (payables/personnel), reference the bucket's own balance row:
  `cash_supplier = (D90-D91) - (D170-C170)`   ← cost − Δ(S&M payable balance)
  `pay_personnel = D91 - (D180-C180)`         ← payroll − Δ(personnel payable balance)

If a cash line still contains a P&L line inside a `*ratio*Δ` term, it is wrong.

## Working-capital balances are the drivers

Each WC line is a **closing balance** = `days/30 × that month's accrual`; the cash line
takes its month-over-month delta. At 30 days this is a clean one-month lag; at other
terms it splits (14-day payroll → ~16/30 this month + 14/30 last month). Opening
balances come from the Inputs opening-balance block.

- `AR_balance = DSO/30 × (Revenue − annually-prepaid subscription)`
- `payable_bucket = DPO/30 × bucket_cost_excl_payroll`
- `personnel_payable = payroll_days/30 × payroll_bucket`

## Receivables exclude annually-prepaid revenue

Revenue billed annually in advance is **deferred revenue, not a receivable** — cash is
collected upfront, recognised over the term. So it is *excluded* from the AR balance
and tracked in a deferred-revenue running balance:
`deferred[m] = deferred[m-1] + billings[m] − recognised[m]` (opening from Inputs).
`billings = recognised + Δdeferred`; the two must reconcile (Σ billings = Σ recognised
+ ending deferred). Deferred must never go negative.

## Annual-in-advance billing = cohort billing

When contracts prepay a year and renew annually, cash in month m is 12× the *new* ARR
plus renewals of cohorts from 12/24/36/48 months ago:
`billings[m] = 12 × Σ_{k∈0,12,24,36,48} ΔARR[m-k]`. Exact when the rate is constant and
the installed base is monotonic; otherwise document the approximation.

## Lag the RECOGNISED revenue, not a helper

When a line recognises on a delay (e.g. usage overage ramping `OFFSET(-J78)` months),
lag the **recognised** row (which already carries the delay), not the pre-delay helper —
and check the recognised row's formula isn't uniform across months before reconstructing
it. Reconstructing a delay you don't fully understand is how you get a tail-month bug.

## Statements are thin; CF is direct-method

- ProForma computes the lines; IS/CF/BS **pull and present** (subtotals + margins on the
  statements, not the ProForma).
- **Direct-method CF**: `CFO = cash from customers − suppliers − personnel − finance +
  tax`. No depreciation add-back needed — which is why a P&L with no D&A still yields a
  complete cash flow.
- **Cash is the plug**: ending cash chains (`ending = beginning + Δ`, `beginning[m] =
  ending[m-1]`); the BS carries `check = Assets − (E+L) = 0` every month.

## Scenario selectors

Every input's active cell is `=OFFSET(K{r},0,$D$2)` reading K/L/M/N via the `D2`
selector. Downstream formulas reference the **active** cell (`' Inputs'!$J$NN`), never a
scenario column directly, so switching `D2` reprices the whole model.

## Clear stray leftovers

Reordered/《WIP》 workbooks carry junk (`=-#REF!`, half-built rows). Clear the cells a
section will re-own before wiring it, or the gate's error scan (rightly) fails on them.

## Verify with the recalc gate — not by eye

openpyxl can't evaluate formulas and OFFSET defeats pure-Python engines. Recompute with
LibreOffice (`core/model/recalc.py`) and assert on the result: `scripts/check_model.py
<client> <wb> --full`. Every rule above is machine-checked there (subtotals foot, cash
chain, BS check = 0, no error cells). A fast Python oracle over cached accruals is a
useful pre-check, but the recalc gate is the authority.
