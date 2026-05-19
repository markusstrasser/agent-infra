#!/usr/bin/env python3
"""Write a stub output file BEFORE dispatching a subagent.

Solves the friction pattern where subagent output JSON is written at the
END of the run, leaving the parent with no live progress visibility.
Convention-based, not hook-based — the dispatcher calls this before
`Agent(...)`, then includes the stub path in the subagent's prompt.

Usage (CLI):
    # Default: empty list under a "verdicts" key
    python3 dispatch-with-stub.py /tmp/batch1-verdicts.json

    # Custom key
    python3 dispatch-with-stub.py /tmp/batch1-verdicts.json --key gap_verdicts

    # Inline JSON stub (overrides key)
    python3 dispatch-with-stub.py /tmp/batch1-verdicts.json --stub '{"verdicts": [], "tool_observations": {}}'

The stub is overwrite-only if the file is empty/missing; if there's
existing content, the call refuses (exit 1) to prevent clobbering a
subagent's in-progress writes.

Pattern in the dispatching agent:
    Bash:    uv run python3 dispatch-with-stub.py /tmp/batch1.json
    Agent:   "...write your output to /tmp/batch1.json (stub already present)..."
    Bash:    stat /tmp/batch1.json   # parent can check progress anytime

The point: the stub exists from t=0, so the parent can `stat` or `cat`
the file at any time during the subagent's run and see at minimum the
schema shape. The subagent appends or overwrites with real data as it
goes (per the agent's own write-first instruction).

Stdlib-only.
"""
import argparse
import json
import pathlib
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=pathlib.Path, help="Output file path the subagent will write to")
    parser.add_argument("--key", default="verdicts", help="Top-level key for the stub list (default: 'verdicts')")
    parser.add_argument("--stub", default=None, help="Inline JSON stub (overrides --key)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing non-empty file")
    args = parser.parse_args()

    if args.path.exists() and args.path.stat().st_size > 2 and not args.force:
        existing = args.path.read_text().strip()
        if existing and existing not in ("{}", "[]"):
            print(f"REFUSE: {args.path} already contains data ({len(existing)} bytes); use --force to overwrite", file=sys.stderr)
            sys.exit(1)

    if args.stub:
        try:
            stub = json.loads(args.stub)
        except json.JSONDecodeError as e:
            print(f"ERROR: --stub is not valid JSON: {e}", file=sys.stderr)
            sys.exit(2)
    else:
        stub = {args.key: []}

    args.path.parent.mkdir(parents=True, exist_ok=True)
    args.path.write_text(json.dumps(stub, indent=2) + "\n")
    print(f"OK   wrote stub to {args.path} ({len(json.dumps(stub))} bytes)")


if __name__ == "__main__":
    main()
