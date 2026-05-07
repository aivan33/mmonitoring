"""Write a new month's column into a copy of the prior taxonomi-actual xlsx.

Bridges ``core/loaders/mr.py`` (MR → keyed values) and the existing taxonomi
format. Uses ``openpyxl`` load-modify-save so cell formatting, column widths,
and other workbook metadata from the prior month carry over untouched.

Two writes happen:
    1. MR-sourced cells (per ``mapping.yaml``) get the values from
       ``extract_month``.
    2. Four derived KPI rows are computed and written:
       - ``Gross Fixed assets`` (CF Indirect): R&D Asset + PP&E + Business Equipment
       - ``Working Capital`` (BS): Total Current Assets − Total Current Liabilities
       - ``Account receivable turnover`` (BS): Sales / Avg(begin TR, end TR)
       - ``Accounts payable turnover`` (BS): (CoS + OPEX − Personnel) / Avg(begin TP, end TP)

       Begin-period balances (TR, TP) are read from the prior taxonomi
       month. KPIs become ``None`` when the denominator is zero or when
       the begin-period balance is unavailable (e.g. Jan with no prior-year
       Dec data).
"""

from __future__ import annotations

import logging
from pathlib import Path

from openpyxl import load_workbook

logger = logging.getLogger(__name__)


# Taxonomi sheet name per statement code.
_SHEET_FOR: dict[str, str] = {
    "IS": "IS (Actual)",
    "CF": "CF Indirect (Actual)",
    "BS": "BS (Actual)",
}


# Cells that should be stored as floats (ratios), not rounded to integers.
# Identified from the existing taxonomi convention.
_FLOAT_CELLS: frozenset[tuple[str, str, str]] = frozenset({
    ("Accounts payable turnover", "Accounts payable turnover", "Accounts payable turnover"),
    ("Account receivable turnover", "Account receivable turnover", "Account receivable turnover"),
    ("% Change in cash", "% Change in cash", "% Change in cash"),
})


# Keys used by the KPI-derivation step. Centralised so the formulas read clean.
_KEY_RD_ASSET     = ("Non-current assets", "Non-tangible fixed assets", "Research and Development Asset")
_KEY_PPE          = ("Non-current assets", "Tangible fixed assets", "PP&E")
_KEY_BUS_EQ       = ("Non-current assets", "Tangible fixed assets", "Business Equipment")
_KEY_PREPAID      = ("Current assets", "Prepaid expenses", "Prepaid expenses")
_KEY_LOANS_CA     = ("Current assets", "Loans (other negotiable instruments)", "Loans (other negotiable instruments)")
_KEY_OTHER_REC    = ("Current assets", "Other receivables", "Other receivables")
_KEY_INVENTORY    = ("Current assets", "Inventory", "Inventory")
_KEY_CASH         = ("Cash and cash equivalents", "Cash and cash equivalents", "Cash and cash equivalents")
_KEY_TR           = ("Trade receivables", "Trade receivables", "Trade receivables")
_KEY_CL_PERSONNEL = ("Current Liabilities", "Payables to personnel", "Payables to personnel")
_KEY_CL_OTHER     = ("Current Liabilities", "Other payables", "Other payables")
_KEY_CL_LOANS     = ("Current Liabilities", "Loans (other negotiable instruments)", "Loans (other negotiable instruments)")
_KEY_TP           = ("Trade payables", "Trade payables", "Trade payables")
_KEY_GFA          = ("Gross Fixed assets", "Gross Fixed assets", "Gross Fixed assets")
_KEY_WC           = ("Working Capital", "Working Capital", "Working Capital")
_KEY_ART          = ("Account receivable turnover", "Account receivable turnover", "Account receivable turnover")
_KEY_APT          = ("Accounts payable turnover", "Accounts payable turnover", "Accounts payable turnover")

