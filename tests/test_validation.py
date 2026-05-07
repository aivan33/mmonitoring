"""Tests for core.data.validation.run_assertions."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.data.validation import Assertion, Result, run_assertions


class TestRunAssertions:
    def test_passes_when_within_tolerance(self) -> None:
        results = run_assertions(
            [Assertion(name="ok", check=lambda: 100.5, expected=100.0)],
            tolerance=1.0,
        )
        assert len(results) == 1
        assert results[0].passed is True
        assert results[0].observed == 100.5
        assert results[0].delta == pytest.approx(0.5)

    def test_fails_when_outside_tolerance(self) -> None:
        results = run_assertions(
            [Assertion(name="off", check=lambda: 102.0, expected=100.0)],
            tolerance=1.0,
        )
        assert results[0].passed is False
        assert results[0].delta == pytest.approx(2.0)

    def test_observed_none_is_a_failure(self) -> None:
        results = run_assertions(
            [Assertion(name="missing", check=lambda: None, expected=100.0)],
            tolerance=1.0,
        )
        assert results[0].passed is False
        assert results[0].observed is None

    def test_check_exception_caught_as_failure(self) -> None:
        def boom() -> float:
            raise RuntimeError("kaboom")
        results = run_assertions(
            [Assertion(name="raises", check=boom, expected=100.0)],
            tolerance=1.0,
        )
        assert results[0].passed is False
        assert "kaboom" in (results[0].error or "")

    def test_runs_all_even_if_one_fails(self) -> None:
        results = run_assertions(
            [
                Assertion(name="a", check=lambda: 100.0, expected=100.0),
                Assertion(name="b", check=lambda: (_ for _ in ()).throw(RuntimeError("x")),
                          expected=0.0),
                Assertion(name="c", check=lambda: 50.0, expected=50.0),
            ],
            tolerance=1.0,
        )
        assert [r.passed for r in results] == [True, False, True]

    def test_default_tolerance_is_one_eur(self) -> None:
        results = run_assertions(
            [Assertion(name="edge", check=lambda: 100.99, expected=100.0)],
        )
        assert results[0].passed is True


class TestResult:
    def test_result_is_a_dataclass(self) -> None:
        r = Result(name="x", expected=1.0, observed=1.0, delta=0.0,
                   passed=True, error=None)
        assert r.name == "x"
        assert r.passed
