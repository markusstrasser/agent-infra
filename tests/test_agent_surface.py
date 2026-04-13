from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "agent_surface.py"


def load_module():
    spec = importlib.util.spec_from_file_location("agent_surface", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class AgentSurfaceTest(unittest.TestCase):
    def test_build_report_counts_root_skills_and_mcp_surface(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            project_root = tmp_path / "meta"
            project_root.mkdir()
            claude = project_root / "CLAUDE.md"
            claude.write_text("A" * 800, encoding="utf-8")
            os.symlink("CLAUDE.md", project_root / "AGENTS.md")

            mcp_project = tmp_path / "fake-mcp"
            mcp_project.mkdir()
            (mcp_project / "pyproject.toml").write_text(
                "\n".join(
                    [
                        "[project]",
                        "name = 'fake-mcp'",
                        "version = '0.1.0'",
                        "[project.scripts]",
                        "fake-mcp = 'server:main'",
                    ]
                ),
                encoding="utf-8",
            )
            (mcp_project / "server.py").write_text(
                "\n".join(
                    [
                        "from fastmcp import FastMCP",
                        "mcp = FastMCP('fake')",
                        "@mcp.tool()",
                        "def alpha():",
                        '    """alpha tool"""',
                        "    return {}",
                        "@mcp.tool()",
                        "async def beta():",
                        '    """beta tool"""',
                        "    return {}",
                    ]
                ),
                encoding="utf-8",
            )

            mcp_config = {
                "mcpServers": {
                    "exa": {
                        "type": "http",
                        "url": "https://example.com/mcp?tools=web_search_exa,crawling_exa",
                    },
                    "fake": {
                        "command": "uv",
                        "args": ["run", "--directory", str(mcp_project), "fake-mcp"],
                    },
                }
            }
            (project_root / ".mcp.json").write_text(json.dumps(mcp_config), encoding="utf-8")

            skills_dir = tmp_path / "skills"
            good_skill = skills_dir / "good"
            good_skill.mkdir(parents=True)
            (good_skill / "references").mkdir()
            (good_skill / "references" / "tooling.md").write_text("reference text", encoding="utf-8")
            (good_skill / "SKILL.md").write_text(
                "\n".join(
                    [
                        "---",
                        "name: good",
                        "description: Analyze MCP usage. Not for broad product strategy or legal review.",
                        "---",
                        "",
                        "Use when narrowing tool surface.",
                        "Read references/tooling.md for details.",
                    ]
                ),
                encoding="utf-8",
            )

            big_skill = skills_dir / "big"
            big_skill.mkdir(parents=True)
            (big_skill / "SKILL.md").write_text(
                "\n".join(
                    [
                        "---",
                        "name: big",
                        "description: Big skill",
                        "---",
                        "",
                        "x" * 22000,
                    ]
                ),
                encoding="utf-8",
            )

            module.RUNLOGS_DB = tmp_path / "missing-runlogs.db"
            report = module.build_report(project_root, skills_dir, days=30, top=5)

            self.assertEqual(len(report["root_files"]), 1)  # AGENTS symlink deduped
            self.assertEqual(report["summary"]["skill_status_counts"]["oversized"], 1)
            fake_server = next(row for row in report["mcp_servers"] if row["name"] == "fake")
            exa_server = next(row for row in report["mcp_servers"] if row["name"] == "exa")
            self.assertEqual(fake_server["tool_count"], 2)
            self.assertEqual(fake_server["schema_source"], "source-scan")
            self.assertEqual(exa_server["tool_count"], 2)
            self.assertEqual(exa_server["schema_source"], "http-query")
            self.assertTrue(any(item["kind"] == "mcp-schema" for item in report["top_always_exposed"]))


if __name__ == "__main__":
    unittest.main()