# Personnel = sum of all "Total Payroll" rows on the IS.
_PERSONNEL_KEYS = (
    ("Cost of Sales", "Total Payroll", "Total Payroll"),
    ("R&D", "Total Payroll", "Germany"),
    ("R&D", "Total Payroll", "Serbia"),
    ("S&M", "Total Payroll", "Total Payroll"),
    ("G&A", "Total Payroll", "Total Payroll"),
)


def populate_taxonomi(
    prev_taxonomi: str | Path,
    mr_extracts: dict[str, dict[tuple[str, str, str], float | None]],
    year: int,
    month: int,
    out_path: str | Path,
) -> None:
    """Copy ``prev_taxonomi`` and overwrite the new month's column with
    MR-sourced values plus derived KPIs.

    Args:
        prev_taxonomi: path to prior month's taxonomi-actual xlsx.
        mr_extracts: ``{statement_code: {(data, grp, subgroup): value}}``
            from ``core/loaders/mr.extract_month``. Statement codes:
            ``'IS' | 'CF' | 'BS'``.
        year, month: target period.
        out_path: where to save the populated xlsx.

    Behavior:
        - Target column = ``3 + month`` (Jan=4, ..., Dec=15).
        - MR-sourced numeric cells round to integers; ratio cells (AP/AR
          turnover, % Change in cash) are stored as floats.
        - Derived KPI rows are computed using MR Mar values plus the
          previous month's Trade Receivables / Trade Payables read from
          ``prev_taxonomi``.
        - Idempotent: same inputs produce the same output content.
    """
    out_path = Path(out_path)
    target_col = 3 + month  # Jan=4, ..., Dec=15

    norm_extracts = {
        stmt: {tuple(_strip(p) for p in key): val for key, val in d.items()}
        for stmt, d in mr_extracts.items()
    }

    wb = load_workbook(prev_taxonomi)
    try:
        # Step 1: derive KPIs from MR values + prior-month begin balances.
        derived = _derive_kpis(wb, norm_extracts, month)
        # Merge into the right per-statement extract dict so the cell-level
        # writer can put each value on its own sheet.
        if "CF" not in norm_extracts:
            norm_extracts["CF"] = {}
        if "BS" not in norm_extracts:
            norm_extracts["BS"] = {}
        norm_extracts["CF"][_KEY_GFA] = derived["gfa"]
        norm_extracts["BS"][_KEY_WC]  = derived["wc"]
        norm_extracts["BS"][_KEY_ART] = derived["ar_turnover"]
        norm_extracts["BS"][_KEY_APT] = derived["ap_turnover"]

        # Step 2: write per-sheet.
        for stmt_code, sheet_name in _SHEET_FOR.items():
            if sheet_name not in wb.sheetnames:
                logger.warning(
                    "prev taxonomi has no sheet %r — skipping %s.",
                    sheet_name, stmt_code,
                )
                continue
            ws = wb[sheet_name]
            extracts = norm_extracts.get(stmt_code, {})
            _populate_sheet(ws, extracts, target_col, sheet_name)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        wb.save(out_path)
    finally:
        wb.close()


# --- KPI derivation --------------------------------------------------------

