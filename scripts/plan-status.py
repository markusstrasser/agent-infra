#!/usr/bin/env python3
"""Plan status tracker — scans .claude/plans/ across projects.

Usage:
    plan-status.py                  # Human-readable table
    plan-status.py --json           # Machine-readable JSON
    plan-status.py --active         # Only partial/running plans
    plan-status.py --verify-coverage  # Which plans carry a runnable ```verify block
    plan-status.py --update FILE STATUS [--completed PHASES]
                                    # Update plan frontmatter

Plan files use YAML frontmatter:
    ---
    status: pending|running|partial|done|failed
    completed_phases: [1, 2]
    content_hash: abc123
    updated: 2026-03-17T12:00:00Z
    ---
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Frontmatter parse is the shared, behavior-preserving plan_core extraction
# (substrate/packages/plan-core) — same narrow-YAML parser genomics planctl uses,
# single-sourced here rather than re-hand-rolled.
from plan_core import parse_frontmatter as _pc_parse_frontmatter

PROJECTS_DIR = Path.home() / "Projects"
PROJECT_NAMES = ["agent-infra", "intel", "phenome", "genomics", "arc-agi", "skills"]


def parse_frontmatter(text: str) -> dict:
    """Extract frontmatter from a plan file via the shared plan_core engine.

    Returns ``{}`` when the file has no frontmatter (plan_core returns ``None``)
    so the cross-project scan stays tolerant of un-fronted plans — many
    agent-infra `.claude/plans/*.md` have none. On malformed frontmatter,
    plan_core raises ``ValueError``; we swallow it to ``{}`` here because this is
    a read-only status scanner that must never crash on one bad file.
    """
    try:
        meta, _ = _pc_parse_frontmatter(text)
    except ValueError:
        return {}
    return meta or {}


def has_verify_block(text: str) -> bool:
    """True if the plan body has a ```verify block with >=1 runnable command.

    The plan-closure mechanism is the ` ```verify ` block, RUN and BLOCKED-ON by
    skills/hooks/stop-plan-gate.sh (globally wired). This is the agent-infra-side
    ADOPTION metric for that mechanism — NOT a parallel frontmatter contract. A
    2026-06-19 history check found the gate fires in every repo but 0/334 plans
    supplied a block; the binding constraint was adoption, so /decide now emits one
    and this reports coverage.

    Parse mirrors stop-plan-gate.sh EXACTLY (lines between a ```verify fence and the
    next ``` fence, excluding blanks and # comments) so coverage == what the gate
    would actually run. The hook stays authoritative for enforcement; this is a
    read-only dashboard, so a slight parse drift only mis-counts, never mis-gates.
    """
    in_verify = False
    cmds: list[str] = []
    for line in text.splitlines():
        s = line.rstrip()
        if s.startswith("```verify"):
            in_verify = True
            continue
        if in_verify and s.startswith("```"):
            break
        if in_verify:
            cmds.append(s)
    return any(c.strip() and not c.strip().startswith("#") for c in cmds)


def verify_coverage(plans: list[dict]) -> list[dict]:
    """Per-plan verify-block presence — the enforced-gate adoption metric."""
    return [
        {"project": p["project"], "file": p["file"], "has_verify": p["verify_block"]}
        for p in plans
    ]


def content_hash(text: str) -> str:
    """Hash plan body (everything after frontmatter) for idempotency."""
    m = re.match(r"^---\n.*?\n---\n(.*)$", text, re.DOTALL)
    body = m.group(1) if m else text
    return hashlib.sha256(body.encode()).hexdigest()[:12]


def count_phases(text: str) -> tuple[int, list[str]]:
    """Count total phases and identify completed ones from ### Phase headers."""
    phases = re.findall(r"^### Phase (\d+[a-z]?):?\s*(.*)", text, re.MULTILINE)
    total = len(phases)
    return total, [p[0] for p in phases]


def scan_plans() -> list[dict]:
    """Scan all projects for plan files."""
    results = []
    for name in PROJECT_NAMES:
        plans_dir = PROJECTS_DIR / name / ".claude" / "plans"
        if not plans_dir.exists():
            continue
        for f in sorted(plans_dir.glob("*.md")):
            try:
                text = f.read_text()
            except OSError:
                continue
            fm = parse_frontmatter(text)
            total_phases, _ = count_phases(text)
            stat = f.stat()
            results.append({
                "project": name,
                "file": f.name,
                "path": str(f),
                "status": fm.get("status", "unknown"),
                "plan_kind": fm.get("plan_kind"),
                "verify_block": has_verify_block(text),
                "completed_phases": fm.get("completed_phases", []),
                "total_phases": total_phases,
                "content_hash": content_hash(text),
                "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "size": stat.st_size,
            })
    return results


def update_plan(filepath: str, status: str, completed: list[str] | None = None):
    """Update or add YAML frontmatter to a plan file."""
    p = Path(filepath)
    text = p.read_text()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    chash = content_hash(text)

    new_fm = f"---\nstatus: {status}\n"
    if completed:
        new_fm += f"completed_phases: [{', '.join(completed)}]\n"
    new_fm += f"content_hash: {chash}\nupdated: {now}\n---\n"

    # Replace existing frontmatter or prepend
    if text.startswith("---\n"):
        text = re.sub(r"^---\n.*?\n---\n", new_fm, text, count=1, flags=re.DOTALL)
    else:
        text = new_fm + text

    p.write_text(text)
    print(f"Updated {p.name}: status={status}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Plan status tracker")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--active", action="store_true", help="Only partial/running")
    parser.add_argument("--update", metavar="FILE", help="Update plan status")
    parser.add_argument("--status", default="partial", help="Status to set")
    parser.add_argument("--completed", help="Comma-separated completed phase numbers")
    parser.add_argument("--verify-coverage", action="store_true",
                        help="Report which plans carry a runnable ```verify block "
                             "(the enforced stop-plan-gate mechanism; advisory, never blocks)")
    args = parser.parse_args()

    if args.update:
        completed = args.completed.split(",") if args.completed else None
        update_plan(args.update, args.status, completed)
        return

    if args.verify_coverage:
        rows = verify_coverage(scan_plans())
        if args.json:
            print(json.dumps(rows, indent=2))
            return
        covered = [r for r in rows if r["has_verify"]]
        print(f"Verify-block coverage (skills/hooks/stop-plan-gate.sh runs + blocks on it) — "
              f"{len(covered)}/{len(rows)} plans carry a runnable ```verify block")
        print("  a plan with no block gets NO stop-time enforcement; /decide now emits one")
        print("-" * 78)
        for r in rows:
            mark = "✓" if r["has_verify"] else "!"
            print(f"  {mark} {r['project']:<9} {r['file'][:56]}")
        return

    plans = scan_plans()
    if args.active:
        plans = [p for p in plans if p["status"] in ("partial", "running")]

    if args.json:
        print(json.dumps(plans, indent=2))
        return

    if not plans:
        print("No plans found.")
        return

    # Table output
    print(f"{'Project':<10} {'Status':<10} {'Phases':<10} {'Modified':<22} {'File'}")
    print("-" * 90)
    for p in plans:
        completed = p["completed_phases"]
        phase_str = f"{len(completed) if isinstance(completed, list) else '?'}/{p['total_phases']}" if p["total_phases"] else "—"
        mod = p["modified"][:16].replace("T", " ")
        status = p["status"]
        from common.console import color_status
        status = color_status(status)
        print(f"{p['project']:<10} {status:<20} {phase_str:<10} {mod:<22} {p['file']}")


if __name__ == "__main__":
    main()
