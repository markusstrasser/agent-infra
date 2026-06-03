"""Unit tests for scripts/reflect_capture.py — zero-LLM session capture.

Covers the pure core (parse_events / extract_corrections / extract_omissions /
read_omission_rules / append_signals) plus main()'s fail-open scoping.

Hermetic: CAPTURE_LOG is monkeypatched to a tmp_path. No real files, no network,
no LLM. Transcripts are synthetic Claude-Code-style JSONL strings.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import reflect_capture as rc  # noqa: E402


# ── synthetic transcript builders ────────────────────────────────────────────
def _line(obj) -> str:
    return json.dumps(obj)


def assistant_text(text):
    return _line({"type": "assistant", "message": {"role": "assistant",
                  "content": [{"type": "text", "text": text}]}})


def assistant_tool(name, inp):
    return _line({"type": "assistant", "message": {"role": "assistant",
                  "content": [{"type": "tool_use", "name": name, "input": inp}]}})


def user_text(text):
    return _line({"type": "user", "message": {"role": "user",
                  "content": [{"type": "text", "text": text}]}})


def user_tool_result(*, is_error=False, content="result"):
    return _line({"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "is_error": is_error, "content": content}]}})


@pytest.fixture()
def capture_log(tmp_path, monkeypatch):
    log = tmp_path / "claude" / "reflect-capture.jsonl"
    monkeypatch.setattr(rc, "CAPTURE_LOG", log)
    return log


# ── parse_events ─────────────────────────────────────────────────────────────
class TestParseEvents:
    def test_assistant_text_and_tool_use(self):
        ev = rc.parse_events([
            assistant_text("hello world"),
            assistant_tool("Bash", {"command": "ls"}),
        ])
        assert len(ev) == 2
        assert ev[0]["role"] == "assistant"
        assert ev[0]["texts"] == ["hello world"]
        assert ev[0]["tools"] == []
        assert ev[1]["tools"] == [{"name": "Bash", "input": {"command": "ls"}}]
        assert ev[1]["is_tool_result"] is False

    def test_user_text_event(self):
        ev = rc.parse_events([user_text("please continue")])
        assert ev[0]["role"] == "user"
        assert ev[0]["texts"] == ["please continue"]
        assert ev[0]["is_tool_result"] is False

    def test_user_tool_result_flagged_and_error_counted(self):
        ev = rc.parse_events([
            user_tool_result(is_error=True),
            user_tool_result(is_error=False),
        ])
        assert ev[0]["is_tool_result"] is True
        assert ev[0]["errors"] == 1
        assert ev[1]["is_tool_result"] is True
        assert ev[1]["errors"] == 0

    def test_string_content_is_coerced_to_text_block(self):
        line = _line({"type": "assistant", "message": {"role": "assistant",
                      "content": "plain string body"}})
        ev = rc.parse_events([line])
        assert ev[0]["texts"] == ["plain string body"]

    def test_blank_and_malformed_lines_skipped(self):
        ev = rc.parse_events(["", "   ", "{not json", assistant_text("ok")])
        assert len(ev) == 1
        assert ev[0]["texts"] == ["ok"]

    def test_role_from_top_level_type_when_no_message_role(self):
        # 'type' present, message.role absent → role comes from 'type'.
        line = _line({"type": "user", "message": {"content": [
            {"type": "text", "text": "hi"}]}})
        ev = rc.parse_events([line])
        assert ev[0]["role"] == "user"


# ── extract_corrections: #f tag ──────────────────────────────────────────────
class TestCorrectionsFtag:
    def test_f_tag_detected(self):
        events = rc.parse_events([user_text("#f you keep missing the bridge step")])
        cs = rc.extract_corrections(events)
        ftags = [c for c in cs if c["subtype"] == "f_tag"]
        assert len(ftags) == 1
        assert ftags[0]["strength"] == "strong"
        assert "bridge step" in ftags[0]["trigger"]

    def test_f_tag_does_not_double_emit_as_negation(self):
        # "#f" also matches _NEG_RE, but the elif means only f_tag fires.
        events = rc.parse_events([user_text("#f that's wrong, do it differently")])
        cs = rc.extract_corrections(events)
        subtypes = [c["subtype"] for c in cs]
        assert subtypes.count("f_tag") == 1
        assert "negation" not in subtypes

    def test_tool_result_with_f_text_is_not_a_correction(self):
        # tool_result envelopes are skipped even if their content looks correction-y.
        events = rc.parse_events([user_tool_result(content="#f")])
        assert rc.extract_corrections(events) == []


# ── extract_corrections: negation-after-action ───────────────────────────────
class TestCorrectionsNegation:
    def test_negation_after_assistant_action_fires(self):
        events = rc.parse_events([
            assistant_tool("Edit", {"file_path": "a.py", "old_string": "x", "new_string": "y"}),
            user_text("no, that is wrong — revert it"),
        ])
        cs = rc.extract_corrections(events)
        negs = [c for c in cs if c["subtype"] == "negation"]
        assert len(negs) == 1
        assert negs[0]["strength"] == "strong"  # "that is wrong" is a STRONG token

    def test_short_negation_without_prior_action_still_fires(self):
        # len(text) < 200 path: negation fires even with no preceding tool action.
        events = rc.parse_events([user_text("don't do that")])
        cs = rc.extract_corrections(events)
        assert any(c["subtype"] == "negation" for c in cs)

    def test_long_negation_without_action_does_not_fire(self):
        # A long (>=200 char) message with a negation token but NO preceding action
        # must NOT fire (after_action is False AND len(text) >= 200).
        long_msg = "instead " + ("padding words here " * 30)  # >200 chars
        assert len(long_msg) >= 200
        events = rc.parse_events([user_text(long_msg)])
        cs = rc.extract_corrections(events)
        assert not any(c["subtype"] == "negation" for c in cs)

    def test_neutral_user_text_no_correction(self):
        events = rc.parse_events([
            assistant_tool("Bash", {"command": "ls"}),
            user_text("Please continue with the next step."),
        ])
        cs = rc.extract_corrections(events)
        assert cs == []

    def test_strength_grading_medium(self):
        events = rc.parse_events([
            assistant_tool("Write", {"file_path": "f"}),
            user_text("use the other approach instead"),
        ])
        negs = [c for c in rc.extract_corrections(events) if c["subtype"] == "negation"]
        assert negs and negs[0]["strength"] == "medium"  # "instead" is MEDIUM


# ── extract_corrections: retry runs (FM24) ───────────────────────────────────
class TestCorrectionsRetryRun:
    def test_three_varied_same_tool_calls_fire(self):
        events = rc.parse_events([
            assistant_tool("Bash", {"command": "pytest -k a"}),
            assistant_tool("Bash", {"command": "pytest -k b"}),
            assistant_tool("Bash", {"command": "pytest -k c"}),
        ])
        runs = [c for c in rc.extract_corrections(events) if c["subtype"] == "retry_run"]
        assert len(runs) == 1
        assert runs[0]["strength"] == "medium"
        assert "Bash x3" in runs[0]["trigger"]

    def test_intervening_user_text_breaks_the_run(self):
        # 2 calls, USER TEXT (diagnosis), 2 calls. Each segment < 3 → no retry_run.
        events = rc.parse_events([
            assistant_tool("Bash", {"command": "pytest -k a"}),
            assistant_tool("Bash", {"command": "pytest -k b"}),
            user_text("Please continue with the next step."),  # neutral, breaks run
            assistant_tool("Bash", {"command": "pytest -k c"}),
            assistant_tool("Bash", {"command": "pytest -k d"}),
        ])
        cs = rc.extract_corrections(events)
        assert not any(c["subtype"] == "retry_run" for c in cs)

    def test_identical_inputs_do_not_fire(self):
        # 3 calls but all identical input → set() < 2 → no run (needs varied input).
        events = rc.parse_events([
            assistant_tool("Bash", {"command": "ls"}),
            assistant_tool("Bash", {"command": "ls"}),
            assistant_tool("Bash", {"command": "ls"}),
        ])
        assert not any(c["subtype"] == "retry_run" for c in rc.extract_corrections(events))

    def test_two_calls_below_threshold(self):
        events = rc.parse_events([
            assistant_tool("Bash", {"command": "a"}),
            assistant_tool("Bash", {"command": "b"}),
        ])
        assert not any(c["subtype"] == "retry_run" for c in rc.extract_corrections(events))

    def test_different_tool_breaks_run(self):
        # A,A,B,A → the B resets the run; neither A-segment reaches 3.
        events = rc.parse_events([
            assistant_tool("Bash", {"command": "a"}),
            assistant_tool("Bash", {"command": "b"}),
            assistant_tool("Read", {"file_path": "x"}),
            assistant_tool("Bash", {"command": "c"}),
        ])
        assert not any(c["subtype"] == "retry_run" for c in rc.extract_corrections(events))

    def test_tool_result_between_calls_does_not_break_run(self):
        # tool_result envelopes are NOT user-text, so they must NOT break the run.
        events = rc.parse_events([
            assistant_tool("Bash", {"command": "a"}),
            user_tool_result(is_error=False),
            assistant_tool("Bash", {"command": "b"}),
            user_tool_result(is_error=False),
            assistant_tool("Bash", {"command": "c"}),
        ])
        runs = [c for c in rc.extract_corrections(events) if c["subtype"] == "retry_run"]
        assert len(runs) == 1


# ── extract_corrections: fail_then_user ──────────────────────────────────────
class TestCorrectionsFailThenUser:
    def test_errored_result_then_user_text_fires(self):
        events = rc.parse_events([
            assistant_tool("Bash", {"command": "boom"}),
            user_tool_result(is_error=True),
            user_text("that broke, try a different command"),
        ])
        fails = [c for c in rc.extract_corrections(events) if c["subtype"] == "fail_then_user"]
        assert len(fails) == 1
        assert fails[0]["strength"] == "medium"
        assert "broke" in fails[0]["trigger"]

    def test_error_then_tool_result_does_not_fire(self):
        # error followed by ANOTHER tool_result (not user text) → no fail_then_user.
        events = rc.parse_events([
            user_tool_result(is_error=True),
            user_tool_result(is_error=False),
        ])
        assert not any(c["subtype"] == "fail_then_user" for c in rc.extract_corrections(events))

    def test_successful_result_then_user_does_not_fire(self):
        events = rc.parse_events([
            user_tool_result(is_error=False),
            user_text("looks good, continue"),
        ])
        assert not any(c["subtype"] == "fail_then_user" for c in rc.extract_corrections(events))


# ── read_omission_rules ──────────────────────────────────────────────────────
class TestReadOmissionRules:
    def _write_claude_md(self, project_dir: Path, body: str):
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "CLAUDE.md").write_text(body, encoding="utf-8")

    def test_parses_rules_block(self, tmp_path):
        rules_json = {
            "rules": [
                {"name": "bridge-sync", "trigger_files": ["src/phenome/"],
                 "required_any": ["bridge_artifact"]},
            ]
        }
        body = "# Project\n\n<!-- omission-rules " + json.dumps(rules_json) + " -->\n"
        self._write_claude_md(tmp_path, body)
        rules = rc.read_omission_rules(tmp_path)
        assert len(rules) == 1
        assert rules[0]["name"] == "bridge-sync"
        assert rules[0]["trigger_files"] == ["src/phenome/"]

    def test_no_claude_md_returns_empty(self, tmp_path):
        assert rc.read_omission_rules(tmp_path) == []

    def test_claude_md_without_block_returns_empty(self, tmp_path):
        self._write_claude_md(tmp_path, "# Project\n\nNo omission rules here.\n")
        assert rc.read_omission_rules(tmp_path) == []

    def test_malformed_json_returns_empty(self, tmp_path):
        self._write_claude_md(tmp_path, "<!-- omission-rules {not valid json} -->")
        assert rc.read_omission_rules(tmp_path) == []

    def test_block_missing_rules_key_returns_empty_list(self, tmp_path):
        self._write_claude_md(tmp_path, "<!-- omission-rules {\"other\": 1} -->")
        assert rc.read_omission_rules(tmp_path) == []


# ── extract_omissions ────────────────────────────────────────────────────────
RULE = {"name": "bridge-sync", "trigger_files": ["src/phenome/"],
        "required_any": ["bridge_artifact", "BridgeSync"]}


class TestExtractOmissions:
    def test_fires_when_trigger_written_and_no_required_capability(self):
        events = rc.parse_events([
            assistant_tool("Write", {"file_path": "/repo/src/phenome/bridge/new.py"}),
            assistant_tool("Bash", {"command": "echo done"}),  # unrelated
        ])
        oms = rc.extract_omissions(events, [RULE])
        assert len(oms) == 1
        assert oms[0]["subtype"] == "bridge-sync"
        assert oms[0]["strength"] == "shadow"
        assert oms[0]["shadow"] is True
        assert "src/phenome/bridge/new.py" in oms[0]["trigger"]

    def test_does_not_fire_when_required_capability_seen_as_tool_name(self):
        events = rc.parse_events([
            assistant_tool("Write", {"file_path": "/repo/src/phenome/bridge/new.py"}),
            assistant_tool("BridgeSync", {"target": "genomics"}),  # required cap present
        ])
        assert rc.extract_omissions(events, [RULE]) == []

    def test_does_not_fire_when_required_capability_in_bash_command(self):
        events = rc.parse_events([
            assistant_tool("Write", {"file_path": "/repo/src/phenome/bridge/new.py"}),
            assistant_tool("Bash", {"command": "uv run python3 scripts/bridge_artifact.py"}),
        ])
        assert rc.extract_omissions(events, [RULE]) == []

    def test_does_not_fire_when_trigger_file_not_written(self):
        events = rc.parse_events([
            assistant_tool("Write", {"file_path": "/repo/scripts/unrelated.py"}),
        ])
        assert rc.extract_omissions(events, [RULE]) == []

    def test_read_of_trigger_path_does_not_count_as_write(self):
        # Only Write/Edit/NotebookEdit count as touching a trigger file; Read does not.
        events = rc.parse_events([
            assistant_tool("Read", {"file_path": "/repo/src/phenome/bridge/x.py"}),
        ])
        assert rc.extract_omissions(events, [RULE]) == []

    def test_edit_also_counts_as_trigger(self):
        events = rc.parse_events([
            assistant_tool("Edit", {"file_path": "/repo/src/phenome/bridge/x.py",
                                    "old_string": "a", "new_string": "b"}),
        ])
        oms = rc.extract_omissions(events, [RULE])
        assert len(oms) == 1

    def test_no_rules_no_omissions(self):
        events = rc.parse_events([
            assistant_tool("Write", {"file_path": "/repo/src/phenome/bridge/x.py"}),
        ])
        assert rc.extract_omissions(events, []) == []


# ── extract_signals (composition) ────────────────────────────────────────────
def test_extract_signals_combines_corrections_and_omissions():
    events = rc.parse_events([
        assistant_tool("Write", {"file_path": "/repo/src/phenome/bridge/x.py"}),
        user_text("#f you skipped the sync"),
    ])
    sigs = rc.extract_signals(events, [RULE])
    kinds = {s["kind"] for s in sigs}
    assert "correction" in kinds
    assert "omission" in kinds


# ── append_signals (dedupe + idempotency) ────────────────────────────────────
class TestAppendSignals:
    def _sig(self, subtype="f_tag", trigger="t"):
        return {"kind": "correction", "subtype": subtype, "strength": "strong", "trigger": trigger}

    def test_writes_rows_and_returns_count(self, capture_log):
        n = rc.append_signals("sess1", "agent-infra",
                              [self._sig(trigger="a"), self._sig(trigger="b")], "2026-06-03T00:00:00+00:00")
        assert n == 2
        rows = [json.loads(l) for l in capture_log.read_text().splitlines() if l.strip()]
        assert len(rows) == 2
        assert all(r["schema"] == "reflect.capture.v1" for r in rows)
        assert all(r["session"] == "sess1" for r in rows)
        assert all(r["project"] == "agent-infra" for r in rows)
        assert all("hash" in r and r["hash"] for r in rows)

    def test_empty_signals_writes_nothing(self, capture_log):
        assert rc.append_signals("sess1", "agent-infra", [], "2026-06-03T00:00:00+00:00") == 0
        assert not capture_log.exists()

    def test_dedupe_within_single_call(self, capture_log):
        # Two identical signals → same hash → only one row written.
        dup = self._sig(trigger="same")
        n = rc.append_signals("sess1", "agent-infra", [dup, dict(dup)], "2026-06-03T00:00:00+00:00")
        assert n == 1
        rows = [l for l in capture_log.read_text().splitlines() if l.strip()]
        assert len(rows) == 1

    def test_idempotent_across_calls(self, capture_log):
        sig = self._sig(trigger="once")
        first = rc.append_signals("sess1", "agent-infra", [sig], "2026-06-03T00:00:00+00:00")
        second = rc.append_signals("sess1", "agent-infra", [sig], "2026-06-03T00:00:00+00:00")
        assert first == 1
        assert second == 0  # already seen → no new row
        rows = [l for l in capture_log.read_text().splitlines() if l.strip()]
        assert len(rows) == 1

    def test_same_signal_different_session_is_not_deduped(self, capture_log):
        # Hash includes the session id, so the same signal in a new session writes.
        sig = self._sig(trigger="shared")
        rc.append_signals("sess1", "agent-infra", [sig], "2026-06-03T00:00:00+00:00")
        n = rc.append_signals("sess2", "agent-infra", [sig], "2026-06-03T00:00:00+00:00")
        assert n == 1
        rows = [json.loads(l) for l in capture_log.read_text().splitlines() if l.strip()]
        assert {r["session"] for r in rows} == {"sess1", "sess2"}

    def test_sig_hash_stable_and_session_sensitive(self):
        s = self._sig(trigger="x")
        assert rc._sig_hash("a", s) == rc._sig_hash("a", s)
        assert rc._sig_hash("a", s) != rc._sig_hash("b", s)
        assert len(rc._sig_hash("a", s)) == 16


# ── main() fail-open + scoping ───────────────────────────────────────────────
class TestMain:
    def _run_main(self, monkeypatch, payload, *, tty=False):
        import io
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
        monkeypatch.setattr(sys.stdin, "isatty", lambda: tty, raising=False)
        return rc.main()

    def test_noop_for_non_testbed_project(self, tmp_path, monkeypatch, capture_log):
        # Project not in TESTBED → returns 0 and writes nothing, even with a transcript.
        transcript = tmp_path / "t.jsonl"
        transcript.write_text(user_text("#f wrong") + "\n", encoding="utf-8")
        payload = {"session_id": "s", "cwd": "/some/path/not-a-testbed",
                   "transcript_path": str(transcript)}
        rccode = self._run_main(monkeypatch, payload)
        assert rccode == 0
        assert not capture_log.exists()

    def test_returns_zero_when_transcript_missing(self, monkeypatch, capture_log):
        payload = {"session_id": "s", "cwd": "/x/agent-infra",
                   "transcript_path": "/nonexistent/transcript.jsonl"}
        assert self._run_main(monkeypatch, payload) == 0
        assert not capture_log.exists()

    def test_testbed_project_captures_signal(self, tmp_path, monkeypatch, capture_log):
        # A testbed project with a real transcript → captures and writes rows.
        project = tmp_path / "agent-infra"
        project.mkdir()
        transcript = tmp_path / "t.jsonl"
        transcript.write_text(
            assistant_tool("Edit", {"file_path": "a.py"}) + "\n"
            + user_text("no, that's wrong") + "\n",
            encoding="utf-8",
        )
        payload = {"session_id": "sess-xyz", "cwd": str(project),
                   "transcript_path": str(transcript),
                   "timestamp": "2026-06-03T00:00:00+00:00"}
        assert self._run_main(monkeypatch, payload) == 0
        assert capture_log.exists()
        rows = [json.loads(l) for l in capture_log.read_text().splitlines() if l.strip()]
        assert rows and rows[0]["session"] == "sess-xyz"
        assert rows[0]["project"] == "agent-infra"

    def test_empty_stdin_payload_fails_open(self, monkeypatch, capture_log):
        # Garbage / empty stdin → JSON parse fails → empty payload → project "unknown"
        # → not in TESTBED → returns 0, no crash.
        import io
        monkeypatch.setattr(sys, "stdin", io.StringIO("not json at all"))
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)
        assert rc.main() == 0
        assert not capture_log.exists()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
