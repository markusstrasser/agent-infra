"""Tests for system_inventory.py — typed derived inventory."""

import json
import sys

import system_inventory as si


def test_plist_manifest_tags_pulse_tick():
    manifest = si.collect_plist_manifest()
    pt = next(m for m in manifest if m["name"] == "pulse-tick")
    assert pt["tagged"]
    assert pt["role"] == "rsi-motor"
    assert pt["layer"] == "gov"


def test_render_architecture_substitutes_placeholders():
    inv = si.collect_inventory()
    mmd = si.render_architecture_mmd(inv)
    assert "{{GENERATED_AT}}" not in mmd
    assert "WATCH" in mmd
    assert "FILEBUS" not in mmd  # file-bus orchestrator retired 2026-09-02
    assert "pulse-tick" in mmd


def test_normalize_volatile_inventory_strips_live_launchctl():
    a = 'L["job-a · ok<br/>job-b · exit 1"]\nLLMJOBS["LLM launchd: clash-detect"]'
    b = 'L["job-c · ok"]\nLLMJOBS["LLM launchd: none"]'
    assert si._normalize_volatile_inventory(a) == si._normalize_volatile_inventory(b)


def test_drift_detects_unloaded_manifest(capsys):
    drift = si.collect_drift()
    names = {m["name"] for m in si.collect_plist_manifest()}
    assert "maintain-tick" not in names
    assert "drift-sentinel" not in names
    assert "pulse-tick" in names


def test_json_entrypoint(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["system_inventory.py", "--json"])
    assert si.main() == 0
    data = json.loads(capsys.readouterr().out)
    assert "launchd" in data
    assert "orchestrator_recipes" not in data
    assert "kinds" in data
