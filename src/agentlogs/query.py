"""Named SQL query runner.

Named query files live in src/agentlogs/queries/*.sql. Parameters are
supplied as :name bindings; callers pass them as keyword args. Queries
that match the glob are returned from `list_queries()`; execute via
`run_query(db, name, **params)`.
"""

from __future__ import annotations

import re
import sqlite3
from importlib import resources
from typing import Any


_PARAM_RE = re.compile(r"(?<!:)[:]([a-zA-Z_][a-zA-Z0-9_]*)")


def list_queries() -> list[str]:
    """Sorted list of named queries available in the package."""
    pkg = resources.files(__name__.split(".")[0]).joinpath("queries")
    return sorted(
        entry.name[:-4]
        for entry in pkg.iterdir()
        if entry.name.endswith(".sql")
    )


def _load_query(name: str) -> str:
    pkg = resources.files(__name__.split(".")[0]).joinpath("queries")
    path = pkg.joinpath(f"{name}.sql")
    if not path.is_file():
        raise KeyError(f"no named query '{name}' (see list_queries())")
    return path.read_text(encoding="utf-8")


def query_params(name: str) -> list[str]:
    """Return the :name parameters referenced by a named query, in source order."""
    sql = _load_query(name)
    seen: list[str] = []
    for match in _PARAM_RE.finditer(sql):
        param = match.group(1)
        if param not in seen:
            seen.append(param)
    return seen


def run_query(
    db: sqlite3.Connection,
    name: str,
    **params: Any,
) -> list[sqlite3.Row]:
    """Execute a named query with the given parameters.

    Raises ValueError if required parameters are missing or extra ones passed.
    """
    sql = _load_query(name)
    required = set(query_params(name))
    supplied = set(params.keys())
    if missing := (required - supplied):
        raise ValueError(f"query '{name}' requires parameters: {sorted(missing)}")
    if extra := (supplied - required):
        raise ValueError(f"query '{name}' does not accept: {sorted(extra)}")
    return list(db.execute(sql, params))
