"""Agent Infra MCP — section-based search over agent-infra, phenome, and genomics research.

Phase 3 of substrate-migration plan: corpus tools (corpus_lookup,
corpus_graph_query, corpus_attest, etc.) live in scripts/corpus_mcp.py.
cross_attestation_lookup is dropped (per §J.1: agent orchestrates
record_verdict + corpus_attest, no cross-repo federation tool).

NOTE: This server reloads indexed markdown when whitelisted files change. After
editing this file itself (new scopes, directories, scoring changes), restart the
running MCP instance.
"""

import logging
import json
import re
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

from fastmcp import Context, FastMCP
from mcp.types import TextContent

from scripts.common.skill_objects import collect_skill_objects, iter_default_roots, load_object_content

log = logging.getLogger(__name__)

META_ROOT = Path(__file__).parent

INCLUDE_GLOBS = [
    "*.md",
    "research/*.md",
    "research/compiled/*.md",
    ".model-review/*/synthesis.md",
]

EXCLUDE_PREFIXES = [
    ".claude/",
    ".model-review/",      # default exclude; synthesis.md re-included above
    "todos.md",
    "node_modules/",
    "downloads/",
]

# Whitelist (default-deny) cross-project research dirs.
# Privacy: phenome/docs/entities/ has self/ and companies/ subdirs with personal
# data. Only genes/ is safe to share.
_PROJECTS_ROOT = Path.home() / "Projects"
CROSS_PROJECT_INCLUDE = [
    (_PROJECTS_ROOT / "phenome" / "docs" / "research", "phenome"),
    (_PROJECTS_ROOT / "phenome" / "docs" / "entities" / "genes", "phenome"),
    (_PROJECTS_ROOT / "genomics" / "docs" / "research", "genomics"),
]

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
Cross-project markdown research search across agent-infra, phenome, genomics.

Use for: hook design patterns, agent failure modes, architecture decisions,
health/genomics research, gene entity pages, improvement-log findings.
Scopes: all, hooks, failures, research, architecture, improvement-log,
health, genomics, genes.

NOT for: behavioral rules (already in CLAUDE.md), enforcement (hooks).

For corpus operations (lookup, graph query, attestation, ingest), use the
corpus-mcp server (scripts/corpus_mcp.py).

