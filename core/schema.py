"""SQLite schema for the monitoring DB.

Three tables: ``financials`` (taxonomy-format IS/CF/BS data),
``cup_volumes``, and ``country_revenue``.

All three tables carry an ``entity`` column so a single client DB can hold
multiple tracked entities (e.g. Almacena's ``consolidated`` and
``ap_foundation``). For single-entity clients (Cupffee), the column simply
takes one constant value.

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
    PRIMARY KEY (period_date, entity, scenario, statement, data, grp, subgroup)
);

CREATE INDEX IF NOT EXISTS idx_fin_period   ON financials(period_date);
CREATE INDEX IF NOT EXISTS idx_fin_scenario ON financials(scenario);
CREATE INDEX IF NOT EXISTS idx_fin_data     ON financials(data);
CREATE INDEX IF NOT EXISTS idx_fin_entity   ON financials(entity);

CREATE TABLE IF NOT EXISTS cup_volumes (
    period_date  DATE NOT NULL,
    entity       TEXT NOT NULL,
    cup_size     TEXT NOT NULL,
    value        INTEGER,
    PRIMARY KEY (period_date, entity, cup_size)
);

CREATE TABLE IF NOT EXISTS country_revenue (
    period_date  DATE NOT NULL,
    entity       TEXT NOT NULL,
    country      TEXT NOT NULL,
    period_type  TEXT NOT NULL CHECK (period_type IN ('monthly','ltm')),
    value        REAL,
    PRIMARY KEY (period_date, entity, country, period_type)
);
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
