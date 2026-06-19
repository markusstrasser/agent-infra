#!/usr/bin/env python3
"""DEPRECATED → audit_findings_consolidation.py --kind debug"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tool_contract import deprecation

deprecation("debug_triage.py", "audit-findings-consolidation")
if __name__ == "__main__":
    if "--kind" not in sys.argv:
        sys.argv.extend(["--kind", "debug"])
    from audit_findings_consolidation import main
    raise SystemExit(main())
