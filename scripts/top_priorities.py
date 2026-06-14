#!/usr/bin/env python3
"""top_priorities.py — the loop's end-of-run answer to "what should we PLAN next?"

The outer loop kept reporting "verified noop / all green" while real work sat
undone — because it watched proxies (hooks/launchd/indexer), never surfaced a
ranked list, and the one aggregator that existed (propose-work.py) drowned real
items under transient noise (stale-agent jsonl, other-repos' uncommitted edits).
(2026-06-14, user: "it should mention after each run the top 10 priorities that
should be planned.")

This pulls ONLY high-signal, actionable, plannable sources, ranks by leverage,
and emits a tight Top-N. It deliberately EXCLUDES the transient proxy noise that
made the morning-brief unreadable. Deterministic, read-only, ~$0.

Sources (highest-leverage first):
  - broken tools actively failing in real use  (observe/scan_tool_failures.py)
  - decisions-pending/  (value blocked on a human yes/no, already drafted)
  - improvement-log.md  [ ] genuinely-open actionable items (NOT [obs]/[x]/...)
  - doctor.py REAL fails/warns  (excludes stale-agent / uncommitted / mcp / memory)
  - stale .claude/plans/  (started, not finished)
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOME = Path.home()
IMPROVEMENT_LOG = REPO / "improvement-log.md"
DECISIONS_PENDING = REPO / "decisions-pending"
FAILURES_SCRIPT = HOME / "Projects" / "skills" / "observe" / "scripts" / "scan_tool_failures.py"
PLANS_DIR = REPO / ".claude" / "plans"

# doctor warnings that are transient/by-design noise, NOT plannable priorities
DOCTOR_NOISE = ("stale-agent", "git:uncommitted", "mcp", "memory:", "CLAUDE.md")

# class -> base leverage score
SCORE = {
    "broken-tool": 100,
    "pending-decision": 80,
    "open-finding": 60,
    "doctor": 50,
    "stale-plan": 40,
}


def _run_json(cmd: list[str]) -> list | dict | None:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120).stdout
        return json.loads(out) if out.strip() else None
    except Exception:
        return None


def broken_tools() -> list[dict]:
    if not FAILURES_SCRIPT.exists():
        return []
    rows = _run_json(["python3", str(FAILURES_SCRIPT), "--days", "14", "--json"]) or []
    out: list[dict] = []
    dep_mods, dep_fails, dep_days = [], 0, 0
    for r in rows:
        cluster = str(r.get("cluster", ""))
        days, fails = r.get("distinct_days", 0), r.get("fails", 0)
        # broken-cli (a specific CLI can't start) stays its OWN priority — distinct, high
        if cluster.startswith("broken-cli"):
            out.append({
                "klass": "broken-tool",
                "score": SCORE["broken-tool"] + min(days, 20),
                "title": f"Broken CLI: {cluster}",
                "why": f"{fails} fails / {days}d — {r.get('sample','')[:70]}",
                "action": "fix the editable/entry-point; verify with a live run",
            })
        # missing-module:* are largely ONE root cause (bare-python/uvx invocation
        # or absent env deps) — collapse into a single priority, don't spam 8 rows
        elif cluster.startswith("missing-module:") and days >= 2:
            dep_mods.append(cluster.split(":", 1)[1])
            dep_fails += fails
            dep_days = max(dep_days, days)
        elif cluster.startswith("import-error") and days >= 2:
            out.append({
                "klass": "broken-tool",
                "score": SCORE["broken-tool"] + min(days, 20) - 5,
                "title": "Recurring ImportError (code/refactor break)",
                "why": f"{fails} fails / {days}d — {r.get('sample','')[:70]}",
                "action": "find the stale import vs moved symbol; fix the caller",
            })
    if dep_mods:
        top = ", ".join(dep_mods[:8]) + (" …" if len(dep_mods) > 8 else "")
        out.append({
            "klass": "broken-tool",
            "score": SCORE["broken-tool"] + min(dep_days, 20) + 5,  # biggest cluster
            "title": f"Recurring missing-dep failures across {len(dep_mods)} modules",
            "why": f"{dep_fails} fails / {dep_days}d — {top}. Likely bare-`python3`/`uvx` invocation or absent env deps",
            "action": "fix invocation discipline (uv run) or add deps; consider a guard for `uvx python3`",
        })
    return out


def pending_decisions() -> list[dict]:
    if not DECISIONS_PENDING.is_dir():
        return []
    out = []
    for f in sorted(DECISIONS_PENDING.glob("*.md")):
        if f.name == "README.md":
            continue
        title = ""
        for line in f.read_text().splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break
        out.append({
            "klass": "pending-decision",
            "score": SCORE["pending-decision"],
            "title": f"Decide: {title or f.stem}",
            "why": f"drafted, awaiting your yes/no — {f.name}",
            "action": f"review decisions-pending/{f.name}",
        })
    return out


def open_findings() -> list[dict]:
    """[ ] genuinely-open actionable items, grouped under their ### header."""
    if not IMPROVEMENT_LOG.exists():
        return []
    out, header = [], ""
    seen = set()
    for line in IMPROVEMENT_LOG.read_text().splitlines():
        if line.startswith("### "):
            header = line[4:].strip()
        elif re.search(r"\[\s\]", line) and "Status" in line:
            # an open actionable status line under the current header
            if header and header not in seen:
                seen.add(header)
                out.append({
                    "klass": "open-finding",
                    "score": SCORE["open-finding"],
                    "title": header[:90],
                    "why": re.sub(r"\s+", " ", line.strip())[:90],
                    "action": "scope + plan, or fix if cheap/local",
                })
    return out


