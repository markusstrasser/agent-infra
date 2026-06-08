#!/usr/bin/env python3
"""gov.py — governance self-revision orchestrator (report-only).

Telos: governance SHRINKS as model capability rises. Every rule/hook is
scaffolding with a presumption of eventual removal; the engine of removal is
re-running the goal's VERIFIER with the scaffold gone (gov-shrink). Goals +
verifiers (evals/) are the durable artifacts; rules are temporary.

This is the DETECTOR half of a strict report/act split. It only emits a
report; a separate (human-gated, earned-autonomy) actor applies. It performs
NO writes to governance artifacts. Authority is markdown/git; the SQLite used
here is an ephemeral :memory: projection rebuilt from source every run — there
is no governance database (clears the 2026-03-21 finding-triage-DB veto).

Every actionable item carries the routing triple {confidence, evidence,
blast_radius} so the actor can route without re-deriving.

Usage:
  uv run python3 scripts/gov.py report [--days N] [--json] [--no-snapshot]
"""

from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from common.io import load_jsonl
from common.paths import EVENT_LOG

REPO = Path(__file__).resolve().parent.parent
RULES_DIR = REPO / ".claude" / "rules"
HOOKS_GLOBS = [
    (Path.home() / "Projects" / "skills" / "hooks", "*"),
    (REPO / "scripts", "*.py"),
]
REPORT_OUT = REPO / "artifacts" / "gov" / "gov-report.md"
CORPUS_HISTORY = Path.home() / ".claude" / "gov-corpus-history.jsonl"

BLAST_TIERS = ("style", "local", "shared", "constitution")

# Earned-autonomy apply-gate is DORMANT until a track record exists.
AUTO_APPLY_ENABLED = False

# Optional consumers (subagent-built); import defensively so gov.py runs even
# if a piece is mid-build.
try:
    from buildthenundo import find_build_then_undo
except Exception:
    find_build_then_undo = None
try:
    from risky_diff_review_shadow import find_unreviewed_risky
except Exception:
    find_unreviewed_risky = None
try:
    from gov_intake import load_pending as load_pending_corrections
except Exception:
    load_pending_corrections = None
try:
    import gov_invariants
except Exception:
    gov_invariants = None


# ── Gov-ID parsing ──────────────────────────────────────────────────────────
# A scaffold declares its lifecycle metadata via a Gov-ID block embeddable in
# markdown (HTML comment) or scripts (# comment):
#   Gov-ID: rule:invariants
#   goal: prevent irreversible/unauthorized autonomous actions
#   verifier: evals/cases/autonomy-boundaries   (or: null)
#   blast_radius: constitution                  (style|local|shared|constitution)

# NOTE: comment prefix is optional (markdown Gov-ID fields sit bare inside an
# HTML comment), so the field scan below is BOUNDED to the contiguous block
# right after the Gov-ID line (stops at blank line / `-->` / first non-field
# line) to avoid matching ordinary prose. `*` is NOT an allowed prefix — bullet
# list items like `* goal: ...` must not be parsed as metadata.
_FIELD = re.compile(r"^\s*(?:#|<!--|//)?\s*(goal|verifier|blast_radius)\s*:\s*(.+?)\s*(?:-->)?\s*$",
                    re.IGNORECASE)
_GOVID = re.compile(r"Gov-ID\s*:\s*([A-Za-z0-9_:./-]+)")


def parse_gov_id(path: Path) -> dict | None:
    """Read the Gov-ID block from the head of a file. Returns artifact dict or None."""
    try:
        head = path.read_text(encoding="utf-8", errors="replace").splitlines()[:50]
    except OSError:
        return None
    gid = None
    fields: dict[str, str] = {}
    for i, line in enumerate(head):
        m = _GOVID.search(line)
        if m:
            gid = m.group(1)
            # scan ONLY the contiguous block right after the Gov-ID line; stop
            # at the comment close, a blank line, or the first non-field line
            # once we've started collecting (prevents prose false-matches).
            for nxt in head[i + 1:i + 8]:
                stripped = nxt.strip()
                if stripped in ("-->", ""):
                    break
                fm = _FIELD.match(nxt)
                if fm:
                    fields[fm.group(1).lower()] = fm.group(2).strip()
                elif fields:
                    break
            break
    if not gid:
        return None
    kind = gid.split(":", 1)[0] if ":" in gid else "rule"
    verifier = fields.get("verifier", "null")
    if verifier.lower() in ("null", "none", ""):
        verifier = None
    br = fields.get("blast_radius", "local").lower()
    if br not in BLAST_TIERS:
        br = "local"
    return {
        "id": gid,
        "kind": kind,
        "path": str(path.relative_to(REPO)) if REPO in path.parents else str(path),
        "goal": fields.get("goal", ""),
        "verifier": verifier,
        "blast_radius": br,
    }


