"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from openpyxl import Workbook


HEADER = ["Data", "Group", "Subgroup", "Jan", "Feb", "Mar", "Apr", "May",
          "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _write_xlsx(path: Path, sheets: dict[str, list[list]]) -> None:
    wb = Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(title=name)
        for row in rows:
            ws.append(row)
    wb.save(path)


@pytest.fixture
def make_test_client(tmp_path: Path, monkeypatch):
    """Factory: build a synthetic client DB and point core.data.query at tmp_path.

    Usage:
        make_test_client(name='demo', config={...}, files={'a.xlsx': {sheet: rows}})
        # → returns tmp_path with clients/demo/{config.yaml, raw/, data/demo.db}
    """
    from core.data.build import build_db
    from core.data import query as query_module

    def _factory(
        *,
        name: str,
        config: dict,
        files: dict[str, dict[str, list[list]]],
    ) -> Path:
        client_dir = tmp_path / "clients" / name
        raw = client_dir / "raw"
        raw.mkdir(parents=True)
        for filename, sheets in files.items():
            _write_xlsx(raw / filename, sheets)
        (client_dir / "config.yaml").write_text(yaml.safe_dump(config))
        build_db(name, tmp_path)
        monkeypatch.setattr(query_module, "_ROOT", tmp_path)
        return tmp_path

    return _factory


@pytest.fixture
def cupffee_test_db(make_test_client) -> Path:
    """A small Cupffee DB with predictable values for query tests.

    Layout (all in 'actual' scenario, 2025):
      IS:
        Sales / Distributors / 220 ml: 100 every month (display_order=0)
        Sales / Distributors / 110 ml: 50 every month  (display_order=1)
        Sales / Direct Sales / 220 ml: 20 every month  (display_order=2)
        Cost of Sales / Materials / Materials: -30 every month (display_order=3)
      BS:
        Cash / Cash / Cash: 1000 in Jan, 1100 in Feb, ... 2100 in Dec
    """
    return make_test_client(
        name="cupffee",
        config={
            "entities": ["cupffee"],
            "financial_sources": [
                {"file": "raw/actuals.xlsx", "year": 2025, "entity": "cupffee"},
            ],
        },
        files={
            "actuals.xlsx": {
                "IS (Actual)": [
                    HEADER,
                    ["Sales", "Distributors", "220 ml", *([100.0] * 12)],
                    ["Sales", "Distributors", "110 ml", *([50.0] * 12)],
                    ["Sales", "Direct Sales", "220 ml", *([20.0] * 12)],
                    ["Cost of Sales", "Materials", "Materials", *([-30.0] * 12)],
                ],
                "BS (Actual)": [
                    HEADER,
                    ["Cash and cash equivalents", "Cash and cash equivalents",
                     "Cash and cash equivalents",
                     *[float(1000 + 100 * i) for i in range(12)]],
                ],
            },
        },
    )


@pytest.fixture
def almacena_test_db(make_test_client) -> Path:
    """Multi-entity test DB so the entity-resolution tests have something to chew on."""
    return make_test_client(
        name="almacena",
        config={
            "entities": ["consolidated", "ap_foundation"],
            "financial_sources": [
                {"file": "raw/cons.xlsx", "year": 2025, "entity": "consolidated"},
                {"file": "raw/ap.xlsx",   "year": 2025, "entity": "ap_foundation"},
            ],
        },
        files={
            "cons.xlsx": {
                "IS (Actual)": [
                    HEADER,
                    ["Sales", "Group", "SG", *([1000.0] * 12)],
                ],
            },
            "ap.xlsx": {
                "IS (Actual)": [
                    HEADER,
                    ["Net Interest Revenue", "Group", "SG", *([-100.0] * 12)],
                ],
            },
        },
    )
