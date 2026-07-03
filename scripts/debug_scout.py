#!/usr/bin/env python3
"""Parallel debug scouts — cursor ask-mode / codex read-only → docs/audit/*.md
(orchestrator model triages later).

Usage:
  debug_scout.py /path/to/repo
  debug_scout.py /path/to/repo --scope scripts/pipeline/
  debug_scout.py /path/to/repo --scope recent --max-scouts 4
  debug_scout.py /path/to/repo --backend codex --effort low
  debug_scout.py /path/to/repo --backend cursor,codex   # round-robin (lens diversity)
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
from scout_backends import parse_backend_spec, scout_ask

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
            [
                "git",
                "-C",
                str(repo),
                "log",
                f"-{n_commits}",
                "--name-only",
                "--pretty=format:",
            ],
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
        return [
            (
                "recent",
                f"Recent work in `{repo.name}` — inspect git log and high-risk modules.",
            )
        ]

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
    backend: str,
    prompt: str,
    out_path: Path,
    *,
    model: str,
    effort: str,
    timeout: int,
    dry_run: bool,
) -> tuple[str, bool, str, dict]:
    if dry_run:
        return (
            scout_id,
            True,
            f"dry-run scout {scout_id} [{backend}] (no files written)",
            {},
        )

    reply = scout_ask(
        backend,
        repo,
        prompt,
        timeout=timeout,
        model=model,
        effort=effort,
        dry_run=False,
    )
    usage = {
        "backend": backend,
        "in_tok": reply.in_tok,
        "out_tok": reply.out_tok,
        "reason_tok": reply.reason_tok,
    }
    if reply.timed_out:
        out_path.write_text(
            f"---\nscout_id: {scout_id}\nbackend: {backend}\nstatus: timeout\n---\n"
        )
        return scout_id, False, f"timeout {timeout}s", usage
    header = (
        f"---\nscout_id: {scout_id}\nrepo: {repo}\ndate: {date.today().isoformat()}\n"
        f"backend: {backend}\nok: {reply.ok}\nmode: audit-only\n"
        f"tokens: in={reply.in_tok} out={reply.out_tok} reason={reply.reason_tok}\n---\n\n"
    )
    out_path.write_text(header + reply.body + "\n")
    ok = reply.ok and valid_scout_body(reply.body)
    return scout_id, ok, str(out_path), usage


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("repo", type=Path, help="Target project root")
    parser.add_argument(
        "--scope", default="recent", help="recent | path | free-text focus"
    )
    parser.add_argument(
        "--prompt", default="", help="Extra focus appended to all scouts"
    )
    parser.add_argument("--max-scouts", type=int, default=DEFAULT_MAX_SCOUTS)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument(
        "--backend",
        default="cursor",
        help="cursor | codex | comma-list (round-robin across scouts, e.g. cursor,codex)",
    )
    parser.add_argument("--model", default="", help="override backend default model")
    parser.add_argument(
        "--effort", default="", help="codex reasoning effort (default: medium)"
    )
    parser.add_argument("--timeout", type=int, default=600, help="seconds per scout")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        backends = parse_backend_spec(args.backend)
    except ValueError as e:
        parser.error(str(e))

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

    scopes = build_scopes(repo, args.scope, args.max_scouts)
    if not scopes:
        return 1
    print(
        f"# debug scout run={run_stamp} repo={repo.name} scopes={len(scopes)}",
        file=sys.stderr,
    )

    if args.dry_run:
        for scout_id, scope_block in scopes:
            out_path = audit_dir / f"{day}-debug-{run_stamp}-{scout_id}.md"
            print(f"  would write {out_path}", file=sys.stderr)
            print(f"  scope[{scout_id}]: {scope_block[:200]}…", file=sys.stderr)
        print(
            f"\n# dry-run: {len(scopes)} scout(s), no files written "
            f"(re-run without --dry-run to dispatch)",
            file=sys.stderr,
        )
        return 0

    audit_dir.mkdir(parents=True, exist_ok=True)
    results: list[tuple[str, bool, str, dict]] = []

    # round-robin the backend list across scouts (mixed = lens diversity)
    jobs = [
        (sid, backends[i % len(backends)], block)
        for i, (sid, block) in enumerate(scopes)
    ]

    def job(item: tuple[str, str, str]) -> tuple[str, bool, str, dict]:
        scout_id, backend, scope_block = item
        prompt = render_prompt(repo.name, scout_id, scope_block, args.prompt)
        out_path = audit_dir / f"{day}-debug-{run_stamp}-{scout_id}.md"
        return run_scout(
            repo,
            scout_id,
            backend,
            prompt,
            out_path,
            model=args.model,
            effort=args.effort,
            timeout=args.timeout,
            dry_run=False,
        )

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = [pool.submit(job, s) for s in jobs]
        for fut in as_completed(futs):
            try:
                results.append(fut.result())
            except Exception as exc:
                results.append(("?", False, f"job failed: {exc}", {}))

    ok_n = sum(1 for _, ok, _, _ in results if ok)
    tot_out = sum(u.get("out_tok", 0) for *_, u in results)
    tot_reason = sum(u.get("reason_tok", 0) for *_, u in results)
    manifest = audit_dir / f"{day}-debug-{run_stamp}-manifest.txt"
    manifest.write_text(
        f"run_id: {run_stamp}\nrepo: {repo}\n"
        f"tokens: out={tot_out} reason={tot_reason}\n"
        + "\n".join(f"{sid}\t{ok}\t{msg}" for sid, ok, msg, _ in sorted(results))
        + "\n"
    )
    jsonl = audit_dir / f"{day}-debug-{run_stamp}-manifest.jsonl"
    scout_rows = [
        ScoutResult(sid, ok, msg if ok else "", kind="debug", message=msg, meta=usage)
        for sid, ok, msg, usage in results
    ]
    write_manifest(jsonl, run_id=run_stamp, repo=repo, kind="debug", results=scout_rows)
    print(
        f"\n# done: {ok_n}/{len(results)} scouts · tokens out={tot_out} "
        f"reason={tot_reason} → {manifest}",
        file=sys.stderr,
    )
    print(
        f"Next: just audit-findings-consolidation {audit_dir} --date {day}",
        file=sys.stderr,
    )
    return 0 if ok_n == len(results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
