# Farada — model-building reference implementation

FaradaIC 5-year fundraising model — the worked example for `model-building`. A fabless sensor
business: hardware (priced off a volume ASP ladder) + a hardware-enabled SaaS line.

## The 3 pillars, as built (`farada_model_v4.5.xlsx`)
- **Inputs** — capacity · hardware price ladder (8 rungs) · Line-3 usage/bundles · the **6-point
  cost-of-sales curve** (chip/packaging/sensor-test/final-test/ASIC, staged on run-rate) · OPEX
  (payroll from the `HR` sheet) · below-EBITDA (capex/finance/tax) · financing & opening balances.
  *(Still on the pre-Cupffee order — the overhaul re-sequences to I–V; see below.)*
- **ProForma** — Volumes & Drivers → Revenue → COGS → (OPEX) → capex/depreciation → WC & financing
  rolls. Pure engine; subtotals/margins stripped out.
- **Statements** — IS/CF/BS monthly + yearly; direct CF, cash-as-plug, BS `check = 0` (proven by a
  synthetic balance oracle).

## Builders & artifacts (`clients/farada/one_offs/`)
- `build_model_v4.py` (ProForma engine → IS) · `build_model_v4_5.py` (strip subtotals, IS computes
  them, WC/financing rolls, CF/BS). `verify_model_v4_5.py` is the oracle (BS check = 0, no dangling
  refs). Lineage/economics: `clients/farada/modeling/farada_model_logic.md` (schema-generated) and
  `farada_revenue_cogs_waterfall.md` (formula-level revenue/COGS derivation).

## Known overhaul worklist (from `core/schema` validate + this session)
- **Re-sequence Inputs to the Cupffee I–V skeleton**; remove duplicate/empty rows; move inline
  comments to col O (needs the `$J$NN` ref-remap — ~14,600 refs; gate on resolved-target equivalence).
- **Clean orphaned inputs** — e.g. the unused Line-3 usage-pricing ladder (`J25–29`).
- **Drop dead proforma rows** — blended ASP / unit-cost display lines.
- **Fix the capacity `#REF!`** (a deleted capacity tier).
- **SaaS calibration** — overage-only revenue gives ~98% GM (`verify_saas_revenue.py` oracle ready).

## Quirks
- No recalc engine (formulas lib lacks `OFFSET`; no LibreOffice) → verify by oracle + eyeball.
- `clients/farada/modeling/*.xlsx` are gitignored; only the `one_offs/` builders are tracked.
- Two Farada models exist — this is the **5Y investor model**, NOT the operational rolling budget.
