"""corpus-mcp — dedicated MCP server for the local corpus store.

Phase 3 of the substrate-migration plan
(.claude/plans/2026-05-11-substrate-migration.md).

Owns five tools, all scoped to the local corpus store at $CORPUS_ROOT
(default ~/Projects/corpus):

    corpus_lookup(source_id)            do we have bytes + parsed markdown?
    corpus_graph_query(paper_id, …)     citation graph queries
    corpus_annotations_query(...)       reverse-query graph.duckdb
                                        annotations table (Phase 2)
    corpus_ingest(pdf_path|url, …)      drive corpus_core.ingest.{ingest_pdf,
                                        ingest_url}
    corpus_dashboard()                  source counts + per-repo activity
                                        + recent annotations

Tool budget: 5 (within the 5-15 documented MCP-tool budget; well under the
20-tool hard cap per round-2 finding 7).

corpus never writes annotations.jsonl. Cross-repo attestation is enforced at
each repo's mutation gateway via a transactional outbox that drains to
corpus_core.annotate (the sole writer) — see
decisions/2026-05-26-cross-attestation-substrate-v2.md. The old
agent-orchestrated record_verdict + corpus_attest ritual (substrate v1) is
retired: 0 invocations in 9 months, and an MCP write tool here was a dual-write
backdoor around the gateway outbox invariant.
"""
from __future__ import annotations

import json
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastmcp import Context, FastMCP
from mcp.types import TextContent, ToolAnnotations

# Ensure the local corpus_core is importable when run via uv from agent-infra
_HERE = Path(__file__).resolve().parent
_CORPUS_PKG = _HERE / "corpus" / "packages" / "corpus-core"
if str(_CORPUS_PKG) not in sys.path:
    sys.path.insert(0, str(_CORPUS_PKG))

from corpus_core import store as paper_store  # noqa: E402
from corpus_core.identity import parse_source_identifier  # noqa: E402
from corpus_core.ingest import ingest_pdf, ingest_url  # noqa: E402

log = logging.getLogger(__name__)


_RO = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)
_WRITE = ToolAnnotations(readOnlyHint=False, idempotentHint=True, openWorldHint=False)


INSTRUCTIONS = """\
corpus-mcp — local scientific corpus store.

This server owns L1 corpus operations:
  - corpus_lookup(source_id) — do we have bytes + parsed markdown locally?
  - corpus_graph_query(paper_id, query, stance) — citation graph queries
  - corpus_annotations_query(repo, scope, since, source_id) — reverse lookups
  - corpus_ingest(pdf_path|url, ...) — write a new source into the store
  - corpus_dashboard() — counts + recent activity

corpus does NOT write annotations. Cross-repo attestation is enforced at each
repo's mutation gateway via a transactional outbox that drains to
corpus_core.annotate (the sole writer) — see
decisions/2026-05-26-cross-attestation-substrate-v2.md. There is no
agent-facing attestation call to remember.

NEVER call this MCP from inside another MCP (no MCP-to-MCP).
"""


def _store_root() -> Path:
    return paper_store.store_root()


def _graph_db() -> Path:
    return paper_store.graph_db_path()


def _wrap(payload: dict) -> list[TextContent]:
    text = json.dumps(payload, indent=2, default=str)
    size_hint = max(len(text) * 2, 16000)
    return [TextContent(
        type="text", text=text,
        _meta={"anthropic/maxResultSizeChars": size_hint},
    )]


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------


