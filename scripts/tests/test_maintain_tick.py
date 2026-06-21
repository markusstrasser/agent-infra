"""Tests for maintain_tick.py — the SAFE/dry-run RSI motor.

The load-bearing guarantees this locks in:
  - the motor LOADS config/build-autonomy-tiers.json (epistemic-principle #9 —
    it never restates the tier rules); a fixture policy is injected here.
  - tier classification: tier-0 (auto-ship draft) requires
    blast_radius=agent-infra + reversible + evidence>=threshold + the THREE
    semantic clear-win predicates (checkable, low_downside, clear_win_vs_baseline).
    A local+reversible item MISSING a clear-win predicate routes to 0E
    (eval-gated, NOT auto-shipped, NOT picked). Shared/irreversible/thin-evidence
    are neither 0 nor 0E.
  - SAFE contract: a normal run produces a DRAFT proposal FILE and a ledger row,
    and does NOT edit code / commit / deploy (asserted structurally).
  - prose `[ ]` items: a self-described-local one routes to 0E (it can't assert
    the semantic predicates), an escalation-marked one is needs-classification.
  - apply lane is TRIPLE-gated: --apply needs MAINTAIN_APPLY_ENABLED AND policy
    go_live.maintain_tick_apply=true; missing either → drafts (apply-refused).
    Even fully gated-open, the safe build only drafts (apply-stub).
  - rate gate stands aside when too many `claude` procs are live.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # scripts/

import maintain_tick as mt  # noqa: E402


# A fixture policy mirroring the REAL config/build-autonomy-tiers.json shape:
# tier-0 rule states the threshold + blast in TEXT (the motor parses these), an
# auto-ship action on 0/1, a 0E eval-gate tier, and go_live default-false.
FIXTURE_POLICY = {
    "version": 1,
    "tiers": {
        "0": {
            "rule": "agent-infra-local AND reversible AND checkable AND "
                    "evidence_sessions>=2 AND blast_radius=agent-infra AND "
                    "low_downside AND clear_win_vs_baseline",
            "action": "auto-ship via maintain-tick",
        },
        "0E": {
            "rule": "(agent-infra-local AND reversible) AND NOT clear-win",
            "action": "EVAL-GATED auto-ship — NOT shipped on the tier rule",
        },
        "1": {"rule": "tier-0 AND single-variable", "action": "auto-ship + notify"},
        "2": {"rule": "shared OR 3+ projects", "action": "decisions-pending (human gate)"},
        "3": {"rule": "GOALS OR constitution", "action": "principal only"},
    },
    "go_live": {"maintain_tick_apply": False},
}


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Redirect every path the motor writes/reads into tmp_path, inject the fixture
    policy (both the module global AND a real file at the patched path so run()'s
    re-read sees it), and force the rate gate open by default."""
    registry = tmp_path / "config" / "maintain-candidates.json"
    registry.parent.mkdir(parents=True)
    log = tmp_path / "improvement-log.md"
    proposal_dir = tmp_path / "artifacts" / "maintain"
    ledger = tmp_path / "maintenance-actions.jsonl"
    policy_path = tmp_path / "config" / "build-autonomy-tiers.json"
    policy_path.write_text(json.dumps(FIXTURE_POLICY), encoding="utf-8")

    monkeypatch.setattr(mt, "CANDIDATES_REGISTRY", registry)
    monkeypatch.setattr(mt, "IMPROVEMENT_LOG", log)
    monkeypatch.setattr(mt, "PROPOSAL_DIR", proposal_dir)
    monkeypatch.setattr(mt, "LEDGER", ledger)
    monkeypatch.setattr(mt, "BUILD_AUTONOMY_POLICY", policy_path)  # run() re-reads here
    monkeypatch.setattr(mt, "POLICY", FIXTURE_POLICY)              # gather/classify read this
    monkeypatch.setattr(mt, "REPO", tmp_path)  # so relative_to(REPO) works in run()
    monkeypatch.setattr(mt, "live_claude_count", lambda: 0)  # gate open

    return {"registry": registry, "log": log, "policy_path": policy_path,
            "proposal_dir": proposal_dir, "ledger": ledger, "root": tmp_path}


def _set_go_live(sandbox, value: bool) -> None:
    p = dict(FIXTURE_POLICY)
    p["go_live"] = {"maintain_tick_apply": value}
    sandbox["policy_path"].write_text(json.dumps(p), encoding="utf-8")


