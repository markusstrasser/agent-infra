"""The Codex MCP mirror must track REMOVALS, not only additions.

2026-09-02: after 27 zero-call MCP servers were removed from repo .mcp.json files,
`just codex-parity` reported `mcp+0` for arc-agi and left `.codex/config.toml`
declaring `brave-search` — Codex kept launching a server Claude no longer had.
"""

from pathlib import Path

import codex_parity_sync as cps  # scripts/ is on sys.path via conftest

STDIO = {"command": "uvx", "args": ["some-server"]}


def test_empty_delta_removes_stale_mirror(tmp_path: Path) -> None:
    cfg = tmp_path / ".codex" / "config.toml"
    cfg.parent.mkdir()
    cfg.write_text(cps.emit_mcp_toml({"brave-search": STDIO}))

    state, changed = cps.reconcile_mcp_config(cfg, {}, check=True)
    assert (state, changed) == ("WOULD REMOVE stale mirror", True)
    assert cfg.exists(), "check mode must not mutate"

    state, changed = cps.reconcile_mcp_config(cfg, {}, check=False)
    assert (state, changed) == ("stale mirror removed", True)
    assert not cfg.exists()


def test_empty_delta_without_mirror_is_a_noop(tmp_path: Path) -> None:
    cfg = tmp_path / ".codex" / "config.toml"
    assert cps.reconcile_mcp_config(cfg, {}, check=False) == ("none", False)
    assert not cfg.parent.exists()


def test_changed_delta_rewrites_whole_file(tmp_path: Path) -> None:
    cfg = tmp_path / ".codex" / "config.toml"
    cfg.parent.mkdir()
    cfg.write_text(cps.emit_mcp_toml({"brave-search": STDIO, "duckdb": STDIO}))

    state, changed = cps.reconcile_mcp_config(cfg, {"duckdb": STDIO}, check=False)
    assert (state, changed) == ("updated", True)
    text = cfg.read_text()
    assert "[mcp_servers.duckdb]" in text
    assert "brave-search" not in text

    assert cps.reconcile_mcp_config(cfg, {"duckdb": STDIO}, check=True) == ("in sync", False)
