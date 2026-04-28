# Stage 1 — Data Layer (Claude Code prompt, v2)

Build the data layer for the monthly monitoring tool. Cupffee is the first client; the structure must generalize to other clients later (GoodBag, AhaPlay) by adding a sibling client folder.

This stage delivers a SQLite database, a single source loader, and basic query helpers. **No charts in this stage.** Charts come in Stage 2 against this database.

---

## Project structure

```
monitoring/
├── core/
│   ├── __init__.py
│   ├── schema.py           # SQLite DDL
│   ├── loaders/
│   │   ├── __init__.py
│   │   ├── financials.py   # loads taxonomy-format xlsx into financials table
│   │   ├── cup_volumes.py  # placeholder loader, no source yet
│   │   └── country.py      # loader for country_revenue (CSV/xlsx)
│   └── query.py            # helper functions for pulling data out of the DB
├── clients/
│   └── cupffee/
│       ├── config.yaml
│       └── data/
│           ├── raw/             # source files (gitignored)
│           └── cupffee.db       # SQLite output (gitignored)
├── scripts/
│   ├── build_db.py         # one-shot: wipe + recreate <client>.db from raw sources
│   └── validate.py         # runs validation assertions
├── pyproject.toml
└── README.md
```

Use `uv` for dependency management. Pin Python ≥3.11.

---

## Source data shape (canonical taxonomy format)

All financial data — actuals and all budget scenarios — arrives in a single canonical xlsx format. The loader is one function that handles every file.

**Each xlsx file represents one snapshot of a year's data — either a full year or a year-to-date through some month.** Months are always laid out Jan–Dec across columns; if the file is a partial year, later months are simply empty. A file may contain multiple sheets, one per (statement, scenario) combination.

### Filename convention

```
actuals_<yy>.xlsx          full-year actuals    e.g. actuals_25.xlsx
actuals_<mm>-<yy>.xlsx     YTD actuals through month MM   e.g. actuals_03-25.xlsx
budget_<yy>.xlsx           full-year budget snapshot      e.g. budget_25.xlsx
budget_<mm>-<yy>.xlsx      mid-year budget revision       e.g. budget_06-25.xlsx
```

`yy` is two-digit year (`25` = 2025). `mm` is two-digit month (`03` = March), denoting the month through which the file is valid.

The filename is informational — the actual year used for the loader comes from `config.yaml`'s `financial_sources` list, where each file is paired with its year. The `mm` part is also not consumed by the loader; it's purely for human filing. The loader treats `actuals_03-25.xlsx` and `actuals_25.xlsx` identically — both are read as 2025 data, and any empty months simply produce no rows.

When a budget gets revised mid-year, drop the new file (e.g. `budget_06-25.xlsx`) into `data/raw/` and update `config.yaml` to point at it instead of (or in addition to, with the new file *after* the old one) the prior version. The "last loaded wins" rule means values in the newer file override values in the older one for any overlapping cells.

### Sheet naming convention

Pattern: `<STATEMENT> (<SCENARIO>)` or `<STATEMENT> Indirect (<SCENARIO>)`. Examples:
- `IS (Realistic)` → statement = IS, scenario = realistic
- `BS (Pessimistic)` → statement = BS, scenario = pessimistic
- `CF Indirect (Realistic)` → statement = CF, scenario = realistic
- `CF (Realistic)` → empty by convention (direct method not used) — **skip if no data rows**

For an actuals file, expect single-scenario sheets named like `IS (Actual)`, `BS (Actual)`, `CF Indirect (Actual)`.

### Sheet layout

| Col 1 | Col 2 | Col 3 | Col 4 | Col 5 | … | Col 15 |
|-------|-------|-------|-------|-------|---|--------|
| `Data` | `Group` | `Subgroup` | `Jan` | `Feb` | … | `Dec` |
| Sales | Distributors | Cupffee 220 ml | 2550 | 4675 | … | 9384 |
| Sales | Distributors | Cupffee 110 ml | 19240 | 35334 | … | 98168 |

Rules:
- Row 1 is the header. Row 2+ are data rows.
- A row with all-null month values is **skipped** (not loaded as zeros).
- A null cell within a row is loaded as **NULL**, not zero.
- `Data`, `Group`, `Subgroup` are always non-null on a data row. When a category has no further breakdown, `Subgroup` repeats the `Group` value (this is by design — keeps the join shape uniform).
- The year is **not** in the file. It comes from the config (see below).

### Reference: the canonical Cupffee taxonomy

The shape was set by `Taxonomy_budget_q2.xlsx`. It includes:

- **IS**: Sales (× channel × cup size), Cost of Sales, Production Costs, R&D, S&M, G&A, Finance income/costs, Depreciation and amortization, Other non operational revenues, Income tax — flat at the `Data` level, with `Group` / `Subgroup` providing further breakdown.
- **BS**: Non-current assets, Current assets, Cash and cash equivalents, Trade receivables, Equity, Non-Current Liabilities, Current Liabilities, Trade payables, plus a few stored ratios (Working Capital, AR turnover, AP turnover) that the budget tracks as forecast targets.
- **CF (indirect)**: CF from Operating / Investing / Financing Activities, Beginning Cash Balance, % Change in cash, Capex, Gross Fixed assets.