def collect_artifacts() -> list[dict]:
    """Scan rule files + hook/script files for Gov-ID blocks."""
    out: list[dict] = []
    seen: set[str] = set()
    paths: list[Path] = []
    if RULES_DIR.exists():
        paths += sorted(RULES_DIR.glob("*.md"))
    for base, pat in HOOKS_GLOBS:
        if base.exists():
            paths += sorted(p for p in base.glob(pat) if p.is_file())
    for p in paths:
        art = parse_gov_id(p)
        if art and art["id"] not in seen:
            seen.add(art["id"])
            out.append(art)
    return out


# ── Corpus trend (the success metric: governance shrinks) ─────────────────────
def corpus_snapshot(artifacts: list[dict]) -> dict:
    rule_files = sorted(RULES_DIR.glob("*.md")) if RULES_DIR.exists() else []
    rule_loc = sum(len(p.read_text(errors="replace").splitlines()) for p in rule_files)
    return {
        "rule_files": len(rule_files),
        "rule_loc": rule_loc,
        "annotated_artifacts": len(artifacts),
        "hooks_annotated": sum(1 for a in artifacts if a["kind"] == "hook"),
    }


def corpus_trend(now: dict, write: bool) -> tuple[str, dict | None]:
    """Append snapshot to history; compare to earliest. Returns (trend_str, baseline)."""
    baseline = None
    if CORPUS_HISTORY.exists():
        rows = load_jsonl(CORPUS_HISTORY)
        if rows:
            baseline = rows[0]
    if write:
        CORPUS_HISTORY.parent.mkdir(parents=True, exist_ok=True)
        with CORPUS_HISTORY.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": datetime.now().isoformat(timespec="seconds"), **now}) + "\n")
    if not baseline:
        return ("baseline run — no prior snapshot; trend tracked from here", None)
    d_loc = now["rule_loc"] - baseline.get("rule_loc", now["rule_loc"])
    arrow = "▼ shrinking" if d_loc < 0 else ("▲ growing" if d_loc > 0 else "▬ flat")
    return (f"rule-corpus LOC {arrow} ({d_loc:+d} vs baseline {baseline.get('rule_loc')})", baseline)