def _write_registry(path: Path, candidates: list[dict]) -> None:
    path.write_text(json.dumps({"version": 1, "candidates": candidates}), encoding="utf-8")


# A canonical TIER-0 candidate: local + reversible + evidence>=2 + all 3 clear-win preds.
TIER0 = {
    "id": "continuation-misread-guard",
    "title": "continuation-misread hook",
    "blast_radius": "agent-infra",
    "reversible": True,
    "evidence_sessions": 4,
    "checkable": True,
    "low_downside": True,
    "clear_win_vs_baseline": True,
    "source": "memo",
    "build_kind": "hook",
    "proposal_outline": "build the hook",
}
# Local + reversible + evidence, but NOT a clear win (no clear_win_vs_baseline) → 0E.
EVAL_GATED = {
    "id": "complex-local-thing",
    "title": "a complex local change with unclear baseline win",
    "blast_radius": "agent-infra",
    "reversible": True,
    "evidence_sessions": 3,
    "checkable": True,
    "low_downside": True,
    "clear_win_vs_baseline": False,
}
SHARED = {
    "id": "cross-repo-thing",
    "title": "a cross-repo fix",
    "blast_radius": "shared",
    "reversible": True,
    "evidence_sessions": 5,
    "checkable": True, "low_downside": True, "clear_win_vs_baseline": True,
}
NOT_REVERSIBLE = {
    "id": "scary-thing",
    "title": "an irreversible change",
    "blast_radius": "agent-infra",
    "reversible": False,
    "evidence_sessions": 9,
    "checkable": True, "low_downside": True, "clear_win_vs_baseline": True,
}
THIN_EVIDENCE = {
    "id": "one-off",
    "title": "seen once",
    "blast_radius": "agent-infra",
    "reversible": True,
    "evidence_sessions": 1,
    "checkable": True, "low_downside": True, "clear_win_vs_baseline": True,
}


# ── policy loading + parsing (the #9 consumer contract) ────────────────────────
def test_policy_threshold_and_blast_parsed_from_rule_text():
    assert mt.policy_min_evidence_sessions(FIXTURE_POLICY) == 2
    assert mt.policy_tier0_blast(FIXTURE_POLICY) == "agent-infra"


def test_auto_ship_tiers_derived_not_hardcoded():
    # Only tiers whose action contains "auto-ship" count (0 and 1 here).
    assert mt.auto_ship_tiers(FIXTURE_POLICY) == {"0", "1"}


def test_empty_policy_fails_closed(monkeypatch):
    # No policy → no auto-ship tiers, threshold falls back to 2, apply gate off.
    assert mt.auto_ship_tiers({}) == set()
    assert mt.policy_min_evidence_sessions({}) == 2
    # Isolate the POLICY gate: pass the other two gates so the empty-policy
    # go_live default-false is the blocker that surfaces.
    monkeypatch.setenv(mt.APPLY_ENV_FLAG, "1")
    allowed, reason = mt._apply_allowed(True, {})
    assert not allowed and "go_live" in reason
    # And with no env either, it still blocks (just an earlier reason).
    monkeypatch.delenv(mt.APPLY_ENV_FLAG, raising=False)
    assert mt._apply_allowed(True, {})[0] is False


# ── tier classification ────────────────────────────────────────────────────────
def test_classify_tier_0_vs_0E_vs_excluded():
    assert mt.classify_tier(TIER0, FIXTURE_POLICY) == "0"
    assert mt.classify_tier(EVAL_GATED, FIXTURE_POLICY) == "0E"   # local but not clear-win
    assert mt.classify_tier(SHARED, FIXTURE_POLICY) == ""         # shared → not 0/0E here
    assert mt.classify_tier(NOT_REVERSIBLE, FIXTURE_POLICY) == "" # irreversible
    assert mt.classify_tier(THIN_EVIDENCE, FIXTURE_POLICY) == ""  # <2 sessions


def test_picks_tier0_and_skips_everything_else(sandbox):
    _write_registry(sandbox["registry"], [SHARED, NOT_REVERSIBLE, EVAL_GATED, TIER0, THIN_EVIDENCE])
    res = mt.run(apply=False, force=True, ledger=True)
    assert res["status"] == "drafted"
    assert res["picked"]["id"] == "continuation-misread-guard"  # the only tier-0
    assert res["picked"]["tier"] == "0"
    assert res["tier0_count"] == 1
    assert res["eval_gated_count"] == 1  # the EVAL_GATED item surfaced separately


