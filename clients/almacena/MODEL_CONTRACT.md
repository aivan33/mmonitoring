# Almacena model — structural contract

Structural inventory of `Almacena-26_AprActuals.xlsx` (47 sheets), as parsed by
`core/model/contract.py` using `clients/almacena/model_rules.yaml`. This is the
**structure** layer of the model parser — entities, statement/taxonomi/engine/
driver roles, and the month-axis. No financial values are recorded here.

## Entities

Four entities plus a shared engine/driver section, delimited in the workbook by
`>>>` separator tabs (`Consolidated >>>`, `Stichting Foundation >>>`, `BG >>>>`,
`BVNV >>>`, `>>>`). Sheet order is **not** reliable (taxonomi tabs and separators
are interleaved), so classification is by **name pattern**, not position.

| Entity | Marker substrings | Notes |
|---|---|---|
| `consolidated` | `cons`, or unmarked IS/CF/BS | operating group (default entity) |
| `foundation` | `found`, `foundation` | AP financing foundation (Stichting) |
| `bg` | `bg` | BG entity |
| `bvnv` | delimited `_bv`/`nv `/… | BV / NV / Holding (delimited so "i**nv**estor" isn't caught) |

## Roles

| Role | Detection | Sheets (examples) |
|---|---|---|
| `separator` | name contains `>>>` | `Consolidated >>>`, `>>>` |
| `taxonomi` | contains `taxonomi` | `is_cons_taxonomi`, `cf_found_taxonomi`, `bs_found_taxonomi` |
| `yearly` | contains `yearly` | `IS_Yearly`, `BS_Cons_Yearly`, `CF_Foundation_Yearly`, ` BS_BV_Yearly` |
| `actuals` | contains `actual` / `_act` | `Consolidated Actuals`, `actuals_found`, `BG Actuals`, `BV_act`, `NV Actuals`, `Holding & NV - Actuals` |
| `statement` | starts with `IS`/`CF`/`BS` token | `IS`, `CF`, `BS`, `IS_Found`, `CF_Found`, `BS_Found`, `IS_BG`, `BS_BG` |
| `engine` | exact-name override | ` Inputs`, `Inputs_Foundation` (foundation), `Pro Forma` |
| `driver` | exact-name override | `HR`, `Loans Database`, `Investor Payment Schedule`, `KPIs` |
| `other` | fallback / override | `BG Accounting Data 10.24`, `Data Validation` |

Statement letter (`IS`/`CF`/`BS`) is extracted from the leading token for
statement / taxonomi / yearly sheets; actuals sheets are multi-statement (no letter).

## Month-axis (taxonomi)

The budget taxonomi tabs share one axis: row 1 = `Data | Group | Subgroup |
Jan..Dec`, with the 12 months in **columns D–O**, year **2026** (the focus year).
Columns A/B/C are `Data`/`Group`/`Subgroup` labels. Statement sheets (`IS`/`CF`/
`BS`, ~52 cols) and `Pro Forma` (~55 cols) use a wider multi-year monthly axis —
out of scope for the taxonomi comparison.

## Actuals / budget seam

- **Budget side** (per entity): the taxonomi tabs (`is/cf/bs_<entity>_taxonomi`)
  — these hold the FY2026 budget, Jan–Dec.
- **Actuals side** (per entity): the `*Actuals` / `*_act` sheets (`Consolidated
  Actuals`, `actuals_found`, `BG Actuals`, `BV_act`/`BV Actuals`/`NV Actuals`,
  `Holding & NV - Actuals`).
- **Period scope:** FY2026; 2025 + 2026 Jan–Apr are actual, May–Dec forecast.

## Shared engine / drivers

`engine` = ` Inputs` (group) + `Inputs_Foundation` (foundation) + `Pro Forma`.
`driver` = `HR`, `Loans Database`, `Investor Payment Schedule`, `KPIs`. These are
where reforecast variance traces land (INPUT · LOAN · ACCOUNT).
