# Onboarding a `text` client

> **Forward-looking.** The `text` use case engine is not implemented
> yet. This doc describes the planned shape so the structure is in
> place when the engine lands. Until then, narrative content is
> written by hand or generated ad-hoc.

The `text` use case produces narrative blocks — executive summaries,
KPI callouts, commentary paragraphs — from templates with a unified
voice and per-client overrides. The output is Markdown, intended for
either:

- the `charts` use case (where text blocks accompany the chart
  inventory in a slide deck), or
- the `report` use case (where text becomes commentary sections of
  the monthly pack).

## Planned shape

```
config/text.yaml                   global voice, structure templates
clients/<client>/config.yaml       per-client voice overrides:
  voice:
    tone: <investor-facing|operational|...>
    terminology: { revenue: "ARR", customer: "tenant", ... }
    carryover_topics: [ ... ]

core/text/                         template engine (planned)
  templates/                       Jinja-style fragments
  render.py                        loads global + per-client config, renders
```

## Why a unified config + per-client overrides

Across clients, ~80% of structure is shared (sections, ordering,
canonical phrasings). The remaining 20% — terminology, tone,
carry-over topics — is per-client.

A unified config + per-client overrides means: one place to evolve
the voice repo-wide, with the cleanest possible escape hatches when a
client genuinely needs something different. Same pattern that's
planned for the `charts` use case (`config/charts.yaml` for global
styling defaults).

This is **not** the right pattern for `report` clients — see
[`onboarding-report.md`](onboarding-report.md). Report pipelines are
bespoke enough that the unification doesn't pay off.

## Status

- Engine: not started
- Templates: none
- Open question: whether to use a templating library (Jinja2) or
  hand-rolled string interpolation. TBD when the use case is picked up.

See issue #3 for status of the cleanup that's putting the scaffolding
in place.
