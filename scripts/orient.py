#!/usr/bin/env python3
"""Live orientation map — assemble the system's shape from ground truth.

A hand-written architecture doc rots (the orchestrator was "live" in
system-architecture.md two months after it was deleted). This queries reality
every time it runs — launchd jobs, hook wiring, MCP servers, repo layout,
skills — so nothing here can go stale. The rot-prone inventory lives in code
that reads the source of truth, not in prose that has to be remembered.

Usage:
    uv run python3 scripts/orient.py            # human-readable map
    uv run python3 scripts/orient.py --json     # machine-readable
    uv run python3 scripts/orient.py --drift    # only the doc-vs-reality drift check

Sibling tools (orient does NOT replace them — it routes to them):
    just doctor      — is the system HEALTHY?   (validation)
    just dashboard   — what HAPPENED recently?  (activity / cost)
    just orient      — what IS the system?      (this — the map)
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from common.console import bold, color_status, con, dim
from common.paths import CLAUDE_DIR
from config import PROJECT_ROOTS
from common.project_registry import MIRRORED_REPOS

HOME = Path.home()
PROJECTS = HOME / "Projects"
REPO_ROOT = Path(__file__).resolve().parent.parent  # agent-infra/
# Shared layers that aren't in the mirrored registry but every repo leans on.
SHARED_LAYERS = ("skills", "research-mcp", "llmx")
# Canonical orientation docs — pointers, with freshness so a stale one self-declares.
MAP_DOCS = [
    ("CLAUDE.md", "constitution · cross-project arch table · launchd loops (auto-loaded)"),
    ("GOALS.md", "what the system optimizes for (human-owned)"),
    ("system-architecture.md", "narrative: how the layers connect end-to-end"),
    (".claude/rules/codebase-map.md", "generated per-file script inventory (path-scoped)"),
    (".claude/overviews/source-overview.md", "generated module/flow map (injected at start)"),
]
STALE_DAYS = 45  # narrative docs older than this get a staleness flag


def _run(cmd: list[str], timeout: int = 6) -> str:
    """Run a command, return stdout (stripped), '' on any failure."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except (FileNotFoundError, subprocess.SubprocessError, OSError):
        return ""


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def _git(repo: Path, *args: str) -> str:
    return _run(["git", "-C", str(repo), *args])


def _age_days(iso_date: str) -> int | None:
    try:
        return (date.today() - date.fromisoformat(iso_date)).days
    except ValueError:
        return None


# ── collectors (pure: return JSON-able data, never print) ────────────


def collect_repos() -> list[dict]:
    """Cross-project layout: which repos exist, branch, last commit, dirty."""
    names: list[str] = []
    for n in (*PROJECT_ROOTS.keys(), *MIRRORED_REPOS, *SHARED_LAYERS):
        if n not in names:
            names.append(n)
    rows = []
    for name in names:
        path = PROJECT_ROOTS.get(name, PROJECTS / name)
        if not Path(path).exists():
            rows.append({"repo": name, "present": False})
            continue
        branch = _git(Path(path), "rev-parse", "--abbrev-ref", "HEAD") or "?"
        last = _git(Path(path), "log", "-1", "--format=%cs") or "?"
        dirty = len([l for l in _git(Path(path), "status", "--porcelain").splitlines() if l])
        rows.append({
            "repo": name, "present": True, "branch": branch,
            "last_commit": last, "dirty": dirty,
            "hub": name == "agent-infra",
            "shared": name in SHARED_LAYERS,
        })
    return rows


def collect_loops() -> list[dict]:
    """launchd jobs — the recurring loops. Live, with last-exit status."""
    out = _run(["launchctl", "list"])
    if not out:
        return [{"unavailable": True}]
    jobs = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) != 3 or "com.agent-infra" not in parts[2]:
            continue
        pid, status, label = parts
        short = label.replace("com.agent-infra.", "")
        try:
            exit_code = int(status)
        except ValueError:
            exit_code = None
        jobs.append({
            "name": short,
            "running": pid not in ("-", "0") and pid.isdigit(),
            "last_exit": exit_code,
            "ok": exit_code == 0,
        })
    return sorted(jobs, key=lambda j: j["name"])