def test_eval_gated_not_picked_but_surfaced(sandbox):
    # Only a 0E candidate → nothing auto-shippable → noop, but it's surfaced.
    _write_registry(sandbox["registry"], [EVAL_GATED])
    res = mt.run(apply=False, force=True, ledger=True)
    assert res["status"] == "noop"
    assert res["eval_gated_count"] == 1
    assert any("complex local change" in t for t in res["eval_gated"])


# ── SAFE contract: draft file + ledger only, no code/commit/deploy ─────────────
def test_dry_run_writes_only_proposal_and_ledger(sandbox):
    _write_registry(sandbox["registry"], [TIER0])
    before = {p for p in sandbox["root"].rglob("*") if p.is_file()}
    res = mt.run(apply=False, force=True, ledger=True)
    after = {p for p in sandbox["root"].rglob("*") if p.is_file()}
    new_files = after - before
    proposal = sandbox["root"] / res["proposal_path"]
    assert proposal in new_files
    assert sandbox["ledger"] in new_files
    assert new_files == {proposal, sandbox["ledger"]}, f"unexpected writes: {new_files}"
    body = proposal.read_text()
    assert "status: draft-proposal" in body
    assert "No code was edited, no commit made, no job deployed" in body
    assert "tier: 0" in body  # the policy tier is recorded in the draft
    rows = [json.loads(l) for l in sandbox["ledger"].read_text().splitlines() if l.strip()]
    assert rows[-1]["action"] == "maintain-tick"
    assert rows[-1]["result"] == "drafted"
    assert set(rows[-1]) == {"ts", "action", "target", "result", "detail"}


# ── prose `[ ]` items: conservative classification ────────────────────────────
def test_prose_unclassified_not_picked_but_surfaced(sandbox):
    sandbox["log"].write_text(
        "- [x] [2026-01-01] done thing\n"
        "- [ ] **Some ADR-candidate cross-repo lever** — worth an ADR.\n"
    )
    res = mt.run(apply=False, force=True, ledger=True)
    assert res["status"] == "noop"
    assert any("ADR-candidate" in t for t in res["needs_classification"])


def test_prose_self_described_local_routes_to_0E(sandbox):
    # A prose item can't assert the semantic clear-win predicates, so even a
    # self-described-local one is 0E (eval-gated), never auto-shipped.
    sandbox["log"].write_text(
        "- [ ] **A small fix** — agent-infra-local, low-sev; heredoc/quoting fix in the recipe.\n"
    )
    res = mt.run(apply=False, force=True, ledger=True)
    assert res["status"] == "noop"          # no tier-0 (prose can't be a clear-win)
    assert res["eval_gated_count"] == 1     # but it IS a 0E candidate


def test_registry_preferred_over_prose(sandbox):
    _write_registry(sandbox["registry"], [TIER0])
    sandbox["log"].write_text(
        "- [ ] **Another fix** — agent-infra-local, low-sev tweak.\n"
    )
    res = mt.run(apply=False, force=True, ledger=True)
    assert res["picked"]["origin"] == "registry"


# ── apply lane TRIPLE-gate ─────────────────────────────────────────────────────
def test_apply_without_env_still_only_drafts(sandbox, monkeypatch):
    monkeypatch.delenv(mt.APPLY_ENV_FLAG, raising=False)
    _set_go_live(sandbox, True)  # even with policy gate open
    _write_registry(sandbox["registry"], [TIER0])
    res = mt.run(apply=True, force=True, ledger=True)
    assert res["status"] == "drafted"
    assert res["mode"] == "dry-run"  # env gate blocked → fell back
    assert "apply-refused" in sandbox["ledger"].read_text()


def test_apply_with_env_but_policy_off_still_only_drafts(sandbox, monkeypatch):
    monkeypatch.setenv(mt.APPLY_ENV_FLAG, "1")
    _set_go_live(sandbox, False)  # policy gate CLOSED (default)
    _write_registry(sandbox["registry"], [TIER0])
    res = mt.run(apply=True, force=True, ledger=True)
    assert res["status"] == "drafted"
    assert res["mode"] == "dry-run"  # policy gate blocked
    led = sandbox["ledger"].read_text()
    assert "apply-refused" in led and "go_live" in led


