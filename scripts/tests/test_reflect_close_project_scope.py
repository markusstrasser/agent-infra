"""Project scope of the close path: the bare fallback and the ack stay in the invoking project.

Regression (steward proposal 2026-07-21): `--latest-digest ""` — the SessionStart-nudge
fallback — run from arc-agi returned agent-infra session 6822f087's digest, so an arc-agi
close would verify and ack another project's claims without its context. The project is
the capture path's cwd → project mapping (reflect_capture.project_from_cwd); crossing
projects takes an explicit `--any-project`.

Also pinned (steward 2026-08-18): `/rsi close` looks up the CURRENT session; when that
misses, stderr names this project's pending digest instead of a bare "no match", so a
prior session's digest does not survive a "clean drain, no digest" close.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import reflect_session_close as rsc  # noqa: E402

ARC = "131bd1e3-0adf-4b91-8775-622295a0c272"
INFRA = "6822f087-8f3b-47ac-a836-4491025912e8"


@pytest.fixture()
def env(tmp_path, monkeypatch):
    log = tmp_path / "reflect-close-digest.jsonl"
    monkeypatch.setattr(rsc, "DIGEST_LOG", log)
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("{}\n", encoding="utf-8")
    rows = [  # the agent-infra digest is the NEWER one, as in the incident
        {"schema": "reflect.close-digest.v1", "session_id": ARC, "project": "arc-agi"},
        {"schema": "reflect.close-digest.v1", "session_id": INFRA, "project": "agent-infra"},
    ]
    with log.open("w", encoding="utf-8") as fh:
        for row in rows:
            row.update(ts=rsc._utc_now(), invoke_skill=True, transcript_path=str(transcript))
            fh.write(json.dumps(row) + "\n")
    for name in ("arc-agi", "agent-infra", "genomics"):
        (tmp_path / name).mkdir()
    return {"log": log, "root": tmp_path, "chdir": lambda name: monkeypatch.chdir(tmp_path / name)}


def _sid(capsys) -> str:
    return json.loads(capsys.readouterr().out)["session_id"]


def test_bare_fallback_stays_in_the_invoking_project(env, capsys):
    env["chdir"]("arc-agi")
    assert rsc.main(["--latest-digest", ""]) == 0
    assert _sid(capsys) == ARC
    env["chdir"]("agent-infra")
    assert rsc.main(["--latest-digest"]) == 0
    assert _sid(capsys) == INFRA


def test_bare_fallback_never_crosses_projects_without_the_flag(env, capsys):
    env["chdir"]("genomics")
    assert rsc.main(["--latest-digest", ""]) == 1
    assert "project 'genomics'" in capsys.readouterr().err
    assert rsc.main(["--latest-digest", "", "--any-project"]) == 0
    assert _sid(capsys) == INFRA  # newest across projects


def test_cross_project_ack_needs_the_flag(env, capsys):
    env["chdir"]("arc-agi")
    before = env["log"].read_text()
    assert rsc.main(["--ack", INFRA]) == 1
    assert "belongs to project 'agent-infra'" in capsys.readouterr().err
    assert env["log"].read_text() == before
    assert rsc.main(["--ack", INFRA, "--any-project"]) == 0
    assert [r["session_id"] for r in rsc.pending_digests()] == [ARC]
    assert rsc.main(["--ack", ARC[:8]]) == 0  # own project: no flag needed
    assert rsc.pending_digests() == []


def test_explicit_lookup_is_not_project_gated(env, capsys):
    env["chdir"]("arc-agi")
    assert rsc.main(["--latest-digest", INFRA]) == 0
    assert _sid(capsys) == INFRA


def test_current_session_miss_points_at_this_projects_pending_digest(env, capsys):
    env["chdir"]("arc-agi")
    current = "9fb0b1e4-1111-2222-3333-444444444444"  # this session: no digest of its own
    assert rsc.main(["--latest-digest", current]) == 1
    err = capsys.readouterr().err
    assert f"--latest-digest {ARC}" in err
    assert INFRA not in err


def test_nudge_and_closer_share_the_capture_mapping(env):
    import reflect_capture as rc

    env["chdir"]("arc-agi")
    assert rsc._current_project() == rc.project_from_cwd(Path.cwd()) == "arc-agi"
    nudge = rsc.pending_nudge()
    assert nudge is not None and ARC in nudge and INFRA not in nudge