Subtotals (Gross Profit, EBITDA, Total Assets, Net Profit, etc.) are **not** in the source. They will be computed in the chart layer.

---

## Database schema

```sql
CREATE TABLE financials (
    period_date  DATE NOT NULL,
    scenario     TEXT NOT NULL
                 CHECK (scenario IN ('actual','pessimistic','realistic','optimistic')),
    statement    TEXT NOT NULL CHECK (statement IN ('IS','CF','BS')),
    data         TEXT NOT NULL,
    grp          TEXT NOT NULL,
    subgroup     TEXT NOT NULL,
    value        REAL,
    PRIMARY KEY (period_date, scenario, statement, data, grp, subgroup)
);
CREATE INDEX idx_fin_period   ON financials(period_date);
CREATE INDEX idx_fin_scenario ON financials(scenario);
CREATE INDEX idx_fin_data     ON financials(data);

-- Operational tables — separate because dimensions differ
CREATE TABLE cup_volumes (
    period_date  DATE NOT NULL,
    cup_size     TEXT NOT NULL,        -- '110ml' | '220ml' | (extensible)
    value        INTEGER,              -- units
    PRIMARY KEY (period_date, cup_size)
);

CREATE TABLE country_revenue (
    period_date  DATE NOT NULL,
    country      TEXT NOT NULL,
    period_type  TEXT NOT NULL CHECK (period_type IN ('monthly','ltm')),
    value        REAL,                 -- in EUR (BGN converted at fixed rate from config)
    PRIMARY KEY (period_date, country, period_type)
);
```

**Sign convention**: store values exactly as they appear in the source. Cash outflows negative in CF, costs positive in IS, etc.

**No `accounts` taxonomy table.** Hierarchy lives in the (`data`, `grp`, `subgroup`) columns of `financials`. Aggregations are done at query time via `GROUP BY`.

**Period storage**: ISO `DATE`, always first-of-month. `Jan` column for year=2025 → `2025-01-01`.

---

## Loader specification (`core/loaders/financials.py`)

A single function:

```python
def load_taxonomy_xlsx(path: Path, year: int) -> Iterable[FinancialRow]:
    """
    Iterates every (statement, scenario) sheet in the file and yields rows.
    - Sheet name pattern: '<STATEMENT> (<SCENARIO>)' or '<STATEMENT> Indirect (<SCENARIO>)'.
    - Sheets where no data row has any value are skipped.
    - Rows where all monthly values are null are skipped.
    - Cells with null values are emitted with value=None (NULL in DB).
    - Whitespace is stripped from data/grp/subgroup; values left untouched.
    """
```

Sheet-name parser handles three patterns:
1. `IS (Realistic)` → `('IS', 'realistic')`
2. `CF Indirect (Realistic)` → `('CF', 'realistic')`
3. `CF (Realistic)` → check if rows have data; if not, skip; otherwise also `('CF', 'realistic')`

Scenario is lowercased. Validate against the schema CHECK; raise on unknown scenario names so typos in sheet names fail loud.

The loader is **idempotent** — running `build_db.py` twice produces the same DB.

---

## Operational loaders

### `core/loaders/cup_volumes.py`

Placeholder. Function exists, accepts a path, returns empty iterator if path is null/missing. When the accounting export adds cup volume data, populate this loader. For MVP, schema accommodates it but no data needs to flow.

### `core/loaders/country.py`

Reads `Top_6_Countries_Invoiced_-_LTM_.csv` and `Top_6_Countries_Invoiced_-_Last_Month_.xlsx` if configured. Both have a `Billing Country` column and `Total Amount` column with values in BGN (e.g., `"BGN 100,848.78"`). Loader strips the prefix, parses the number, converts to EUR using the fixed peg from config, and yields rows. The LTM file → `period_type='ltm'`; the monthly file → `period_type='monthly'`.

For LTM rows, set `period_date` to the first-of-month for the LTM period start (i.e., the month that begins the LTM window — derived from `as_of_date` in config minus 12 months).

For MVP, the loaders should run if files exist in `data/raw/`, otherwise no-op.

---

## Query helpers (`core/query.py`)

Minimum useful set. These are the **only things Stage 2 imports** — the DB is hidden behind them.

```python
get_value(data: str, grp: str, subgroup: str, period_date, scenario='actual') -> float | None

get_line(data: str, grp: str = None, subgroup: str = None,
         scenarios=('actual','realistic'), periods=None) -> pd.DataFrame
    # Returns long-format DataFrame: [period_date, scenario, data, grp, subgroup, value]

get_statement(statement: str, period_date,
              scenarios=('actual','realistic')) -> pd.DataFrame
    # Returns full statement (all rows) for that period in long format,
    # ordered by data → grp → subgroup as they appear in the source

get_aggregation(data: str, period_date, scenario='actual', level: str='data') -> float
    # level='data' sums everything matching `data`
    # level='grp' returns dict-like {grp: sum}, also useful for donut charts
    # level='subgroup' returns dict-like {(grp, subgroup): value}

get_trend(data: str, grp: str = None, subgroup: str = None,
          scenario='actual', start_date=None, end_date=None) -> pd.Series
    # Time series for charting

ytd(data: str, year: int, grp=None, subgroup=None, scenario='actual',
    through_month: int=12) -> float

to_csv(query_result, path: Path) -> None
    # Convenience for pulling data out of the DB into Excel for manual transformations
```

