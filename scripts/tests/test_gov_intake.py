"""Tests for the governance correction intake hook (scripts/gov_intake.py).

Feeds synthetic UserPromptSubmit hook JSON with and without `#f governance:`
and asserts: capture only when tagged, dedupe on repeat, quarantine file
written, exit 0 in all cases.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent
SCRIPT = SCRIPTS_DIR / "gov_intake.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("gov_intake", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_hook(payload: dict, home: Path) -> subprocess.CompletedProcess:
    env = {"HOME": str(home), "PATH": "/usr/bin:/bin:/usr/local/bin"}
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )


def _quarantine(home: Path, session: str) -> Path:
    return home / ".claude" / "gov-intake" / f"{session}.jsonl"


def test_no_tag_writes_nothing_exit_0(tmp_path):
    home = tmp_path
    payload = {"prompt": "please refactor this module", "session_id": "s1", "cwd": "/proj"}
    res = _run_hook(payload, home)
    assert res.returncode == 0
    assert not _quarantine(home, "s1").exists()


def test_empty_prompt_exit_0(tmp_path):
    res = _run_hook({"session_id": "s0", "cwd": "/proj"}, tmp_path)
    assert res.returncode == 0
    assert not _quarantine(tmp_path, "s0").exists()


def test_tagged_prompt_captures(tmp_path):
    home = tmp_path
    payload = {
        "prompt": "ok thanks. #f governance: never auto-commit research memos without a body.",
        "session_id": "s2",
        "cwd": "/proj",
    }
    res = _run_hook(payload, home)
    assert res.returncode == 0
    qf = _quarantine(home, "s2")
    assert qf.exists()
    recs = [json.loads(l) for l in qf.read_text().splitlines() if l.strip()]
    assert len(recs) == 1
    r = recs[0]
    assert r["correction_text"] == "never auto-commit research memos without a body."
    assert r["session"] == "s2"
    assert r["project"] == "/proj"
    assert r["scope"] == "unknown"
    assert r["generalization_risk"] == "unconfirmed"
    assert r["requires_confirmation"] is True
    assert r["status"] == "pending"
    assert len(r["dedupe_hash"]) == 64


def test_case_insensitive_and_to_end_of_line(tmp_path):
    payload = {
        "prompt": "#F GOVERNANCE: Always tag sources.\nnext line ignored",
        "session_id": "s3",
        "cwd": "/proj",
    }
    res = _run_hook(payload, tmp_path)
    assert res.returncode == 0
    recs = [json.loads(l) for l in _quarantine(tmp_path, "s3").read_text().splitlines() if l.strip()]
    assert len(recs) == 1
    assert recs[0]["correction_text"] == "Always tag sources."


def test_dedupe_on_repeat(tmp_path):
    home = tmp_path
    payload = {
        "prompt": "#f governance: prefer SQLite views over CLI wrappers",
        "session_id": "s4",
        "cwd": "/proj",
    }
    _run_hook(payload, home)
    _run_hook(payload, home)  # identical repeat
    # whitespace/case variant — normalizes to same hash
    payload2 = dict(payload, prompt="#f GOVERNANCE:   Prefer SQLite Views Over CLI Wrappers  ")
    _run_hook(payload2, home)
    recs = [json.loads(l) for l in _quarantine(home, "s4").read_text().splitlines() if l.strip()]
    assert len(recs) == 1


def test_max_one_capture_per_prompt(tmp_path):
    payload = {
        "prompt": "#f governance: first rule\n#f governance: second rule",
        "session_id": "s5",
        "cwd": "/proj",
    }
    _run_hook(payload, tmp_path)
    recs = [json.loads(l) for l in _quarantine(tmp_path, "s5").read_text().splitlines() if l.strip()]
    assert len(recs) == 1
    assert recs[0]["correction_text"] == "first rule"


def test_malformed_stdin_fails_open(tmp_path):
    env = {"HOME": str(tmp_path), "PATH": "/usr/bin:/bin"}
    res = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input="not json {{{",
        capture_output=True,
        text=True,
        env=env,
    )
    assert res.returncode == 0


def test_load_pending(tmp_path, monkeypatch):
    mod = _load_module()
    monkeypatch.setenv("HOME", str(tmp_path))
    # capture via the module's own dir resolution (honors HOME)
    mod.capture({"prompt": "#f governance: rule A", "session_id": "sx", "cwd": "/p"})
    mod.capture({"prompt": "#f governance: rule B", "session_id": "sy", "cwd": "/p"})
    all_pending = mod.load_pending()
    assert len(all_pending) == 2
    one = mod.load_pending(session="sx")
    assert len(one) == 1
    assert one[0]["correction_text"] == "rule A"


def test_load_pending_empty_dir(tmp_path, monkeypatch):
    mod = _load_module()
    monkeypatch.setenv("HOME", str(tmp_path))
    assert mod.load_pending() == []
