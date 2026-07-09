"""Tests for improvement_log_accretion.py (L1 read-only slice)."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import improvement_log_accretion as ila  # noqa: E402


SAMPLE = """\
### [2026-01-01] HOOK: pretool bash loop guard edge case
- **Status:** [ ] proposed

### [2026-01-02] HOOK: pretool bash loop guard false positive
- **Status:** [ ] proposed

### [2025-01-01] INFRA: old open item
- **Status:** [ ] proposed

### [2026-06-01] TOKEN WASTE: something behavioral
- **Status:** [obs]
"""


def test_duplicate_cluster_detection():
    items = ila._parse_open_items(SAMPLE)
    clusters = ila.duplicate_clusters(items, threshold=0.4)
    assert len(clusters) == 1
    assert len(clusters[0]) == 2


def test_stale_open_items():
    items = ila._parse_open_items(SAMPLE)
    stale = ila.stale_items(items, today=date(2026, 6, 30), days=30)
    titles = {it.title for it in stale}
    assert any("old open item" in t for t in titles)
