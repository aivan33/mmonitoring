"""SQLite schema for the monitoring DB.

One table: ``financials`` (taxonomy-format IS/CF/BS data, all scenarios).
The ``entity`` column lets a single client DB hold multiple tracked entities
(e.g. consolidated + subsidiary). Single-entity clients use one constant
value throughout.

``apply`` is idempotent and safe to run against an existing DB.
``wipe_and_create`` is destructive — it deletes the file first.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DDL = """
CREATE TABLE IF NOT EXISTS financials (
    period_date    DATE NOT NULL,
    entity         TEXT NOT NULL,
    scenario       TEXT NOT NULL
                   CHECK (scenario IN ('actual','pessimistic','realistic','optimistic')),
    statement      TEXT NOT NULL CHECK (statement IN ('IS','CF','BS')),
    data           TEXT NOT NULL,
    grp            TEXT NOT NULL,
    subgroup       TEXT NOT NULL,
    display_order  INTEGER NOT NULL,
    value          REAL,
    is_aggregate   INTEGER NOT NULL DEFAULT 0
                   CHECK (is_aggregate IN (0, 1)),
    PRIMARY KEY (period_date, entity, scenario, statement, data, grp, subgroup)
);

CREATE INDEX IF NOT EXISTS idx_fin_period   ON financials(period_date);
CREATE INDEX IF NOT EXISTS idx_fin_scenario ON financials(scenario);
CREATE INDEX IF NOT EXISTS idx_fin_data     ON financials(data);
CREATE INDEX IF NOT EXISTS idx_fin_entity   ON financials(entity);
"""


def apply(path: str | Path) -> None:
    """Create the schema in ``path`` if not already present. Idempotent."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(DDL)


def wipe_and_create(path: str | Path) -> None:
    """Delete ``path`` if present, then create a fresh schema."""
    path = Path(path)
    if path.exists():
        path.unlink()
    apply(path)
