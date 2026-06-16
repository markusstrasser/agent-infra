from __future__ import annotations

import importlib.util
import json
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


def test_shim_wrap_is_idempotent_and_carries_event() -> None:
    module = load_module()
    wrapped = module.shim_wrap("/abs/path/hook.sh --flag", "Stop")
    assert wrapped.startswith("CODEX_HOOK_EVENT=Stop python3 ")
    assert "codex_hook_shim.py" in wrapped
    assert module.shim_wrap(wrapped, "Stop") == wrapped  # idempotent


def test_sync_global_codex_agents_links_to_claude_md(tmp_path: Path, monkeypatch) -> None:
    module = load_module()
    claude_md = tmp_path / "claude" / "CLAUDE.md"
    codex_dir = tmp_path / "codex"
    agents_md = codex_dir / "AGENTS.md"
    claude_md.parent.mkdir(parents=True)
    claude_md.write_text("# global rules\n")
    codex_dir.mkdir()
    agents_md.write_text("# stale standalone copy\n")

    monkeypatch.setattr(module, "GLOBAL_CLAUDE_MD", claude_md)
    monkeypatch.setattr(module, "GLOBAL_CODEX_AGENTS", agents_md)

    check = module.sync_global_codex_agents(check=True)
    assert check["would_update"] is True
    assert check["linked"] is False
    assert agents_md.read_text().startswith("# stale")

    applied = module.sync_global_codex_agents(check=False)
    assert applied["linked"] is True
    assert agents_md.is_symlink()
    assert agents_md.resolve() == claude_md.resolve()
    assert agents_md.read_text() == claude_md.read_text()
    assert (codex_dir / "AGENTS.md.prewrap.bak").exists()

    again = module.sync_global_codex_agents(check=False)
    assert again["linked"] is True and again["would_update"] is False


def test_sync_global_codex_hooks_wraps_and_backs_up(tmp_path: Path, monkeypatch) -> None:
    module = load_module()
    hooks_file = tmp_path / "hooks.json"
    hooks_file.write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {"matcher": "Bash", "hooks": [{"type": "command", "command": "/abs/guard.sh"}]}
                    ]
                }
            }
        )
    )
    monkeypatch.setattr(module, "GLOBAL_CODEX_HOOKS", hooks_file)

    # check mode writes nothing
    res = module.sync_global_codex_hooks(check=True)
    assert res["wrapped"] == 1 and res["would_update"] is True
    assert "codex_hook_shim" not in hooks_file.read_text()

    # apply mode wraps + backs up + is idempotent
    res = module.sync_global_codex_hooks(check=False)
    assert res["wrapped"] == 1
    assert "codex_hook_shim" in hooks_file.read_text()
    assert hooks_file.with_suffix(".json.prewrap.bak").exists()
    again = module.sync_global_codex_hooks(check=False)
    assert again["wrapped"] == 0 and again["would_update"] is False


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


def test_stale_hook_scripts_flags_missing_absolute(tmp_path: Path) -> None:
    module = load_module()
    gone = tmp_path / "hooks" / "deleted-hook.sh"  # never created
    shim = str(module.CODEX_HOOK_SHIM)

    # bare absolute path to a missing hook script → flagged
    assert module.stale_hook_scripts(str(gone)) == [str(gone)]
    # shim-wrapped form (the real on-disk shape) → flagged once, not duplicated
    wrapped = f"CODEX_HOOK_EVENT=PreToolUse python3 {shim} {gone}"
    assert module.stale_hook_scripts(wrapped) == [str(gone)]


def test_stale_hook_scripts_ignores_live_relative_and_shim(tmp_path: Path) -> None:
    module = load_module()
    live = tmp_path / "hooks" / "live-hook.sh"
    live.parent.mkdir(parents=True)
    live.write_text("#!/bin/bash\nexit 0\n")
    shim = str(module.CODEX_HOOK_SHIM)

    # existing script → not flagged
    assert module.stale_hook_scripts(f"python3 {shim} {live}") == []
    # relative path (cwd-dependent) → never flagged
    assert module.stale_hook_scripts("cd /repo && uv run python3 scripts/x.py") == []
    # the shim itself is plumbing, not a hook script → never flagged
    assert module.stale_hook_scripts(shim) == []


def test_sync_global_codex_hooks_prunes_stale(tmp_path: Path, monkeypatch) -> None:
    module = load_module()
    live = tmp_path / "hooks" / "live.sh"
    live.parent.mkdir(parents=True)
    live.write_text("#!/bin/bash\nexit 0\n")
    gone = tmp_path / "hooks" / "gone.sh"  # never created
    hooks_file = tmp_path / "hooks.json"
    hooks_file.write_text(json.dumps({
        "hooks": {
            "PreToolUse": [
                {"hooks": [
                    {"type": "command", "command": str(live)},
                    {"type": "command", "command": str(gone)},
                ]},
                {"hooks": [{"type": "command", "command": str(gone)}]},  # becomes empty
            ]
        }
    }))
    monkeypatch.setattr(module, "GLOBAL_CODEX_HOOKS", hooks_file)

    result = module.sync_global_codex_hooks(check=False)
    assert result["pruned"] == 2
    assert result["stale"] == [str(gone), str(gone)]

    data = json.loads(hooks_file.read_text())
    groups = data["hooks"]["PreToolUse"]
    assert len(groups) == 1  # the all-stale group was dropped
    remaining = [h["command"] for g in groups for h in g["hooks"]]
    assert len(remaining) == 1
    assert str(gone) not in remaining[0]
    assert "codex_hook_shim" in remaining[0]  # live one got shim-wrapped
