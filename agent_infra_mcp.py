"""Agent Infra MCP — section-based search over agent-infra, phenome, and genomics research.

NOTE: This server indexes files at startup. After editing this file (new scopes,
new directories, scoring changes), the running MCP instance must be restarted
for changes to take effect. New scopes/features will return errors against the
old server.
"""

import logging
import re
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

from fastmcp import Context, FastMCP
from mcp.types import TextContent

log = logging.getLogger(__name__)

META_ROOT = Path(__file__).parent

# Files to index within agent-infra. Relative to META_ROOT.
INCLUDE_GLOBS = [
    "*.md",
    "research/*.md",
    "research/compiled/*.md",
    ".model-review/*/synthesis.md",
]

# Skip these paths (relative to META_ROOT).
EXCLUDE_PREFIXES = [
    ".claude/",
    ".model-review/",      # default exclude; synthesis.md re-included above
    "todos.md",
    "node_modules/",
    "downloads/",
]

# Cross-project research directories. Whitelist (default-deny).
# Only these directories are indexed — new dirs must be explicitly added.
# Privacy: phenome/docs/entities/ has self/ and companies/ subdirs with personal
# data. Only genes/ is safe to share.
_PROJECTS_ROOT = Path.home() / "Projects"
CROSS_PROJECT_INCLUDE = [
    (_PROJECTS_ROOT / "phenome" / "docs" / "research", "phenome"),
    (_PROJECTS_ROOT / "phenome" / "docs" / "entities" / "genes", "phenome"),
    (_PROJECTS_ROOT / "genomics" / "docs" / "research", "genomics"),
]

# Scope categories: scope_name -> list of path substrings or file names
SCOPE_MAP = {
    "hooks": ["hook", "pretool", "posttool", "stop-", "session-init", "session-end",
              "spinning", "reference_data"],
    "failures": ["agent-failure-modes", "failure"],
    "research": ["research/", "frontier-agentic", "search-retrieval"],
    "architecture": ["architecture", "cockpit", "search-retrieval", "claude-code-architecture"],
    "improvement-log": ["improvement-log"],
    "health": ["pots", "intervention", "supplement", "biomarker", "blood-test",
               "differential", "symptom", "circadian", "sleep"],
    "genomics": ["variant", "acmg", "pharmacogenomics", "pgx", "cyp", "hla",
                 "noncoding", "prs", "carrier", "wgs"],
    "genes": ["entities/genes/", "cyp2d6", "cyp2c19", "mthfr", "hla-", "slco",
              "dpyd", "vkorc1", "tpmt"],
}

INSTRUCTIONS = """\
Cross-project knowledge base — markdown research search + paper-status trio
spanning agent-infra, phenome, genomics, and intel.

## Tool: search (markdown sections)
Use for hook design patterns, agent failure modes, architecture decisions,
health/genomics research, gene entity pages, improvement-log findings.
Scopes: all, hooks, failures, research, architecture, improvement-log,
health, genomics, genes.
Do NOT use for: behavioral rules (already in CLAUDE.md), enforcement (hooks).

## Tool trio: paper status before you fetch
Call in order, short-circuit when sufficient:
  1. corpus_lookup(identifier) — canonical store at ~/Projects/corpus/.
     "Do we have the bytes + parsed markdown?" — instant filesystem hit.
  2. cross_attestation_lookup(source_id) — read-only DuckDB federation over
     genomics/phenome/intel knowledge stores. "Has any repo VERIFIED this
     source?" Independent of whether bytes are stored.
  3. corpus_graph_query(paper_id, query) — citation graph at
     ~/Projects/corpus/graph.duckdb. "What does the citation graph say?"
     Requires paper_id from steps 1 or 2.
All three accept DOI, PMID, PMCID, or paper_id forms. Use cross_attestation_lookup's
returned `paper_id` field to chain directly into corpus_lookup or corpus_graph_query.\
"""


# --- Section parsing ---

