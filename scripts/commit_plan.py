#!/usr/bin/env python3
"""DEPRECATED → commit_slice_planning.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tool_contract import deprecation

deprecation("commit_plan.py", "commit-slice-planning")
if __name__ == "__main__":
    for i, a in enumerate(sys.argv):
        if a == "--llm":
            sys.argv[i] = "--draft-messages-with-agent"
    from commit_slice_planning import main
    raise SystemExit(main())
