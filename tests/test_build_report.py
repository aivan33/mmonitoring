"""Smoke tests for ``scripts/build_report.py``.

End-to-end: invokes the orchestrator's main() against the real farada
files and verifies it produces the expected outputs.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import scripts.build_report as br


_REPO = Path(__file__).resolve().parent.parent
_REAL_MR = _REPO / "clients" / "farada" / "raw" / "mr_2026-03.xlsx"


@pytest.mark.skipif(not _REAL_MR.exists(),
                    reason="real farada files not present")
def test_extract_only_writes_taxonomi(tmp_path, monkeypatch, capsys):
    """--extract-only against the real farada files writes the new
    populated taxonomi xlsx."""
    monkeypatch.setattr(sys, "argv",
                        ["build_report.py", "farada", "2026-03",
                         "--extract-only"])
    rc = br.main()
    assert rc == 0
    captured = capsys.readouterr()
    assert "extract: wrote" in captured.out

    out_taxonomi = (_REPO / "clients" / "farada" / "raw"
                    / "taxonomi_act_2026-03.xlsx")
    assert out_taxonomi.exists()


def test_unknown_client_returns_error(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv",
                        ["build_report.py", "nope", "2026-03",
                         "--extract-only"])
    rc = br.main()
    assert rc == 1
    err = capsys.readouterr().err
    assert "config" in err.lower()


def test_bad_period_returns_error(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv",
                        ["build_report.py", "farada", "2026",
                         "--extract-only"])
    rc = br.main()
    assert rc == 2
    err = capsys.readouterr().err
    assert "YYYY-MM" in err


def test_variance_phase_writes_outputs(monkeypatch, capsys, tmp_path):
    """--variance-only runs end-to-end and writes variance.{md,csv}."""
    monkeypatch.setattr(sys, "argv",
                        ["build_report.py", "farada", "2026-02",
                         "--variance-only"])
    rc = br.main()
    assert rc == 0
    repo = Path(__file__).resolve().parent.parent
    out_dir = repo / "clients" / "farada" / "reports" / "2026-02"
    assert (out_dir / "variance.md").exists()
    assert (out_dir / "variance.csv").exists()