def test_apply_fully_gated_open_still_only_drafts_in_safe_build(sandbox, monkeypatch):
    monkeypatch.setenv(mt.APPLY_ENV_FLAG, "1")
    _set_go_live(sandbox, True)  # all three gates open
    _write_registry(sandbox["registry"], [TIER0])
    res = mt.run(apply=True, force=True, ledger=True)
    # Even fully gated-open, the safe build only drafts (apply path is a loud stub).
    assert res["status"] == "drafted"
    assert res["mode"] == "apply-stub"
    assert "apply-stub" in sandbox["ledger"].read_text()


# ── rate gate ──────────────────────────────────────────────────────────────────
def test_rate_gate_stands_aside(sandbox, monkeypatch):
    monkeypatch.setattr(mt, "live_claude_count", lambda: 5)  # over MAX_LIVE_CLAUDE
    _write_registry(sandbox["registry"], [TIER0])
    res = mt.run(apply=False, force=False, ledger=True)  # force=False so gate applies
    assert res["status"] == "rate-gated"
    assert res["picked"] is None
    assert not list(sandbox["proposal_dir"].glob("*.md")) if sandbox["proposal_dir"].exists() else True


# ── empty / nothing-to-do ──────────────────────────────────────────────────────
def test_noop_when_no_candidates(sandbox):
    res = mt.run(apply=False, force=True, ledger=True)
    assert res["status"] == "noop"
    assert res["picked"] is None


# ── SUBTRACT pass (governance shrink) ──────────────────────────────────────────
# gov's eligible-item shape: {id, kind, path, goal, verifier, blast_radius, verdict}
SHRINK_LOCAL_PASS = {
    "id": "rule:some-local-rule", "kind": "rule",
    "path": ".claude/rules/some-local-rule.md", "goal": "prevent X",
    "verifier": "evals/graders/governance/x.py", "blast_radius": "local",
    "verdict": {"passed": True, "margin": "5", "evidence": "goal holds with scaffold"},
}
SHRINK_LOCAL_FAIL = {**SHRINK_LOCAL_PASS,
                     "verdict": {"passed": False, "margin": "-2", "evidence": "goal VIOLATED"}}
SHRINK_LOCAL_NOGRADER = {**SHRINK_LOCAL_PASS, "verdict": None}  # grader file absent
ADVISORY = {"hook": "some-advisory-hook", "fires": 999, "confidence": "medium",
            "evidence": "999 fires in 60d, actions=['warn'] (advisory-only)",
            "blast_radius": "shared", "disposition": "review→quarantine/delete (never auto-BLOCK)"}


def _patch_gov(monkeypatch, *, eligible=None, noise=None, raise_=False):
    """Patch gov.py's report-only detectors so the subtract pass runs offline (no
    real graders / agentlogs). Leaves gov.route REAL by default so the routing
    invariant is genuinely exercised."""
    import gov
    if raise_:
        def _boom(*a, **k):
            raise RuntimeError("gov detectors down")
        monkeypatch.setattr(gov, "collect_artifacts", _boom)
        return
    monkeypatch.setattr(gov, "collect_artifacts", lambda: [])
    monkeypatch.setattr(gov, "gov_shrink_dryrun",
                        lambda arts: {"eligible": eligible or [], "backlog": [], "style": []})
    monkeypatch.setattr(gov, "advisory_noise", lambda days: noise or [])


def test_subtract_drafts_shrink_candidate_safely(sandbox, monkeypatch):
    """A local shrink-eligible scaffold whose goal PASSES → drafted, route=human,
    and the SAFE contract holds: ONLY the proposal + ledger are written (nothing
    removed, no governance file touched)."""
    _patch_gov(monkeypatch, eligible=[SHRINK_LOCAL_PASS])
    before = {p for p in sandbox["root"].rglob("*") if p.is_file()}
    res = mt.run_subtract(force=True, ledger=True)
    after = {p for p in sandbox["root"].rglob("*") if p.is_file()}
    assert res["status"] == "drafted"
    assert res["route"] == "human"  # pre-ablation: always human
    assert res["picked"]["origin"] == "gov-shrink"
    proposal = sandbox["root"] / res["proposal_path"]
    assert (after - before) == {proposal, sandbox["ledger"]}, "subtract must write ONLY proposal+ledger"
    body = proposal.read_text()
    assert "status: draft-retire-proposal" in body
    assert "Ablation NOT run" in body  # ablate defaults off → gate not yet satisfied
    assert "nothing was removed" in body
    rows = [json.loads(l) for l in sandbox["ledger"].read_text().splitlines() if l.strip()]
    assert rows[-1]["action"] == "maintain-subtract" and rows[-1]["result"] == "drafted"