def _derive_kpis(wb, mr_extracts: dict, month: int) -> dict[str, float | None]:
    """Compute the four derived KPIs for the target month.

    Returns ``{'gfa', 'wc', 'ar_turnover', 'ap_turnover'}``. Any can be
    ``None`` when components are missing.
    """
    is_e = mr_extracts.get("IS", {})
    bs_e = mr_extracts.get("BS", {})

    def g(d, key):
        v = d.get(key)
        return v if isinstance(v, (int, float)) else 0.0

    # GFA = R&D Asset + PP&E + Business Equipment
    gfa = g(bs_e, _KEY_RD_ASSET) + g(bs_e, _KEY_PPE) + g(bs_e, _KEY_BUS_EQ)

    # WC = Total Current Assets − Total Current Liabilities
    total_ca = (g(bs_e, _KEY_PREPAID) + g(bs_e, _KEY_LOANS_CA)
                + g(bs_e, _KEY_OTHER_REC) + g(bs_e, _KEY_INVENTORY)
                + g(bs_e, _KEY_CASH) + g(bs_e, _KEY_TR))
    total_cl = (g(bs_e, _KEY_CL_PERSONNEL) + g(bs_e, _KEY_CL_OTHER)
                + g(bs_e, _KEY_CL_LOANS) + g(bs_e, _KEY_TP))
    wc = total_ca - total_cl

    # Begin-period Trade Receivables / Trade Payables read from the prior
    # month's column of the taxonomi (the file we're copying).
    begin_tr = _read_prior_month(wb, "BS (Actual)", _KEY_TR, month)
    begin_tp = _read_prior_month(wb, "BS (Actual)", _KEY_TP, month)

    # AR Turnover = Sales / Avg(begin AR, end AR)
    end_tr = g(bs_e, _KEY_TR)
    sales_total = sum(g(is_e, k) for k in is_e if k[0] == "Sales")
    avg_ar = ((begin_tr or 0) + end_tr) / 2 if begin_tr is not None else None
    if avg_ar is None or avg_ar == 0:
        ar_turnover = None
    else:
        ar_turnover = sales_total / avg_ar

    # AP Turnover = (CoS + OPEX − Personnel) / Avg(begin TP, end TP)
    end_tp = g(bs_e, _KEY_TP)
    cos_total = sum(g(is_e, k) for k in is_e if k[0] == "Cost of Sales")
    opex_total = sum(g(is_e, k) for k in is_e if k[0] in ("R&D", "S&M", "G&A"))
    personnel = sum(g(is_e, k) for k in _PERSONNEL_KEYS)
    avg_tp = ((begin_tp or 0) + end_tp) / 2 if begin_tp is not None else None
    if avg_tp is None or avg_tp == 0:
        ap_turnover = None
    else:
        ap_turnover = (cos_total + opex_total - personnel) / avg_tp

    return {
        "gfa": gfa,
        "wc": wc,
        "ar_turnover": ar_turnover,
        "ap_turnover": ap_turnover,
    }


def _read_prior_month(wb, sheet_name: str,
                      key: tuple[str, str, str], month: int) -> float | None:
    """Read the value at ``key`` from the prior month's column of
    ``sheet_name``. Returns ``None`` if month==1 (no prior month in the
    fiscal year), if the row isn't found, or if the cell is empty."""
    if month <= 1:
        return None
    if sheet_name not in wb.sheetnames:
        return None
    ws = wb[sheet_name]
    prior_col = 3 + (month - 1)
    for r in range(2, ws.max_row + 1):
        d = _strip(ws.cell(r, 1).value)
        g = _strip(ws.cell(r, 2).value)
        s = _strip(ws.cell(r, 3).value)
        if (d, g, s) == key:
            v = ws.cell(r, prior_col).value
            return float(v) if isinstance(v, (int, float)) else None
    return None


# --- per-sheet writer ------------------------------------------------------

def _populate_sheet(ws, extracts, target_col: int, sheet_name: str) -> None:
    for r in range(2, ws.max_row + 1):
        d = ws.cell(r, 1).value
        g = ws.cell(r, 2).value
        s = ws.cell(r, 3).value
        if d is None and g is None and s is None:
            continue
        key = (_strip(d), _strip(g), _strip(s))
        if key not in extracts:
            logger.warning(
                "taxonomi %s row %d %r has no MR mapping — leaving cell unchanged.",
                sheet_name, r, key,
            )
            continue
        value = extracts[key]
        if value is None:
            ws.cell(r, target_col).value = None
        elif key in _FLOAT_CELLS:
            ws.cell(r, target_col).value = float(value)
        else:
            ws.cell(r, target_col).value = round(value)


def _strip(v):
    if isinstance(v, str):
        return v.strip()
    return v
