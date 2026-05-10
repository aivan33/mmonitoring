# Honey — one-offs

Scripts here are **bespoke for Honey** and run on demand, not as part of
the standard monthly framework. They exist because some of Honey's data
isn't yet modeled in `core/data/`. Each one-off should document the
gap it fills and the condition under which it gets retired.

## Inventory

### `build_slide4.py`

**Renders:** the two B2C charts on slide 4 of Honey's quarterly deck —
*Active Subscriptions by Package* (stacked) and *Subscription Flow*
(diverging).

**Why bespoke:** the input is operational subscription data — per-month
B2C SUB rosters with paused-flags and package types. The shared
financials data layer (`core/data/`) only models monthly financial
statements; there is no schema or query API for subscription-event /
roster data yet.

**Inputs:**
- `clients/honey/raw/sales_report/<MM>/B2C SUB *.xlsx` for months where
  exports exist (Nov-25 onward)
- Hard-coded values transcribed from the previous Dec-25 deck for
  Jun-25 .. Oct-25 (no exports were captured at the time)

**Outputs:** `_out/slide4_active_b2c.png`, `_out/slide4_flow_b2c.png`

**When this gets retired:** when the operational data layer lands
(option 2 of the cleanup plan), the slide-4 charts can be re-expressed
as ordinary chart specs in `clients/honey/chart_specs/` and this
script can be deleted.

## Conventions

- `_ref/` — visual reference assets (e.g. PNGs extracted from a prior
  deck used as a transcription source). Gitignored.
- `_out/` — rendered outputs. Gitignored.
- Only `*.py` and `*.md` at the top of `one_offs/` are tracked.
