"""Tests for questions_view.py — the focused 'Questions for you' VIEW.

Covers the 5 robustness HOWs the cross-model critique confirmed (ADR
2026-06-16-agent-question-convergence): envelope id stability, parser-robustness
(skip+count), fail-loud feeder errors, dedup, and the dormant-inert clash seam.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # scripts/

import questions_view as qv  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate_ambient_feeders(monkeypatch, tmp_path):
    """Hermetic by default: don't let the real predictions.jsonl / clash-shadow.jsonl leak
    into count assertions. Tests that exercise those feeders override these explicitly."""
    import predictions
    monkeypatch.setattr(predictions, "LEDGER", tmp_path / "_no_predictions.jsonl")
    monkeypatch.setattr(qv, "CLASH_LOG", tmp_path / "_no_clash.jsonl")
    monkeypatch.setattr(qv, "HUMAN_MD_ROOT", tmp_path / "_no_projects")
    monkeypatch.setattr(qv, "STEWARD_DIR", tmp_path / "_no_steward")

DECISION = """# Fix the rate-limit gate — pgrep over-counts, gate stuck closed

**Boundary:** shared — edits skills/improve/SKILL.md
**Recommendation:** swap `pgrep -lf claude` for `pgrep -x claude`
**Open question for you:** total claude processes or headless-dispatch load only?
**Reversible?** Yes, one-line revert.
**Evidence:** live measurement 1130 vs 21
"""

STEWARD = """# Steward proposal: LLM hooks on the metered API are silently dead

**Found:** 2026-06-15
**Class:** silent dead infra / false-coverage confidence
**Reversible:** yes

