#!/usr/bin/env python3
"""DEPRECATED → session_automation_telemetry.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tool_contract import deprecation

deprecation("session_classify.py", "session-automation-telemetry")
from session_automation_telemetry import main

if __name__ == "__main__":
    raise SystemExit(main())
