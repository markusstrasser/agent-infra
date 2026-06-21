#!/usr/bin/env python3
"""maintain_tick.py — the MOTOR of the RSI loop (SAFE / dry-run by default).

Two symmetric passes:
  - ADD (default): drafts BUILD proposals for tier-0 candidates (run / --list).
  - SUBTRACT (--subtract): drafts RETIREMENT proposals — the governance-shrink half,
    a pure consumer of gov.py's report-only detectors + gov.route(). Telos: governance
    shrinks as capability rises (gov-id.md). The READ-ONLY ablation gate (--ablate)
    re-runs a scaffold's grader against a throwaway worktree with the scaffold REMOVED
    (live repo untouched) and folds the verdict into the draft. route stays human;
    actually auto-APPLYING a retirement is Phase 3 (apply lane + go_live, operator
    only). See run_subtract() / run_ablation().


The audit research/2026-06-19-auto-self-improvement-audit.md found the loop has
healthy sensors but no MOTOR: `/improve maintain` is interactive-only, the
launchd maintain job was eradicated 2026-06-07, and `maintain-tick` last ran
2026-06-14. tier-0 builds sit `[ ]` because nothing autonomously picks and ships
them. This is that picker — but it ships NOTHING on its own. It:

  1. gathers tier-0 candidates from two sources (structured registry + prose log),
  2. filters to TIER-0 = agent-infra-local AND reversible AND evidence>=2 sessions,
  3. picks ONE (oldest-evidence-first, deterministic),
  4. in SAFE/DRY-RUN (default) writes a DRAFT PROPOSAL to
     artifacts/maintain/<date>-<slug>.md — it does NOT edit code, commit, or deploy,
  5. appends the tick to maintenance-actions.jsonl (the existing ledger),
  6. rate-gates on a `claude` process cap so a launchd fire never piles onto a
     live interactive session.

Why a proposal and not an auto-edit: per the constitution's verifier-conditioned
autonomy + gov.py's DORMANT earned-autonomy gate (route(): local+high+0-reverts
+AUTO_APPLY_ENABLED → auto-apply, else human), the motor's safe contract is
"produce a reversible draft, recommend, leave the apply to a human or to an
explicitly-enabled apply lane." A draft proposal is reversible (it's a file the
operator reads), so it's the right safe-mode output. `--apply` exists for the
future apply lane but DEFAULTS OFF and additionally requires MAINTAIN_APPLY_ENABLED
(belt-and-suspenders: a stray --apply in a plist cannot ship code).

Scheduled (when wired): com.agent-infra.maintain-tick (30-60m, dry-run).
Manual: uv run python3 scripts/maintain_tick.py  (or with --json for the machine form).

GROUND TRUTH (verified 2026-06-19, recorded so a future reader doesn't re-derive):
  - improvement-log `[ ]` items carry NO machine-readable blast_radius /
    evidence_sessions / tier fields — they are free prose. So tier-0 cannot be
    filtered from the log by structured fields alone. The conservative parser here
    only auto-promotes a prose `[ ]` item to a tier-0 CANDIDATE when it
    self-describes as agent-infra-local AND low-severity in its own text; anything
    ambiguous is surfaced as "needs-classification" and never auto-picked.
  - The audit's named tier-0 items (continuation-misread hook, HUMAN.md grep) are
    NOT in the `[ ]` list — they live in the audit + steering-vectors memos. The
    structured registry config/maintain-candidates.json is where such named items
    get explicit tier fields so the motor can pick them safely.
"""
# Gov-ID: hook:maintain-tick-motor
# goal: ship the dead maintain-tick MOTOR so tier-0 agent-infra-local items don't
#       sit `[ ]` for days waiting for a human to start a /improve session — but
#       SAFE BY DEFAULT (draft proposal only; never auto-edit/commit/deploy)
# verifier: null  # the SAFE contract is structurally checkable (asserts no code
#                 # edit / no commit / no deploy in dry-run) via the test
#                 # scripts/tests/test_maintain_tick.py; promotion of the apply
#                 # lane needs a real grader on the produced diff
# blast_radius: local  # agent-infra-only: reads improvement-log + a local
#               # registry, writes a draft proposal + a ledger row. The launchd
#               # job (when wired) runs dry-run. The apply lane is double-gated off.
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
IMPROVEMENT_LOG = REPO / "improvement-log.md"
CANDIDATES_REGISTRY = REPO / "config" / "maintain-candidates.json"
# Single-source tier policy (authored + owned by the team-lead, operator-approved
# 2026-06-19). This module is a pure CONSUMER of it — it never restates the tier
# rules (epistemic-principle #9: a shared invariant has ONE definition; consumers
# LOAD it). The go-live flag and the tier→action map live there; we read them.
BUILD_AUTONOMY_POLICY = REPO / "config" / "build-autonomy-tiers.json"
PROPOSAL_DIR = REPO / "artifacts" / "maintain"
LEDGER = REPO / "maintenance-actions.jsonl"

# Rate gate: if more than this many `claude` processes are live, a launchd fire
# steps aside rather than racing an interactive session's git index / context.
# (Mirrors the existing pgrep-cap pattern; uses a self-non-matching class so the
# pgrep pattern text cannot match its own command line — remote-ssh-ops gotcha 2.)
MAX_LIVE_CLAUDE = 1

# Belt-and-suspenders for the apply lane: --apply alone is NOT enough; the
# environment must also opt in AND the policy's go_live flag must be true (triple
# gate, see _apply_allowed). A stray --apply in a plist cannot ship code.
APPLY_ENV_FLAG = "MAINTAIN_APPLY_ENABLED"

# A tier counts as auto-ship iff its policy `action` contains "auto-ship" AND
# none of the eval-gate disclaimers — the 0E action literally reads
# "EVAL-GATED auto-ship — NOT shipped on the tier rule", which contains the
# marker but is explicitly NOT auto-shipped by this consumer. Reading the
# policy's own language keeps the set derived (not hardcoded) yet correct.
_AUTO_SHIP_ACTION_MARKER = "auto-ship"
_AUTO_SHIP_DISQUALIFIERS = ("eval-gated", "not shipped", "decisions-pending", "principal only")


