#!/usr/bin/env python3
# Gov-ID: tool:observe-run
# goal: deterministic observe prep — one run dir, all modes, merged candidates, composed digest.
# verifier: scripts/tests/test_observe_run.py
# blast_radius: local
"""Unified /observe deterministic orchestrator.

Runs Tier-0 extraction for one or all modes into a timestamped artifact tree, merges
candidates, runs preflight gates, and composes a master digest with cross-mode triangulation.

LLM lanes (sessions/architecture/supervision synthesis) still run via subagents or
observe_bulk — this script owns everything that should be deterministic, inspectable, and
never invented.

Usage:
    observe_run.py all [--days 7] [--project agent-infra]
    observe_run.py supervision --days 7
    observe_run.py drift --days 21
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILL = Path(
    __import__("os").environ.get(
        "CLAUDE_SKILL_DIR",
        Path.home() / ".cursor/skills/observe",
    )
)
if not SKILL.is_dir():
    SKILL = Path.home() / ".claude/skills/observe"

DEFAULT_PROJECTS = ("agent-infra", "genomics", "substrate", "phenome", "intel", "hutter")
MODE_DAYS = {
    "sessions": 1,
    "architecture": 1,
    "supervision": 7,
    "drift": 21,
    "failures": 21,
    "blindspot": 7,
}


def _run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd or REPO, capture_output=True, text=True, check=check)


def _run_emb(cmd: list[str]) -> subprocess.CompletedProcess:
    return _run(["uv", "run", "--project", str(Path.home() / "Projects/emb"), *cmd])


def active_projects(days: int, limit: int = 8) -> list[str]:
    """Rank projects by recent session file mtime."""
    cutoff = datetime.now().timestamp() - days * 86400
    projects_dir = Path.home() / ".claude/projects"
    counts: Counter[str] = Counter()
    for d in projects_dir.iterdir():
        if not d.is_dir():
            continue
        name = d.name
        # -Users-alien-Projects-agent-infra → agent-infra
        slug = name.split("-Projects-")[-1].split("--")[0].lower() if "-Projects-" in name else name
        if slug.startswith("-") or slug.startswith("private"):
            continue
        for f in d.glob("*.jsonl"):
            if "agent-" in f.name or "compact" in f.name:
                continue
            if f.stat().st_mtime >= cutoff:
                counts[slug] += 1
    ranked = [p for p, _ in counts.most_common(limit)]
    for p in DEFAULT_PROJECTS:
        if p not in ranked:
            ranked.append(p)
    return ranked[:limit]


def run_dir(base: Path, run_id: str | None) -> Path:
    rid = run_id or datetime.now().strftime("%Y-%m-%d-%H%M")
    root = base / rid
    root.mkdir(parents=True, exist_ok=True)
    return root


SIGPIPE = 141


def coverage_digest(out: Path) -> None:
    script = REPO / "scripts/coverage-digest.sh"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as fh:
        proc = subprocess.run(["bash", str(script)], stdout=fh, stderr=subprocess.PIPE, text=True, cwd=REPO)
    if proc.returncode == 0:
        return
    if proc.returncode == SIGPIPE and out.stat().st_size > 0:
        return
    raise subprocess.CalledProcessError(proc.returncode, ["bash", str(script)], stderr=proc.stderr)


def prep_sessions(root: Path, project: str, days: int, sessions: int = 5) -> dict:
    lane = root / "sessions"
    lane.mkdir(exist_ok=True)
    _run([
        sys.executable, str(REPO / "scripts/observe_prepare_context.py"),
        "--project", project,
        "--sessions", str(sessions),
        "--days", str(days),
        "--artifact-dir", str(lane),
        "--full",
    ])
    # shape pre-filter
    shape_out = lane / "shape-filter.txt"
    try:
        proc = _run([
            "uv", "run", "python3", str(SKILL / "scripts/session-shape.py"),
            "--days", str(days), "--project", project,
        ], check=False)
        shape_out.write_text(proc.stdout or proc.stderr or "")
    except Exception as e:
        shape_out.write_text(f"shape-filter error: {e}\n")
    ctx = lane / "observe-context.md"
    if not ctx.is_file():
        ctx = lane / "input.md"
    return {
        "lane": "sessions",
        "artifact_dir": str(lane),
        "context_bytes": ctx.stat().st_size if ctx.is_file() else 0,
        "project": project,
    }


def prep_supervision(root: Path, project: str | None, days: int) -> dict:
    lane = root / "supervision"
    lane.mkdir(exist_ok=True)
    cmd = [
        "uv", "run", "python3", str(REPO / "scripts/supervision-kpi.py"),
        "--days", str(days),
        "--report", str(lane / "supervision-report.json"),
        "--output", str(lane / "supervision-sessions.jsonl"),
    ]
    if project:
        cmd.extend(["--project", project])
    _run(cmd)
    report = json.loads((lane / "supervision-report.json").read_text())
    meta = {"lane": "supervision", "artifact_dir": str(lane), **report, **LANE_SCOPE["supervision"]}
    if project:
        meta["project_filter"] = project
    return meta


def prep_drift(root: Path, days: int, projects: list[str], sessions: int = 40) -> dict:
    lane = root / "drift"
    lane.mkdir(exist_ok=True)
    _run([
        sys.executable, str(REPO / "scripts/observe_drift_context.py"),
        "--artifact-dir", str(lane),
        "--sessions", str(sessions),
        "--projects", *projects,
    ])
    ctx = lane / "observe-context.md"
    return {
        "lane": "drift",
        "artifact_dir": str(lane),
        "context_bytes": ctx.stat().st_size if ctx.is_file() else 0,
        "projects": projects,
        "days": days,
    }


def prep_failures(root: Path, days: int) -> dict:
    lane = root / "failures"
    lane.mkdir(exist_ok=True)
    out_json = lane / "failures.json"
    proc = _run([
        sys.executable, str(SKILL / "scripts/scan_tool_failures.py"),
        "--days", str(days), "--json",
    ], check=False)
    out_json.write_text(proc.stdout or "[]")
    clusters = json.loads(out_json.read_text() or "[]")
    real = [c for c in clusters if c.get("invoker_primary") == "interactive_agent"][:10]
    return {"lane": "failures", "artifact_dir": str(lane), "clusters": len(clusters), "top_real": real}


def prep_blindspot(root: Path, days: int) -> dict:
    lane = root / "blindspot"
    lane.mkdir(exist_ok=True)
    digest_path = REPO / ".claude/blindspot-digest.md"
    fresh = False
    if digest_path.is_file():
        age_h = (datetime.now().timestamp() - digest_path.stat().st_mtime) / 3600
        fresh = age_h < 24
    if not fresh:
        proc = _run_emb([
            "python3", str(REPO / "scripts/blindspot_miner.py"),
            "--days", str(days),
        ], check=False)
        (lane / "miner-output.txt").write_text((proc.stdout or "") + (proc.stderr or ""))
    if digest_path.is_file():
        (lane / "blindspot-digest.md").write_text(digest_path.read_text())
    text = (lane / "blindspot-digest.md").read_text() if (lane / "blindspot-digest.md").is_file() else ""
    m = re.search(r"\*\*(\d+) corrections", text)
    corrections = int(m.group(1)) if m else None
    directions = {}
    for label, key in [
        ("GROW_COVERAGE", "grow_coverage"),
        ("RAISE_AUTONOMY", "raise_autonomy"),
        ("REDUCE_ERROR", "reduce_error"),
        ("AMPLIFY_TASTE", "amplify_taste"),
    ]:
        dm = re.search(rf"\*\*{label}[^*]+\*\* — (\d+)", text)
        if dm:
            directions[key] = int(dm.group(1))
    return {
        "lane": "blindspot",
        "artifact_dir": str(lane),
        "corrections": corrections,
        "directions": directions,
        "fresh_run": not fresh,
        **LANE_SCOPE["blindspot"],
    }


def prep_architecture(root: Path, projects: list[str], sessions: int = 3) -> dict:
    lane = root / "architecture"
    lane.mkdir(exist_ok=True)
    combined: list[str] = []
    for proj in projects[:6]:
        out = lane / f"{proj}.md"
        try:
            _run([
                sys.executable, str(SKILL / "scripts/extract_transcript.py"),
                proj, "--sessions", str(sessions), "--full", "--output", str(out),
            ], check=False)
            if out.stat().st_size > 0:
                combined.append(out.read_text(errors="replace")[:120_000])
        except Exception:
            pass
    all_md = lane / "all.md"
    all_md.write_text("\n\n---\n\n".join(combined))
    return {
        "lane": "architecture",
        "artifact_dir": str(lane),
        "projects": projects[:6],
        "context_bytes": all_md.stat().st_size,
    }


LANE_SCOPE = {
    "supervision": {"scope": "project", "sensitivity": "strict"},
    "blindspot": {"scope": "fleet", "sensitivity": "loose"},
    "failures": {"scope": "fleet", "sensitivity": "strict"},
    "drift": {"scope": "fleet", "sensitivity": "loose"},
    "sessions": {"scope": "project", "sensitivity": "strict"},
    "architecture": {"scope": "fleet", "sensitivity": "loose"},
}


def _known_open_blobs() -> str:
    parts: list[str] = []
    il = REPO / "improvement-log.md"
    if il.is_file():
        parts.append(il.read_text(errors="replace"))
    steward = Path.home() / ".claude/steward-proposals"
    if steward.is_dir():
        for p in sorted(steward.glob("*.md")):
            parts.append(p.read_text(errors="replace"))
    return "\n".join(parts)


def _match_known_open(summary: str, blob: str) -> str | None:
    """Return first matching line id if summary overlaps known-open backlog."""
    tokens = [t.lower() for t in re.findall(r"[A-Za-z][A-Za-z0-9_-]{4,}", summary)][:8]
    if not tokens or not blob:
        return None
    for i, line in enumerate(blob.splitlines()):
        low = line.lower()
        if sum(1 for t in tokens if t in low) >= min(2, len(tokens)):
            return f"known-open:{i + 1}:{line.strip()[:100]}"
    return None


def annotate_candidates_known_open(root: Path) -> int:
    """Join merged candidates against improvement-log + steward-proposals at emit time."""
    out = root / "candidates.jsonl"
    if not out.is_file():
        return 0
    blob = _known_open_blobs()
    annotated = 0
    rows: list[str] = []
    for line in out.read_text().splitlines():
        if not line.strip():
            continue
        cand = json.loads(line)
        if not cand.get("existing_coverage_match"):
            summary = cand.get("summary") or cand.get("pattern_summary") or ""
            hit = _match_known_open(summary, blob)
            if hit:
                cand["existing_coverage_match"] = hit
                cand["dedupe_status"] = cand.get("dedupe_status") or "matched"
                annotated += 1
        rows.append(json.dumps(cand, ensure_ascii=False))
    out.write_text("\n".join(rows) + ("\n" if rows else ""))
    return annotated


def merge_candidates(root: Path) -> int:
    paths = list(root.glob("*/candidates.jsonl")) + list(root.glob("*/*/candidates.jsonl"))
    lines: list[str] = []
    for p in paths:
        if p.name == "candidates.jsonl" and p.parent == root:
            continue
        for line in p.read_text().splitlines():
            if line.strip():
                lines.append(line)
    out = root / "candidates.jsonl"
    out.write_text("\n".join(lines) + ("\n" if lines else ""))
    annotate_candidates_known_open(root)
    return len(lines)


def run_preflight(root: Path) -> dict:
    proc = _run([
        "uv", "run", "python3", str(SKILL / "scripts/observe_gates.py"),
        "--artifact-root", str(root), "preflight", "--quiet",
    ], check=False)
    pf = root / "preflight.json"
    return json.loads(pf.read_text()) if pf.is_file() else {"error": proc.stderr}


def triangulate(
    supervision: dict | None,
    blindspot: dict | None,
    failures: dict | None,
    project_filter: str | None = None,
) -> list[dict]:
    """Cross-mode signals — only triangulate within compatible scope.

    A zero reading from a strict project-scoped lane is NOT corroboration for a
    fleet-wide loose lane. Silent strict detectors downweight, never inflate.
    """
    hits: list[dict] = []
    proj = project_filter or supervision.get("project_filter") if supervision else None

    if supervision and blindspot:
        oc = supervision.get("by_type", {}).get("over_caution", 0)
        ra = blindspot.get("directions", {}).get("raise_autonomy", 0)
        if oc and ra:
            hits.append({
                "theme": "over_caution / timidity",
                "modes": ["supervision", "blindspot"],
                "scope": f"project={proj} + fleet",
                "evidence": f"supervision over_caution={oc} (strict/{proj}), blindspot raise_autonomy={ra} (fleet)",
                "rsi_response": "RAISE_AUTONOMY — loosen act-without-ask on reversible work (scope: both fired)",
                "confidence": "high",
            })
        elif ra and not oc:
            hits.append({
                "theme": "over_caution / timidity (fleet-only)",
                "modes": ["blindspot"],
                "scope": "fleet",
                "evidence": f"supervision over_caution=0 (strict/{proj or 'all'}), blindspot raise_autonomy={ra} (fleet)",
                "rsi_response": "RAISE_AUTONOMY — fleet signal; do NOT loosen act-without-ask on "
                f"{proj or 'filtered project'} without local evidence",
                "confidence": "low",
            })
        elif oc and not ra:
            hits.append({
                "theme": "over_caution / timidity (project-only)",
                "modes": ["supervision"],
                "scope": f"project={proj}",
                "evidence": f"supervision over_caution={oc} (strict/{proj}), blindspot raise_autonomy=0",
                "rsi_response": "RAISE_AUTONOMY — project-scoped timidity",
                "confidence": "medium",
            })

    if supervision and blindspot:
        rd = supervision.get("by_type", {}).get("rediscovery", 0)
        gc = blindspot.get("directions", {}).get("grow_coverage", 0)
        if rd and gc:
            hits.append({
                "theme": "prior-context / rediscovery",
                "modes": ["supervision", "blindspot"],
                "scope": f"project={proj} + fleet",
                "evidence": f"supervision rediscovery={rd} (strict/{proj}), blindspot grow_coverage={gc} (fleet)",
                "rsi_response": "GROW_COVERAGE — extend prior-context / git-log detectors",
                "confidence": "high",
            })
        elif gc and not rd:
            hits.append({
                "theme": "prior-context / rediscovery (fleet-only)",
                "modes": ["blindspot"],
                "scope": "fleet",
                "evidence": f"supervision rediscovery={rd} (strict/{proj or 'all'}), blindspot grow_coverage={gc} (fleet)",
                "rsi_response": "GROW_COVERAGE — fleet rediscovery; extend detectors where "
                f"{proj or 'filtered project'} has local hits only",
                "confidence": "low" if rd == 0 else "medium",
            })
        elif rd and not gc:
            hits.append({
                "theme": "prior-context / rediscovery (project-only)",
                "modes": ["supervision"],
                "scope": f"project={proj}",
                "evidence": f"supervision rediscovery={rd} (strict/{proj}), blindspot grow_coverage=0",
                "rsi_response": "GROW_COVERAGE — project-scoped prior-context miss",
                "confidence": "medium",
            })

    # failures lane: report top REAL breaks without prescribing uv-guard (Opus: wrong mechanism)
    if failures:
        for c in failures.get("top_real", [])[:3]:
            if c.get("fails", 0) >= 3:
                hits.append({
                    "theme": f"tool failure: {c.get('cluster', '?')}",
                    "modes": ["failures"],
                    "scope": "fleet",
                    "evidence": f"{c['cluster']} fails={c.get('fails')} days={c.get('distinct_days')}",
                    "rsi_response": "REDUCE_ERROR — inspect actual invoker command before prescribing fix",
                    "confidence": "medium" if c.get("distinct_days", 0) >= 2 else "low",
                })

    return hits


def compose_digest(
    root: Path,
    modes: list[str],
    lane_meta: dict[str, dict],
    preflight: dict,
    triangulated: list[dict],
    project: str | None,
) -> None:
    h = preflight.get("health", {})
    s = preflight.get("saturation", {})
    promos = preflight.get("promotion_counts", {})
    n_cand = merge_candidates(root)

    lines = [
        f"# Observe — {datetime.now().strftime('%Y-%m-%d')} ({', '.join(modes)})",
        "",
        "## Data validity",
        f"- **Indexer:** {h.get('indexer_ok', '?')} (status={h.get('last_index_status', '?')})",
        f"- **Promotions allowed:** {preflight.get('promotions_allowed', '?')}",
        f"- **Saturation:** {s.get('saturated', '?')} (token_overlap={s.get('token_overlap', '?')})",
        f"- **Candidates merged:** {n_cand}",
        "",
        "> Deterministic Tier-0 below. LLM lanes (sessions/architecture synthesis) add Tier-1 — verify before promote.",
        "",
        "## Metric legend",
        "| Lane | Source | Headline |",
        "|------|--------|----------|",
    ]

    if "supervision" in lane_meta:
        sup = lane_meta["supervision"]
        v = sup.get("vector", {})
        pf = sup.get("project_filter") or project or "all"
        lines.append(
            f"| supervision | supervision-report.json | "
            f"scope=project/{pf} strict · correction_rate={sup.get('correction_rate_pct')}% "
            f"vector autonomy={v.get('raise_autonomy',0)} error={v.get('reduce_error',0)} "
            f"coverage={v.get('grow_coverage',0)} reading={sup.get('autonomy_reading')} |"
        )
    if "blindspot" in lane_meta:
        bs = lane_meta["blindspot"]
        lines.append(
            f"| blindspot | blindspot-digest.md | "
            f"scope=fleet loose · {bs.get('corrections', '?')} corrections/7d emb-contrastive |"
        )
    if "failures" in lane_meta:
        fl = lane_meta["failures"]
        lines.append(f"| failures | failures.json | {fl.get('clusters', 0)} clusters |")
    if "drift" in lane_meta:
        dr = lane_meta["drift"]
        lines.append(f"| drift | observe-context.md | {dr.get('context_bytes', 0)//1024}KB wide window |")

    lines.extend([
        "",
        "## Triangulated signals (scope-aware — silent strict lane ≠ corroboration)",
        "",
    ])
    if triangulated:
        for t in triangulated:
            lines.append(f"### {t['theme']} [{t['confidence']}]")
            lines.append(f"- **Modes:** {', '.join(t['modes'])} · **Scope:** {t.get('scope', '?')}")
            lines.append(f"- **Evidence:** {t['evidence']}")
            lines.append(f"- **RSI response:** {t['rsi_response']}")
            lines.append("")
    else:
        lines.append("_No cross-mode triangulation this run._")
        lines.append("")

    if "supervision" in lane_meta:
        sup = lane_meta["supervision"]
        lines.extend([
            "## Supervision vector (headline objective)",
            f"- Sessions: {sup.get('sessions_analyzed')} · User turns: {sup.get('user_turns')}",
            f"- **Correction rate:** {sup.get('correction_rate_pct')}% (NOT legacy wasted%)",
            f"- **Autonomy reading:** {sup.get('autonomy_reading')}",
            f"- Vector: `{json.dumps(sup.get('vector', {}))}`",
            "",
        ])
        examples = sup.get("examples", [])[:5]
        if examples:
            lines.append("Top correction examples (inspectable):")
            for ex in examples:
                lines.append(f"- `{ex.get('project')}/{ex.get('session_id')}` "
                             f"[{ex.get('type_id')}] {ex.get('evidence', '')[:80]}")
            lines.append("")

    lines.extend([
        "## LLM lanes (run subagents or --headless on artifacts above)",
        "- **sessions** → read `sessions/observe-context.md` + shape-filter.txt",
        "- **architecture** → read `architecture/all.md`",
        "- **drift** → read `drift/observe-context.md`",
        "",
        "## Promotion queue",
        f"Verdicts: `{json.dumps(promos)}` — see `promotion-verdicts.jsonl`",
        "",
        f"Artifact root: `{root}`",
    ])

    (root / "digest.md").write_text("\n".join(lines) + "\n")


def write_manifest(root: Path, modes: list[str], lane_meta: dict, project: str | None) -> None:
    manifest = {
        "schema": "observe.manifest.v2",
        "run_id": root.name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "modes": modes,
        "project_filter": project or "all",
        "artifact_dir": str(root),
        "lanes": lane_meta,
        "orchestrator": "scripts/observe_run.py",
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser(description="Unified observe deterministic orchestrator")
    ap.add_argument(
        "mode",
        choices=["all", "sessions", "architecture", "supervision", "drift", "failures", "blindspot"],
    )
    ap.add_argument("--days", type=int, help="Override default window for mode")
    ap.add_argument("--project", "-p", help="Filter to one project (sessions/supervision)")
    ap.add_argument("--run-id", help="Artifact subdirectory name")
    ap.add_argument("--artifact-root", type=Path, default=REPO / "artifacts/observe")
    ap.add_argument("--sessions", type=int, default=5, help="Transcript session cap per project")
    args = ap.parse_args()

    modes = (
        ["sessions", "architecture", "supervision", "drift", "failures", "blindspot"]
        if args.mode == "all"
        else [args.mode]
    )
    root = run_dir(args.artifact_root, args.run_id)
    cov = root / "coverage-digest.txt"
    coverage_digest(cov)

    project = args.project or "agent-infra"
    projects = active_projects(args.days or 7)
    lane_meta: dict[str, dict] = {}

    for mode in modes:
        days = args.days or MODE_DAYS.get(mode, 7)
        try:
            if mode == "sessions":
                lane_meta[mode] = prep_sessions(root, project, days, args.sessions)
            elif mode == "supervision":
                lane_meta[mode] = prep_supervision(root, args.project, days)
            elif mode == "drift":
                lane_meta[mode] = prep_drift(root, days, projects, max(args.sessions * 8, 40))
            elif mode == "failures":
                lane_meta[mode] = prep_failures(root, days)
            elif mode == "blindspot":
                lane_meta[mode] = prep_blindspot(root, days)
            elif mode == "architecture":
                lane_meta[mode] = prep_architecture(root, projects, args.sessions)
        except subprocess.CalledProcessError as e:
            lane_meta[mode] = {"lane": mode, "error": (e.stderr or str(e))[:500]}
            print(f"WARN: {mode} prep failed: {e}", file=sys.stderr)

    preflight = run_preflight(root)
    triangulated = triangulate(
        lane_meta.get("supervision"),
        lane_meta.get("blindspot"),
        lane_meta.get("failures"),
        args.project,
    )
    compose_digest(root, modes, lane_meta, preflight, triangulated, args.project)
    write_manifest(root, modes, lane_meta, args.project)

    print(json.dumps({
        "run_id": root.name,
        "artifact_dir": str(root),
        "modes": modes,
        "triangulated": len(triangulated),
        "promotions_allowed": preflight.get("promotions_allowed"),
        "digest": str(root / "digest.md"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
