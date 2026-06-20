"""Tests for memory_provenance_check.py."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Ensure scripts/ is on the path (conftest.py already does this, but be explicit)
SCRIPTS_DIR = Path(__file__).parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import memory_provenance_check as mpc


def _write(tmp: Path, name: str, content: str) -> Path:
    p = tmp / name
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture
def memory_dir(tmp_path):
    """Tmp dir acting as the memory dir, with a real rule file available."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "live-rule.md").write_text("# live rule\n", encoding="utf-8")
    yield tmp_path, rules_dir


def test_clean_file_no_warnings(memory_dir, monkeypatch):
    """A file with a valid links_rule pointing to a real path: no warnings."""
    mem_dir, _ = memory_dir
    # Patch REPO_ROOT so relative links_rule resolves under tmp_path
    monkeypatch.setattr(mpc, "REPO_ROOT", mem_dir)

    _write(mem_dir, "clean.md", """\
---
name: clean
description: a clean memory with rule provenance
provenance:
  source_session_id: abc-123
  links_rule: rules/live-rule.md
  lifecycle: active
---
This file mentions hook and rule but links_rule is set.
""")

    warnings = mpc._check_file(mem_dir / "clean.md")
    assert warnings == [], f"Expected no warnings but got: {warnings}"


def test_missing_links_rule_warning(memory_dir, monkeypatch):
    """Body mentions 'rule' but no provenance.links_rule: MISSING_LINKS_RULE."""
    mem_dir, _ = memory_dir
    monkeypatch.setattr(mpc, "REPO_ROOT", mem_dir)

    _write(mem_dir, "no_link.md", """\
---
name: no-link
description: references a rule but has no provenance block
---
This mentions the global rule for commit messages.
""")

    warnings = mpc._check_file(mem_dir / "no_link.md")
    codes = [w["code"] for w in warnings]
    assert "MISSING_LINKS_RULE" in codes


def test_dangling_links_rule_warning(memory_dir, monkeypatch):
    """links_rule set but the file does not exist: DANGLING_LINKS_RULE."""
    mem_dir, _ = memory_dir
    monkeypatch.setattr(mpc, "REPO_ROOT", mem_dir)

    _write(mem_dir, "dangling.md", """\
---
name: dangling
description: has a dangling rule link
provenance:
  links_rule: rules/does-not-exist.md
  lifecycle: active
---
Mentions a hook somewhere in here.
""")

    warnings = mpc._check_file(mem_dir / "dangling.md")
    codes = [w["code"] for w in warnings]
    assert "DANGLING_LINKS_RULE" in codes


def test_invalid_lifecycle_warning(memory_dir, monkeypatch):
    """provenance.lifecycle has a bad value: INVALID_LIFECYCLE."""
    mem_dir, _ = memory_dir
    monkeypatch.setattr(mpc, "REPO_ROOT", mem_dir)

    _write(mem_dir, "bad_lifecycle.md", """\
---
name: bad-lifecycle
description: lifecycle value is wrong
provenance:
  links_rule: rules/live-rule.md
  lifecycle: pending
---
Some content about governance with no rule claim here.
""")

    warnings = mpc._check_file(mem_dir / "bad_lifecycle.md")
    codes = [w["code"] for w in warnings]
    assert "INVALID_LIFECYCLE" in codes


def test_run_counts(memory_dir, monkeypatch):
    """run() returns correct warning count across all four fixture files."""
    mem_dir, _ = memory_dir
    monkeypatch.setattr(mpc, "REPO_ROOT", mem_dir)

    # clean: 0 warnings
    _write(mem_dir, "clean.md", """\
---
name: clean
description: clean memory
provenance:
  links_rule: rules/live-rule.md
  lifecycle: active
---
Mentions rule but linked.
""")
    # missing links_rule: 1 warning
    _write(mem_dir, "no_link.md", """\
---
name: no-link
description: mentions rule but no provenance
---
References a hook.
""")
    # dangling: 1 warning
    _write(mem_dir, "dangling.md", """\
---
name: dangling
description: dangling rule link
provenance:
  links_rule: rules/ghost.md
  lifecycle: active
---
Hook reference.
""")
    # bad lifecycle: 1 warning
    _write(mem_dir, "bad_lifecycle.md", """\
---
name: bad-lifecycle
description: bad lifecycle value
provenance:
  links_rule: rules/live-rule.md
  lifecycle: unknown_state
---
No rule mention in body.
""")

    n_warn = mpc.run(mem_dir, json_out=False)
    # no_link: MISSING_LINKS_RULE
    # dangling: DANGLING_LINKS_RULE (also has hook mention but links_rule present → no MISSING)
    # bad_lifecycle: INVALID_LIFECYCLE
    # clean: 0
    assert n_warn == 3, f"Expected 3 warnings, got {n_warn}"


def test_memory_md_skipped(memory_dir, monkeypatch):
    """MEMORY.md index file is never checked."""
    mem_dir, _ = memory_dir
    monkeypatch.setattr(mpc, "REPO_ROOT", mem_dir)

    _write(mem_dir, "MEMORY.md", """\
# Memory Index
- [Some hook rule](hook.md)
""")

    files = sorted(p for p in mem_dir.glob("*.md") if p.name != "MEMORY.md")
    assert all(f.name != "MEMORY.md" for f in files)
    # run should not fail on a dir with only MEMORY.md
    n = mpc.run(mem_dir, json_out=False)
    assert n == 0
