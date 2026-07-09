"""Tests for scan_tool_failures shell-env classification."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

SKILL = Path.home() / "Projects" / "skills" / "observe" / "scripts" / "scan_tool_failures.py"
spec = importlib.util.spec_from_file_location("scan_tool_failures", SKILL)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)
classify = mod.classify


class TestScanToolFailuresShellEnv(unittest.TestCase):
    def test_zsh_nomatch(self):
        key, _ = classify("Exit code 1\n(eval):1: no matches found: *.md")
        self.assertEqual(key, "zsh-env:nomatch")

    def test_zsh_alias_collision(self):
        key, _ = classify("(eval):2: defining function based on alias `t'\nparse error near `()'")
        self.assertEqual(key, "zsh-env:alias-collision")

    def test_zsh_parse_error(self):
        key, _ = classify("Exit code 1\n(eval):2: parse error near `()'")
        self.assertEqual(key, "zsh-env:parse-error")

    def test_skips_pretool_hook_block(self):
        text = (
            "PreToolUse:Bash hook error: [/hooks/pretool-bash-loop-guard.sh]: "
            "BLOCKED: Multiline for/while/if blocks cause zsh parse errors."
        )
        self.assertIsNone(classify(text))

    def test_import_still_works(self):
        text = "Traceback (most recent call last):\n  ...\nModuleNotFoundError: No module named 'duckdb'"
        key, _ = classify(text)
        self.assertEqual(key, "missing-module:duckdb")


if __name__ == "__main__":
    unittest.main()
