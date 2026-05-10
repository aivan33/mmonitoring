"""CLI: rebuild a client's SQLite DB from its config.yaml.

Usage: ``python scripts/build_db.py <client>``
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the repo root importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.data.build import build_db


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python scripts/build_db.py <client>", file=sys.stderr)
        return 2
    client = sys.argv[1]
    base_dir = Path(__file__).resolve().parent.parent
    try:
        summary = build_db(client, base_dir)
    except Exception as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return 1

    print(f"built {summary['db_path']}")
    print(f"  financials rows: {summary['financials_rows']}")
    for src in summary["sources"]:
        print(f"  - {src['file']}: {src['rows']} rows")
    if summary.get("operational_kpi_rows"):
        print(f"  operational KPI rows: {summary['operational_kpi_rows']}")
        for src in summary.get("operational_sources", []):
            print(f"  - {src['file']} ({src['format']}): {src['rows']} rows")
    print(f"  duration: {summary['duration_s']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
