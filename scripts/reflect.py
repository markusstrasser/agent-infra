#!/usr/bin/env python3
"""reflect.py — the deep pass of the recursive learning loop.

Reads captured signals (reflect_capture.py → ~/.claude/reflect-capture.jsonl),
clusters them, classifies each cluster against the FM taxonomy (fm.py),
ENFORCES merge-before-mint, routes to the cheapest enforcer, and emits proposals.

Auto-record-never-auto-apply (user decision, plan 4d40085a):
  • cluster maps to an EXISTING active FM  → AUTO-RECORD evidence (fm.py attach,
    audited) — low-blast bookkeeping, no human gate.
  • new FM (mint) or an ENFORCER proposal  → QUARANTINE for human disposition.
    No enforcer ever activates without approval.

The classifier SPINE is deterministic (probe→FM anchors + signature string-sim),
so the loop runs at $0 with no transport dependency and is fully testable. The
optional --llm flag enriches enforcer/verifier proposals via the $0 Claude
subscription route (`claude -p`, key stripped); it fails open to the
deterministic proposal. This deliberately bypasses the api_only shared dispatcher
(no $0 profile exists there yet) — see plan 4d40085a transport note.

Commands:
  reflect.py classify [--llm] [--min-cluster N] [--dry-run]
  reflect.py review            — ranked quarantine for human disposition
  reflect.py status            — capture / cluster / quarantine stats
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fm  # noqa: E402  (taxonomy primitives)

CAPTURE_LOG = Path.home() / ".claude" / "reflect-capture.jsonl"
PROCESSED = Path.home() / ".claude" / "reflect-processed.json"
QUARANTINE_DIR = Path.home() / ".claude" / "reflect-quarantine"

MIN_CLUSTER = 3          # signals before a cluster is classified
MIN_SESSIONS = 2         # distinct sessions a cluster must span
SIM_THRESH = 0.55        # difflib ratio to join a correction cluster
MATCH_THRESH = 0.30      # signature-sim to attach to an existing FM vs mint
WIP_CAP = 10             # max active quarantine items
ARRIVAL_CAP = 3          # max new quarantine items per classify run
# Omission probes are SHADOW (high FP by design) — they have NO durable effect
# (no evidence-attach, no quarantine) until their subtype clears a PPV gate. Empty
# until shadow data is labelled; until then omission clusters are held, capture-only.
PPV_CLEARED: set[str] = set()

# Deterministic anchors: a probe's nearest existing FM (a prior, confirmed by
# signature-sim). Corrections without an anchor fall back to pure signature-sim.
PROBE_FM = {
    "entity-write-without-identity-read": "fm25-belief6-fae",
    "state-claim-without-ground-truth-query": "fm15-silent-semantic-failure",
    "gate-bounce-without-preflight": "fm24-retry-without-diagnosis",
    "new-script-without-test": "fm15-silent-semantic-failure",
    "retry_run": "fm24-retry-without-diagnosis",
}
# Router: signal kind/subtype → failure-class axis → enforcer family.
AXIS = {
    "omission": "reach", "retry_run": "reach",
    "f_tag": "knowledge", "negation": "knowledge", "fail_then_user": "capability",
}
ENFORCER_BY_AXIS = {
    "reach": "decision-point gate / make-the-tool-the-default-path",
    "capability": "build/extend a tool (rare — confirm the capability is truly missing)",
    "knowledge": "inject a per-task preflight checklist at task start",
    "taste": "surface as a question for the operator",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ── IO ───────────────────────────────────────────────────────────────────────
def load_capture() -> list[dict]:
    if not CAPTURE_LOG.exists():
        return []
    out = []
    for line in CAPTURE_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            out.append(json.loads(line))
        except (json.JSONDecodeError, ValueError):
            continue
    return out


def load_processed() -> dict:
    if PROCESSED.exists():
        try:
            return json.loads(PROCESSED.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            pass
    return {"hashes": [], "fm_enforced": []}


def save_processed(state: dict) -> None:
    PROCESSED.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED.write_text(json.dumps(state, indent=0), encoding="utf-8")


# ── clustering (deterministic) ───────────────────────────────────────────────
def cluster_signals(signals: list[dict]) -> list[list[dict]]:
    """Greedy clustering. Omission/retry signals bucket by (project, kind, subtype)
    — project-scoped so two repos' same-named probes don't collide, and free
    corrections can't contaminate a retry/omission bucket. Free-text corrections
    join an existing FREE cluster of the same project+kind whose representative
    trigger is similar (difflib ratio >= SIM_THRESH), else seed a new cluster."""
    keyed: dict[tuple, list[dict]] = defaultdict(list)
    free: list[dict] = []
    for s in signals:
        st = s.get("subtype", "")
        if s.get("kind") == "omission" or st == "retry_run":
            keyed[(s.get("project", "?"), s.get("kind"), st)].append(s)
        else:
            free.append(s)

    free_clusters: list[list[dict]] = []
    for s in free:
        trig = s.get("trigger", "")
        placed = False
        for c in free_clusters:
            if c[0].get("kind") != s.get("kind") or c[0].get("project") != s.get("project"):
                continue
            if difflib.SequenceMatcher(None, c[0].get("trigger", ""), trig).ratio() >= SIM_THRESH:
                c.append(s)
                placed = True
                break
        if not placed:
            free_clusters.append([s])
    return list(keyed.values()) + free_clusters


def _distinct_sessions(cluster: list[dict]) -> int:
    return len({s.get("session") for s in cluster if s.get("session")})


# ── classification (deterministic spine) ─────────────────────────────────────
def _sig_text(cluster: list[dict]) -> str:
    return " ".join(s.get("trigger", "") for s in cluster)[:600]


def classify_cluster(cluster: list[dict], fm_blocks: list[dict]) -> dict:
    """Map a cluster to an existing FM (attach) or propose a mint. Anchor by
    probe→FM prior, confirm by signature string-sim. Returns the routing dict."""
    subtype = cluster[0].get("subtype", "")
    text = _sig_text(cluster).lower()
    active = [b for b in fm_blocks if b["status"] == "active"]

    def sim(b):
        return difflib.SequenceMatcher(None, b["signature"].lower(), text).ratio()

    ranked = sorted(active, key=sim, reverse=True)
    best = ranked[0] if ranked else None
    best_sim = sim(best) if best else 0.0

    anchor_id = PROBE_FM.get(subtype)
    anchor = next((b for b in active if b["id"] == anchor_id), None)

    # Prefer the anchor if it exists; else the best signature match.
    target = anchor or best
    target_sim = (sim(anchor) if anchor else best_sim)

    axis = AXIS.get(subtype) or AXIS.get(cluster[0].get("kind", ""), "knowledge")

    trace = {"best_fm": best["id"] if best else None, "best_sim": round(best_sim, 2),
             "anchor_used": anchor["id"] if anchor else None, "threshold": MATCH_THRESH}
    if target and (anchor is not None or target_sim >= MATCH_THRESH):
        return {"action": "attach", "fm_id": target["id"], "confidence": round(target_sim, 2),
                "axis": axis, "merges": [], "trace": trace}
    # below threshold and no anchor → mint candidate. Merge-before-mint: a mint MUST
    # name the >=2 nearest existing FMs it collapses; if the taxonomy can't supply
    # two, it is NOT a mint — flag for taxonomy review rather than emit an invalid one.
    merges = [b["id"] for b in ranked[:2]]
    action = "mint" if len(merges) >= 2 else "needs-review"
    return {"action": action, "fm_id": None, "confidence": round(best_sim, 2),
            "axis": axis, "merges": merges, "trace": trace}


def propose_enforcer(cluster: list[dict], cls: dict) -> dict:
    axis = cls["axis"]
    subtype = cluster[0].get("subtype", "unknown")
    return {
        "enforcer_family": ENFORCER_BY_AXIS.get(axis, ENFORCER_BY_AXIS["knowledge"]),
        "axis": axis,
        "mode": "report-only",  # canary: never ships active without human flip
        "verifier_sketch": (
            f"A check that FAILS when '{subtype}' recurs: assert the required "
            f"capability/step appears in the session before the triggering action. "
            f"Falsifiable, report-only first."
        ),
    }


# ── optional $0 LLM enrichment (claude -p subscription; fail-open) ───────────
def llm_enrich(proposal: dict) -> dict:
    """Refine an enforcer proposal via the $0 Claude subscription route. Bypasses
    the api_only shared dispatcher deliberately (no $0 profile exists). Fail-open."""
    prompt = (
        "You are refining a self-improvement proposal for an agent system. Given this "
        "failure-mode cluster and its draft enforcer, return ONE tightened sentence for "
        "`verifier_sketch` (a falsifiable, report-only check) and nothing else.\n\n"
        f"Cluster: {json.dumps(proposal.get('cluster_summary',''))[:800]}\n"
        f"Axis: {proposal.get('axis')}\nDraft: {proposal.get('verifier_sketch')}\n"
    )
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("CLAUDE_API_KEY", None)
    try:
        r = subprocess.run(
            ["claude", "-p", "--permission-mode", "dontAsk", "--tools", "",
             "--output-format", "text", prompt],
            capture_output=True, text=True, timeout=90, env=env,
        )
        out = (r.stdout or "").strip()
        if r.returncode == 0 and out and "Credit balance is too low" not in out:
            proposal["verifier_sketch"] = out[:500]
            proposal["llm_enriched"] = True
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass  # fail-open: keep the deterministic sketch
    return proposal


# ── emit (auto-record vs quarantine) ─────────────────────────────────────────
def _quarantine_path() -> Path:
    return QUARANTINE_DIR / f"{_utc_now()[:10]}.jsonl"


def _active_quarantine_count() -> int:
    if not QUARANTINE_DIR.exists():
        return 0
    n = 0
    for f in QUARANTINE_DIR.glob("*.jsonl"):
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                if json.loads(line).get("status") == "pending":
                    n += 1
            except (json.JSONDecodeError, ValueError):
                continue
    return n


def run_classify(use_llm: bool = False, min_cluster: int = MIN_CLUSTER,
                 dry_run: bool = False) -> dict:
    signals = load_capture()
    state = load_processed()
    seen = set(state.get("hashes", []))
    fm_enforced = set(state.get("fm_enforced", []))
    fresh = [s for s in signals if s.get("hash") not in seen]
    clusters = cluster_signals(fresh)
    fm_blocks = fm.parse_blocks()

    auto_recorded, quarantined, deferred = [], [], []
    arrival = suppressed = 0
    active_q = _active_quarantine_count()
    newly_processed: set[str] = set()

    def cap_open() -> bool:
        return arrival < ARRIVAL_CAP and (active_q + arrival) < WIP_CAP

    for cluster in clusters:
        kind = cluster[0].get("kind")
        subtype = cluster[0].get("subtype", "")
        # SHADOW: an omission probe has NO durable effect until its PPV gate clears.
        # Hold the cluster (don't classify, don't process) — it keeps accumulating
        # in the capture log for PPV measurement. Corrections (incl. retry_run) flow.
        if kind == "omission" and subtype not in PPV_CLEARED:
            deferred.append({"reason": "shadow-omission-held", "subtype": subtype,
                             "size": len(cluster)})
            continue
        if len(cluster) < min_cluster or _distinct_sessions(cluster) < MIN_SESSIONS:
            deferred.append({"reason": "below-threshold", "size": len(cluster),
                             "sessions": _distinct_sessions(cluster), "subtype": subtype})
            continue  # leave UNprocessed so future signals can join
        cls = classify_cluster(cluster, fm_blocks)
        summary = f"{subtype} x{len(cluster)} ({_distinct_sessions(cluster)} sessions)"
        handled = True

        if cls["action"] == "attach":
            # AUTO-RECORD evidence (idempotent attach → re-runs after a cap are safe)
            if not dry_run:
                for s in cluster:
                    if fm.cmd_attach(_AttachArgs(cls["fm_id"], s.get("session", "?"),
                                                 s.get("trigger", "")[:160])) != 0:
                        handled = False  # attach failed → retry next run, don't process
            auto_recorded.append({"fm_id": cls["fm_id"], "summary": summary,
                                  "confidence": cls["confidence"]})
            # Propose the ENFORCER once per FM (behavior change → quarantine)
            if cls["fm_id"] not in fm_enforced:
                if cap_open():
                    prop = _build_proposal(cluster, cls, summary, use_llm)
                    if not dry_run:
                        _write_quarantine(prop)
                        fm_enforced.add(cls["fm_id"])
                    quarantined.append(prop)
                    arrival += 1
                else:
                    suppressed += 1
                    handled = False  # enforcer not yet emitted → retry (idempotent attach)
        else:  # mint OR needs-review — taxonomy/review change, always human-gated
            if cap_open():
                prop = _build_proposal(cluster, cls, summary, use_llm)
                if not dry_run:
                    _write_quarantine(prop)
                quarantined.append(prop)
                arrival += 1
            else:
                suppressed += 1
                handled = False  # not emitted → retry next run (no silent drop)

        if handled:
            newly_processed.update(h for h in (s.get("hash") for s in cluster) if h)

    if not dry_run:
        seen.update(newly_processed)
        state["hashes"] = sorted(h for h in seen if h)
        state["fm_enforced"] = sorted(fm_enforced)
        save_processed(state)

    return {"fresh_signals": len(fresh), "clusters": len(clusters),
            "auto_recorded": auto_recorded, "quarantined": quarantined,
            "deferred": len(deferred), "suppressed": suppressed,
            "capped": (arrival >= ARRIVAL_CAP) or suppressed > 0}


def _build_proposal(cluster, cls, summary, use_llm) -> dict:
    enf = propose_enforcer(cluster, cls)
    prop = {
        "schema": "reflect.proposal.v1", "ts": _utc_now(), "status": "pending",
        "action": cls["action"], "fm_id": cls["fm_id"], "merges": cls["merges"],
        "axis": cls["axis"], "confidence": cls["confidence"],
        "trace": cls.get("trace", {}),  # auditable: best FM, sim, anchor, threshold
        "project_set": sorted({s.get("project", "?") for s in cluster}),
        "cluster_summary": summary, "evidence": [s.get("trigger", "")[:160] for s in cluster[:5]],
        **enf,
    }
    if cls["action"] == "mint":
        prop["mint_note"] = (
            f"merge-before-mint: would merge {cls['merges']}. Refuse unless these "
            f">=2 prior classes genuinely collapse into one. Human decides."
        )
    elif cls["action"] == "needs-review":
        prop["mint_note"] = ("taxonomy too small to satisfy merge-before-mint (<2 nearest "
                             "FMs). Human: attach to an existing FM or seed a new one manually.")
    return llm_enrich(prop) if use_llm else prop


def _write_quarantine(prop: dict) -> None:
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    with _quarantine_path().open("a", encoding="utf-8") as f:
        f.write(json.dumps(prop, default=str) + "\n")


class _AttachArgs:
    def __init__(self, id_, session, quote):
        self.id, self.session, self.quote = id_, session, quote


# ── commands ─────────────────────────────────────────────────────────────────
def cmd_classify(args) -> int:
    r = run_classify(use_llm=args.llm, min_cluster=args.min_cluster, dry_run=args.dry_run)
    tag = " [DRY-RUN]" if args.dry_run else ""
    print(f"\n[reflect classify]{tag} {r['fresh_signals']} fresh signals → "
          f"{r['clusters']} clusters ({r['deferred']} below threshold)")
    for a in r["auto_recorded"]:
        print(f"  ✓ auto-recorded → {a['fm_id']} ({a['summary']}, sim={a['confidence']})")
    _kind = {"mint": "MINT", "needs-review": "NEEDS-REVIEW"}
    for q in r["quarantined"]:
        kind = _kind.get(q["action"], f"enforcer→{q['fm_id']}")
        print(f"  ▸ quarantined [{kind}] axis={q['axis']} :: {q['cluster_summary']}")
    if r.get("suppressed"):
        print(f"  ! {r['suppressed']} eligible cluster(s) cap-suppressed — NOT processed, "
              f"retry next run (no silent drop)")
    print(f"\nReview: reflect.py review   (auto-record is applied; enforcers/mints await you)")
    return 0


def _load_pending() -> list[tuple[Path, int, dict]]:
    out = []
    if not QUARANTINE_DIR.exists():
        return out
    for f in sorted(QUARANTINE_DIR.glob("*.jsonl")):
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        for i, line in enumerate(lines):
            try:
                r = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if r.get("status") == "pending":
                out.append((f, i, r))
    return out


def cmd_review(_args) -> int:
    pending = _load_pending()
    if not pending:
        print("\n[reflect review] quarantine empty — nothing awaiting disposition.")
        return 0
    print(f"\n[reflect review] {len(pending)} pending (cap {WIP_CAP}). "
          f"Approve → improvement-log [ ] proposed; report-only canary until you flip active.\n")
    _head = {"mint": "MINT", "needs-review": "NEEDS-REVIEW"}
    for _, _, r in sorted(pending, key=lambda x: x[2].get("confidence", 0), reverse=True):
        head = _head.get(r["action"], f"enforcer → {r['fm_id']}")
        print(f"  ▸ [{head}] axis={r['axis']} conf={r.get('confidence')} proj={r.get('project_set')}")
        print(f"      {r['cluster_summary']}")
        print(f"      verifier: {r['verifier_sketch'][:140]}")
        if r.get("mint_note"):
            print(f"      {r['mint_note']}")
        print()
    print("Disposition is manual (auto-record-never-auto-apply): edit status to "
          "approved/rejected in the quarantine jsonl, then promote approved items.")
    return 0


def cmd_status(_args) -> int:
    sig = load_capture()
    by_kind: dict[str, int] = defaultdict(int)
    for s in sig:
        by_kind[s.get("kind", "?")] += 1
    proc = len(load_processed().get("hashes", []))
    pending = len(_load_pending())
    print(f"\n[reflect status]")
    print(f"  captured signals : {len(sig)} ({dict(by_kind)})")
    print(f"  processed        : {proc}")
    print(f"  quarantine pending: {pending} / {WIP_CAP}")
    print(f"  FM blocks        : {len(fm.parse_blocks())}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="reflect.py — deep pass of the learning loop")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("classify")
    c.add_argument("--llm", action="store_true", help="enrich proposals via $0 claude -p")
    c.add_argument("--min-cluster", type=int, default=MIN_CLUSTER)
    c.add_argument("--dry-run", action="store_true")
    c.set_defaults(fn=cmd_classify)
    sub.add_parser("review").set_defaults(fn=cmd_review)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
