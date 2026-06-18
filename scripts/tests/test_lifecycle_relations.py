"""Drift-test for the canonical lifecycle-relation vocabulary.

`scripts/lifecycle_relations.json` is the single source of truth for the
RSI-lifecycle relation types used in `decisions/*.md` frontmatter (and
downstream: improvement-log, predictions, trailers). This test enforces the
no-silent-drift guarantee: every `type:` value actually used across the
decision journal must be a KNOWN string — either canonical or fold-mapped.

It is report-only on fold-mapped usage (those are known-but-non-canonical,
cleanup-visible) and only HARD-FAILS on an UNKNOWN string, listing the
offenders so the drift is actionable.
"""

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
VOCAB = REPO / "scripts" / "lifecycle_relations.json"
DECISIONS = REPO / "decisions"


def _load_vocab():
    d = json.loads(VOCAB.read_text())
    return set(d["canonical"].keys()), set(d["fold"].keys())


def _frontmatter(text):
    """Return the YAML frontmatter block (between the first two '---'), or ''."""
    if not text.startswith("---"):
        return ""
    parts = text.split("---", 2)
    return parts[1] if len(parts) >= 3 else ""


def _relation_types(fm):
    """Extract `- type: X` values from inside a `relations:` block.

    Line-based (not full YAML) on purpose: it skips commented template lines
    (`# - type: ...`) and survives malformed/alternative frontmatter schemas
    that a strict YAML parse would crash on.
    """
    out = []
    in_block = False
    for raw in fm.splitlines():
        line = raw.rstrip()
        if re.match(r"^relations:", line):
            in_block = True
            continue
        if in_block:
            # A new top-level key (no leading whitespace, has a colon) ends the block.
            if line and not line[0].isspace() and re.match(r"^\S+:", line):
                in_block = False
                continue
            m = re.match(r"^\s*-\s*type:\s*(\S+)", line)
            if m:
                out.append(m.group(1))
    return out


def test_no_unknown_lifecycle_relation_strings():
    canonical, fold = _load_vocab()

    n_canonical = 0
    n_fold = 0
    unknown = {}  # string -> list of files

    for f in sorted(DECISIONS.glob("*.md")):
        fm = _frontmatter(f.read_text())
        if not fm:
            continue
        for t in _relation_types(fm):
            if t in canonical:
                n_canonical += 1
            elif t in fold:
                n_fold += 1
            else:
                unknown.setdefault(t, []).append(f.name)

    print(
        f"lifecycle-relations: {n_canonical} canonical, {n_fold} fold-mapped "
        f"(non-canonical-but-known), {len(unknown)} unknown"
    )

    assert not unknown, (
        "Unknown lifecycle-relation type string(s) — not in canonical or fold "
        f"of {VOCAB.relative_to(REPO)}: "
        + "; ".join(f"{s!r} ({', '.join(files)})" for s, files in sorted(unknown.items()))
    )


if __name__ == "__main__":
    test_no_unknown_lifecycle_relation_strings()
    print("PASS")
