"""Negative controls for hooks_smoke.py — prove the detector fires on the
failure classes it claims to catch (a smoke gate that has never seen a true
positive is unverified)."""

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))


def run_smoke(settings: Path) -> tuple[list[dict], int]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "hooks_smoke.py"),
         "--settings-file", str(settings), "--project-only", "--json", "--timeout", "5"],
        capture_output=True, text=True,
    )
    return json.loads(proc.stdout), proc.returncode


def write_settings(tmp_path: Path, command: str, event: str = "Stop") -> Path:
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps(
        {"hooks": {event: [{"hooks": [{"type": "command", "command": command}]}]}}
    ))
    return settings


def test_failopen_syntaxerror_detected(tmp_path):
    """The 2026-06-11 class: SyntaxError swallowed by a fail-open trap, exit 0."""
    hook = tmp_path / "dead.sh"
    hook.write_text(
        "#!/usr/bin/env bash\ntrap 'exit 0' ERR\n"
        "python3 -c 'def broken(:' \n"  # SyntaxError on stderr, but exit 0 via trap
        "exit 0\n"
    )
    hook.chmod(0o755)
    results, rc = run_smoke(write_settings(tmp_path, str(hook)))
    assert rc == 1
    assert results[0]["status"] == "fail"
    assert "SyntaxError" in results[0]["problem"]


def test_missing_script_detected(tmp_path):
    results, rc = run_smoke(write_settings(tmp_path, "/nonexistent/hook.sh"))
    assert rc == 1
    assert results[0]["status"] == "fail"


def test_malformed_json_stdout_detected(tmp_path):
    hook = tmp_path / "badjson.sh"
    hook.write_text("#!/usr/bin/env bash\necho '{\"decision\": '\nexit 0\n")
    hook.chmod(0o755)
    results, rc = run_smoke(write_settings(tmp_path, str(hook)))
    assert rc == 1
    assert "not valid JSON" in results[0]["problem"]


def test_healthy_hook_passes(tmp_path):
    hook = tmp_path / "ok.sh"
    hook.write_text("#!/usr/bin/env bash\ncat > /dev/null\nexit 0\n")
    hook.chmod(0o755)
    results, rc = run_smoke(write_settings(tmp_path, str(hook)))
    assert rc == 0
    assert results[0]["status"] == "pass"


def test_intentional_block_not_failed(tmp_path):
    hook = tmp_path / "block.sh"
    hook.write_text("#!/usr/bin/env bash\necho 'BLOCK: smoke says no' >&2\nexit 2\n")
    hook.chmod(0o755)
    results, rc = run_smoke(write_settings(tmp_path, str(hook)))
    assert rc == 0
    assert results[0]["status"] == "intentional_block"


def test_updated_input_bad_keys_detected(tmp_path):
    """CC 2.1.300 denies invalid updatedInput: an invented key or a dropped required key fails."""
    out = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "updatedInput": {"cmd": "ls"}}}
    hook = tmp_path / "mut.sh"
    hook.write_text(f"#!/usr/bin/env bash\ncat >/dev/null\necho '{json.dumps(out)}'\n")
    hook.chmod(0o755)
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"hooks": {"PreToolUse": [
        {"matcher": "Bash", "hooks": [{"type": "command", "command": str(hook)}]}]}}))
    results, rc = run_smoke(settings)
    bad = [r for r in results if r["command"] == str(hook) and r["status"] == "fail"]
    assert rc == 1 and bad
    assert "unknown Bash keys ['cmd']" in bad[0]["problem"]
    assert "drops required Bash keys ['command']" in bad[0]["problem"]


def test_check_updated_input_accepts_valid_rewrite():
    from hooks_smoke import check_updated_input

    ok = json.dumps({"hookSpecificOutput": {"updatedInput": {"command": "ls", "timeout": 5}}})
    assert check_updated_input("Bash", ok) == (True, None)
    assert check_updated_input("Bash", "plain advisory") == (False, None)


def test_relative_script_lint():
    from hooks_smoke import relative_script

    # The two F10 commands as they stood on 2026-10-21.
    assert relative_script(
        "TOOL_NAME=\"$( jq -r '.tool_name // empty' )\" bash .claude/hooks/bio-constants-gate.sh"
    ) == ".claude/hooks/bio-constants-gate.sh"
    assert relative_script(".claude/hooks/knowledge/ruff-format.sh") == ".claude/hooks/knowledge/ruff-format.sh"
    assert relative_script("uv run python3 scripts/x.py") == "scripts/x.py"
    assert relative_script('bash "$CLAUDE_PROJECT_DIR"/.claude/hooks/x.sh') is None
    assert relative_script("~/Projects/skills/hooks/x.sh") is None
    assert relative_script("cd /Users/x/repo && python3 scripts/x.py") is None
    assert relative_script("BLOCK_MSG='regenerate via scripts/.' ~/hooks/x.sh") is None
    assert relative_script("jq -r .x | grep foo/bar") is None


def test_interpreter_check_flags_old_python(monkeypatch):
    import hooks_smoke

    class Proc:
        returncode, stdout, stderr = 0, "3.9\n", ""

    monkeypatch.setattr(hooks_smoke.subprocess, "run", lambda *a, **k: Proc())
    assert hooks_smoke.interpreter_check().status == "fail"
    Proc.stdout = "3.14\n"
    assert hooks_smoke.interpreter_check().status == "pass"
