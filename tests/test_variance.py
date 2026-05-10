"""Tests for ``core/report/variance.py``."""

from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path

import pytest

from core.data import schema
from core.report import variance


@pytest.fixture
def synth_client(tmp_path: Path, monkeypatch):
    """Build a synthetic client tree under tmp_path with a fresh DB.

    Returns a helper that takes (config_dict, rows) and creates the
    config.yaml + DB so compute_variance can be called against it.
    """
    monkeypatch.setattr(variance, "_ROOT", tmp_path)

    def _build(client: str, config: dict, rows: list[tuple]) -> None:
        cdir = tmp_path / "clients" / client
        (cdir / "data").mkdir(parents=True, exist_ok=True)
        (cdir / "config.yaml").write_text(_dump_yaml(config))
        db = cdir / "data" / f"{client}.db"
        schema.wipe_and_create(db)
        with sqlite3.connect(db) as conn:
            conn.executemany(
                "INSERT INTO financials VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
            conn.commit()

    return _build


def _dump_yaml(d: dict) -> str:
    """Tiny inline YAML dumper to avoid importing yaml at test scope."""
    import yaml as _y
    return _y.safe_dump(d)


# Each row tuple is (period_date, entity, scenario, statement, data, grp,
#                    subgroup, display_order, value, is_aggregate)
def _row(period, entity, scenario, statement, data, grp, subgroup,
         order, value, is_agg=0):
    return (period, entity, scenario, statement, data, grp, subgroup,
            order, value, is_agg)


def test_basic_actual_vs_budget(synth_client):
    """One IS row, actual + realistic budget present in March → variance."""
    synth_client("c1",
        {"entities": ["e1"], "reporting": {
            "variance_thresholds": {"flag_pct": 20, "flag_eur": 10000},
        }},
        [
            _row("2026-03-01", "e1", "actual",     "IS", "Sales", "g", "x", 1, 1000),
            _row("2026-03-01", "e1", "realistic",  "IS", "Sales", "g", "x", 1, 800),
        ],
    )
    res = variance.compute_variance("c1", dt.date(2026, 3, 1))
    assert len(res.rows) == 1
    r = res.rows[0]
    assert r.statement == "IS"
    assert r.actual == 1000
    assert r.budget == 800
    assert r.abs_var == 200
    assert r.pct_var == pytest.approx(0.25)
    assert res.scenario == "realistic"  # default


def test_missing_budget_yields_none_variance(synth_client):
    synth_client("c1",
        {"entities": ["e1"]},
        [
            _row("2026-03-01", "e1", "actual", "IS", "Sales", "g", "x", 1, 1000),
        ],
    )
    res = variance.compute_variance("c1", dt.date(2026, 3, 1))
    r = res.rows[0]
    assert r.actual == 1000
    assert r.budget is None
    assert r.abs_var is None
    assert r.pct_var is None
    assert r.flagged is False


def test_missing_actual_yields_none_variance(synth_client):
    synth_client("c1",
        {"entities": ["e1"]},
        [
            _row("2026-03-01", "e1", "realistic", "IS", "Sales", "g", "x", 1, 800),
        ],
    )
    res = variance.compute_variance("c1", dt.date(2026, 3, 1))
    r = res.rows[0]
    assert r.actual is None
    assert r.budget == 800
    assert r.abs_var is None


def test_threshold_flag_eur_breached(synth_client):
    synth_client("c1",
        {"entities": ["e1"], "reporting": {
            "variance_thresholds": {"flag_pct": 100, "flag_eur": 50},
        }},
        [
            _row("2026-03-01", "e1", "actual",    "IS", "S", "g", "x", 1, 200),
            _row("2026-03-01", "e1", "realistic", "IS", "S", "g", "x", 1, 100),
        ],
    )
    res = variance.compute_variance("c1", dt.date(2026, 3, 1))
    # abs_var = 100 > flag_eur=50 → flagged.
    assert res.rows[0].flagged is True


def test_threshold_flag_pct_breached(synth_client):
    synth_client("c1",
        {"entities": ["e1"], "reporting": {
            "variance_thresholds": {"flag_pct": 10, "flag_eur": 1000000},
        }},
        [
            _row("2026-03-01", "e1", "actual",    "IS", "S", "g", "x", 1, 130),
            _row("2026-03-01", "e1", "realistic", "IS", "S", "g", "x", 1, 100),
        ],
    )
    res = variance.compute_variance("c1", dt.date(2026, 3, 1))
    # abs_var = 30; pct_var = 30%; flag_pct = 10 → flagged on percent.
    assert res.rows[0].flagged is True


def test_threshold_below_both_does_not_flag(synth_client):
    synth_client("c1",
        {"entities": ["e1"], "reporting": {
            "variance_thresholds": {"flag_pct": 50, "flag_eur": 100},
        }},
        [
            _row("2026-03-01", "e1", "actual",    "IS", "S", "g", "x", 1, 110),
            _row("2026-03-01", "e1", "realistic", "IS", "S", "g", "x", 1, 100),
        ],
    )
    res = variance.compute_variance("c1", dt.date(2026, 3, 1))
    assert res.rows[0].flagged is False


def test_mom_within_year(synth_client):
    """MoM compares actual at period to actual at prior month."""
    synth_client("c1",
        {"entities": ["e1"]},
        [
            _row("2026-02-01", "e1", "actual", "IS", "S", "g", "x", 1, 100),
            _row("2026-03-01", "e1", "actual", "IS", "S", "g", "x", 1, 130),
        ],
    )
    res = variance.compute_variance("c1", dt.date(2026, 3, 1))
    r = res.rows[0]
    assert r.actual_prior == 100
    assert r.mom_abs == 30
    assert r.mom_pct == pytest.approx(0.30)


def test_mom_january_is_none(synth_client):
    """January period → no prior month within the year, mom fields are None."""
    synth_client("c1",
        {"entities": ["e1"]},
        [
            _row("2026-01-01", "e1", "actual", "IS", "S", "g", "x", 1, 100),
        ],
    )
    res = variance.compute_variance("c1", dt.date(2026, 1, 1))
    r = res.rows[0]
    assert r.actual == 100
    assert r.actual_prior is None
    assert r.mom_abs is None
    assert r.mom_pct is None


def test_ytd_for_is_sums_jan_through_period(synth_client):
    synth_client("c1",
        {"entities": ["e1"]},
        [
            _row("2026-01-01", "e1", "actual",    "IS", "S", "g", "x", 1, 100),
            _row("2026-02-01", "e1", "actual",    "IS", "S", "g", "x", 1, 200),
            _row("2026-03-01", "e1", "actual",    "IS", "S", "g", "x", 1, 300),
            _row("2026-01-01", "e1", "realistic", "IS", "S", "g", "x", 1, 90),
            _row("2026-02-01", "e1", "realistic", "IS", "S", "g", "x", 1, 90),
            _row("2026-03-01", "e1", "realistic", "IS", "S", "g", "x", 1, 90),
        ],
    )
    res = variance.compute_variance("c1", dt.date(2026, 3, 1))
    r = res.rows[0]
    assert r.actual_ytd == 600        # 100+200+300
    assert r.budget_ytd == 270        # 90+90+90
    assert r.ytd_abs == 330
    assert r.ytd_pct == pytest.approx(330 / 270)


def test_ytd_for_bs_is_none(synth_client):
    """Balance sheet rows: YTD doesn't apply (balances are point-in-time)."""
    synth_client("c1",
        {"entities": ["e1"]},
        [
            _row("2026-01-01", "e1", "actual", "BS", "Cash", "g", "x", 1, 100),
            _row("2026-02-01", "e1", "actual", "BS", "Cash", "g", "x", 1, 110),
            _row("2026-03-01", "e1", "actual", "BS", "Cash", "g", "x", 1, 120),
        ],
    )
    res = variance.compute_variance("c1", dt.date(2026, 3, 1))
    r = res.rows[0]
    assert r.actual == 120
    assert r.actual_prior == 110
    assert r.actual_ytd is None
    assert r.budget_ytd is None
    assert r.ytd_abs is None


def test_explicit_scenario_overrides_default(synth_client):
    """Caller can pass scenario= to override config / default."""
    synth_client("c1",
        {"entities": ["e1"]},
        [
            _row("2026-03-01", "e1", "actual",      "IS", "S", "g", "x", 1, 100),
            _row("2026-03-01", "e1", "pessimistic", "IS", "S", "g", "x", 1, 60),
            _row("2026-03-01", "e1", "realistic",   "IS", "S", "g", "x", 1, 80),
        ],
    )
    res = variance.compute_variance("c1", dt.date(2026, 3, 1),
                                    scenario="pessimistic")
    r = res.rows[0]
    assert r.actual == 100
    assert r.budget == 60
    assert res.scenario == "pessimistic"


def test_config_variance_scenario_is_used(synth_client):
    """When config sets reporting.variance_scenario, that's the default."""
    synth_client("c1",
        {"entities": ["e1"], "reporting": {
            "variance_scenario": "optimistic",
        }},
        [
            _row("2026-03-01", "e1", "actual",     "IS", "S", "g", "x", 1, 100),
            _row("2026-03-01", "e1", "optimistic", "IS", "S", "g", "x", 1, 150),
            _row("2026-03-01", "e1", "realistic",  "IS", "S", "g", "x", 1, 80),
        ],
    )
    res = variance.compute_variance("c1", dt.date(2026, 3, 1))
    assert res.scenario == "optimistic"
    assert res.rows[0].budget == 150


def test_multi_entity_requires_explicit_entity(synth_client):
    synth_client("c1",
        {"entities": ["e1", "e2"]},
        [
            _row("2026-03-01", "e1", "actual", "IS", "S", "g", "x", 1, 100),
        ],
    )
    with pytest.raises(ValueError, match="multiple entities"):
        variance.compute_variance("c1", dt.date(2026, 3, 1))


def test_multi_entity_with_explicit_entity(synth_client):
    synth_client("c1",
        {"entities": ["e1", "e2"]},
        [
            _row("2026-03-01", "e1", "actual",    "IS", "S", "g", "x", 1, 100),
            _row("2026-03-01", "e1", "realistic", "IS", "S", "g", "x", 1, 80),
            _row("2026-03-01", "e2", "actual",    "IS", "S", "g", "x", 1, 999),
            _row("2026-03-01", "e2", "realistic", "IS", "S", "g", "x", 1, 999),
        ],
    )
    res = variance.compute_variance("c1", dt.date(2026, 3, 1), entity="e1")
    # e1 only — e2 rows must not leak in.
    assert len(res.rows) == 1
    assert res.rows[0].actual == 100
    assert res.rows[0].budget == 80


def test_rows_ordered_by_display_order(synth_client):
    synth_client("c1",
        {"entities": ["e1"]},
        [
            _row("2026-03-01", "e1", "actual", "IS", "S", "g", "third",  3, 30),
            _row("2026-03-01", "e1", "actual", "IS", "S", "g", "first",  1, 10),
            _row("2026-03-01", "e1", "actual", "IS", "S", "g", "second", 2, 20),
        ],
    )
    res = variance.compute_variance("c1", dt.date(2026, 3, 1))
    is_rows = [r for r in res.rows if r.statement == "IS"]
    assert [r.subgroup for r in is_rows] == ["first", "second", "third"]


def test_zero_budget_yields_none_pct(synth_client):
    """Avoid divide-by-zero — pct_var is None when budget is 0."""
    synth_client("c1",
        {"entities": ["e1"]},
        [
            _row("2026-03-01", "e1", "actual",    "IS", "S", "g", "x", 1, 100),
            _row("2026-03-01", "e1", "realistic", "IS", "S", "g", "x", 1, 0),
        ],
    )
    res = variance.compute_variance("c1", dt.date(2026, 3, 1))
    r = res.rows[0]
    assert r.abs_var == 100
    assert r.pct_var is None  # 100 / 0 → None, not error


# Writers -------------------------------------------------------------------

def test_csv_writer_emits_one_row_per_variance_row(synth_client, tmp_path):
    synth_client("c1",
        {"entities": ["e1"]},
        [
            _row("2026-03-01", "e1", "actual",    "IS", "Sales", "g", "x", 1, 1000),
            _row("2026-03-01", "e1", "realistic", "IS", "Sales", "g", "x", 1, 800),
            _row("2026-03-01", "e1", "actual",    "BS", "Cash",  "g", "y", 2, 500),
        ],
    )
    res = variance.compute_variance("c1", dt.date(2026, 3, 1))
    out = tmp_path / "out.csv"
    variance.write_variance_csv(res, out)
    text = out.read_text()
    lines = text.strip().split("\n")
    # 1 header + 2 data rows.
    assert len(lines) == 3
    # Header is column names.
    assert lines[0].startswith("statement,data,grp,subgroup,actual,budget")
    # IS row appears with its values.
    assert "IS,Sales,g,x" in lines[1]


def test_csv_writer_none_renders_as_empty(synth_client, tmp_path):
    synth_client("c1",
        {"entities": ["e1"]},
        [
            _row("2026-03-01", "e1", "actual", "IS", "S", "g", "x", 1, 100),
        ],
    )
    res = variance.compute_variance("c1", dt.date(2026, 3, 1))
    out = tmp_path / "out.csv"
    variance.write_variance_csv(res, out)
    text = out.read_text()
    # budget is None → empty string between commas.
    data_line = text.strip().split("\n")[1]
    cells = data_line.split(",")
    # statement, data, grp, subgroup, actual, budget, abs_var, pct_var, ...
    assert cells[0] == "IS"
    assert cells[4] == "100.00"  # actual
    assert cells[5] == ""        # budget None
    assert cells[6] == ""        # abs_var None


def test_md_writer_includes_summary_header(synth_client, tmp_path):
    synth_client("c1",
        {"entities": ["e1"], "reporting": {
            "variance_thresholds": {"flag_pct": 25, "flag_eur": 5000},
        }},
        [
            _row("2026-03-01", "e1", "actual",    "IS", "Sales", "g", "x", 1, 100),
            _row("2026-03-01", "e1", "realistic", "IS", "Sales", "g", "x", 1, 80),
        ],
    )
    res = variance.compute_variance("c1", dt.date(2026, 3, 1))
    out = tmp_path / "variance.md"
    variance.write_variance_md(res, out)
    text = out.read_text()
    assert "# Variance — c1 2026-03" in text
    assert "Scenario: **realistic** budget" in text
    assert "Thresholds: |Δ €| > 5,000 OR |Δ %| > 25%" in text


def test_md_writer_flagged_section_when_no_flags(synth_client, tmp_path):
    synth_client("c1",
        {"entities": ["e1"]},
        [
            _row("2026-03-01", "e1", "actual",    "IS", "S", "g", "x", 1, 100),
            _row("2026-03-01", "e1", "realistic", "IS", "S", "g", "x", 1, 100),
        ],
    )
    res = variance.compute_variance("c1", dt.date(2026, 3, 1))
    out = tmp_path / "variance.md"
    variance.write_variance_md(res, out)
    text = out.read_text()
    assert "## Flagged for discussion" in text
    assert "_No rows breach the thresholds._" in text


def test_md_writer_flagged_section_with_flags(synth_client, tmp_path):
    synth_client("c1",
        {"entities": ["e1"], "reporting": {
            "variance_thresholds": {"flag_pct": 10, "flag_eur": 50},
        }},
        [
            _row("2026-03-01", "e1", "actual",    "IS", "Sales", "g", "x", 1, 1000),
            _row("2026-03-01", "e1", "realistic", "IS", "Sales", "g", "x", 1, 500),
        ],
    )
    res = variance.compute_variance("c1", dt.date(2026, 3, 1))
    out = tmp_path / "variance.md"
    variance.write_variance_md(res, out)
    text = out.read_text()
    # Flagged table header includes Stmt column for cross-statement view.
    assert "| Stmt |" in text
    # Flag glyph appears.
    assert "⚑" in text


def test_md_writer_omits_ytd_columns_for_pure_bs_section(synth_client, tmp_path):
    """BS rows shouldn't have YTD columns rendered (always None for BS)."""
    synth_client("c1",
        {"entities": ["e1"]},
        [
            _row("2026-03-01", "e1", "actual",    "BS", "Cash", "g", "x", 1, 500),
            _row("2026-03-01", "e1", "realistic", "BS", "Cash", "g", "x", 1, 400),
        ],
    )
    res = variance.compute_variance("c1", dt.date(2026, 3, 1))
    out = tmp_path / "variance.md"
    variance.write_variance_md(res, out)
    text = out.read_text()
    # Find the BS section and check no YTD columns there.
    bs_section = text.split("## Balance Sheet (BS)")[1]
    assert "YTD Act" not in bs_section
    assert "YTD Bud" not in bs_section


def test_md_writer_includes_ytd_columns_for_is(synth_client, tmp_path):
    synth_client("c1",
        {"entities": ["e1"]},
        [
            _row("2026-01-01", "e1", "actual",    "IS", "Sales", "g", "x", 1, 100),
            _row("2026-02-01", "e1", "actual",    "IS", "Sales", "g", "x", 1, 200),
            _row("2026-03-01", "e1", "actual",    "IS", "Sales", "g", "x", 1, 300),
            _row("2026-03-01", "e1", "realistic", "IS", "Sales", "g", "x", 1, 250),
        ],
    )
    res = variance.compute_variance("c1", dt.date(2026, 3, 1))
    out = tmp_path / "variance.md"
    variance.write_variance_md(res, out)
    text = out.read_text()
    is_section = text.split("## Income Statement (IS)")[1]
    assert "YTD Act" in is_section
    assert "YTD Bud" in is_section
