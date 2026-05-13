"""Extract 2025 Almacena KPIs from the legacy dashboard JSON into a
kpi_wide xlsx the monitoring loader can consume.

Source: _archive/dashboard/dashboard/dist/data/dashboard_data.json
Output: clients/almacena/raw/almacena_2025_kpis.xlsx

The legacy JSON stores both USD and EUR variants. We take the EUR side
verbatim since the monitoring DB is EUR-native. KPI names are normalized
to match the 2026 Q1 file (e.g. "Cash Drag" → "Cash Drag %") so chart
specs can reference one name across years.

Run from repo root:
    uv run python clients/almacena/one_offs/build_2025_kpis.py
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from openpyxl import Workbook


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC = REPO_ROOT / "_archive/dashboard/dashboard/dist/data/dashboard_data.json"
OUT = REPO_ROOT / "clients/almacena/raw/almacena_2025_kpis.xlsx"


# Map legacy 2025 KPI names → 2026 Q1 names so the same chart spec works
# across both years. Names not in the map pass through unchanged.
RENAME = {
    "Cash Drag": "Cash Drag %",
    "Avg Days Outstanding": "Average Days Outstanding",
    "Avg Portfolio Outstanding": "Average Portfolio Outstanding",
    "Accrued Interests": "Accrued Interest",
    "Cost of Funds (Accrued)": "Cost of Funds",
    "Warehouse Destination Fees": "Handling & Warehouse Destination Fees",
    "Warehouse Destination Costs": "Handling & Warehouse Destination Costs",
}

# KPIs to skip — not real KPIs or not needed.
SKIP = {"exch_rate", "nan"}


def _parse_period(label: str) -> dt.date:
    """'Jan-25' → date(2025, 1, 1)."""
    month_abbr, yr = label.split("-")
    months = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
    }
    return dt.date(2000 + int(yr), months[month_abbr], 1)


def main() -> None:
    payload = json.loads(SRC.read_text())
    periods = [_parse_period(p) for p in payload["periods"]]
    values = payload["values_eur"]  # use EUR values directly

    wb = Workbook()
    ws = wb.active
    ws.title = "KPIs"

    # Header row: ["", Jan 25, Feb 25, ..., Dec 25]
    header = [""] + [p.strftime("%b %y") for p in periods]
    ws.append(header)

    # Data rows: one KPI per row
    for kpi_name, series in values.items():
        if kpi_name in SKIP:
            continue
        out_name = RENAME.get(kpi_name, kpi_name)
        row = [out_name] + [v if v is not None else None for v in series]
        ws.append(row)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"wrote {OUT.relative_to(REPO_ROOT)} ({len(periods)} months, "
          f"{len(values) - len(SKIP & values.keys())} KPIs)")


if __name__ == "__main__":
    main()
