#!/usr/bin/env python3
"""Claude Code infrastructure health checker.

Checks hooks, settings, skills, MCP, memory, git state, and symlinks
across all configured projects. Structured pass/warn/fail output.

Usage: uv run python3 scripts/doctor.py [--project PROJECT] [--json]
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from config import PROJECT_ROOTS

# --- Configuration ---

PROJECTS_DIR = Path.home() / "Projects"
PROJECTS = list(PROJECT_ROOTS.keys())
from common.paths import CLAUDE_DIR
GLOBAL_SETTINGS = CLAUDE_DIR / "settings.json"
GLOBAL_CLAUDE_MD = CLAUDE_DIR / "CLAUDE.md"
MEMORY_WARN_LINES = 180
MEMORY_MAX_LINES = 200


class Check:
    """Single health check result."""

    def __init__(self, name: str, scope: str):
        self.name = name
        self.scope = scope
        self.status = "pass"  # pass, warn, fail
        self.message = ""

    def warn(self, msg: str):
        self.status = "warn"
        self.message = msg
        return self

    def fail(self, msg: str):
        self.status = "fail"
        self.message = msg
        return self

    def ok(self, msg: str = ""):
        self.status = "pass"
        self.message = msg
        return self


def run(cmd: list[str], cwd: str | None = None, timeout: int = 5) -> str | None:
    """Run a command, return stdout or None on failure."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


# --- Check Functions ---


def check_settings_json(path: Path, scope: str) -> list[Check]:
    """Validate a settings.json file."""
    c = Check("settings.json", scope)
    if not path.exists():
        return [c.warn("No settings.json")]
    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [c.fail(f"Invalid JSON: {e}")]

    checks = [c.ok(f"{len(data.get('hooks', {}))} hook events")]

    # Validate hook command paths exist
    for event, hook_groups in data.get("hooks", {}).items():
        for group in hook_groups:
            for hook in group.get("hooks", []):
                if hook.get("type") != "command":
                    continue
                cmd = hook.get("command", "")
                # Extract script path (first token if it's a file path)
                parts = cmd.split()
                # Find the script file — may be the command itself or an argument to bash/python3
                script_token = next((p for p in parts if p.endswith(('.sh', '.py'))), None)
                if script_token:
                    script = Path(script_token)
                elif parts and parts[0].startswith("/"):
                    script = Path(parts[0])
                else:
                    script = None
                if script is not None:
                    hc = Check(f"hook:{event}:{script.name}", scope)
                    if not script.exists():
                        checks.append(hc.fail(f"Script missing: {script}"))
                    elif not os.access(script, os.X_OK):
                        checks.append(hc.fail(f"Not executable: {script}"))
                    else:
                        checks.append(hc.ok())

    return checks


def check_skill_symlinks(project_dir: Path) -> list[Check]:
    """Check for broken skill symlinks."""
    skills_dir = project_dir / ".claude" / "skills"
    if not skills_dir.exists():
        return []

    checks = []
    for entry in skills_dir.iterdir():
        if entry.is_symlink():
            c = Check(f"skill:{entry.name}", project_dir.name)
            if not entry.exists():  # broken symlink
                checks.append(c.fail(f"Broken symlink → {os.readlink(entry)}"))
            else:
                checks.append(c.ok())
    return checks


def check_skill_frontmatter(project_dir: Path) -> list[Check]:
    """Validate SKILL.md files have required frontmatter fields."""
    skills_dir = project_dir / ".claude" / "skills"
    if not skills_dir.exists():
        return []

    checks = []
    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            # Check if it's a symlinked SKILL.md directly
            if skill_dir.is_symlink():
                continue
            c = Check(f"frontmatter:{skill_dir.name}", project_dir.name)
            checks.append(c.warn("No SKILL.md"))
            continue

        c = Check(f"frontmatter:{skill_dir.name}", project_dir.name)
        try:
            content = skill_md.read_text()
            # Check for frontmatter delimiter
            if not content.startswith("---"):
                checks.append(c.warn("Missing frontmatter"))
                continue
            # Extract frontmatter
            parts = content.split("---", 2)
            if len(parts) < 3:
                checks.append(c.warn("Malformed frontmatter"))
                continue
            # Basic field check
            fm = parts[1]
            required = ["name"]
            missing = [f for f in required if f"{f}:" not in fm]
            if missing:
                checks.append(c.warn(f"Missing fields: {', '.join(missing)}"))
            else:
                checks.append(c.ok())
        except Exception as e:
            checks.append(c.fail(f"Read error: {e}"))

    return checks