Donut chart data shape note: chart 5.3/5.4 wants channel-level breakdown of Sales. The query is `get_aggregation(data='Sales', period_date='2025-12-01', level='grp')`.

---

## Config (`clients/cupffee/config.yaml`)

```yaml
client_name: Cupffee
fiscal_year_start_month: 1
currency: EUR
bgn_to_eur_rate: 1.95583    # fixed peg, used for country_revenue conversion
as_of_date: 2025-12-01      # latest closed month; drives LTM windowing for country data

# Each entry is one xlsx file in canonical taxonomy format.
# The loader uses 'year' to anchor month columns to ISO dates.
# Files later in the list override earlier files on cell conflicts.
financial_sources:
  - file: data/raw/actuals_24.xlsx
    year: 2024
  - file: data/raw/actuals_25.xlsx
    year: 2025
  - file: data/raw/budget_25.xlsx
    year: 2025

# Optional sources — load if present, no-op otherwise
cup_volumes_source: null
country_revenue_ltm_source: null
country_revenue_monthly_source: null

# Brand placeholder — used in Stage 2
brand:
  primary: "#2A625E"
  accent: "#E67D5A"
  budget: "#D4A24C"
  font_header: "Calibri"
  font_body: "Calibri"
```

If two files cover the same `(period_date, scenario, statement, data, grp, subgroup)` tuple, the **last one loaded wins**. Document this in the README so the user knows the load order from `config.yaml` matters for overrides.

---

## Validation (`scripts/validate.py`)

Run after `build_db.py`. Assert these against the loaded data — values cross-checked from `year-mar.xlsx` (the canonical 2025 actuals reference).

| Query | Expected (EUR) |
|-------|----------------|
| `get_aggregation('Sales', '2025-12-01', 'actual', level='data')` | 124,061.80 |
| `get_value('Sales', 'Distributors', 'Cupffee 220 ml', '2025-12-01', 'actual')` | 81,551.52 |
| `get_value('Sales', 'Distributors', 'Cupffee 110 ml', '2025-12-01', 'actual')` | 15,350.40 |
| `get_aggregation('Sales', '2025-03-01', 'actual', level='data')` | 50,592.64 |
| `ytd('Sales', 2025, scenario='actual')` | 1,043,795.81 |
| `get_value('Cost of Sales', 'Materials', 'Materials', '2025-12-01', 'actual')` | 13,815.54 |
| `get_value('Cash and cash equivalents', 'Cash and cash equivalents', 'Cash and cash equivalents', '2025-12-01', 'actual')` | 258,651.54 |
| `get_value('Cash Flow from Operating Activities', 'Cash from Sales', 'Cash from Sales', '2025-12-01', 'actual')` | 67,466.55 |

Tolerance: **1 EUR** (the source data has minor float artifacts).

For budget validation: pick 3-5 cells from the loaded budget file, verify them manually before committing the assertion list. Use the `realistic` scenario.

---

## Build script (`scripts/build_db.py`)

Sequence:
1. Read `config.yaml` for the target client.
2. Wipe existing `<client>.db`.
3. Create schema.
4. For each `financial_sources` entry: run `load_taxonomy_xlsx(path, year)` and bulk-insert into `financials`.
5. Run cup_volumes and country loaders if their sources are configured.
6. Print summary: row counts per table, list of any sheets that were skipped (with reason).
7. Run validation assertions.
8. Exit non-zero on any validation failure or unrecognized scenario name.

CLI: `python scripts/build_db.py cupffee` (positional arg = client folder name).

---

## Out of scope for Stage 1

- Chart primitives (Stage 2)
- Derived metrics / KPIs (Gross Profit, EBITDA, ratios — deferred to chart layer)
- `prior_period` / `prior_year` materialization (computed at query time by lagging)
- Cup volumes ingestion logic (parser stub only)
- Snapshot/version control of the DB (single live DB per client; rebuild on every run)
- Multi-currency support (Cupffee is EUR-only)

---

## Pass criteria

- `python scripts/build_db.py cupffee` runs clean against the source files in `data/raw/` and produces `cupffee.db`.
- `python scripts/validate.py cupffee` passes all assertions within tolerance.
- A second person can run `from core.query import get_statement; get_statement('IS', '2025-12-01')` and get back a properly ordered IS for December 2025 with both `actual` and `realistic` columns.
- README documents: how to add a new month of data (replace the relevant year file, rerun build), how to onboard a new client (new folder under `clients/`, new config), and how to handle a previous-month correction (replace the year file, rerun build — full rebuild handles it).