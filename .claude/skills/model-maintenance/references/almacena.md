# Almacena — model-maintenance reference

> **STATUS: scaffold.** Filled from the first real alignment run (FY2026,
> Jan–Apr actuals). See `clients/almacena/MODEL_CONTRACT.md` for the full
> structural inventory and `clients/almacena/model_rules.yaml` for the parser rules.

## Model & data

- **Model (budget side):** `clients/almacena/budget/Almacena-26_AprActuals.xlsx`
  (gitignored). Budget taxonomi tabs: `is/cf/bs_cons_taxonomi` (consolidated),
  `is/cf/bs_found_taxonomi` (foundation).
- **Stale budget vintage:** `clients/almacena/budget/budget-q126.xlsx` (the pre-
  actuals plan — the "budget" in budget-vs-actual).
- **Management data (actuals):** `clients/almacena/raw/taxonomi_consolidated_04.xlsx`
  + `taxonomi_ap_foundation_04.xlsx` (2026 Jan–Apr), also in `almacena.db`.
- **Period:** FY2026 focus; 2025 + 2026 Jan–Apr actual; May–Dec forecast.

## Drivers (where variances get fixed)

- `Inputs_Foundation` — foundation funding book size + funding cost rate.
- `KPIs` — pricing rows (gross interest rate, funding cost, net interest rate, flat fee).
- `Loans Database` — the loan schedule (**stale; the main NEEDS-CLIENT item**).
- ` Inputs`, `Pro Forma`, `HR` — group engine / headcount.

## Quirks

- Crossed raw filenames on intake; mislabeled CF/BS header years (keyed by column position).
- `Loans Database` not yet updated for the real ~€13.7M book.
- bvnv classification uses delimited tokens (so "Investor" isn't mis-tagged).

## Worked example (FY2026 Jan–Apr)

> Filled by the alignment run — see `clients/almacena/ALIGNMENT_LEDGER.md`.