def check_memory_health() -> list[Check]:
    """Check MEMORY.md sizes across projects."""
    checks = []
    memory_base = CLAUDE_DIR / "projects"
    if not memory_base.exists():
        return []

    for proj_dir in memory_base.iterdir():
        if not proj_dir.is_dir():
            continue
        memory_dir = proj_dir / "memory"
        if not memory_dir.exists():
            continue
        memory_md = memory_dir / "MEMORY.md"
        if not memory_md.exists():
            continue

        # Extract project name from path
        proj_name = proj_dir.name.split("-")[-1] if "-" in proj_dir.name else proj_dir.name
        c = Check(f"memory:{proj_name}", "global")
        lines = memory_md.read_text().count("\n")
        if lines > MEMORY_MAX_LINES:
            checks.append(c.fail(f"{lines} lines (max {MEMORY_MAX_LINES}, will be truncated)"))
        elif lines > MEMORY_WARN_LINES:
            checks.append(c.warn(f"{lines} lines (warn at {MEMORY_WARN_LINES})"))
        else:
            checks.append(c.ok(f"{lines} lines"))

    return checks


def check_git_state(project_dir: Path) -> list[Check]:
    """Check git repository health."""
    c = Check("git", project_dir.name)
    if not (project_dir / ".git").exists():
        return [c.warn("Not a git repo")]

    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(project_dir))
    if branch is None:
        return [c.fail("git rev-parse failed")]

    checks = [c.ok(f"branch={branch}")]

    # Check for uncommitted changes
    status = run(["git", "status", "--porcelain"], cwd=str(project_dir))
    if status:
        line_count = len(status.strip().split("\n"))
        sc = Check("git:uncommitted", project_dir.name)
        checks.append(sc.warn(f"{line_count} uncommitted changes"))

    return checks


def check_mcp(project_dir: Path) -> list[Check]:
    """Check MCP configuration exists and is valid JSON."""
    mcp_path = project_dir / ".mcp.json"
    c = Check("mcp", project_dir.name)
    if not mcp_path.exists():
        return [c.warn("No .mcp.json")]
    try:
        with open(mcp_path) as f:
            data = json.load(f)
        servers = data.get("mcpServers", {})
        return [c.ok(f"{len(servers)} servers configured")]
    except json.JSONDecodeError as e:
        return [c.fail(f"Invalid JSON: {e}")]


def check_stale_agents() -> list[Check]:
    """Check for subagent JSONL files with no matching process (crashed agents)."""
    import time

    checks = []
    projects_dir = CLAUDE_DIR / "projects"
    if not projects_dir.exists():
        return checks

    stale_threshold = 30 * 60  # 30 minutes
    max_age = 2 * 60 * 60  # only check last 2 hours (older = completed, not crashed)
    now = time.time()

    for subagents_dir in projects_dir.glob("*/*/subagents"):
        for jsonl in subagents_dir.glob("agent-*.jsonl"):
            age = now - jsonl.stat().st_mtime
            if age < stale_threshold or age > max_age:
                continue
            # Extract agent ID, check if any claude process references it
            agent_id = jsonl.stem.replace("agent-", "")
            try:
                ps = subprocess.run(
                    ["pgrep", "-f", agent_id], capture_output=True, timeout=5
                )
                has_process = ps.returncode == 0
            except Exception:
                has_process = True  # fail open — don't report if pgrep fails

            if not has_process:
                c = Check("stale-agent", agent_id[:12])
                age_min = int(age / 60)
                c.warn(f"No process found, last write {age_min}m ago: {jsonl.name}")
                checks.append(c)

    if not checks:
        c = Check("stale-agents", "global")
        checks.append(c.ok("No stale agents"))
    return checks


