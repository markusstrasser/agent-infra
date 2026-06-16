"""Tests for scripts/common/surface_gates.py"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from common.surface_gates import (
    CODEX_SKILLS_BUDGET_CHARS,
    FailureEnvelope,
    build_skills_budget,
    search_governance,
    sync_skill_symlinks,
    validate_closeout_dispatch,
)


class FailureEnvelopeTest(unittest.TestCase):
    def test_format_includes_fix_line(self) -> None:
        env = FailureEnvelope(check="t", reason="bad", fix="just doctor")
        text = env.format()
        self.assertIn("[t] BLOCKED — bad", text)
        self.assertIn("fix: just doctor", text)

    def test_to_payload_merges_extra(self) -> None:
        payload = FailureEnvelope("t", "r", "f").to_payload(error_type="X")
        self.assertTrue(payload["error"])
        self.assertEqual(payload["error_type"], "X")
        self.assertIn("envelope", payload)


class SkillsBudgetTest(unittest.TestCase):
    def test_detects_over_budget_mount(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "skills"
            big = root / "big"
            big.mkdir(parents=True)
            desc = "x" * (CODEX_SKILLS_BUDGET_CHARS + 100)
            (big / "SKILL.md").write_text(
                f"---\nname: big\ndescription: {desc}\n---\n",
                encoding="utf-8",
            )
            from common.surface_gates import measure_skill_mount

            mount = measure_skill_mount("test", root)
            self.assertGreater(mount.description_chars, CODEX_SKILLS_BUDGET_CHARS)


class DispatchLintTest(unittest.TestCase):
    def test_rejects_composer_on_design(self) -> None:
        data = {
            "artifact": "closeout",
            "layers": {
                "diff": {"owner": "code-review", "run": True},
                "design": {"owner": "critique", "run": True, "axes": "standard,composer"},
            },
            "blockers": [],
        }
        errs = validate_closeout_dispatch(data)
        self.assertTrue(any("composer" in e for e in errs))

    def test_accepts_valid_partition(self) -> None:
        data = {
            "artifact": "closeout",
            "layers": {
                "diff": {"owner": "code-review", "run": True},
                "design": {"owner": "critique", "run": True, "axes": "standard"},
            },
            "blockers": [],
        }
        self.assertEqual(validate_closeout_dispatch(data), [])


class SyncSkillsTest(unittest.TestCase):
    def test_mirror_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            dst = Path(tmp) / "dst"
            skill = src / "demo"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nname: demo\ndescription: test skill\n---\n",
                encoding="utf-8",
            )
            result = sync_skill_symlinks(src, dst)
            self.assertEqual(result["created"], 1)
            self.assertTrue((dst / "demo").is_symlink())


class DedupSearchTest(unittest.TestCase):
    def test_finds_substring_in_claude_md(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp)
            (proj / "CLAUDE.md").write_text(
                "Unique governance phrase about surface gates and budgets here.",
                encoding="utf-8",
            )
            hits = search_governance(
                "Unique governance phrase about surface gates",
                proj,
                min_needle_len=10,
            )
            self.assertTrue(hits)


if __name__ == "__main__":
    unittest.main()
