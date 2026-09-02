#!/usr/bin/env python3
"""orphan_check.py — the orphaned-generator ratchet (report-only).

The standing consumer for the orphaned-generator disease: a generator that
produces analysis/report output NOTHING reads, on no cadence, with no consumer.
The 2026-06-08 sweep that found ~17 of these was MANUAL; this makes detection
automatic so the answer to "why did a human have to notice" becomes "they don't."

Computes four consumption signals per top-level `scripts/*.py|*.sh`, mechanically:

  1. wired      — an evidence-bound Just/launchd/shell relation, or a reference
                  in external hook settings not stored in this repository.
  2. imported   — a resolved import/call relation from another live source file,
                  including supported dynamic-import idioms.
  3. referenced — named in a REAL consumer: a skill, a non-inventory rule, a
                  decision, an active plan, an agent doc, or a memory file.
                  EXCLUDES auto-generated inventories (codebase-map.md,
                  overviews/, *_inventory.md, *-overview.md) — those describe that
                  the script exists, they do not consume it. That conflation is
                  the trap the manual sweep had to drill past.
  4. invocations — distinct-ish Bash tool_calls in agentlogs (last 90d). WEAK
                  signal both ways (low counts are often the author editing/
                  fact-checking the file, not running it; hook-fired scripts show
                  0). Used only as the tie-breaker the sweep specified (<3 / 90d).

A generator is FLAGGED (candidate orphan) when:
    wired=no AND imported=no AND referenced=no AND invocations<3-in-90d
and it is NOT on the occasional-manual allowlist.

Report-only — NEVER auto-deletes. The sweep's own false-negative rate was high
(4 scripts flipped dead→keep only after drill-down), so a human re-verifies each
flag before acting.

Usage:
    uv run python3 scripts/orphan_check.py            # human report
    uv run python3 scripts/orphan_check.py --json      # machine-readable
    uv run python3 scripts/orphan_check.py --days 90   # invocation window
"""

from __future__ import annotations

import json
import sqlite3
import sys

from common.db import open_db_ro
from code_relations import CodeRelationGraph, build_code_relations
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
AGENTLOGS_DB = Path.home() / ".claude" / "agentlogs.db"

# Files that DESCRIBE the script surface (auto-generated inventories), not
# consumers of it. Referencing one of these is NOT consumption.
INVENTORY_MARKERS = ("codebase-map.md", "_inventory.md", "-overview.md")
INVENTORY_DIRS = ("overviews",)

# Occasional-manual CLI tools and completed one-shots — appear "unwired" but are
# ad-hoc utilities a human/agent runs on demand, NOT generators-without-consumers.
# Sourced from research/2026-06-08-orphaned-generator-sweep.md NOT-THE-DISEASE list.
# Keep this list tight; an entry here suppresses a flag, so it is the one place a
# false negative can hide — review additions.
OCCASIONAL_MANUAL = {
    # manual convenience
    "git-push-all.sh", "daily-recon.sh",
    "ts-replace.py", "usage-check.py",
    # completed one-shot migrations (harmless, delete-eligible)
    "compress-research-index.py",
    # repo-introspection on demand
    "repo-outline.py", "repo-summary.py", "repo-changes.py",
    "verify-subagent-claims.py", "researcher-postmortem.py",
    "dispatch-with-stub.py", "parallel_mcp.py", "parallel_search.py",
    # one-time characterization probes (kept as occasional-manual per their vetoes)
    "tool_hallucination_probe.py", "prompt-archaeology.py",
    # data-exhaust producer — on-demand (--today/--days N, no schedule). Its output
    # artifacts/epistemic-metrics.jsonl has 8 live consumers (dashboard, claims-reader,
    # trace-faithfulness, safe-lite-eval, observe/session-shape, 2 advisory hooks). The
    # 0-invocations/90d proxy flags it as orphan, but deleting it strands the consumers:
    # this is the producer-of-consumed-static-output false-positive class, not dead infra.
    "session-features.py",
}

