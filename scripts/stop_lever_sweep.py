#!/usr/bin/env python3
# Gov-ID: tool:stop-lever-sweep
# goal: deterministic checklist of cheap reversible probes still available at Stop
# verifier: --selftest
# blast_radius: local (called by stop-idle-lever-sweep hook; llm:none)
"""stop_lever_sweep.py — llm:none lever checklist for idle Stop wind-downs.

Used by skills/hooks/stop-idle-lever-sweep.py (shadow → advisory). Surfaces:
  • recent git commits
  • open `[ ]` rows in ideas.md / HUMAN.md (capped)
  • fresh audit/debug artifacts (7d)
  • recent agentlogs titles (best-effort, 3s timeout)
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

OPEN_ROW = re.compile(r"^\s*[-*]\s*\[\s*\]\s+")
AUDIT_GLOBS = (
    "artifacts/**/debug*.md",
    "docs/audit/**/*.md",
    "**/DEBUG_UNTIL_DRY*.md",
)


def _run(cmd: list[str], *, cwd: Path, timeout: float = 3.0) -> str:
    try:
        r = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return (r.stdout or "").strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _open_todos(cwd: Path, limit: int = 5) -> list[str]:
    rows: list[str] = []
    for name in ("ideas.md", "HUMAN.md", "loop/HUMAN.md", ".claude/ideas.md"):
        p = cwd / name
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for ln in text.splitlines():
            if OPEN_ROW.match(ln):
                rows.append(f"{name}: {ln.strip()[:120]}")
                if len(rows) >= limit:
                    return rows
    return rows


def _fresh_audits(cwd: Path, days: int = 7, limit: int = 5) -> list[str]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    hits: list[tuple[float, str]] = []
    for pattern in AUDIT_GLOBS:
        for p in cwd.glob(pattern):
            if not p.is_file():
                continue
            try:
                mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
            except OSError:
                continue
            if mtime >= cutoff:
                hits.append((mtime.timestamp(), str(p.relative_to(cwd))))
    hits.sort(reverse=True)
    return [path for _, path in hits[:limit]]


def checklist(cwd: Path, *, project: str = "") -> str:
    cwd = cwd.expanduser().resolve()
    project = project or cwd.name
    lines = [
        f"LEVER SWEEP ({project}) — cheap reversible probes still available:",
        "",
        "Recent git:",
    ]
    git = _run(["git", "log", "--oneline", "-5"], cwd=cwd)
    lines.extend(f"  {ln}" for ln in (git.splitlines() if git else ["(no git log)"]))

    todos = _open_todos(cwd)
    lines.append("")
    lines.append("Open `[ ]` rows:")
    if todos:
        lines.extend(f"  {t}" for t in todos)
    else:
        lines.append("  (none in ideas.md / HUMAN.md)")

    audits = _fresh_audits(cwd)
    lines.append("")
    lines.append("Fresh audit/debug artifacts (7d):")
    if audits:
        lines.extend(f"  {a}" for a in audits)
    else:
        lines.append("  (none)")

    al = _run(
        ["uv", "run", "agentlogs", "recent", "--project", project, "--limit", "3"],
        cwd=cwd,
        timeout=3.0,
    )
    lines.append("")
    lines.append("agentlogs recent:")
    if al:
        lines.extend(f"  {ln}" for ln in al.splitlines()[:6])
    else:
        lines.append("  (unavailable / timeout)")

    lines.append("")
    lines.append(
        "Before stopping: list 1–3 reversible probes you have NOT run this session "
        "(experiments, transcript reads, parallel portfolio items). If none, say why."
    )
    return "\n".join(lines)


def _selftest() -> int:
    out = checklist(Path.home() / "Projects" / "agent-infra", project="agent-infra")
    ok = "LEVER SWEEP" in out and "Recent git:" in out
    print("PASS" if ok else "FAIL")
    print(out[:400])
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cwd", default=".")
    ap.add_argument("--project", default="")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    print(checklist(Path(args.cwd), project=args.project))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
