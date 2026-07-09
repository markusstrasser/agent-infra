#!/usr/bin/env python3
"""Tests for harness_cost_meter — observe rollup + probe dry-run."""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import harness_cost_meter as hcm  # noqa: E402


def _seed_db(path: Path) -> None:
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE sessions (
          session_pk INTEGER PRIMARY KEY,
          vendor TEXT, client TEXT, project_slug TEXT,
          start_ts TEXT, duration_min REAL, model TEXT,
          is_subagent INTEGER DEFAULT 0
        );
        CREATE TABLE runs (
          run_id TEXT PRIMARY KEY,
          session_pk INTEGER,
          vendor TEXT, client TEXT,
          input_tokens INTEGER, output_tokens INTEGER,
          reasoning_tokens INTEGER, cached_tokens INTEGER
        );
        CREATE TABLE tool_calls (
          tool_call_id INTEGER PRIMARY KEY,
          run_id TEXT
        );
        """
    )
    # claude session with tokens
    con.execute(
        "INSERT INTO sessions VALUES (1,'claude','cc','agent-infra',"
        "'2026-07-08T12:00:00Z',10.0,'claude-opus-4-8',0)"
    )
    con.execute(
        "INSERT INTO runs VALUES ('r1',1,'claude','cc',10000,500,100,0)"
    )
    con.execute("INSERT INTO tool_calls VALUES (1,'r1')")
    con.execute("INSERT INTO tool_calls VALUES (2,'r1')")
    # cursor session without tokens
    con.execute(
        "INSERT INTO sessions VALUES (2,'cursor','cursor','agent-infra',"
        "'2026-07-08T13:00:00Z',5.0,'composer-2.5',0)"
    )
    con.execute(
        "INSERT INTO runs VALUES ('r2',2,'cursor','cursor',0,0,0,0)"
    )
    con.execute("INSERT INTO tool_calls VALUES (3,'r2')")
    con.commit()
    con.close()


class TestObserve(unittest.TestCase):
    def test_rollup_by_vendor(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "t.db"
            _seed_db(db)
            rows = hcm.observe(db=db, project="agent-infra", days=30)
            by = {r.vendor: r for r in rows}
            self.assertEqual(by["claude"].sessions, 1)
            self.assertEqual(by["claude"].with_tokens, 1)
            self.assertEqual(by["claude"].avg_in_tok, 10000)
            self.assertEqual(by["claude"].avg_tools, 2.0)
            self.assertIsNotNone(by["claude"].est_usd_per_session)
            self.assertEqual(by["cursor"].sessions, 1)
            self.assertEqual(by["cursor"].with_tokens, 0)
            self.assertIn("token", by["cursor"].note.lower())

    def test_json_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "t.db"
            _seed_db(db)
            rc = hcm.main(["observe", "--db", str(db), "--project", "agent-infra",
                           "--days", "30", "--json"])
            self.assertEqual(rc, 0)


class TestProbe(unittest.TestCase):
    def test_dry_run(self):
        rows = hcm.run_probe(backends=["cursor", "pi"], prompt="x", timeout=5, dry_run=True)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r.get("dry_run") for r in rows))

    def test_parse_cursor_json(self):
        raw = json.dumps({
            "type": "result", "is_error": False,
            "usage": {"inputTokens": 100, "outputTokens": 10, "cacheReadTokens": 50},
            "result": "ok",
        })
        d = hcm._parse_cursor_json(raw)
        self.assertEqual(d["usage"]["inputTokens"], 100)

    def test_parse_pi_jsonl_sums_turn_end(self):
        lines = [
            {"type": "turn_end", "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "first"}],
                "usage": {
                    "input": 100, "output": 5, "cacheRead": 10, "reasoning": 0,
                    "cost": {"total": 0.01},
                },
            }},
            {"type": "message_update", "message": {"usage": {"input": 999}}},  # ignore
            {"type": "turn_end", "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "second"}],
                "usage": {
                    "input": 50, "output": 3, "cacheRead": 20, "reasoning": 2,
                    "cost": {"total": 0.02},
                },
            }},
        ]
        raw = "\n".join(json.dumps(x) for x in lines)
        in_tok, out_tok, cached, cost, preview = hcm._parse_pi_jsonl(raw)
        self.assertEqual(in_tok, 150)
        self.assertEqual(out_tok, 10)  # 5+3 + reasoning 2
        self.assertEqual(cached, 30)
        self.assertAlmostEqual(cost, 0.03)
        self.assertEqual(preview, "second")


if __name__ == "__main__":
    unittest.main()
