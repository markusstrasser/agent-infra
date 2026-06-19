#!/usr/bin/env python3
"""DEPRECATED → sensor_integration_ranking.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tool_contract import deprecation

deprecation("integrate_rank.py", "sensor-integration-ranking")
if __name__ == "__main__":
    if "--no-llm" not in sys.argv:
        sys.argv.append("--no-llm")
    from sensor_integration_ranking import main
    raise SystemExit(main())
