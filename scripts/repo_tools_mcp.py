#!/usr/bin/env python3
"""MCP server exposing repo navigation tools to AI agents.

Tools:
  repo_outline   — class/function signatures with line numbers
  repo_callgraph — who-calls-what edges within a file or directory
  repo_imports   — cross-file import graph
  repo_deps      — project dependencies with PyPI descriptions
  repo_changes   — recent git changes grouped by area or hotspots
  repo_summary   — per-file one-line summaries (cached by content hash)

Configure in .mcp.json:
  "repo-tools": {
    "command": "uv",
    "args": ["run", "--directory", "/Users/alien/Projects/meta", "python3", "scripts/repo_tools_mcp.py"]
  }
"""
import subprocess
import sys
from pathlib import Path

from fastmcp import FastMCP

SCRIPTS_DIR = Path(__file__).resolve().parent

from scripts.mcp_middleware import TelemetryMiddleware

mcp = FastMCP(
    "repo-tools",
    instructions=(
        "Code repository navigation tools. Use these to understand codebase structure "
        "without reading every file. Start with repo_outline or repo_summary for overview, "
        "then repo_imports --internal for cross-file relationships, "
        "then repo_callgraph with cross_file=True for call chains."
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


@mcp.tool()
def repo_outline(path: str, depth: int = 99) -> str:
    """List all classes and functions with signatures and line numbers.

    Shows the structure of Python files without reading full source.
    ~1/10th the tokens of reading files directly.

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
    """Show who-calls-what edges in Python files.

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
    """Cross-file import graph for Python projects.

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
    """Show project dependencies with PyPI descriptions.

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


@mcp.tool()
def repo_summary(path: str, use_llm: bool = False) -> str:
    """Per-file one-line summary map. Docstring-first, optionally LLM-enriched.

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
