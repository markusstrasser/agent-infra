#!/usr/bin/env python3
"""Codex dispatch wrapper — lifecycle management for parallel codex exec.

Encodes correct flags, handles parallel launch, output polling, and collection.
Replaces manual sleep-polling observed in dispatch-research sessions.

Usage:
    codex_dispatch.py dispatch prompts.json --output-dir docs/audit/
    codex_dispatch.py dispatch --prompt "Review auth flow" --output-dir out/
    codex_dispatch.py status --pids 1234,5678
    codex_dispatch.py collect --output-dir docs/audit/
    codex_dispatch.py summary --output-dir docs/audit/
    codex_dispatch.py wait --pids 1234,5678 --timeout 600
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_MODEL = "o3"
MAX_PARALLEL_MCP = 4


def dispatch(
    prompts: list[dict],
    output_dir: Path,
    model: str = DEFAULT_MODEL,
    project: str | None = None,
    max_parallel: int = MAX_PARALLEL_MCP,
) -> list[dict]:
    """Launch parallel codex exec processes.

    Each prompt dict: {"name": str, "prompt": str, "model"?: str}
    Returns: [{"name", "pid", "output_file", "started"}]
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Clean env to avoid nested session detection
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_SESSION_ID")}

    results: list[dict] = []
    active: list[dict] = []

    for item in prompts:
        name = item["name"]
        prompt = item["prompt"]
        m = item.get("model", model)
        output_file = output_dir / f"{name}.md"

        # Wait if at max_parallel
        while len(active) >= max_parallel:
            active = [p for p in active if p["process"].poll() is None]
            if len(active) >= max_parallel:
                time.sleep(2)

        cmd = [
            "codex", "exec",
            "--full-auto",
            "-m", m,
            "-o", str(output_file),
            prompt,
        ]
        if project:
            cmd.extend(["--cwd", project])

        proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        entry = {
            "name": name,
            "pid": proc.pid,
            "output_file": str(output_file),
            "started": time.time(),
        }
        active.append({"process": proc, **entry})
        results.append(entry)

    return results


def check_status(pids: list[int]) -> list[dict]:
    """Check which PIDs are still running."""
    statuses = []
    for pid in pids:
        try:
            os.kill(pid, 0)
            statuses.append({"pid": pid, "running": True})
        except ProcessLookupError:
            statuses.append({"pid": pid, "running": False})
        except PermissionError:
            statuses.append({"pid": pid, "running": True})
    return statuses


def wait_all(pids: list[int], timeout: float = 600) -> list[dict]:
    """Wait for all PIDs to finish, with timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        statuses = check_status(pids)
        if not any(s["running"] for s in statuses):
            return statuses
        time.sleep(5)
    return check_status(pids)


def collect(output_dir: Path) -> list[dict]:
    """Read all completed output files."""
    results = []
    if not output_dir.exists():
        return results
    for f in sorted(output_dir.iterdir()):
        if not f.is_file() or f.name.startswith("."):
            continue
        content = f.read_text().strip()
        results.append({
            "name": f.stem,
            "file": str(f),
            "size": len(content),
            "content": content,
        })
    return results


def summary(output_dir: Path) -> str:
    """One-line summary per output file."""
    lines = []
    for item in collect(output_dir):
        first_line = ""
        for line in item["content"].splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                first_line = stripped[:100]
                break
        lines.append(f"  {item['name']}: {item['size']} chars — {first_line}")
    return "\n".join(lines) if lines else "(no outputs found)"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # dispatch
    d = sub.add_parser("dispatch", help="Launch parallel codex exec tasks")
    d.add_argument("prompts_file", nargs="?", type=Path, help="JSON file: [{name, prompt, model?}]")
    d.add_argument("--prompt", help="Single prompt (use with --name)")
    d.add_argument("--name", default="task", help="Name for single prompt")
    d.add_argument("--output-dir", type=Path, required=True)
    d.add_argument("-m", "--model", default=DEFAULT_MODEL)
    d.add_argument("--project", help="Working directory for codex")
    d.add_argument("--max-parallel", type=int, default=MAX_PARALLEL_MCP)
    d.add_argument("--wait", action="store_true", help="Wait for all to finish, then print summary")
    d.add_argument("--timeout", type=float, default=600, help="Wait timeout in seconds")

    # status
    s = sub.add_parser("status", help="Check if PIDs are still running")
    s.add_argument("--pids", required=True, help="Comma-separated PIDs")

    # collect
    c = sub.add_parser("collect", help="Read completed output files as JSON")
    c.add_argument("--output-dir", type=Path, required=True)

    # summary
    sm = sub.add_parser("summary", help="One-line summary per output")
    sm.add_argument("--output-dir", type=Path, required=True)

    # wait
    w = sub.add_parser("wait", help="Wait for PIDs to finish")
    w.add_argument("--pids", required=True, help="Comma-separated PIDs")
    w.add_argument("--timeout", type=float, default=600)

    args = parser.parse_args()

    if args.command == "dispatch":
        if args.prompts_file:
            prompts = json.loads(args.prompts_file.read_text())
        elif args.prompt:
            prompts = [{"name": args.name, "prompt": args.prompt}]
        else:
            parser.error("Provide prompts_file or --prompt")
            return 1
        results = dispatch(
            prompts, args.output_dir, model=args.model,
            project=args.project, max_parallel=args.max_parallel,
        )
        if args.wait:
            pids = [r["pid"] for r in results]
            wait_all(pids, timeout=args.timeout)
            print(summary(args.output_dir))
        else:
            print(json.dumps(results, indent=2))
        return 0

    if args.command == "status":
        pids = [int(p) for p in args.pids.split(",")]
        print(json.dumps(check_status(pids), indent=2))
        return 0

    if args.command == "collect":
        results = collect(args.output_dir)
        print(json.dumps(results, indent=2))
        return 0

    if args.command == "summary":
        print(summary(args.output_dir))
        return 0

    if args.command == "wait":
        pids = [int(p) for p in args.pids.split(",")]
        statuses = wait_all(pids, timeout=args.timeout)
        print(json.dumps(statuses, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