Skill registry tools expose compact, read-only skill objects, modules, lenses,
and role-agent contracts. Use them to lazily load phase-specific instructions
instead of recursively reading every file under `.claude/skills/`.
"""


# --- Section parsing ---

def _collect_files() -> list[tuple[Path, str]]:
    """Collect .md files from agent-infra (via globs) and cross-project dirs (whitelist)."""
    seen: set[Path] = set()
    files: list[tuple[Path, str]] = []

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

    for directory, project_name in CROSS_PROJECT_INCLUDE:
        if not directory.is_dir():
            log.warning("cross-project dir not found: %s", directory)
            continue
        for p in directory.rglob("*.md"):
            if not p.is_file() or p.is_symlink():
                continue
            if p not in seen:
                seen.add(p)
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
    current_heading = display_key
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


def _index_sections() -> tuple[list[dict], int, float]:
    files = _collect_files()
    sections = []
    latest_mtime = 0.0
    for path, display_key in files:
        try:
            latest_mtime = max(latest_mtime, path.stat().st_mtime)
        except OSError:
            continue
        sections.extend(_parse_sections(path, display_key))
    return sections, len(files), latest_mtime


def _get_git_sha() -> str:
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
    if scope == "all":
        return True
    keywords = SCOPE_MAP.get(scope, [])
    file_lower = section["file"].lower()
    heading_lower = section["heading"].lower()
    return any(kw in file_lower or kw in heading_lower for kw in keywords)


def _score_section(section: dict, terms: list[str]) -> int:
    heading_lower = section["heading"].lower()
    content_lower = section["content"].lower()
    score = 0
    for term in terms:
        if term in heading_lower:
            score += 10
        if term in content_lower:
            score += 1
    length_penalty = len(section["content"]) // 500
    return score - length_penalty


def _search(sections: list[dict], query: str, scope: str, max_tokens: int) -> dict:
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


def create_mcp() -> FastMCP:
    @asynccontextmanager
    async def lifespan(server):
        sections, file_count, index_mtime = _index_sections()
        log.info("agent-infra: indexed %d sections from %d files", len(sections), file_count)
        yield {"sections": sections, "index_mtime": index_mtime}

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
        gene entities. Indexes agent-infra, phenome, and genomics research dirs.

        Returns matching sections ranked by relevance. When no results are found,
        returns a structured error with suggested alternative queries. Side
        effects: none.

        Args:
            query: search terms (matched against section headers and content)
            max_tokens: max response size (default 1000, max 4000)
            scope: filter by category - "all", "hooks", "failures", "research",
                   "architecture", "improvement-log", "health", "genomics", "genes"
        """
        global _call_count
        _call_count += 1

        max_tokens = min(max(max_tokens, 50), 4000)

        def _wrap(data: dict) -> list[TextContent]:
            text = json.dumps(data, indent=2, default=str)
            size_hint = max(len(text) * 2, 16000)
            return [TextContent(
                type="text", text=text,
                _meta={"anthropic/maxResultSizeChars": size_hint},
            )]

        if scope not in ("all", *SCOPE_MAP):
            return _wrap({
                "error": True, "error_type": "INVALID_SCOPE",
                "message": f"Unknown scope '{scope}'",
                "recoverable": True,
                "suggested_action": f"use one of: all, {', '.join(SCOPE_MAP.keys())}",
                "call_number": _call_count,
            })

        if not query or not query.strip():
            return _wrap({
                "error": True, "error_type": "EMPTY_QUERY",
                "message": "Query string is empty",
                "recoverable": True,
                "suggested_action": "provide search terms (2+ chars each)",
                "call_number": _call_count,
            })

        sections, file_count, index_mtime = _index_sections()
        if index_mtime > ctx.lifespan_context.get("index_mtime", 0):
            ctx.lifespan_context["sections"] = sections
            ctx.lifespan_context["index_mtime"] = index_mtime
            log.info("agent-infra: reindexed %d sections from %d files", len(sections), file_count)
        else:
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

    def _wrap_json(data: dict) -> list[TextContent]:
        text = json.dumps(data, indent=2, default=str)
        size_hint = max(len(text) * 2, 16000)
        return [TextContent(
            type="text", text=text,
            _meta={"anthropic/maxResultSizeChars": size_hint},
        )]

    def _fresh_skill_objects() -> list[dict]:
        # Refresh on each call. Collection is cheap at current scale and avoids
        # serving stale skill edits for the lifetime of an MCP process.
        return [obj.to_json() for obj in collect_skill_objects(iter_default_roots(None))]

    def _matching_rows(ctx: Context) -> list[dict]:
        return [dict(row) for row in _fresh_skill_objects()]

    def _with_content(row: dict, max_chars: int) -> dict:
        out = dict(row)
        out["content"] = load_object_content(row, max_chars)
        return out

    @mcp.tool()
    def get_skill_object(
        ctx: Context,
        name: str,
        project: str = "",
        include_content: bool = False,
        max_chars: int = 6000,
    ) -> list[TextContent]:
        """Return one skill-object manifest row by object id or name.

        Side effects: none. Use this before loading a module/lens/reference body.
        `name` may be a full object id such as `intel:asset-decision.lens.drawdown-context`
        or a simple object/name such as `drawdown-context`.
        """
        rows = _matching_rows(ctx)
        matches = []
        for row in rows:
            if project and row.get("project") != project:
                continue
            if name in {row.get("object_id"), row.get("name")}:
                matches.append(row)
        if not matches:
            matches = [
                row for row in rows
                if (not project or row.get("project") == project)
                and name.lower() in str(row.get("object_id", "")).lower()
            ]
        result = {"query": name, "project": project or None, "matches": matches[:10]}
        if include_content:
            result["matches"] = [_with_content(row, max_chars) for row in result["matches"]]
        return _wrap_json(result)

    @mcp.tool()
    def get_cognitive_lens(
        ctx: Context,
        lens_name: str,
        project: str = "",
        max_chars: int = 6000,
    ) -> list[TextContent]:
        """Return a registered LensDoc and its fallback file content when present."""
        rows = [
            row for row in _matching_rows(ctx)
            if row.get("object_type") == "LensDoc"
            and (not project or row.get("project") == project)
            and (
                lens_name == row.get("name")
                or lens_name == row.get("object_id")
                or lens_name.lower() in str(row.get("object_id", "")).lower()
            )
        ]
        result = {
            "query": lens_name,
            "project": project or None,
            "matches": [_with_content(row, max_chars) for row in rows[:10]],
        }
        return _wrap_json(result)

    @mcp.tool()
    def get_module_contract(
        ctx: Context,
        module_name: str,
        project: str = "",
        max_chars: int = 6000,
    ) -> list[TextContent]:
        """Return a registered ModuleDoc or RoleAgentContract with fallback content."""
        rows = [
            row for row in _matching_rows(ctx)
            if row.get("object_type") in {"ModuleDoc", "RoleAgentContract"}
            and (not project or row.get("project") == project)
            and (
                module_name == row.get("name")
                or module_name == row.get("object_id")
                or module_name.lower() in str(row.get("object_id", "")).lower()
            )
        ]
        result = {
            "query": module_name,
            "project": project or None,
            "matches": [_with_content(row, max_chars) for row in rows[:10]],
        }
        return _wrap_json(result)

    return mcp


def main():
    create_mcp().run()


if __name__ == "__main__":
    main()
