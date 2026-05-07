"""CLI: build the monthly reporting pack for a client.

Pipeline (--all):
    extract → reload-DB → variance → commentary

Each phase has its own flag for partial runs. Outputs land under
``clients/<client>/reports/<YYYY-MM>/``.

Usage:
    python scripts/build_report.py <client> <YYYY-MM> [--extract-only|--variance-only|--commentary-only|--all]
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import yaml

# Make the repo root importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.report.mr import extract_month
from core.report.mr_to_taxonomi import populate_taxonomi


_REPO = Path(__file__).resolve().parent.parent


def _parse_period(s: str) -> dt.date:
    parts = s.split("-")
    if len(parts) != 2:
        raise ValueError(f"period must be YYYY-MM, got {s!r}")
    return dt.date(int(parts[0]), int(parts[1]), 1)


def _load_client_config(client: str) -> tuple[Path, dict]:
    client_dir = _REPO / "clients" / client
    cfg_path = client_dir / "config.yaml"
    if not cfg_path.exists():
        raise FileNotFoundError(f"no config at {cfg_path}")
    return client_dir, yaml.safe_load(cfg_path.read_text())


def _require_use_case(cfg: dict, client: str, required: str) -> None:
    use_cases = cfg.get("use_cases") or []
    if required not in use_cases:
        raise SystemExit(
            f"error: client {client!r} doesn't subscribe to use_case "
            f"{required!r} (use_cases={use_cases}). Add it to "
            f"clients/{client}/config.yaml or run a different script."
        )


def _phase_extract(
    client_dir: Path, config: dict, period: dt.date,
) -> Path:
    """MR → populated taxonomi-actual. Returns path to the new taxonomi."""
    reporting = config.get("reporting") or {}
    mr_path = client_dir / reporting["mr_source"]
    mapping_path = client_dir / reporting["mapping"]
    mapping = yaml.safe_load(mapping_path.read_text())

    extracts = {
        stmt: extract_month(mr_path, mapping, period.year, period.month, stmt)
        for stmt in ("IS", "CF", "BS")
    }

    prev_taxonomi = _find_prev_taxonomi(client_dir, config, period)
    out_taxonomi = client_dir / "raw" / f"taxonomi_act_{period.strftime('%Y-%m')}.xlsx"
    populate_taxonomi(prev_taxonomi, extracts, period.year, period.month, out_taxonomi)
    print(f"  extract: wrote {out_taxonomi.relative_to(_REPO)}")
    return out_taxonomi


def _find_prev_taxonomi(client_dir: Path, config: dict,
                        period: dt.date) -> Path:
    """The latest taxonomi-actual file for the same year, strictly before
    ``period``. Falls back to the first source if no month-stamped file is
    found (handles the case where only a year-level taxonomi exists)."""
    sources = config.get("financial_sources", []) or []
    candidates = []
    for src in sources:
        path = client_dir / src["file"]
        name = path.stem
        if "act" not in name.lower():
            continue
        # Prefer files whose name ends in _YYYY-MM.
        if name.endswith(period.strftime("%Y-%m")):
            continue  # don't pick the file we're about to write
        candidates.append(path)
    if not candidates:
        raise FileNotFoundError(
            f"no prior taxonomi-actual file in financial_sources for {period}"
        )
    return candidates[-1]


def _phase_variance(*_args, **_kwargs) -> None:
    raise NotImplementedError("variance phase ships in F3 (Task 9)")


def _phase_commentary(*_args, **_kwargs) -> None:
    raise NotImplementedError("commentary phase ships in F4 (Task 11)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a client's monthly reporting pack.")
    parser.add_argument("client")
    parser.add_argument("period", help="YYYY-MM")
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument("--extract-only", action="store_true",
                     help="run MR → populated taxonomi only")
    grp.add_argument("--variance-only", action="store_true",
                     help="run variance phase only (F3)")
    grp.add_argument("--commentary-only", action="store_true",
                     help="run commentary phase only (F4)")
    grp.add_argument("--all", action="store_true",
                     help="run the full pipeline (default)")
    args = parser.parse_args()

    try:
        period = _parse_period(args.period)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        client_dir, config = _load_client_config(args.client)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    _require_use_case(config, args.client, "report")

    run_all = args.all or not (args.extract_only or args.variance_only
                                or args.commentary_only)

    print(f"build_report {args.client} {period.strftime('%Y-%m')}")
    try:
        if args.extract_only or run_all:
            _phase_extract(client_dir, config, period)
        if args.variance_only or run_all:
            _phase_variance(client_dir, config, period)
        if args.commentary_only or run_all:
            _phase_commentary(client_dir, config, period)
    except NotImplementedError as exc:
        print(f"  {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"build_report failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(f"build_report {args.client} {period.strftime('%Y-%m')}: done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
