# Almacena — model-maintenance reference

Distilled from the first real alignment run (FY2026, Jan–Apr actuals). See
`clients/almacena/MODEL_CONTRACT.md` for the full structural inventory,
`clients/almacena/model_rules.yaml` for the parser rules, and
`clients/almacena/ALIGNMENT_LEDGER.md` for the worked variance→driver ledger.

## Model & data

- **Model (budget side):** `clients/almacena/budget/Almacena-26_AprActuals.xlsx`
  (gitignored). Budget taxonomi tabs: `is/cf/bs_cons_taxonomi` (consolidated),
  `is/cf/bs_found_taxonomi` (foundation).
- **Stale budget vintage:** `clients/almacena/budget/budget-q126.xlsx` (the pre-
  actuals plan — the "budget" in budget-vs-actual).
- **Management data (actuals):** `clients/almacena/raw/taxonomi_consolidated_04.xlsx`
  + `taxonomi_ap_foundation_04.xlsx` (2026 Jan–Apr), also in `almacena.db`.
- **Period:** FY2026 focus; 2025 + 2026 Jan–Apr actual; May–Dec forecast. EUR.

## Drivers — the LIVE wiring (corrected via the `core/model` parser)

> A trap this client taught us: the obviously-named driver sheets are **orphans**.
> `Inputs_Foundation` and `KPIs` have *no formula referencing them* — editing them
> changes nothing. This was only caught by tracing with the parser. Always confirm
> before editing.

The live wiring (per `trace_precedents`):

- **` Inputs`** (leading space) — the single live driver sheet; feeds IS, CF, BS,
  IS_Found, `Pro Forma`, KPIs, HR, Loans Database. This is where revenue-ramp and
  rate edits land.
- **`Pro Forma`** (~10k formulas) — the forecast engine; feeds every statement.
- **`Loans Database` → ` Inputs`!J191** (`AVERAGEIFS` = derived blended funding
  cost) — so updating the loan book **auto-propagates** the funding-cost rate.
- **`Loans Database`** — the loan schedule itself (**stale; the main NEEDS-CLIENT
  item**; the real book is ~€15.4M / 21 loans @ ~9.09%, not the modelled ~€8.2M).
- **Orphans — do NOT edit:** `Inputs_Foundation`, `KPIs`.

Note: in the live model the monthly **taxonomi tabs are wired to the *actuals*
sheets**, so a forecast-month taxonomi cell traces to `actuals_*` (empty past
April), not to a driver. The taxonomi tabs are the *actuals view*; the forecast
lives in `Pro Forma`. Align the budget by editing ` Inputs` / `Pro Forma` /
`Loans Database` — not the taxonomi cells.

## Quirks

- Crossed raw filenames on intake; mislabeled CF/BS header years (the contract
  keys months by column position — positional axis, not the header year).
- `Loans Database` not yet updated for the real book; modelled as **evergreen**
  (live loans pushed past the horizon) to avoid phantom roll-over cash flows —
  see the ledger's "roll-overs & phantom cash flow" section.
- bvnv entity classification uses delimited tokens (so "Investor" isn't mis-tagged
  as the BV/NV entity).
- `Senior Debt €120M` / `Venture Debt €30M` are the *unclosed fundraise*, not the
  real book — they inflated the old model to €159M; model separately.

## Worked example (FY2026 Jan–Apr)

The full run — material variances, their live drivers, INTERNAL vs NEEDS-CLIENT
classification, and the distilled client ask — is the alignment ledger:
`clients/almacena/ALIGNMENT_LEDGER.md`. Headline numbers and the GL-level signal
trace are in `clients/almacena/budget/APR_BUDGET_VS_ACTUAL.md`.
