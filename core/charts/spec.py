"""Chart spec loader + JSON-schema validator.

A chart spec is a small JSON document under ``specs/<client>/<chart_id>.json``
that describes one chart: title, type, data queries, period semantics, and
brand overrides. The renderer reads the spec, calls ``core.query`` to resolve
each data series, and emits PNG + a sidecar JSON snapshot.

This module is purely declarative — it loads, validates, and exposes the
parsed spec as a typed dataclass. Rendering lives in ``core.charts.render``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator
from jsonschema.exceptions import ValidationError


_SCHEMA_PATH = Path(__file__).parent / "spec_schema.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text())
_VALIDATOR = Draft7Validator(_SCHEMA)


class SpecValidationError(ValueError):
    """Raised when a spec JSON file fails schema validation."""


@dataclass(frozen=True)
class DataSeries:
    label: str
    query: dict[str, Any]


@dataclass(frozen=True)
class ChartSpec:
    chart_id: str
    client: str
    title: str
    chart_type: str
    source: str
    period: dict[str, Any]
    data: list[DataSeries]
    entity: str | None = None
    platform_export: str | None = None
    axes: dict[str, Any] = field(default_factory=dict)
    style: dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    @property
    def is_platform(self) -> bool:
        return self.source == "platform"


def load_spec(path: str | Path) -> ChartSpec:
    """Read ``path``, validate against the JSON schema, return ChartSpec.

    Raises ``SpecValidationError`` (a ValueError subclass) on any schema
    violation. The error message names the failing field.
    """
    path = Path(path)
    raw = json.loads(path.read_text())
    errors = sorted(_VALIDATOR.iter_errors(raw), key=lambda e: list(e.absolute_path))
    if errors:
        first = errors[0]
        location = ".".join(str(p) for p in first.absolute_path) or "<root>"
        raise SpecValidationError(
            f"{path.name}: schema violation at {location}: {first.message}"
        )

    return ChartSpec(
        chart_id=raw["chart_id"],
        client=raw["client"],
        title=raw["title"],
        chart_type=raw["chart_type"],
        source=raw["source"],
        period=raw["period"],
        data=[DataSeries(label=d["label"], query=d["query"]) for d in raw["data"]],
        entity=raw.get("entity"),
        platform_export=raw.get("platform_export"),
        axes=raw.get("axes", {}),
        style=raw.get("style", {}),
        notes=raw.get("notes", ""),
    )
