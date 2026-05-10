"""Tests for core.data.build.build_db — the orchestrator behind scripts/build_db.py."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
import yaml
from openpyxl import Workbook

from core.data.build import build_db


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
                "currencies": {"BGN": 1.95583},
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

    def test_summary_records_provenance_per_source(self, tmp_path: Path) -> None:
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
        src = summary["sources"][0]
        assert src["file"] == "raw/a.xlsx"
        assert "sha256" in src and len(src["sha256"]) == 64
        assert "mtime" in src and "T" in src["mtime"]   # ISO datetime
        assert "size_bytes" in src and src["size_bytes"] > 0

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


class TestRegistryTagging:
    """Build pipeline must tag rows whose triplet is in the client's
    aggregate_formulas.yaml as is_aggregate=1."""

    def _setup(self, tmp_path: Path, *, registry_yaml: str | None) -> Path:
        # Burn = -Sales, so leaf 50 + sign -1 = parsed -50 → R4 passes.
        _setup_client(tmp_path, "demo",
            config={
                "entities": ["demo"],
                "financial_sources": [
                    {"file": "raw/a.xlsx", "year": 2025, "entity": "demo"},
                ],
            },
            files={"a.xlsx": {"IS (Actual)": [HEADER,
                ["Sales", "g", "leaf", *([50.0] * 12)],
                ["KPI", "Burn", "Gross", *([-50.0] * 12)],
            ]}},
        )
        if registry_yaml is not None:
            (tmp_path / "clients/demo/aggregate_formulas.yaml").write_text(
                registry_yaml,
            )
        return tmp_path / "clients/demo/data/demo.db"

    def test_no_registry_keeps_all_rows_as_leaves(self, tmp_path: Path) -> None:
        db = self._setup(tmp_path, registry_yaml=None)
        build_db("demo", tmp_path)
        with sqlite3.connect(db) as conn:
            distinct = conn.execute(
                "SELECT DISTINCT is_aggregate FROM financials"
            ).fetchall()
        assert distinct == [(0,)]

    def test_registered_row_tagged_as_aggregate(self, tmp_path: Path) -> None:
        db = self._setup(tmp_path, registry_yaml="""
gross_burn:
  taxonomi: ["KPI", "Burn", "Gross"]
  leaves:
    - {data: "Sales", sign: -1}
""")
        build_db("demo", tmp_path)
        with sqlite3.connect(db) as conn:
            tagged = conn.execute(
                "SELECT data, grp, subgroup, is_aggregate FROM financials "
                "WHERE is_aggregate=1 GROUP BY data, grp, subgroup"
            ).fetchall()
            untagged = conn.execute(
                "SELECT data, grp, subgroup FROM financials "
                "WHERE is_aggregate=0 GROUP BY data, grp, subgroup"
            ).fetchall()
        assert tagged == [("KPI", "Burn", "Gross", 1)]
        assert untagged == [("Sales", "g", "leaf")]

    def test_registered_aggregate_missing_from_data_raises(
        self, tmp_path: Path,
    ) -> None:
        # Registers an aggregate whose triplet doesn't appear in source.
        self._setup(tmp_path, registry_yaml="""
ghost:
  taxonomi: ["KPI", "Ghost", "Missing"]
  leaves:
    - {data: "Sales", sign: 1}
""")
        with pytest.raises(ValueError, match="ghost"):
            build_db("demo", tmp_path)


class TestLoadReport:
    """Every successful build emits clients/<client>/data/<client>.load_report.md.
    Failed integrity checks still emit the report, then raise."""

    def _setup(self, tmp_path: Path) -> None:
        _setup_client(tmp_path, "demo",
            config={
                "entities": ["demo"],
                "financial_sources": [
                    {"file": "raw/a.xlsx", "year": 2025, "entity": "demo"},
                ],
            },
            files={"a.xlsx": {"IS (Actual)": [HEADER,
                ["Sales", "g", "leaf", *([100.0] * 12)]]}},
        )

    def test_writes_report_alongside_db(self, tmp_path: Path) -> None:
        self._setup(tmp_path)
        build_db("demo", tmp_path)
        report_path = tmp_path / "clients/demo/data/demo.load_report.md"
        assert report_path.exists()

    def test_report_lists_source_filename_and_sha(self, tmp_path: Path) -> None:
        self._setup(tmp_path)
        build_db("demo", tmp_path)
        body = (tmp_path / "clients/demo/data/demo.load_report.md").read_text()
        assert "raw/a.xlsx" in body
        assert "sha256" in body.lower() or "sha" in body.lower()

    def test_report_includes_findings_section(self, tmp_path: Path) -> None:
        self._setup(tmp_path)
        build_db("demo", tmp_path)
        body = (tmp_path / "clients/demo/data/demo.load_report.md").read_text()
        # Even if there are zero findings, the section is present so the
        # reader knows the check ran.
        assert "Integrity" in body or "findings" in body.lower()

    def test_r4_failure_raises_and_still_writes_report(
        self, tmp_path: Path,
    ) -> None:
        # Set up a registered aggregate whose stored value is wrong.
        _setup_client(tmp_path, "demo",
            config={
                "entities": ["demo"],
                "financial_sources": [
                    {"file": "raw/a.xlsx", "year": 2025, "entity": "demo"},
                ],
            },
            files={"a.xlsx": {"IS (Actual)": [HEADER,
                ["Sales", "g", "leaf",         *([100.0] * 12)],
                ["KPI",   "Burn", "Gross",     *([-9999.0] * 12)],  # wrong
            ]}},
        )
        (tmp_path / "clients/demo/aggregate_formulas.yaml").write_text("""
gross_burn:
  taxonomi: ["KPI", "Burn", "Gross"]
  leaves:
    - {data: "Sales", sign: -1}
""")
        report_path = tmp_path / "clients/demo/data/demo.load_report.md"
        with pytest.raises(Exception):
            build_db("demo", tmp_path)
        # Report must still exist so the user can see what failed.
        assert report_path.exists()
        assert "R4" in report_path.read_text()
