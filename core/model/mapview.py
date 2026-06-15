"""Human-readable dump of a model contract (the ``model-map``).

``format_contract(contract)`` renders the entities, per-entity budget<->actuals
seams, shared engine/driver sheets, and the taxonomi month-axis. It depends only
on the contract (no value reads), so it is cheap and easy to test. The CLI
``scripts/model_map.py`` wires it to a real workbook and can append a driver trace.
"""

from __future__ import annotations

from .contract import ModelContract


def format_contract(contract: ModelContract) -> str:
    lines: list[str] = []
    lines.append(f"Entities: {', '.join(contract.entities()) or '(none)'}")

    axis = contract.month_axis()
    if axis:
        cols = list(axis)
        lines.append(f"Taxonomi month-axis: {cols[0]}={axis[cols[0]]} .. {cols[-1]}={axis[cols[-1]]}")

    lines.append("")
    lines.append("Per entity (budget taxonomi <-> actuals):")
    for ent, seam in contract.seams().items():
        lines.append(f"  {ent}")
        lines.append(f"    budget : {', '.join(seam['budget']) or '(none)'}")
        lines.append(f"    actuals: {', '.join(seam['actuals']) or '(none)'}")

    lines.append("")
    lines.append("Shared:")
    lines.append(f"  engine : {', '.join(s.name for s in contract.engine()) or '(none)'}")
    lines.append(f"  drivers: {', '.join(s.name for s in contract.drivers()) or '(none)'}")

    return "\n".join(lines)
