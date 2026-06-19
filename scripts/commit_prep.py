#!/usr/bin/env python3
"""DEPRECATED → commit_slice_planning.py --status-only"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tool_contract import deprecation

deprecation("commit_prep.py", "commit-slice-planning --status-only")
if __name__ == "__main__":
    sys.argv.extend(["--status-only", "--include-untracked"])
    from commit_slice_planning import main
    raise SystemExit(main())
