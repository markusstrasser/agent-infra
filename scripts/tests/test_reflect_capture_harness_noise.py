"""parse_events must drop harness-injected lines (isCompactSummary/isMeta).

Regression: 2026-07-04 reflect quarantine — every pending MINT's evidence was
five copies of the compaction-summary preamble because #f re-quoted inside
summaries was mined as a fresh f_tag signal.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reflect_capture import extract_corrections, parse_events


def _line(text, **extra):
    d = {"type": "user", "message": {"role": "user", "content": text}}
    d.update(extra)
    return json.dumps(d)


def test_compact_summary_and_meta_dropped():
    lines = [
        _line("This session is being continued ... old flag #f", isCompactSummary=True),
        _line("skill expansion #f", isMeta=True),
        _line("real correction #f fix the parser"),
    ]
    events = parse_events(lines)
    assert len(events) == 1
    corrections = extract_corrections(events)
    assert len(corrections) == 1
    assert "real correction" in corrections[0]["trigger"]
