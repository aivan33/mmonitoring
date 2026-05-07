# core.text — text templating engine (planned)

Stub package, not implemented yet. See
[`docs/onboarding-text.md`](../../docs/onboarding-text.md) for the
full description of the planned use case.

## Intended shape

```
core/text/
├── __init__.py           public API (render, etc.)
├── render.py             loads global + per-client config, renders templates
└── templates/            shared template fragments
```

## Why a package now, before the engine exists

So the use-case split (`core/data/` ← `core/charts/` / `core/text/` /
`core/report/`) is visible in the file tree and consistent. New
contributors looking at `core/` see four clearly-named packages and
understand the system's seams without needing to read code.

When the text use case is picked up, the engine lands here without
any restructuring.

## Open questions (when picked up)

- Templating library (Jinja2) vs hand-rolled string interpolation
- Where templates live: in `core/text/templates/` (engine-managed,
  global) or `clients/<client>/text_templates/` (client-managed,
  per-client overrides) — likely both, with the engine merging
- Output format: pure Markdown vs Markdown + a structured-block
  intermediate (consumable by both deck assembly and report
  pipelines)
