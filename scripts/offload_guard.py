#!/usr/bin/env python3
"""Offload / storage-repair safety — refuse whole-dir moves when git-tracked files exist.

Failure class (arc-agi DATA_LOSS_2026-08-07, session 554b1579):
  whole-dir rsync → symlink → repair treated "dir exists locally" as full duplicate
  → rm -rf SSD copy of untracked out/ while only 6 tracked files were restored.

Contract:
  1. If `git ls-files <dir>` is non-empty → refuse whole-dir offload/symlink.
  2. Repair prune is per-file only (path exists on both sides AND content equal).
  3. Prefer untracked-only artifact moves; keep tracked files local always.

Usage:
  uv run python3 scripts/offload_guard.py check <repo> <rel_or_abs_dir>
  uv run python3 scripts/offload_guard.py safe-to-whole-dir-offload <repo> <dir>  # exit 0/1
  from offload_guard import tracked_under, refuse_whole_dir_offload, files_content_equal
"""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path


def _git_ls_files(repo: Path, rel: str) -> list[str]:
    """List tracked files under rel (repo-relative). Empty if none / not a git repo."""
    repo = repo.resolve()
    rel = rel.strip().rstrip("/") or "."
    try:
        r = subprocess.run(
            ["git", "-C", str(repo), "ls-files", "-z", "--", rel],
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        raise RuntimeError(f"git ls-files failed: {e}") from e
    if r.returncode != 0:
        err = (r.stderr or b"").decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git ls-files exit {r.returncode}: {err}")
    raw = r.stdout.split(b"\0")
    return [p.decode("utf-8", errors="replace") for p in raw if p]


def tracked_under(repo: Path, path: Path) -> list[str]:
    """Tracked files under path. path may be abs or relative to repo."""
    repo = repo.resolve()
    path = path.expanduser()
    if not path.is_absolute():
        path = (repo / path).resolve()
    else:
        path = path.resolve()
    try:
        rel = path.relative_to(repo).as_posix()
    except ValueError as e:
        raise ValueError(f"path {path} is not under repo {repo}") from e
    return _git_ls_files(repo, rel)


def refuse_whole_dir_offload(repo: Path, path: Path) -> tuple[bool, str]:
    """Return (ok_to_whole_dir, reason). ok_to_whole_dir True only if zero tracked files."""
    tracked = tracked_under(repo, path)
    if tracked:
        sample = ", ".join(tracked[:5])
        more = f" (+{len(tracked) - 5} more)" if len(tracked) > 5 else ""
        return (
            False,
            f"REFUSE whole-dir offload: {len(tracked)} git-tracked file(s) under "
            f"{path} (e.g. {sample}{more}). Offload untracked artifacts only, "
            f"or use per-entry symlink of untracked paths.",
        )
    return True, f"OK whole-dir offload: no git-tracked files under {path}"


def file_sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def files_content_equal(a: Path, b: Path) -> bool:
    """True iff both exist as regular files and content hashes match.

    Directory-level presence is NEVER sufficient — that was the data-loss class.
    """
    if not a.is_file() or not b.is_file():
        return False
    if a.stat().st_size != b.stat().st_size:
        return False
    return file_sha256(a) == file_sha256(b)


def safe_to_delete_ssd_copy(local: Path, ssd: Path) -> tuple[bool, str]:
    """May delete ssd only when local is an identical regular file (per-file merge)."""
    if not ssd.exists():
        return False, f"ssd path missing: {ssd}"
    if ssd.is_dir():
        return (
            False,
            f"REFUSE dir-level delete of {ssd}: only delete individual files after "
            f"per-file content equality with local counterparts",
        )
    if not local.is_file():
        return False, f"local is not a file (cannot prove full duplicate): {local}"
    if files_content_equal(local, ssd):
        return True, f"OK delete ssd copy (content-equal): {ssd}"
    return False, f"REFUSE: content differs or unreadable: {local} vs {ssd}"


def cmd_check(repo: Path, path: Path) -> int:
    ok, reason = refuse_whole_dir_offload(repo, path)
    print(reason)
    return 0 if ok else 2


def cmd_safe_to_delete(local: Path, ssd: Path) -> int:
    ok, reason = safe_to_delete_ssd_copy(local, ssd)
    print(reason)
    return 0 if ok else 2


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_check = sub.add_parser("check", help="refuse whole-dir offload if git-tracked files present")
    p_check.add_argument("repo", type=Path)
    p_check.add_argument("path", type=Path, help="dir under repo (rel or abs)")

    p_del = sub.add_parser(
        "safe-to-delete-ssd",
        help="per-file only: OK to delete ssd copy iff content-equal to local file",
    )
    p_del.add_argument("local", type=Path)
    p_del.add_argument("ssd", type=Path)

    args = ap.parse_args(argv)
    if args.cmd == "check":
        return cmd_check(args.repo, args.path)
    if args.cmd == "safe-to-delete-ssd":
        return cmd_safe_to_delete(args.local, args.ssd)
    return 2


if __name__ == "__main__":
    sys.exit(main())
