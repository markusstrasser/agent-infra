#!/usr/bin/env python3
"""Plan status tracker — scans .claude/plans/ across projects.

Usage:
    plan-status.py                  # Human-readable table
    plan-status.py --json           # Machine-readable JSON
    plan-status.py --active         # Only partial/running plans
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

PROJECTS_DIR = Path.home() / "Projects"
PROJECT_NAMES = ["agent-infra", "intel", "phenome", "genomics", "arc-agi", "skills"]

# --- Planning-lifecycle contract (ADR 2026-06-18-planning-lifecycle-contract) ---
# Phase-1 MINIMAL slice: partial-regime only; 3 fields, each mapped to an uncovered
# failure class (panel invariant: a field with no class is a tracker field → cut).
# Do NOT add fields/regimes here until a field is shown to change an outcome.
# Regime is REPO-LEVEL (panel); a per-plan `regime:` frontmatter line overrides.
REGIME_BY_PROJECT = {"hutter": "clean", "genomics": "partial", "phenome": "partial"}
CONTRACT_REQUIRED = {"partial": ["exit_signal", "scope_out", "verifier_commands"]}
CONTRACT_FIELD_CLASS = {
    "exit_signal": "D4 — no measurable stop",
    "scope_out": "D3/D2 — unscoped op / scope creep",
    "verifier_commands": "D2 — closure without surfacing verifier output",
}


def parse_frontmatter(text: str) -> dict:
    """Extract YAML-ish frontmatter from plan file."""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                val = [v.strip().strip("'\"") for v in val[1:-1].split(",") if v.strip()]
            fm[key.strip()] = val
    return fm


def plan_regime(project: str, fm: dict) -> str | None:
    """Repo-level regime; a per-plan `regime:` frontmatter line overrides (panel: repo-level default)."""
    return fm.get("regime") or REGIME_BY_PROJECT.get(project)


def merge_frontmatter(filepath: str, updates: dict):
    """Merge keys into a plan's YAML frontmatter, preserving existing keys (reuses parse_frontmatter)."""
    p = Path(filepath)
    text = p.read_text()
    fm = parse_frontmatter(text)
    fm.update({k: v for k, v in updates.items() if v is not None})
    lines = []
    for k, v in fm.items():
        lines.append(f"{k}: [{', '.join(v)}]" if isinstance(v, list) else f"{k}: {v}")
    new_fm = "---\n" + "\n".join(lines) + "\n---\n"
    if text.startswith("---\n"):
        text = re.sub(r"^---\n.*?\n---\n", new_fm, text, count=1, flags=re.DOTALL)
    else:
        text = new_fm + text
    p.write_text(text)


def contract_check(plans: list[dict]) -> list[dict]:
    """Advisory: report contract fields missing by regime. Slice scopes to partial. Never blocks."""
    out = []
    for p in plans:
        required = CONTRACT_REQUIRED.get(p.get("regime") or "")
        if not required:
            continue  # slice covers partial-regime only; others skipped (post-validation)
        missing = [f for f in required if not p.get("contract", {}).get(f)]
        out.append({**p, "missing": missing})
    return out


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
            total_phases, phase_ids = count_phases(text)
            stat = f.stat()
            results.append({
                "project": name,
                "file": f.name,
                "path": str(f),
                "status": fm.get("status", "unknown"),
                "regime": plan_regime(name, fm),
                "contract": {k: fm.get(k) for k in CONTRACT_FIELD_CLASS},
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
    # Planning-lifecycle contract (Phase-1 slice) — advisory check + light elicitation
    parser.add_argument("--contract-check", action="store_true",
                        help="Advisory: report contract fields missing by regime (never blocks)")
    parser.add_argument("--contract-init", metavar="FILE",
                        help="Write contract fields into a plan's frontmatter (light elicitation)")
    parser.add_argument("--exit-signal", help="contract: measurable stop condition (D4)")
    parser.add_argument("--scope-out", help="contract: what this must NOT become (D3/D2)")
    parser.add_argument("--verifier", help="contract: verifier_commands surfaced at close (D2)")
    parser.add_argument("--regime", help="override repo-level regime for --contract-init")
    args = parser.parse_args()

    if args.update:
        completed = args.completed.split(",") if args.completed else None
        update_plan(args.update, args.status, completed)
        return

    if args.contract_init:
        merge_frontmatter(args.contract_init, {
            "regime": args.regime, "exit_signal": args.exit_signal,
            "scope_out": args.scope_out, "verifier_commands": args.verifier,
        })
        print(f"  ✓ contract written to {Path(args.contract_init).name}", file=sys.stderr)
        return

    if args.contract_check:
        rows = contract_check(scan_plans())
        if args.json:
            print(json.dumps(rows, indent=2))
            return
        complete = [r for r in rows if not r["missing"]]
        print(f"Plan-contract check (partial-regime; advisory) — {len(complete)}/{len(rows)} complete")
        for fld, cls in CONTRACT_FIELD_CLASS.items():
            print(f"  • {fld:<18} guards {cls}")
        print("-" * 78)
        for r in rows:
            mark = "✓" if not r["missing"] else "!"
            miss = "" if not r["missing"] else f"  missing: {', '.join(r['missing'])}"
            print(f"  {mark} {r['project']:<9} {r['file'][:48]:<48}{miss}")
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
