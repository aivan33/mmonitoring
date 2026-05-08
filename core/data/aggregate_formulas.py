"""Per-client registry of aggregate row formulas.

Format: ``clients/<client>/aggregate_formulas.yaml`` (optional). Each entry
declares an aggregate row that exists in the source spreadsheet and the
leaf rows it should equal:

    gross_burn:
      taxonomi: ["KPI", "Burn", "Gross"]      # (data, grp, subgroup)
      source_cell: "IS!A47"                   # optional, used by R5
      leaves:
        - {data: "Cost of Sales", sign: -1}   # data-level: sum all leaves with this data
        - {data: "S&M", sign: -1}
        - {data: "Sales", grp: "Distributors", subgroup: "220 ml", sign: 1}

A leaf may specify ``data`` only (sums all leaves with that data) or a
full ``(data, grp, subgroup)`` triplet (single leaf row).

The registry is the single declarative source for "is this row an
aggregate?" — the loader uses it to set the ``is_aggregate`` flag, the
integrity checker uses it for R4/R5, and ``get_aggregation`` uses the
flag to avoid double-counting.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class FormulaLeaf:
    data: str
    grp: str | None = None
    subgroup: str | None = None
    sign: int = 1


@dataclass(frozen=True)
class AggregateFormula:
    name: str
    data: str
    grp: str
    subgroup: str
    leaves: tuple[FormulaLeaf, ...]
    source_cell: str | None = None


def load_registry(client_dir: str | Path) -> dict[str, AggregateFormula]:
    """Read ``aggregate_formulas.yaml`` from ``client_dir``. Empty dict if absent."""
    path = Path(client_dir) / "aggregate_formulas.yaml"
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text()) or {}
    out: dict[str, AggregateFormula] = {}
    for name, body in raw.items():
        out[name] = _parse_entry(name, body)
    return out


def _parse_entry(name: str, body: dict) -> AggregateFormula:
    taxonomi = body.get("taxonomi")
    if not isinstance(taxonomi, list):
        raise ValueError(
            f"aggregate_formulas.yaml: {name!r}: 'taxonomi' is required and "
            f"must be a 3-element list [data, grp, subgroup]"
        )
    if len(taxonomi) != 3:
        raise ValueError(
            f"aggregate_formulas.yaml: {name!r}: 'taxonomi' must be a "
            f"3-element list [data, grp, subgroup], got {taxonomi!r}"
        )

    leaves_raw = body.get("leaves") or []
    if not leaves_raw:
        raise ValueError(
            f"aggregate_formulas.yaml: {name!r}: 'leaves' is required and "
            f"must be non-empty"
        )

    leaves = tuple(_parse_leaf(name, raw_leaf) for raw_leaf in leaves_raw)
    return AggregateFormula(
        name=name,
        data=str(taxonomi[0]),
        grp=str(taxonomi[1]),
        subgroup=str(taxonomi[2]),
        leaves=leaves,
        source_cell=body.get("source_cell"),
    )


def _parse_leaf(name: str, raw: dict) -> FormulaLeaf:
    if "data" not in raw:
        raise ValueError(
            f"aggregate_formulas.yaml: {name!r}: every leaf must have 'data'"
        )
    sign = int(raw.get("sign", 1))
    if sign not in (-1, 1):
        raise ValueError(
            f"aggregate_formulas.yaml: {name!r}: leaf sign must be -1 or 1, "
            f"got {sign!r}"
        )
    return FormulaLeaf(
        data=str(raw["data"]),
        grp=str(raw["grp"]) if raw.get("grp") is not None else None,
        subgroup=str(raw["subgroup"]) if raw.get("subgroup") is not None else None,
        sign=sign,
    )


def aggregate_keys(
    registry: dict[str, AggregateFormula],
) -> set[tuple[str, str, str]]:
    """Triplets that should be tagged ``is_aggregate=1`` after load."""
    return {(f.data, f.grp, f.subgroup) for f in registry.values()}
