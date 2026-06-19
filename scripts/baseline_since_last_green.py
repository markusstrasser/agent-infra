#!/usr/bin/env python3
"""Baseline since last green — commits/files since recorded gate pass.

llm: none

Usage:
  baseline_since_last_green.py --repo ~/Projects/genomics
  baseline_since_last_green.py --repo . --gate canary --record-green
  baseline_since_last_green.py --repo . --suggest-only
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

from tool_contract import (
    GATE_GREEN,
    GATE_RED,
    GATE_SKIPPED,
    GATE_UNKNOWN,
    LlmClass,
    detect_default_gate,
    print_llm_header,
    repo_state_dir,
)

TOOL = "baseline-since-last-green"
COMMIT_THRESHOLD = 5
INFRA = Path(__file__).resolve().parent.parent


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True, stderr=subprocess.STDOUT).strip()


def git_ok(repo: Path, *args: str) -> bool:
    try:
        subprocess.check_call(["git", "-C", str(repo), *args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False


def state_path(repo: Path) -> Path:
    return repo_state_dir(repo, TOOL) / "last-green.json"


def load_state(repo: Path) -> dict:
    p = state_path(repo)
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return {}


def save_state_atomic(repo: Path, payload: dict) -> None:
    d = repo_state_dir(repo, TOOL)
    d.mkdir(parents=True, exist_ok=True)
    target = state_path(repo)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".json")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(payload, fh, indent=2)
            fh.write("\n")
        os.replace(tmp, target)
    except Exception:
        os.unlink(tmp)
        raise


def run_gate(repo: Path, gate: str) -> tuple[str, str]:
    if not (repo / "justfile").is_file():
        return GATE_UNKNOWN, "no justfile"
    try:
        r = subprocess.run(["just", gate], cwd=repo, capture_output=True, text=True, timeout=600)
        tail = (r.stdout + r.stderr)[-500:]
        return (GATE_GREEN if r.returncode == 0 else GATE_RED), tail
    except subprocess.TimeoutExpired:
        return GATE_UNKNOWN, "gate timeout 600s"
    except FileNotFoundError:
        return GATE_UNKNOWN, "just not found"


def commits_since(repo: Path, sha: str | None, *, fallback_n: int | None) -> list[str]:
    try:
        if sha:
            out = git(repo, "log", f"{sha}..HEAD", "--oneline")
        elif fallback_n:
            out = git(repo, "log", f"-{fallback_n}", "--oneline")
        else:
            return []
    except subprocess.CalledProcessError:
        return []
    return [ln for ln in out.splitlines() if ln.strip()]


def changed_files_since(repo: Path, sha: str | None, *, fallback_n: int | None) -> list[str]:
    try:
        if sha:
            out = git(repo, "diff", "--name-only", sha, "HEAD")
        elif fallback_n:
            out = git(repo, "diff", "--name-only", f"HEAD~{fallback_n}", "HEAD")
        else:
            return []
    except subprocess.CalledProcessError:
        return []
    return sorted({ln.strip() for ln in out.splitlines() if ln.strip()})


def git_anomaly(repo: Path) -> str | None:
    if not git_ok(repo, "rev-parse", "--verify", "HEAD"):
        return "invalid HEAD"
    try:
        git(repo, "symbolic-ref", "-q", "HEAD")
    except subprocess.CalledProcessError:
        return "detached HEAD"
    return None


def build_report(
    repo: Path,
    *,
    gate: str,
    gate_status: str,
    baseline_sha: str | None,
    head_sha: str,
    commits: list[str],
    files: list[str],
    allow_no_baseline: bool,
) -> dict:
    reasons: list[str] = []
    if gate_status == GATE_RED:
        reasons.append(f"gate `{gate}` RED")
    if gate_status == GATE_UNKNOWN:
        reasons.append(f"gate `{gate}` UNKNOWN")
    if baseline_sha and len(commits) >= COMMIT_THRESHOLD:
        reasons.append(f"{len(commits)} commits since baseline (≥{COMMIT_THRESHOLD})")
    elif not baseline_sha and allow_no_baseline and len(commits) >= COMMIT_THRESHOLD:
        reasons.append(f"no baseline; {len(commits)} commits in window (≥{COMMIT_THRESHOLD})")
    clinical = [f for f in files if f.startswith(("scripts/", "src/", "pipeline", "agent/", "loop/"))]
    if len(clinical) >= 3:
        reasons.append(f"{len(clinical)} high-churn path files changed")
    trigger = bool(reasons) and gate_status != GATE_RED
    suggested = (
        f"just adversarial-debug-scout {repo} --scope recent"
        if trigger
        else "(none)"
    )
    return {
        "tool": TOOL,
        "llm": LlmClass.NONE.value,
        "repo": str(repo),
        "head_sha": head_sha,
        "baseline_sha": baseline_sha,
        "gate": gate,
        "gate_status": gate_status,
        "commits_since": len(commits),
        "files_changed": len(files),
        "trigger_scout": trigger,
        "reasons": reasons,
        "suggested_cmd": suggested,
        "consumer_note": "Treat gate_status UNKNOWN like RED for autonomous apply.",
    }


def render(report: dict, commits: list[str], files: list[str]) -> str:
    day = date.today().isoformat()
    gs = report["gate_status"]
    lines = [
        f"# Baseline since last green — {day}",
        "",
        f"**Repo:** `{report['repo']}`",
        f"**HEAD:** `{report['head_sha'][:12]}`",
        f"**Baseline:** `{report['baseline_sha'][:12] if report.get('baseline_sha') else '(none)'}`",
        f"**Gate:** `{report['gate']}` — **{gs}**",
        f"**Commits since baseline:** {report['commits_since']}",
        f"**Files changed:** {report['files_changed']}",
        "",
    ]
    if report["reasons"]:
        lines.extend(["## Trigger reasons", ""] + [f"- {r}" for r in report["reasons"]] + [""])
    lines.append(f"**Suggested:** `{report['suggested_cmd']}`")
    lines.append("")
    if commits[:10]:
        lines.extend(["## Recent commits", ""] + [f"- {c}" for c in commits[:10]] + [""])
    if files[:20]:
        lines.extend(["## Changed files (sample)", ""] + [f"- `{f}`" for f in files[:20]] + [""])
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--gate", help="just recipe (default: autodetect)")
    ap.add_argument("--record-green", action="store_true")
    ap.add_argument("--suggest-only", action="store_true")
    ap.add_argument("--allow-no-baseline", action="store_true")
    ap.add_argument("--write", type=Path)
    args = ap.parse_args()

    print_llm_header(LlmClass.NONE)
    repo = args.repo.resolve()
    if not repo.is_dir():
        print(f"Not a directory: {repo}", file=sys.stderr)
        return 1

    anomaly = git_anomaly(repo)
    head_sha = git(repo, "rev-parse", "HEAD") if not anomaly else ""
    gate = args.gate or detect_default_gate(repo)
    state = load_state(repo)
    baseline_sha = state.get("sha")

    if args.record_green:
        gs, tail = run_gate(repo, gate)
        if gs == GATE_GREEN:
            save_state_atomic(repo, {
                "repo": str(repo), "gate": gate, "sha": head_sha,
                "ts": datetime.now(timezone.utc).isoformat(),
            })
            print(f"recorded green @ {head_sha[:8]}", file=sys.stderr)
        else:
            print(tail[-300:], file=sys.stderr)
            return 1
        gate_status = gs
    elif args.suggest_only:
        gate_status = GATE_SKIPPED
    else:
        gate_status, tail = run_gate(repo, gate)
        if gate_status != GATE_GREEN:
            print(tail[-300:], file=sys.stderr)

    if anomaly:
        gate_status = GATE_UNKNOWN
        commits, files = [], []
    else:
        fb = 20 if (args.allow_no_baseline and not baseline_sha) else None
        commits = commits_since(repo, baseline_sha, fallback_n=fb)
        files = changed_files_since(repo, baseline_sha, fallback_n=fb)

    report = build_report(
        repo, gate=gate, gate_status=gate_status, baseline_sha=baseline_sha,
        head_sha=head_sha, commits=commits, files=files,
        allow_no_baseline=args.allow_no_baseline,
    )

    out_dir = repo_state_dir(repo, TOOL)
    out_dir.mkdir(parents=True, exist_ok=True)
    day = date.today().isoformat()
    json_path = out_dir / f"{day}-report.json"
    json_path.write_text(json.dumps(report, indent=2) + "\n")
    md_path = args.write or out_dir / f"{day}-report.md"
    md_path.write_text(render(report, commits, files))

    print(md_path)
    if report["trigger_scout"]:
        print(report["suggested_cmd"], file=sys.stderr)
        return 2
    if gate_status in (GATE_RED, GATE_UNKNOWN) and not args.suggest_only:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