def collect_hooks() -> dict:
    """Hook wiring from settings.json (global + project) — the guardrail layer."""
    sources = {
        "global": CLAUDE_DIR / "settings.json",
        "project": REPO_ROOT / ".claude" / "settings.json",
        "project_local": REPO_ROOT / ".claude" / "settings.local.json",
    }
    scripts: set[str] = set()
    by_event: dict[str, int] = {}
    for path in sources.values():
        hooks = _load_json(path).get("hooks", {})
        for event, entries in hooks.items():
            for entry in entries:
                for h in entry.get("hooks", []):
                    by_event[event] = by_event.get(event, 0) + 1
                    m = re.findall(r"[\w./~-]+\.(?:sh|py)", h.get("command", ""))
                    if m:
                        scripts.add(Path(m[-1]).name)
    return {
        "events": dict(sorted(by_event.items(), key=lambda kv: -kv[1])),
        "total_hooks": sum(by_event.values()),
        "unique_scripts": len(scripts),
    }


def collect_mcp() -> dict:
    """MCP servers from ~/.claude.json (global + this project's scope)."""
    cfg = _load_json(HOME / ".claude.json")
    glob = sorted((cfg.get("mcpServers") or {}).keys())
    proj = cfg.get("projects", {}).get(str(REPO_ROOT), {})
    proj_servers = sorted((proj.get("mcpServers") or {}).keys())
    enabled = sorted(proj.get("enabledMcpjsonServers") or [])
    return {"global": glob, "project": proj_servers, "enabled_mcpjson": enabled}


def collect_skills() -> dict:
    """Skill library — shared capabilities (incl. the epistemics/reasoning lenses)."""
    skills_dir = PROJECTS / "skills"
    names = sorted(p.parent.name for p in skills_dir.glob("*/SKILL.md")) if skills_dir.exists() else []
    return {"dir": str(skills_dir), "count": len(names), "names": names}


def collect_maps() -> list[dict]:
    """Where to read more — canonical docs with freshness so staleness shows."""
    rows = []
    for rel, desc in MAP_DOCS:
        p = REPO_ROOT / rel
        if not p.exists():
            rows.append({"doc": rel, "present": False, "desc": desc})
            continue
        last = _git(REPO_ROOT, "log", "-1", "--format=%cs", "--", rel) or "?"
        age = _age_days(last)
        rows.append({
            "doc": rel, "present": True, "desc": desc,
            "last_commit": last, "age_days": age,
            "stale": age is not None and age > STALE_DAYS,
        })
    return rows


def collect_drift(loops: list[dict]) -> dict:
    """Drift guard: live launchd jobs that CLAUDE.md does not mention.

    This is the exact rot class that motivated orient — CLAUDE.md's
    documented job list had already drifted from reality. Set comparison
    against live ground truth, not fuzzy prose parsing.
    """
    claude_md = (REPO_ROOT / "CLAUDE.md")
    text = claude_md.read_text() if claude_md.exists() else ""
    live = [j["name"] for j in loops if j.get("name")]
    undocumented = [n for n in live if n not in text]
    return {"live_jobs": len(live), "undocumented_in_claude_md": undocumented}


# ── renderers (human output) ─────────────────────────────────────────


