# Model design system

The standardized **formatting** of a client financial model — harvested from the reference budgets
(Cupffee, Almacena, original Farada) so any new model looks like the house. Calculations are
client-specific; *this* is fixed. Harvest real style objects from a reference file (`copy.copy`);
never approximate RGB (it gets rejected). Confirmed values below are the live ones.

## Typography
- **Century Gothic, 10pt** everywhere; **9pt** for the month date-ribbon.
- **Bold:** section headers, sub-numbers, statement banners, input values, the active scenario cell.

## Palette (fills — role → hex)
| Role | Fill | Where |
|---|---|---|
| Section header band | `FFD8D8D8` (grey) | Inputs section rows (`I.`/`II.`…) |
| Editable input value | `FFFEF2CB` (cream) | the Realistic cell (col L) — "this is yours to change" |
| Scenario-active cell | `FFDDFBFF` (cyan) | col J `=OFFSET(K,0,$D$2)` |
| Statement banner / title / line headers | `FFD5EBF4` (light blue) | IS/CF/BS titles, section bands (GROSS PROFIT, ASSETS…) |
| Date ribbon | `FFFFFFFF` (white) | the month row |

## Number formats (explicit constants — do NOT harvest these; harvesting mis-maps them)
`int #,##0` · `eur €#,##0.00` · `pct 0.0%` · `num2 0.00` · `date [$-409]mmm-yy` (real datetimes).
Per-input: counts→int, rates→pct, money→eur, sub-€ costs→num2.

## Pillar 1 — Inputs grammar (one sheet, scenario-switchable)
Columns: **A** Roman section (`I.`) · **B** sub-number (`1.1`,`3.1.1`, bold) · **C** label (left) ·
**D** unit · **F** ladder threshold (if any) · **G/H** start/end date · **J** active `=OFFSET(K{r},0,$D$2)`
(cyan) · **K–N** scenario columns (Realistic/Optimistic/Pessimistic…) · **L** Realistic value (cream) ·
**O** notes. The selector lives at **`D2`** (Realistic=1). Sections, in order (Cupffee skeleton):
**I. FUNDING · II. REVENUE · III. PRODUCTION (yield, cost of sales) · IV. OPERATING EXPENSES ·
V. OTHER ASSUMPTIONS.** Notes go in **col O**, never inline in the label.

## Pillar 2 — ProForma (calc engine, NOT a statement)
One sheet; month columns from `C2` (a real date; fill-right). Section order, top→bottom:
**Volume & Drivers** (revenue drivers on top, cost drivers below) → **Revenue** → **Cost of Sales**
→ **OPEX** → **Balance Sheet** (rolls) → **WC drivers & ratios** → **Cash Flow** → **Taxation** →
**Funding**. *Not all used every time; additions allowed.* **No profitability subtotals/margins
here** — those live on the statements. Leaves pull `' Inputs'!$J$NN`; drivers are computed rows.

## Pillar 3 — Statements (thin) + the taxonomi (the review view)
- **IS / CF / BS**, each **monthly and yearly** (yearly = SUM flows / period-end balances). Pull from
  the ProForma; **compute subtotals + margins here**. CF is **direct-method, cash-as-plug**; BS
  carries a **`check = Assets − (E+L) = 0`** integrity row. Banners in light-blue, accounting `#,##0`.
- **Taxonomi tab** (`*_taxonomi` / `*_platform`) — the standardized meeting view: a FLAT table,
  **col A = Data, B = Group, C = Subgroup**, then month columns pulling each line from the live
  statement (`=CF!<cell>`). Row 1 = `Data | Group | Subgroup | <month labels>`. This is what
  `core/model` classifies and what reviews read.

## KPIs — ad-hoc per business model (not standardized).

## Cardinal formatting rules
1. **Format is a GIVEN** — never restructure an existing model's layout/styling without explicit
   approval (see `core/model/README.md`).
2. **Harvest, don't approximate** — `copy.copy` real font/fill objects from the reference; baked RGB
   gets rejected as "the format is different."
3. **One workbook**, scenario-switchable via `D2` + `OFFSET`; **notes in col O**; **no naked rows**
   (every emitted cell carries a copied style).
