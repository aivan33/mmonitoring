"""The formula layer of the model parser.

``parse_refs(formula, sheet)`` turns a formula string into the set of cell and
range references it depends on — its *precedents* — resolving cross-sheet and
quoted sheet names and stripping absolute markers. It uses openpyxl's
``Tokenizer`` (no evaluation).

Dynamic functions (``OFFSET`` / ``INDEX`` / ``INDIRECT``) are **flagged** in the
result rather than having their refs dropped: the cell they ultimately resolve
to depends on runtime values, so a static parse of their literal operands is
necessarily incomplete. The flow layer resolves them via cached values (D6).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from openpyxl.formula.tokenizer import Tokenizer
from openpyxl.utils.cell import get_column_letter, range_boundaries

# Functions whose resolved target is runtime-dependent.
DYNAMIC_FUNCS = {"OFFSET", "INDEX", "INDIRECT"}


@dataclass(frozen=True)
class Ref:
    """A reference to a single cell (``end is None``) or a rectangular range."""

    sheet: str
    start: str
    end: str | None = None

    @property
    def is_range(self) -> bool:
        return self.end is not None

    def cells(self) -> Iterator[tuple[str, str]]:
        """Yield ``(sheet, coord)`` for every cell, expanding a bounded range."""
        if self.end is None:
            yield (self.sheet, self.start)
            return
        min_col, min_row, max_col, max_row = range_boundaries(f"{self.start}:{self.end}")
        if None in (min_col, min_row, max_col, max_row):
            raise ValueError(f"cannot expand unbounded range {self.start}:{self.end}")
        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                yield (self.sheet, f"{get_column_letter(col)}{row}")


@dataclass
class ParseResult:
    """Refs found in a formula, plus what could not be statically resolved."""

    refs: list[Ref] = field(default_factory=list)
    dynamic: list[str] = field(default_factory=list)   # dynamic funcs encountered
    unresolved: list[str] = field(default_factory=list)  # operands that didn't parse


def _unquote(sheet: str) -> str:
    if sheet.startswith("'") and sheet.endswith("'"):
        return sheet[1:-1].replace("''", "'")
    return sheet


def _parse_operand(value: str, default_sheet: str) -> Ref | None:
    """Parse a tokenizer RANGE operand into a :class:`Ref`, or ``None`` if it is
    not a coordinate (e.g. a defined name)."""
    if "!" in value:
        sheet_part, cell_part = value.rsplit("!", 1)
        sheet = _unquote(sheet_part)
    else:
        sheet, cell_part = default_sheet, value
    cell_part = cell_part.replace("$", "")
    try:
        range_boundaries(cell_part)
    except ValueError:
        return None
    if ":" in cell_part:
        start, end = cell_part.split(":", 1)
        return Ref(sheet, start.upper(), end.upper())
    return Ref(sheet, cell_part.upper(), None)


def parse_refs(formula: str, sheet: str) -> ParseResult:
    """Parse ``formula`` (evaluated on ``sheet``) into its referenced cells."""
    result = ParseResult()
    seen: set[tuple[str, str, str | None]] = set()
    for token in Tokenizer(formula).items:
        if token.type == "FUNC" and token.subtype == "OPEN":
            name = token.value.rstrip("(").upper()
            if name in DYNAMIC_FUNCS and name not in result.dynamic:
                result.dynamic.append(name)
        elif token.type == "OPERAND" and token.subtype == "RANGE":
            ref = _parse_operand(token.value, sheet)
            if ref is None:
                if token.value not in result.unresolved:
                    result.unresolved.append(token.value)
            else:
                key = (ref.sheet, ref.start, ref.end)
                if key not in seen:
                    seen.add(key)
                    result.refs.append(ref)
    return result
