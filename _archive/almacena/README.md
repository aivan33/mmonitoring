# Almacena (archived)

Status: **archived 2026-05** — onboarding never completed end-to-end.

## What's in the archive

- `config.yaml` — initial draft config with two entities (`consolidated`,
  `ap_foundation`) and a `Profitabilit Report Q126.xlsx` that needed
  USD→EUR conversion.
- Source files under `_archive/almacena/raw/` and similar — gitignored.

## Why archived

When the repo was cleaned up into the three-use-case structure
(charts / text / report — see issue #3), Almacena had:

- A draft `config.yaml`.
- Source data dropped into `clients/almacena/` (loose at top level,
  not yet organized into `raw/`).
- A reference deck (`Almacena Management Report Dec.pptx`).
- **No chart specs authored.**
- **No end-to-end run completed.**

It was neither delivering output nor cleanly partway through the
charts onboarding flow. Rather than carry a half-onboarded client
through the cleanup, the tree was archived here to be revisited when
Almacena gets prioritized again.

## To pick this back up

When Almacena is the active client again:

1. Move `_archive/almacena/` → `clients/almacena/`.
2. Add `use_cases: [charts]` to the config.
3. Reorganize source files into `raw/` and `reference/` per the
   layout in [`docs/onboarding-charts.md`](../../docs/onboarding-charts.md).
4. Resolve the open questions captured in the original plan
   (BGN/EUR sanity check, the duplicate `taxonomi_act_q1` vs
   `taxonomi_act_1` files, etc.) — these are in git history under
   commits prior to `f834cd8`.
5. Author chart specs in `clients/almacena/chart_specs/`.
6. Validate end-to-end against the reference deck.