## Finding
The metered key returns credit-too-low; any hook calling it is a silent no-op.
"""


# ── envelope id stability (#20) ──────────────────────────────────────────────
def test_make_id_stable_and_distinct():
    a = qv.make_id("decisions-pending", "x.md")
    assert a == qv.make_id("decisions-pending", "x.md")  # idempotent
    assert a != qv.make_id("steward-proposals", "x.md")  # source-scoped
    assert a != qv.make_id("decisions-pending", "y.md")  # ref-scoped


# ── decision parse + category + prompt = the open-question line ───────────────
def test_parse_decision(tmp_path):
    p = tmp_path / "2026-06-15-rate-gate.md"
    p.write_text(DECISION)
    q = qv._parse_decision(p)
    assert q.source == "decisions-pending"
    assert q.created == "2026-06-15"  # from filename, not mtime
    assert "total claude processes" in q.prompt  # open-question line wins over title
    assert "boundary=shared" in q.detail
    assert q.category in qv.CAT_ORDER


def test_parse_steward_strips_prefix(tmp_path):
    p = tmp_path / "2026-06-15-dead-hooks.md"
    p.write_text(STEWARD)
    q = qv._parse_steward(p)
    assert not q.prompt.lower().startswith("steward proposal")  # prefix stripped
    assert "silently dead" in q.prompt
    assert q.created == "2026-06-15"
    assert "class=" in q.detail


# ── parser-robust: one malformed item is skipped + counted, others survive (#13/#16/#34)
def test_malformed_item_skipped_not_crash(tmp_path, monkeypatch):
    dp = tmp_path / "decisions-pending"
    dp.mkdir()
    (dp / "2026-06-15-good.md").write_text(DECISION)
    (dp / "2026-06-15-bad.md").write_text("no title here, just prose\n")  # no `# ` → ValueError
    (dp / "README.md").write_text("# README\nskip me")  # explicitly skipped
    monkeypatch.setattr(qv, "STEWARD_DIR", tmp_path / "nonexistent-steward")
    result = qv.collect_questions(tmp_path)
    assert len(result.questions) == 1  # only the good one
    assert len(result.skipped) == 1 and "bad.md" in result.skipped[0]
    assert result.degraded == []  # a bad item is NOT a feeder failure


# ── fail-loud: a feeder-LEVEL read error emits [DEGRADED], never silent (#18, P8) ──
def test_feeder_unreadable_is_loud(tmp_path, monkeypatch):
    dp = tmp_path / "decisions-pending"
    dp.mkdir()
    (dp / "2026-06-15-good.md").write_text(DECISION)

    def _boom(_d):
        raise OSError("permission denied")

    monkeypatch.setattr(qv, "_list_md", _boom)
    monkeypatch.setattr(qv, "STEWARD_DIR", tmp_path / "nonexistent-steward")
    result = qv.collect_questions(tmp_path)
    assert result.questions == []
    assert any("DEGRADED" in d and "decisions-pending" in d for d in result.degraded)
    # and a degraded result still renders (loud), not None
    section = qv.render_section(result)
    assert section and "⚠" in section


# ── absent feeder = silent green (not an error) ──────────────────────────────
def test_absent_feeder_silent(tmp_path, monkeypatch):
    monkeypatch.setattr(qv, "STEWARD_DIR", tmp_path / "nope")
    result = qv.collect_questions(tmp_path / "also-nope")
    assert result.questions == [] and result.degraded == [] and result.skipped == []
    assert qv.render_section(result) is None


# ── dedup by id (#20) ────────────────────────────────────────────────────────
def test_dedup_by_id():
    q = qv.Question(id="dup", source="decisions-pending", category="governance",
                    prompt="a", created="2026-06-15", ref="x")
    assert len(qv._dedup([q, q])) == 1


def test_dedup_cross_feeder_structured_wins():
    qd = qv.Question(id="i1", source="decisions-pending", category="tool",
                     prompt="Same Question Text", created="2026-06-15", ref="d.md")
    qs = qv.Question(id="i2", source="steward-proposals", category="tool",
                     prompt="same question text", created="2026-06-15", ref="s.md")
    out = qv._dedup([qs, qd])
    assert len(out) == 1 and out[0].source == "decisions-pending"  # structured source wins


# ── clash seam: dormant + inert today, but works when promoted=true (#gate) ──
def test_clash_seam_inert_without_promotion(tmp_path, monkeypatch):
    log = tmp_path / "clash-shadow.jsonl"
    log.write_text('{"ts":"2026-06-16T00:00:00Z","item":"some veto","message":"do X","promoted":false}\n')
    monkeypatch.setattr(qv, "CLASH_LOG", log)
    monkeypatch.setattr(qv, "STEWARD_DIR", tmp_path / "no-steward")
    result = qv.collect_questions(tmp_path / "no-decisions", include_clash=True)
    assert result.questions == []  # nothing promoted → inert


def test_clash_seam_fires_when_promoted(tmp_path, monkeypatch):
    log = tmp_path / "clash-shadow.jsonl"
    log.write_text('{"ts":"2026-06-16T00:00:00Z","item":"PyMC veto","message":"add PyMC","promoted":true}\n')
    monkeypatch.setattr(qv, "CLASH_LOG", log)
    monkeypatch.setattr(qv, "STEWARD_DIR", tmp_path / "no-steward")
    result = qv.collect_questions(tmp_path / "no-decisions", include_clash=True)
    assert len(result.questions) == 1
    q = result.questions[0]
    assert q.source == "clash" and q.category == "governance" and "PyMC veto" in q.prompt


def test_clash_off_by_default(tmp_path, monkeypatch):
    log = tmp_path / "clash-shadow.jsonl"
    log.write_text('{"ts":"2026-06-16T00:00:00Z","item":"v","message":"m","promoted":true}\n')
    monkeypatch.setattr(qv, "CLASH_LOG", log)
    monkeypatch.setattr(qv, "STEWARD_DIR", tmp_path / "no-steward")
    result = qv.collect_questions(tmp_path / "no-decisions")  # include_clash defaults False
    assert result.questions == []


# ── render: grouping + empty contract ────────────────────────────────────────
def test_render_groups_and_header(tmp_path, monkeypatch):
    dp = tmp_path / "decisions-pending"
    dp.mkdir()
    (dp / "2026-06-15-rate-gate.md").write_text(DECISION)
    monkeypatch.setattr(qv, "STEWARD_DIR", tmp_path / "no-steward")
    section = qv.render_section(qv.collect_questions(tmp_path))
    assert section.startswith("## Questions for you")
    assert "###" in section  # at least one category group
    assert "`" in section    # ref is shown (clickable)


def test_render_empty_is_none():
    assert qv.render_section(qv.ViewResult()) is None


# ── predictions feeder: DUE predictions converge into the VIEW (single-sourced) ──
def test_predictions_feeder_due_only(tmp_path, monkeypatch):
    import json as _json

    import predictions
    ledger = tmp_path / "predictions.jsonl"
    rows = [
        {"id": "2020-01-01-old", "kind": "prediction", "change": "past change",
         "prediction": "X happens", "check_date": "2020-01-01"},
        {"id": "2099-01-01-future", "kind": "prediction", "change": "future change",
         "prediction": "Y happens", "check_date": "2099-01-01"},
    ]
    ledger.write_text("\n".join(_json.dumps(r) for r in rows) + "\n")
    monkeypatch.setattr(predictions, "LEDGER", ledger)
    monkeypatch.setattr(qv, "STEWARD_DIR", tmp_path / "no-steward")
    result = qv.collect_questions(tmp_path / "no-decisions")
    preds = [q for q in result.questions if q.source == "predictions"]
    assert len(preds) == 1  # only the DUE (past) one; the future one is not due
    assert "past change" in preds[0].prompt and preds[0].category == "governance"


def test_predictions_resolved_excluded(tmp_path, monkeypatch):
    import json as _json

    import predictions
    ledger = tmp_path / "predictions.jsonl"
    rows = [
        {"id": "2020-01-01-x", "kind": "prediction", "change": "c",
         "prediction": "p", "check_date": "2020-01-01"},
        {"id": "2020-01-01-x", "kind": "resolution", "status": "confirmed", "note": "done"},
    ]
    ledger.write_text("\n".join(_json.dumps(r) for r in rows) + "\n")
    monkeypatch.setattr(predictions, "LEDGER", ledger)
    monkeypatch.setattr(qv, "STEWARD_DIR", tmp_path / "no-steward")
    result = qv.collect_questions(tmp_path / "no-decisions")
    assert not [q for q in result.questions if q.source == "predictions"]  # resolved → not DUE


# ── stale predicate + drain hint (plan 17d2a35c-middle-manager-harvests) ────
def test_is_stale_predicate():
    from datetime import datetime, timedelta, timezone
    old = (datetime.now(timezone.utc) - timedelta(days=qv.STALE_DAYS + 5)).strftime("%Y-%m-%d")
    fresh = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    mk = lambda created: qv.Question(  # noqa: E731
        id="x", source="steward-proposals", category="tool",
        prompt="p", created=created, ref="/tmp/x.md",
    )
    assert qv.is_stale(mk(old))
    assert not qv.is_stale(mk(fresh))
    assert not qv.is_stale(mk(""))          # unparseable → not-stale (never crash)
    assert not qv.is_stale(mk("garbage"))


def test_render_surfaces_drain_verb_when_stale():
    from datetime import datetime, timedelta, timezone
    old = (datetime.now(timezone.utc) - timedelta(days=qv.STALE_DAYS + 5)).strftime("%Y-%m-%d")
    q = qv.Question(id="x", source="steward-proposals", category="tool",
                    prompt="ancient proposal", created=old, ref="/tmp/x.md")
    section = qv.render_section(qv.ViewResult(questions=[q]))
    assert "questions-drain --dispatch" in section
    assert "STALE" in section


def test_render_no_drain_verb_when_fresh():
    from datetime import datetime, timezone
    fresh = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    q = qv.Question(id="x", source="steward-proposals", category="tool",
                    prompt="new proposal", created=fresh, ref="/tmp/x.md")
    section = qv.render_section(qv.ViewResult(questions=[q]))
    assert "questions-drain" not in section


# ── human-md feeder (plan e3eceeaf: W1 open asks + W2 awaiting-agent fold) ───
ARC_STYLE = """# HUMAN.md — escalation outbox

