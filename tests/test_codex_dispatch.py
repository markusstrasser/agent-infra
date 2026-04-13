from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "codex_dispatch.py"


def load_module():
    spec = importlib.util.spec_from_file_location("codex_dispatch", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class CodexDispatchTest(unittest.TestCase):
    def test_default_log_dir_uses_archive_root_for_nested_audit_output(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            output_dir = repo_root / "docs" / "audit" / "dispatch-2026-04-02"
            expected = (repo_root / "docs" / "archive" / "audit-logs" / "dispatch-2026-04-02").resolve()

            self.assertEqual(module.default_log_dir(output_dir), expected)

    def test_default_log_dir_stamps_audit_root_runs(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            output_dir = repo_root / "docs" / "audit"
            expected = (repo_root / "docs" / "archive" / "audit-logs" / "dispatch-2026-04-02-010203").resolve()

            with patch.object(module.time, "strftime", return_value="dispatch-2026-04-02-010203"):
                self.assertEqual(module.default_log_dir(output_dir), expected)

    def test_dispatch_writes_raw_logs_to_archive_by_default(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            output_dir = repo_root / "docs" / "audit" / "dispatch-2026-04-02"
            popen_calls: list[dict[str, object]] = []

            class FakePopen:
                def __init__(self, cmd, env, stdout, stderr):
                    popen_calls.append(
                        {
                            "cmd": cmd,
                            "env": env,
                            "stdout": Path(stdout.name),
                            "stderr": Path(stderr.name),
                        }
                    )
                    self.pid = 4242

                def poll(self):
                    return None

            with patch.object(module.subprocess, "Popen", FakePopen):
                results = module.dispatch(
                    [{"name": "lint-adjacent", "prompt": "Audit the repo"}],
                    output_dir,
                    max_parallel=1,
                )

            expected_log_dir = (repo_root / "docs" / "archive" / "audit-logs" / "dispatch-2026-04-02").resolve()
            self.assertEqual(results[0]["stdout_log"], str(expected_log_dir / "lint-adjacent.stdout.log"))
            self.assertEqual(results[0]["stderr_log"], str(expected_log_dir / "lint-adjacent.stderr.log"))
            self.assertEqual(popen_calls[0]["stdout"], expected_log_dir / "lint-adjacent.stdout.log")
            self.assertEqual(popen_calls[0]["stderr"], expected_log_dir / "lint-adjacent.stderr.log")


if __name__ == "__main__":
    unittest.main()
