"""Cross-repo source identity crosswalk.

Maps a repo's local identifier (e.g. intel's filing UUID, phenome's
doc_id) to the canonical corpus source_id (doi_*, pmid_*, sha_*) when
the local entity references or IS a canonical scientific source.

Why typed links instead of owl:sameAs (Raad et al., swj2430): the
"sameAs Problem" — two things called sameAs may be the same record,
two records about the same thing, the same surface with different
content, etc. Schema.org's typed properties (mainEntityOfPage, about,
subjectOf, cites, derivedFrom) preserve the actual relation. We bless
`sameAs` only for the strict-identity case; everything else uses a
specific link_type.

PK is composite (repo, repo_local_id, corpus_source_id, link_type) so
the SAME (repo, local_id, corpus_id) triple can carry BOTH
mainEntityOfPage AND cites simultaneously (an intel filing that IS
about a paper AND cites it). Strong-identity defaults
(`sameAs`, `mainEntityOfPage`) for resolve_repo_to_corpus.

Phase B of .claude/plans/2026-05-27-knowledge-infra-next-foundations.md.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Optional

from .schema_version import verify_graph_schema
from .store import graph_db_path

if TYPE_CHECKING:
    import duckdb


VALID_LINK_TYPES = frozenset({
    "sameAs",          # strict identity (use sparingly)
    "mainEntityOfPage",  # this resource IS the canonical surface for the entity
    "about",           # this resource IS ABOUT the entity
    "subjectOf",       # the entity is the subject of this resource
    "cites",           # this resource cites the entity
    "derivedFrom",     # this resource is derived from the entity
})

VALID_CONFIDENCE = frozenset({"asserted", "inferred", "unverified"})

# Strong-identity link types for resolve_repo_to_corpus default. Caller
# explicitly broadens to include 'cites' etc. when they want it.
STRONG_IDENTITY_LINKS: tuple[str, ...] = ("sameAs", "mainEntityOfPage")


def _open_rw(db_path: Path, retries: int = 3, backoff_ms: int = 100):
    """Brief writer connection with bounded retry on IOException
    (concurrent writer)."""
    import duckdb

    last_exc: Optional[Exception] = None
    for attempt in range(retries):
        try:
            return duckdb.connect(str(db_path), read_only=False)
        except duckdb.IOException as exc:
            last_exc = exc
            if attempt + 1 < retries:
                time.sleep(backoff_ms / 1000.0)
    assert last_exc is not None
    raise last_exc


def insert_crosswalk(
    *,
    repo: str,
    repo_local_id: str,
    corpus_source_id: str,
    link_type: str,                       # REQUIRED — no default
    asserted_by: str,                     # REQUIRED
    confidence: str = "asserted",
    db_path: Optional[Path] = None,
) -> None:
    """Insert one crosswalk row. Idempotent on (repo, repo_local_id,
    corpus_source_id, link_type) — composite PK + ON CONFLICT DO NOTHING.
    """
    if link_type not in VALID_LINK_TYPES:
        raise ValueError(
            f"unknown link_type {link_type!r}; valid: {sorted(VALID_LINK_TYPES)}"
        )
    if confidence not in VALID_CONFIDENCE:
        raise ValueError(
            f"unknown confidence {confidence!r}; valid: {sorted(VALID_CONFIDENCE)}"
        )
    if not asserted_by.startswith("urn:agent:"):
        raise ValueError(
            f"asserted_by must be 'urn:agent:<type>:<name>[@<version>]'; got {asserted_by!r}"
        )

    target = db_path or graph_db_path()
    verify_graph_schema(target)

    # _connect ensures schema_sql has been applied (which creates the
    # crosswalk table on first run + bumps meta). After that we open a
    # brief RW connection for the INSERT.
    from .index import _connect
    _connect(target).close()

    con = _open_rw(target)
    try:
        con.execute(
            """
            INSERT INTO source_identity_crosswalk
                (repo, repo_local_id, corpus_source_id,
                 link_type, confidence, asserted_by)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (repo, repo_local_id, corpus_source_id, link_type)
                DO NOTHING
            """,
            [repo, repo_local_id, corpus_source_id, link_type, confidence, asserted_by],
        )
    finally:
        con.close()


def resolve_repo_to_corpus(
    repo: str,
    repo_local_id: str,
    *,
    link_types: Iterable[str] = STRONG_IDENTITY_LINKS,
    db_path: Optional[Path] = None,
) -> Optional[str]:
    """Resolve (repo, local_id) → corpus_source_id via strong-identity
    links. Returns None if no crosswalk row matches.

    When multiple matches exist (e.g. mainEntityOfPage to TWO different
    corpus_ids — bug in writer), returns the FIRST by primary key order;
    caller is responsible for noticing degenerate cases (use
    resolve_corpus_to_repos for multi-target inspection).
    """
    import duckdb

    target = db_path or graph_db_path()
    if not Path(target).exists():
        return None
    try:
        con = duckdb.connect(str(target), read_only=True)
    except duckdb.IOException:
        return None
    try:
        placeholders = ",".join("?" * len(tuple(link_types)))
        link_types_list = list(link_types)
        try:
            row = con.execute(
                f"""
                SELECT corpus_source_id
                FROM source_identity_crosswalk
                WHERE repo = ?
                  AND repo_local_id = ?
                  AND link_type IN ({placeholders})
                ORDER BY link_type
                LIMIT 1
                """,
                [repo, repo_local_id, *link_types_list],
            ).fetchone()
        except (duckdb.BinderException, duckdb.CatalogException):
            return None
        return row[0] if row else None
    finally:
        con.close()


def resolve_corpus_to_repos(
    corpus_source_id: str,
    *,
    link_types: Optional[Iterable[str]] = None,
    db_path: Optional[Path] = None,
) -> list[tuple[str, str, str]]:
    """Reverse lookup: every (repo, local_id, link_type) that points at
    this corpus source. Returns empty list when DB / table missing /
    no matches."""
    import duckdb

    target = db_path or graph_db_path()
    if not Path(target).exists():
        return []
    try:
        con = duckdb.connect(str(target), read_only=True)
    except duckdb.IOException:
        return []
    try:
        if link_types is None:
            sql = """
                SELECT repo, repo_local_id, link_type
                FROM source_identity_crosswalk
                WHERE corpus_source_id = ?
                ORDER BY repo, repo_local_id, link_type
                """
            params: list = [corpus_source_id]
        else:
            link_types_list = list(link_types)
            placeholders = ",".join("?" * len(link_types_list))
            sql = f"""
                SELECT repo, repo_local_id, link_type
                FROM source_identity_crosswalk
                WHERE corpus_source_id = ?
                  AND link_type IN ({placeholders})
                ORDER BY repo, repo_local_id, link_type
                """
            params = [corpus_source_id, *link_types_list]
        try:
            rows = con.execute(sql, params).fetchall()
        except (duckdb.BinderException, duckdb.CatalogException):
            return []
        return [(r[0], r[1], r[2]) for r in rows]
    finally:
        con.close()


__all__ = [
    "STRONG_IDENTITY_LINKS",
    "VALID_CONFIDENCE",
    "VALID_LINK_TYPES",
    "insert_crosswalk",
    "resolve_corpus_to_repos",
    "resolve_repo_to_corpus",
]
