# monitoring

Monthly client monitoring tool. Three use cases share one data layer.

> **Cleanup in progress.** The repo is mid-migration to the structure
> described in this README — a few paths still reflect the target state
> rather than the current tree. See issue #3 for status.

## Use cases

| Use case | What it produces | Today |
|---|---|---|
| **`charts`** | PNG charts with JSON sidecars, for slide decks | Cupffee |
| **`text`** | Narrative blocks (executive summaries, commentary) | Planned |
| **`report`** | Full monthly pack: reconcile + variance + commentary, as Markdown | Farada |

A client declares its use cases in `clients/<client>/config.yaml`. They
are not mutually exclusive — a client can subscribe to any combination.

## Quickstart

```bash
uv sync                                                # install deps
uv run python scripts/build_db.py <client>             # build the DB
uv run python scripts/validate.py <client>             # sanity-check it
```

**Charts:**

```bash
uv run python scripts/build_charts.py <client> <YYYY-MM>
# → clients/<client>/charts/<YYYY-MM>/*.png + index.html
```

**Report:**

```bash
uv run python scripts/build_report.py <client> <YYYY-MM> --all
# → clients/<client>/reports/<YYYY-MM>/{reconcile,variance,commentary,checklist}.md
```

## Repo layout

```
core/                 shared data layer + per-use-case packages
  data/               schema, build, query, validation, financials loader
  charts/             chart spec + renderer
  text/               (planned) text template engine
  report/             MR loader + reconcile + variance + commentary

scripts/              CLI entry points
  build_db.py
  build_charts.py
  build_report.py
  validate.py

clients/<client>/     per-client configs, inputs, and outputs
  config.yaml         declares use cases, source files, brand overrides
  README.md           colleague-facing: input → pipeline → output
  raw/                source files (gitignored)
  data/               generated SQLite DB (gitignored)
  reference/          source decks/PDFs/templates (gitignored)
  chart_specs/        chart definitions (charts use case, tracked)
  charts/             rendered chart output (gitignored)
  mapping.yaml        MR → taxonomi mapping (report use case, tracked)
  onboarding.md       engineer-facing setup + runbook (report use case)
  reports/            generated report output (gitignored)

docs/                 project documentation
  architecture.md
  onboarding-charts.md
  onboarding-text.md
  onboarding-report.md
```

## Onboarding a new client

- **Charts** → [`docs/onboarding-charts.md`](docs/onboarding-charts.md)
- **Report** → [`docs/onboarding-report.md`](docs/onboarding-report.md)
- **Text** → [`docs/onboarding-text.md`](docs/onboarding-text.md) *(planned use case, scaffolding only)*

The canonical taxonomi format and the data layer are documented in
[`docs/architecture.md`](docs/architecture.md).

## Development

```bash
uv run pytest -q
```
