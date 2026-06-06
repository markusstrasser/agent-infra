import sqlite3
import json
from pathlib import Path

from conftest import import_hyphenated


def test_hook_roi_highlights_tolerates_non_utf8_trigger_log(monkeypatch, tmp_path):
    mod = import_hyphenated("propose-work")
    trigger_log = tmp_path / "hook-triggers.jsonl"
    trigger_log.write_bytes(
        b'{"ts":"2999-01-01T00:00:00","hook":"clean","action":"block"}\n'
        b'{"ts":"2999-01-01T00:00:00","hook":"bad-\xe2","action":"warn"}\n'
        b'not-json-\xff\n'
        b'"json scalar is ignored"\n'
    )
    monkeypatch.setattr(mod, "TRIGGERS_FILE", trigger_log)

    out = mod.hook_roi_highlights(days=1)

    assert out["total"] == 2
    hooks = {h["hook"]: h for h in out["hooks"]}
    assert hooks["clean"]["blocks"] == 1
    assert hooks["bad-�"]["warns"] == 1


def test_orchestrator_queue_tolerates_empty_stale_db(monkeypatch, tmp_path):
    mod = import_hyphenated("propose-work")
    db_path = tmp_path / "orchestrator.db"
    sqlite3.connect(db_path).close()
    monkeypatch.setattr(mod, "ORCHESTRATOR_DB", db_path)

    assert mod.orchestrator_queue() == {
        "pending": 0,
        "running": 0,
        "failed": 0,
        "tasks": [],
    }


def _proposal_ranker_cases() -> list[dict]:
    root = Path(__file__).resolve().parents[2]
    fixture = root / "experiments" / "proposal-ranker" / "test_cases.json"
    data = json.loads(fixture.read_text())
    return data["dev"] + data["holdout"] + [
        {
            "name": "security fail outranks routine warning",
            "higher": {"category": "security", "title": "FAIL: token leaked to public repo", "metadata": {}},
            "lower": {"category": "health", "title": "WARN: local dashboard slow", "metadata": {}},
        },
        {
            "name": "data loss beats high false-positive hook",
            "higher": {"category": "health", "title": "FAIL: losing session data during ingest", "metadata": {}},
            "lower": {"category": "hook-roi", "title": "Hook blocking 95% — false positives", "metadata": {"block_rate": 0.95}},
        },
        {
            "name": "shared drift beats single warning",
            "higher": {"category": "health", "title": "WARN: shared MCP config drift", "metadata": {"scope": "shared", "affected_projects": 5}},
            "lower": {"category": "health", "title": "WARN: one repo has stale path", "metadata": {"scope": "single"}},
        },
        {
            "name": "fresh autonomy blocker beats old cosmetic",
            "higher": {"category": "improvement-log", "title": "Unresolved: agent cannot proceed after hook denial", "metadata": {"age_days": 1, "tags": ["autonomy", "hook"]}},
            "lower": {"category": "improvement-log", "title": "Unresolved: old commit-scope style nit", "metadata": {"age_days": 90, "tags": ["style"]}},
        },
        {
            "name": "morning brief repeated failure beats optional stale repo",
            "higher": {"category": "orchestrator", "title": "Task failed: morning-brief — 3rd consecutive failure", "metadata": {"pipeline": "morning-brief", "consecutive_failures": 3}},
            "lower": {"category": "staleness", "title": "research-mcp has no commits in 21 days", "metadata": {"days_ago": 21}},
        },
    ]


def test_rank_score_matches_fixture_priority_pairs():
    mod = import_hyphenated("propose-work")

    misses = []
    for case in _proposal_ranker_cases():
        higher = mod._rank_score(case["higher"])
        lower = mod._rank_score(case["lower"])
        if higher <= lower:
            misses.append((case["name"], higher, lower))

    assert misses == []


def test_generate_proposals_enriches_rank_metadata():
    mod = import_hyphenated("propose-work")
    data = {
        "stale_projects": [{"project": "skills", "days_ago": 9}],
        "doctor_failures": [{"status": "fail", "name": "hook:guard", "message": "Script missing", "scope": "shared"}],
        "unresolved_findings": [{"age_days": 20, "title": "Agent skips cross-model review"}],
        "hook_roi": {"hooks": [{"hook": "data-guard", "total": 20, "blocks": 15, "block_rate": 0.75}]},
        "strategic_notes": [],
        "drift_alerts": [],
        "maintenance_errors": {},
        "orchestrator": {"tasks": [{"id": 3, "pipeline": "morning-brief", "step": "collect", "error": "DB locked"}]},
    }

    proposals = mod.generate_proposals(data)
    metadata_by_category = {p["category"]: p["metadata"] for p in proposals}

    assert metadata_by_category["staleness"]["project"] == "skills"
    assert metadata_by_category["health"]["scope"] == "shared"
    assert "autonomy" in metadata_by_category["improvement-log"]["tags"]
    assert metadata_by_category["hook-roi"]["risk_class"] == "false-positive-hook"
    assert metadata_by_category["orchestrator"]["pipeline"] == "morning-brief"
