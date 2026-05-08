"""Tests for core.charts.spec.lint_spec — R10 soft warnings.

R10: chart specs with inline ``data + signs`` arrays of >1 elements should
instead reference a registered aggregate so the formula is named once and
verified by R4. Lint is warn-only during Phase 1; later it becomes a hard
schema rejection.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.charts.spec import lint_spec


def _write_spec(path: Path, **overrides) -> Path:
    base = {
        "chart_id": "test_chart",
        "client": "demo",
        "title": "Test",
        "chart_type": "line",
        "source": "custom",
        "period": {"kind": "month"},
        "data": [],
    }
    base.update(overrides)
    path.write_text(json.dumps(base))
    return path


class TestR10:
    def test_single_data_no_finding(self, tmp_path: Path) -> None:
        spec = _write_spec(tmp_path / "s.json", data=[
            {"label": "Sales", "query": {"kind": "trend", "data": "Sales"}},
        ])
        assert lint_spec(spec) == []

    def test_single_element_array_no_finding(self, tmp_path: Path) -> None:
        spec = _write_spec(tmp_path / "s.json", data=[
            {"label": "Sales", "query": {
                "kind": "trend", "data": ["Sales"], "signs": [1],
            }},
        ])
        assert lint_spec(spec) == []

    def test_multi_element_array_warns(self, tmp_path: Path) -> None:
        spec = _write_spec(tmp_path / "burn.json",
                           chart_id="burn_chart",
                           data=[
            {"label": "Gross Burn", "query": {
                "kind": "trend",
                "data": ["Cost of Sales", "S&M", "G&A"],
                "signs": [-1, -1, -1],
            }},
        ])
        findings = lint_spec(spec)
        assert len(findings) == 1
        assert findings[0].rule == "R10"
        assert findings[0].spec_id == "burn_chart"
        assert "Gross Burn" in findings[0].message

    def test_each_series_is_checked(self, tmp_path: Path) -> None:
        spec = _write_spec(tmp_path / "x.json", data=[
            {"label": "A", "query": {"kind": "trend",
                                     "data": ["x", "y"], "signs": [1, 1]}},
            {"label": "B", "query": {"kind": "trend",
                                     "data": ["p", "q"], "signs": [1, 1]}},
        ])
        findings = lint_spec(spec)
        assert len(findings) == 2
