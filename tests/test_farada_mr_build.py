"""Guard the Farada MR build mechanism.

The BWA data sheet is a faithful account-keyed paste of the raw German BWA
Jahresübersicht. We prove that by reproducing April from raw 04 and diffing
against the delivered workbook — it must match to the cent.

These tests depend on gitignored client data, so they skip cleanly when the
raw files / workbook are not present (e.g. CI or another machine).
"""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_farada_mr.py"
MR_04 = ROOT / "clients" / "farada" / "raw" / "mr_2026-04.xlsx"
RAW_04_BWA = ROOT / "clients" / "farada" / "raw" / "accounting" / "04-2026" / \
    "BWA - Jahresübersicht 04-2026.xlsx"

pytestmark = pytest.mark.skipif(
    not (MR_04.exists() and RAW_04_BWA.exists()),
    reason="Farada client data not present (gitignored)",
)


def _load_build():
    spec = importlib.util.spec_from_file_location("build_farada_mr", BUILD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_bwa_reproduces_april_exactly():
    """BWA April column, rebuilt from raw 04, matches the delivered workbook."""
    build = _load_build()
    assert build.golden_april(MR_04) == 0


def test_only_bwa_is_a_paste_target():
    """Guard the deliberate scope: only BWA is mechanically pasted.

    CR-Upload / ControllingReport BWA / BS sheets carry manual judgement and
    must not be silently added back as paste targets.
    """
    build = _load_build()
    assert set(build.DATA_SHEETS) == {"BWA"}