def test_subtract_only_passing_scaffolds_are_candidates(sandbox, monkeypatch):
    """A FAIL scaffold (goal violated WITH it) or a no-grader one is NOT a
    retire-candidate — only goal-currently-holds scaffolds are ablation candidates."""
    _patch_gov(monkeypatch, eligible=[SHRINK_LOCAL_FAIL, SHRINK_LOCAL_NOGRADER])
    res = mt.run_subtract(force=True, ledger=True)
    assert res["status"] == "noop"


def test_subtract_never_auto_routes_preablation(sandbox, monkeypatch):
    """THE safety invariant: even a LOCAL scaffold whose goal PASSES routes to human
    pre-ablation — route_retire pins confidence='medium', so the REAL gov.route can
    never return auto-apply even with AUTO_APPLY_ENABLED forced on."""
    _patch_gov(monkeypatch, eligible=[SHRINK_LOCAL_PASS])  # local + passing
    import gov
    monkeypatch.setattr(gov, "AUTO_APPLY_ENABLED", True, raising=False)  # auto-apply env ON
    res = mt.run_subtract(force=True, ledger=True)
    assert res["route"] == "human"


def test_subtract_advisory_noise_human_gated(sandbox, monkeypatch):
    _patch_gov(monkeypatch, noise=[ADVISORY])
    res = mt.run_subtract(force=True, ledger=True)
    assert res["status"] == "drafted"
    assert res["picked"]["retire_kind"] == "advisory-noise"
    assert res["route"] == "human"  # blast=shared → always human


def test_subtract_shrink_preferred_over_noise(sandbox, monkeypatch):
    _patch_gov(monkeypatch, eligible=[SHRINK_LOCAL_PASS], noise=[ADVISORY])
    res = mt.run_subtract(force=True, ledger=True)
    assert res["picked"]["origin"] == "gov-shrink"  # real shrink loop first


def test_subtract_noop_when_no_candidates(sandbox, monkeypatch):
    _patch_gov(monkeypatch, eligible=[], noise=[])
    res = mt.run_subtract(force=True, ledger=True)
    assert res["status"] == "noop"
    assert res["picked"] is None


def test_subtract_gov_unavailable_fails_safe(sandbox, monkeypatch):
    """Off-happy-path: a gov detector raising → status=error, no crash, nothing drafted."""
    _patch_gov(monkeypatch, raise_=True)
    res = mt.run_subtract(force=True, ledger=True)
    assert res["status"] == "error"
    assert res["picked"] is None
    assert not (sandbox["proposal_dir"].exists() and list(sandbox["proposal_dir"].glob("*.md")))


def test_subtract_rate_gate_stands_aside(sandbox, monkeypatch):
    monkeypatch.setattr(mt, "live_claude_count", lambda: 5)  # over MAX_LIVE_CLAUDE
    _patch_gov(monkeypatch, eligible=[SHRINK_LOCAL_PASS])
    res = mt.run_subtract(force=False, ledger=True)  # force=False so gate applies
    assert res["status"] == "rate-gated"
    assert res["picked"] is None


# ── ablation gate (READ-ONLY) ──────────────────────────────────────────────────
def test_run_ablation_no_verifier_fails_closed():
    """No verifier or artifact_path → ablated None (never claims removable)."""
    assert mt.run_ablation({})["ablated"] is None
    assert mt.run_ablation({"verifier": "x.py"})["ablated"] is None        # no artifact_path
    assert mt.run_ablation({"artifact_path": ".claude/rules/x.md"})["ablated"] is None  # no verifier


def test_subtract_ablate_folds_verdict_into_draft(sandbox, monkeypatch):
    """With ablate=True, the picked shrink candidate's ablation verdict is run and
    folded into the draft + result. (run_ablation is mocked — the live worktree path
    is integration-tested separately; here we test the WIRING.)"""
    _patch_gov(monkeypatch, eligible=[SHRINK_LOCAL_PASS])
    monkeypatch.setattr(mt, "run_ablation",
                        lambda c: {"ablated": True, "evidence": "goal holds without it (mock)"})
    res = mt.run_subtract(force=True, ledger=True, ablate=True)
    assert res["status"] == "drafted"
    assert res["ablation"] == {"ablated": True, "evidence": "goal holds without it (mock)"}
    body = (sandbox["root"] / res["proposal_path"]).read_text()
    assert "Ablation PASSED" in body  # the ablated=True branch of the gate text
    # ledger records the ablation verdict
    assert "ablated=True" in sandbox["ledger"].read_text()


