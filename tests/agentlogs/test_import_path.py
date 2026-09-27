"""agentlogs must import from src/, never from a site-packages copy.

A wheel copy in site-packages shadows the editable install's src/ path and
serves stale code: the weekly archive ran two-week-old code in August, and
its import guard refused every run after a reinstall recreated the copy.
"""
from pathlib import Path

import agentlogs


def test_agentlogs_imports_from_src_tree():
    pkg = Path(agentlogs.__file__).resolve().parent
    assert "site-packages" not in pkg.parts, f"stale shadow copy: {pkg}"
    assert pkg.parent.name == "src", f"agentlogs not served from src/: {pkg}"
