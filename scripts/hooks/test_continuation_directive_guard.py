#!/usr/bin/env python3
"""Selftest for continuation-directive-guard.py.

Run: uv run python3 scripts/hooks/test_continuation_directive_guard.py
(also collected by pytest).

Verifies: fires on a bare continuation directive ("Continue from where you left
off" and friends), stays SILENT on a substantive prompt / a continue-plus-real-ask
/ non-continuation prose, emits the correct UserPromptSubmit additionalContext
shape, and always exits 0 (fail-open) — mirrors test_userprompt_prior_context.py.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).parent / "continuation-directive-guard.py"

# Hermetic HOME so the hook's best-effort hook-trigger-log call can't write into
# the real ~/.claude (it shells to a script under $HOME; redirecting HOME makes
# that path miss harmlessly).
_HOME = tempfile.TemporaryDirectory()
(Path(_HOME.name) / ".claude").mkdir(parents=True, exist_ok=True)


def run(envelope: dict) -> str:
    p = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(envelope), capture_output=True, text=True, timeout=10,
        env={**os.environ, "HOME": _HOME.name},
    )
    assert p.returncode == 0, f"hook must always exit 0, got {p.returncode}: {p.stderr}"
    return p.stdout.strip()


def ctx(out: str) -> str:
    if not out:
        return ""
    obj = json.loads(out)
    return obj["hookSpecificOutput"]["additionalContext"]


def main() -> None:
    passed = 0
    failed = 0

    def check(name: str, cond: bool) -> None:
        nonlocal passed, failed
        if cond:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL: {name}")

    # --- FIRES on bare continuation directives ---
    fire_cases = [
        "Continue from where you left off",
        "continue from where you left off.",
        "Continue",
        "resume",
        "keep going",
        "carry on",
        "please continue",
        "pick up where you were",
        "proceed",
        "Continue from where you left off please",
        "ok, continue",
        "finish the task",
    ]
    for i, prompt in enumerate(fire_cases):
        out = run({"user_message": prompt, "cwd": ".", "session_id": f"f{i}"})
        c = ctx(out)
        check(f"fires on {prompt!r}", bool(c))
        if c:
            check(f"names CONTINUATION DIRECTIVE for {prompt!r}",
                  "CONTINUATION DIRECTIVE" in c)
            check(f"says not a no-op for {prompt!r}",
                  "no-op" in c or "no response needed" in c)
            check(f"emits UserPromptSubmit shape for {prompt!r}",
                  json.loads(out)["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit")

    # --- SILENT on substantive / non-continuation prompts ---
    silent_cases = [
        "fix the import error in maintain_tick.py",
        "why is the build failing?",
        "add a test for the continuation hook",
        "what's the status of the maintain-tick motor?",
        "continue building the parser, but first fix the regex in foo.py",  # continue + real ask
        "resume the deploy after you check the disk space on /Volumes/SSK1TB",  # resume + real ask
        "let's keep the architecture simple here",  # 'keep' but not 'keep going'
        "the continuation hook is working great, thanks",  # praise, not a directive
        "should we continue using opus for this lane or switch?",  # question, not a directive
    ]
    for i, prompt in enumerate(silent_cases):
        out = run({"user_message": prompt, "cwd": ".", "session_id": f"s{i}"})
        check(f"silent on {prompt!r}", out == "")

    # --- fail-open / malformed input ---
    check("empty stdin is safe", run({}) == "")
    p = subprocess.run([sys.executable, str(HOOK)], input="not json{",
                       capture_output=True, text=True, timeout=10)
    check("garbage stdin exits 0 silently", p.returncode == 0 and p.stdout.strip() == "")
    check("empty message is silent",
          run({"user_message": "", "cwd": ".", "session_id": "e"}) == "")

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


# pytest entry point (collected as test_*)
def test_continuation_directive_guard():
    # Re-run the standalone main in a subprocess so an assert/exit doesn't kill
    # the pytest process; assert it reports zero failures.
    r = subprocess.run([sys.executable, str(Path(__file__))],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "0 failed" in r.stdout, r.stdout


if __name__ == "__main__":
    main()