# Pure library / helper modules and the inventory generators themselves — not
# "generators with a report" at all; exclude from the surface.
SKIP_FILES = {
    "__init__.py", "config.py", "orphan_check.py",
}
SKIP_SUFFIXES = ("_helpers.py",)
SKIP_PREFIXES = ("_",)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


# ── signal sources (read once) ───────────────────────────────────────────────
def external_wiring_corpus() -> str:
    """Hook/launchd wiring outside the repository relation graph."""
    parts: list[str] = []
    for p in (REPO / ".claude" / "settings.json",
              Path.home() / ".claude" / "settings.json",
              Path.home() / ".codex" / "hooks.json"):
        parts.append(_read(p))
    la = Path.home() / "Library" / "LaunchAgents"
    if la.is_dir():
        for plist in la.glob("com.agent-infra.*.plist"):
            parts.append(_read(plist))
    return "\n".join(parts)


def consumer_corpus() -> dict[str, str]:
    """Real-consumer surfaces, keyed by area, with inventories filtered out."""
    out: dict[str, str] = {}
    roots = {
        "skills": [Path.home() / "Projects" / "skills"],
        "rules": [REPO / ".claude" / "rules"],
        "decisions": [REPO / "decisions"],
        "plans": [REPO / ".claude" / "plans"],
        "agents": [REPO / ".claude" / "agents"],
        "memory": [REPO / ".claude" / "agent-memory",
                   Path.home() / ".claude" / "projects"
                   / "-Users-alien-Projects-agent-infra" / "memory"],
    }
    for area, dirs in roots.items():
        chunks: list[str] = []
        for d in dirs:
            if not d.is_dir():
                continue
            for f in d.rglob("*"):
                if not f.is_file():
                    continue
                if any(part in INVENTORY_DIRS for part in f.parts):
                    continue
                if any(m in f.name for m in INVENTORY_MARKERS):
                    continue
                if f.suffix not in (".md", ".sh", ".py", ".txt", ".json"):
                    continue
                chunks.append(_read(f))
        out[area] = "\n".join(chunks)
    return out


def invocation_counts(days: int) -> dict[str, str]:
    if not AGENTLOGS_DB.exists() or AGENTLOGS_DB.stat().st_size == 0:
        return {}
    try:
        con = open_db_ro(AGENTLOGS_DB)
    except sqlite3.Error:
        return {}
    try:
        rows = con.execute(
            "SELECT args_json FROM tool_calls "
            "WHERE tool_name='Bash' AND ts_start > date('now', ?)",
            (f"-{days} days",),
        ).fetchall()
    except sqlite3.Error:
        return {}
    finally:
        con.close()
    blob = "\n".join((r[0] or "") for r in rows)
    return {"__blob__": blob}  # counted per-script below to avoid N queries


# ── per-script signal computation ─────────────────────────────────────────────
def is_generator(path: Path) -> bool:
    name = path.name
    if name in SKIP_FILES or name in SKIP_SUFFIXES:
        return False
    if any(name.endswith(s) for s in SKIP_SUFFIXES):
        return False
    if any(name.startswith(p) for p in SKIP_PREFIXES):
        return False
    return True


def _incoming_paths(
    graph: CodeRelationGraph,
    rel: str,
    relation_types: set[str],
) -> set[str]:
    try:
        hops = graph.impact(
            rel,
            max_depth=1,
            relation_types=relation_types,
            include_ambiguous=False,
        )
    except ValueError:
        return set()
    return {
        graph.nodes[hop.relation.source].path
        for hop in hops
        if graph.nodes[hop.relation.source].path
        and graph.nodes[hop.relation.source].path != rel
    }


