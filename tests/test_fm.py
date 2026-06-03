"""Unit tests for scripts/fm.py — the failure-mode taxonomy spine.

Hermetic: FM_FILE and EVIDENCE_LOG are monkeypatched onto temp paths so the real
agent-failure-modes.md and ~/.claude/fm-evidence.jsonl are never touched. No
network, no LLM.

Load-bearing tests:
  - the merge-before-mint guard (must REFUSE with exit 2 when <2 --merges, succeed >=2)
  - attach-evidence appends to the evidence log AND bumps evidence_count in markdown
  - list/show don't crash on empty/missing files
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import fm  # noqa: E402


# ── fixtures ─────────────────────────────────────────────────────────────────
SAMPLE_MD = """\
# Agent Failure Modes

Intro prose that should be ignored by the parser.

### Failure Mode 24: Blind Retry (No Diagnosis Between Attempts)
<!--
FM-ID: fm24-blind-retry
signature: >=3 same-tool calls with varied input and no user message between
target_surface: any dispatch loop; reflect_capture retry_run detector
status: active
evidence_count: 2
-->

Some body text describing FM24.

### Failure Mode 26: Confirmatory Fan-Out (N Workers, One Prior)
<!--
FM-ID: fm26-confirmatory-fanout
signature: dispatch prompt embeds the desired conclusion AND accept-rate >0.7
target_surface: intel re-underwrite dispatch; CONFIRMATORY_FANOUT analyst label
status: active
evidence_count: 0
-->

