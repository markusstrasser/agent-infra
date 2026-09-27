"""doctor check: new Claude/Codex/Cursor sessions must get a session_role."""

import sqlite3
from datetime import datetime, timedelta, timezone

from doctor import check_agentlogs_session_roles


def _db(path, rows):
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE sessions (vendor TEXT, start_ts TEXT, session_role TEXT)")
    con.executemany("INSERT INTO sessions VALUES (?, ?, ?)", rows)
    con.commit()
    con.close()
    return path


def _ago(**delta):
    return (datetime.now(timezone.utc) - timedelta(**delta)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def test_new_session_without_role_warns(tmp_path):
    db = _db(tmp_path / "a.db", [
        ("claude", _ago(days=1), "operator"),
        ("cursor", _ago(days=1), None),  # a renamed stamp would look like this
    ])
    [check] = check_agentlogs_session_roles(db)
    assert check.status == "warn" and "cursor 1/1" in check.message


def test_fresh_and_old_nulls_are_expected(tmp_path):
    db = _db(tmp_path / "b.db", [
        ("claude", _ago(hours=1), None),  # parent transcript not indexed yet
        ("claude", _ago(days=40), None),  # transcript past retention
        ("codex", _ago(days=1), "dispatch"),
        ("gemini", _ago(days=1), None),  # no origin stamp to read
    ])
    [check] = check_agentlogs_session_roles(db)
    assert check.status == "pass", check.message
