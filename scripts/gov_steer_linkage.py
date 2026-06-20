#!/usr/bin/env python3
"""Steer-linkage for gov.py — join Gov-ID scaffolds + constitution atoms to steer/blindspot themes.

Sense-only: surfaces orphan themes and redundancy hypotheses. Does NOT emit shrink candidates
(zero-hit join is Goodhart-prone on path-scoped rules and safety constraints).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
THEMES_PATH = REPO / "config" / "steer_themes.yaml"
CLAUDE_MD = REPO / "CLAUDE.md"
BLINDSPOT_DIGEST = REPO / ".claude" / "blindspot-digest.md"
STEER_GLOB_OBSERVE = REPO / "artifacts" / "observe" / "*-steer-signals.jsonl"
STEER_GLOB_PROBE = Path.home() / ".claude" / "steer-mining" / "probe-*.jsonl"

_PRINCIPLE_START = re.compile(r"^\*\*(\d+)\.\s+([^*]+)\*\*", re.MULTILINE)
_BLINDSPOT_DIR = re.compile(
    r"^\*\*([A-Z_]+)\s+\([^)]+\)\*\* — (\d+)", re.MULTILINE
)
_TOKEN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN.findall(text.lower()))


def load_themes(path: Path = THEMES_PATH) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return list(data.get("themes") or [])


def steer_signal_paths() -> list[Path]:
    paths = sorted(STEER_GLOB_OBSERVE.parent.glob(STEER_GLOB_OBSERVE.name))
    if STEER_GLOB_PROBE.parent.exists():
        paths += sorted(STEER_GLOB_PROBE.parent.glob(STEER_GLOB_PROBE.name))
    seen: set[str] = set()
    out: list[Path] = []
    for p in paths:
        key = str(p.resolve())
        if key not in seen and p.is_file():
            seen.add(key)
            out.append(p)
    return out


def load_steer_signals(paths: list[Path] | None = None) -> list[dict]:
    rows: list[dict] = []
    for p in paths or steer_signal_paths():
        try:
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            continue
    return rows


def signal_text(row: dict) -> str:
    parts = [
        row.get("vector"),
        row.get("quote"),
        row.get("before"),
        row.get("what_approved"),
        row.get("type"),
    ]
    return " ".join(str(p) for p in parts if p).lower()


def score_themes_on_text(text: str, themes: list[dict]) -> dict[str, int]:
    t = text.lower()
    hits: dict[str, int] = {}
    for th in themes:
        n = sum(1 for kw in th.get("keywords") or [] if kw.lower() in t)
        if n:
            hits[th["id"]] = n
    return hits


def aggregate_theme_hits(signals: list[dict], themes: list[dict]) -> dict[str, int]:
    totals: dict[str, int] = {th["id"]: 0 for th in themes}
    for row in signals:
        for tid, n in score_themes_on_text(signal_text(row), themes).items():
            totals[tid] += n
    return totals


def parse_constitution_principles(path: Path = CLAUDE_MD) -> list[dict]:
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    start = text.find("### Principles")
    if start < 0:
        return []
    chunk = text[start:]
    end = chunk.find("\n### ", 1)
    if end > 0:
        chunk = chunk[:end]
    matches = list(_PRINCIPLE_START.finditer(chunk))
    out: list[dict] = []
    for i, m in enumerate(matches):
        n, title = m.group(1), m.group(2).strip()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(chunk)
        body = re.sub(r"\s+", " ", chunk[body_start:body_end]).strip()[:400]
        goal = f"{title}. {body}"
        out.append({
            "id": f"constitution:P{n}",
            "kind": "constitution",
            "path": str(path.relative_to(REPO)) if REPO in path.parents else str(path),
            "goal": goal,
            "verifier": None,
            "blast_radius": "constitution",
        })
    return out


def _owner_theme_map(themes: list[dict]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for th in themes:
        for oid in th.get("gov_owners") or []:
            out.setdefault(str(oid), []).append(th["id"])
    return out


def join_atoms_to_themes(atoms: list[dict], themes: list[dict]) -> list[dict]:
    owners = _owner_theme_map(themes)
    joined: list[dict] = []
    for atom in atoms:
        goal = atom.get("goal") or ""
        theme_hits = score_themes_on_text(goal, themes)
        for tid in owners.get(atom.get("id") or "", []):
            theme_hits[tid] = max(theme_hits.get(tid, 0), 1)
        joined.append({**atom, "theme_hits": theme_hits, "theme_score": sum(theme_hits.values())})
    return joined


def parse_blindspot_directions(path: Path = BLINDSPOT_DIGEST) -> dict[str, int]:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    return {m.group(1).lower(): int(m.group(2)) for m in _BLINDSPOT_DIR.finditer(text)}


def redundancy_pairs(atoms: list[dict], threshold: float = 0.55) -> list[dict]:
    """Jaccard on goal tokens — hypothesis only (one-line goals miss body dupes)."""
    pairs: list[dict] = []
    with_goals = [(a, _tokenize(a.get("goal") or "")) for a in atoms if a.get("goal")]
    for i, (a, ta) in enumerate(with_goals):
        if not ta:
            continue
        for b, tb in with_goals[i + 1:]:
            if not tb:
                continue
            j = len(ta & tb) / len(ta | tb)
            if j >= threshold:
                pairs.append({
                    "a": a["id"], "b": b["id"],
                    "jaccard": round(j, 3),
                    "note": "goal-token overlap — verify bodies before deduping",
                })
    return sorted(pairs, key=lambda x: -x["jaccard"])[:20]


def orphan_themes(
    theme_totals: dict[str, int],
    joined: list[dict],
    themes: list[dict],
    min_hits: int = 3,
) -> list[dict]:
    """Themes with steer hits but no scaffold goal overlap — architecture gap candidates."""
    by_id = {th["id"]: th for th in themes}
    orphans: list[dict] = []
    for tid, total in sorted(theme_totals.items(), key=lambda kv: -kv[1]):
        if total < min_hits:
            continue
        th = by_id.get(tid, {})
        owner_ids = {str(o) for o in (th.get("gov_owners") or [])}
        atom_ids = {a.get("id") for a in joined}
        if owner_ids & atom_ids:
            continue
        if not any(tid in (a.get("theme_hits") or {}) for a in joined):
            th = by_id.get(tid, {})
            orphans.append({
                "theme_id": tid,
                "label": th.get("label", tid),
                "steer_hits": total,
                "note": "no Gov-ID/constitution goal overlap — consider hook or Gov-ID owner",
            })
    return orphans


def build_linkage(artifacts: list[dict]) -> dict:
    themes = load_themes()
    constitution = parse_constitution_principles()
    atoms = list(artifacts) + constitution
    signals = load_steer_signals()
    theme_totals = aggregate_theme_hits(signals, themes)
    joined = join_atoms_to_themes(atoms, themes)
    top_atoms = sorted(
        [a for a in joined if a.get("theme_score", 0) > 0],
        key=lambda a: (-a["theme_score"], a["id"]),
    )[:15]
    return {
        "steer_sources": [str(p) for p in steer_signal_paths()],
        "signal_count": len(signals),
        "constitution_atoms": len(constitution),
        "theme_totals": theme_totals,
        "blindspot_directions": parse_blindspot_directions(),
        "top_linked_atoms": [
            {
                "id": a["id"],
                "kind": a.get("kind"),
                "theme_hits": a.get("theme_hits"),
                "goal_preview": (a.get("goal") or "")[:80],
            }
            for a in top_atoms
        ],
        "orphan_themes": orphan_themes(theme_totals, joined, themes),
        "redundancy_hypotheses": redundancy_pairs(atoms),
        "sense_only": True,
    }