def create_mcp() -> FastMCP:
    @asynccontextmanager
    async def lifespan(server):
        log.info("corpus-mcp: store_root=%s", _store_root())
        yield {}

    mcp = FastMCP("corpus", instructions=INSTRUCTIONS, lifespan=lifespan)

    # ----- corpus_lookup -----

    @mcp.tool(annotations=_RO)
    def corpus_lookup(ctx: Context, identifier: str) -> list[TextContent]:
        """Look up a source in the canonical local store at ~/Projects/corpus/.

        Use BEFORE fetching from upstream — cache hits are instantaneous and
        return parsed markdown + citance counts if present.

        Args:
            identifier: DOI ("10.1038/...", optionally prefixed "doi:"),
                PMID (bare digits, optionally prefixed "pmid:"), or
                source_id ("doi_10_1038_...", "pmid_12345", "sha_abc...").

        Returns:
            {paper_id, present, doi, pmid, title, parsed_present,
             citances_in_count, citances_out_count, paths}
        """
        ident = identifier.strip()
        if ident.startswith("doi:"):
            ident = ident[4:].strip()
        if ident.startswith("pmid:"):
            ident = ident[5:].strip()

        if ident.startswith(("doi_", "pmid_", "sha_", "pmcid_")):
            paper_id = ident
        elif "/" in ident or "." in ident:
            ids = parse_source_identifier(ident)
            paper_id = ids.get("source_id") or ""
        elif ident.isdigit():
            paper_id = f"pmid_{ident}"
        else:
            return _wrap({
                "error": True,
                "error_type": "UNRECOGNIZED_IDENTIFIER",
                "message": f"Cannot resolve {identifier!r} to a source_id",
                "recoverable": True,
                "suggested_action": "pass a DOI, PMID, or source_id",
            })

        p_dir = paper_store.paper_path(paper_id)
        if not p_dir.exists():
            return _wrap({
                "paper_id": paper_id, "present": False,
                "message": f"Not in store; ingest via 'corpus ingest --pdf <path> --doi <doi>'",
            })

        meta = {}
        meta_path = p_dir / "metadata.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
            except json.JSONDecodeError:
                meta = {}

        # Find any parsed.<parser_id>/page.md
        parsed_present = False
        parsed_paths = []
        for child in sorted(p_dir.iterdir()):
            if child.is_dir() and child.name.startswith("parsed."):
                if (child / "page.md").exists():
                    parsed_present = True
                    parsed_paths.append(str(child / "page.md"))

        cin = p_dir / "citances_in.jsonl"
        cout = p_dir / "citances_out.jsonl"
        ann = p_dir / "annotations.jsonl"

        def _count_lines(p: Path) -> int:
            if not p.exists():
                return 0
            return sum(1 for ln in p.read_text(errors="replace").splitlines() if ln.strip())

        from corpus_core.index import active_annotations_for_source
        active_ann = active_annotations_for_source(paper_id, db_path=_graph_db())
        return _wrap({
            "paper_id": paper_id,
            "present": True,
            "doi": meta.get("doi"),
            "pmid": meta.get("pmid"),
            "title": meta.get("title"),
            "source_type": meta.get("source_type"),
            "retraction_status": meta.get("retraction_status", "unknown"),
            "parsed_present": parsed_present,
            "parsed_pages": parsed_paths,
            "pdf_sha256": meta.get("pdf_sha256"),
            "content_hash": meta.get("content_hash"),
            "citances_in_count": _count_lines(cin),
            "citances_out_count": _count_lines(cout),
            "annotations_count": _count_lines(ann),
            "active_annotations": active_ann,
            "epistemic": {
                "paper_retraction_status": meta.get("retraction_status", "unknown"),
                "active_verdict_count": len(active_ann),
                "attesting_repos": sorted({a["repo"] for a in active_ann if a.get("repo")}),
                "retracted_annotations": [a for a in active_ann if a.get("status") == "retracted"],
            },
            "paths": {
                "dir": str(p_dir),
                "pdf": str(p_dir / "paper.pdf") if (p_dir / "paper.pdf").exists() else None,
                "metadata": str(meta_path) if meta_path.exists() else None,
            },
        })

    # ----- corpus_graph_query -----

    @mcp.tool(annotations=_RO)
    def corpus_graph_query(
        ctx: Context,
        paper_id: str,
        query: str = "cited-by",
        stance: str | None = None,
        limit: int = 50,
    ) -> list[TextContent]:
        """Query the canonical citation graph at ~/Projects/corpus/graph.duckdb.

        Args:
            paper_id: doi_*, pmid_*, sha_*.
            query: 'cited-by' | 'cites' | 'contradictions'.
            stance: optional filter for cited-by — supporting|contrasting|mentioning.
            limit: max edges (capped at 200).
        """
        db_path = _graph_db()
        if not db_path.exists():
            return _wrap({
                "error": True, "error_type": "GRAPH_NOT_BUILT",
                "message": "graph.duckdb missing",
                "suggested_action": "run 'corpus maintain --rebuild-graph'",
            })

        try:
            import duckdb
        except ImportError:
            return _wrap({"error": True, "error_type": "DUCKDB_NOT_INSTALLED"})

        capped = max(1, min(limit, 200))
        try:
            con = duckdb.connect(str(db_path), read_only=True)
        except Exception as exc:
            return _wrap({"error": True, "error_type": "GRAPH_OPEN_FAILED", "message": str(exc)})

        try:
            if query == "cites":
                rows = con.execute(
                    "SELECT cited_paper_id, stance_class, stance_cito, "
                    "stance_confidence, snippet, citing_section, citing_page "
                    "FROM edges WHERE citing_paper_id = ? LIMIT ?",
                    [paper_id, capped],
                ).fetchall()
                edges = [{
                    "paper_id": r[0], "stance_class": r[1], "stance_cito": r[2],
                    "confidence": r[3], "snippet": r[4],
                    "citing_section": r[5], "citing_page": r[6],
                } for r in rows]
            elif query == "cited-by":
                base_sql = (
                    "SELECT citing_paper_id, stance_class, stance_cito, "
                    "stance_confidence, snippet, citing_section, citing_page "
                    "FROM edges WHERE cited_paper_id = ?"
                )
                params: list = [paper_id]
                if stance:
                    if stance not in ("supporting", "contrasting", "mentioning"):
                        return _wrap({"error": True, "error_type": "INVALID_STANCE"})
                    base_sql += " AND stance_class = ?"
                    params.append(stance)
                base_sql += " LIMIT ?"
                params.append(capped)
                rows = con.execute(base_sql, params).fetchall()
                edges = [{
                    "paper_id": r[0], "stance_class": r[1], "stance_cito": r[2],
                    "confidence": r[3], "snippet": r[4],
                    "citing_section": r[5], "citing_page": r[6],
                } for r in rows]
            elif query == "contradictions":
                rows = con.execute(
                    "SELECT e.citing_paper_id, e.snippet, e.stance_cito, "
                    "e.stance_confidence, p.retraction_status "
                    "FROM edges e LEFT JOIN papers p ON p.paper_id = e.citing_paper_id "
                    "WHERE e.cited_paper_id = ? "
                    "AND (e.stance_class = 'contrasting' OR e.stance_cito LIKE '%disagreesWith%') "
                    "LIMIT ?",
                    [paper_id, capped],
                ).fetchall()
                edges = [{
                    "paper_id": r[0], "snippet": r[1], "stance_cito": r[2],
                    "confidence": r[3], "retraction_status": r[4],
                } for r in rows]
            else:
                return _wrap({"error": True, "error_type": "INVALID_QUERY"})
        finally:
            con.close()

        return _wrap({
            "paper_id": paper_id, "query": query, "stance_filter": stance,
            "count": len(edges), "edges": edges,
        })

    # ----- corpus_annotations_query -----

    @mcp.tool(annotations=_RO)
    def corpus_annotations_query(
        ctx: Context,
        repo: str | None = None,
        scope: str | None = None,
        since: str | None = None,
        until: str | None = None,
        source_id: str | None = None,
        actor_id: str | None = None,
        limit: int = 100,
    ) -> list[TextContent]:
        """Reverse-query the graph.duckdb annotations table (Phase 2 projection).

        All args are optional filters. Empty filter set returns the most
        recent `limit` annotations (capped at 500).
        """
        try:
            import duckdb
        except ImportError:
            return _wrap({"error": True, "error_type": "DUCKDB_NOT_INSTALLED"})

        db_path = _graph_db()
        if not db_path.exists():
            return _wrap({"error": True, "error_type": "GRAPH_NOT_BUILT",
                          "suggested_action": "run 'corpus maintain --rebuild-annotations-index'"})

        capped = max(1, min(limit, 500))
        clauses: list[str] = []
        params: list = []
        if repo:
            clauses.append("repo = ?")
            params.append(repo)
        if scope:
            clauses.append("scope = ?")
            params.append(scope)
        if source_id:
            clauses.append("source_id = ?")
            params.append(source_id)
        if actor_id:
            clauses.append("actor_id = ?")
            params.append(actor_id)
        if since:
            clauses.append("recorded_at >= ?")
            params.append(since)
        if until:
            clauses.append("recorded_at <= ?")
            params.append(until)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(capped)

        try:
            con = duckdb.connect(str(db_path), read_only=True)
            rows = con.execute(
                f"SELECT annotation_id, source_id, repo, actor_type, actor_id, "
                f"scope, tool, output_uri, status, asserted_at, recorded_at "
                f"FROM annotations_current{where} "
                f"ORDER BY recorded_at DESC LIMIT ?",
                params,
            ).fetchall()
            con.close()
        except Exception as exc:
            return _wrap({"error": True, "error_type": "QUERY_FAILED", "message": str(exc)})

        results = [
            {
                "annotation_id": r[0], "source_id": r[1], "repo": r[2],
                "actor_type": r[3], "actor_id": r[4], "scope": r[5],
                "tool": r[6], "output_uri": r[7], "status": r[8],
                "asserted_at": r[9], "recorded_at": r[10],
            }
            for r in rows
        ]
        return _wrap({"count": len(results), "results": results})

    # ----- corpus_ingest -----

    @mcp.tool(annotations=_WRITE)
    def corpus_ingest(
        ctx: Context,
        pdf_path: str | None = None,
        url: str | None = None,
        doi: str | None = None,
        pmid: str | None = None,
        title: str | None = None,
        source_type: str | None = None,
        parser: str | None = None,
    ) -> list[TextContent]:
        """Ingest a PDF (file path) or URL into the corpus store.

        Returns the ingested source_id and parsed metadata.
        """
        if not (pdf_path or url):
            return _wrap({"error": True, "error_type": "MISSING_INPUT",
                          "message": "Provide pdf_path or url"})
        try:
            if pdf_path:
                meta = ingest_pdf(
                    Path(pdf_path), doi=doi, pmid=pmid, title=title,
                    source_type=source_type or "paper", parser=parser,
                )
            else:
                meta = ingest_url(
                    url,  # type: ignore[arg-type]
                    title=title,
                    source_type=source_type or "webpage",
                    parser=parser,
                )
            return _wrap({"status": "ok", "source_id": meta["source_id"], "metadata": meta})
        except Exception as exc:
            return _wrap({"error": True, "error_type": "INGEST_FAILED", "message": str(exc)})

    # ----- corpus_dashboard -----

    @mcp.tool(annotations=_RO)
    def corpus_dashboard(ctx: Context) -> list[TextContent]:
        """Stats: source count by type, annotation count by repo, recent activity."""
        root = _store_root()
        sources = list(paper_store.iter_papers())
        source_types: dict[str, int] = {}
        for sid in sources:
            meta_path = root / sid / "metadata.json"
            if meta_path.exists():
                try:
                    st = json.loads(meta_path.read_text()).get("source_type") or "unknown"
                except json.JSONDecodeError:
                    st = "malformed"
            else:
                st = "no-metadata"
            source_types[st] = source_types.get(st, 0) + 1

        per_repo: dict[str, int] = {}
        recent: list[dict] = []
        try:
            import duckdb
            con = duckdb.connect(str(_graph_db()), read_only=True)
            for repo, n in con.execute(
                "SELECT repo, COUNT(*) FROM annotations_current GROUP BY repo"
            ).fetchall():
                per_repo[repo] = n
            for r in con.execute(
                "SELECT annotation_id, source_id, repo, scope, recorded_at "
                "FROM annotations_current ORDER BY recorded_at DESC LIMIT 10"
            ).fetchall():
                recent.append({
                    "annotation_id": r[0], "source_id": r[1], "repo": r[2],
                    "scope": r[3], "recorded_at": r[4],
                })
            con.close()
        except Exception as exc:
            log.warning("dashboard duckdb query failed: %s", exc)

        return _wrap({
            "store_root": str(root),
            "source_count": len(sources),
            "source_types": source_types,
            "annotations_by_repo": per_repo,
            "recent_annotations": recent,
        })

    return mcp


def main():
    create_mcp().run()


if __name__ == "__main__":
    main()
