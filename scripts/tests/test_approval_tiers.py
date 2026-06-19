"""Tests for approval_tiers.py manifest validation."""

from pathlib import Path

import approval_tiers as at


def test_manifest_loads():
    data = at.load_manifest()
    assert data["version"] == 1
    assert len(data["tiers"]) >= 5


def test_manifest_hooks_nonempty():
    hooks = at.manifest_hooks()
    assert "pretool-cost-guard.sh" in hooks
    assert hooks["pretool-cost-guard.sh"] == "predicate"


def test_validate_manifest_ok():
    chk = at.validate_manifest()
    assert chk.ok, f"missing={chk.missing_files} uncovered={chk.uncovered_global}"


def test_global_pretools_subset_of_manifest_or_inject():
    listed = set(at.manifest_hooks())
    inject = {
        h for tier in at.load_manifest()["tiers"]
        if tier.get("action") == "inject"
        for h in tier.get("hooks", [])
    }
    for h in at.global_pretool_hooks():
        assert h in listed or h in inject, f"uncovered global pretool: {h}"


def test_resolve_known_hook():
    assert at.resolve_hook_file("pretool-bash-loop-guard.sh") is not None
