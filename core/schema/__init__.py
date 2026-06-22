"""The financial model as a normalized SQLite schema (structure + lineage).

A model is a DAG: inputs → drivers → revenue/cost lines → statements. This package holds the
portable DDL (`model.sql`) and helpers to create the DB and traverse the lineage edges with a
recursive CTE — the SQL equivalent of ``core.model.flow.Flow.trace_precedents``. Values stay in
Excel; the schema captures structure + the dependency graph.

See ``docs/superpowers/specs/2026-06-22-model-as-schema.md``.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

_DDL = Path(__file__).with_name("model.sql")


def create_db(path: str = ":memory:") -> sqlite3.Connection:
    """Create the schema in a fresh SQLite DB and return the connection (FKs enforced)."""
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_DDL.read_text())
    return conn


# Walk a line's transitive dependencies down to the input leaves (lineage trace).
_TRACE_INPUTS = """
WITH RECURSIVE deps(kind, id) AS (
    SELECT dep_kind, dep_id FROM line_dependency WHERE line_id = ?
    UNION
    SELECT ld.dep_kind, ld.dep_id
    FROM line_dependency ld
    JOIN deps d ON d.kind = 'line' AND ld.line_id = d.id
)
SELECT DISTINCT id FROM deps WHERE kind = 'input';
"""


def trace_input_leaves(conn: sqlite3.Connection, line_id: int) -> set[int]:
    """The set of ``input_id`` a line transitively depends on (recursive-CTE lineage)."""
    return {r[0] for r in conn.execute(_TRACE_INPUTS, (line_id,))}
