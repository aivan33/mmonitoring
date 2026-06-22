-- A financial model as a normalized schema: STRUCTURE + the dependency graph (lineage).
-- Values stay in Excel (line_value is defined but left unpopulated for now). Portable SQL —
-- runs on SQLite (default) and DuckDB. See docs/superpowers/specs/2026-06-22-model-as-schema.md.

-- ---- dimensions ----------------------------------------------------------
CREATE TABLE client (
    client_id   INTEGER PRIMARY KEY,
    name        TEXT NOT NULL
);

CREATE TABLE model (
    model_id        INTEGER PRIMARY KEY,
    client_id       INTEGER NOT NULL REFERENCES client(client_id),
    name            TEXT NOT NULL,
    base_ccy        TEXT,
    start_date      TEXT,            -- ISO yyyy-mm-dd
    horizon_months  INTEGER
);

CREATE TABLE scenario (
    scenario_id     INTEGER PRIMARY KEY,
    model_id        INTEGER NOT NULL REFERENCES model(model_id),
    name            TEXT NOT NULL,
    offset_index    INTEGER NOT NULL  -- the D2 scenario-selector value (Realistic=1, …)
);

CREATE TABLE period (
    period_id   INTEGER PRIMARY KEY,
    model_id    INTEGER NOT NULL REFERENCES model(model_id),
    kind        TEXT NOT NULL CHECK (kind IN ('month','year')),
    idx         INTEGER NOT NULL,
    date        TEXT,
    label       TEXT
);

CREATE TABLE section (
    section_id  INTEGER PRIMARY KEY,
    model_id    INTEGER NOT NULL REFERENCES model(model_id),
    pillar      TEXT NOT NULL CHECK (pillar IN ('input','proforma','statement')),
    code        TEXT,
    title       TEXT NOT NULL,
    ord         INTEGER NOT NULL
);

CREATE TABLE grp (
    group_id    INTEGER PRIMARY KEY,
    section_id  INTEGER NOT NULL REFERENCES section(section_id),
    code        TEXT,
    title       TEXT,
    ord         INTEGER NOT NULL
);

-- ---- config (Pillar 1 — inputs) -----------------------------------------
CREATE TABLE input (
    input_id    INTEGER PRIMARY KEY,
    group_id    INTEGER NOT NULL REFERENCES grp(group_id),
    label       TEXT NOT NULL,
    unit        TEXT,
    dtype       TEXT,            -- eur | pct | days | count | date | num
    threshold   REAL,            -- col F ladder threshold, if any
    start_date  TEXT,
    end_date    TEXT,
    notes       TEXT,            -- col O
    ord         INTEGER NOT NULL,
    cell        TEXT             -- provenance: "<sheet>!<coord>" of the active value
);

CREATE TABLE input_value (
    input_id    INTEGER NOT NULL REFERENCES input(input_id),
    scenario_id INTEGER NOT NULL REFERENCES scenario(scenario_id),
    value       REAL,
    PRIMARY KEY (input_id, scenario_id)
);

-- ---- structure (Pillars 2 & 3 — proforma + statement lines) -------------
CREATE TABLE line (
    line_id     INTEGER PRIMARY KEY,
    section_id  INTEGER NOT NULL REFERENCES section(section_id),
    label       TEXT NOT NULL,
    role        TEXT CHECK (role IN ('driver','leaf','subtotal','total','margin','roll','header')),
    unit        TEXT,
    ord         INTEGER NOT NULL,
    cell        TEXT             -- provenance: "<sheet>!<row>" anchor
);

CREATE TABLE line_formula (
    line_id     INTEGER PRIMARY KEY REFERENCES line(line_id),
    formula     TEXT
);

-- the DAG edges = lineage. dep_kind says whether dep_id points at an input or another line.
CREATE TABLE line_dependency (
    line_id     INTEGER NOT NULL REFERENCES line(line_id),
    dep_kind    TEXT NOT NULL CHECK (dep_kind IN ('input','line')),
    dep_id      INTEGER NOT NULL,
    PRIMARY KEY (line_id, dep_kind, dep_id)
);

-- ---- facts (optional; unpopulated for now — values live in Excel) -------
CREATE TABLE line_value (
    line_id     INTEGER NOT NULL REFERENCES line(line_id),
    period_id   INTEGER NOT NULL REFERENCES period(period_id),
    scenario_id INTEGER NOT NULL REFERENCES scenario(scenario_id),
    value       REAL,
    PRIMARY KEY (line_id, period_id, scenario_id)
);

CREATE TABLE kpi (
    kpi_id      INTEGER PRIMARY KEY,
    model_id    INTEGER NOT NULL REFERENCES model(model_id),
    label       TEXT NOT NULL,
    formula     TEXT,
    unit        TEXT
);

CREATE INDEX ix_dep_line ON line_dependency(line_id);
CREATE INDEX ix_dep_target ON line_dependency(dep_kind, dep_id);
CREATE INDEX ix_line_section ON line(section_id);
CREATE INDEX ix_input_group ON input(group_id);