def doctor_real() -> list[dict]:
    rows = _run_json(["uv", "run", "python3", str(REPO / "scripts" / "doctor.py"), "--json"]) or []
    out = []
    for r in rows:
        if r.get("status") not in ("fail", "warn"):
            continue
        name = r.get("name", "")
        if any(name.startswith(n) or n in name for n in DOCTOR_NOISE):
            continue
        out.append({
            "klass": "doctor",
            "score": SCORE["doctor"] + (15 if r["status"] == "fail" else 0),
            "title": f"Health: {name}",
            "why": r.get("message", "")[:90],
            "action": "diagnose + fix the mechanical issue",
        })
    return out


def stale_plans(days: int = 7) -> list[dict]:
    if not PLANS_DIR.is_dir():
        return []
    now = datetime.now(timezone.utc).timestamp()
    out = []
    for f in PLANS_DIR.glob("*.md"):
        age_d = (now - f.stat().st_mtime) / 86400
        if age_d > days:
            out.append({
                "klass": "stale-plan",
                "score": SCORE["stale-plan"],
                "title": f"Stale plan: {f.stem[:80]}",
                "why": f"untouched {age_d:.0f}d — finish or drop",
                "action": "resume, or archive if abandoned",
            })
    return out


def gather() -> list[dict]:
    items: list[dict] = []
    for src in (broken_tools, pending_decisions, open_findings, doctor_real, stale_plans):
        try:
            items.extend(src())
        except Exception as e:  # one bad source never sinks the digest
            items.append({"klass": "doctor", "score": 1,
                          "title": f"(priorities source {src.__name__} errored)",
                          "why": str(e)[:80], "action": "fix the priorities scanner"})
    items.sort(key=lambda x: x["score"], reverse=True)
    return items


def render(items: list[dict], top: int) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    lines = [f"# Top priorities to plan — {stamp}", ""]
    if not items:
        lines.append("_Nothing actionable surfaced. If this persists, the scanner's coverage is wrong, not the system perfect._")
        return "\n".join(lines) + "\n"
    for i, x in enumerate(items[:top], 1):
        lines.append(f"{i}. **[{x['klass']}]** {x['title']}")
        lines.append(f"   - why: {x['why']}")
        lines.append(f"   - → {x['action']}")
    extra = len(items) - top
    if extra > 0:
        lines.append(f"\n_(+{extra} more below the cut)_")
    return "\n".join(lines) + "\n"


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Ranked Top-N plannable priorities across repos.")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--out", default=str(REPO / "PRIORITIES.md"), help="digest path (gitignored)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    items = gather()
    if args.json:
        print(json.dumps(items[: args.top], indent=2))
        return 0
    digest = render(items, args.top)
    try:
        Path(args.out).write_text(digest)
    except Exception:
        pass
    print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
