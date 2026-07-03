"""Runner for hardcoded validation assertions.

The script ``scripts/validate.py`` defines a list of ``Assertion``s per
client and hands them to ``run_assertions``. Each assertion is a thunk
(zero-arg callable) that returns the observed value, plus an expected
value. ``run_assertions`` returns a ``Result`` per assertion — never
raises — so all assertions execute even if one blows up.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence


@dataclass(frozen=True)
class Assertion:
    name: str
    check: Callable[[], float | None]
    expected: float
    # Per-assertion absolute tolerance; None falls back to the run-level default.
    tolerance: float | None = None


@dataclass(frozen=True)
class Result:
    name: str
    expected: float
    observed: float | None
    delta: float | None
    passed: bool
    error: str | None


def run_assertions(
    assertions: Sequence[Assertion],
    tolerance: float = 1.0,
) -> list[Result]:
    out: list[Result] = []
    for a in assertions:
        try:
            observed = a.check()
        except Exception as exc:
            out.append(Result(
                name=a.name, expected=a.expected, observed=None,
                delta=None, passed=False, error=f"{type(exc).__name__}: {exc}",
            ))
            continue

        if observed is None:
            out.append(Result(
                name=a.name, expected=a.expected, observed=None,
                delta=None, passed=False, error="check returned None",
            ))
            continue

        delta = abs(observed - a.expected)
        tol = a.tolerance if a.tolerance is not None else tolerance
        out.append(Result(
            name=a.name, expected=a.expected, observed=observed,
            delta=delta, passed=delta <= tol, error=None,
        ))
    return out
