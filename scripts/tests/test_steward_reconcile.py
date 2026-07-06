"""Tests for steward_reconcile.reconcile — the already-done LOCATE heuristic.

Guards the precision invariants that keep it a useful triage flag rather than noise:
  1. a proposal that CITES a hook/script sharing its slug token, and the file exists,
     is flagged (the userprompt-clock case);
  2. a proposal that cites an UNRELATED existing file (context it modifies, no shared
     slug token) is NOT flagged (the false-positive the tightening killed);
  3. a slug-token match against a shipped basename (no citation) is flagged;
  4. a same-intent file in implemented/ flags dup-implemented;
  5. it is READ-ONLY — proposals are never moved, edited, or closed.
"""
import importlib.util
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent


def _load(steward: Path, projects: Path):
    spec = importlib.util.spec_from_file_location("steward_reconcile_t", SCRIPTS / "steward_reconcile.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # Redirect every module-level filesystem seam at the tmp dirs.
    mod.STEWARD_DIR = steward
    mod.IMPLEMENTED_DIR = steward / "implemented"
    mod.PROJECTS = projects
    hooks = projects / "skills" / "hooks"
    mod.ARTIFACT_ROOTS = (hooks,)
    mod.ARTIFACT_GLOBS = ("*/scripts",)
    return mod


def _mk(base: Path, rel: str, text: str = "x") -> Path:
    p = base / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def test_cited_artifact_sharing_slug_token_is_flagged(tmp_path):
    steward = tmp_path / "steward"
    projects = tmp_path / "Projects"
    _mk(projects, "skills/hooks/userprompt-clock.sh")
    _mk(steward, "2026-07-06-userprompt-clock.md",
        "# Proposal\n\nA `userprompt-clock.sh` UserPromptSubmit hook.\n")
    mod = _load(steward, projects)
    res = mod.reconcile()
    assert res["candidate_count"] == 1
    c = res["candidates"][0]
    assert c["signal"] == "artifact-exists" and c["cited"] is True
    assert "clock" in c["shared"]


def test_cited_unrelated_file_is_not_flagged(tmp_path):
    steward = tmp_path / "steward"
    projects = tmp_path / "Projects"
    _mk(projects, "skills/hooks/stop-smart-judge.sh")
    # Proposal about dead metered-API hooks CITES an existing unrelated hook — no
    # shared slug token, so it must NOT be read as already-done.
    _mk(steward, "2026-06-15-llm-hooks-dead-metered-api.md",
        "# Proposal\n\nThe `stop-smart-judge.sh` hook still routes to a dead API.\n")
    mod = _load(steward, projects)
    res = mod.reconcile()
    assert res["candidate_count"] == 0
    assert res["open_count"] == 1


def test_slug_token_match_without_citation_is_flagged(tmp_path):
    steward = tmp_path / "steward"
    projects = tmp_path / "Projects"
    _mk(projects, "genomics/scripts/qc_fanout.py")
    _mk(steward, "2026-06-29-qc-fanout-hardening.md", "# Proposal\n\nHarden QC fanout.\n")
    mod = _load(steward, projects)
    res = mod.reconcile()
    assert res["candidate_count"] == 1
    assert res["candidates"][0]["shared"] == ["fanout", "qc"]


def test_no_match_leaves_proposal_open(tmp_path):
    steward = tmp_path / "steward"
    projects = tmp_path / "Projects"
    _mk(steward, "2026-07-01-some-brand-new-idea.md", "# Proposal\n\nNothing shipped yet.\n")
    mod = _load(steward, projects)
    res = mod.reconcile()
    assert res == {"open_count": 1, "candidate_count": 0, "candidates": []}


def test_dup_implemented_signal(tmp_path):
    steward = tmp_path / "steward"
    projects = tmp_path / "Projects"
    _mk(steward, "implemented/2026-06-16-agentlogs-write-gateway.md", "done")
    _mk(steward, "2026-06-30-agentlogs-write-gateway.md", "# Proposal\n\nGateway for agentlogs writes.\n")
    mod = _load(steward, projects)
    res = mod.reconcile()
    assert res["candidate_count"] == 1
    assert res["candidates"][0]["signal"] == "dup-implemented"


def test_readonly_never_mutates(tmp_path):
    steward = tmp_path / "steward"
    projects = tmp_path / "Projects"
    _mk(projects, "skills/hooks/userprompt-clock.sh")
    prop = _mk(steward, "2026-07-06-userprompt-clock.md",
               "# Proposal\n\nA `userprompt-clock.sh` hook.\n")
    mod = _load(steward, projects)
    mod.reconcile()
    # The proposal is a LOCATE candidate, but reconcile must not close it.
    assert prop.exists()
    assert not (steward / "implemented" / prop.name).exists()


def test_skips_triage_and_readme(tmp_path):
    steward = tmp_path / "steward"
    projects = tmp_path / "Projects"
    _mk(steward, "TRIAGE-2026-06-16.md", "# Triage\n")
    _mk(steward, "README.md", "# Readme\n")
    mod = _load(steward, projects)
    res = mod.reconcile()
    assert res["open_count"] == 0
