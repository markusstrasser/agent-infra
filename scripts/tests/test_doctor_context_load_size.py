"""doctor check: rules and skills big enough to tax every reload get flagged."""

from doctor import check_context_load_size


def _rule(path, body, scoped):
    fm = "---\npaths:\n  - \"scripts/**\"\n---\n" if scoped else ""
    path.write_text(fm + body)


def test_small_files_pass(tmp_path):
    rules = tmp_path / "rules"
    rules.mkdir()
    _rule(rules / "a.md", "x" * 5_000, scoped=True)
    _rule(rules / "b.md", "x" * 7_000, scoped=False)
    [c] = check_context_load_size(rules, "p")
    assert c.status == "pass"


def test_scoped_rule_has_tighter_budget_than_always_loaded(tmp_path):
    rules = tmp_path / "rules"
    rules.mkdir()
    _rule(rules / "scoped.md", "x" * 7_000, scoped=True)
    _rule(rules / "always.md", "x" * 7_000, scoped=False)
    [c] = check_context_load_size(rules, "p")
    assert c.status == "warn"
    assert "scoped.md" in c.message and "always.md" not in c.message


def test_skill_over_reattach_cap_is_marked_truncated(tmp_path):
    skills = tmp_path / "skills"
    for name, n in (("big", 25_000), ("mid", 9_000), ("ok", 3_000)):
        (skills / name).mkdir(parents=True)
        (skills / name / "SKILL.md").write_text("---\nname: x\n---\n" + "x" * n)
    [c] = check_context_load_size(tmp_path / "none", "p", skills)
    assert "big/SKILL.md 25K, TRUNCATED" in c.message
    assert "mid/SKILL.md 9K" in c.message and "TRUNCATED" not in c.message.split("mid/")[1]
    assert "ok/SKILL.md" not in c.message