def render(data: dict) -> None:
    gen = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(bold("\nAGENT-INFRA — live orientation map") + dim(f"  ({gen}, assembled from ground truth)"))

    con.header("Repos — cross-project layout")
    rows = []
    for r in data["repos"]:
        if not r.get("present"):
            rows.append([r["repo"], dim("absent"), "", ""])
            continue
        tag = "hub" if r.get("hub") else ("shared" if r.get("shared") else "")
        dirty = f"±{r['dirty']}" if r["dirty"] else "clean"
        rows.append([r["repo"], r["branch"], r["last_commit"], f"{dirty} {dim(tag)}".strip()])
    con.table(["repo", "branch", "last commit", ""], rows)

    con.header("Loops — launchd recurring jobs (live)")
    loops = data["loops"]
    if loops and loops[0].get("unavailable"):
        con.warn("launchd unavailable (non-macOS or not loaded)")
    else:
        for j in loops:
            state = "running" if j["running"] else "idle"
            exit_s = "ok" if j["ok"] else (f"last exit {j['last_exit']}" if j["last_exit"] is not None else "unknown")
            mark = con.ok if j["ok"] else con.warn
            mark(f"{j['name']:<24} {color_status(state)}  {exit_s if j['ok'] else bold(exit_s)}")

    con.header("Hooks — guardrail layer (settings.json)")
    h = data["hooks"]
    con.kv("total hook fires wired", str(h["total_hooks"]))
    con.kv("unique hook scripts", str(h["unique_scripts"]))
    top = ", ".join(f"{e}:{n}" for e, n in list(h["events"].items())[:8])
    con.kv("by event (top)", top)

    con.header("MCP servers — external tool access")
    m = data["mcp"]
    con.kv("global", ", ".join(m["global"]) or dim("none"))
    if m["project"]:
        con.kv("project", ", ".join(m["project"]))
    if m["enabled_mcpjson"]:
        con.kv("enabled .mcp.json", ", ".join(m["enabled_mcpjson"]))

    con.header("Skills — shared capabilities")
    s = data["skills"]
    con.kv("count", str(s["count"]))
    con.kv("dir", s["dir"])

    con.header("Where to read more (freshness shown)")
    for d in data["maps"]:
        if not d.get("present"):
            con.warn(f"{d['doc']:<42} {dim('(missing)')}  {d['desc']}")
            continue
        age = f"{d['age_days']}d ago" if d.get("age_days") is not None else d["last_commit"]
        line = f"{d['doc']:<42} {dim(age):<14} {d['desc']}"
        con.warn(line) if d.get("stale") else con.step(line)

    render_drift(data["drift"])
    print(dim("\n  doctor = healthy?   dashboard = what happened?   orient = what is it?\n"))


def render_drift(drift: dict) -> None:
    con.header("Drift check — docs vs. reality")
    und = drift["undocumented_in_claude_md"]
    if not und:
        con.ok(f"all {drift['live_jobs']} live launchd jobs are named in CLAUDE.md")
    else:
        con.fail(f"{len(und)} live job(s) NOT documented in CLAUDE.md: {', '.join(und)}")
        con.step("→ add them to CLAUDE.md 'Active launchd jobs', or retire the job")


def main() -> int:
    args = set(sys.argv[1:])

    loops = _safe(collect_loops, "loops")
    if "--drift" in args:
        drift = collect_drift(loops if isinstance(loops, list) else [])
        if "--json" in args:
            print(json.dumps(drift, indent=2))
        else:
            render_drift(drift)
        return 1 if drift.get("undocumented_in_claude_md") else 0

    data = {
        "repos": _safe(collect_repos, "repos"),
        "loops": loops,
        "hooks": _safe(collect_hooks, "hooks"),
        "mcp": _safe(collect_mcp, "mcp"),
        "skills": _safe(collect_skills, "skills"),
        "maps": _safe(collect_maps, "maps"),
    }
    data["drift"] = collect_drift(loops if isinstance(loops, list) else [])

    if "--json" in args:
        print(json.dumps(data, indent=2, default=str))
    else:
        render(data)
    return 0


def _safe(fn, label):
    """Fault-isolate a section so one failure doesn't kill the whole map."""
    try:
        return fn()
    except Exception as e:  # noqa: BLE001 — orientation must never hard-fail
        return {"error": f"{type(e).__name__}: {e}", "section": label}


if __name__ == "__main__":
    raise SystemExit(main())
