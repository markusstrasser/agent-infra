#!/usr/bin/env python3
"""Refresh agent-facing codebase maps for one or all configured repos."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from codebase_map_config import RepoMapConfig, assert_maps_gitignored, config_for_repo, load_repo_configs  # noqa: E402


def refresh_repo(cfg: RepoMapConfig, *, quiet: bool = False) -> None:
    assert_maps_gitignored(cfg)
    py = sys.executable
    summary = ROOT / "scripts" / "repo-summary.py"
    cmap = ROOT / "scripts" / "codebase-map.py"

    for src in cfg.source_dirs:
        src_path = cfg.root / src
        if not src_path.exists():
            continue
        cmd = [py, str(summary), str(src_path), "--refresh", "--no-llm"]
        if cfg.compact:
            cmd.append("--compact")
        subprocess.run(
            cmd,
            cwd=ROOT,
            check=True,
            stdout=subprocess.DEVNULL if quiet else None,
        )

    subprocess.run(
        [py, str(cmap), str(cfg.root), "--source-dirs", ",".join(cfg.source_dirs)],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL if quiet else None,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", help="Refresh one repo by name (default: all)")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    configs = load_repo_configs()
    targets = (
        [configs[args.repo]]
        if args.repo
        else [configs[name] for name in sorted(configs)]
    )

    fail = 0
    for cfg in targets:
        if not cfg.root.exists():
            print(f"skip {cfg.name}: missing {cfg.root}", file=sys.stderr)
            continue
        if not args.quiet:
            print(f"▸ {cfg.name}", file=sys.stderr)
        try:
            refresh_repo(cfg, quiet=args.quiet)
        except subprocess.CalledProcessError as exc:
            print(f"  ✗ {cfg.name}: {exc}", file=sys.stderr)
            fail = 1
    return fail


if __name__ == "__main__":
    raise SystemExit(main())
