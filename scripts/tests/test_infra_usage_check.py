"""Tests for scripts/infra_usage_check.py — adoption ratchet."""
from __future__ import annotations

from datetime import datetime, timezone

import infra_usage_check as iuc


def test_artifact_dir_unadopted_when_only_ignored(tmp_path, monkeypatch):
    monkeypatch.setattr(iuc, "REPO", tmp_path)
    d = tmp_path / "mechanism-records"
    d.mkdir()
    (d / "README.md").write_text("x")
    (d / "example-tool-error-rate.json").write_text("{}")
    surf = iuc.InfraSurface(
        id="f3",
        kind="artifact_dir",
        path="mechanism-records",
        description="t",
        ignore_names=("README.md", "example-tool-error-rate.json"),
        stale_days=0,
    )
    # No git history → unadopted
    r = iuc.check_surface(surf, now=datetime.now(timezone.utc))
    assert r["status"] == "unadopted"
    assert r["usage_count"] == 0


def test_artifact_dir_adopted_with_real_file(tmp_path, monkeypatch):
    monkeypatch.setattr(iuc, "REPO", tmp_path)
    d = tmp_path / "mechanism-records"
    d.mkdir()
    (d / "real-record.json").write_text("{}")
    surf = iuc.InfraSurface(
        id="f3",
        kind="artifact_dir",
        path="mechanism-records",
        description="t",
        ignore_names=("README.md",),
    )
    r = iuc.check_surface(surf)
    assert r["status"] == "adopted"
    assert r["usage_count"] == 1


def test_script_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(iuc, "REPO", tmp_path)
    surf = iuc.InfraSurface(
        id="gone",
        kind="script",
        path="scripts/nope.py",
        description="t",
    )
    r = iuc.check_surface(surf)
    assert r["status"] == "missing"


def test_script_adoption_uses_resolved_code_relations(tmp_path, monkeypatch):
    monkeypatch.setattr(iuc, "REPO", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "producer.py").write_text("def run():\n    return 1\n")
    (scripts / "consumer.py").write_text("from producer import run\nrun()\n")
    surf = iuc.InfraSurface(
        id="producer",
        kind="script",
        path="scripts/producer.py",
        description="t",
    )

    result = iuc.check_surface(surf, relation_graph=iuc._relation_graph())

    assert result["status"] == "adopted"
    assert result["usage_count"] == 1
    assert result["adoption_signal"] == "code_relations"
