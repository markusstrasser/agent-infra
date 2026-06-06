from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "codex_hook_compat.py"


def load_module():
    spec = importlib.util.spec_from_file_location("codex_hook_compat", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class CodexHookCompatTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def ref(self, event: str = "SessionStart", command: str = "true"):
        return self.module.HookRef(
            source="hooks.json",
            event=event,
            matcher="<all>",
            index=0,
            command=command,
        )

    def test_invalid_stdout_json_fails_for_codex_parsed_events(self) -> None:
        result = self.module.classify_result(
            "repo",
            self.ref("SessionStart"),
            0,
            "plain advisory text\n",
            "",
        )
        self.assertEqual(result.status, "fail")
        self.assertIn("not a JSON object", result.problem)

    def test_valid_json_stdout_passes(self) -> None:
        result = self.module.classify_result(
            "repo",
            self.ref("PostToolUse"),
            0,
            '{"additionalContext":"ok"}\n',
            "",
        )
        self.assertEqual(result.status, "pass")

    def test_exit_64_fails_on_smoke_input(self) -> None:
        result = self.module.classify_result("repo", self.ref("PreToolUse"), 64, "", "usage")
        self.assertEqual(result.status, "fail")
        self.assertIn("unexpected exit 64", result.problem)

    def test_exit_2_with_block_message_is_preserved(self) -> None:
        result = self.module.classify_result(
            "repo",
            self.ref("PreToolUse"),
            2,
            "",
            "BLOCKED: protected path",
        )
        self.assertEqual(result.status, "intentional_block")

    def test_exit_2_without_block_message_fails(self) -> None:
        result = self.module.classify_result("repo", self.ref("PreToolUse"), 2, "", "usage")
        self.assertEqual(result.status, "fail")
        self.assertIn("unexpected exit 2", result.problem)

    def test_run_hook_sets_codex_smoke_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "hook.py"
            script.write_text(
                "\n".join(
                    [
                        "#!/usr/bin/env python3",
                        "import json, os, sys",
                        "payload=json.loads(sys.stdin.read())",
                        "assert os.environ['CODEX_HOOK_COMPAT_SMOKE'] == '1'",
                        "assert os.environ['CLAUDE_PROJECT_DIR']",
                        "assert payload['hook_event_name'] == 'PostToolUse'",
                        "print(json.dumps({'additionalContext':'ok'}))",
                    ]
                ),
                encoding="utf-8",
            )
            os.chmod(script, 0o755)
            result = self.module.run_hook(
                "repo",
                root,
                self.ref("PostToolUse", str(script)),
                timeout=5,
            )
            self.assertEqual(result.status, "pass")

    def test_load_hooks_extracts_command_hooks_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hooks_path = Path(tmp) / "hooks.json"
            hooks_path.write_text(
                json.dumps(
                    {
                        "hooks": {
                            "SessionStart": [
                                {
                                    "hooks": [
                                        {"type": "command", "command": "echo '{}'"},
                                        {"type": "prompt", "prompt": "skip"},
                                    ]
                                }
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )
            refs = self.module.load_hooks(hooks_path)
            self.assertEqual(len(refs), 1)
            self.assertEqual(refs[0].command, "echo '{}'")


if __name__ == "__main__":
    unittest.main()
