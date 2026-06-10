# Almacena — April 2026 taxonomi build notes

Wiring of the April close (Jan–Apr 2026 YTD) for both tracked entities, via
`build_taxonomi.py` + `taxonomi_mapping.yaml`.

## Inputs (renamed — filenames were crossed vs their stream)

The two raw statements the client dropped in `raw/` were named for the *opposite*
stream they feed (confirmed by cell content, `_archive/almacena/README.md`, and
the `scripts/validate.py` assertions). Renamed on intake:

| Original name | Renamed to | Real content | Feeds entity |
|---|---|---|---|
| `foundation_apr.xlsx` | `src_consolidated_apr.xlsx` | operating group conso (`IS/BS/CF Conso` + Holding/NV/BV) | `consolidated` |
| `consolidated_apr.xlsx` | `src_ap_foundation_apr.xlsx` | AP financing foundation (deal-financing, "Foundation capital") | `ap_foundation` |

## Outputs

- `raw/taxonomi_consolidated_04.xlsx` — `consolidated` (template: `taxonomi_act_q1.xlsx`)
- `raw/taxonomi_ap_foundation_04.xlsx` — `ap_foundation` (template: `foundation_q1.xlsx`)

Both carry the `taxonomi_` prefix + the entity name so it's unambiguous which is
which (the prior `taxonomi_act_*` / `ap_*_act` split was confusing).

Four sheets each, Jan–Apr populated, May–Dec blank. **CF method differs by
entity** and is preserved: consolidated uses `CF Indirect (Actual)` (direct `CF`
blank); ap_foundation uses the direct `CF (Actual)` (`CF Indirect` blank).

## Validation

`build_taxonomi.py --validate` recomputes Jan–Mar from the April raw files and
diffs every cell against the Q1 templates: **"Q1 reproduction clean"** for both
entities (89 + 42 rows, zero label-drift warnings). April reconciliations:

- consolidated `Sales` Apr = **79,317.73** = src `Revenue` Apr (cross-sourced).
- ap_foundation `Cash` (BS) Apr = **2,368,594.74** = CF `Ending Cash Balance`
  Apr — confirms the mislabeled BS/CF headers (below) did not shift the column.
- ap_foundation Apr `Gross Interest Revenue` 128,762.28 / `Funding Cost`
  −99,477.89 → NIR 29,284.39.

## Non-obvious mapping decisions (baked into `taxonomi_mapping.yaml`)

- **Cross-sourced revenue.** The consolidated `Sales` lines `Net Interest
  Revenue` and `Flat Fee` are pulled from the **AP** source (the operating
  conso books them at 0 / only "IT services"). `Other` ← operating "IT services".
- **Sign flips.** ap_foundation `Funding Cost` ← src `Funding cost` ×−1; all
  ap direct-CF outflows ×−1; consolidated `Finance costs` and `Depreciation and
  amortization` ×−1 (src stores them negative).
- **Sums.** consolidated BS `R&D` = R&D Asset + Software; `Financial Assets` =
  subsidiary + loan APF + loan NV + other (post-elimination closing column);
  `Legal reserves` = Reval. reserves BV + NV; `VAT` = VAT + VAT previous years;
  `Tax Payables` = VAT current year + Tax Payables. ap_foundation BS `Other
  receivables` = Other receivables + VAT Receivable. CF Indirect `Other
  payments/proceeds, net` = Other payments + Non-cash Adjustments.
- **Label drift (mapped by value, flagged in YAML):** consolidated `Team
  Development` ← src `Lease`; `Short term loans` ← src `Net Factoring balance`;
  `Accrual expenses` ← src `Other Payables`. ap_foundation `Money out/Other` ←
  src `Non-cash Adjustments` ×−1.
- **Working Capital** (both, derived) = src `Current assets` subtotal − src
  `Current liabilities` subtotal (ties to the cent).
- **BS Conso reads the post-elimination Closing-balance column** (each month is a
  4-column block: period / 2× elimination / closing).

## Source quirks (flagged, not silently fixed)

- **Header years mislabeled.** In `src_ap_foundation_apr.xlsx` the `CF` and `BS`
  sheet header rows read `2025-01…` while the data is **2026** (the `IS` header is
  correct). The builder keys months by **column position**, not the year label,
  so April lands correctly (verified by the cash tie above).
- **Accountant typos** in source labels carried as-is: `Intfrastructure costs`,
  `Contrctors`, `Almcena BV` (sheet tab).

## Intentionally-unmapped source lines (mirror Q1 — confirm with finance)

- **consolidated `BG Invoice`** (operating IS r43, €10k in Jan) is excluded from
  G&A — it's capitalised and appears in CF Indirect Investing (`R&D` / Software
  −10,000). Zero in Apr, so no April impact.
- **ap_foundation `Other payments/ proceeds, net`** (direct-CF r17) is not
  carried; the taxonomi's `Money out/Other` maps to `Non-cash Adjustments`
  instead, per the Q1 model. A small reconciling line — confirm the intent.

## Re-running for the next month (May, …)

1. Drop the two raw statements in `raw/`; rename to `src_consolidated_<mon>.xlsx`
   / `src_ap_foundation_<mon>.xlsx` and update the `file:` fields in the mapping.
2. `--validate` first — it re-anchors Jan–Mar against Q1 and WARNs on any source
   row whose label no longer matches (accountant reorder); fix `src_row` then.
3. Emit: `build_taxonomi.py 2026-05`.