# ── build-autonomy policy (LOADED, never restated) ─────────────────────────────
def load_policy() -> dict:
    """Load config/build-autonomy-tiers.json. Returns {} on any failure — every
    consumer below treats {} as 'fail closed': no auto-ship tiers, apply gate OFF.
    The tier RULES stay in the JSON; we never re-encode them here."""
    try:
        return json.loads(BUILD_AUTONOMY_POLICY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def auto_ship_tiers(policy: dict) -> set[str]:
    """Tier names whose policy `action` is an auto-ship action (e.g. tier 0 and 1).
    Derived from the policy — NOT hardcoded — so adding/renaming a tier in the JSON
    flows through without touching this file. Fail-closed: {} policy → no tiers."""
    out: set[str] = set()
    for name, spec in (policy.get("tiers") or {}).items():
        action = str(spec.get("action", "")).lower()
        if _AUTO_SHIP_ACTION_MARKER in action and not any(
            d in action for d in _AUTO_SHIP_DISQUALIFIERS
        ):
            out.add(str(name))
    return out


def policy_min_evidence_sessions(policy: dict) -> int:
    """The evidence_sessions threshold, parsed from the tier-0 rule TEXT in the
    policy (the one numeric the prose rule states machine-recoverably:
    'evidence_sessions>=N'). Falls back to 2 (the constitution's recurs-2+ gate)
    only if the policy is unreadable or the rule omits it."""
    rule = str(((policy.get("tiers") or {}).get("0") or {}).get("rule", ""))
    m = re.search(r"evidence_sessions\s*>=\s*(\d+)", rule)
    return int(m.group(1)) if m else 2


def policy_tier0_blast(policy: dict) -> str:
    """The blast_radius value the tier-0 rule requires, parsed from the rule text
    ('blast_radius=<value>'). Fallback 'agent-infra'."""
    rule = str(((policy.get("tiers") or {}).get("0") or {}).get("rule", ""))
    m = re.search(r"blast_radius\s*=\s*([a-z0-9-]+)", rule)
    return m.group(1) if m else "agent-infra"


def _apply_allowed(apply_flag: bool, policy: dict) -> tuple[bool, str]:
    """Triple gate for the apply (auto-ship) lane. ALL THREE must hold:
      1. --apply passed on the CLI,
      2. env MAINTAIN_APPLY_ENABLED in {1,true,yes},
      3. policy go_live.maintain_tick_apply is true.
    Returns (allowed, reason-if-blocked). The policy flag is authoritative — its
    default-false means draft-only even if the operator forgets the other two."""
    if not apply_flag:
        return False, "no --apply"
    if os.environ.get(APPLY_ENV_FLAG, "").strip().lower() not in ("1", "true", "yes"):
        return False, f"{APPLY_ENV_FLAG} not enabled"
    if not bool((policy.get("go_live") or {}).get("maintain_tick_apply", False)):
        return False, "policy go_live.maintain_tick_apply is false"
    return True, ""


# Loaded ONCE at import (read-only config). Tests monkeypatch this to inject a
# fixture policy; the classify/gather functions read it so a single load is shared
# across a run. run() re-reads it (via load_policy()) for the apply gate so a
# policy edit between import and invocation is honored on the safety-critical path.
POLICY: dict = load_policy()

# Prose self-description gates for parsing improvement-log `[ ]` items into
# tier-0 CANDIDATES. Conservative by design: a prose item is only auto-promoted
# when it positively self-describes as agent-infra-local AND carries no
# escalation marker. Everything else is "needs-classification" (never picked).
_LOCAL_RE = re.compile(r"agent-infra-local|agent-infra only|local\b.*wiring|low-sev", re.I)
_ESCALATE_RE = re.compile(
    r"\bADR\b|ADR-candidate|cross-repo|cross-project|3\+ projects|shared\b|"
    r"steward|constitution|GOALS|hand to|hand off|owner:|policy choice|"
    r"design-laden|deliberately|do deliberately|genuine evaluate|worth an ADR",
    re.I,
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _slug(text: str, n: int = 6) -> str:
    words = re.findall(r"[a-z0-9]+", text.lower())
    stop = {"the", "a", "an", "to", "of", "for", "and", "with", "via", "into"}
    words = [w for w in words if w not in stop] or words
    return "-".join(words[:n]) or "candidate"


def live_claude_count() -> int:
    """Count live `claude` processes (self-non-matching pattern). Fail-open: on any
    error return 0 so a probe failure never wedges the motor (it just won't gate)."""
    try:
        r = subprocess.run(
            ["pgrep", "-fc", r"[c]laude"],
            capture_output=True, text=True, timeout=5,
        )
        return int((r.stdout or "0").strip() or 0)
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return 0


# ── candidate sourcing ─────────────────────────────────────────────────────────
def _from_registry() -> list[dict]:
    """Structured tier-0 candidates. This is the PREFERRED source — explicit
    fields, no prose inference. Schema per item:
        {id, title, blast_radius, reversible(bool), evidence_sessions(int),
         source(str), build_kind(str: hook|script|recipe|rule),
         proposal_outline(str), [done(bool)]}
    Tier-0-ONLY predicates the policy names but that are NOT mechanically derivable
    (semantic): checkable, low_downside, clear_win_vs_baseline. The registry
    declares them per candidate. They DEFAULT FALSE — an item that doesn't assert
    them is NOT a clear tier-0 win and routes to 0E (eval-gated), never auto-ship.
    """
    if not CANDIDATES_REGISTRY.exists():
        return []
    try:
        data = json.loads(CANDIDATES_REGISTRY.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError, OSError):
        return []
    out: list[dict] = []
    for item in data.get("candidates", []):
        if item.get("done"):
            continue
        out.append({
            "origin": "registry",
            "id": item.get("id") or _slug(item.get("title", "")),
            "title": item.get("title", "(untitled)"),
            "blast_radius": (item.get("blast_radius") or "").lower(),
            "reversible": bool(item.get("reversible", False)),
            "evidence_sessions": int(item.get("evidence_sessions", 0) or 0),
            # tier-0-only semantic predicates — DEFAULT FALSE (conservative).
            "checkable": bool(item.get("checkable", False)),
            "low_downside": bool(item.get("low_downside", False)),
            "clear_win_vs_baseline": bool(item.get("clear_win_vs_baseline", False)),
            "source": item.get("source", ""),
            "build_kind": item.get("build_kind", ""),
            "proposal_outline": item.get("proposal_outline", ""),
        })
    return out


def _from_improvement_log() -> list[dict]:
    """Prose `[ ]` items, conservatively classified. A prose item becomes a tier-0
    candidate ONLY if it self-describes as agent-infra-local and carries no
    escalation marker; otherwise it is returned with classified=False so the
    picker skips it (and so the digest can show "N items need classification")."""
    if not IMPROVEMENT_LOG.exists():
        return []
    out: list[dict] = []
    for raw in IMPROVEMENT_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line.startswith("- [ ]"):
            continue
        body = line[len("- [ ]"):].strip()
        title = re.sub(r"\*\*", "", body)[:120]
        is_local = bool(_LOCAL_RE.search(body))
        escalates = bool(_ESCALATE_RE.search(body))
        classified = is_local and not escalates
        out.append({
            "origin": "improvement-log",
            "id": _slug(title),
            "title": title,
            # prose carries no explicit blast/evidence — encode what we inferred.
            "blast_radius": policy_tier0_blast(POLICY) if classified else "unclassified",
            "reversible": classified,         # only the self-described-local pass
            "evidence_sessions": policy_min_evidence_sessions(POLICY) if classified else 0,
            # Prose items can NEVER assert the semantic tier-0 predicates, so they
            # stay False → a self-described-local prose item lands at 0E (eval-
            # gated), never auto-ship. That is the intended conservative routing.
            "checkable": False,
            "low_downside": False,
            "clear_win_vs_baseline": False,
            "classified": classified,
            "source": "improvement-log.md",
            "build_kind": "",
            "proposal_outline": body,
        })
    return out


def classify_tier(c: dict, policy: dict) -> str:
    """Assign a candidate to a policy tier. Returns the tier NAME ('0','0E','1',
    '2','3') or '' (unclassifiable — skipped). Loads the gate VALUES from the
    policy; it does NOT restate the policy's prose rule (that string stays the
    single human-readable source). The decision is the AND of the policy's
    machine-recoverable tier-0 predicates:

      tier-0  = blast_radius==policy_tier0_blast AND reversible
                AND evidence_sessions>=policy_threshold
                AND checkable AND low_downside AND clear_win_vs_baseline
      0E      = (local AND reversible) but NOT a clear low-risk win
                (missing any of checkable/low_downside/clear_win_vs_baseline)
      else    -> not auto-shippable here (shared/constitution → '2'/'3' upstream;
                 this consumer only acts on auto-ship tiers, so it returns '' for
                 anything not 0/0E, letting the caller route it to needs-attention)

    Highest-tier-wins (policy invariant): a non-local / shared item is never 0/0E
    even if it happens to be reversible — the blast check fails first.
    """
    local = (c.get("blast_radius") == policy_tier0_blast(policy))
    reversible = bool(c.get("reversible"))
    enough_evidence = int(c.get("evidence_sessions", 0)) >= policy_min_evidence_sessions(policy)
    if not (local and reversible and enough_evidence):
        return ""  # not even in the tier-0 LOCATION (or too little evidence)
    clear_win = (
        bool(c.get("checkable"))
        and bool(c.get("low_downside"))
        and bool(c.get("clear_win_vs_baseline"))
    )
    return "0" if clear_win else "0E"


def gather_candidates() -> dict:
    reg = _from_registry()
    log = _from_improvement_log()
    all_items = reg + log
    for c in all_items:
        c["tier"] = classify_tier(c, POLICY)
    tier0 = [c for c in all_items if c["tier"] == "0"]
    eval_gated = [c for c in all_items if c["tier"] == "0E"]
    # registry items first (explicit > inferred); then by lowest evidence_sessions
    # so the longest-standing-but-just-qualifying item isn't starved, then by id
    # for determinism.
    tier0.sort(key=lambda c: (c["origin"] != "registry", c["evidence_sessions"], c["id"]))
    eval_gated.sort(key=lambda c: (c["origin"] != "registry", c["evidence_sessions"], c["id"]))
    needs_classification = [
        c for c in log if not c.get("classified")
    ]
    return {
        "tier0": tier0,
        "eval_gated": eval_gated,
        "needs_classification": needs_classification,
        "n_registry": len(reg),
        "n_log_open": len(log),
        "auto_ship_tiers": sorted(auto_ship_tiers(POLICY)),
    }


# ── proposal drafting (the SAFE output) ────────────────────────────────────────
def draft_proposal(c: dict) -> tuple[Path, str]:
    slug = c["id"]
    path = PROPOSAL_DIR / f"{_today()}-{slug}.md"
    outline = c.get("proposal_outline") or c.get("title")
    build_kind = c.get("build_kind") or "(infer from item)"
    body = f"""---
title: "Maintain-tick draft proposal — {c['title']}"
date: {_today()}
status: draft-proposal
generated_by: scripts/maintain_tick.py (SAFE/dry-run)
candidate_origin: {c['origin']}
candidate_source: {c.get('source','')}
tier: {c.get('tier','?')}
blast_radius: {c['blast_radius']}
reversible: {c['reversible']}
evidence_sessions: {c['evidence_sessions']}
---

# Maintain-tick draft proposal

> This is a DRAFT produced by the maintain-tick motor in SAFE/dry-run mode.
> No code was edited, no commit made, no job deployed. A human (or the explicitly
> enabled apply lane) decides whether to build it. Reversible by construction.

## Candidate
**{c['title']}**

- Origin: `{c['origin']}`  ·  Source: `{c.get('source','')}`  ·  Tier (per config/build-autonomy-tiers.json): `{c.get('tier','?')}`
- Tier-0 gate: blast_radius=`{c['blast_radius']}` · reversible=`{c['reversible']}` · evidence_sessions=`{c['evidence_sessions']}` ≥ {policy_min_evidence_sessions(POLICY)} · checkable=`{c.get('checkable')}` · low_downside=`{c.get('low_downside')}` · clear_win_vs_baseline=`{c.get('clear_win_vs_baseline')}`
- Build kind: {build_kind}

## What the item asks for
{outline}

## Proposed approach (draft — operator to confirm/replace)
1. Read the source ({c.get('source','the item')}) and any prior context it cites.
2. Build the smallest correct version (Pre-Build #4) as a NEW file under the
   agent-infra-local convention (`scripts/` or `scripts/hooks/`).
3. Add a test mirroring an existing sibling test; run it.
4. If it's a hook, output (do NOT auto-apply) the `.claude/settings.json` snippet.
5. Mark the improvement-log item `[x]` with the implementing commit, OR set
   `done: true` on the registry entry.

## Safety / tier check (policy: config/build-autonomy-tiers.json)
- [x] agent-infra-local (blast_radius=agent-infra)
- [x] reversible
- [x] evidence_sessions ≥ {policy_min_evidence_sessions(POLICY)}
- [x] tier-0 clear-win predicates (checkable + low_downside + clear_win_vs_baseline)
- [ ] operator approved build  ← gate before any code lands (and go_live.maintain_tick_apply flip = tier-3, operator only)

## Next
- Build: open a session and implement per the approach above.
- Or reject: set `done: true` (registry) / mark `[-]` (log) with a one-line reason.
"""
    return path, body


# ── ledger ─────────────────────────────────────────────────────────────────────
def append_ledger(action: str, target: str, result: str, detail: str) -> None:
    row = {"ts": _now(), "action": action, "target": target,
           "result": result, "detail": detail}
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


# ── SUBTRACT pass (governance SHRINK — the symmetric half) ──────────────────────
# The motor only GREW: it drafts BUILDS. The constitution's telos is that
# governance SHRINKS as capability rises (gov-id.md). This is the symmetric half —
# it drafts RETIREMENTS. It is a pure CONSUMER of gov.py's report-only detectors
# (epistemic-#9: LOAD the canonical detector, never re-detect) and of gov.route()
# (the existing earned-autonomy router). SAFE/dry-run: drafts a retirement proposal
# for human review; it removes nothing. The auto-retire gate is the ABLATION runner
# (re-run a scaffold's grader with the scaffold REMOVED, retire only if still PASS)
# — Phase 2, not built here. Until it exists, every candidate routes to human
# because route_retire() passes confidence="medium" (route() needs "high" for auto).
def gather_retire_candidates(days: int = 60) -> dict:
    """Retire-candidates from gov.py, two streams mirroring the add-motor's
    registry+log sources:
      - gov-shrink: a Gov-ID scaffold WITH a verifier whose goal currently HOLDS
        (verdict.passed is True). Goal-holds-WITH-the-scaffold is necessary but NOT
        sufficient — the auto-retire gate is the ablation (re-run WITHOUT it). So
        these are ABLATION-PENDING, drafted human-gated here.
      - advisory-noise: a high-fire advisory-only hook (gov hardcodes blast=shared)
        → quarantine/delete candidate. shared ⇒ always human-gated.
    Returns {shrink_pending, advisory_noise, n_eligible, n_backlog[, error]}.
    """
    try:
        import gov  # lazy: heavy import chain (graders, agentlogs); no cycle (gov ⊅ this)
    except Exception as e:  # noqa: BLE001
        return {"shrink_pending": [], "advisory_noise": [], "n_eligible": 0,
                "n_backlog": 0, "error": f"gov import failed: {str(e)[:120]}"}
    try:
        artifacts = gov.collect_artifacts()
        shrink = gov.gov_shrink_dryrun(artifacts)
        noise = gov.advisory_noise(days)
    except Exception as e:  # noqa: BLE001
        return {"shrink_pending": [], "advisory_noise": [], "n_eligible": 0,
                "n_backlog": 0, "error": f"gov detectors failed: {str(e)[:120]}"}
    shrink_pending = []
    for a in shrink.get("eligible", []):
        v = a.get("verdict") or {}
        if v.get("passed") is True:  # goal holds WITH the scaffold → ablation candidate
            shrink_pending.append({
                "origin": "gov-shrink",
                "id": _slug(str(a.get("id", ""))) or str(a.get("id", "")),
                "gov_id": a.get("id", ""),
                "title": f"retire scaffold {a.get('id','')} — goal holds (ablation-pending)",
                "blast_radius": (a.get("blast_radius") or "local"),
                "retire_kind": "scaffold-shrink",
                "verifier": a.get("verifier") or "",
                "verdict": "PASS (goal holds WITH scaffold; ablation needed to confirm WITHOUT)",
                "goal": a.get("goal", ""),
                "artifact_path": a.get("path", ""),
                "evidence": (str(v.get("evidence") or ""))[:200],
                "source": "scripts/gov.py: gov_shrink_dryrun",
            })
    advisory = []
    for n in noise:
        advisory.append({
            "origin": "advisory-noise",
            "id": _slug(str(n.get("hook", ""))) or str(n.get("hook", "")),
            "gov_id": n.get("hook", ""),
            "title": f"retire/quarantine advisory hook {n.get('hook','')} — fires without changing behavior",
            "blast_radius": (n.get("blast_radius") or "shared"),
            "retire_kind": "advisory-noise",
            "verifier": "",
            "verdict": "",
            "goal": "",
            "artifact_path": "",
            "evidence": n.get("evidence", ""),
            "disposition": n.get("disposition", ""),
            "source": "scripts/gov.py: advisory_noise",
        })
    return {"shrink_pending": shrink_pending, "advisory_noise": advisory,
            "n_eligible": len(shrink.get("eligible", [])),
            "n_backlog": len(shrink.get("backlog", []))}


# ── ablation runner (the auto-retire GATE — READ-ONLY, worktree-isolated) ────────
def _run_grader_against(verifier: str, repo_path: Path) -> dict | None:
    """Import a governance grader (from gov.GRADERS_ROOT — the evals sibling) and run
    grade(repo_path). Parameterized mirror of gov.run_grader so the SAME grader code
    can score a DIFFERENT repo state (an ablated worktree). Returns {passed, margin,
    evidence} or None if the grader file is absent. passed=None on grader error."""
    try:
        import gov
        grader_file = (gov.GRADERS_ROOT / verifier).resolve()
    except Exception as e:  # noqa: BLE001
        return {"passed": None, "margin": None, "evidence": f"(gov/grader-path error: {str(e)[:100]})"}
    if not grader_file.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(grader_file.stem, grader_file)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        v = mod.grade(repo_path)
        return {"passed": bool(v["passed"]), "margin": v.get("margin"),
                "evidence": str(v.get("evidence", ""))}
    except Exception as e:  # noqa: BLE001
        return {"passed": None, "margin": None, "evidence": f"(grader error: {str(e)[:120]})"}


def _path_confined(worktree: Path, art_path: str) -> bool:
    """READ-ONLY guard for ablation: True iff worktree/art_path stays INSIDE worktree.
    An ABSOLUTE art_path makes `worktree / art_path` discard the worktree (Path drops
    the lhs on an absolute rhs) and a `..`-escaping path resolves outside it — either
    would let unlink() touch the LIVE repo. gov yields repo-relative paths today, but
    run_ablation accepts any dict, so this is defense-in-depth, not decoration."""
    try:
        return (worktree / art_path).resolve().is_relative_to(worktree.resolve())
    except (OSError, ValueError):
        return False


def _ablation_verdict(before: dict | None, after: dict | None) -> dict:
    """PURE decision from the with-scaffold (before) and without-scaffold (after)
    grader verdicts. FAIL-CLOSED: BOTH must be conclusive, else ablated=None — an
    inconclusive baseline cannot attribute a without-scaffold PASS to the scaffold.
    An unchanged verdict (grader insensitive to the file, or hardcodes a repo path)
    is also inconclusive. Only a conclusive, CHANGED verdict yields True/False."""
    if before is None or before.get("passed") is None:
        return {"ablated": None, "evidence": f"grader inconclusive WITH scaffold (baseline) — cannot ablate: {before}"}
    if after is None or after.get("passed") is None:
        return {"ablated": None, "evidence": f"grader inconclusive WITHOUT scaffold: {after}"}
    if before.get("passed") == after.get("passed") and before.get("margin") == after.get("margin"):
        return {"ablated": None,
                "evidence": f"grader verdict identical with/without scaffold "
                            f"(passed={after['passed']}, margin={after.get('margin')}) — "
                            f"insensitive to this file; ablation inconclusive"}
    return {"ablated": bool(after["passed"]),
            "evidence": f"grader WITHOUT scaffold: passed={after['passed']} "
                        f"margin={after.get('margin')} — {after.get('evidence','')}"}


def run_ablation(candidate: dict) -> dict:
    """SAFETY-CRITICAL but strictly READ-ONLY. Decide whether a scaffold's GOAL still
    holds WITHOUT the scaffold, by re-running its grader against a throwaway git
    worktree at HEAD with the scaffold file REMOVED. The LIVE repo is NEVER mutated:
    the worktree is a separate checkout, the file is removed only there, and the
    worktree is torn down in `finally`.

    Returns {ablated: bool|None, evidence: str}:
      - ablated True  → goal STILL PASSES without the scaffold ⇒ training wheels, removable.
      - ablated False → goal FAILS without it ⇒ load-bearing, KEEP.
      - ablated None  → inconclusive (no verifier, worktree/grader error, or grader
        proved insensitive to the file). FAIL-CLOSED: an inconclusive ablation NEVER
        upgrades a candidate toward retirement — the human still decides.
    """
    verifier = candidate.get("verifier") or ""
    art_path = candidate.get("artifact_path") or ""
    if not verifier or not art_path:
        return {"ablated": None, "evidence": "no verifier or artifact_path → cannot ablate"}
    wt = Path(tempfile.gettempdir()) / f"ablate-wt-{os.getpid()}-{candidate.get('id','x')[:24]}"
    created = False
    try:
        r = subprocess.run(
            ["git", "-C", str(REPO), "worktree", "add", "--detach", str(wt), "HEAD"],
            capture_output=True, text=True, timeout=90)
        if r.returncode != 0:
            return {"ablated": None, "evidence": f"worktree add failed: {(r.stderr or '')[:120]}"}
        created = True
        target = wt / art_path
        # READ-ONLY confinement FIRST (before any fs op): refuse a path that escapes
        # the worktree so unlink() can never touch the live repo (Finding 1).
        if not _path_confined(wt, art_path):
            return {"ablated": None,
                    "evidence": f"artifact_path {art_path} escapes the worktree — refused (READ-ONLY guard)"}
        if not target.exists():
            return {"ablated": None, "evidence": f"scaffold {art_path} not present at HEAD in worktree"}
        before = _run_grader_against(verifier, wt)        # with the scaffold
        target.unlink()                                    # ablate: remove ONLY in the worktree
        after = _run_grader_against(verifier, wt)           # without the scaffold
        return _ablation_verdict(before, after)             # pure, fail-closed on both
    except Exception as e:  # noqa: BLE001
        return {"ablated": None, "evidence": f"ablation error: {str(e)[:120]}"}
    finally:
        if created:
            subprocess.run(["git", "-C", str(REPO), "worktree", "remove", "--force", str(wt)],
                           capture_output=True, text=True, timeout=30)
        shutil.rmtree(wt, ignore_errors=True)  # belt-and-suspenders if remove left a stub


def resolve_predictions_for_ablation(candidate: dict, ablation: dict,
                                   *, dry_run: bool = False) -> list[str]:
    """When ablation is conclusive, close matching earn-its-keep predictions.

    ablated=True  → refuted   (goal holds without scaffold; didn't earn keep)
    ablated=False → confirmed (load-bearing)
    Matches conservatively: gov_id or artifact basename in prediction change text.
    """
    if ablation.get("ablated") is None:
        return []
    try:
        import predictions as pred
    except Exception:  # noqa: BLE001
        return []
    preds, resolved = pred._load()
    gov_id = (candidate.get("gov_id") or "").strip()
    art_name = Path(candidate.get("artifact_path") or "").name
    needles = [n for n in (gov_id, art_name) if n and len(n) >= 4]
    if not needles:
        return []
    status = "refuted" if ablation["ablated"] else "confirmed"
    note = (f"auto: ablation ablated={ablation['ablated']}: "
            f"{(ablation.get('evidence') or '')[:220]}")
    acted: list[str] = []
    for pid, p in preds.items():
        if pid in resolved:
            continue
        change = p.get("change", "")
        if not any(n in change for n in needles):
            continue
        if not dry_run:
            pred._append_resolution(pid, status, note)
        acted.append(pid)
    return acted


def route_retire(c: dict) -> str:
    """Reuse gov.route() (the canonical earned-autonomy router) — never restate it.
    confidence is pinned "medium" pre-ablation so route() can NEVER return auto-apply
    (it requires "high"). After the ablation runner confirms WITHOUT-scaffold PASS
    (Phase 2), a local scaffold may pass confidence="high" and become auto-eligible
    (still behind AUTO_APPLY_ENABLED + the policy go_live flag)."""
    try:
        import gov
        return gov.route(c.get("blast_radius", "shared"), "medium", 0)
    except Exception:  # noqa: BLE001
        return "human"  # fail-closed: unknown router → human


def draft_retire_proposal(c: dict) -> tuple[Path, str]:
    slug = f"retire-{c['id']}"
    path = PROPOSAL_DIR / f"{_today()}-{slug}.md"
    route = route_retire(c)
    if c["retire_kind"] == "scaffold-shrink":
        abl = c.get("ablation")
        if abl and abl.get("ablated") is True:
            gate = (f"**Ablation PASSED — the auto-gate is satisfied.** {abl.get('evidence','')} "
                    f"The goal holds WITHOUT the scaffold ⇒ training wheels. Mark `[~]` retired and "
                    f"remove the artifact. (Actually auto-applying still requires the apply lane + "
                    f"go_live.maintain_tick_apply + AUTO_APPLY_ENABLED — operator only; this is a draft.)")
        elif abl and abl.get("ablated") is False:
            gate = (f"**Ablation FAILED — KEEP the scaffold (load-bearing).** {abl.get('evidence','')} "
                    f"The goal FAILS without it; do NOT retire — drop this candidate.")
        elif abl:  # ablated is None → inconclusive (fail-closed)
            gate = (f"**Ablation INCONCLUSIVE.** {abl.get('evidence','')} Cannot auto-confirm; "
                    f"human decides — treat as KEEP until a conclusive ablation.")
        else:
            gate = (f"**Ablation NOT run** (pass `--ablate`). Re-run the verifier "
                    f"`{c.get('verifier','')}` with the scaffold REMOVED; mark `[~]` retired ONLY if it "
                    f"still PASSES (training wheels). Current grader verdict (WITH the scaffold): "
                    f"{c.get('verdict','')}.")
    else:
        gate = (f"**Advisory-only hook**, {c.get('evidence','')}, with no measured behavior change. "
                f"Disposition: {c.get('disposition','')}. blast_radius=shared ⇒ human-gated — never "
                f"auto-BLOCK and never auto-delete a shared hook; the operator quarantines/deletes.")
    body = f"""---
title: "Maintain-tick RETIRE draft — {c['gov_id']}"
date: {_today()}
status: draft-retire-proposal
generated_by: scripts/maintain_tick.py --subtract (SAFE/dry-run)
retire_kind: {c['retire_kind']}
blast_radius: {c['blast_radius']}
route: {route}
verifier: {c.get('verifier','')}
---

# Maintain-tick RETIRE draft (governance SHRINK)

> SAFE/dry-run: nothing was removed, no commit, no governance write. This drafts a
> RETIREMENT for human review (or, once the ablation gate + earned-autonomy exist,
> the apply lane). Telos: governance shrinks as capability rises (gov-id.md).
> Reversible by construction — it is a file the operator reads.

## Candidate to retire
**{c['title']}**

- Origin: `{c['origin']}`  ·  Source: `{c['source']}`  ·  Route: **{route}**
- blast_radius: `{c['blast_radius']}`  ·  retire_kind: `{c['retire_kind']}`
- Artifact: `{c.get('artifact_path') or c['gov_id']}`
- Verifier: `{c.get('verifier') or '(none — advisory-noise)'}`
- Evidence: {c.get('evidence','')}

## The retire gate (NOT yet satisfied by this draft)
{gate}

## Proposed lifecycle marking (gov-id.md) — operator (or earned-autonomy actor) applies
1. Confirm the gate above (ablation PASS for a scaffold; operator decision for advisory-noise).
2. Mark the improvement-log entry `[~]` retired (cite the ablation verdict / decay evidence),
   OR `[>]` superseded-by `<id>` if a replacement exists.
3. Remove the scaffold artifact (`{c.get('artifact_path') or c['gov_id']}`) in the SAME commit
   that records the marking, with an `Evidence:` trailer (governance commit).

## Next
- Confirm + apply: satisfy the gate, then make the marking + removal commit.
- Or reject: leave the scaffold; note why (it is still load-bearing) — append one `[obs]` line.
"""
    return path, body


def run_subtract(force: bool, ledger: bool, days: int = 60, ablate: bool = False) -> dict:
    """SAFE/dry-run subtract tick: gather retire-candidates from gov, pick one
    deterministically, draft a retirement proposal. Removes nothing. With ablate=True,
    runs the READ-ONLY ablation gate on the picked shrink candidate (worktree-isolated
    grader re-run without the scaffold) and folds the verdict into the draft. The apply
    lane (actual removal) is Phase 3; route stays human here. Same rate-gate as add."""
    live = live_claude_count()
    if not force and live > MAX_LIVE_CLAUDE:
        if ledger:
            append_ledger("maintain-subtract", "rate-gate", "skipped",
                          f"{live} live claude procs > {MAX_LIVE_CLAUDE}; stood aside")
        return {"status": "rate-gated", "live_claude": live, "picked": None}
    g = gather_retire_candidates(days)
    if g.get("error"):
        if ledger:
            append_ledger("maintain-subtract", "scan", "error", g["error"])
        return {"status": "error", "picked": None, "error": g["error"]}
    cands = g["shrink_pending"] + g["advisory_noise"]
    if not cands:
        if ledger:
            append_ledger("maintain-subtract", "scan", "noop",
                          f"0 retire-candidates (shrink_eligible={g['n_eligible']}, "
                          f"backlog={g['n_backlog']})")
        return {"status": "noop", "picked": None,
                "n_eligible": g["n_eligible"], "n_backlog": g["n_backlog"]}
    # deterministic: real shrink loop first (gov-shrink), then advisory-noise; by id.
    cands.sort(key=lambda c: (c["origin"] != "gov-shrink", c["id"]))
    picked = cands[0]
    # The READ-ONLY ablation gate (opt-in) — only meaningful for a scaffold with a
    # verifier; advisory-noise has none. Folds {ablated, evidence} into the draft.
    if ablate and picked.get("retire_kind") == "scaffold-shrink":
        picked["ablation"] = run_ablation(picked)
        abl = picked.get("ablation") or {}
        if abl.get("ablated") is not None:
            picked["predictions_resolved"] = resolve_predictions_for_ablation(picked, abl)
    path, body = draft_retire_proposal(picked)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    if ledger:
        abl = picked.get("ablation") or {}
        append_ledger("maintain-subtract", picked["gov_id"], "drafted",
                      f"retire draft -> {path.relative_to(REPO)} "
                      f"(origin={picked['origin']}, route={route_retire(picked)}, "
                      f"ablated={abl.get('ablated', 'not-run')})")
    return {
        "status": "drafted",
        "picked": {k: picked.get(k) for k in ("id", "gov_id", "title", "origin",
                                              "blast_radius", "retire_kind")},
        "route": route_retire(picked),
        "ablation": picked.get("ablation"),
        "proposal_path": str(path.relative_to(REPO)),
        "shrink_pending": len(g["shrink_pending"]),
        "advisory_noise": len(g["advisory_noise"]),
    }


# ── main ───────────────────────────────────────────────────────────────────────
def run(apply: bool, force: bool, ledger: bool) -> dict:
    """Returns a result dict (also the --json payload). Never raises for normal
    'nothing to do' / 'rate-gated' paths — those are results, not errors."""
    # Rate gate (skip with --force, e.g. for the test / manual run).
    live = live_claude_count()
    if not force and live > MAX_LIVE_CLAUDE:
        if ledger:
            append_ledger("maintain-tick", "rate-gate",
                          "skipped", f"{live} live claude procs > {MAX_LIVE_CLAUDE}; stood aside")
        return {"status": "rate-gated", "live_claude": live, "picked": None}

    g = gather_candidates()
    tier0 = g["tier0"]
    if not tier0:
        if ledger:
            append_ledger("maintain-tick", "scan", "noop",
                          f"0 tier-0 candidates (registry={g['n_registry']}, "
                          f"log_open={g['n_log_open']}, eval_gated={len(g['eval_gated'])}, "
                          f"need-classify={len(g['needs_classification'])})")
        return {"status": "noop", "picked": None,
                "n_registry": g["n_registry"], "n_log_open": g["n_log_open"],
                "eval_gated_count": len(g["eval_gated"]),
                "eval_gated": [c["title"] for c in g["eval_gated"]],
                "needs_classification": [c["title"] for c in g["needs_classification"]]}

    picked = tier0[0]

    # --- APPLY LANE (TRIPLE-gated by the policy; deliberately a stub) ---
    # Re-read the policy here (not the import-time snapshot) so a go_live flip is
    # honored on the safety-critical path even mid-process.
    apply_allowed, apply_block_reason = _apply_allowed(apply, load_policy())
    if apply and not apply_allowed:
        # --apply was passed but a gate blocked it (env or policy flag) — fall
        # back to dry-run draft and record WHY.
        if ledger:
            append_ledger("maintain-tick", picked["id"], "apply-refused",
                          f"--apply set but blocked: {apply_block_reason}; "
                          "falling back to dry-run draft")
    elif apply_allowed:
        # The actual code-shipping path is intentionally NOT implemented in this
        # safe build. Promoting it requires implementing the apply path + a grader
        # on the produced diff + operator sign-off (manifest GO-LIVE). Even fully
        # gated-open, an enabled apply lane STILL only drafts — loudly.
        if ledger:
            append_ledger("maintain-tick", picked["id"], "apply-stub",
                          "apply lane fully gated-open but not implemented in safe "
                          "build; drafted instead — promote per manifest before shipping code")

    # --- SAFE/DRY-RUN: draft a proposal ---
    mode = "apply-stub" if apply_allowed else "dry-run"
    path, body = draft_proposal(picked)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    if ledger:
        append_ledger("maintain-tick", picked["id"], "drafted",
                      f"draft proposal -> {path.relative_to(REPO)} "
                      f"(origin={picked['origin']}, tier={picked.get('tier')}, mode={mode})")
    return {
        "status": "drafted",
        "mode": mode,
        "picked": {k: picked[k] for k in ("id", "title", "origin", "blast_radius",
                                          "reversible", "evidence_sessions", "tier")},
        "proposal_path": str(path.relative_to(REPO)),
        "tier0_count": len(tier0),
        "eval_gated_count": len(g["eval_gated"]),
        "eval_gated": [c["title"] for c in g["eval_gated"]],
        "needs_classification": [c["title"] for c in g["needs_classification"]],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="maintain-tick motor (SAFE/dry-run by default)")
    ap.add_argument("--apply", action="store_true",
                    help=f"ENABLE apply lane (still requires {APPLY_ENV_FLAG}=1; "
                         "off by default; in this safe build it still only drafts)")
    ap.add_argument("--force", action="store_true",
                    help="skip the live-claude rate gate (manual/test use)")
    ap.add_argument("--no-ledger", action="store_true",
                    help="do not append to maintenance-actions.jsonl (test use)")
    ap.add_argument("--json", action="store_true", help="machine-readable result")
    ap.add_argument("--list", action="store_true",
                    help="list candidates, pick nothing (ADD tier-0/0E, or with --subtract the retire-candidates)")
    ap.add_argument("--subtract", action="store_true",
                    help="run the SUBTRACT pass: draft governance RETIREMENTS from gov.py "
                         "detectors (the symmetric shrink half). SAFE/dry-run; removes nothing.")
    ap.add_argument("--ablate", action="store_true",
                    help="(with --subtract) run the READ-ONLY ablation gate: re-run each shrink "
                         "candidate's grader with the scaffold REMOVED in a throwaway worktree "
                         "(live repo untouched) and fold the verdict into the draft.")
    args = ap.parse_args()

    # ── SUBTRACT pass (governance shrink) ──
    if args.subtract:
        if args.list:
            g = gather_retire_candidates()
            if args.ablate and not g.get("error"):
                for c in g.get("shrink_pending", []):
                    c["ablation"] = run_ablation(c)
            if args.json:
                print(json.dumps({
                    "shrink_pending": [{**{k: c[k] for k in ("gov_id", "blast_radius", "verifier")},
                                        "ablation": c.get("ablation")}
                                       for c in g.get("shrink_pending", [])],
                    "advisory_noise": [{"hook": c["gov_id"], "blast_radius": c["blast_radius"]}
                                       for c in g.get("advisory_noise", [])],
                    "n_eligible": g.get("n_eligible", 0), "n_backlog": g.get("n_backlog", 0),
                    "error": g.get("error"),
                }, indent=2))
            else:
                if g.get("error"):
                    print(f"[maintain-subtract] gov detectors unavailable: {g['error']}")
                    return 0
                print(f"[maintain-subtract] retire-candidates: "
                      f"shrink-pending={len(g['shrink_pending'])} · "
                      f"advisory-noise={len(g['advisory_noise'])} "
                      f"(shrink-eligible={g['n_eligible']}, backlog={g['n_backlog']})"
                      f"{' · ablation ON' if args.ablate else ' (ablation: pass --ablate)'}")
                for c in g["shrink_pending"]:
                    abl = c.get("ablation")
                    asfx = f", ablated={abl.get('ablated')}" if abl else ""
                    print(f"  ⌫ [shrink] {c['gov_id']}  (blast={c['blast_radius']}, route={route_retire(c)}{asfx})")
                for c in g["advisory_noise"]:
                    print(f"  ⌫ [noise]  {c['gov_id']}  (route={route_retire(c)})")
            return 0
        res = run_subtract(force=args.force, ledger=not args.no_ledger, ablate=args.ablate)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            st = res["status"]
            if st == "drafted":
                print(f"[maintain-subtract] drafted retire proposal: {res['proposal_path']}")
                abl = res.get("ablation")
                asfx = f"  ablated={abl.get('ablated')}" if abl else ""
                print(f"  picked: {res['picked']['title']}  (route={res['route']}){asfx}")
            elif st == "rate-gated":
                print(f"[maintain-subtract] rate-gated: {res['live_claude']} live claude procs — stood aside.")
            elif st == "error":
                print(f"[maintain-subtract] error: {res['error']}")
            else:
                print(f"[maintain-subtract] noop: 0 retire-candidates "
                      f"(shrink-eligible={res.get('n_eligible')}, backlog={res.get('n_backlog')}).")
        return 0

    if args.list:
        g = gather_candidates()
        go_live = bool((load_policy().get("go_live") or {}).get("maintain_tick_apply", False))
        if args.json:
            print(json.dumps({
                "tier0": [{k: c[k] for k in ("id", "title", "origin", "evidence_sessions")}
                          for c in g["tier0"]],
                "eval_gated_0E": [{"id": c["id"], "title": c["title"], "origin": c["origin"]}
                                  for c in g["eval_gated"]],
                "needs_classification": [c["title"] for c in g["needs_classification"]],
                "auto_ship_tiers": g["auto_ship_tiers"],
                "go_live_maintain_tick_apply": go_live,
                "n_registry": g["n_registry"], "n_log_open": g["n_log_open"],
            }, indent=2))
        else:
            print(f"[maintain-tick] tier-0 candidates: {len(g['tier0'])} "
                  f"(registry={g['n_registry']}, log_open={g['n_log_open']}) · "
                  f"policy auto-ship tiers={g['auto_ship_tiers']} · "
                  f"go_live.apply={go_live}")
            for c in g["tier0"]:
                print(f"  ✓ [{c['origin']}] {c['title']}  (ev={c['evidence_sessions']})")
            if g["eval_gated"]:
                print(f"  ◐ {len(g['eval_gated'])} tier-0E (local+reversible but NOT a clear-win → eval-gated, NOT auto-shipped):")
                for c in g["eval_gated"][:8]:
                    print(f"    ▸ [{c['origin']}] {c['title']}")
            if g["needs_classification"]:
                print(f"  ! {len(g['needs_classification'])} prose `[ ]` item(s) need classification:")
                for c in g["needs_classification"][:8]:
                    print(f"    ▸ {c['title']}")
        return 0

    res = run(apply=args.apply, force=args.force, ledger=not args.no_ledger)
    if args.json:
        print(json.dumps(res, indent=2))
    else:
        st = res["status"]
        if st == "drafted":
            print(f"[maintain-tick] drafted ({res['mode']}): {res['proposal_path']}")
            print(f"  picked: {res['picked']['title']}")
            if res.get("needs_classification"):
                print(f"  ({len(res['needs_classification'])} prose item(s) need classification — see --list)")
        elif st == "rate-gated":
            print(f"[maintain-tick] rate-gated: {res['live_claude']} live claude procs — stood aside.")
        else:
            print(f"[maintain-tick] noop: 0 tier-0 candidates "
                  f"(registry={res.get('n_registry')}, log_open={res.get('n_log_open')}).")
            if res.get("needs_classification"):
                print(f"  ({len(res['needs_classification'])} prose item(s) need classification — see --list)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
