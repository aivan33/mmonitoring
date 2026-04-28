"""CLI: run hardcoded validation assertions against a client's DB.

Usage: ``python scripts/validate.py <client>``

Exit code 0 on all-pass, 1 on any failure or unknown client.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the repo root importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.query import get_aggregation, get_value, ytd
from core.validation import Assertion, Result, run_assertions


def cupffee_assertions() -> list[Assertion]:
    """The 8 actuals assertions from specs/data_layer.md plus 4 budget
    cells inspected from Taxonomy_budget_q2.xlsx (realistic scenario)."""
    cli = "cupffee"

    def agg(data: str, period: str, scenario: str = "actual") -> float:
        # level='data' returns a 1-element Series; iloc[0] unwraps the value.
        return get_aggregation(data, period, scenario=scenario,
                               client=cli, level="data").iloc[0]

    actuals = [
        Assertion("Sales total 2025-12 actual",
                  lambda: agg("Sales", "2025-12-01"), 124061.80),
        Assertion("Sales/Distributors/Cupffee 220 ml 2025-12 actual",
                  lambda: get_value("Sales", "Distributors", "Cupffee 220 ml",
                                    "2025-12-01", client=cli),
                  81551.52),
        Assertion("Sales/Distributors/Cupffee 110 ml 2025-12 actual",
                  lambda: get_value("Sales", "Distributors", "Cupffee 110 ml",
                                    "2025-12-01", client=cli),
                  15350.40),
        Assertion("Sales total 2025-03 actual",
                  lambda: agg("Sales", "2025-03-01"), 50592.64),
        Assertion("ytd Sales 2025 actual",
                  lambda: ytd("Sales", 2025, client=cli), 1043795.81),
        Assertion("Cost of Sales/Materials/Materials 2025-12 actual",
                  lambda: get_value("Cost of Sales", "Materials", "Materials",
                                    "2025-12-01", client=cli),
                  13815.54),
        Assertion("Cash and cash equivalents 2025-12 actual",
                  lambda: get_value("Cash and cash equivalents",
                                    "Cash and cash equivalents",
                                    "Cash and cash equivalents",
                                    "2025-12-01", client=cli),
                  258651.54),
        Assertion("CF Op/Cash from Sales 2025-12 actual",
                  lambda: get_value("Cash Flow from Operating Activities",
                                    "Cash from Sales", "Cash from Sales",
                                    "2025-12-01", client=cli),
                  67466.55),
    ]

    # Budget assertions — realistic scenario, picked from
    # Taxonomy_budget_q2.xlsx by reading raw cells.
    budget = [
        Assertion("Sales total 2026-04 realistic",
                  lambda: agg("Sales", "2026-04-01", scenario="realistic"),
                  50145.0),
        Assertion("Sales total 2026-12 realistic",
                  lambda: agg("Sales", "2026-12-01", scenario="realistic"),
                  116033.0),
        Assertion("CF Op/Cash from Sales 2026-04 realistic",
                  lambda: get_value("Cash Flow from Operating Activities",
                                    "Cash from Sales", "Cash from Sales",
                                    "2026-04-01", scenario="realistic",
                                    client=cli),
                  69878.0),
        Assertion("Cash 2026-12 realistic",
                  lambda: get_value("Cash and cash equivalents",
                                    "Cash and cash equivalents",
                                    "Cash and cash equivalents",
                                    "2026-12-01", scenario="realistic",
                                    client=cli),
                  355830.0),
    ]
    return actuals + budget


CLIENT_ASSERTIONS = {
    "cupffee": cupffee_assertions,
}


def _print_failures(results: list[Result]) -> None:
    for r in results:
        if r.passed:
            continue
        print(f"FAIL: {r.name}", file=sys.stderr)
        print(f"  expected: {r.expected}", file=sys.stderr)
        print(f"  observed: {r.observed}", file=sys.stderr)
        if r.delta is not None:
            print(f"  delta:    {r.delta}", file=sys.stderr)
        if r.error is not None:
            print(f"  error:    {r.error}", file=sys.stderr)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python scripts/validate.py <client>", file=sys.stderr)
        return 2
    client = sys.argv[1]
    if client not in CLIENT_ASSERTIONS:
        print(f"unknown client {client!r}; known: {sorted(CLIENT_ASSERTIONS)}",
              file=sys.stderr)
        return 1

    results = run_assertions(CLIENT_ASSERTIONS[client]())
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print(f"{client}: {passed}/{total} assertions passed")

    if passed != total:
        _print_failures(results)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
