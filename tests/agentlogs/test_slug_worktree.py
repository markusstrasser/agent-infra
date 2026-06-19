"""slug_from_path canonicalizes isolate-by-default worktree slugs.

P2 of .claude/plans/c2417c3c-worktree-isolation-adoption.md: a worktree session's
cwd basename is "<repo>-wt<pid>" (claude-launch.sh), which would otherwise index
under a distinct project_slug, going blind to its canonical repo in
`agentlogs recent` / dashboards / loop-funnel. slug_from_path is the single
chokepoint every adapter (claude/codex/cursor/kimi) routes through, so the
canonicalization lives there.
"""
from __future__ import annotations

from agentlogs.adapters.common import slug_from_path


def test_canonical_repo_slug_unchanged():
    assert slug_from_path("/Users/alien/Projects/agent-infra") == "agent-infra"
    assert slug_from_path("/Users/alien/Projects/genomics") == "genomics"


def test_worktree_suffix_collapses_to_canonical():
    assert slug_from_path("/Users/alien/Projects/agent-infra-wt1628") == "agent-infra"
    assert slug_from_path("/x/y/genomics-wt99") == "genomics"
    # location-independent: only the basename matters, so a worktree anywhere maps home
    assert slug_from_path("/anywhere/.worktrees/phenome-wt7") == "phenome"


def test_only_digit_suffix_stripped_no_false_positive():
    # a real repo whose name merely contains "wt" must NOT be collapsed
    assert slug_from_path("/x/y/foo-wtbar") == "foo-wtbar"
    assert slug_from_path("/x/y/swt") == "swt"
    assert slug_from_path("/x/y/widget") == "widget"


def test_none_and_empty():
    assert slug_from_path(None) is None
    assert slug_from_path("") is None
