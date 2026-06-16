"""Guards the model-maintenance skill against drift.

The skill (`SKILL.md` + `references/almacena.md`) cites repo paths and
`core/model` API symbols. If a doc names a file or function that does not exist,
following the skill cold breaks. These tests assert every cited repo path and
every `core/model.<symbol>` reference actually resolves. Gitignored client data
(`.xlsx`) is exempt — only tracked source/docs/config are checked.
"""

from __future__ import annotations

import re
from pathlib import Path

import core.model as model

SKILL_DIR = Path(".claude/skills/model-maintenance")
SKILL_FILES = [SKILL_DIR / "SKILL.md", SKILL_DIR / "references" / "almacena.md"]

# Inline-code spans, e.g. `clients/almacena/model_rules.yaml` or `core/model.read_contract`.
_CODE_SPAN = re.compile(r"`([^`]+)`")
_REPO_PATH = re.compile(r"^(?:clients|core|scripts|tests)/[\w./ -]+\.(md|yaml|yml|py)$")
_MODEL_SYMBOL = re.compile(r"core[./]model\.(\w+)")


def _spans(text: str) -> list[str]:
    return _CODE_SPAN.findall(text)


def test_skill_files_exist():
    for f in SKILL_FILES:
        assert f.exists(), f"skill file missing: {f}"


def test_cited_repo_paths_exist():
    missing = []
    for f in SKILL_FILES:
        for span in _spans(f.read_text()):
            if _REPO_PATH.match(span) and not Path(span).exists():
                missing.append(f"{f.name}: {span}")
    assert not missing, "skill cites non-existent repo paths: " + "; ".join(missing)


def test_cited_model_api_symbols_are_package_exports():
    bad = []
    for f in SKILL_FILES:
        for symbol in _MODEL_SYMBOL.findall(f.read_text()):
            if not hasattr(model, symbol):
                bad.append(f"{f.name}: core/model.{symbol}")
    assert not bad, (
        "skill cites core/model symbols that are not package-level exports "
        "(use the real entry points, e.g. build_flow().trace_precedents): " + "; ".join(bad)
    )


def test_skill_is_not_marked_scaffold():
    for f in SKILL_FILES:
        assert "STATUS: scaffold" not in f.read_text(), f"{f.name} still marked scaffold"
