"""Token aggregation: cumulative-vs-delta combination + cache-field mapping.

Regression guard for two bugs found 2026-06-29:
  A) codex emits `total_token_usage` (a running cumulative) on every token_count
     event; the old code summed them -> ~600x inflation. Must MAX-combine.
  B) Anthropic usage uses cache_read_input_tokens / cache_creation_input_tokens;
     the old field map matched neither, silently dropping all Claude cache tokens.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from agentlogs import index as ix


def _ev(payload):
    return SimpleNamespace(payload=payload)


def test_codex_cumulative_snapshots_are_max_not_summed():
    # Three codex token_count events, each restating the running session total.
    def snap(inp, cached, out):
        return {"info": {
            "total_token_usage": {"input_tokens": inp, "cached_input_tokens": cached,
                                  "output_tokens": out, "total_tokens": inp + out},
            "last_token_usage": {"input_tokens": inp, "cached_input_tokens": cached,
                                 "output_tokens": out, "total_tokens": inp + out},
        }}
    events = [_ev(snap(10_000, 8_000, 50)),
              _ev(snap(25_000, 20_000, 120)),
              _ev(snap(40_000, 33_000, 200))]
    t = ix.aggregate_tokens(events)
    # MAX of the final snapshot — NOT the sum (which would be 75_000 input).
    assert t["input_tokens"] == 40_000
    assert t["cached_tokens"] == 33_000
    assert t["output_tokens"] == 200
    assert t["total_tokens"] == 40_200


def test_claude_usage_deltas_summed_with_cache_fields():
    # Two Claude assistant messages (per-call deltas) -> summed; cache fields mapped.
    def usage(inp, cw, cr, out):
        return {"usage": {"input_tokens": inp, "cache_creation_input_tokens": cw,
                          "cache_read_input_tokens": cr, "output_tokens": out}}
    events = [_ev(usage(100, 5_000, 16_000, 1_400)),
              _ev(usage(200, 1_000, 30_000, 900))]
    t = ix.aggregate_tokens(events)
    assert t["input_tokens"] == 300            # summed (delta semantics)
    assert t["cached_tokens"] == 46_000        # cache_read -> cached_tokens
    assert t["cache_write_tokens"] == 6_000    # cache_creation -> cache_write_tokens
    assert t["output_tokens"] == 2_300


def test_no_token_events_returns_empty():
    assert ix.aggregate_tokens([_ev({"foo": "bar"}), _ev(None)]) == {}


def test_cache_write_column_exists_after_migration(tmp_path):
    import agentlogs
    db = agentlogs.connect(tmp_path / "t.db")
    cols = {r[1] for r in db.execute("PRAGMA table_info(runs)")}
    assert "cache_write_tokens" in cols
    db.close()
