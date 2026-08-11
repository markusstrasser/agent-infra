from lint_plan_killswitch import lint


def test_no_trigger_ok():
    code, _ = lint("# Plan\n\nAdd a logging line to doctor.\n")
    assert code == 0


def test_trigger_without_section_fails():
    code, msg = lint(
        "# Plan\n\nMulti-phase kernel refactor with dual-write cutover then remove-old-path.\n"
    )
    assert code == 2
    assert "missing" in msg.lower()


def test_trigger_with_section_ok():
    text = """# Plan
Multi-phase kernel refactor.

## Kill-switch vertical slice
- **Race:** re-derive from receipts on one chain
- **Pass:** stage N succeeds
- **Fail:** journal dead
"""
    code, _ = lint(text)
    assert code == 0
