"""slug_from_path / canonicalize_project_slug — worktree + llmx-cache canonicalization.

Attribution for llmx cache cwds: prefer `.llmx-caller-cwd` marker in the cache
dir (per-caller subdirs), sidecar fallback with TTL. NEVER indexer os.environ
(Opus 2026-07-12 REJECT → FIX-THEN-LAND).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from agentlogs.adapters import common as common_mod
from agentlogs.adapters.common import canonicalize_project_slug, slug_from_path


def test_canonical_repo_slug_unchanged():
    assert slug_from_path("/Users/alien/Projects/agent-infra") == "agent-infra"
    assert slug_from_path("/Users/alien/Projects/genomics") == "genomics"


def test_worktree_suffix_collapses_to_canonical():
    assert slug_from_path("/Users/alien/Projects/agent-infra-wt1628") == "agent-infra"
    assert slug_from_path("/x/y/genomics-wt99") == "genomics"
    assert slug_from_path("/anywhere/.worktrees/phenome-wt7") == "phenome"


def test_claude_worktree_dir_collapses():
    assert (
        slug_from_path(
            "/Users/alien/Projects/arc-agi--claude-worktrees-sorted-jumping-parnas"
        )
        == "arc-agi"
    )
    assert (
        canonicalize_project_slug("arc-agi--claude-worktrees-sorted-jumping-parnas")
        == "arc-agi"
    )


def test_only_digit_suffix_stripped_no_false_positive():
    assert slug_from_path("/x/y/foo-wtbar") == "foo-wtbar"
    assert slug_from_path("/x/y/swt") == "swt"


def test_llmx_cache_marker_file(tmp_path, monkeypatch):
    monkeypatch.delenv("AGENTLOGS_PROJECT", raising=False)
    monkeypatch.delenv("LLMX_CALLER_CWD", raising=False)
    cache = tmp_path / ".cache" / "llmx" / "cursor" / "abc123"
    cache.mkdir(parents=True)
    (cache / ".llmx-caller-cwd").write_text(
        str(tmp_path / "Projects" / "arc-agi") + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(common_mod, "_LLMX_ATTRIBUTION", tmp_path / "missing.jsonl")
    assert slug_from_path(str(cache)) == "arc-agi"


def test_llmx_sidecar_ttl_and_clean_env(tmp_path, monkeypatch):
    monkeypatch.delenv("AGENTLOGS_PROJECT", raising=False)
    monkeypatch.delenv("LLMX_CALLER_CWD", raising=False)
    cache = tmp_path / ".cache" / "llmx" / "cursor" / "def456"
    cache.mkdir(parents=True)
    attr = tmp_path / "dispatch-attribution.jsonl"
    caller = tmp_path / "Projects" / "genomics"
    caller.mkdir(parents=True)
    old = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    fresh = datetime.now(timezone.utc).isoformat()
    attr.write_text(
        json.dumps(
            {
                "ts": old,
                "cli_cwd": str(cache.resolve()),
                "caller_cwd": str((tmp_path / "Projects" / "stale").resolve()),
                "pid": 1,
            }
        )
        + "\n"
        + json.dumps(
            {
                "ts": fresh,
                "cli_cwd": str(cache.resolve()),
                "caller_cwd": str(caller.resolve()),
                "pid": 2,
            }
        )
        + "\n"
        + "{truncated\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(common_mod, "_LLMX_ATTRIBUTION", attr)
    assert slug_from_path(str(cache)) == "genomics"


def test_encoded_cache_dirname_refused():
    assert canonicalize_project_slug("Users-alien--cache-llmx-lite-bare") is None
    assert slug_from_path("/tmp/Users-alien--cache-llmx-cursor") is None


def test_none_and_empty():
    assert slug_from_path(None) is None
    assert slug_from_path("") is None
