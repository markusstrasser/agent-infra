#!/usr/bin/env python3
"""Propose ranked work items from cross-project signals.

Combines: git staleness, hook ROI highlights, unresolved improvement-log findings,
doctor.py failures, daily cost, orchestrator queue, and last session-retro findings.
Each proposal formatted as an orchestrator-submittable command.

Output: ~/.claude/morning-brief.md

Usage: uv run python3 scripts/propose-work.py [--days N] [--output PATH]
"""

import json
import logging
import re
import subprocess
import sys
from datetime import datetime, timedelta, date
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROJECTS_DIR = Path.home() / "Projects"
PROJECTS = ["meta", "intel", "selve", "genomics", "skills", "papers-mcp"]
RECEIPTS_FILE = Path.home() / ".claude" / "session-receipts.jsonl"
TRIGGERS_FILE = Path.home() / ".claude" / "hook-triggers.jsonl"
ORCHESTRATOR_DB = Path.home() / ".claude" / "orchestrator.db"
IMPROVEMENT_LOG = Path(__file__).resolve().parent.parent / "improvement-log.md"
RETRO_DIR = Path(__file__).resolve().parent.parent / "artifacts" / "session-retro"
HOOK_ROI_DIR = Path(__file__).resolve().parent.parent / "artifacts" / "hook-roi"
DESIGN_REVIEW_DIR = Path(__file__).resolve().parent.parent / "artifacts" / "design-review"
DEFAULT_OUTPUT = Path.home() / ".claude" / "morning-brief.md"

STALE_DAYS = 3  # flag projects with no commits in this many days

log = logging.getLogger("propose-work")


# ---------------------------------------------------------------------------
# Data collectors
# ---------------------------------------------------------------------------

