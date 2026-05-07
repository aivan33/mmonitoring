"""CLI: run hardcoded validation assertions against a client's DB.

Usage: ``python scripts/validate.py <client>``

Exit code 0 on all-pass, 1 on any failure or unknown client.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the repo root importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.data.query import get_aggregation, get_trend, get_value, ytd
from core.data.validation import Assertion, Result, run_assertions


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


def almacena_assertions() -> list[Assertion]:
    """Empirically picked cells across both entities and both periods.
    Values copied verbatim from the loaded DB after build_db ran clean."""
    cli = "almacena"

    def agg(data: str, period: str, entity: str,
            scenario: str = "actual") -> float:
        return get_aggregation(data, period, scenario=scenario,
                               client=cli, entity=entity, level="data").iloc[0]

    def grp_ytd(data: str, grp: str, year: int, entity: str,
                scenario: str = "actual") -> float:
        s = get_trend(data, grp=grp, scenario=scenario,
                      client=cli, entity=entity,
                      start_date=f"{year}-01-01",
                      end_date=f"{year}-12-01")
        return float(s.dropna().sum())

    return [
        # Consolidated
        Assertion("cons IS Sales total 2025-12 actual",
                  lambda: agg("Sales", "2025-12-01", "consolidated"),
                  37748.15),
        Assertion("cons Cash 2025-12 actual",
                  lambda: get_value("Cash and cash equivalents",
                                    "Cash and Cash equivalents",
                                    "Cash and Cash equivalents",
                                    "2025-12-01", client=cli,
                                    entity="consolidated"),
                  201032.99),
        Assertion("cons IS Sales total 2026-03 actual",
                  lambda: agg("Sales", "2026-03-01", "consolidated"),
                  78005.99),
        # AP Foundation
        Assertion("AP IS Sales total 2025-12 actual",
                  lambda: agg("Sales", "2025-12-01", "ap_foundation"),
                  31248.15),
        Assertion("AP IS Sales total 2026-03 actual",
                  lambda: agg("Sales", "2026-03-01", "ap_foundation"),
                  78005.99),
        Assertion("AP NIR/Gross Interest Revenue 2025-12 actual",
                  lambda: get_value("Sales", "Net Interest Revenue",
                                    "Gross Interest Revenue",
                                    "2025-12-01", client=cli,
                                    entity="ap_foundation"),
                  55492.37),
        Assertion("AP NIR/Funding Cost 2025-12 actual",
                  lambda: get_value("Sales", "Net Interest Revenue",
                                    "Funding Cost",
                                    "2025-12-01", client=cli,
                                    entity="ap_foundation"),
                  -73976.35),
        Assertion("AP NIR group YTD 2025 actual (deck narrative -149K)",
                  lambda: grp_ytd("Sales", "Net Interest Revenue", 2025,
                                  "ap_foundation"),
                  -149511.53),
    ]


def farada_assertions() -> list[Assertion]:
    """Cells picked by reading the FaradaIC source files directly. Spans
    IS / BS / CF Indirect, both ``actual`` (Jan/Feb 2026) and ``realistic``
    (March 2026 budget). PY columns are not yet asserted — 2025 actuals
    aren't in the source set."""
    cli = "farada"

    def agg(data: str, period: str, scenario: str = "actual") -> float:
        return get_aggregation(data, period, scenario=scenario,
                               client=cli, level="data").iloc[0]

    return [
        # IS actual (Feb 2026)
        Assertion("IS Sales/Consumer Electronics/Eval-Kits 2026-02 actual",
                  lambda: get_value("Sales", "Consumer Electronics",
                                    "Eval-Kits", "2026-02-01", client=cli),
                  2000.0),
        Assertion("IS Sales total 2026-02 actual",
                  lambda: agg("Sales", "2026-02-01"), 2500.0),
        # BS actual (Feb 2026)
        Assertion("BS Cash and cash equivalents 2026-02 actual",
                  lambda: get_value("Cash and cash equivalents",
                                    "Cash and cash equivalents",
                                    "Cash and cash equivalents",
                                    "2026-02-01", client=cli),
                  1382641.0),
        Assertion("BS Equity/Share capital 2026-02 actual",
                  lambda: get_value("Equity", "Share capital", "Share capital",
                                    "2026-02-01", client=cli),
                  5436593.0),
        # CF Indirect actual
        Assertion("CF Op/Cash paid to suppliers 2026-02 actual",
                  lambda: get_value("Cash Flow from Operating Activities",
                                    "Cash paid to suppliers",
                                    "Cash paid to suppliers",
                                    "2026-02-01", client=cli),
                  -219844.0),
        Assertion("CF Op/Payment for personnel 2026-01 actual",
                  lambda: get_value("Cash Flow from Operating Activities",
                                    "Payment for personnel and social security",
                                    "Payment for personnel and social security",
                                    "2026-01-01", client=cli),
                  -125859.0),
        # IS realistic (Mar 2026 budget)
        Assertion("IS Sales/Food Logistics/Eval-Kits 2026-03 realistic",
                  lambda: get_value("Sales", "Food Logistics", "Eval-Kits",
                                    "2026-03-01", scenario="realistic",
                                    client=cli),
                  1500.0),
        Assertion("IS Sales total 2026-03 realistic",
                  lambda: agg("Sales", "2026-03-01", scenario="realistic"),
                  31500.0),
    ]


CLIENT_ASSERTIONS = {
    "cupffee":  cupffee_assertions,
    "almacena": almacena_assertions,
    "farada":   farada_assertions,
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