def _collect_files() -> list[tuple[Path, str]]:
    """Collect .md files from agent-infra (via globs) and cross-project dirs (whitelist).

    Returns (path, display_key) tuples. display_key is:
    - relative path for agent-infra files (e.g., "research/foo.md")
    - project-prefixed path for cross-project files (e.g., "phenome:docs/research/foo.md")
    """
    seen: set[Path] = set()
    files: list[tuple[Path, str]] = []

    # Repo-local files
    for pattern in INCLUDE_GLOBS:
        for p in META_ROOT.glob(pattern):
            if not p.is_file() or p.is_symlink():
                continue
            rel = str(p.relative_to(META_ROOT))
            if any(rel.startswith(ex) for ex in EXCLUDE_PREFIXES):
                if not rel.endswith("synthesis.md"):
                    continue
            if p not in seen:
                seen.add(p)
                files.append((p, rel))

    # Cross-project files (whitelist — default-deny)
    for directory, project_name in CROSS_PROJECT_INCLUDE:
        if not directory.is_dir():
            log.warning("cross-project dir not found: %s", directory)
            continue
        for p in directory.rglob("*.md"):
            if not p.is_file() or p.is_symlink():
                continue
            if p not in seen:
                seen.add(p)
                # Project-prefixed display key
                try:
                    rel = str(p.relative_to(_PROJECTS_ROOT / project_name))
                except ValueError:
                    rel = p.name
                files.append((p, f"{project_name}:{rel}"))

    return sorted(files, key=lambda x: x[1])


def _parse_sections(path: Path, display_key: str) -> list[dict]:
    """Split a markdown file into sections at ## and ### headers."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        log.warning("Failed to read %s", path)
        return []

    sections = []
    lines = text.split("\n")
    current_heading = display_key  # default: file name as heading
    current_level = 1
    current_lines: list[str] = []

    def _flush():
        if current_lines:
            content = "\n".join(current_lines).strip()
            if content:
                sections.append({
                    "file": display_key,
                    "heading": current_heading,
                    "level": current_level,
                    "content": content,
                })

    for line in lines:
        m = re.match(r"^(#{2,3})\s+(.+)", line)
        if m:
            _flush()
            current_level = len(m.group(1))
            current_heading = m.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    _flush()
    return sections


def _get_git_sha() -> str:
    """Get current HEAD short SHA."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=META_ROOT, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


# --- Search ---

def _matches_scope(section: dict, scope: str) -> bool:
    """Check if a section matches the requested scope."""
    if scope == "all":
        return True
    keywords = SCOPE_MAP.get(scope, [])
    file_lower = section["file"].lower()
    heading_lower = section["heading"].lower()
    return any(kw in file_lower or kw in heading_lower for kw in keywords)


def _score_section(section: dict, terms: list[str]) -> int:
    """Score a section by term matches. Higher = better."""
    heading_lower = section["heading"].lower()
    content_lower = section["content"].lower()
    score = 0
    for term in terms:
        if term in heading_lower:
            score += 10  # heading match is high value
        if term in content_lower:
            score += 1
    # Prefer shorter sections (more focused)
    length_penalty = len(section["content"]) // 500
    return score - length_penalty


