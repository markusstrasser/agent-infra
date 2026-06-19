#!/usr/bin/env python3
"""Refresh agent-facing codebase maps when mapped source paths are staged or touched."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from codebase_map_config import config_for_repo  # noqa: E402
from refresh_all_codebase_maps import refresh_repo  # noqa: E402


def _git(repo: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo), *args],
            text=True,
            stderr=subprocess.PIPE,
        ).strip()
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or str(exc)).strip().splitlines()[-1] if exc.stderr or exc else str(exc)
        raise RuntimeError(f"git -C {repo.name} {' '.join(args)}: {detail}") from exc


def _repo_root(start: Path) -> Path | None:
    try:
        return Path(_git(start, "rev-parse", "--show-toplevel")).resolve()
    except (RuntimeError, OSError):
        return None


def _staged_paths(repo: Path) -> list[str]:
    try:
        out = _git(repo, "diff", "--cached", "--name-only", "--diff-filter=ACMRD")
    except RuntimeError as exc:
        print(f"[codebase-map] skip staged read: {exc}", file=sys.stderr)
        return []
    return [line for line in out.splitlines() if line]


def _touches_mapped(paths: list[str], source_dirs: list[str]) -> bool:
    prefixes = tuple(f"{d}/" for d in source_dirs)
    for path in paths:
        if path in source_dirs:
            return True
        if path.startswith(prefixes):
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--touched",
        type=Path,
        help="Refresh if this path is under mapped source dirs (PostToolUse)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        help="Repo being committed (required when uv --directory changes cwd)",
    )
    args = parser.parse_args()

    if args.touched:
        touched = args.touched.resolve()
        repo_root = _repo_root(touched.parent)
        if not repo_root:
            return 0
        try:
            rel_path = str(touched.relative_to(repo_root))
        except ValueError:
            return 0
        trigger_paths = [rel_path]
    else:
        repo_root = (
            args.repo_root.resolve()
            if args.repo_root
            else _repo_root(Path.cwd())
        )
        if not repo_root:
            return 0
        trigger_paths = _staged_paths(repo_root)

    repo_cfg = config_for_repo(repo_root)
    if not repo_cfg or not trigger_paths:
        return 0
    if not _touches_mapped(trigger_paths, list(repo_cfg.source_dirs)):
        return 0

    try:
        refresh_repo(repo_cfg, quiet=True)
    except subprocess.CalledProcessError as exc:
        print(f"[codebase-map] refresh failed: {exc}", file=sys.stderr)
        return 0

    print(f"[codebase-map] refreshed agent maps for {repo_root.name}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