### Failure Mode 99: Retired Example
<!--
FM-ID: fm99-retired
signature: an example that has been retired
target_surface: nothing
status: retired
evidence_count: 5
-->
"""


@pytest.fixture()
def fm_env(tmp_path, monkeypatch):
    """Point fm at temp FM_FILE + EVIDENCE_LOG; return (fm_file, evidence_log).

    parse_blocks() reads the module global FM_FILE at call time, so rebinding
    fm.FM_FILE is sufficient for full hermeticity (the prior import-frozen
    default-arg trap was fixed in fm.py).
    """
    fm_file = tmp_path / "agent-failure-modes.md"
    fm_file.write_text(SAMPLE_MD, encoding="utf-8")
    evidence_log = tmp_path / "claude" / "fm-evidence.jsonl"
    monkeypatch.setattr(fm, "FM_FILE", fm_file)
    monkeypatch.setattr(fm, "EVIDENCE_LOG", evidence_log)
    return fm_file, evidence_log


def _args(**kw):
    """Minimal argparse.Namespace stand-in for the cmd_* handlers."""
    return types.SimpleNamespace(**kw)


# ── parse_blocks ─────────────────────────────────────────────────────────────
class TestParseBlocks:
    def test_parses_all_blocks_with_fields(self, fm_env):
        fm_file, _ = fm_env
        blocks = fm.parse_blocks(fm_file)
        assert len(blocks) == 3
        ids = {b["id"] for b in blocks}
        assert ids == {"fm24-blind-retry", "fm26-confirmatory-fanout", "fm99-retired"}

    def test_field_extraction_and_heading_association(self, fm_env):
        fm_file, _ = fm_env
        blocks = fm.parse_blocks(fm_file)
        b24 = next(b for b in blocks if b["id"] == "fm24-blind-retry")
        assert b24["heading"].startswith("Failure Mode 24")
        assert "varied input" in b24["signature"]
        assert b24["target_surface"].startswith("any dispatch loop")
        assert b24["status"] == "active"
        assert b24["evidence_count"] == 2  # int, not str
        assert isinstance(b24["evidence_count"], int)
        # line points at the FM-ID line (1-based)
        assert b24["line"] > 1

    def test_evidence_count_defaults_and_status_default(self, tmp_path, monkeypatch):
        # A block with no evidence_count / no status falls back to 0 / "active".
        md = tmp_path / "fm.md"
        md.write_text(
            "### Failure Mode 1: Bare\n<!--\nFM-ID: fm1-bare\n"
            "signature: minimal block\n-->\n",
            encoding="utf-8",
        )
        blocks = fm.parse_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["evidence_count"] == 0
        assert blocks[0]["status"] == "active"
        assert blocks[0]["target_surface"] == ""

    def test_missing_file_returns_empty_list(self, tmp_path):
        assert fm.parse_blocks(tmp_path / "does-not-exist.md") == []

    def test_empty_file_returns_empty_list(self, tmp_path):
        empty = tmp_path / "empty.md"
        empty.write_text("", encoding="utf-8")
        assert fm.parse_blocks(empty) == []

    def test_file_without_fmid_blocks_returns_empty(self, tmp_path):
        plain = tmp_path / "plain.md"
        plain.write_text("# Title\n\nJust prose, no FM-ID anywhere.\n", encoding="utf-8")
        assert fm.parse_blocks(plain) == []


# ── _find ────────────────────────────────────────────────────────────────────
class TestFind:
    def test_find_hit(self, fm_env):
        blocks = fm.parse_blocks(fm_env[0])
        b = fm._find(blocks, "fm26-confirmatory-fanout")
        assert b is not None
        assert b["id"] == "fm26-confirmatory-fanout"

    def test_find_miss_returns_none(self, fm_env):
        blocks = fm.parse_blocks(fm_env[0])
        assert fm._find(blocks, "fm-nonexistent") is None

    def test_find_on_empty_list(self):
        assert fm._find([], "anything") is None


# ── merge-before-mint guard (review finding #1) ──────────────────────────────
class TestMintGuard:
    def test_refuses_with_zero_merges(self, fm_env, capsys):
        rc = fm.cmd_mint(_args(slug="fmX", signature="s", target_surface="t", merges=""))
        assert rc == 2
        out = capsys.readouterr().out
        assert "merge-before-mint" in out

    def test_refuses_with_one_merge(self, fm_env):
        rc = fm.cmd_mint(
            _args(slug="fmX", signature="s", target_surface="t", merges="fm24-blind-retry")
        )
        assert rc == 2

    def test_refuses_when_merges_is_none(self, fm_env):
        # args.merges defaults to "" in argparse, but guard must tolerate None too.
        rc = fm.cmd_mint(_args(slug="fmX", signature="s", target_surface="t", merges=None))
        assert rc == 2

    def test_succeeds_with_two_merges(self, fm_env, capsys):
        rc = fm.cmd_mint(
            _args(
                slug="fm30-merged",
                signature="merged signature",
                target_surface="some surface",
                merges="fm24-blind-retry,fm26-confirmatory-fanout",
            )
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert "merge-before-mint OK" in out
        assert "2 classes merged" in out
        # It prints a paste-ready block, but must NOT mutate the FM file.
        assert "FM-ID: fm30-merged" in out
        assert "fm30-merged" not in fm_env[0].read_text()

    def test_three_merges_with_whitespace_and_blanks(self, fm_env, capsys):
        # Splitting must strip whitespace and drop empty segments.
        rc = fm.cmd_mint(
            _args(
                slug="fm31",
                signature="s",
                target_surface="t",
                merges=" fm24-blind-retry , , fm26-confirmatory-fanout , fm99-retired ",
            )
        )
        assert rc == 0
        assert "3 classes merged" in capsys.readouterr().out

    def test_two_commas_one_real_id_still_refuses(self, fm_env):
        # ",," is two empty segments → 0 real merges → refuse.
        rc = fm.cmd_mint(_args(slug="fmX", signature="s", target_surface="t", merges=",,"))
        assert rc == 2


# ── attach-evidence ──────────────────────────────────────────────────────────
class TestAttachEvidence:
    def test_appends_row_and_bumps_count(self, fm_env, capsys):
        fm_file, evidence_log = fm_env
        before = fm._find(fm.parse_blocks(fm_file), "fm24-blind-retry")["evidence_count"]
        assert before == 2

        rc = fm.cmd_attach(
            _args(id="fm24-blind-retry", session="sess-abc", quote="observed a blind retry run")
        )
        assert rc == 0

        # Evidence log got exactly one JSONL row with the right shape.
        assert evidence_log.exists()
        rows = [json.loads(l) for l in evidence_log.read_text().splitlines() if l.strip()]
        assert len(rows) == 1
        assert rows[0]["fm_id"] == "fm24-blind-retry"
        assert rows[0]["session"] == "sess-abc"
        assert rows[0]["quote"] == "observed a blind retry run"
        assert "ts" in rows[0] and rows[0]["ts"]  # ISO timestamp present

        # evidence_count bumped 2 -> 3 in the markdown.
        after = fm._find(fm.parse_blocks(fm_file), "fm24-blind-retry")["evidence_count"]
        assert after == 3
        assert "✓" in capsys.readouterr().out

    def test_bump_only_affects_target_block(self, fm_env):
        fm_file, _ = fm_env
        fm.cmd_attach(_args(id="fm26-confirmatory-fanout", session="s1", quote="q"))
        blocks = {b["id"]: b for b in fm.parse_blocks(fm_file)}
        assert blocks["fm26-confirmatory-fanout"]["evidence_count"] == 1  # 0 -> 1
        assert blocks["fm24-blind-retry"]["evidence_count"] == 2  # untouched
        assert blocks["fm99-retired"]["evidence_count"] == 5  # untouched

    def test_two_attaches_accumulate(self, fm_env):
        fm_file, evidence_log = fm_env
        fm.cmd_attach(_args(id="fm26-confirmatory-fanout", session="s1", quote="first"))
        fm.cmd_attach(_args(id="fm26-confirmatory-fanout", session="s2", quote="second"))
        rows = [json.loads(l) for l in evidence_log.read_text().splitlines() if l.strip()]
        assert len(rows) == 2
        count = fm._find(fm.parse_blocks(fm_file), "fm26-confirmatory-fanout")["evidence_count"]
        assert count == 2  # 0 -> 1 -> 2

    def test_unknown_id_refuses_and_writes_nothing(self, fm_env):
        fm_file, evidence_log = fm_env
        rc = fm.cmd_attach(_args(id="fm-bogus", session="s", quote="q"))
        assert rc == 1
        assert not evidence_log.exists()  # no log row created
        # FM file untouched.
        assert "fm-bogus" not in fm_file.read_text()

    def test_bump_count_directly_returns_true_on_hit(self, fm_env):
        assert fm._bump_count("fm24-blind-retry", 1) is True
        count = fm._find(fm.parse_blocks(fm_env[0]), "fm24-blind-retry")["evidence_count"]
        assert count == 3

    def test_bump_count_returns_false_on_miss(self, fm_env):
        assert fm._bump_count("fm-not-here", 1) is False


# ── list / show robustness ───────────────────────────────────────────────────
class TestListShow:
    def test_list_populated(self, fm_env, capsys):
        rc = fm.cmd_list(_args())
        assert rc == 0
        out = capsys.readouterr().out
        assert "fm24-blind-retry" in out
        assert "fm26-confirmatory-fanout" in out

    def test_list_empty_does_not_crash(self, tmp_path, monkeypatch, capsys):
        empty = tmp_path / "empty.md"
        empty.write_text("", encoding="utf-8")
        monkeypatch.setattr(fm, "FM_FILE", empty)
        rc = fm.cmd_list(_args())
        assert rc == 0
        assert "no FM-ID blocks found" in capsys.readouterr().out

    def test_list_missing_file_does_not_crash(self, tmp_path, monkeypatch, capsys):
        missing = tmp_path / "nope.md"
        monkeypatch.setattr(fm, "FM_FILE", missing)
        rc = fm.cmd_list(_args())
        assert rc == 0
        assert "no FM-ID blocks found" in capsys.readouterr().out

    def test_show_known_id_with_no_evidence_log(self, fm_env, capsys):
        # EVIDENCE_LOG does not exist yet → show must not crash.
        _, evidence_log = fm_env
        assert not evidence_log.exists()
        rc = fm.cmd_show(_args(id="fm24-blind-retry"))
        assert rc == 0
        out = capsys.readouterr().out
        assert "fm24-blind-retry" in out
        assert "signature:" in out

    def test_show_unknown_id_returns_1(self, fm_env, capsys):
        rc = fm.cmd_show(_args(id="fm-missing"))
        assert rc == 1
        assert "unknown FM-ID" in capsys.readouterr().out

    def test_show_renders_recent_evidence(self, fm_env, capsys):
        # Attach two rows, then show should print the recent-evidence section.
        fm.cmd_attach(_args(id="fm24-blind-retry", session="sX", quote="a noteworthy quote"))
        capsys.readouterr()  # drop attach output
        rc = fm.cmd_show(_args(id="fm24-blind-retry"))
        assert rc == 0
        out = capsys.readouterr().out
        assert "recent evidence" in out
        assert "a noteworthy quote" in out

    def test_show_ignores_evidence_for_other_ids(self, fm_env, capsys):
        # Evidence rows for a DIFFERENT fm_id must not appear under this one.
        fm.cmd_attach(_args(id="fm26-confirmatory-fanout", session="sY", quote="other-fm quote"))
        capsys.readouterr()
        fm.cmd_show(_args(id="fm24-blind-retry"))
        out = capsys.readouterr().out
        assert "other-fm quote" not in out


# ── main() dispatch via argparse ─────────────────────────────────────────────
class TestMain:
    def test_main_mint_refuses_exit_2(self, fm_env, monkeypatch):
        monkeypatch.setattr(
            sys, "argv",
            ["fm.py", "mint", "fmZ", "--signature", "s", "--target-surface", "t"],
        )
        assert fm.main() == 2

    def test_main_list_runs(self, fm_env, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["fm.py", "list"])
        assert fm.main() == 0
        assert "fm24-blind-retry" in capsys.readouterr().out

    def test_main_attach_then_count_bumped(self, fm_env, monkeypatch):
        monkeypatch.setattr(
            sys, "argv",
            ["fm.py", "attach-evidence", "fm99-retired", "--session", "s9", "--quote", "q9"],
        )
        assert fm.main() == 0
        count = fm._find(fm.parse_blocks(fm_env[0]), "fm99-retired")["evidence_count"]
        assert count == 6  # 5 -> 6


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
