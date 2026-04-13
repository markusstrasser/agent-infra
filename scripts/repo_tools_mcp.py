#!/usr/bin/env python3
"""MCP server exposing repo navigation tools to AI agents.

Tools (tiered context loading):
  L0: repo_summary   — per-file one-line index (quick orientation)
  L1: repo_overview  — functional overview with section filtering
  L2: repo_outline   — class/function signatures with line numbers
  L2: repo_callgraph — who-calls-what edges within a file or directory
  L2: repo_imports   — cross-file import graph
  L2: repo_deps      — project dependencies with PyPI descriptions
      repo_changes   — recent git changes grouped by area or hotspots

Configure in .mcp.json:
    "repo-tools": {
    "command": "uv",
    "args": ["run", "--directory", "/Users/alien/Projects/agent-infra", "python3", "scripts/repo_tools_mcp.py"]
  }
"""
import re
import subprocess
import sys
import time
from pathlib import Path

from fastmcp import FastMCP

SCRIPTS_DIR = Path(__file__).resolve().parent

from scripts.mcp_middleware import TelemetryMiddleware

mcp = FastMCP(
    "repo-tools",
    instructions=(
        "Code repository navigation tools for tiered context loading. "
        "L0: repo_summary for quick file index. "
        "L1: repo_overview for functional overview (sections filterable). "
        "L2: repo_outline / repo_callgraph / repo_imports for detailed structure. "
        "Start at the lowest tier that answers your question."
    ),
    middleware=[TelemetryMiddleware()],
)


def _serf_error(error_type: str, message: str, recoverable: bool = True,
                 suggested_action: str = "") -> dict:
    """Build a SERF-style structured error response.

    SERF (Structured Error Response Format) enables deterministic agent
    self-correction by providing machine-readable failure categories.
    Source: arXiv:2603.13417 (MCP Design Patterns).
    """
    return {
        "error": True,
        "error_type": error_type,
        "message": message,
        "recoverable": recoverable,
        "suggested_action": suggested_action,
    }


def _run_script(script: str, args: list[str], timeout: int = 30) -> str | dict:
    """Run a repo-tool script and return its stdout, or SERF error on failure."""
    cmd = [sys.executable, str(SCRIPTS_DIR / script)] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            stderr = result.stderr.strip() if result.stderr else ""
            # Classify error type from stderr/exit code
            if "FileNotFoundError" in stderr or "No such file" in stderr:
                return _serf_error(
                    "FILE_NOT_FOUND", f"Path not found: {stderr[:200]}",
                    recoverable=True, suggested_action="check path with Glob or ls",
                )
            elif "SyntaxError" in stderr or "IndentationError" in stderr:
                return _serf_error(
                    "PARSE_ERROR", f"Failed to parse source: {stderr[:200]}",
                    recoverable=False, suggested_action="file may have syntax errors",
                )
            elif result.returncode == 2:
                return _serf_error(
                    "INVALID_ARGS", f"Invalid arguments: {stderr[:200]}",
                    recoverable=True, suggested_action="check tool parameter docs",
                )
            else:
                output = result.stdout or ""
                if stderr:
                    output += f"\n[stderr: {stderr}]"
                return output or "(no output)"
        return result.stdout or "(no output)"
    except subprocess.TimeoutExpired:
        return _serf_error(
            "TIMEOUT", f"Script timed out after {timeout}s",
            recoverable=True, suggested_action="try a smaller path scope or increase timeout",
        )
    except Exception as e:
        return _serf_error(
            "INTERNAL_ERROR", str(e)[:200],
            recoverable=False, suggested_action="report this error",
        )


# ---------------------------------------------------------------------------
# L1: Functional overview
# ---------------------------------------------------------------------------

def _extract_section(content: str, section: str) -> str | None:
    """Extract a section from overview markdown by heading match.

    Matches against ### or #### headings. Case-insensitive substring match.
    Returns content from the matched heading to the next heading at the same
    or higher level, or end of file.
    """
    lines = content.splitlines()
    section_lower = section.lower()
    start_idx = None
    start_level = None

    for i, line in enumerate(lines):
        m = re.match(r'^(#{2,4})\s+(.+)', line)
        if m:
            level = len(m.group(1))
            heading = m.group(2).strip()
            if start_idx is None:
                # Looking for match
                if section_lower in heading.lower():
                    start_idx = i
                    start_level = level
            else:
                # Found start, looking for end (same or higher level heading)
                if level <= start_level:
                    return "\n".join(lines[start_idx:i]).rstrip()

    if start_idx is not None:
        return "\n".join(lines[start_idx:]).rstrip()
    return None


def _staleness_days(filepath: Path) -> int | None:
    """Return days since file was last modified, or None if can't determine."""
    try:
        mtime = filepath.stat().st_mtime
        age_s = time.time() - mtime
        return int(age_s / 86400)
    except OSError:
        return None


