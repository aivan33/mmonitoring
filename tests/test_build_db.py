"""Tests for core.build.build_db — the orchestrator behind scripts/build_db.py."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
import yaml
from openpyxl import Workbook

from core.build import build_db


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


def _setup_client(
    base: Path,
    client: str,
    *,
    config: dict,
    files: dict[str, dict[str, list[list]]],
) -> None:
    """Create a client directory with config.yaml and raw xlsx files."""
    client_dir = base / "clients" / client
    raw_dir = client_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for filename, sheets in files.items():
        _write_xlsx(raw_dir / filename, sheets)
    (client_dir / "config.yaml").write_text(yaml.safe_dump(config))


class TestBuildDb:
    def test_creates_db_at_expected_path(self, tmp_path: Path) -> None:
        _setup_client(tmp_path, "demo",
            config={
                "client_name": "Demo",
                "currency": "EUR",
                "entities": ["demo"],
                "financial_sources": [
                    {"file": "raw/a.xlsx", "year": 2025, "entity": "demo"},
                ],
            },
            files={
                "a.xlsx": {
                    "IS (Actual)": [HEADER,
                        ["Sales", "Distributors", "X", *([100.0] * 12)]],
                },
            },
        )
        build_db("demo", tmp_path)
        assert (tmp_path / "clients/demo/data/demo.db").exists()

    def test_inserts_rows_from_all_sources(self, tmp_path: Path) -> None:
        _setup_client(tmp_path, "demo",
            config={
                "entities": ["demo"],
                "financial_sources": [
                    {"file": "raw/a.xlsx", "year": 2025, "entity": "demo"},
                    {"file": "raw/b.xlsx", "year": 2026, "entity": "demo"},
                ],
            },
            files={
                "a.xlsx": {"IS (Actual)": [HEADER,
                    ["Sales", "g", "x", *([100.0] * 12)]]},
                "b.xlsx": {"IS (Realistic)": [HEADER,
                    ["Sales", "g", "y", *([200.0] * 12)]]},
            },
        )
        summary = build_db("demo", tmp_path)
        with sqlite3.connect(tmp_path / "clients/demo/data/demo.db") as conn:
            count = conn.execute("SELECT COUNT(*) FROM financials").fetchone()[0]
        # 12 months * 2 source rows = 24
        assert count == 24
        assert summary["financials_rows"] == 24

    def test_idempotent_same_count_on_rerun(self, tmp_path: Path) -> None:
        _setup_client(tmp_path, "demo",
            config={
                "entities": ["demo"],
                "financial_sources": [
                    {"file": "raw/a.xlsx", "year": 2025, "entity": "demo"},
                ],
            },
            files={"a.xlsx": {"IS (Actual)": [HEADER,
                ["Sales", "g", "x", *([100.0] * 12)]]}},
        )
        first = build_db("demo", tmp_path)
        second = build_db("demo", tmp_path)
        assert first["financials_rows"] == second["financials_rows"]

    def test_default_currency_is_eur(self, tmp_path: Path) -> None:
        # Source omits currency → defaults to EUR; no fx_rate needed.
        _setup_client(tmp_path, "demo",
            config={
                "entities": ["demo"],
                "financial_sources": [
                    {"file": "raw/a.xlsx", "year": 2025, "entity": "demo"},
                ],
            },
            files={"a.xlsx": {"IS (Actual)": [HEADER,
                ["Sales", "g", "x", *([100.0] * 12)]]}},
        )
        build_db("demo", tmp_path)
        with sqlite3.connect(tmp_path / "clients/demo/data/demo.db") as conn:
            value = conn.execute(
                "SELECT value FROM financials WHERE period_date='2025-01-01'"
            ).fetchone()[0]
        assert value == 100.0  # EUR pass-through

    def test_bgn_currency_uses_config_rate(self, tmp_path: Path) -> None:
        _setup_client(tmp_path, "demo",
            config={
                "entities": ["demo"],
                "bgn_to_eur_rate": 1.95583,
                "financial_sources": [
                    {"file": "raw/a.xlsx", "year": 2025, "entity": "demo",
                     "currency": "BGN"},
                ],
            },
            files={"a.xlsx": {"IS (Actual)": [HEADER,
                ["Sales", "g", "x", *([195.583] * 12)]]}},
        )
        build_db("demo", tmp_path)
        with sqlite3.connect(tmp_path / "clients/demo/data/demo.db") as conn:
            value = conn.execute(
                "SELECT value FROM financials WHERE period_date='2025-01-01'"
            ).fetchone()[0]
        assert value == pytest.approx(100.0)  # 195.583 / 1.95583

    def test_invalid_entity_in_source_raises(self, tmp_path: Path) -> None:
        _setup_client(tmp_path, "demo",
            config={
                "entities": ["demo"],
                "financial_sources": [
                    {"file": "raw/a.xlsx", "year": 2025, "entity": "ghost"},
                ],
            },
            files={"a.xlsx": {"IS (Actual)": [HEADER,
                ["Sales", "g", "x", *([1.0] * 12)]]}},
        )
        with pytest.raises(ValueError, match="ghost"):
            build_db("demo", tmp_path)

    def test_last_loaded_wins_via_insert_or_replace(self, tmp_path: Path) -> None:
        # Two sources hit the same PK; second source's value must win.
        _setup_client(tmp_path, "demo",
            config={
                "entities": ["demo"],
                "financial_sources": [
                    {"file": "raw/old.xlsx", "year": 2025, "entity": "demo"},
                    {"file": "raw/new.xlsx", "year": 2025, "entity": "demo"},
                ],
            },
            files={
                "old.xlsx": {"IS (Actual)": [HEADER,
                    ["Sales", "g", "x", *([100.0] * 12)]]},
                "new.xlsx": {"IS (Actual)": [HEADER,
                    ["Sales", "g", "x", *([999.0] * 12)]]},
            },
        )
        build_db("demo", tmp_path)
        with sqlite3.connect(tmp_path / "clients/demo/data/demo.db") as conn:
            value = conn.execute(
                "SELECT value FROM financials WHERE period_date='2025-01-01'"
            ).fetchone()[0]
        assert value == 999.0

    def test_summary_lists_per_source_rows(self, tmp_path: Path) -> None:
        _setup_client(tmp_path, "demo",
            config={
                "entities": ["demo"],
                "financial_sources": [
                    {"file": "raw/a.xlsx", "year": 2025, "entity": "demo"},
                ],
            },
            files={"a.xlsx": {"IS (Actual)": [HEADER,
                ["Sales", "g", "x", *([10.0] * 12)]]}},
        )
        summary = build_db("demo", tmp_path)
        assert "sources" in summary
        assert summary["sources"][0]["file"] == "raw/a.xlsx"
        assert summary["sources"][0]["rows"] == 12
