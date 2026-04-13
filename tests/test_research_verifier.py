from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "research_verifier.py"


def load_module():
    spec = importlib.util.spec_from_file_location("research_verifier", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ResearchVerifierTest(unittest.TestCase):
    def test_build_artifact_splits_verified_and_followup_claims(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            memo = Path(tmp) / "memo.md"
            memo.write_text(
                "\n".join(
                    [
                        "# Memo",
                        "",
                        "### Claims Table",
                        "",
                        "| # | Claim | Evidence | Confidence | Source | Status |",
                        "|---|-------|----------|------------|--------|--------|",
                        "| 1 | Verified claim | paper | HIGH | [SOURCE: https://example.com/a] | VERIFIED |",
                        "| 2 | Frontier claim | preprint | MEDIUM | [SOURCE: https://example.com/b] | FRONTIER |",
                        "",
                        "[INFERENCE]",
                    ]
                ),
                encoding="utf-8",
            )

            artifact = module.build_artifact(memo)
            rendered = module.render_artifact(artifact)

            self.assertEqual(artifact.total_claims, 2)
            self.assertEqual(len(artifact.verified_claims), 1)
            self.assertEqual(len(artifact.followup_claims), 1)
            self.assertIn("https://example.com/a", artifact.source_inventory)
            self.assertIn("https://example.com/b", artifact.source_inventory)
            self.assertIn("Follow-Up Candidates", rendered)


if __name__ == "__main__":
    unittest.main()
