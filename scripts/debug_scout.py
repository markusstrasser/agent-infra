#!/usr/bin/env python3
"""Parallel debug scouts — cursor ask-mode → docs/audit/*.md (orchestrator model triages later).

Usage:
  debug_scout.py /path/to/repo
  debug_scout.py /path/to/repo --scope scripts/pipeline/
  debug_scout.py /path/to/repo --scope recent --max-scouts 4
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path

from fan_out_lib import ScoutResult, write_manifest

AGENT = Path.home() / ".local/bin/agent"
PROMPT_PATH = Path(__file__).parent / "debug_scout_prompt.md"
DEFAULT_MAX_SCOUTS = 6
DEFAULT_WORKERS = 3
SCOPE_SKIP = {".git", "node_modules", "__pycache__", ".venv", "artifacts", "data"}


def load_prompt_template() -> str:
    return PROMPT_PATH.read_text()


def slug(s: str, max_len: int = 32) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower()).strip("-")
    return (s or "scope")[:max_len]


def git_recent_files(repo: Path, n_commits: int = 10) -> list[Path]:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(repo), "log", f"-{n_commits}", "--name-only", "--pretty=format:"],
            text=True,
        )
    except subprocess.CalledProcessError:
        return []
    files: list[Path] = []
    seen: set[str] = set()
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        if any(part in SCOPE_SKIP for part in Path(line).parts):
            continue
        p = repo / line
        if p.is_file() and line not in seen:
            seen.add(line)
            files.append(p)
    return files


def group_by_top_dir(files: list[Path], repo: Path) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = {}
    for f in files:
        rel = f.relative_to(repo)
        key = rel.parts[0] if len(rel.parts) > 1 else "root"
        groups.setdefault(key, []).append(f)
    return dict(sorted(groups.items()))


def build_scopes(repo: Path, scope: str, max_scouts: int) -> list[tuple[str, str]]:
    if scope != "recent":
        p = (repo / scope).resolve()
        try:
            p.relative_to(repo.resolve())
        except ValueError:
            print(f"Scope outside repo: {scope}", file=sys.stderr)
            return []
        if p.exists():
            label = scope.rstrip("/")
            block = f"Directory or path: `{label}` under `{repo.name}`."
            return [(slug(label), block)]
        return [(slug(scope), f"Focus: {scope}")]

    files = git_recent_files(repo)
    if not files:
        return [("recent", f"Recent work in `{repo.name}` — inspect git log and high-risk modules.")]

    groups = group_by_top_dir(files, repo)
    scopes: list[tuple[str, str]] = []
    for mod, mod_files in list(groups.items())[:max_scouts]:
        rels = [str(f.relative_to(repo)) for f in mod_files[:40]]
        listing = "\n".join(f"- `{r}`" for r in rels)
        extra = f"\n- … +{len(mod_files) - 40} more" if len(mod_files) > 40 else ""
        block = (
            f"Recent changes in module `{mod}` ({len(mod_files)} files):\n{listing}{extra}\n\n"
            "Adversarially verify correctness and conceptual soundness in this slice."
        )
        scopes.append((slug(mod), block))
    return scopes[:max_scouts]


def render_prompt(project: str, scout_id: str, scope_block: str, extra: str) -> str:
    tpl = load_prompt_template()
    return (
        tpl.replace("{project}", project)
        .replace("{scout_id}", scout_id)
        .replace("{scope_block}", scope_block)
        .replace("{extra_prompt}", extra or "(none)")
    )


def valid_scout_body(body: str) -> bool:
    if "## NO_FINDINGS" in body:
        return True
    return bool(re.search(r"^## FINDING ", body, re.MULTILINE))


def run_scout(
    repo: Path,
    scout_id: str,
    prompt: str,
    out_path: Path,
    dry_run: bool,
) -> tuple[str, bool, str]:
    if dry_run:
        out_path.write_text(f"# DRY RUN scout {scout_id}\n\n{prompt[:500]}…\n")
        return scout_id, True, f"dry-run → {out_path}"

    if not AGENT.is_file():
        return scout_id, False, "agent CLI not found (~/.local/bin/agent)"

    cmd = [
        str(AGENT), "-p", "--trust", "--mode", "ask", "--model", "composer-2.5",
        "--workspace", str(repo), "--output-format", "text", prompt,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired as e:
        partial = (e.stdout or "") + (e.stderr or "")
        out_path.write_text(f"---\nscout_id: {scout_id}\nstatus: timeout\n---\n\n{partial}\n")
        return scout_id, False, "timeout 600s"

    body = result.stdout.strip() or result.stderr.strip() or "(empty scout output)"
    header = (
        f"---\nscout_id: {scout_id}\nrepo: {repo}\ndate: {date.today().isoformat()}\n"
        f"exit_code: {result.returncode}\nmode: ask\n---\n\n"
    )
    out_path.write_text(header + body + "\n")
    ok = result.returncode == 0 and valid_scout_body(body)
    return scout_id, ok, str(out_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("repo", type=Path, help="Target project root")
    parser.add_argument("--scope", default="recent", help="recent | path | free-text focus")
    parser.add_argument("--prompt", default="", help="Extra focus appended to all scouts")
    parser.add_argument("--max-scouts", type=int, default=DEFAULT_MAX_SCOUTS)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.workers < 1:
        print("--workers must be >= 1", file=sys.stderr)
        return 1
    if args.max_scouts < 1:
        print("--max-scouts must be >= 1", file=sys.stderr)
        return 1

    repo = args.repo.resolve()
    if not repo.is_dir():
        print(f"Not a directory: {repo}", file=sys.stderr)
        return 1

    run_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    day = date.today().isoformat()
    audit_dir = repo / "docs" / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)

    scopes = build_scopes(repo, args.scope, args.max_scouts)
    if not scopes:
        return 1
    print(f"# debug scout run={run_stamp} repo={repo.name} scopes={len(scopes)}", file=sys.stderr)

    results: list[tuple[str, bool, str]] = []

    def job(item: tuple[str, str]) -> tuple[str, bool, str]:
        scout_id, scope_block = item
        prompt = render_prompt(repo.name, scout_id, scope_block, args.prompt)
        out_path = audit_dir / f"{day}-debug-{run_stamp}-{scout_id}.md"
        return run_scout(repo, scout_id, prompt, out_path, args.dry_run)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = [pool.submit(job, s) for s in scopes]
        for fut in as_completed(futs):
            try:
                results.append(fut.result())
            except Exception as exc:
                results.append(("?", False, f"job failed: {exc}"))

    ok_n = sum(1 for _, ok, _ in results if ok)
    manifest = audit_dir / f"{day}-debug-{run_stamp}-manifest.txt"
    manifest.write_text(
        f"run_id: {run_stamp}\nrepo: {repo}\n"
        + "\n".join(f"{sid}\t{ok}\t{msg}" for sid, ok, msg in sorted(results))
        + "\n"
    )
    jsonl = audit_dir / f"{day}-debug-{run_stamp}-manifest.jsonl"
    scout_rows = [
        ScoutResult(sid, ok, msg if ok else "", kind="debug", message=msg)
        for sid, ok, msg in results
    ]
    write_manifest(jsonl, run_id=run_stamp, repo=repo, kind="debug", results=scout_rows)
    print(f"\n# done: {ok_n}/{len(results)} scouts → {manifest}", file=sys.stderr)
    print(f"Next: just audit-findings-consolidation {audit_dir} --date {day}", file=sys.stderr)
    return 0 if ok_n == len(results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