# ── Advisory-noise decay (hooks/advisories only) ──────────────────────────────
def advisory_noise(days: int) -> list[dict]:
    """Flag high-fire advisory hooks (action=warn, never block) for disposition.
    Default disposition is delete/quarantine — NEVER auto-escalate to BLOCK."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    rows = load_jsonl(EVENT_LOG, since=cutoff) if EVENT_LOG.exists() else []
    fires: dict[str, int] = defaultdict(int)
    actions: dict[str, set] = defaultdict(set)
    for r in rows:
        h = r.get("hook", "")
        if not h:
            continue
        fires[h] += 1
        actions[h].add(r.get("action", ""))
    if not fires:
        return []
    counts = sorted(fires.values())
    decile = counts[int(len(counts) * 0.9)] if len(counts) >= 10 else max(counts)
    # Absolute floor: never flag "noise" on sparse telemetry — a hook that fired
    # a handful of times in the window is not a habituation problem, even if it
    # tops a small sample. Habituation is a HIGH-volume phenomenon.
    MIN_FIRES = 50
    threshold = max(decile, MIN_FIRES)
    out = []
    for h, n in sorted(fires.items(), key=lambda kv: -kv[1]):
        advisory_only = actions[h].issubset({"warn", "advise", "", "context"})
        if n >= threshold and advisory_only:
            out.append({
                "hook": h, "fires": n,
                "confidence": "medium",  # no per-fire heeded/ignored signal yet
                "evidence": f"{n} fires in {days}d, actions={sorted(a for a in actions[h] if a)} (advisory-only)",
                "blast_radius": "shared",
                "disposition": "review→quarantine/delete (never auto-BLOCK)",
            })
    return out


# ── reasoning-quality signals (the gray-zone trio's standing reader) ──────────
# reasoning-audit / tool-trajectory / thesis-challenge were report-only detectors
# with NO consumer (orphaned-generator sweep 2026-06-08). This collector is their
# standing reader: gov-report runs each and folds in a one-line headline so the
# output is actually read on a cadence. Fail-open subprocess — a broken or slow
# detector surfaces as an error line (which is itself the signal that it rotted),
# never crashes the report.
REASONING_DETECTORS = (
    ("tool-trajectory", ["--json"], "tool_utilization"),
    ("thesis-challenge", [], "thesis_challenge"),
    ("reasoning-audit", ["--top", "10"], "fast_mode_savings"),
)


def reasoning_signals(days: int) -> list[dict]:
    out: list[dict] = []
    for name, extra, kind in REASONING_DETECTORS:
        script = REPO / "scripts" / f"{name}.py"
        if not script.exists():
            out.append({"detector": name, "kind": kind, "error": "script missing"})
            continue
        cmd = ["uv", "run", "python3", str(script), "--days", str(days), *extra]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=REPO)
        except subprocess.TimeoutExpired:
            out.append({"detector": name, "kind": kind, "error": "timeout (120s)"})
            continue
        except Exception as e:  # noqa: BLE001
            out.append({"detector": name, "kind": kind, "error": str(e)[:120]})
            continue
        stdout = (p.stdout or "").strip()
        if p.returncode != 0 or not stdout:
            err = (p.stderr or "").strip().splitlines()
            out.append({"detector": name, "kind": kind,
                        "error": (err[-1][:120] if err else f"exit {p.returncode}, no output")})
            continue
        out.append(_summarize_reasoning(name, kind, stdout))
    return out


def _summarize_reasoning(name: str, kind: str, stdout: str) -> dict:
    """Collapse a detector's stdout into one report headline. Fail-open: any parse
    miss degrades to a raw first-line snippet, never an exception."""
    rec: dict = {"detector": name, "kind": kind}
    try:
        if name == "tool-trajectory":
            data = json.loads(stdout)
            n = data.get("total_sessions", 0)
            tips = data.get("tipping_signals") or data.get("tips") or []
            rec["headline"] = (f"{n} sessions over window · "
                               f"{len(tips)} task-type tipping signal(s) (>20% util drop)")
            rec["detail"] = tips[:5]
        elif name == "thesis-challenge":
            recs = [json.loads(ln) for ln in stdout.splitlines() if ln.strip().startswith("{")]
            theses = sum(r.get("thesis_count", 0) for r in recs)
            challenged = sum(r.get("challenged_count", 0) for r in recs)
            rate = (challenged / theses) if theses else None
            rec["headline"] = (f"{theses} investment theses across {len(recs)} intel session(s) · "
                               f"challenge rate {rate:.0%}" if rate is not None
                               else f"{len(recs)} session(s) scanned · no theses found")
            rec["detail"] = [r["session_id"][:8] for r in recs if r.get("challenge_rate") == 0.0][:5]
        else:  # reasoning-audit
            rec["headline"] = stdout.splitlines()[0][:160]
    except Exception as e:  # noqa: BLE001
        rec["headline"] = f"(unparsed) {stdout.splitlines()[0][:120] if stdout else ''}"
        rec["parse_error"] = str(e)[:80]
    return rec


# ── gov-shrink dry-run ────────────────────────────────────────────────────────
def gov_shrink_dryrun(artifacts: list[dict]) -> dict:
    """A scaffold is shrink-eligible iff it has a verifier (re-run with scaffold
    removed on model bump; if grader still passes, retire). Without a verifier it
    can't be capability-tested — that's the generative backlog."""
    eligible, backlog, style = [], [], []
    for a in artifacts:
        if a["blast_radius"] == "style":
            style.append(a)
        elif a["verifier"]:
            eligible.append(a)
        else:
            backlog.append(a)
    return {"eligible": eligible, "backlog": backlog, "style": style}


# ── Earned-autonomy routing (Phase 3 — DORMANT) ───────────────────────────────
def route(blast_radius: str, confidence: str, reverts_14d: int) -> str:
    """What an actor WOULD do with an actionable item. Auto-apply is dormant
    until AUTO_APPLY_ENABLED and a clean 14-day revert record exist."""
    if blast_radius in ("constitution", "shared"):
        return "human" + (" (quota ≤1/wk)" if blast_radius == "constitution" else "")
    if (blast_radius == "local" and confidence == "high"
            and reverts_14d == 0 and AUTO_APPLY_ENABLED):
        return "auto-apply (after quiet window)"
    return "human"


# ── Projection (ephemeral :memory:, proves we CAN join, no DB on disk) ────────
def build_projection(artifacts: list[dict]) -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE artifact(id TEXT, kind TEXT, path TEXT, goal TEXT, "
                "verifier TEXT, blast_radius TEXT)")
    con.executemany("INSERT INTO artifact VALUES (?,?,?,?,?,?)",
                    [(a["id"], a["kind"], a["path"], a["goal"], a["verifier"] or "",
                      a["blast_radius"]) for a in artifacts])
    con.commit()
    return con


# ── Report assembly ───────────────────────────────────────────────────────────
def build_report(days: int, write_snapshot: bool) -> dict:
    artifacts = collect_artifacts()
    build_projection(artifacts).close()  # prove the join path works; discard

    snap = corpus_snapshot(artifacts)
    trend, _ = corpus_trend(snap, write=write_snapshot)
    invariants = gov_invariants.run_all(artifacts) if gov_invariants else []
    noise = advisory_noise(days)
    shrink = gov_shrink_dryrun(artifacts)
    btu = []
    if find_build_then_undo:
        try:
            btu = [f for f in find_build_then_undo(days) if f.get("confidence") == "high"]
        except Exception as e:  # noqa: BLE001
            btu = [{"error": str(e)}]
    unreviewed_risky = []
    if find_unreviewed_risky:
        try:
            unreviewed_risky = find_unreviewed_risky(days)
        except Exception as e:  # noqa: BLE001
            unreviewed_risky = [{"error": str(e)}]
    corrections = []
    if load_pending_corrections:
        try:
            corrections = load_pending_corrections() or []
        except Exception:
            corrections = []
    return {
        "days": days, "snapshot": snap, "trend": trend, "invariants": invariants,
        "advisory_noise": noise, "shrink": shrink, "build_then_undo": btu,
        "unreviewed_risky": unreviewed_risky,
        "corrections": corrections,
        "reasoning_signals": reasoning_signals(days),
        "coverage_note": gov_invariants.coverage_note() if gov_invariants else "",
    }


def render_md(rep: dict) -> str:
    L: list[str] = []
    L.append(f"# Governance Report — last {rep['days']}d")
    L.append(f"_Generated {datetime.now().isoformat(timespec='minutes')}. Report-only; "
             f"no governance artifact was modified. Markdown/git is authoritative._\n")

    s = rep["snapshot"]
    L.append("## Success metric — does governance shrink?")
    L.append(f"- Rule files: **{s['rule_files']}** · rule LOC: **{s['rule_loc']}** · "
             f"annotated artifacts: **{s['annotated_artifacts']}** "
             f"({s['hooks_annotated']} hooks)")
    L.append(f"- Trend: **{rep['trend']}**")
    L.append("- Telos check: corpus should trend ▼ as model IQ rises while eval pass-rate holds.\n")

    L.append("## Contradiction invariants")
    L.append(f"_{rep['coverage_note']}_\n")
    for inv in rep["invariants"]:
        mark = "✓ pass" if inv["passed"] else "✗ **CONTRADICTION**"
        L.append(f"- {mark} · `{inv['id']}` ({inv['clause']})")
        L.append(f"  - value `{inv['value']}` (threshold `{inv['threshold']}`) · "
                 f"confidence {inv['confidence']} · blast `{inv['blast_radius']}`")
        L.append(f"  - evidence: {inv['evidence']}")
        if not inv["passed"]:
            L.append(f"  - → contradiction proposal · route: **{route(inv['blast_radius'], inv['confidence'], 0)}**")
    L.append("")

    L.append("## gov-shrink dry-run (the core loop)")
    sh = rep["shrink"]
    L.append(f"- **Shrink-eligible** (has verifier → re-run with scaffold removed on next model bump): "
             f"**{len(sh['eligible'])}**")
    for a in sh["eligible"]:
        L.append(f"  - `{a['id']}` verifier=`{a['verifier']}` blast=`{a['blast_radius']}`")
    L.append(f"- **Backlog — needs a verifier before it can be capability-tested**: **{len(sh['backlog'])}**")
    for a in sh["backlog"]:
        L.append(f"  - `{a['id']}` — goal: {a['goal'][:80] or '(undeclared)'}")
    L.append(f"- Style/format artifacts (excluded from shrink): {len(sh['style'])}")
    L.append("- NOTE: ablation-eval execution (run grader with scaffold removed) is wired in "
             "Phase 2 once `evals/` verifiers exist; this run reports eligibility, not verdicts.\n")

    L.append("## Advisory-noise (hooks firing without changing behavior)")
    if rep["advisory_noise"]:
        for n in rep["advisory_noise"]:
            L.append(f"- `{n['hook']}` — {n['evidence']} · route: **{route(n['blast_radius'], n['confidence'], 0)}** · "
                     f"disposition: {n['disposition']}")
    else:
        L.append("- none flagged (or no telemetry in window)")
    L.append("")

    L.append("## Build-then-undo (high-confidence, report-only)")
    btu = rep["build_then_undo"]
    if btu:
        errs = [f for f in btu if "error" in f]
        for f in errs:
            L.append(f"- (analyzer error: {f['error']})")
        graded = [f for f in btu if "error" not in f]
        # move_type splits genuine rebuild waste from legitimate regime
        # transitions (supersession/discovery) — surface churn, de-emphasize the
        # rest (arXiv 2606.01444; decisions/2026-06-07-categorical-discovery-*).
        churn = [f for f in graded if f.get("move_type", "churn") == "churn"]
        transitions = [f for f in graded if f.get("move_type", "churn") != "churn"]
        L.append(f"- **churn (suspect): {len(churn)}** · regime transitions "
                 f"(superseded/discovery, de-emphasized): {len(transitions)}")
        for f in churn[:15]:
            L.append(f"- ⚠ {f.get('files')} · add `{str(f.get('add_commit'))[:8]}` → "
                     f"del `{str(f.get('delete_commit'))[:8]}` · session {str(f.get('session'))[:8]}")
        if len(churn) > 15:
            L.append(f"- … +{len(churn) - 15} more churn")
        if not churn:
            L.append("- no suspect churn — all high-confidence findings are regime transitions")
    else:
        L.append("- none (or analyzer unavailable)")
    L.append("")

    L.append("## Unreviewed risky diffs (SHADOW — high-blast-radius, no test, no review)")
    ur = rep.get("unreviewed_risky", [])
    if ur:
        for f in ur[:15]:
            if "error" in f:
                L.append(f"- (analyzer error: {f['error']})")
            else:
                L.append(f"- `{f.get('sha')}` {f.get('date')} [{','.join(f.get('blast_reasons', []))}]"
                         f" — {f.get('subject')}")
        if len(ur) > 15:
            L.append(f"- … +{len(ur) - 15} more")
        L.append("- _shadow only — promote/cut ~2026-06-21 (`just risky-diff-report`)_")
    else:
        L.append("- none (or analyzer unavailable)")
    L.append("")

    L.append("## Reasoning-quality signals (report-only — gray-trio standing reader)")
    rs = rep.get("reasoning_signals", [])
    if rs:
        for s in rs:
            if s.get("error"):
                L.append(f"- ⚠ `{s['detector']}` — analyzer error: {s['error']}")
            else:
                L.append(f"- `{s['detector']}` ({s['kind']}): {s.get('headline', '(no headline)')}")
                for d in (s.get("detail") or [])[:5]:
                    L.append(f"    - {d}")
        L.append("- _kept by decision 2026-06-04 (reasoning-quality-signal); this section is the "
                 "consumer the sweep flagged was missing. Detectors run report-only on the gov cadence._")
    else:
        L.append("- none (detectors unavailable)")
    L.append("")

    L.append("## Pending corrections (`#f governance:` quarantine)")
    if rep["corrections"]:
        for c in rep["corrections"][:15]:
            L.append(f"- {str(c.get('correction_text', ''))[:120]} "
                     f"(scope={c.get('scope')}, needs confirm={c.get('requires_confirmation')})")
    else:
        L.append("- none pending")
    L.append("")
    return "\n".join(L)


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] != "report":
        print("usage: gov.py report [--days N] [--json] [--no-snapshot]")
        return 2
    days = 60
    if "--days" in args:
        days = int(args[args.index("--days") + 1])
    rep = build_report(days, write_snapshot="--no-snapshot" not in args)
    if "--json" in args:
        print(json.dumps(rep, indent=2, default=str))
        return 0
    md = render_md(rep)
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.write_text(md, encoding="utf-8")
    print(md)
    print(f"\n[gov] wrote {REPORT_OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
