"""Tests for core.data.aggregate_formulas — the per-client registry of
aggregate row definitions.

The registry is read from ``clients/<client>/aggregate_formulas.yaml``. It
declares which (data, grp, subgroup) triplets are aggregate rows and how
each one should be recomputed from leaves.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.data.aggregate_formulas import (
    AggregateFormula,
    FormulaLeaf,
    aggregate_keys,
    load_registry,
)


def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)


class TestLoadRegistry:
    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        # No aggregate_formulas.yaml present → no aggregates.
        assert load_registry(tmp_path) == {}

    def test_parses_minimal_entry(self, tmp_path: Path) -> None:
        _write(tmp_path / "aggregate_formulas.yaml", """
gross_burn:
  taxonomi: ["KPI", "Burn", "Gross"]
  leaves:
    - {data: "Cost of Sales", sign: -1}
    - {data: "S&M", sign: -1}
""")
        reg = load_registry(tmp_path)
        assert "gross_burn" in reg
        f = reg["gross_burn"]
        assert isinstance(f, AggregateFormula)
        assert (f.data, f.grp, f.subgroup) == ("KPI", "Burn", "Gross")
        assert f.leaves == (
            FormulaLeaf(data="Cost of Sales", grp=None, subgroup=None, sign=-1),
            FormulaLeaf(data="S&M",          grp=None, subgroup=None, sign=-1),
        )
        assert f.source_cell is None

    def test_parses_source_cell_and_specific_leaves(self, tmp_path: Path) -> None:
        _write(tmp_path / "aggregate_formulas.yaml", """
contribution_margin:
  taxonomi: ["KPI", "Margin", "Contribution"]
  source_cell: "IS!B47"
  leaves:
    - {data: "Sales", grp: "Distributors", subgroup: "220 ml", sign: 1}
    - {data: "Cost of Sales", sign: -1}
""")
        reg = load_registry(tmp_path)
        f = reg["contribution_margin"]
        assert f.source_cell == "IS!B47"
        assert f.leaves[0] == FormulaLeaf(
            data="Sales", grp="Distributors", subgroup="220 ml", sign=1,
        )

    def test_default_sign_is_plus_one(self, tmp_path: Path) -> None:
        _write(tmp_path / "aggregate_formulas.yaml", """
revenue:
  taxonomi: ["KPI", "Revenue", "Total"]
  leaves:
    - {data: "Sales"}
""")
        reg = load_registry(tmp_path)
        assert reg["revenue"].leaves[0].sign == 1

    def test_rejects_missing_taxonomi(self, tmp_path: Path) -> None:
        _write(tmp_path / "aggregate_formulas.yaml", """
broken:
  leaves:
    - {data: "Sales", sign: 1}
""")
        with pytest.raises(ValueError, match="taxonomi"):
            load_registry(tmp_path)

    def test_rejects_non_triplet_taxonomi(self, tmp_path: Path) -> None:
        _write(tmp_path / "aggregate_formulas.yaml", """
broken:
  taxonomi: ["KPI", "Only"]
  leaves:
    - {data: "Sales", sign: 1}
""")
        with pytest.raises(ValueError, match="3-element"):
            load_registry(tmp_path)

    def test_rejects_empty_leaves(self, tmp_path: Path) -> None:
        _write(tmp_path / "aggregate_formulas.yaml", """
broken:
  taxonomi: ["KPI", "X", "Y"]
  leaves: []
""")
        with pytest.raises(ValueError, match="leaves"):
            load_registry(tmp_path)

    def test_rejects_invalid_sign(self, tmp_path: Path) -> None:
        _write(tmp_path / "aggregate_formulas.yaml", """
broken:
  taxonomi: ["KPI", "X", "Y"]
  leaves:
    - {data: "Sales", sign: 2}
""")
        with pytest.raises(ValueError, match="sign"):
            load_registry(tmp_path)


class TestAggregateKeys:
    def test_returns_triplet_set(self, tmp_path: Path) -> None:
        _write(tmp_path / "aggregate_formulas.yaml", """
a:
  taxonomi: ["KPI", "X", "A"]
  leaves: [{data: "Sales"}]
b:
  taxonomi: ["KPI", "X", "B"]
  leaves: [{data: "Sales"}]
""")
        reg = load_registry(tmp_path)
        assert aggregate_keys(reg) == {("KPI", "X", "A"), ("KPI", "X", "B")}

    def test_empty_registry_empty_keys(self) -> None:
        assert aggregate_keys({}) == set()
