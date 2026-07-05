"""Recalculate a workbook with LibreOffice headless.

openpyxl never evaluates formulas, and the OFFSET-heavy models here also defeat
pure-Python engines (e.g. ``formulas`` has no OFFSET). LibreOffice recomputes every
formula on load — for workbooks saved with ``fullCalcOnLoad`` — and ``--convert-to``
writes the cached results, which we then read back with ``data_only=True``.

This is the authoritative verification gate: integrity checks assert on the values
returned here, not on cached or oracle-derived numbers.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import openpyxl

# Standard macOS install location (soffice is not on PATH there by default).
_MAC = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")


class SofficeNotFound(RuntimeError):
    """Raised when no LibreOffice ``soffice`` binary can be located."""


def _find_soffice() -> str:
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    if _MAC.exists():
        return str(_MAC)
    raise SofficeNotFound(
        "LibreOffice 'soffice' not found on PATH or at "
        f"{_MAC}; install it (e.g. `apt-get install libreoffice-calc` or "
        "`brew install --cask libreoffice`) to run the model recalc gate."
    )


def soffice_available() -> bool:
    """True if a LibreOffice binary can be located (for test ``skipif``)."""
    try:
        _find_soffice()
        return True
    except SofficeNotFound:
        return False


def recalc(path: str | Path, *, timeout: float = 180.0):
    """Recompute ``path`` with LibreOffice and return the loaded (``data_only``)
    openpyxl workbook. Uses an isolated LO user profile so a running desktop
    instance doesn't hijack the headless conversion.

    Raises ``SofficeNotFound`` if LibreOffice is absent, or ``RuntimeError`` if
    the conversion produces no output.
    """
    soffice = _find_soffice()
    src = Path(path)
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(
            [soffice, "--headless",
             f"-env:UserInstallation=file://{td}/profile",
             "--convert-to", "xlsx", "--outdir", td, str(src)],
            check=True, capture_output=True, timeout=timeout,
        )
        out = Path(td) / f"{src.stem}.xlsx"
        if not out.exists():
            raise RuntimeError(
                f"LibreOffice recalc produced no output for {src.name}"
            )
        return openpyxl.load_workbook(out, data_only=True)
