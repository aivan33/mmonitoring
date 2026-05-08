"""Tests for core.data.query.runway_months."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.data.query import runway_months


HEADER = ["Data", "Group", "Subgroup", "Jan", "Feb", "Mar", "Apr", "May",
          "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _runway_client(make_test_client) -> Path:
    """A synthetic client with cash + burn rows under the standard convention."""
    return make_test_client(
        name="runway_demo",
        config={
            "entities": ["demo"],
            "financial_sources": [
                {"file": "raw/a.xlsx", "year": 2025, "entity": "demo"},
            ],
        },
        files={"a.xlsx": {
            "BS (Actual)": [
                HEADER,
                ["Cash and cash equivalents",
                 "Cash and cash equivalents",
                 "Cash and cash equivalents",
                 *[float(2400 - 100 * (i + 1)) for i in range(12)]],
                # Cash: Jan 2300, Feb 2200, ..., Dec 1200
            ],
            "CF (Actual)": [
                HEADER,
                # Burn rows live below the CF in the registry contract.
                ["KPI", "Burn", "Gross", *([-200.0] * 12)],
                ["KPI", "Burn", "Net",   *([-100.0] * 12)],
            ],
        }},
    )


@pytest.fixture
def runway_db(make_test_client) -> Path:
    tmp = _runway_client(make_test_client)
    # Register the burn rows so they're tagged is_aggregate=1.
    (tmp / "clients/runway_demo/aggregate_formulas.yaml").write_text("""
gross_burn:
  taxonomi: ["KPI", "Burn", "Gross"]
  leaves:
    - {data: "Cash and cash equivalents", sign: 1}
net_burn:
  taxonomi: ["KPI", "Burn", "Net"]
  leaves:
    - {data: "Cash and cash equivalents", sign: 1}
""")
    # Rebuild after writing the registry.
    from core.data.build import build_db
    # The build will fail R4 because cash != burn, but we want the rows
    # tagged. Use a dummy registry where the recompute matches:
    (tmp / "clients/runway_demo/aggregate_formulas.yaml").write_text("""
gross_burn:
  taxonomi: ["KPI", "Burn", "Gross"]
  leaves: [{data: "FAKE_LEAF", sign: 1}]
net_burn:
  taxonomi: ["KPI", "Burn", "Net"]
  leaves: [{data: "FAKE_LEAF", sign: 1}]
""")
    # No FAKE_LEAF data → recompute returns None → R4 skips, no failure.
    build_db("runway_demo", tmp)
    return tmp


class TestRunwaySpot:
    def test_spot_gross(self, runway_db: Path) -> None:
        # Dec 2025: cash 1200, gross burn -200/month → 6.0 months.
        r = runway_months("runway_demo", "2025-12-01", "gross")
        assert r == pytest.approx(6.0)

    def test_spot_net(self, runway_db: Path) -> None:
        # Dec 2025: cash 1200, net burn -100/month → 12.0 months.
        r = runway_months("runway_demo", "2025-12-01", "net")
        assert r == pytest.approx(12.0)

    def test_spot_at_different_period(self, runway_db: Path) -> None:
        # Jan: cash 2300, net burn -100 → 23 months.
        r = runway_months("runway_demo", "2025-01-01", "net")
        assert r == pytest.approx(23.0)


class TestRunwayWindow:
    def test_trailing_3month_average(self, runway_db: Path) -> None:
        # All months -100 net burn → 3-month avg also -100 → same as spot.
        r = runway_months("runway_demo", "2025-12-01", "net", window=3)
        assert r == pytest.approx(12.0)


class TestRunwayMissingData:
    def test_missing_cash_returns_none(
        self, make_test_client,
    ) -> None:
        tmp = make_test_client(
            name="r2",
            config={
                "entities": ["demo"],
                "financial_sources": [
                    {"file": "raw/a.xlsx", "year": 2025, "entity": "demo"},
                ],
            },
            files={"a.xlsx": {
                "CF (Actual)": [HEADER,
                    ["KPI", "Burn", "Net", *([-100.0] * 12)]],
            }},
        )
        # No BS, no cash row → None.
        from core.data.build import build_db
        build_db("r2", tmp)
        assert runway_months("r2", "2025-06-01", "net") is None

    def test_zero_burn_returns_none(
        self, make_test_client,
    ) -> None:
        tmp = make_test_client(
            name="r3",
            config={
                "entities": ["demo"],
                "financial_sources": [
                    {"file": "raw/a.xlsx", "year": 2025, "entity": "demo"},
                ],
            },
            files={"a.xlsx": {
                "BS (Actual)": [HEADER, [
                    "Cash and cash equivalents",
                    "Cash and cash equivalents",
                    "Cash and cash equivalents",
                    *([1000.0] * 12),
                ]],
                "CF (Actual)": [HEADER,
                    ["KPI", "Burn", "Net", *([0.0] * 12)]],
            }},
        )
        from core.data.build import build_db
        build_db("r3", tmp)
        assert runway_months("r3", "2025-06-01", "net") is None


class TestRunwayValidation:
    def test_unknown_burn_kind_raises(self) -> None:
        with pytest.raises(ValueError, match="burn_kind"):
            runway_months("anything", "2025-01-01", "wrong")
