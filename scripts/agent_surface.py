#!/usr/bin/env python3
"""Agent surface analyzer.

Measures current project instruction surface, shared skill footprint, and MCP
exposure. The report separates:

- always-exposed surface: root instructions, skill descriptions, enabled MCPs
- on-invoke surface: skill bodies
- on-demand surface: referenced companion files

It also reads runlogs.db when available to show whether enabled MCP servers are
actually used in recent sessions.

Usage:
    uv run python3 scripts/agent_surface.py
    uv run python3 scripts/agent_surface.py --format json
    uv run python3 scripts/agent_surface.py --write artifacts/agent-surface/meta.md
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import re
import sqlite3
import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import yaml

from common.paths import RUNLOGS_DB

SKILLS_DIR = Path.home() / "Projects" / "skills"
DEFAULT_MCP_FILE = ".mcp.json"
NEGATIVE_SCOPE_RE = re.compile(
    r"\b("
    r"do not use for|do not trigger when|do not trigger|do not use when|"
    r"not for|not when|do not use\b|avoid using for"
    r")\b",
    re.IGNORECASE,
)
TOOL_PATH_RE = re.compile(r"\b(?:references|scripts|assets)/[A-Za-z0-9_./-]+\b")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\((?!https?://)([^)#]+)\)")
DESCRIPTION_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
MULTI_FOCUS_HINT_RE = re.compile(r"\b(or|and)\b|/|;|,")
BRAVE_SERVER_TOOLS = [
    "brave_web_search",
    "brave_local_search",
    "brave_news_search",
    "brave_summarizer",
    "brave_image_search",
    "brave_video_search",
]


@dataclass
class RootInstruction:
    path: str
    label: str
    bytes: int
    tokens: int
    symlink: bool


@dataclass
class SkillSurface:
    name: str
    path: str
    description_tokens: int
    body_tokens: int
    reference_tokens: int
    line_count: int
    description_words: int
    has_negative_scope: bool
    vague_description: bool
    multi_focus_suspect: bool
    status: str
    companion_files: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class MCPServerSurface:
    name: str
    tool_count: int
    schema_tokens: int
    schema_source: str
    tool_names: list[str] = field(default_factory=list)
    call_count_30d: int = 0
    run_count_30d: int = 0


def estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


def parse_frontmatter(skill_md: Path) -> tuple[dict[str, Any], str]:
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    try:
        frontmatter = yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError:
        frontmatter = {}
    body = text[end + 5 :]
    return frontmatter, body


def description_word_count(text: str) -> int:
    return len(DESCRIPTION_WORD_RE.findall(text))


def collect_root_instructions(project_root: Path) -> list[RootInstruction]:
    candidates = [
        ("CLAUDE.md", project_root / "CLAUDE.md"),
        ("AGENTS.md", project_root / "AGENTS.md"),
        ("GEMINI.md", project_root / "GEMINI.md"),
    ]
    seen_realpaths: set[Path] = set()
    results: list[RootInstruction] = []
    for label, path in candidates:
        if not path.exists():
            continue
        real_path = path.resolve()
        if real_path in seen_realpaths:
            continue
        seen_realpaths.add(real_path)
        text = real_path.read_text(encoding="utf-8", errors="replace")
        results.append(
            RootInstruction(
                path=str(path),
                label=label,
                bytes=len(text.encode("utf-8")),
                tokens=estimate_tokens(text),
                symlink=path.is_symlink(),
            )
        )
    return results


def collect_companion_files(skill_dir: Path, body: str) -> list[Path]:
    refs: set[Path] = set()
    for match in TOOL_PATH_RE.findall(body):
        candidate = (skill_dir / match).resolve()
        if candidate.exists() and candidate.is_file():
            refs.add(candidate)
    for rel in MARKDOWN_LINK_RE.findall(body):
        rel = rel.strip()
        if rel.startswith("#"):
            continue
        candidate = (skill_dir / rel).resolve()
        if candidate.exists() and candidate.is_file():
            refs.add(candidate)
    return sorted(refs)


def analyze_skill(skill_dir: Path) -> SkillSurface | None:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return None
    frontmatter, body = parse_frontmatter(skill_md)
    description = str(frontmatter.get("description", "") or "")
    companions = collect_companion_files(skill_dir, body)
    companion_tokens = 0
    companion_names: list[str] = []
    for companion in companions:
        text = companion.read_text(encoding="utf-8", errors="replace")
        companion_tokens += estimate_tokens(text)
        try:
            rel = companion.relative_to(skill_dir)
            companion_names.append(str(rel))
        except ValueError:
            companion_names.append(str(companion))

    desc_tokens = estimate_tokens(description) if description else 0
    body_tokens = estimate_tokens(body)
    line_count = len(skill_md.read_text(encoding="utf-8", errors="replace").splitlines())
    has_negative_scope = bool(NEGATIVE_SCOPE_RE.search(description) or NEGATIVE_SCOPE_RE.search(body))
    desc_words = description_word_count(description)
    vague_description = desc_words < 8 or len(description.strip()) < 50
    multi_focus_suspect = len(MULTI_FOCUS_HINT_RE.findall(description)) >= 4

    warnings: list[str] = []
    if vague_description:
        warnings.append("vague-description")
    if not has_negative_scope and (multi_focus_suspect or desc_words >= 18):
        warnings.append("missing-negative-scope")
    if multi_focus_suspect:
        warnings.append("multi-focus-suspect")
    if companion_tokens > 10_000:
        warnings.append("large-companions")

    status = "ok"
    if line_count > 500 or body_tokens > 5_000 or companion_tokens > 12_000:
        status = "oversized"
    elif warnings:
        status = "warn"

    return SkillSurface(
        name=skill_dir.name,
        path=str(skill_md),
        description_tokens=desc_tokens,
        body_tokens=body_tokens,
        reference_tokens=companion_tokens,
        line_count=line_count,
        description_words=desc_words,
        has_negative_scope=has_negative_scope,
        vague_description=vague_description,
        multi_focus_suspect=multi_focus_suspect,
        status=status,
        companion_files=companion_names,
        warnings=warnings,
    )


def scan_fastmcp_tools(entrypoint_file: Path) -> tuple[list[str], int]:
    tools: list[tuple[str, str]] = []
    try:
        tree = ast.parse(entrypoint_file.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return [], 0
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not any(_is_tool_decorator(dec) for dec in node.decorator_list):
            continue
        docstring = ast.get_docstring(node) or ""
        tools.append((node.name, docstring.strip()))
    tools.sort(key=lambda item: item[0])
    schema_chars = len(json.dumps([{"name": name, "description": desc} for name, desc in tools], sort_keys=True))
    return [name for name, _ in tools], estimate_tokens("x" * schema_chars)


def _is_tool_decorator(node: ast.AST) -> bool:
    if isinstance(node, ast.Call):
        return _is_tool_decorator(node.func)
    if isinstance(node, ast.Attribute):
        return node.attr == "tool"
    if isinstance(node, ast.Name):
        return node.id == "tool"
    return False


def load_mcp_servers(project_root: Path) -> dict[str, dict[str, Any]]:
    mcp_path = project_root / DEFAULT_MCP_FILE
    if not mcp_path.exists():
        return {}
    try:
        data = json.loads(mcp_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data.get("mcpServers", {}) if isinstance(data.get("mcpServers"), dict) else {}


def extract_project_dir(args: list[Any]) -> Path | None:
    for idx, value in enumerate(args):
        if value == "--directory" and idx + 1 < len(args):
            candidate = Path(str(args[idx + 1])).expanduser()
            if candidate.exists():
                return candidate
    return None


def resolve_entrypoint_file(project_dir: Path, entrypoint_name: str) -> Path | None:
    pyproject = project_dir / "pyproject.toml"
    if not pyproject.exists():
        return None
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return None
    scripts = data.get("project", {}).get("scripts", {})
    target = scripts.get(entrypoint_name)
    if not isinstance(target, str) or ":" not in target:
        return None
    module_name = target.split(":", 1)[0]
    rel_path = Path(*module_name.split("."))
    candidates = [
        project_dir / f"{rel_path}.py",
        project_dir / "src" / f"{rel_path}.py",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def mcp_server_surface(name: str, config: dict[str, Any]) -> MCPServerSurface:
    tool_names: list[str] = []
    schema_source = "config-only"

    if config.get("type") == "http":
        url = str(config.get("url", ""))
        parsed = urlparse(url)
        tools = parse_qs(parsed.query).get("tools")
        if tools:
            tool_names = [t for t in tools[0].split(",") if t]
            schema_source = "http-query"
    elif str(config.get("command", "")).endswith("npx") or config.get("command") == "npx":
        args = [str(x) for x in config.get("args", [])]
        if any("@modelcontextprotocol/server-brave-search" in item for item in args):
            tool_names = list(BRAVE_SERVER_TOOLS)
            schema_source = "known-package"

    if not tool_names:
        project_dir = extract_project_dir(config.get("args", []))
        if project_dir is not None:
            args = [str(x) for x in config.get("args", [])]
            entrypoint_name = next(
                (item for item in reversed(args) if not item.startswith("-") and item != str(project_dir)),
                None,
            )
            entrypoint_file = resolve_entrypoint_file(project_dir, entrypoint_name) if entrypoint_name else None
            if entrypoint_file is not None:
                scanned_names, scanned_tokens = scan_fastmcp_tools(entrypoint_file)
            else:
                scanned_names, scanned_tokens = [], 0
            if scanned_names:
                return MCPServerSurface(
                    name=name,
                    tool_count=len(scanned_names),
                    schema_tokens=scanned_tokens,
                    schema_source="source-scan",
                    tool_names=scanned_names,
                )

    schema_tokens = estimate_tokens(json.dumps(tool_names)) if tool_names else 0
    return MCPServerSurface(
        name=name,
        tool_count=len(tool_names),
        schema_tokens=schema_tokens,
        schema_source=schema_source,
        tool_names=tool_names,
    )


def load_mcp_telemetry(project_root: Path, days: int) -> dict[str, dict[str, int]]:
    if not RUNLOGS_DB.exists():
        return {}
    db = sqlite3.connect(RUNLOGS_DB)
    db.row_factory = sqlite3.Row
    prefix = f"{project_root}%"
    rows = db.execute(
        """
        SELECT
            tc.mcp_server AS mcp_server,
            COUNT(*) AS call_count,
            COUNT(DISTINCT tc.run_id) AS run_count
        FROM tool_calls tc
        JOIN runs r USING(run_id)
        WHERE tc.mcp_server IS NOT NULL
          AND r.started_at >= datetime('now', ?)
          AND (
                r.cwd LIKE ?
                OR EXISTS (
                    SELECT 1
                    FROM sessions s
                    WHERE s.session_pk = r.session_pk
                      AND s.project_root LIKE ?
                )
          )
        GROUP BY tc.mcp_server
        """,
        (f"-{days} days", prefix, prefix),
    ).fetchall()
    db.close()
    return {
        str(row["mcp_server"]): {
            "call_count": int(row["call_count"]),
            "run_count": int(row["run_count"]),
        }
        for row in rows
    }


def build_report(project_root: Path, skills_dir: Path, days: int, top: int) -> dict[str, Any]:
    root_files = collect_root_instructions(project_root)
    skills = [skill for skill in (analyze_skill(path) for path in sorted(skills_dir.iterdir()) if path.is_dir()) if skill]
    mcp_servers = [
        mcp_server_surface(name, config)
        for name, config in sorted(load_mcp_servers(project_root).items())
    ]
    telemetry = load_mcp_telemetry(project_root, days)
    for server in mcp_servers:
        stats = telemetry.get(server.name, {})
        server.call_count_30d = int(stats.get("call_count", 0))
        server.run_count_30d = int(stats.get("run_count", 0))

    always_items: list[tuple[str, str, int]] = []
    conditional_items: list[tuple[str, str, int]] = []
    for item in root_files:
        always_items.append(("root", item.label, item.tokens))
    for skill in skills:
        always_items.append(("skill-description", skill.name, skill.description_tokens))
        conditional_items.append(("skill-body", skill.name, skill.body_tokens))
        conditional_items.append(("skill-reference", skill.name, skill.reference_tokens))
    for server in mcp_servers:
        always_items.append(("mcp-schema", server.name, server.schema_tokens))

    always_items.sort(key=lambda row: row[2], reverse=True)
    conditional_items.sort(key=lambda row: row[2], reverse=True)

    summary = {
        "root_instruction_tokens": sum(item.tokens for item in root_files),
        "skill_description_tokens": sum(skill.description_tokens for skill in skills),
        "skill_body_tokens": sum(skill.body_tokens for skill in skills),
        "skill_reference_tokens": sum(skill.reference_tokens for skill in skills),
        "mcp_schema_tokens": sum(server.schema_tokens for server in mcp_servers),
        "skill_status_counts": {
            "ok": sum(1 for skill in skills if skill.status == "ok"),
            "warn": sum(1 for skill in skills if skill.status == "warn"),
            "oversized": sum(1 for skill in skills if skill.status == "oversized"),
        },
    }

    return {
        "project_root": str(project_root),
        "skills_dir": str(skills_dir),
        "telemetry_window_days": days,
        "summary": summary,
        "root_files": [asdict(item) for item in root_files],
        "skills": [asdict(skill) for skill in skills],
        "mcp_servers": [asdict(server) for server in mcp_servers],
        "top_always_exposed": [
            {"kind": kind, "name": name, "tokens": tokens}
            for kind, name, tokens in always_items[:top]
        ],
        "top_conditional": [
            {"kind": kind, "name": name, "tokens": tokens}
            for kind, name, tokens in conditional_items[:top]
            if tokens > 0
        ],
    }


def format_table(report: dict[str, Any]) -> str:
    lines: list[str] = []
    summary = report["summary"]
    lines.append("Agent Surface Report")
    lines.append(f"Project: {report['project_root']}")
    lines.append(f"Telemetry window: {report['telemetry_window_days']} days")
    lines.append("")
    lines.append("Summary")
    lines.append(f"  Root instructions:    {summary['root_instruction_tokens']:>6} tokens")
    lines.append(f"  Skill descriptions:  {summary['skill_description_tokens']:>6} tokens")
    lines.append(f"  Skill bodies:        {summary['skill_body_tokens']:>6} tokens (on invoke)")
    lines.append(f"  Skill references:    {summary['skill_reference_tokens']:>6} tokens (on demand)")
    lines.append(f"  MCP schemas:         {summary['mcp_schema_tokens']:>6} tokens")
    counts = summary["skill_status_counts"]
    lines.append(
        f"  Skill hygiene:       ok={counts['ok']} warn={counts['warn']} oversized={counts['oversized']}"
    )
    lines.append("")
    lines.append("Top always-exposed contributors")
    for item in report["top_always_exposed"]:
        lines.append(f"  {item['kind']:<18} {item['name']:<28} {item['tokens']:>6} tok")
    lines.append("")
    lines.append("Top conditional contributors")
    for item in report["top_conditional"]:
        lines.append(f"  {item['kind']:<18} {item['name']:<28} {item['tokens']:>6} tok")
    lines.append("")
    lines.append("Skill hygiene")
    for skill in sorted(report["skills"], key=lambda row: (row["status"], -row["body_tokens"], row["name"])):
        warn = ",".join(skill["warnings"]) if skill["warnings"] else "-"
        lines.append(
            f"  {skill['name']:<24} {skill['status']:<9} "
            f"desc={skill['description_tokens']:>4} body={skill['body_tokens']:>5} "
            f"refs={skill['reference_tokens']:>5} neg={'y' if skill['has_negative_scope'] else 'n'} "
            f"warn={warn}"
        )
    if report["mcp_servers"]:
        lines.append("")
        lines.append("MCP exposure")
        for server in report["mcp_servers"]:
            tool_names = ",".join(server["tool_names"][:5])
            if len(server["tool_names"]) > 5:
                tool_names += ",..."
            lines.append(
                f"  {server['name']:<16} tools={server['tool_count']:<3} "
                f"schema={server['schema_tokens']:<5} source={server['schema_source']:<12} "
                f"calls_30d={server['call_count_30d']:<4} runs_30d={server['run_count_30d']:<3} "
                f"{tool_names}"
            )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=str(Path.cwd()), help="Project root to analyze")
    parser.add_argument("--skills-dir", default=str(SKILLS_DIR), help="Shared skills dir")
    parser.add_argument("--days", type=int, default=30, help="Telemetry lookback window")
    parser.add_argument("--top", type=int, default=10, help="Top contributors to print")
    parser.add_argument("--format", choices=("table", "json"), default="table")
    parser.add_argument("--write", help="Optional output file")
    args = parser.parse_args(argv)

    report = build_report(
        project_root=Path(args.project_root).resolve(),
        skills_dir=Path(args.skills_dir).resolve(),
        days=args.days,
        top=args.top,
    )

    output = json.dumps(report, indent=2, sort_keys=True) if args.format == "json" else format_table(report)
    if args.write:
        target = Path(args.write)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(output, encoding="utf-8")
    print(output, end="" if output.endswith("\n") else "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