@mcp.tool()
def repo_overview(path: str, scope: str = "source", section: str = "") -> str:
    """L1 context: functional overview of project structure and relationships.

    Returns auto-generated overview content organized by functional groups.
    Use this AFTER repo_summary (L0 index) identifies relevant areas,
    and BEFORE repo_outline (L2 detail) for specific files.

    Args:
        path: Project root directory (absolute path)
        scope: Overview type - "source" for code structure, "tooling" for hooks/skills/MCP
        section: Optional heading name to return only that section (substring match)
    """
    project_root = Path(path)
    overview_path = project_root / ".claude" / "overviews" / f"{scope}-overview.md"

    if not overview_path.exists():
        return (
            f"No {scope} overview found for {project_root.name}. "
            f"Use repo_outline for detailed file structure, or repo_summary for a file index."
        )

    content = overview_path.read_text()

    # Check staleness — warn but don't block
    age_days = _staleness_days(overview_path)
    warning = ""
    if age_days is not None and age_days > 7:
        warning = (
            f"[WARNING: Overview is {age_days} days old. "
            f"Content may not reflect recent changes. "
            f"Trust repo_outline for current state.]\n\n"
        )

    if section:
        extracted = _extract_section(content, section)
        if extracted is None:
            # List available sections as a hint
            headings = re.findall(r'^#{2,4}\s+(.+)', content, re.MULTILINE)
            available = ", ".join(headings[:15]) if headings else "(none found)"
            return (
                f"Section '{section}' not found in {scope} overview.\n"
                f"Available sections: {available}"
            )
        return warning + extracted

    return warning + content


# ---------------------------------------------------------------------------
# L2: Detailed structure tools
# ---------------------------------------------------------------------------

@mcp.tool()
def repo_outline(path: str, depth: int = 99) -> str:
    """L2 detail: class/function signatures with line numbers.

    Shows the structure of Python files without reading full source.
    ~1/10th the tokens of reading files directly.
    Use after identifying relevant files via L0 (repo_summary) or L1 (repo_overview).

    Args:
        path: File or directory to outline (absolute path)
        depth: 1=classes only, 2+=include methods (default: all)
    """
    args = [path]
    if depth != 99:
        args.extend(["--depth", str(depth)])
    return _run_script("repo-outline.py", ["outline"] + args)


@mcp.tool()
def repo_callgraph(
    path: str, external: bool = False, cross_file: bool = False, target: str = ""
) -> str:
    """L2 detail: who-calls-what edges in Python files.

    Default: intra-file calls. Use cross_file=True to trace calls
    across files (resolves imports to source modules).
    Use target="func_name" to find all callers of a specific function.

    Args:
        path: File or directory to analyze (absolute path)
        external: Include calls to imported names (default: internal only)
        cross_file: Resolve calls across files via import graph
        target: Find all cross-file callers of this function name
    """
    if cross_file or target:
        args = [path]
        if target:
            args.extend(["--for", target])
        return _run_script("repo-outline.py", ["xrefs"] + args)
    args = [path]
    if external:
        args.append("--external")
    return _run_script("repo-outline.py", ["callgraph"] + args)


@mcp.tool()
def repo_imports(path: str, mode: str = "internal") -> str:
    """L2 detail: cross-file import graph for Python projects.

    Args:
        path: File or directory to analyze (absolute path)
        mode: "internal" (cross-file refs only), "full" (all imports),
              "deps" (group by external dependency), or "for:NAME" (who imports NAME?)
    """
    args = [path]
    if mode == "internal":
        args.append("--internal")
    elif mode == "deps":
        args.append("--deps")
    elif mode.startswith("for:"):
        args.extend(["--for", mode[4:]])
    # "full" = no extra flags
    return _run_script("repo-imports.py", args)


@mcp.tool()
def repo_deps(path: str) -> str:
    """L2 detail: project dependencies with PyPI descriptions.

    Parses pyproject.toml and enriches each dep with its summary.

    Args:
        path: Project directory containing pyproject.toml (absolute path)
    """
    return _run_script("repo-deps.py", [path], timeout=60)


@mcp.tool()
def repo_changes(path: str, days: int = 7, mode: str = "default") -> str:
    """Recent git changes — what changed and where.

    Args:
        path: Git repository path (absolute path)
        days: Look back N days (default: 7)
        mode: "default" (chronological), "by-area" (grouped by directory),
              "hot" (most-changed files)
    """
    args = [path, "--days", str(days)]
    if mode == "by-area":
        args.append("--by-area")
    elif mode == "hot":
        args.append("--hot")
    return _run_script("repo-changes.py", args)


# ---------------------------------------------------------------------------
# L0: Quick file index
# ---------------------------------------------------------------------------

@mcp.tool()
def repo_summary(path: str, use_llm: bool = False) -> str:
    """L0 index: per-file one-line summary map. Start here to orient.

    Quick file-level index. Identifies which files are relevant before
    diving into L1 (repo_overview) or L2 (repo_outline) detail.
    Docstring-first, optionally LLM-enriched.

    Args:
        path: File or directory to summarize (absolute path)
        use_llm: Use Haiku for files without docstrings (costs ~$0.01/file)
    """
    args = [path, "--refresh"]
    if not use_llm:
        args.append("--no-llm")
    return _run_script("repo-summary.py", args, timeout=120)


if __name__ == "__main__":
    mcp.run()
