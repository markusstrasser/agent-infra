#!/usr/bin/env python3
"""Generate the compact governance index from the CANONICAL sources.

The single-source substrate for curated-governance injection (critique) and
governance clash-detection (ADR 2026-06-16-governance-clash-detection). Consumers
LOAD `.claude/governance-index.md`; none re-state governance (the shared-invariant
rule — a re-stated copy is exactly the stale-noise anti-pattern this exists to kill).

Deterministic output (NO timestamp) → regenerating only churns git when a source
actually changed, mirroring `com.agent-infra.codebase-map-refresh`. Wire a launchd
WatchPath on the three sources to keep it current.

Canonical sources (per --repo):
  GOALS.md                          → telos one-liners (core sections only)
  CLAUDE.md  <constitution>         → PRINCIPLE: <n> <title>
  .claude/rules/vetoed-decisions.md → VETO: <name> — <verdict clause>
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Telos-bearing GOALS sections (operational sections like Strategy/Execution are skipped
# — the index is for "what we optimize for / must not violate", not how-we-run).
CORE_GOAL_SECTIONS = {
    "Mission",
    "Generative Principle",
    "Success Metric",
    "Self-Modification Boundaries",
    "Goal-Drift Detection",
    "Quality Standard",
}


def _first_sentence(s: str, limit: int = 150) -> str:
    s = re.sub(r"[*`]", "", s)  # strip markdown emphasis/code bleed
    s = re.split(r"(?<=[.!?])\s", s.strip())[0].strip()
    return (s[: limit - 1] + "…") if len(s) > limit else s


def extract_goals(text: str) -> list[str]:
    out: list[str] = []
    parts = re.split(r"^##\s+(.+)$", text, flags=re.M)  # [pre, h1, body1, h2, body2, ...]
    body_iter = iter(parts[1:])
    for header, body in zip(body_iter, body_iter):
        header = header.strip()
        if header not in CORE_GOAL_SECTIONS:
            continue
        for line in body.strip().splitlines():
            s = line.strip().lstrip(">").strip()
            if not s or s.startswith(("<!--", "**Human", "| ", "#")):
                continue
            out.append(f"{header}: {_first_sentence(s)}")
            break
    return out


def extract_principles(text: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(r"^\*\*(\d+)\.\s+([^*]+?)\.\*\*", text, flags=re.M):
        out.append(f"P{m.group(1)} {m.group(2).strip()}")
    return out


def extract_vetoes(text: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(r"^- \*\*(.+?)\*\*\s+—\s+(.+)$", text, flags=re.M):
        name = m.group(1).strip().strip("~")  # ~~struck~~ vetoes keep their name
        verdict = re.split(r"\s+→\s+", m.group(2).strip())[0]  # drop the pointer
        out.append(f"{name} — {_first_sentence(verdict, 120)}")
    return out


def build_index(repo: Path) -> str:
    goals_src = repo / "GOALS.md"
    claude_src = repo / "CLAUDE.md"
    vetoed_src = repo / ".claude" / "rules" / "vetoed-decisions.md"

    goals = extract_goals(goals_src.read_text()) if goals_src.is_file() else []
    principles = extract_principles(claude_src.read_text()) if claude_src.is_file() else []
    vetoes = extract_vetoes(vetoed_src.read_text()) if vetoed_src.is_file() else []

    lines = [
        f"# Governance Index — {repo.name} (GENERATED — do not edit)",
        "",
        "Compact single-source governance for curated injection + clash-detection.",
        "Consumers LOAD this; never re-state it. Canonical: GOALS.md · CLAUDE.md"
        " <constitution> · .claude/rules/vetoed-decisions.md. Regen: `just governance-index`.",
        "",
        "## GOALS (the telos)",
        *(f"- {g}" for g in goals),
        "",
        "## PRINCIPLES",
        *(f"- {p}" for p in principles),
        "",
        "## VETOED (do not re-propose)",
        *(f"- {v}" for v in vetoes),
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, default=Path.cwd())
    ap.add_argument("--out", type=Path, default=None,
                    help="default <repo>/.claude/governance-index.md")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the on-disk index is stale (for CI/WatchPath)")
    args = ap.parse_args()

    repo = args.repo.resolve()
    out = args.out or (repo / ".claude" / "governance-index.md")
    index = build_index(repo)

    if args.check:
        current = out.read_text() if out.is_file() else ""
        if current != index:
            print(f"governance-index STALE: {out}", file=sys.stderr)
            return 1
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(index)
    n = index.count("\n- ")
    print(f"wrote {out} ({n} entries, {len(index)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
