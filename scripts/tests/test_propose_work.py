import sqlite3

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
