"""Focused contract tests for agent-infra's tolerant plan metadata reader."""

from conftest import import_hyphenated

mod = import_hyphenated("plan-status")


def test_parse_frontmatter_supports_scalar_and_list_forms():
    text = """---
status: running
completed_phases: [1, 2]
blocks:
  - deploy
  - 'review'
---
# Body
"""
    assert mod.parse_frontmatter(text) == {
        "status": "running",
        "completed_phases": ["1", "2"],
        "blocks": ["deploy", "review"],
    }


def test_parse_frontmatter_is_tolerant_of_missing_or_malformed_data():
    assert mod.parse_frontmatter("# no frontmatter\n") == {}
    assert mod.parse_frontmatter("---\nstatus: running\nbroken\n---\n") == {}