def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Rough truncation: ~4 chars per token."""
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... (truncated)"


def _search(sections: list[dict], query: str, scope: str, max_tokens: int) -> dict:
    """Search sections by query terms."""
    terms = [t.lower() for t in query.split() if len(t) >= 2]
    if not terms:
        return {"results": [], "meta_commit": _get_git_sha(), "total_matches": 0}

    scored = []
    for s in sections:
        if not _matches_scope(s, scope):
            continue
        score = _score_section(s, terms)
        if score > 0:
            scored.append((score, s))

    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    total_chars = 0
    char_budget = max_tokens * 4

    for score, s in scored:
        content = s["content"]
        remaining = char_budget - total_chars
        if remaining <= 0:
            break
        if len(content) > remaining:
            content = content[:remaining] + "\n... (truncated)"
        results.append({
            "file": s["file"],
            "heading": s["heading"],
            "content": content,
            "relevance": score,
        })
        total_chars += len(content)

    return {
        "results": results,
        "meta_commit": _get_git_sha(),
        "total_matches": len(scored),
        "total_chars": total_chars,
    }


# --- MCP Server ---

_call_count = 0


# --- Cross-project attestation federation ---
# Decision: decisions/2026-05-11-cross-attestation-substrate.md
# Read-only DuckDB ATTACH-style lookup over genomics/phenome/intel knowledge stores.
# Fail-soft on lock contention — one repo failing must not sink the others.

_ATTEST_STORES = [
    ("genomics", _PROJECTS_ROOT / "genomics" / "data" / "knowledge" / "knowledge.duckdb"),
    ("phenome",  _PROJECTS_ROOT / "phenome" / "indexed" / "claims.duckdb"),
    ("intel",    _PROJECTS_ROOT / "intel" / "intel" / "indexed" / "theses.duckdb"),
]

_DOI_RE = re.compile(r"^10\.\d{4,9}/", re.IGNORECASE)
_PMID_RE = re.compile(r"^\d{6,9}$")
_PMCID_RE = re.compile(r"^PMC\d+$", re.IGNORECASE)


def _slugify_doi(doi: str) -> str:
    """Match corpus_lookup / canonical store paper_id derivation."""
    slug = doi.lower()
    for ch in "/.-:":
        slug = slug.replace(ch, "_")
    # Collapse consecutive underscores and strip trailing.
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_")


def _normalize_source_id(s: str) -> dict:
    """Parse a free-form source_id into typed components.

    Accepts: 'doi:10.x/y', '10.x/y', 'pmid:12345', '12345', 'PMC123', 'pmcid:PMC123', 'nct:NCT...'.
    Returns dict with keys: doi, pmid, pmcid, nct, raw, normalized, paper_id (canonical-store form).
    """
    raw = s.strip()
    out = {"doi": None, "pmid": None, "pmcid": None, "nct": None,
           "raw": raw, "normalized": raw, "paper_id": None}
    low = raw.lower()
    if low.startswith("doi:"):
        out["doi"] = raw[4:].strip()
    elif _DOI_RE.match(raw):
        out["doi"] = raw
    elif low.startswith("pmid:"):
        out["pmid"] = raw[5:].strip()
    elif low.startswith("pmcid:"):
        out["pmcid"] = raw[6:].strip().upper()
        if not out["pmcid"].startswith("PMC"):
            out["pmcid"] = "PMC" + out["pmcid"]
    elif _PMCID_RE.match(raw):
        out["pmcid"] = raw.upper()
    elif low.startswith("nct:"):
        out["nct"] = raw[4:].strip().upper()
    elif _PMID_RE.match(raw):
        out["pmid"] = raw
    if out["doi"]:
        out["normalized"] = f"doi:{out['doi']}"
        out["paper_id"] = f"doi_{_slugify_doi(out['doi'])}"
    elif out["pmid"]:
        out["normalized"] = f"pmid:{out['pmid']}"
        out["paper_id"] = f"pmid_{out['pmid']}"
    elif out["pmcid"]:
        out["normalized"] = f"pmcid:{out['pmcid']}"
    elif out["nct"]:
        out["normalized"] = f"nct:{out['nct']}"
    return out


def _query_attestation_store(repo: str, db_path: Path, ids: dict) -> dict:
    """Read-only query against one repo's DuckDB. Fail-soft.

    Returns: {repo, status, count, hits, error?}
    status ∈ {"ok", "missing", "locked", "error"}
    """
    if not db_path.exists():
        return {"repo": repo, "status": "missing", "count": 0, "hits": []}
    try:
        import duckdb
        con = duckdb.connect(str(db_path), read_only=True)
    except Exception as e:
        # IO Error from concurrent writer → mark locked, not fatal.
        msg = str(e)
        if "lock" in msg.lower() or "in use" in msg.lower() or "io error" in msg.lower():
            return {"repo": repo, "status": "locked", "count": 0, "hits": [], "error": msg[:200]}
        return {"repo": repo, "status": "error", "count": 0, "hits": [], "error": msg[:200]}
    try:
        candidates = []
        if ids["doi"]:
            candidates += [ids["doi"], f"doi:{ids['doi']}"]
        if ids["pmid"]:
            candidates += [ids["pmid"], f"pmid:{ids['pmid']}"]
        if ids["pmcid"]:
            candidates += [ids["pmcid"], f"pmcid:{ids['pmcid']}"]
        if ids["nct"]:
            candidates += [ids["nct"], f"nct:{ids['nct']}"]
        candidates += [ids["raw"]]
        candidates = sorted({c for c in candidates if c})

        hits = []
        if repo == "genomics":
            rows = con.execute(
                """SELECT source_id, source_release_id, fetched_at, fetched_via, evidence_depth, status
                   FROM source_observations
                   WHERE source_id IN (SELECT UNNEST(?))
                   ORDER BY fetched_at DESC LIMIT 10""",
                [candidates],
            ).fetchall()
            for r in rows:
                hits.append({
                    "table": "source_observations",
                    "source_id": r[0], "release_id": r[1],
                    "fetched_at": str(r[2]) if r[2] else None,
                    "fetched_via": r[3], "evidence_depth": r[4], "status": r[5],
                })
        elif repo == "phenome":
            # primary_sources has separate doi/pmid/pmcid columns
            rows = con.execute(
                """SELECT primary_source_id, kind, doi, pmid, pmcid, title, year, retrieved_at,
                          retraction_status
                   FROM primary_sources
                   WHERE (doi IS NOT NULL AND doi IN (SELECT UNNEST(?)))
                      OR (pmid IS NOT NULL AND pmid IN (SELECT UNNEST(?)))
                      OR (pmcid IS NOT NULL AND pmcid IN (SELECT UNNEST(?)))
                   LIMIT 10""",
                [
                    [ids["doi"]] if ids["doi"] else [],
                    [ids["pmid"]] if ids["pmid"] else [],
                    [ids["pmcid"]] if ids["pmcid"] else [],
                ],
            ).fetchall()
            for r in rows:
                hits.append({
                    "table": "primary_sources",
                    "primary_source_id": str(r[0]), "kind": r[1],
                    "doi": r[2], "pmid": r[3], "pmcid": r[4],
                    "title": r[5], "year": r[6],
                    "retrieved_at": str(r[7]) if r[7] else None,
                    "retraction_status": r[8],
                })
        elif repo == "intel":
            # filings_and_datasets has doi + ssrn_id; theses tables don't carry raw paper ids directly
            rows = con.execute(
                """SELECT filing_or_dataset_id, kind, doi, title, year, venue, retrieved_at
                   FROM filings_and_datasets
                   WHERE doi IS NOT NULL AND doi IN (SELECT UNNEST(?))
                   LIMIT 10""",
                [[ids["doi"]] if ids["doi"] else []],
            ).fetchall()
            for r in rows:
                hits.append({
                    "table": "filings_and_datasets",
                    "id": r[0], "kind": r[1], "doi": r[2],
                    "title": r[3], "year": r[4], "venue": r[5],
                    "retrieved_at": str(r[6]) if r[6] else None,
                })
        return {"repo": repo, "status": "ok", "count": len(hits), "hits": hits}
    except Exception as e:
        return {"repo": repo, "status": "error", "count": 0, "hits": [], "error": str(e)[:300]}
    finally:
        try:
            con.close()
        except Exception:
            pass


def create_mcp() -> FastMCP:
    @asynccontextmanager
    async def lifespan(server):
        files = _collect_files()
        sections = []
        for path, display_key in files:
            sections.extend(_parse_sections(path, display_key))
        log.info("agent-infra: indexed %d sections from %d files", len(sections), len(files))
        yield {"sections": sections}

    from scripts.mcp_middleware import TelemetryMiddleware

    mcp = FastMCP("agent-infra", instructions=INSTRUCTIONS, lifespan=lifespan,
                  middleware=[TelemetryMiddleware()])

    @mcp.tool()
    def search(
        ctx: Context,
        query: str,
        max_tokens: int = 1000,
        scope: str = "all",
    ) -> list[TextContent]:
        """Search cross-project knowledge: hook designs, agent failure modes,
        architecture decisions, research findings, health/genomics research,
        gene entities. Indexes agent-infra, phenome, and genomics research directories.

        Returns matching sections ranked by relevance. When no results are found,
        returns a structured error with suggested alternative queries. Side effects: none.

        Args:
            query: search terms (matched against section headers and content)
            max_tokens: max response size (default 1000, max 4000)
            scope: filter by category - "all", "hooks", "failures", "research",
                   "architecture", "improvement-log", "health", "genomics", "genes"
        """
        global _call_count
        _call_count += 1

        max_tokens = min(max(max_tokens, 50), 4000)

        import json

        def _wrap(data: dict) -> list[TextContent]:
            text = json.dumps(data, indent=2, default=str)
            size_hint = max(len(text) * 2, 16000)  # 2x headroom, min 16K
            return [TextContent(
                type="text", text=text,
                _meta={"anthropic/maxResultSizeChars": size_hint},
            )]

        if scope not in ("all", *SCOPE_MAP):
            return _wrap({
                "error": True,
                "error_type": "INVALID_SCOPE",
                "message": f"Unknown scope '{scope}'",
                "recoverable": True,
                "suggested_action": f"use one of: all, {', '.join(SCOPE_MAP.keys())}",
                "call_number": _call_count,
            })

        if not query or not query.strip():
            return _wrap({
                "error": True,
                "error_type": "EMPTY_QUERY",
                "message": "Query string is empty",
                "recoverable": True,
                "suggested_action": "provide search terms (2+ chars each)",
                "call_number": _call_count,
            })

        sections = ctx.lifespan_context["sections"]
        result = _search(sections, query, scope, max_tokens)
        result["call_number"] = _call_count

        if not result["results"]:
            result["error"] = True
            result["error_type"] = "NO_RESULTS"
            result["recoverable"] = True
            result["suggested_action"] = (
                "try broader terms, different scope, or check if the topic exists "
                "in research/ files"
            )

        return _wrap(result)

    @mcp.tool()
    def cross_attestation_lookup(ctx: Context, source_id: str) -> list[TextContent]:
        """Check whether any local repo (genomics, phenome, intel) has already
        attested to a paper/source identifier — independent of whether the
        bytes are in the canonical store.

        Part of the unified paper-status trio (call in this order):
          1. corpus_lookup(identifier) — do we have bytes + parsed markdown?
          2. cross_attestation_lookup(source_id) — has any repo VERIFIED it?
             (this tool — read-only DuckDB federation, fail-soft on lock)
          3. corpus_graph_query(paper_id, ...) — what does the citation
             graph say once we have a paper_id?

        Use BEFORE fetching a paper to detect duplicate work across repos.
        Federation is read-only over each repo's DuckDB store; one repo
        being write-locked returns status='locked' for that repo only.

        Args:
            source_id: DOI, PMID, PMCID, or NCT identifier. Accepted forms:
                - "doi:10.1038/nature12345"
                - "10.1038/nature12345"
                - "pmid:12345678" or "12345678"
                - "pmcid:PMC1234567" or "PMC1234567"
                - "nct:NCT01234567"

        Returns:
            JSON with:
              source_id: parsed components (doi/pmid/pmcid/nct/raw/normalized)
              paper_id: canonical-store form (e.g. "doi_10_1038_nature12345"),
                        suitable for direct corpus_lookup / corpus_graph_query
              found_in: list of repos with attestation hits
              results: per-repo hits with sample rows
              errors: per-repo error strings (e.g., for locked databases)
        """
        import json
        ids = _normalize_source_id(source_id)
        results = []
        errors = {}
        for repo, db_path in _ATTEST_STORES:
            r = _query_attestation_store(repo, db_path, ids)
            results.append(r)
            if r["status"] not in ("ok", "missing"):
                errors[repo] = r.get("error", r["status"])
        found_in = [r["repo"] for r in results if r["count"] > 0]
        payload = {
            "source_id": ids,
            "paper_id": ids.get("paper_id"),  # canonical-store form when DOI/PMID
            "found_in": found_in,
            "any_hits": bool(found_in),
            "results": results,
            "errors": errors,
        }
        text = json.dumps(payload, indent=2, default=str)
        return [TextContent(
            type="text", text=text,
            _meta={"anthropic/maxResultSizeChars": max(len(text) * 2, 16000)},
        )]

    @mcp.tool()
    def corpus_graph_query(
        ctx: Context,
        paper_id: str,
        query: str = "cited-by",
        stance: str | None = None,
        limit: int = 50,
    ) -> list[TextContent]:
        """Query the canonical paper citation graph at ~/Projects/corpus/graph.duckdb.

        Use AFTER corpus_lookup confirms a paper is in the store to surface
        the actual evidence around it (supporting/contrasting snippets, not
        just counts).

        Args:
            paper_id: The canonical paper_id (doi_*, pmid_*, or sha_*).
            query: One of:
              - "cited-by" (default): incoming citances; combine with stance="contrasting"
                to surface counter-evidence.
              - "cites": outgoing references.
              - "contradictions": incoming citances tagged cito:disagreesWith
                or stance_class='contrasting', joined with retraction status
                of the citing paper.
            stance: Optional filter for cited-by — "supporting" | "contrasting"
                | "mentioning".
            limit: Max edges (default 50, capped at 200).

        Returns:
            {paper_id, query, count, edges: [{paper_id, stance_class, stance_cito,
             confidence, snippet, retraction_status?}]}
        """
        import json as _json
        from pathlib import Path as _Path

        store_root = _Path.home() / "Projects" / "corpus"
        db_path = store_root / "graph.duckdb"

        def _wrap(payload: dict) -> list[TextContent]:
            text = _json.dumps(payload, indent=2, default=str)
            return [TextContent(
                type="text", text=text,
                _meta={"anthropic/maxResultSizeChars": max(len(text) * 2, 16000)},
            )]

        if not db_path.exists():
            return _wrap({
                "error": True,
                "error_type": "GRAPH_NOT_BUILT",
                "message": "graph.duckdb does not exist",
                "recoverable": True,
                "suggested_action": "run 'corpus maintain --rebuild-graph'",
            })

        try:
            import duckdb
        except ImportError:
            return _wrap({
                "error": True,
                "error_type": "DUCKDB_NOT_INSTALLED",
                "message": "duckdb python package not available in this environment",
                "recoverable": False,
            })

        capped = max(1, min(limit, 200))

        try:
            con = duckdb.connect(str(db_path), read_only=True)
        except Exception as exc:
            return _wrap({
                "error": True,
                "error_type": "GRAPH_OPEN_FAILED",
                "message": str(exc),
            })

        try:
            if query == "cites":
                sql = (
                    "SELECT cited_paper_id, stance_class, stance_cito, "
                    "stance_confidence, snippet, citing_section, citing_page "
                    "FROM edges WHERE citing_paper_id = ? LIMIT ?"
                )
                rows = con.execute(sql, [paper_id, capped]).fetchall()
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
                        return _wrap({
                            "error": True,
                            "error_type": "INVALID_STANCE",
                            "message": f"stance must be supporting|contrasting|mentioning, got {stance!r}",
                        })
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
                sql = (
                    "SELECT e.citing_paper_id, e.snippet, e.stance_cito, "
                    "e.stance_confidence, p.retraction_status "
                    "FROM edges e LEFT JOIN papers p ON p.paper_id = e.citing_paper_id "
                    "WHERE e.cited_paper_id = ? "
                    "AND (e.stance_class = 'contrasting' OR "
                    "     e.stance_cito LIKE '%disagreesWith%') "
                    "LIMIT ?"
                )
                rows = con.execute(sql, [paper_id, capped]).fetchall()
                edges = [{
                    "paper_id": r[0], "snippet": r[1], "stance_cito": r[2],
                    "confidence": r[3], "retraction_status": r[4],
                } for r in rows]
            else:
                return _wrap({
                    "error": True,
                    "error_type": "INVALID_QUERY",
                    "message": f"query must be 'cited-by' | 'cites' | 'contradictions', got {query!r}",
                })
        finally:
            con.close()

        return _wrap({
            "paper_id": paper_id,
            "query": query,
            "stance_filter": stance,
            "count": len(edges),
            "edges": edges,
        })

    @mcp.tool()
    def corpus_lookup(
        ctx: Context,
        identifier: str,
    ) -> list[TextContent]:
        """Look up a paper in the canonical local store at ~/Projects/corpus/.

        Use BEFORE fetching a paper from upstream — the cache hit is
        instantaneous (filesystem only) and gives you parsed markdown +
        citance edges if they exist.

        Complementary to cross_attestation_lookup: that one tells you "has any
        repo VERIFIED this source", this one tells you "do we have the BYTES
        + PARSE locally".

        Args:
            identifier: DOI ("10.1038/...", optionally prefixed "doi:"),
                PMID (bare digits, optionally prefixed "pmid:"), or
                paper_id ("doi_10_1038_...", "pmid_12345", "sha_abc...").

        Returns:
            {paper_id, present, doi, pmid, title, parsed_present,
             citances_in_count, citances_out_count, used_by, paths}
        """
        import json as _json
        from pathlib import Path as _Path

        # Resolve identifier → paper_id
        ident = identifier.strip()
        if ident.startswith("doi:"):
            ident = ident[4:].strip()
        if ident.startswith("pmid:"):
            ident = ident[5:].strip()

        if ident.startswith(("doi_", "pmid_", "sha_")):
            paper_id = ident
        elif "/" in ident or "." in ident:
            slug = ident.lower()
            for ch in "/.-:":
                slug = slug.replace(ch, "_")
            paper_id = f"doi_{slug}"
        elif ident.isdigit():
            paper_id = f"pmid_{ident}"
        else:
            payload = {
                "error": True,
                "error_type": "UNRECOGNIZED_IDENTIFIER",
                "message": f"Cannot resolve {identifier!r} to a paper_id",
                "recoverable": True,
                "suggested_action": "pass a DOI, PMID, or paper_id (doi_*, pmid_*, sha_*)",
            }
            text = _json.dumps(payload, indent=2)
            return [TextContent(type="text", text=text)]

        store_root = _Path.home() / "Projects" / "corpus"
        paper_dir = store_root / paper_id

        if not paper_dir.exists():
            payload = {
                "paper_id": paper_id,
                "present": False,
                "message": f"Not in store; ingest via 'corpus ingest --pdf <path> --doi <doi>'",
            }
            text = _json.dumps(payload, indent=2)
            return [TextContent(type="text", text=text)]

        meta_path = paper_dir / "metadata.json"
        meta = {}
        if meta_path.exists():
            try:
                meta = _json.loads(meta_path.read_text())
            except Exception:
                meta = {}

        parsed_md = paper_dir / "parsed" / "paper.md"
        cin = paper_dir / "citances_in.jsonl"
        cout = paper_dir / "citances_out.jsonl"
        idx = paper_dir / "INDEX.json"

        def _count_lines(p: _Path) -> int:
            if not p.exists():
                return 0
            return sum(1 for ln in p.read_text(errors="replace").splitlines() if ln.strip())

        used_by = []
        if idx.exists():
            try:
                used_by = _json.loads(idx.read_text()).get("used_by", [])
            except Exception:
                pass

        payload = {
            "paper_id": paper_id,
            "present": True,
            "doi": meta.get("doi"),
            "pmid": meta.get("pmid"),
            "title": meta.get("title"),
            "fabio_class": meta.get("fabio_class"),
            "retraction_status": meta.get("retraction_status", "unknown"),
            "parsed_present": parsed_md.exists(),
            "parsed_sha256": meta.get("parsed_sha256"),
            "pdf_sha256": meta.get("pdf_sha256"),
            "citances_in_count": _count_lines(cin),
            "citances_out_count": _count_lines(cout),
            "used_by": used_by,
            "paths": {
                "dir": str(paper_dir),
                "pdf": str(paper_dir / "paper.pdf"),
                "parsed_md": str(parsed_md) if parsed_md.exists() else None,
                "metadata": str(meta_path) if meta_path.exists() else None,
            },
            "graph_db": str(store_root / "graph.duckdb") if (store_root / "graph.duckdb").exists() else None,
        }
        text = _json.dumps(payload, indent=2, default=str)
        return [TextContent(
            type="text", text=text,
            _meta={"anthropic/maxResultSizeChars": max(len(text) * 2, 16000)},
        )]

    return mcp


def main():
    create_mcp().run()


if __name__ == "__main__":
    main()