def test_subtract_ablate_failed_says_keep(sandbox, monkeypatch):
    """ablated False → the draft says KEEP (load-bearing), not retire."""
    _patch_gov(monkeypatch, eligible=[SHRINK_LOCAL_PASS])
    monkeypatch.setattr(mt, "run_ablation",
                        lambda c: {"ablated": False, "evidence": "goal FAILS without it (mock)"})
    res = mt.run_subtract(force=True, ledger=True, ablate=True)
    body = (sandbox["root"] / res["proposal_path"]).read_text()
    assert "Ablation FAILED" in body and "KEEP" in body


def test_subtract_ablate_not_run_when_flag_off(sandbox, monkeypatch):
    """ablate defaults off → run_ablation is NOT called (no worktree work per tick)."""
    _patch_gov(monkeypatch, eligible=[SHRINK_LOCAL_PASS])
    called = {"n": 0}
    def _spy(c):
        called["n"] += 1
        return {"ablated": True, "evidence": "x"}
    monkeypatch.setattr(mt, "run_ablation", _spy)
    res = mt.run_subtract(force=True, ledger=True)  # ablate defaults False
    assert called["n"] == 0
    assert res.get("ablation") is None


# ── ablation safety helpers (pure; the worktree path is integration-tested live) ──
def test_path_confined_blocks_escape(tmp_path):
    """READ-ONLY guard: relative-inside OK; absolute or ..-escape REFUSED (Finding 1)."""
    wt = tmp_path / "wt"
    wt.mkdir()
    assert mt._path_confined(wt, ".claude/rules/x.md") is True
    assert mt._path_confined(wt, "/Users/alien/Projects/agent-infra/improvement-log.md") is False  # absolute escapes
    assert mt._path_confined(wt, "../../../Projects/agent-infra/CLAUDE.md") is False               # ..-escape
    assert mt._path_confined(wt, "a/../b.md") is True                                              # stays inside


def test_ablation_verdict_failclosed_on_inconclusive_baseline():
    """Finding 2: an inconclusive `before` must NEVER yield ablated=True even when
    `after` passes — the without-scaffold PASS cannot be attributed to the scaffold."""
    incon = {"passed": None, "margin": None, "evidence": "grader errored"}
    passed = {"passed": True, "margin": 5, "evidence": "ok"}
    assert mt._ablation_verdict(incon, passed)["ablated"] is None      # the exact Finding-2 case
    assert mt._ablation_verdict(None, passed)["ablated"] is None
    assert mt._ablation_verdict(passed, None)["ablated"] is None
    assert mt._ablation_verdict(passed, incon)["ablated"] is None


def test_ablation_verdict_sensitivity_and_real_verdicts():
    fail = {"passed": False, "margin": -2, "evidence": "violated"}
    passW = {"passed": True, "margin": 5, "evidence": "holds"}
    passN = {"passed": True, "margin": 9, "evidence": "holds more"}
    # identical verdict with/without → inconclusive (grader insensitive to the file)
    assert mt._ablation_verdict(passW, dict(passW))["ablated"] is None
    # goal was failing WITH, passes WITHOUT (changed) → removable
    assert mt._ablation_verdict(fail, passN)["ablated"] is True
    # goal passed WITH, fails WITHOUT (changed) → load-bearing, KEEP
    assert mt._ablation_verdict(passW, fail)["ablated"] is False


def test_resolve_predictions_for_ablation_matches_gov_id(monkeypatch, tmp_path):
    """Conclusive ablation closes a matching earn-its-keep prediction."""
    import predictions as pred

    ledger = tmp_path / "predictions.jsonl"
    monkeypatch.setattr(pred, "LEDGER", ledger)
    pred.register_prediction(
        change="**hook:foo-bar** — test scaffold",
        prediction="earns keep",
        metric="gov-shrink",
        check_date="2099-01-01",
        pid="impl-deadbeef-00000001",
    )
    c = {"gov_id": "hook:foo-bar", "artifact_path": ".claude/rules/foo-bar.md"}
    abl = {"ablated": True, "evidence": "passes without scaffold"}
    acted = mt.resolve_predictions_for_ablation(c, abl)
    assert acted == ["impl-deadbeef-00000001"]
    _, resolved = pred._load()
    assert "impl-deadbeef-00000001" in resolved
