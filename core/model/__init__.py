"""Model pillar — parse a financial-model workbook into structure, cells,
formulas, and flows.

The ``model`` pillar treats a hand-maintained Excel model (e.g. the Almacena
budget) as the source of truth and *parses* it rather than reimplementing its
engine. The parser is built in four layers:

- ``cells``    — value / formula / number-format / type per cell (this module's
                 first concrete piece).
- ``contract`` — typed structure: entities, statements, engine, drivers, month-axis.
- ``formula``  — each formula's referenced cells (precedents).
- ``flow``     — the precedent/dependent graph; trace an output back to its driver
                 leaves, or a driver forward to its impacts.

See ``docs/superpowers/specs/2026-06-15-modeling-pillar-plan.md``.
"""

from __future__ import annotations
