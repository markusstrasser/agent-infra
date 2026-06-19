#!/usr/bin/env python3
"""Run a verification gate recipe and capture pass/fail artifact.

llm: none

Usage:
  verification_gate_runner.py --repo ~/Projects/genomics --gate canary
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from tool_contract import GATE_GREEN, GATE_RED, GATE_UNKNOWN, LlmClass, detect_default_gate, print_llm_header, repo_state_dir

TOOL = "verification-gate-runner"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--gate", help="just recipe (default: autodetect)")
    args = ap.parse_args()

    print_llm_header(LlmClass.NONE)
    repo = args.repo.resolve()
    gate = args.gate or detect_default_gate(repo)
    status = GATE_UNKNOWN
    tail = ""
    if (repo / "justfile").is_file():
        try:
            r = subprocess.run(["just", gate], cwd=repo, capture_output=True, text=True, timeout=600)
            tail = (r.stdout + r.stderr)[-2000:]
            status = GATE_GREEN if r.returncode == 0 else GATE_RED
        except subprocess.TimeoutExpired:
            tail = "timeout 600s"
        except FileNotFoundError:
            tail = "just not found"
    else:
        tail = "no justfile"

    payload = {
        "tool": TOOL,
        "llm": LlmClass.NONE.value,
        "repo": str(repo),
        "gate": gate,
        "gate_status": status,
        "ts": datetime.now(timezone.utc).isoformat(),
        "tail": tail,
    }
    out_dir = repo_state_dir(repo, TOOL)
    out_dir.mkdir(parents=True, exist_ok=True)
    day = date.today().isoformat()
    json_path = out_dir / f"{day}-{gate}.json"
    json_path.write_text(json.dumps(payload, indent=2) + "\n")
    md_path = out_dir / f"{day}-{gate}.md"
    md_path.write_text(
        f"# Verification gate — {day}\n\n**Gate:** `{gate}` · **Status:** {status}\n\n```\n{tail}\n```\n"
    )
    print(md_path)
    return 0 if status == GATE_GREEN else (3 if status == GATE_UNKNOWN else 1)


if __name__ == "__main__":
    raise SystemExit(main())