def check_gitignore(project_dir: Path) -> list[Check]:
    """Check that .claude/ artifacts are gitignored."""
    c = Check("gitignore:.claude", project_dir.name)
    gitignore = project_dir / ".gitignore"
    if not gitignore.exists():
        return [c.warn("No .gitignore")]
    content = gitignore.read_text()
    if ".claude/" in content or ".claude" in content:
        return [c.ok()]
    # Check if plans dir would be committed
    plans = project_dir / ".claude" / "plans"
    if plans.exists():
        return [c.warn(".claude/plans/ exists but .claude not in .gitignore")]
    return [c.ok("No .claude artifacts to ignore")]


# --- Main ---


def run_all_checks(project_filter: str | None = None) -> list[Check]:
    """Run all checks, optionally filtered to one project."""
    all_checks: list[Check] = []

    # Global checks
    if not project_filter:
        all_checks.extend(check_settings_json(GLOBAL_SETTINGS, "global"))
        all_checks.extend(check_memory_health())
        all_checks.extend(check_stale_agents())

        # Global CLAUDE.md
        gc = Check("global:CLAUDE.md", "global")
        if GLOBAL_CLAUDE_MD.exists():
            lines = GLOBAL_CLAUDE_MD.read_text().count("\n")
            all_checks.append(gc.ok(f"{lines} lines"))
        else:
            all_checks.append(gc.fail("Missing"))

    # Per-project checks
    for proj in PROJECTS:
        if project_filter and proj != project_filter:
            continue
        proj_dir = PROJECTS_DIR / proj
        if not proj_dir.exists():
            c = Check("project", proj)
            all_checks.append(c.warn(f"Directory not found: {proj_dir}"))
            continue

        settings = proj_dir / ".claude" / "settings.json"
        all_checks.extend(check_settings_json(settings, proj))
        all_checks.extend(check_skill_symlinks(proj_dir))
        all_checks.extend(check_skill_frontmatter(proj_dir))
        all_checks.extend(check_git_state(proj_dir))
        all_checks.extend(check_mcp(proj_dir))
        all_checks.extend(check_gitignore(proj_dir))

    return all_checks


SYMBOLS = {"pass": "\033[32m✓\033[0m", "warn": "\033[33m!\033[0m", "fail": "\033[31m✗\033[0m"}


def print_results(checks: list[Check], as_json: bool = False):
    """Print check results."""
    if as_json:
        out = [{"name": c.name, "scope": c.scope, "status": c.status, "message": c.message} for c in checks]
        print(json.dumps(out, indent=2))
        return

    # Group by scope
    by_scope: dict[str, list[Check]] = {}
    for c in checks:
        by_scope.setdefault(c.scope, []).append(c)

    total = len(checks)
    passes = sum(1 for c in checks if c.status == "pass")
    warns = sum(1 for c in checks if c.status == "warn")
    fails = sum(1 for c in checks if c.status == "fail")

    for scope in sorted(by_scope.keys()):
        scope_checks = by_scope[scope]
        print(f"\n\033[1m[{scope}]\033[0m")
        for c in scope_checks:
            sym = SYMBOLS[c.status]
            msg = f"  {c.message}" if c.message else ""
            print(f"  {sym} {c.name}{msg}")

    print(f"\n\033[1m{total} checks: {passes} pass, {warns} warn, {fails} fail\033[0m")


def main():
    project_filter = None
    as_json = False

    args = sys.argv[1:]
    while args:
        arg = args.pop(0)
        if arg == "--project" and args:
            project_filter = args.pop(0)
        elif arg == "--json":
            as_json = True
        elif arg in ("--help", "-h"):
            print(__doc__.strip())
            sys.exit(0)

    checks = run_all_checks(project_filter)
    print_results(checks, as_json)

    # Exit code: 1 if any failures
    if any(c.status == "fail" for c in checks):
        sys.exit(1)


if __name__ == "__main__":
    main()
