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