def check_script(
    path: Path,
    *,
    external_wiring: str,
    consumers: dict[str, str],
    graph: CodeRelationGraph,
    inv_blob: str,
) -> dict:
    name = path.name
    rel = path.relative_to(REPO).as_posix()

    wired_paths = _incoming_paths(
        graph,
        rel,
        {"configures", "executes", "invokes_recipe", "launches", "sources"},
    )
    wired = bool(wired_paths) or any(
        alias in external_wiring for alias in (name, name.rsplit(".", 1)[0])
    )
    imported = bool(_incoming_paths(graph, rel, {"calls", "imports"}))

    ref_areas = [area for area, blob in consumers.items()
                 if any(a in blob for a in (name, name.rsplit(".", 1)[0]))]
    referenced = bool(ref_areas)

    invocations = inv_blob.count(name) if inv_blob else 0

    on_allowlist = name in OCCASIONAL_MANUAL

    flagged = (not wired and not imported and not referenced
               and invocations < 3 and not on_allowlist)

    return {
        "script": name,
        "wired": wired,
        "imported": imported,
        "referenced_by": ref_areas,
        "invocations_90d": invocations,
        "occasional_manual": on_allowlist,
        "flagged": flagged,
    }


def scan(days: int = 90, with_invocations: bool = False) -> dict:
    external_wiring = external_wiring_corpus()
    consumers = consumer_corpus()
    source_dirs = [REPO, SCRIPTS]
    if (REPO / "src").is_dir():
        source_dirs.append(REPO / "src")
    graph = build_code_relations(REPO, python_source_dirs=source_dirs)
    graph.require_complete()
    # The invocation signal scans the whole agentlogs args_json (11GB / ~500K rows)
    # into memory — seconds-to-minutes. It is the WEAKEST signal (it only RESCUES a
    # statically-orphaned script that's actually run directly) and report-only output
    # is hand-verified before any deletion, so it is OFF by default to keep `just
    # orphan-check` / doctor instant. Opt in with --with-invocations for the rescue pass.
    inv_blob = invocation_counts(days).get("__blob__", "") if with_invocations else ""

    results: list[dict] = []
    for f in sorted(SCRIPTS.glob("*.py")) + sorted(SCRIPTS.glob("*.sh")):
        if not is_generator(f):
            continue
        results.append(check_script(
            f,
            external_wiring=external_wiring,
            consumers=consumers,
            graph=graph,
            inv_blob=inv_blob,
        ))

    flagged = [r for r in results if r["flagged"]]
    suppressed = [r for r in results
                  if r["occasional_manual"] and not r["wired"]
                  and not r["imported"] and not r["referenced_by"]]
    return {
        "days": days,
        "total_generators": len(results),
        "flagged": flagged,
        "suppressed_by_allowlist": suppressed,
        "results": results,
    }


def render(rep: dict) -> str:
    L: list[str] = []
    L.append(f"# Orphan-check — {rep['total_generators']} generators scanned "
             f"(invocation window {rep['days']}d)")
    L.append("Report-only. A flag means zero deterministic consumer; re-verify "
             "by hand before deleting (the manual sweep's false-negative rate was "
             "high — drill into importlib + skill-script chains).\n")
    fl = rep["flagged"]
    if not fl:
        L.append("✓ No orphaned generators — every script is wired, imported, "
                 "referenced by a real consumer, or on the occasional-manual allowlist.")
    else:
        L.append(f"⚠ {len(fl)} candidate orphan(s) — generator with "
                 "wired=no ∧ imported=no ∧ referenced=no ∧ invocations<3/window:\n")
        for r in fl:
            L.append(f"- `{r['script']}` — invocations(90d)={r['invocations_90d']}")
    sup = rep["suppressed_by_allowlist"]
    if sup:
        L.append(f"\n_({len(sup)} unwired script(s) suppressed by the "
                 "occasional-manual allowlist — review the allowlist itself "
                 "periodically; it is where a false negative hides.)_")
    return "\n".join(L)


def main() -> int:
    args = sys.argv[1:]
    days = 90
    if "--days" in args:
        days = int(args[args.index("--days") + 1])
    rep = scan(days, with_invocations="--with-invocations" in args)
    if "--json" in args:
        print(json.dumps(rep, indent=2, default=str))
        return 0
    print(render(rep))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
