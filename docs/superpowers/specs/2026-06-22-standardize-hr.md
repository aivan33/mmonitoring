# Spec — standardize HR (template + schema), with space for ambiguity

HR is the headcount/payroll driver. The three models share a **roster → monthly cost → dept rollup**
shape but differ in columns (Farada/Almacena cost-rosters; Cupffee shift/scenario roster). Standardize
it as a **flexible roster**: a fixed core that the schema can compress, plus an open extension for the
client-specific bits. Lossy compression is acceptable (the user: "compressed, albeit a bit worse, if
it's beneficial for the big picture of the DB"). This also makes the schema's orphan list trustworthy
(today `Inputs!J137` salary-indexation looks orphaned only because HR isn't loaded).

## What the 3 HR sheets actually are
| | Farada | Almacena | Cupffee |
|---|---|---|---|
| Row = | one role | one role | one role (shift worker) |
| Core cols | Dept · Name · Position · Entity · **Type** · Start · End · **Monthly cost (H)** | Dept · Position · Name · Entity · **Type** · **Engagement** · Start · End · **Monthly cost (I)** | Dept · Position · shift · Name · **SC1/SC2/SC3 toggles** |
| Monthly grid | `IF(start≤m≤end, cost·(1+J137)^Δyr, 0)` | `IF(start≤m≤end, cost·…, 0)` | scenario-gated `IF(Inputs!$J$5=…)` |
| Rollups | COUNTIF headcount · SUMIF cost by **Type** | same | same |
| Cost taxonomy (Type) | COGS / S&M / G&A / R&D | CoS / S&M / G&A / R&D | (by dept) |

**Common core:** a roster keyed by a **cost Type** (→ the OPEX/COGS bucket it feeds) with **start/end
dates** and a **monthly cost**, escalated, gated by the date window, summed per Type into the P&L.
**The ambiguity:** names (TBD/[To be hired]), entity (multi-entity), engagement (FTE/contractor),
and **scenario activation** (Cupffee's per-scenario Yes/No) — all optional / client-specific.

## Architecture decision — standardize ON TOP of the existing Excel HR (never replace it)
The Excel HR sheet **stays as the source of the VALUES** — it computes the date-gated, escalated
monthly cost grid the ProForma pulls (`=HR!O16`…), and the schema has no recalc engine (it can't
produce those numbers; `line_value`/grid are intentionally unpopulated). So standardization is
**additive**, two layers on top of the live HR:
1. **Schema `headcount`** = a read-only roster *derived from* the existing Excel HR (parse the rows).
   Excel keeps the values; the DB gets the queryable structure + lineage.
2. **Template** = when building a NEW model, author HR to the standard layout; when overhauling an
   existing one, **conform/augment** the sheet (add any missing core columns, normalise the Type
   taxonomy) — keep the existing employee rows + costs, never regenerate from scratch.

## Standardized HR — the roster template (sheet)
Fixed columns: **Type** (CoS|S&M|G&A|R&D…) · **Position** · **Name** · **Entity** · **Engagement** ·
**Start** · **End** · **Monthly cost** → then the **monthly grid** (`IF(start≤m≤end, cost·(1+esc)^Δyr,
0)`, esc = the salary-indexation input) → **rollups** per Type (headcount COUNTIF, cost SUMIF). An
**extension area** (extra columns, e.g. scenario toggles / shift) holds client-specific bits without
breaking the core. The P&L payroll lines pull the Type subtotals (`=HR!O16` …). Lives in the design
system as the HR template.

## Schema — a flexible `headcount` table (the compression)
```
headcount(
  headcount_id pk, model_id fk,
  type      TEXT,            -- cost category → OPEX/COGS bucket (CoS|S&M|G&A|R&D|…)
  position  TEXT,
  name      TEXT,            -- nullable (TBD / [To be hired])
  entity    TEXT,            -- nullable (multi-entity)
  engagement TEXT,           -- nullable (FTE/contractor)
  start_date TEXT, end_date TEXT,
  monthly_cost REAL,         -- total employer monthly cost (one number; the grid is DERIVED)
  escalation_input_id INTEGER REFERENCES input(input_id),  -- the salary-indexation input (nullable)
  attrs     TEXT             -- JSON: the "space for ambiguity" (scenario toggles, shift, custom cols)
)
```
- **Lossy by design:** we store the roster + dates + escalation link, NOT the 120-cell monthly grid
  (it's reconstructable) and not bespoke formulas. "A bit worse" but uniform + queryable (headcount &
  cost by type/period/entity in one SQL).
- **Space for ambiguity = `attrs` JSON + nullable cols** — Cupffee's SC1/2/3 toggles and shift go in
  `attrs`; the core still loads.
- Lineage: the loader also emits the HR **Type-subtotal rows as driver lines** so `ProForma!…=HR!O16`
  resolves; the `escalation_input_id` edge means **J137 is no longer orphaned** and EBITDA→payroll→
  salary-indexation traces end-to-end.

## Tasks
- [ ] **H1 — `headcount` table** in `core/schema/model.sql` (+ widen `section.pillar` CHECK to allow
  `driver`). *Verify:* creates clean; FK to input; `attrs` present.
- [ ] **H2 — loader: load HR** (`core/schema/load.py`): detect the HR sheet, parse roster rows into
  `headcount` (map the columns flexibly; unknowns → `attrs`), link `escalation_input_id` to the
  salary-indexation input, and emit the Type-subtotal rows as driver `line`s so payroll refs resolve.
  *Verify:* Farada → ~30 headcount rows by Type; `J137` drops off `v_orphan_input`; EBITDA traces to
  the salary-indexation input. Cupffee/Almacena load too (core cols; toggles → `attrs`).
- [ ] **H3 — HR template in the design system** (`references/design-system.md` + the skill): the roster
  column grammar + monthly-grid + rollup conventions + the extension area. *Verify:* reproducible.
- [ ] **H4 — report:** `model_logic.md` gains an HR/headcount section (headcount & cost by Type).

### Checkpoint — Farada loads HR; orphan list trustworthy (J137 resolved) → unblocks the overhaul reflow.

## Risks
| Risk | Mitigation |
|---|---|
| HR column layout varies per client | flexible column detection by header keywords; unknown cols → `attrs`; only Type/dates/cost are required |
| Cupffee cost not in the roster (looked up) | capture the toggle in `attrs`; monthly_cost may be null → flag, don't fail |
| Over-modelling the grid | store roster only; derive the grid — keeps it "a bit worse" but clean |

## Open question
- Make HR a `headcount` **table** (recommended — it's a roster, not formula lines) vs shoehorn into
  `line`? Table is cleaner + queryable; the Type-subtotal *lines* still exist for ProForma lineage.
