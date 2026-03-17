"""Meta Knowledge MCP — section-based search over meta project .md files."""

import logging
import re
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

from fastmcp import Context, FastMCP

log = logging.getLogger(__name__)

META_ROOT = Path(__file__).parent

# Files to index. Relative to META_ROOT.
INCLUDE_GLOBS = [
    "*.md",
    "research/*.md",
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

# Scope categories: scope_name -> list of path substrings or file names
SCOPE_MAP = {
    "hooks": ["hook", "pretool", "posttool", "stop-", "session-init", "session-end",
              "spinning", "reference_data"],
    "failures": ["agent-failure-modes", "failure"],
    "research": ["research/", "frontier-agentic", "search-retrieval"],
    "architecture": ["architecture", "cockpit", "search-retrieval", "claude-code-architecture"],
    "improvement-log": ["improvement-log"],
}

INSTRUCTIONS = """\
Meta project knowledge base — hook designs, agent failure modes, prompting
patterns, architecture decisions, and research findings across all projects.

Use search_meta when you need:
- Hook design patterns (how to write hooks, gotchas, event types)
- Agent failure mode reference (22 documented modes with mitigations)
- Prompting best practices (XML tags, model-specific tips)
- Architecture decisions (search/retrieval, git workflow, cross-project)
- Session-analyst findings (improvement-log entries)
- Research findings (self-modification, prompt structure, native features)

Do NOT use for: behavioral rules (already in CLAUDE.md), enforcement (use hooks).\
"""


# --- Section parsing ---

def _collect_files() -> list[Path]:
    """Collect .md files matching INCLUDE_GLOBS, minus EXCLUDE_PREFIXES."""
    seen: set[Path] = set()
    files: list[Path] = []

    for pattern in INCLUDE_GLOBS:
        for p in META_ROOT.glob(pattern):
            if not p.is_file():
                continue
            rel = str(p.relative_to(META_ROOT))
            # .model-review/*/synthesis.md is explicitly included via glob
            # but other .model-review/ files are excluded
            if any(rel.startswith(ex) for ex in EXCLUDE_PREFIXES):
                # Allow synthesis.md through
                if not rel.endswith("synthesis.md"):
                    continue
            if p not in seen:
                seen.add(p)
                files.append(p)

    # Also skip symlinks (AGENTS.md -> CLAUDE.md, GEMINI.md -> CLAUDE.md)
    files = [f for f in files if not f.is_symlink()]
    return sorted(files)


def _parse_sections(path: Path) -> list[dict]:
    """Split a markdown file into sections at ## and ### headers."""
    rel = str(path.relative_to(META_ROOT))
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        log.warning("Failed to read %s", path)
        return []

    sections = []
    lines = text.split("\n")
    current_heading = rel  # default: file name as heading
    current_level = 1
    current_lines: list[str] = []

    def _flush():
        if current_lines:
            content = "\n".join(current_lines).strip()
            if content:
                sections.append({
                    "file": rel,
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
    }


# --- MCP Server ---

_call_count = 0


def create_mcp() -> FastMCP:
    @asynccontextmanager
    async def lifespan(server):
        files = _collect_files()
        sections = []
        for f in files:
            sections.extend(_parse_sections(f))
        log.info("meta-mcp: indexed %d sections from %d files", len(sections), len(files))
        yield {"sections": sections}

    mcp = FastMCP("meta-knowledge", instructions=INSTRUCTIONS, lifespan=lifespan)

    @mcp.tool()
    def search_meta(
        ctx: Context,
        query: str,
        max_tokens: int = 350,
        scope: str = "all",
    ) -> dict:
        """Search meta project knowledge: hook designs, agent failure modes,
        prompting patterns, architecture decisions, research findings.

        Returns matching sections ranked by relevance. When no results are found,
        returns a structured error with suggested alternative queries. Side effects: none.

        Args:
            query: search terms (matched against section headers and content)
            max_tokens: max response size (default 350, max 1000)
            scope: filter by category - "all", "hooks", "failures", "research",
                   "architecture", "improvement-log"
        """
        global _call_count
        _call_count += 1

        max_tokens = min(max(max_tokens, 50), 1000)

        if scope not in ("all", *SCOPE_MAP):
            return {
                "error": True,
                "error_type": "INVALID_SCOPE",
                "message": f"Unknown scope '{scope}'",
                "recoverable": True,
                "suggested_action": f"use one of: all, {', '.join(SCOPE_MAP.keys())}",
                "call_number": _call_count,
            }

        if not query or not query.strip():
            return {
                "error": True,
                "error_type": "EMPTY_QUERY",
                "message": "Query string is empty",
                "recoverable": True,
                "suggested_action": "provide search terms (2+ chars each)",
                "call_number": _call_count,
            }

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

        return result

    return mcp


def main():
    create_mcp().run()


if __name__ == "__main__":
    main()
