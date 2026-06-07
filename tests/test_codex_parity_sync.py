from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "codex_parity_sync.py"


def load_module():
    spec = importlib.util.spec_from_file_location("codex_parity_sync", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_generated_hook_commands_route_through_shim(tmp_path: Path) -> None:
    module = load_module()
    transformed = module.transform_hooks(
        {
            "SessionStart": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python3 .claude/hooks/session-start.py",
                        }
                    ]
                }
            ]
        },
        tmp_path,
    )

    command = transformed["SessionStart"][0]["hooks"][0]["command"]
    assert command.startswith("CODEX_HOOK_EVENT=SessionStart python3 ")
    assert "codex_hook_shim.py" in command
    assert str(tmp_path / ".claude/hooks/session-start.py") in command


def test_generated_hook_commands_do_not_double_wrap(tmp_path: Path) -> None:
    module = load_module()
    once = module.codex_hook_command("scripts/hooks/x.sh", tmp_path, "PreToolUse")
    twice = module.codex_hook_command(once, tmp_path, "PreToolUse")

    assert twice == once
    assert once.count("codex_hook_shim") == 1


def test_env_placeholders_emit_as_codex_env_vars_not_plaintext() -> None:
    module = load_module()
    text = module.emit_mcp_toml(
        {
            "research": {
                "command": "uv",
                "args": ["run", "research-mcp"],
                "env": {
                    "S2_API_KEY": "${S2_API_KEY}",
                    "STATIC_FLAG": "1",
                },
            }
        }
    )

    assert 'env_vars = ["S2_API_KEY"]' in text
    assert '${S2_API_KEY}' not in text
    assert "S2_API_KEY =" not in text
    assert 'STATIC_FLAG = "1"' in text


def test_missing_env_placeholder_server_is_not_emitted(monkeypatch, tmp_path: Path) -> None:
    module = load_module()
    (tmp_path / ".mcp.json").write_text(
        """
        {
          "mcpServers": {
            "fmp": {
              "command": "npx",
              "args": ["-y", "@houtini/fmp-mcp"],
              "env": {"FMP_API_KEY": "${FMP_API_KEY}"}
            }
          }
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "load_global_mcp", lambda: {})

    monkeypatch.delenv("FMP_API_KEY", raising=False)
    monkeypatch.setattr(module, "keychain_has_secret", lambda env_var: False)
    emit, drift = module.compute_mcp_delta("fixture", tmp_path)
    assert "fmp" not in emit
    assert any("FMP_API_KEY" in note and "skipped" in note for note in drift)

    monkeypatch.setenv("FMP_API_KEY", "present")
    emit, drift = module.compute_mcp_delta("fixture", tmp_path)
    assert "fmp" in emit
    assert not drift


def test_missing_env_placeholder_uses_keychain_wrapper(monkeypatch, tmp_path: Path) -> None:
    module = load_module()
    (tmp_path / ".mcp.json").write_text(
        """
        {
          "mcpServers": {
            "fmp": {
              "command": "npx",
              "args": ["-y", "@houtini/fmp-mcp"],
              "env": {"FMP_API_KEY": "${FMP_API_KEY}"}
            }
          }
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "load_global_mcp", lambda: {})
    monkeypatch.setattr(module, "keychain_has_secret", lambda env_var: env_var == "FMP_API_KEY")
    monkeypatch.delenv("FMP_API_KEY", raising=False)

    emit, drift = module.compute_mcp_delta("fixture", tmp_path)
    assert emit["fmp"]["command"] == "zsh"
    assert "security find-generic-password" in emit["fmp"]["args"][1]
    assert "FMP_API_KEY" not in emit["fmp"].get("env", {})
    assert any("Keychain fallback" in note for note in drift)
