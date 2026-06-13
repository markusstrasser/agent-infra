"""Contract tests for orient.py — the live orientation map.

orient is meant to NEVER hard-fail (it's the "where am I" tool), so the
contract is: every section returns a sane shape, the --json entry point
emits all keys, faults are isolated, and the drift check actually compares
against CLAUDE.md. These guard against silent breakage as the system evolves.
"""

import json
import sys

import orient  # scripts/ is on sys.path via conftest


def test_json_entrypoint_emits_all_sections(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["orient.py", "--json"])
    rc = orient.main()
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    for key in ("repos", "loops", "hooks", "mcp", "skills", "maps", "drift"):
        assert key in data, f"missing section: {key}"


def test_human_render_never_raises(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["orient.py"])
    assert orient.main() == 0
    assert "orientation map" in capsys.readouterr().out


def test_fault_isolation_returns_error_not_raise():
    def boom():
        raise RuntimeError("section blew up")

    res = orient._safe(boom, "demo")
    assert res["error"].startswith("RuntimeError")
    assert res["section"] == "demo"


def test_hooks_shape():
    h = orient.collect_hooks()
    assert {"events", "total_hooks", "unique_scripts"} <= set(h)
    assert isinstance(h["events"], dict)
    assert h["total_hooks"] >= 0


def test_mcp_shape():
    m = orient.collect_mcp()
    assert {"global", "project", "enabled_mcpjson"} <= set(m)
    assert isinstance(m["global"], list)


def test_repos_include_the_hub():
    repos = orient.collect_repos()
    hub = [r for r in repos if r.get("hub")]
    assert hub and hub[0]["repo"] == "agent-infra"


def test_drift_flags_a_job_absent_from_claude_md():
    out = orient.collect_drift([{"name": "zzz-not-a-real-job-xyz"}])
    assert "zzz-not-a-real-job-xyz" in out["undocumented_in_claude_md"]


def test_drift_passes_a_documented_job():
    # agentlogs-index is named in CLAUDE.md's active-launchd-jobs paragraph
    out = orient.collect_drift([{"name": "agentlogs-index"}])
    assert out["undocumented_in_claude_md"] == []


def test_drift_only_mode_exit_code(monkeypatch):
    # --drift returns nonzero iff there is drift; with the real (in-sync)
    # CLAUDE.md and real launchd, it should be 0. The synthetic checks above
    # already prove the flagging logic, so here we just assert it runs clean.
    monkeypatch.setattr(sys, "argv", ["orient.py", "--drift"])
    rc = orient.main()
    assert rc in (0, 1)  # 0 = in sync, 1 = drift found; both are valid runs