def git_staleness(days: int) -> list[dict]:
    """Find projects with no commits in the last N days."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    stale = []
    for name in PROJECTS:
        proj_dir = PROJECTS_DIR / name
        if not (proj_dir / ".git").is_dir():
            continue
        try:
            result = subprocess.run(
                ["git", "-C", str(proj_dir), "log", "-1", "--format=%aI", "--all"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode != 0 or not result.stdout.strip():
                continue
            last_commit = result.stdout.strip()
            if last_commit < cutoff:
                days_ago = (datetime.now() - datetime.fromisoformat(last_commit)).days
                stale.append({
                    "project": name,
                    "last_commit": last_commit[:10],
                    "days_ago": days_ago,
                })
        except (subprocess.TimeoutExpired, Exception) as e:
            log.debug(f"git staleness check failed for {name}: {e}")
    return sorted(stale, key=lambda x: -x["days_ago"])


def hook_roi_highlights(days: int = 1) -> dict:
    """Extract high-fire and zero-block hooks from trigger log."""
    if not TRIGGERS_FILE.exists():
        return {"total": 0, "hooks": []}

    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    by_hook: dict[str, dict[str, int]] = {}

    with open(TRIGGERS_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = entry.get("ts", "")
            if ts < cutoff:
                continue
            hook = entry.get("hook", "?")
            action = entry.get("action", "?")
            if hook not in by_hook:
                by_hook[hook] = {"total": 0}
            by_hook[hook]["total"] += 1
            by_hook[hook][action] = by_hook[hook].get(action, 0) + 1

    hooks = []
    for name, counts in sorted(by_hook.items(), key=lambda x: -x[1]["total"]):
        total = counts["total"]
        blocks = counts.get("block", 0)
        warns = counts.get("warn", 0)
        hooks.append({
            "hook": name, "total": total, "blocks": blocks, "warns": warns,
            "block_rate": blocks / total if total else 0,
        })

    return {"total": sum(h["total"] for h in hooks), "hooks": hooks}


def unresolved_findings() -> list[dict]:
    """Parse improvement-log.md for unresolved findings."""
    if not IMPROVEMENT_LOG.exists():
        return []

    findings = []
    current_date = None
    current_title = None

    for line in IMPROVEMENT_LOG.read_text().splitlines():
        # Match date headers like ### [2026-03-04] ...
        date_match = re.match(r"^###\s+\[(\d{4}-\d{2}-\d{2})\]\s+(.*)", line)
        if date_match:
            current_date = date_match.group(1)
            current_title = date_match.group(2).strip()
            continue

        # Match status lines
        if line.strip().startswith("- **Status:**") and current_date and current_title:
            status_text = line.strip()
            if "[ ]" in status_text and "no action" not in status_text.lower():
                age_days = (datetime.now() - datetime.strptime(current_date, "%Y-%m-%d")).days
                findings.append({
                    "date": current_date,
                    "title": current_title,
                    "age_days": age_days,
                    "status": status_text,
                })

    return sorted(findings, key=lambda x: -x["age_days"])


def doctor_failures() -> list[dict]:
    """Run doctor.py and extract failures/warnings."""
    try:
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "doctor.py"), "--json"],
            capture_output=True, text=True, timeout=30,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        checks = json.loads(result.stdout)
        return [c for c in checks if c.get("status") in ("warn", "fail")]
    except json.JSONDecodeError:
        return [{"name": "doctor.py", "status": "fail", "message": f"exit {result.returncode}, no JSON output"}]
    except Exception as e:
        return [{"name": "doctor.py", "status": "fail", "message": str(e)[:100]}]


def daily_cost_summary(days: int = 1) -> dict:
    """Summarize session costs from receipts."""
    if not RECEIPTS_FILE.exists():
        return {"sessions": 0, "cost": 0.0, "by_project": {}}

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    sessions = 0
    total_cost = 0.0
    by_project: dict[str, float] = {}

    with open(RECEIPTS_FILE) as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
            except (json.JSONDecodeError, ValueError):
                continue
            ts = entry.get("ts", "")
            if ts[:10] < cutoff:
                continue
            sessions += 1
            cost = entry.get("cost_usd", 0) or 0
            total_cost += cost
            proj = entry.get("project", "?")
            by_project[proj] = by_project.get(proj, 0) + cost

    return {"sessions": sessions, "cost": total_cost, "by_project": by_project}


def orchestrator_queue() -> dict:
    """Get orchestrator queue snapshot."""
    if not ORCHESTRATOR_DB.exists():
        return {"pending": 0, "running": 0, "failed": 0, "tasks": []}

    import sqlite3
    db = sqlite3.connect(str(ORCHESTRATOR_DB))
    db.row_factory = sqlite3.Row

    pending = db.execute(
        "SELECT count(*) as n FROM tasks WHERE status='pending'"
    ).fetchone()["n"]
    running = db.execute(
        "SELECT count(*) as n FROM tasks WHERE status='running'"
    ).fetchone()["n"]
    failed_recent = db.execute(
        "SELECT id, pipeline, step, error FROM tasks WHERE status='failed' "
        "AND date(finished_at) >= date('now', '-3 days', 'localtime') "
        "ORDER BY finished_at DESC LIMIT 5"
    ).fetchall()
    tasks = [dict(r) for r in failed_recent]
    db.close()
    return {"pending": pending, "running": running, "failed": len(tasks), "tasks": tasks}


def last_session_retro() -> str | None:
    """Read most recent session-retro artifact."""
    if not RETRO_DIR.exists():
        return None
    files = sorted(RETRO_DIR.glob("*.md"), reverse=True)
    if not files:
        return None
    content = files[0].read_text().strip()
    return content[:2000] if content else None


def last_hook_roi() -> str | None:
    """Read most recent hook-roi artifact."""
    if not HOOK_ROI_DIR.exists():
        return None
    files = sorted(HOOK_ROI_DIR.glob("*.md"), reverse=True)
    if not files:
        return None
    content = files[0].read_text().strip()
    return content[:2000] if content else None


# ---------------------------------------------------------------------------
# Proposal generation
# ---------------------------------------------------------------------------

def _rank_score(proposal: dict) -> float:
    """Score a proposal for sorting. Higher = more urgent.

    Derived from autoresearch experiment (experiments/proposal-ranker/).
    Constitutional priority: health > orchestrator > high-block hooks >
    autonomy findings > staleness > cosmetic/info.
    """
    category = proposal.get("category", "")
    title = proposal.get("title", "")
    metadata = proposal.get("metadata", {})

    base = {
        "health": 80, "orchestrator": 70, "staleness": 40,
        "improvement-log": 30, "hook-roi": 20,
    }.get(category, 10)

    if "FAIL" in title:
        base += 20
    elif "WARN" in title:
        base += 5

    age_days = metadata.get("age_days", 0)
    if age_days > 14:
        base += min(age_days - 14, 20)

    days_ago = metadata.get("days_ago", 0)
    if days_ago > 7:
        base += 10

    block_rate = metadata.get("block_rate", 0)
    if block_rate > 0.3:
        base += 30

    consecutive = metadata.get("consecutive_failures", 0)
    if consecutive > 1:
        base += consecutive * 5

    tags = metadata.get("tags", [])
    if "autonomy" in tags or "hook" in tags:
        base += 15

    return base


def generate_proposals(data: dict) -> list[dict]:
    """Generate ranked work proposals from collected data."""
    proposals = []

    # Stale projects
    for proj in data["stale_projects"]:
        if proj["days_ago"] >= STALE_DAYS:
            proposals.append({
                "category": "staleness",
                "title": f"{proj['project']} has no commits in {proj['days_ago']} days",
                "metadata": {"days_ago": proj["days_ago"]},
                "command": f'orchestrator.py run -p {proj["project"]} --prompt "Review recent state, check for stale TODOs or pending work"',
            })

    # Doctor failures
    for check in data["doctor_failures"]:
        is_fail = check.get("status") == "fail"
        proposals.append({
            "category": "health",
            "title": f"{'FAIL' if is_fail else 'WARN'}: {check['name']} — {check.get('message', '')[:80]}",
            "metadata": {"scope": check.get("scope", "single")},
            "command": None,
        })

    # Unresolved improvement-log findings (>14 days old)
    for finding in data["unresolved_findings"]:
        if finding["age_days"] >= 14:
            proposals.append({
                "category": "improvement-log",
                "title": f"Unresolved ({finding['age_days']}d): {finding['title'][:60]}",
                "metadata": {"age_days": finding["age_days"]},
                "command": None,
            })

    # Hook ROI: high-block-rate hooks (potential false positives)
    for hook in data["hook_roi"].get("hooks", []):
        if hook["blocks"] > 5 and hook["block_rate"] > 0.5:
            proposals.append({
                "category": "hook-roi",
                "title": f"Hook '{hook['hook']}' blocking {hook['block_rate']:.0%} ({hook['blocks']}/{hook['total']}) — review for false positives",
                "metadata": {"block_rate": hook["block_rate"], "total": hook["total"], "blocks": hook["blocks"]},
                "command": None,
            })
        elif hook["total"] > 20 and hook["blocks"] == 0:
            proposals.append({
                "category": "hook-roi",
                "title": f"Hook '{hook['hook']}' fires {hook['total']}x but never blocks — consider promoting",
                "metadata": {"block_rate": 0, "total": hook["total"], "blocks": 0},
                "command": None,
            })

    # Failed orchestrator tasks
    for task in data["orchestrator"].get("tasks", []):
        proposals.append({
            "category": "orchestrator",
            "title": f"Task #{task['id']} failed: {task.get('pipeline', '?')}/{task.get('step', '?')} — {(task.get('error') or '?')[:60]}",
            "metadata": {},
            "command": f"orchestrator.py show {task['id']} --full",
        })

    # Score and sort (higher score = more urgent = first)
    for p in proposals:
        p["score"] = _rank_score(p)
        # Map score to priority label for display
        s = p["score"]
        p["priority"] = 1 if s >= 95 else 2 if s >= 70 else 3 if s >= 40 else 4 if s >= 25 else 5

    return sorted(proposals, key=lambda x: -x["score"])


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def render_brief(data: dict, proposals: list[dict]) -> str:
    """Render morning brief as markdown."""
    today = date.today().isoformat()
    lines = [
        f"# Morning Brief — {today}",
        "",
    ]

    # Cost summary
    cost = data["cost_summary"]
    lines.append(f"**Yesterday:** {cost['sessions']} sessions, ${cost['cost']:.2f} spent")
    if cost["by_project"]:
        parts = [f"{p}: ${c:.2f}" for p, c in sorted(cost["by_project"].items(), key=lambda x: -x[1])]
        lines.append(f"  By project: {', '.join(parts)}")
    lines.append("")

    # Orchestrator
    orch = data["orchestrator"]
    if orch["pending"] or orch["running"] or orch["failed"]:
        lines.append(f"**Orchestrator:** {orch['pending']} pending, {orch['running']} running, {orch['failed']} recently failed")
        lines.append("")

    # Proposals
    if proposals:
        lines.append(f"## Proposals ({len(proposals)})")
        lines.append("")
        for i, p in enumerate(proposals, 1):
            pri_label = {1: "URGENT", 2: "HIGH", 3: "MED", 4: "LOW", 5: "INFO"}.get(p["priority"], "?")
            lines.append(f"{i}. **[{pri_label}]** [{p['category']}] {p['title']}")
            if p.get("command"):
                lines.append(f"   ```")
                lines.append(f"   {p['command']}")
                lines.append(f"   ```")
        lines.append("")
    else:
        lines.append("## No proposals — all clear.")
        lines.append("")

    # Hook ROI summary
    roi = data["hook_roi"]
    if roi["total"] > 0:
        lines.append(f"## Hook Activity")
        lines.append(f"**{roi['total']}** triggers yesterday. Top hooks:")
        for h in roi["hooks"][:5]:
            parts = []
            if h["blocks"]:
                parts.append(f"{h['blocks']} block")
            if h["warns"]:
                parts.append(f"{h['warns']} warn")
            detail = ", ".join(parts) if parts else "?"
            lines.append(f"- {h['hook']}: {h['total']} ({detail})")
        lines.append("")

    # Session retro
    retro = data.get("last_retro")
    if retro:
        lines.append("## Last Session Retro")
        # Truncate to keep brief readable
        lines.append(retro[:1000])
        lines.append("")

    # Design review proposals
    dr = data.get("design_review_proposals")
    if dr:
        lines.append(f"## Design Review ({len(dr)} recurring patterns)")
        for p in dr[:5]:
            lines.append(f"- **{p['name']}** ({p['type']}, {p['count']}× across {p['projects']})")
        lines.append("")

    # Stale projects
    if data["stale_projects"]:
        lines.append("## Stale Projects")
        for p in data["stale_projects"]:
            lines.append(f"- **{p['project']}**: last commit {p['last_commit']} ({p['days_ago']}d ago)")
        lines.append("")

    # Doctor issues
    if data["doctor_failures"]:
        lines.append(f"## Doctor Issues ({len(data['doctor_failures'])})")
        for c in data["doctor_failures"][:10]:
            icon = "X" if c.get("status") == "fail" else "!"
            lines.append(f"- [{icon}] {c.get('scope', '?')}/{c['name']}: {c.get('message', '')[:80]}")
        lines.append("")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def design_review_proposals(days: int = 7) -> list[dict]:
    """Read design-review patterns.jsonl and find recurring patterns (3+)."""
    patterns_file = DESIGN_REVIEW_DIR / "patterns.jsonl"
    if not patterns_file.exists():
        return []

    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    counts: dict[str, dict] = {}  # name -> {count, type, projects}

    try:
        for line in patterns_file.read_text().splitlines():
            if not line.strip():
                continue
            try:
                p = json.loads(line)
            except json.JSONDecodeError:
                continue
            if p.get("ts", "") < cutoff:
                continue
            name = p.get("name", "unknown")
            if name not in counts:
                counts[name] = {
                    "name": name,
                    "type": p.get("type", "?"),
                    "count": 0,
                    "projects_set": set(),
                }
            counts[name]["count"] += 1
            for proj in p.get("projects", []):
                counts[name]["projects_set"].add(proj)
    except OSError:
        return []

    # Only surface patterns with 3+ recurrences
    results = []
    for entry in sorted(counts.values(), key=lambda x: -x["count"]):
        if entry["count"] >= 3:
            results.append({
                "name": entry["name"],
                "type": entry["type"],
                "count": entry["count"],
                "projects": ", ".join(sorted(entry["projects_set"])),
            })
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate morning work proposals")
    parser.add_argument("--days", type=int, default=1, help="Look-back window for costs/triggers")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT), help="Output path")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    log.info("Collecting signals...")

    data = {
        "stale_projects": git_staleness(STALE_DAYS),
        "hook_roi": hook_roi_highlights(args.days),
        "unresolved_findings": unresolved_findings(),
        "doctor_failures": doctor_failures(),
        "cost_summary": daily_cost_summary(args.days),
        "orchestrator": orchestrator_queue(),
        "last_retro": last_session_retro(),
        "last_hook_roi": last_hook_roi(),
        "design_review_proposals": design_review_proposals(days=7),
    }

    proposals = generate_proposals(data)
    brief = render_brief(data, proposals)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(brief)

    # Also print to stdout for debugging
    print(brief)
    print(f"Written to {output_path}")


if __name__ == "__main__":
    main()
