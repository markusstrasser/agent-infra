#!/usr/bin/env python3
"""DEPRECATED → audit_findings_consolidation.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tool_contract import deprecation

deprecation("scout_triage.py", "audit-findings-consolidation")
from audit_findings_consolidation import main

if __name__ == "__main__":
    raise SystemExit(main())
