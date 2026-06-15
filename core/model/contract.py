"""The structure layer of the model parser.

A general classifier engine turns sheet names into typed :class:`SheetInfo`
(entity, role, statement), driven by a small per-client :class:`Rules` config.
:class:`ModelContract` groups the sheets and exposes the actuals/budget/driver
seams plus the taxonomi month-axis.

The engine knows the *generic* financial conventions (taxonomi / yearly /
actuals / IS-CF-BS statements); the client config carries the specifics — entity
name patterns, exact-name role overrides, the separator marker, and the taxonomi
month-axis. See ``clients/almacena/model_rules.yaml`` and
``clients/almacena/budget/MODEL_CONTRACT.md``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string, get_column_letter

# A statement sheet name starts with IS/CF/BS as a delimited token.
_STATEMENT_RE = re.compile(r"^\s*(IS|CF|BS)(?=[_ ]|$)", re.IGNORECASE)
# An "actuals" sheet either says "actual" or carries an "act" token (e.g. BV_act).
_ACT_TOKEN_RE = re.compile(r"(^|[_ ])act([_ ]|$)", re.IGNORECASE)

_STATEMENT_ROLES = {"statement", "taxonomi", "yearly"}
_ENTITY_DEFAULT_ROLES = {"statement", "taxonomi", "yearly", "actuals"}


@dataclass(frozen=True)
class TaxonomiAxis:
    """Where the months live on the budget taxonomi tabs."""

    header_row: int
    first_month_col: str
    months: int
    year: int


@dataclass
class Rules:
    """Per-client classification config (the engine is general)."""

    entity_patterns: dict[str, list[str]]
    default_entity: str = "consolidated"
    role_overrides: dict[str, str] = field(default_factory=dict)
    separator_marker: str = ">>>"
    taxonomi_axis: TaxonomiAxis | None = None


@dataclass(frozen=True)
class SheetInfo:
    """A classified sheet."""

    name: str
    entity: str | None
    role: str  # separator | taxonomi | yearly | actuals | statement | engine | driver | other
    statement: str | None  # IS | CF | BS | None


def _detect_entity(name: str, rules: Rules) -> str | None:
    low = name.lower()
    for entity, subs in rules.entity_patterns.items():
        if any(s.lower() in low for s in subs):
            return entity
    return None


def _detect_statement(name: str) -> str | None:
    m = _STATEMENT_RE.match(name.strip())
    return m.group(1).upper() if m else None


def _detect_role(name: str, rules: Rules) -> str:
    if rules.separator_marker and rules.separator_marker in name:
        return "separator"
    if name in rules.role_overrides:
        return rules.role_overrides[name]
    low = name.lower()
    if "taxonomi" in low:
        return "taxonomi"
    if "yearly" in low:
        return "yearly"
    if "actual" in low or _ACT_TOKEN_RE.search(name):
        return "actuals"
    if _STATEMENT_RE.match(name.strip()):
        return "statement"
    return "other"


def classify_sheet(name: str, rules: Rules) -> SheetInfo:
    """Classify one sheet name into a :class:`SheetInfo`."""
    role = _detect_role(name, rules)
    if role == "separator":
        return SheetInfo(name, None, "separator", None)
    entity = _detect_entity(name, rules)
    if entity is None and role in _ENTITY_DEFAULT_ROLES:
        entity = rules.default_entity
    statement = _detect_statement(name) if role in _STATEMENT_ROLES else None
    return SheetInfo(name, entity, role, statement)


class ModelContract:
    """The classified sheets of one model workbook, grouped and queryable."""

    def __init__(self, sheets: list[SheetInfo], rules: Rules, path: Path) -> None:
        self.sheets = sheets
        self.rules = rules
        self._path = path

    def entities(self) -> list[str]:
        return sorted({s.entity for s in self.sheets if s.entity})

    def by_role(self, role: str) -> list[SheetInfo]:
        return [s for s in self.sheets if s.role == role]

    def by_entity(self, entity: str) -> list[SheetInfo]:
        return [s for s in self.sheets if s.entity == entity]

    def taxonomi(self, entity: str | None = None) -> list[SheetInfo]:
        return [s for s in self.sheets if s.role == "taxonomi" and (entity is None or s.entity == entity)]

    def actuals(self, entity: str | None = None) -> list[SheetInfo]:
        return [s for s in self.sheets if s.role == "actuals" and (entity is None or s.entity == entity)]

    def drivers(self) -> list[SheetInfo]:
        return self.by_role("driver")

    def engine(self) -> list[SheetInfo]:
        return self.by_role("engine")

    def month_axis(self) -> dict[str, str]:
        """Map each taxonomi month column letter to its ``YYYY-MM`` period."""
        ax = self.rules.taxonomi_axis
        if ax is None:
            return {}
        start = column_index_from_string(ax.first_month_col)
        return {
            get_column_letter(start + i): f"{ax.year}-{i + 1:02d}"
            for i in range(ax.months)
        }

    def seams(self) -> dict[str, dict[str, list[str]]]:
        """Per entity, the budget (taxonomi) and actuals sheet names."""
        return {
            ent: {
                "budget": [s.name for s in self.taxonomi(ent)],
                "actuals": [s.name for s in self.actuals(ent)],
            }
            for ent in self.entities()
        }

    def last_populated_month(self, sheet_name: str) -> str | None:
        """The last month column on a taxonomi sheet that holds any value."""
        ax = self.rules.taxonomi_axis
        if ax is None:
            return None
        wb = load_workbook(self._path, read_only=True, data_only=True)
        try:
            ws = wb[sheet_name]
            start = column_index_from_string(ax.first_month_col)
            rows = list(
                ws.iter_rows(
                    min_row=ax.header_row + 1,
                    min_col=start,
                    max_col=start + ax.months - 1,
                    values_only=True,
                )
            )
        finally:
            wb.close()
        last = None
        for i in range(ax.months):
            if any(row[i] is not None for row in rows):
                last = i
        return None if last is None else f"{ax.year}-{last + 1:02d}"


def read_contract(path: str | Path, rules: Rules) -> ModelContract:
    """Classify every sheet in the workbook at ``path``."""
    path = Path(path)
    wb = load_workbook(path, read_only=True)
    try:
        names = list(wb.sheetnames)
    finally:
        wb.close()
    sheets = [classify_sheet(n, rules) for n in names]
    return ModelContract(sheets, rules, path)


def load_rules(path: str | Path) -> Rules:
    """Load a per-client :class:`Rules` config from YAML."""
    data = yaml.safe_load(Path(path).read_text())
    m = data["model"]
    ax = m.get("taxonomi_axis")
    axis = (
        TaxonomiAxis(
            header_row=ax["header_row"],
            first_month_col=ax["first_month_col"],
            months=ax["months"],
            year=ax["year"],
        )
        if ax
        else None
    )
    return Rules(
        entity_patterns=m["entity_patterns"],
        default_entity=m.get("default_entity", "consolidated"),
        role_overrides=m.get("role_overrides", {}),
        separator_marker=m.get("separator_marker", ">>>"),
        taxonomi_axis=axis,
    )
