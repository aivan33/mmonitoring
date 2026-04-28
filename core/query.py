"""Public query surface for the monitoring DB.

These helpers are the *only* thing Stage 2 (charts) imports. The DB shape
is hidden behind them — anything that needs to look at a financials row
goes through one of these functions.

Connection lifecycle: every call opens, queries, closes. No module-level
state. Tests can override the repo root via the ``_ROOT`` module attribute.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import yaml


# Tests monkeypatch this to redirect lookups at a tmp_path.
_ROOT: Path | None = None


def _root() -> Path:
    return _ROOT if _ROOT is not None else Path(__file__).resolve().parent.parent


def _client_dir(client: str) -> Path:
    return _root() / "clients" / client


def _db_path(client: str) -> Path:
    return _client_dir(client) / "data" / f"{client}.db"


def _config(client: str) -> dict:
    return yaml.safe_load((_client_dir(client) / "config.yaml").read_text())


def _resolve_entity(client: str, entity: str | None) -> str:
    if entity is not None:
        return entity
    entities = _config(client).get("entities", [])
    if len(entities) == 1:
        return entities[0]
    raise ValueError(
        f"client {client!r} has multiple entities ({entities}); "
        f"pass entity= explicitly"
    )


def _to_iso(d: dt.date | str) -> str:
    return d.isoformat() if isinstance(d, dt.date) else d


def _connect(client: str) -> sqlite3.Connection:
    return sqlite3.connect(_db_path(client))


# ---------------------------------------------------------------------------
# get_value
# ---------------------------------------------------------------------------

def get_value(
    data: str,
    grp: str,
    subgroup: str,
    period_date: dt.date | str,
    scenario: str = "actual",
    *,
    client: str,
    entity: str | None = None,
) -> float | None:
    entity = _resolve_entity(client, entity)
    with _connect(client) as conn:
        row = conn.execute(
            "SELECT value FROM financials WHERE "
            "period_date=? AND entity=? AND scenario=? "
            "AND data=? AND grp=? AND subgroup=?",
            (_to_iso(period_date), entity, scenario, data, grp, subgroup),
        ).fetchone()
    return None if row is None else row[0]


# ---------------------------------------------------------------------------
# get_statement
# ---------------------------------------------------------------------------

def get_statement(
    statement: str,
    period_date: dt.date | str,
    scenarios: tuple[str, ...] = ("actual", "realistic"),
    *,
    client: str,
    entity: str | None = None,
) -> pd.DataFrame:
    entity = _resolve_entity(client, entity)
    placeholders = ",".join(["?"] * len(scenarios))
    sql = (
        "SELECT period_date, scenario, data, grp, subgroup, "
        "       display_order, value "
        "FROM financials "
        f"WHERE statement=? AND period_date=? AND entity=? "
        f"AND scenario IN ({placeholders}) "
        "ORDER BY scenario, display_order ASC"
    )
    with _connect(client) as conn:
        df = pd.read_sql_query(
            sql, conn,
            params=(statement, _to_iso(period_date), entity, *scenarios),
        )
    return df


# ---------------------------------------------------------------------------
# get_aggregation
# ---------------------------------------------------------------------------

def get_aggregation(
    data: str,
    period_date: dt.date | str,
    scenario: str = "actual",
    level: str = "data",
    *,
    client: str,
    entity: str | None = None,
) -> pd.Series:
    if level not in ("data", "grp", "subgroup"):
        raise ValueError(
            f"unknown level {level!r}; expected 'data' | 'grp' | 'subgroup'"
        )
    entity = _resolve_entity(client, entity)
    period = _to_iso(period_date)

    with _connect(client) as conn:
        if level == "data":
            row = conn.execute(
                "SELECT SUM(value) FROM financials "
                "WHERE data=? AND period_date=? AND scenario=? AND entity=?",
                (data, period, scenario, entity),
            ).fetchone()
            value = row[0] if row else None
            return pd.Series([value], index=[data], name="value")

        if level == "grp":
            rows = conn.execute(
                "SELECT grp, SUM(value) FROM financials "
                "WHERE data=? AND period_date=? AND scenario=? AND entity=? "
                "GROUP BY grp ORDER BY MIN(display_order)",
                (data, period, scenario, entity),
            ).fetchall()
            return pd.Series(
                [v for _, v in rows], index=[g for g, _ in rows], name="value",
            )

        # level == 'subgroup'
        rows = conn.execute(
            "SELECT grp, subgroup, SUM(value) FROM financials "
            "WHERE data=? AND period_date=? AND scenario=? AND entity=? "
            "GROUP BY grp, subgroup ORDER BY MIN(display_order)",
            (data, period, scenario, entity),
        ).fetchall()
        idx = pd.MultiIndex.from_tuples(
            [(g, sg) for g, sg, _ in rows], names=("grp", "subgroup"),
        )
        return pd.Series([v for _, _, v in rows], index=idx, name="value")


# ---------------------------------------------------------------------------
# get_trend
# ---------------------------------------------------------------------------

def get_trend(
    data: str,
    grp: str | None = None,
    subgroup: str | None = None,
    scenario: str = "actual",
    start_date: dt.date | str | None = None,
    end_date: dt.date | str | None = None,
    *,
    client: str,
    entity: str | None = None,
) -> pd.Series:
    entity = _resolve_entity(client, entity)
    where = ["data=?", "scenario=?", "entity=?"]
    args: list[Any] = [data, scenario, entity]
    if grp is not None:
        where.append("grp=?")
        args.append(grp)
    if subgroup is not None:
        where.append("subgroup=?")
        args.append(subgroup)
    if start_date is not None:
        where.append("period_date>=?")
        args.append(_to_iso(start_date))
    if end_date is not None:
        where.append("period_date<=?")
        args.append(_to_iso(end_date))

    sql = (
        "SELECT period_date, SUM(value) FROM financials "
        f"WHERE {' AND '.join(where)} "
        "GROUP BY period_date ORDER BY period_date"
    )
    with _connect(client) as conn:
        rows = conn.execute(sql, args).fetchall()

    idx = [dt.date.fromisoformat(d) for d, _ in rows]
    vals = [v for _, v in rows]
    return pd.Series(vals, index=idx, name=data)


# ---------------------------------------------------------------------------
# ytd
# ---------------------------------------------------------------------------

def ytd(
    data: str,
    year: int,
    grp: str | None = None,
    subgroup: str | None = None,
    scenario: str = "actual",
    through_month: int = 12,
    *,
    client: str,
    entity: str | None = None,
) -> float:
    series = get_trend(
        data,
        grp=grp,
        subgroup=subgroup,
        scenario=scenario,
        start_date=dt.date(year, 1, 1),
        end_date=dt.date(year, through_month, 1),
        client=client,
        entity=entity,
    )
    return float(series.dropna().sum())


# ---------------------------------------------------------------------------
# get_line
# ---------------------------------------------------------------------------

def get_line(
    data: str,
    grp: str | None = None,
    subgroup: str | None = None,
    scenarios: tuple[str, ...] = ("actual", "realistic"),
    periods: Iterable[dt.date | str] | None = None,
    *,
    client: str,
    entity: str | None = None,
) -> pd.DataFrame:
    entity = _resolve_entity(client, entity)
    where = ["data=?", "entity=?"]
    args: list[Any] = [data, entity]
    if grp is not None:
        where.append("grp=?")
        args.append(grp)
    if subgroup is not None:
        where.append("subgroup=?")
        args.append(subgroup)
    if scenarios:
        placeholders = ",".join(["?"] * len(scenarios))
        where.append(f"scenario IN ({placeholders})")
        args.extend(scenarios)
    if periods is not None:
        period_list = list(periods)
        placeholders = ",".join(["?"] * len(period_list))
        where.append(f"period_date IN ({placeholders})")
        args.extend(_to_iso(p) for p in period_list)

    sql = (
        "SELECT period_date, scenario, data, grp, subgroup, value "
        "FROM financials "
        f"WHERE {' AND '.join(where)} "
        "ORDER BY period_date, scenario, display_order"
    )
    with _connect(client) as conn:
        return pd.read_sql_query(sql, conn, params=args)


# ---------------------------------------------------------------------------
# to_csv
# ---------------------------------------------------------------------------

def to_csv(query_result: Any, path: str | Path) -> None:
    """Convenience: dump a query result to CSV. Wraps scalars/dicts into a
    single-row DataFrame so any of the helpers' return types just work."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(query_result, pd.DataFrame):
        query_result.to_csv(path, index=False)
    elif isinstance(query_result, pd.Series):
        query_result.to_frame().to_csv(path)
    elif isinstance(query_result, dict):
        pd.DataFrame([query_result]).to_csv(path, index=False)
    elif query_result is None or isinstance(query_result, (int, float, str)):
        pd.DataFrame([{"value": query_result}]).to_csv(path, index=False)
    else:
        raise TypeError(
            f"to_csv: don't know how to serialize {type(query_result).__name__}"
        )
