"""The flow layer of the model parser — the dependency graph.

``build_flow(cells)`` gives a :class:`Flow` over a parsed workbook. From there:

- ``trace_precedents(sheet, coord)`` walks a formula cell back to its driver
  *leaves* (cells with no formula — the literal inputs). This is the mechanic
  behind variance->driver tracing: from a budget output cell you reach the
  Inputs/Loans/KPIs cells that drive it.
- ``trace_dependents(sheet, coord)`` walks the reverse — every cell a driver
  feeds (impact analysis).

Precedents are computed lazily from formula strings (via the formula layer) over
cached values, so tracing one output is cheap. Dynamic references (OFFSET/…) and
unbounded/oversized ranges are recorded on the trace rather than dropped — the
edge to their literal operands is kept, but the trace is marked incomplete there.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .cells import Cells
from .formula import parse_refs

CellId = tuple[str, str]

# A bounded range larger than this is treated as dynamic (not expanded edge-by-edge).
RANGE_EXPANSION_CAP = 10_000


@dataclass
class TraceResult:
    """The outcome of a precedent trace."""

    leaves: set[CellId] = field(default_factory=set)
    visited: set[CellId] = field(default_factory=set)
    dynamic: list[CellId] = field(default_factory=list)  # cells where the trace is incomplete


class Flow:
    """Lazy dependency graph over a parsed workbook."""

    def __init__(self, cells: Cells) -> None:
        self._cells = cells
        self._prec_cache: dict[CellId, list[CellId]] = {}
        self._dynamic_cells: set[CellId] = set()
        self._dependents: dict[CellId, set[CellId]] | None = None

    def precedents(self, sheet: str, coord: str) -> list[CellId]:
        """Direct precedent cells of ``sheet!coord`` (``[]`` for a leaf)."""
        cid = (sheet, coord.upper())
        if cid in self._prec_cache:
            return self._prec_cache[cid]
        cell = self._cells.cell(sheet, coord)
        out: list[CellId] = []
        if cell.formula is not None:
            parsed = parse_refs(cell.formula, sheet)
            if parsed.dynamic or parsed.unresolved:
                self._dynamic_cells.add(cid)
            seen: set[CellId] = set()
            for ref in parsed.refs:
                try:
                    expanded = list(ref.cells())
                except ValueError:  # unbounded range — can't expand statically
                    self._dynamic_cells.add(cid)
                    continue
                if len(expanded) > RANGE_EXPANSION_CAP:
                    self._dynamic_cells.add(cid)
                    continue
                for s, c in expanded:
                    key = (s, c.upper())
                    if key not in seen:
                        seen.add(key)
                        out.append(key)
        self._prec_cache[cid] = out
        return out

    def trace_precedents(self, sheet: str, coord: str) -> TraceResult:
        """Walk precedents back to driver leaves, depth-first."""
        res = TraceResult()
        stack: list[CellId] = [(sheet, coord.upper())]
        while stack:
            cid = stack.pop()
            if cid in res.visited:
                continue
            res.visited.add(cid)
            s, c = cid
            try:
                cell = self._cells.cell(s, c)
            except KeyError:  # external / missing-sheet reference
                res.dynamic.append(cid)
                continue
            if cell.formula is None:
                if cell.value is not None:
                    res.leaves.add(cid)
                continue
            precs = self.precedents(s, c)
            if cid in self._dynamic_cells:
                res.dynamic.append(cid)
            for p in precs:
                if p not in res.visited:
                    stack.append(p)
        return res

    def _build_dependents(self) -> None:
        deps: dict[CellId, set[CellId]] = {}
        for cell in self._cells.iter_formula_cells():
            cid = (cell.sheet, cell.coord)
            for p in self.precedents(cell.sheet, cell.coord):
                deps.setdefault(p, set()).add(cid)
        self._dependents = deps

    def trace_dependents(self, sheet: str, coord: str) -> set[CellId]:
        """Every cell that (transitively) depends on ``sheet!coord``."""
        if self._dependents is None:
            self._build_dependents()
        assert self._dependents is not None
        out: set[CellId] = set()
        stack: list[CellId] = [(sheet, coord.upper())]
        while stack:
            cid = stack.pop()
            for d in self._dependents.get(cid, ()):
                if d not in out:
                    out.add(d)
                    stack.append(d)
        return out


def build_flow(cells: Cells) -> Flow:
    """Build a :class:`Flow` over a parsed workbook."""
    return Flow(cells)
