"""headless_pin_audit flags a launch that names no model or effort and passes one that names both."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import headless_pin_audit as audit


def problems(tmp_path: Path, name: str, text: str) -> list[str]:
    path = tmp_path / name
    path.write_text(text)
    return audit.audit_file(path)


def test_python_launch_without_effort_is_flagged(tmp_path: Path) -> None:
    found = problems(tmp_path, "a.py", 'def run(p):\n    return ["claude", "-p", "--model", "opus", p]\n')
    assert len(found) == 1 and "a.py:2" in found[0] and "no effort" in found[0]


def test_python_launch_without_model_or_effort_is_flagged(tmp_path: Path) -> None:
    found = problems(tmp_path, "b.py", 'def run(p):\n    cmd = ["codex", "exec", "-s", "read-only", p]\n    return cmd\n')
    assert len(found) == 1 and "no model or effort" in found[0]


def test_flags_added_later_in_the_function_count(tmp_path: Path) -> None:
    text = (
        "def run(p, model, effort):\n"
        '    cmd = ["codex", "exec", p]\n'
        '    cmd.extend(["-m", model])\n'
        "    cmd.extend([\"-c\", f'model_reasoning_effort=\"{effort}\"'])\n"
        "    return cmd\n"
    )
    assert problems(tmp_path, "c.py", text) == []


def test_docstring_mention_is_not_a_launch(tmp_path: Path) -> None:
    assert problems(tmp_path, "d.py", 'def f():\n    """Runs subprocess.run(["codex", "exec", ...])."""\n') == []


def test_shell_launch_and_expanded_array(tmp_path: Path) -> None:
    bare = 'caffeinate -i codex exec -s read-only "$prompt" < /dev/null\n'
    found = problems(tmp_path, "lane", bare)
    assert len(found) == 1 and "no model or effort" in found[0]
    pinned = (
        'args=(-m "$MODEL" -c "model_reasoning_effort=\\"$EFFORT\\"")\n'
        'caffeinate -i codex exec "${args[@]}" -s read-only "$prompt" < /dev/null\n'
    )
    assert problems(tmp_path, "lane2", pinned) == []


def test_quoted_mention_and_waiver_are_skipped(tmp_path: Path) -> None:
    text = (
        'echo "use codex exec -m gpt-6-astra instead"\n'
        'claude -p "$prompt"  # headless-pin: ok (fixture)\n'
    )
    assert problems(tmp_path, "x.sh", text) == []


def test_resume_needs_effort_but_not_model(tmp_path: Path) -> None:
    # A bare resume keeps the session's model and takes the saved /effort (measured 2026-11-11).
    found = problems(tmp_path, "r.sh", 'claude -p -r "$ID" --setting-sources user "/compact"\n')
    assert len(found) == 1 and found[0].endswith("names no effort")
    assert problems(tmp_path, "r2.sh", 'claude -p -r "$ID" --effort "$EFFORT" "/compact"\n') == []


def test_python_in_a_shell_heredoc_is_checked(tmp_path: Path) -> None:
    text = "python3 - <<'PY'\nr = subprocess.run(\n    [\"claude\", \"-p\", \"--model\", MODEL],\n    input=p)\nPY\n"
    found = problems(tmp_path, "hook.sh", text)
    assert len(found) == 1 and "no effort" in found[0]


def test_agent_definition_needs_model_and_effort(tmp_path: Path) -> None:
    assert problems_agent(tmp_path, "---\nname: a\nmodel: opus\neffort: high\n---\nbody\n") == []
    assert "no effort" in problems_agent(tmp_path, "---\nname: a\nmodel: opus\n---\neffort: high in the body\n")[0]
    assert "no model or effort" in problems_agent(tmp_path, "---\nname: a\nmodel: inherit\n---\n")[0]


def problems_agent(tmp_path: Path, text: str) -> list[str]:
    path = tmp_path / "agent.md"
    path.write_text(text)
    return audit.audit_agent(path)


def test_harness_roots_are_clean() -> None:
    files, found = audit.audit(audit.DEFAULT_ROOTS, audit.AGENT_DIRS)
    assert files > 100
    assert found == []
