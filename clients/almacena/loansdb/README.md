# Almacena — loansdb

A small, self-contained tool to explore Almacena's **lender funding book** month-by-month,
separate from the monthly deck.

> ⚠️ **DERIVED, not raw.** There is only one lender file (the April export). Every loan
> carries its start + repayment dates, so the monthly book is **reconstructed** by replaying
> each loan's active window. Scope is **2026 (Jan–Apr)** and everything is in **USD** (the
> lender data's native currency). These are derived snapshots, not raw monthly statements.

## What's here

| File | What |
|---|---|
| `loan_book.py` | Reconstruction engine. Reads `../raw/04/lender_loans_accrued_interest.xlsx`, builds the 2026 monthly book + MoM deltas. Shared by the HTML and the notebook. |
| `build_loans_html.py` | Renders `loans.html` (embeds the data + vanilla JS/CSS). |
| `loans.html` | **The dashboard** — open by double-click. Month tabs, a non-scrolling MoM matrix + KPIs, a "what changed" panel, and a filterable/sortable loan table (filters: lender, status, rate band). |
| `loans_exploration.ipynb` | Standalone analyst notebook (monthly book, MoM, lender concentration, maturity wall, rate distribution). Imports `loan_book.py`. |

## How the numbers are derived

For each 2026 month, a loan is **active** if its `[start, repayment]` window overlaps the
calendar month (inclusive day count). Then:

- **Available funds** contribution = `Principal × overlap_days / days_in_month` (time-weighted average drawn principal).
- **Cost of funds / accrued interest** = `Principal × annual_rate × overlap_days / 365`.
- **Blended rate** = principal-weighted average annual rate of the active book.

**Validation:** reconstructing **April** reproduces the source file's own figures exactly —
Available Funds **$15,590,305**, Cost of Funds **$116,409**, **24** active loans, **9.08%**
blended. As an extra check, the reconstructed Available Funds *and* Cost of Funds also match
the platform's reported KPIs (`profitability_main_apr.xlsx`, ÷1.087) for **every** month
Jan–Apr — so the derivation is trustworthy across 2026, not just at the April anchor.

## Use

```bash
uv run python clients/almacena/loansdb/loan_book.py --check      # prove April == source
uv run python clients/almacena/loansdb/build_loans_html.py       # regenerate loans.html
open clients/almacena/loansdb/loans.html                         # the dashboard
# notebook: open loans_exploration.ipynb in Jupyter (not in this project's venv — use your own)
```

## Caveats

- **2026 only.** Loans fully repaid and purged before the April export aren't in the file, so
  the book can't be reliably reconstructed before ~early 2026 — hence the 2026 scope.
- **Derived, not audited.** These are reconstructed snapshots for analysis, not the lender's
  monthly statements. Swap in real monthly snapshots later by pointing `loan_book.py` at them.
- Jupyter isn't installed in the repo venv; run the notebook in your own Jupyter.