Format (status tag: open | answered):
```
## YYYY-MM-DD HH:MM — <one-line ask>  STATUS
the call: <question>  [open]
```

## 2026-07-20 09:00 — Approve the eval budget bump  [open]
context: stage-2 needs $80
the call: yes/no?

## 2026-07-20 10:00 — Pick the corpus cutover date  [answered: Aug 1, go]
context: blocking the sync rewrite

## 2026-07-21 08:00 — Name the held-out reserve size  [answered: 20%]
consumed: 2026-07-21 abc1234 — reserve wired into splitter
"""

HUTTER_STYLE = """# HUMAN.md

### 2026-07-20 · restart the grinder with wider beam? · [open]
context: beam=8 plateaued

### 2026-07-01 · old pre-cutoff ask · [answered: yes]
never consumed, but ask predates the cutoff fence
"""


def _mk_projects(tmp_path, **files):
    root = tmp_path / "projects"
    for repo, text in files.items():
        d = root / repo
        d.mkdir(parents=True)
        (d / "HUMAN.md").write_text(text)
    return root


def test_human_md_open_asks_surface_both_grammars(tmp_path, monkeypatch):
    root = _mk_projects(tmp_path, arc=ARC_STYLE, hutter=HUTTER_STYLE)
    monkeypatch.setattr(qv, "HUMAN_MD_ROOT", root)
    result = qv.collect_questions(tmp_path)  # empty repo → only human-md feeds
    prompts = [q.prompt for q in result.questions]
    assert any("eval budget bump" in p for p in prompts)      # ## — style
    assert any("wider beam" in p for p in prompts)            # ### · style
    assert all(q.source == "human-md" for q in result.questions)
    assert len(result.questions) == 2  # fenced template line never counts


def test_human_md_fenced_template_excluded(tmp_path, monkeypatch):
    fence_only = "# H\n\n```\n## 2026-01-01 — template example  [open]\n```\n"
    monkeypatch.setattr(qv, "HUMAN_MD_ROOT", _mk_projects(tmp_path, r=fence_only))
    result = qv.collect_questions(tmp_path)
    assert result.questions == [] and result.awaiting_agent == []


def test_human_md_awaiting_agent_fold(tmp_path, monkeypatch):
    monkeypatch.setattr(qv, "HUMAN_MD_ROOT", _mk_projects(tmp_path, arc=ARC_STYLE, hutter=HUTTER_STYLE))
    result = qv.collect_questions(tmp_path)
    waiting = [q.prompt for q in result.awaiting_agent]
    # answered post-cutoff without consumed: → awaiting
    assert any("corpus cutover" in p for p in waiting)
    # answered WITH consumed: → not awaiting; pre-cutoff answered → grandfathered out
    assert not any("held-out reserve" in p for p in waiting)
    assert not any("old pre-cutoff" in p for p in waiting)
    assert len(result.awaiting_agent) == 1
    # awaiting rows never leak into the operator-question count
    assert not any("corpus cutover" in q.prompt for q in result.questions)


def test_human_md_awaiting_renders_own_subsection(tmp_path, monkeypatch):
    monkeypatch.setattr(qv, "HUMAN_MD_ROOT", _mk_projects(tmp_path, arc=ARC_STYLE))
    result = qv.collect_questions(tmp_path)
    section = qv.render_section(result)
    assert "Answers waiting on agents (1)" in section
    assert "consumed:" in section  # the pickup instruction names the marker


def test_human_md_nested_depth2_found(tmp_path, monkeypatch):
    root = tmp_path / "projects"
    d = root / "anim" / "evolver"
    d.mkdir(parents=True)
    (d / "HUMAN.md").write_text("## 2026-07-20 — nested ask  [open]\n")
    monkeypatch.setattr(qv, "HUMAN_MD_ROOT", root)
    result = qv.collect_questions(tmp_path)
    assert len(result.questions) == 1 and "nested ask" in result.questions[0].prompt


def test_human_md_bad_file_skipped_not_crash(tmp_path, monkeypatch):
    root = _mk_projects(tmp_path, ok=ARC_STYLE)
    bad = root / "bad"
    bad.mkdir()
    (bad / "HUMAN.md").mkdir()  # a DIRECTORY named HUMAN.md → read_text raises
    monkeypatch.setattr(qv, "HUMAN_MD_ROOT", root)
    result = qv.collect_questions(tmp_path)
    assert any("human-md/bad" in s for s in result.skipped)
    assert any("eval budget bump" in q.prompt for q in result.questions)  # peer survives


def test_human_md_absent_root_silent(tmp_path, monkeypatch):
    monkeypatch.setattr(qv, "HUMAN_MD_ROOT", tmp_path / "nowhere")
    result = qv.collect_questions(tmp_path)
    assert result.degraded == [] and result.questions == []
