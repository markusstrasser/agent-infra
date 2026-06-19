#!/usr/bin/env python3
"""DEPRECATED → baseline_since_last_green.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tool_contract import deprecation

deprecation("audit_delta.py", "baseline-since-last-green")
from baseline_since_last_green import main

if __name__ == "__main__":
    # map legacy flags
    if "--suggest-only" not in sys.argv:
        pass
    raise SystemExit(main())
