#!/usr/bin/env python3
"""steward_reconcile.py — flag open steward proposals whose artifact already shipped.

The RSI loop CAPTURES steward proposals but never RECONCILES them against shipped
work, so already-done proposals accrete: the 2026-07-06 triage found 26/71 open
proposals were ALREADY-DONE or STALE (docs/audit/2026-07-06-steward-triage-*.md).
The manual method — "checked against implemented/, git log, and vetoed-decisions;
every ALREADY-DONE cites a live file read" — is exactly the deterministic-locate +
human-decide split this encodes:

  - LOCATE (this script, cheap, deterministic): a proposal whose slug tokens match an
    already-shipped hook/script basename, OR a same-slug file already in implemented/,
    is a LIKELY-ALREADY-DONE candidate. Cite the evidence path.
  - DECIDE (human/agent, never here): closing requires reading the cited source to
    confirm the proposal's intent actually shipped. A grep hit LOCATES, it never
    DECIDES (global rule: regex is a false-positive-prone locator). So this is
    REPORT-ONLY — it flags candidates and prints the verify command; it never moves,
    edits, or closes a proposal.

Surfaced in the pulse tick drain phase so the flag can't sit invisibly (the exact
failure it fixes). Consumers LOAD `reconcile()` — they never re-derive the heuristic.

Usage:
  steward_reconcile.py                 # human-readable report
  steward_reconcile.py --json          # machine lane (pulse tick imports reconcile())
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HOME = Path.home()
STEWARD_DIR = HOME / ".claude" / "steward-proposals"
IMPLEMENTED_DIR = STEWARD_DIR / "implemented"
PROJECTS = HOME / "Projects"

# Roots where a shipped hook/script artifact would live. Bounded on purpose — a wider
# sweep buys false positives, not recall (the strong signal is a hook/script basename).
ARTIFACT_ROOTS = (
    PROJECTS / "skills" / "hooks",
    HOME / ".claude" / "skills",
    HOME / ".claude" / "hooks",
)
# Per-repo scripts/hooks dirs (skills/hooks covers the shared set; repos hold their own).
ARTIFACT_GLOBS = ("*/scripts", "*/.claude/hooks", "*/.claude/rules")

# Tokens that carry no discriminating signal for slug↔artifact matching. A proposal
# and an unrelated hook both containing "hook" is not evidence they are the same thing.
_STOP = {
    "the", "a", "an", "for", "and", "to", "not", "no", "of", "in", "on", "is",
    "hook", "guard", "gate", "check", "pretool", "posttool", "stop", "userprompt",
    "session", "start", "sh", "py", "md", "add", "fix", "new", "use",
}
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")
_BACKTICK_FILE = re.compile(r"`([A-Za-z0-9_./-]+\.(?:sh|py|ts))`")
# One name is not a match. Require ≥2 shared discriminating tokens to flag.
MIN_SHARED = 2
# …and a real overlap ratio against the artifact (kills "shares 2 of its 15 tokens").
MIN_RATIO = 0.5


def _tokens(name: str) -> set[str]:
    """Discriminating tokens of a slug/basename: date prefix + extension stripped,
    split on non-alphanumerics, stopwords dropped, ≥2-char tokens kept."""
    name = _DATE_RE.sub("", name)
    name = re.sub(r"\.(sh|py|ts|md|json)$", "", name)
    toks = re.split(r"[^a-z0-9]+", name.lower())
    return {t for t in toks if len(t) >= 2 and t not in _STOP}


def _open_proposals() -> list[Path]:
    if not STEWARD_DIR.is_dir():
        return []
    skip = {"README.md"}
    return sorted(
        p for p in STEWARD_DIR.glob("*.md")
        if p.is_file() and p.name not in skip and not p.name.startswith("TRIAGE-")
    )


def _artifact_index() -> dict[str, Path]:
    """basename → path for every candidate shipped hook/script. First-seen wins;
    only the basename+tokens matter for matching, so collisions are immaterial."""
    idx: dict[str, Path] = {}
    for root in ARTIFACT_ROOTS:
        if root.is_dir():
            for ext in ("*.sh", "*.py"):
                for f in root.rglob(ext):
                    idx.setdefault(f.name, f)
    for glob in ARTIFACT_GLOBS:
        for d in PROJECTS.glob(glob):
            if d.is_dir():
                for ext in ("*.sh", "*.py"):
                    for f in d.glob(ext):
                        idx.setdefault(f.name, f)
    return idx


def _implemented_tokens() -> list[tuple[str, set[str]]]:
    if not IMPLEMENTED_DIR.is_dir():
        return []
    return [(p.name, _tokens(p.stem)) for p in IMPLEMENTED_DIR.glob("*.md")]


def _best_match(slug_tokens: set[str], name: str, cand_tokens: set[str]) -> tuple[int, float]:
    shared = slug_tokens & cand_tokens
    ratio = len(shared) / len(cand_tokens) if cand_tokens else 0.0
    return len(shared), ratio


def reconcile() -> dict:
    """Return {candidates: [...], open_count, candidate_count}. Report-only, read-only.

    A candidate carries: proposal, slug, signal (dup-implemented|artifact-exists),
    evidence (path), shared (matched tokens), verify (the read-the-source command).
    The verify command is load-bearing — the candidate is a LOCATE, the operator
    DECIDES by reading `evidence`."""
    proposals = _open_proposals()
    art_idx = _artifact_index()
    impl = _implemented_tokens()
    art_tokens = {name: _tokens(name) for name in art_idx}

    candidates: list[dict] = []
    for p in proposals:
        slug_toks = _tokens(p.stem)
        if not slug_toks:
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        # Names the proposal explicitly cites — a matched cited artifact is the
        # strongest signal (it's the exact thing the proposal said it would create).
        cited = {m.group(1).rsplit("/", 1)[-1] for m in _BACKTICK_FILE.finditer(text)}

        best: dict | None = None

        # Signal 0 (strongest): the proposal cites a hook/script BY NAME, that exact
        # basename exists on disk, AND the name shares a discriminating token with the
        # proposal slug — i.e. the cited file is the proposal's OWN subject, not a
        # context file it merely modifies. Catches userprompt-clock (cited
        # `userprompt-clock.sh` shares "clock"); rejects a proposal that cites an
        # unrelated existing hook (`stop-smart-judge.sh` shares nothing with its slug).
        for name in cited:
            path = art_idx.get(name)
            if path is None:
                continue
            overlap = _tokens(name) & slug_toks
            if not overlap:
                continue
            cand = {"signal": "artifact-exists", "evidence": _short(path),
                    "cited": True, "shared": sorted(overlap), "score": (99, 1.0)}
            if best is None or cand["score"] > best["score"]:
                best = cand

        # Signal 1: a same-intent proposal already sits in implemented/.
        for iname, itoks in impl:
            shared, ratio = _best_match(slug_toks, iname, itoks)
            if shared >= MIN_SHARED and ratio >= MIN_RATIO:
                cand = {"signal": "dup-implemented", "evidence": f"implemented/{iname}",
                        "shared": sorted(slug_toks & itoks), "score": (shared, round(ratio, 2))}
                if best is None or cand["score"] > best["score"]:
                    best = cand

        # Signal 2: a shipped hook/script basename matches the proposal slug.
        for name, path in art_idx.items():
            shared, ratio = _best_match(slug_toks, name, art_tokens[name])
            if shared < MIN_SHARED or ratio < MIN_RATIO:
                continue
            score = (shared + (2 if name in cited else 0), round(ratio, 2))
            cand = {"signal": "artifact-exists", "evidence": _short(path),
                    "cited": name in cited, "shared": sorted(slug_toks & art_tokens[name]),
                    "score": score}
            if best is None or cand["score"] > best["score"]:
                best = cand

        if best is not None:
            best.update({
                "proposal": p.name,
                "verify": f"read {_short(p)} + {best['evidence']} — same intent? then mv to implemented/",
            })
            best.pop("score", None)
            candidates.append(best)

    return {
        "open_count": len(proposals),
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def _short(p: Path) -> str:
    return str(p).replace(str(HOME), "~")


def render(res: dict) -> str:
    n, total = res["candidate_count"], res["open_count"]
    if not n:
        return f"steward-reconcile: {total} open proposals, 0 likely-already-done.\n"
    lines = [
        f"## Steward reconcile — {n}/{total} open proposals likely ALREADY-DONE",
        "_Report-only LOCATE (deterministic). Read the cited source to DECIDE before closing._",
        "",
    ]
    for c in sorted(res["candidates"], key=lambda x: x["signal"]):
        tag = "★" if c.get("cited") else " "
        lines.append(f"- [{c['signal']}]{tag} **{c['proposal']}**")
        lines.append(f"    ↳ evidence: `{c['evidence']}`  · shared: {', '.join(c['shared'])}")
        lines.append(f"    ↳ verify: {c['verify']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Flag open steward proposals whose artifact already shipped")
    ap.add_argument("--json", action="store_true", help="machine lane (pulse tick imports reconcile())")
    args = ap.parse_args()
    res = reconcile()
    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print(render(res), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
