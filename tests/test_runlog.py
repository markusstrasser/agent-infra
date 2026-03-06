from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNLOG = REPO_ROOT / "scripts" / "runlog.py"


class RunlogFixtureImportTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "runlogs.db"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(RUNLOG), "--db", str(self.db_path), *args],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            capture_output=True,
        )

    def test_fixture_import_and_idempotence(self) -> None:
        init_result = self.run_cli("init-db")
        self.assertEqual(init_result.returncode, 0, init_result.stderr)

        import_result = self.run_cli("import", "--fixtures")
        self.assertEqual(import_result.returncode, 0, import_result.stderr)
        summary = json.loads(import_result.stdout)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(summary["imported"], 11)

        rerun_result = self.run_cli("import", "--fixtures")
        self.assertEqual(rerun_result.returncode, 0, rerun_result.stderr)
        rerun_summary = json.loads(rerun_result.stdout)
        self.assertEqual(rerun_summary["failed"], 0)
        self.assertEqual(rerun_summary["skipped"], 11)

    def test_named_queries_return_rows(self) -> None:
        self.run_cli("init-db")
        self.run_cli("import", "--fixtures")

        supervision = self.run_cli("query", "supervision_ratio_by_vendor_week", "--format", "json")
        self.assertEqual(supervision.returncode, 0, supervision.stderr)
        supervision_rows = json.loads(supervision.stdout)
        self.assertTrue(any(row["vendor"] == "kimi" for row in supervision_rows))

        touches = self.run_cli(
            "query",
            "runs_touching_path",
            "--param",
            "path_like=%runlog%",
            "--format",
            "json",
        )
        self.assertEqual(touches.returncode, 0, touches.stderr)
        touch_rows = json.loads(touches.stdout)
        self.assertGreaterEqual(len(touch_rows), 1)

        edges = self.run_cli(
            "query",
            "run_edges_over_time",
            "--param",
            "vendor=codex",
            "--format",
            "json",
        )
        self.assertEqual(edges.returncode, 0, edges.stderr)
        edge_rows = json.loads(edges.stdout)
        self.assertTrue(any(row["edge_type"] == "spawned_by" for row in edge_rows))


if __name__ == "__main__":
    unittest.main()
