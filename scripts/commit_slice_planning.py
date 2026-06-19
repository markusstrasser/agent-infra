#!/usr/bin/env python3
"""Commit slice planning — cluster diff, optional agent-drafted messages, apply.

llm: optional (--draft-messages-with-agent)

Usage:
  commit_slice_planning.py --repo . --status-only
  commit_slice_planning.py --repo . --include-untracked
  commit_slice_planning.py --repo . --draft-messages-with-agent
  commit_slice_planning.py --repo . --apply 1
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from tool_contract import (
    LlmClass,
    is_excluded_path,
    llm_denied,
    print_llm_header,
    repo_state_dir,
)

TOOL = "commit-slice-planning"
AGENT = Path.home() / ".local/bin/agent"
PLACEHOLDER_MARKERS = ("<one-line", "<orchestrator", "…")


@dataclass
class Slice:
    id: int
    paths: list[str]
    ctype: str = "chore"
    scope: str = ""
    subject: str = ""
    gate: str = ""
    head_sha: str = ""


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True, stderr=subprocess.STDOUT)


def head_sha(repo: Path) -> str:
    return git(repo, "rev-parse", "HEAD").strip()


def changed_paths(repo: Path, include_untracked: bool) -> list[str]:
    names: list[str] = []
    names.extend(git(repo, "diff", "--name-only").splitlines())
    names.extend(git(repo, "diff", "--cached", "--name-only").splitlines())
    if include_untracked:
        for line in git(repo, "status", "--short").splitlines():
            if line.startswith("??"):
                names.append(line[3:].strip())
    out: list[str] = []
    seen: set[str] = set()
    for n in names:
        n = n.strip()
        if n and n not in seen and not is_excluded_path(n):
            seen.add(n)
            out.append(n)
    return sorted(out)


def cluster_key(path: str) -> str:
    if path.startswith("research/"):
        return "research"
    if path.startswith("decisions/"):
        return "decisions"
    if path.startswith("docs/audit/"):
        return "audit"
    if path.startswith(".claude/"):
        return "claude"
    if path.startswith("scripts/"):
        return "scripts"
    return Path(path).parts[0] if len(Path(path).parts) > 1 else "root"


def infer_type(paths: list[str]) -> str:
    if all(p.endswith(".md") for p in paths):
        return "docs"
    if any("test" in p for p in paths):
        return "test"
    if any(p.endswith((".py", ".sh")) for p in paths):
        return "feat"
    return "chore"


def infer_gate(repo: Path, paths: list[str]) -> str:
    jf = repo / "justfile"
    if not jf.is_file():
        return ""
    text = jf.read_text(errors="replace")
    if any(p.startswith("scripts/") for p in paths) and "harness-eval" in text:
        return "just harness-eval"
    if any(p.endswith(".py") for p in paths) and "smoke" in text:
        return "just smoke"
    return ""


def build_slices(repo: Path, paths: list[str], sha: str) -> list[Slice]:
    buckets: dict[str, list[str]] = {}
    for p in paths:
        buckets.setdefault(cluster_key(p), []).append(p)
    slices: list[Slice] = []
    for i, (key, ps) in enumerate(sorted(buckets.items()), start=1):
        slices.append(Slice(
            id=i, paths=ps, ctype=infer_type(ps),
            scope=key if key not in ("root", "scripts") else repo.name,
            subject=f"<one-line why for {key}>",
            gate=infer_gate(repo, ps), head_sha=sha,
        ))
    return slices


def draft_messages_with_agent(repo: Path, slices: list[Slice]) -> None:
    if not AGENT.is_file():
        print("agent CLI missing", file=sys.stderr)
        return
    lines = []
    for s in slices:
        listing = "\n".join(f"  {p}" for p in s.paths[:30])
        lines.append(f"Slice {s.id} ({s.ctype}/{s.scope}):\n{listing}\n")
    prompt = (
        "Reply ONE line per slice ONLY:\nSLICE N: type(scope): subject\n\n" + "\n".join(lines)
    )
    r = subprocess.run(
        [str(AGENT), "-p", "--trust", "--mode", "ask", "--model", "composer-2.5",
         "--workspace", str(repo), prompt],
        capture_output=True, text=True, timeout=120,
    )
    if r.returncode != 0:
        print(r.stderr[:300], file=sys.stderr)
        return
    for line in r.stdout.splitlines():
        m = re.match(r"SLICE\s+(\d+):\s*(.+)", line.strip(), re.I)
        if not m:
            continue
        sid = int(m.group(1))
        msg = m.group(2).strip()
        for s in slices:
            if s.id != sid:
                continue
            parts = msg.split(":", 1)
            if len(parts) == 2 and "(" in parts[0]:
                m2 = re.match(r"(\w+)\(([^)]+)\)", parts[0])
                if m2:
                    s.ctype, s.scope = m2.group(1), m2.group(2)
                s.subject = parts[1].strip()
            else:
                s.subject = msg


def status_only(repo: Path, paths: list[str]) -> str:
    status = git(repo, "status", "--short")
    stat = git(repo, "diff", "--stat")
    lines = [
        f"# Commit slice status — {date.today().isoformat()}",
        f"**Repo:** `{repo}` · **HEAD:** `{head_sha(repo)[:12]}`",
        "",
        "```", status.strip() or "(clean)", "```",
        "", "## Diff stat", "```", stat.strip() or "(none)", "```",
        "", "## Files", *(f"- `{p}`" for p in paths[:50]),
    ]
    return "\n".join(lines) + "\n"


def write_plan(repo: Path, slices: list[Slice]) -> tuple[Path, Path]:
    out_dir = repo_state_dir(repo, TOOL)
    out_dir.mkdir(parents=True, exist_ok=True)
    day = date.today().isoformat()
    jsonl = out_dir / f"{day}-plan.jsonl"
    md = out_dir / f"{day}-plan.md"
    header = {"tool": TOOL, "head_sha": slices[0].head_sha if slices else head_sha(repo), "slices": len(slices)}
    with jsonl.open("w") as fh:
        fh.write(json.dumps(header) + "\n")
        for s in slices:
            d = asdict(s)
            d["message"] = f"{s.ctype}({s.scope}): {s.subject}"
            fh.write(json.dumps(d) + "\n")
    md_lines = [
        f"# Commit slice plan — {day}",
        f"**HEAD:** `{header['head_sha'][:12]}` · **Slices:** {len(slices)}",
        "",
        "Apply: `just commit-slice-planning --apply N` (operator approves)",
        "",
    ]
    for s in slices:
        msg = f"{s.ctype}({s.scope}): {s.subject}"
        md_lines.extend([
            f"## Slice {s.id}", f"- **Message:** `{msg}`",
            f"- **Gate:** `{s.gate or '(none)'}`", f"- **Files:** {len(s.paths)}", "",
            "```bash", f"git add -- {' '.join(s.paths)}", f'git commit -m "{msg}"', "```", "",
        ])
    md.write_text("\n".join(md_lines) + "\n")
    return jsonl, md


def load_slices(plan_path: Path) -> tuple[str, list[Slice]]:
    lines = [ln for ln in plan_path.read_text().splitlines() if ln.strip()]
    plan_head = json.loads(lines[0])
    sha = plan_head.get("head_sha", "")
    fields = {f.name for f in Slice.__dataclass_fields__.values()}
    slices: list[Slice] = []
    for ln in lines[1:]:
        d = json.loads(ln)
        slices.append(Slice(**{k: d[k] for k in d if k in fields}))
    return sha, slices


def message_ok(msg: str) -> bool:
    return not any(m in msg for m in PLACEHOLDER_MARKERS)


def apply_slices(repo: Path, plan_sha: str, slices: list[Slice], which: str, dry_run: bool) -> int:
    current = head_sha(repo)
    if plan_sha and plan_sha != current:
        print(f"HEAD moved: plan={plan_sha[:8]} current={current[:8]}", file=sys.stderr)
        return 1
    todo = slices if which == "all" else [s for s in slices if s.id == int(which)]
    if not todo:
        print(f"No slice {which}", file=sys.stderr)
        return 1
    for s in todo:
        msg = f"{s.ctype}({s.scope}): {s.subject}"
        if not message_ok(msg):
            print(f"Refusing placeholder message: {msg}", file=sys.stderr)
            return 1
        if s.gate and not dry_run:
            subprocess.run(s.gate.split(), cwd=repo, check=False)
        print("$", "git add --", " ".join(s.paths))
        print("$", f'git commit -m "{msg}"')
        if dry_run:
            continue
        subprocess.run(["git", "-C", str(repo), "add", "--"] + s.paths, check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-m", msg], check=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, default=Path.cwd())
    ap.add_argument("--include-untracked", action="store_true")
    ap.add_argument("--status-only", action="store_true")
    ap.add_argument("--draft-messages-with-agent", action="store_true")
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--apply", metavar="N|all")
    ap.add_argument("--plan", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--llm", action="store_true", help=argparse.SUPPRESS)  # legacy
    args = ap.parse_args()

    repo = args.repo.resolve()
    use_agent = (args.draft_messages_with_agent or args.llm) and not args.no_llm and not llm_denied()
    print_llm_header(LlmClass.OPTIONAL if use_agent else LlmClass.NONE,
                     "draft-messages-with-agent" if use_agent else "")

    if args.apply:
        plan = args.plan or sorted(repo_state_dir(repo, TOOL).glob("*-plan.jsonl"))[-1]
        plan_sha, slices = load_slices(plan)
        return apply_slices(repo, plan_sha, slices, args.apply, args.dry_run)

    paths = changed_paths(repo, args.include_untracked)
    if not paths:
        print("Working tree clean.", file=sys.stderr)
        return 0
    if args.status_only:
        print(status_only(repo, paths))
        return 0

    sha = head_sha(repo)
    slices = build_slices(repo, paths, sha)
    if use_agent:
        draft_messages_with_agent(repo, slices)
    jsonl, md = write_plan(repo, slices)
    print(md.read_text())
    print(f"plan: {jsonl}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
