"""Tests for system_inventory.py — typed derived inventory."""

import json
import sys

import system_inventory as si


def test_orchestrator_recipes_have_layer_role():
    rows = si.collect_orchestrator_recipes()
    assert rows
    assert rows[0]["recipe"] == "operator-status-briefing"
    assert rows[0]["layer"] == "session"
    assert rows[0]["role"] == "operator-tool"


def test_plist_manifest_tags_maintain_tick():
    manifest = si.collect_plist_manifest()
    mt = next(m for m in manifest if m["name"] == "maintain-tick")
    assert mt["tagged"]
    assert mt["role"] == "rsi-motor"
    assert mt["layer"] == "gov"


def test_render_architecture_substitutes_placeholders():
    inv = si.collect_inventory()
    mmd = si.render_architecture_mmd(inv)
    assert "{{GENERATED_AT}}" not in mmd
    assert "FILEBUS" in mmd
    assert "maintain-tick" in mmd


def test_drift_detects_unloaded_manifest(capsys):
    drift = si.collect_drift()
    assert "integrate-rank" not in drift["manifest_not_loaded"]


def test_json_entrypoint(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["system_inventory.py", "--json"])
    assert si.main() == 0
    data = json.loads(capsys.readouterr().out)
    assert "launchd" in data
    assert "orchestrator_recipes" in data
    assert "kinds" in data
