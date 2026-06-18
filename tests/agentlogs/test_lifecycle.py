"""Correctness tests for the agentlogs-native RSI-lifecycle edge index (Phase C).

Guards the three load-bearing behaviors ported from the oracle
(`scripts/lifecycle_graph.py`, deleted), now homed in `lifecycle_edges`:
  (a) invert-safe normalization — a synthetic `superseded_by A->B` decision
      relation yields a row `supersedes B->A` (subject/target SWAP, per the
      vocab's `fold.superseded_by.invert: true`). Reversing this silently
      reverses lifecycle direction.
  (b) `relates_to` (canonical traversable:false) NEVER gets traversable=1 — it
      stays in the weak/non-traversable bucket excluded from bundling.
  (c) the resolver spans all three node sources: a decisions/ slug AND a
      research/ stem both resolve to non-dangling targets (a decisions-only
      resolver resolves ~25%).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import agentlogs
from agentlogs import lifecycle as lc

REPO = Path(__file__).resolve().parents[2]


def _synthetic_repo(tmp_path: Path) -> Path:
    """A minimal repo root: a vocab copy + two decisions wired A->B (superseded_by)
    and a relates_to edge, so build_edges has invert + weak rows to produce."""
    (tmp_path / "scripts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "decisions").mkdir(parents=True, exist_ok=True)
    (tmp_path / "research").mkdir(parents=True, exist_ok=True)
    # Reuse the canonical vocab verbatim — the test is about edge assembly, not vocab.
    (tmp_path / "scripts" / "lifecycle_relations.json").write_text(
        (REPO / "scripts" / "lifecycle_relations.json").read_text()
    )
    (tmp_path / "decisions" / "A.md").write_text(
        "---\n"
        "id: A\n"
        "relations:\n"
        "  - type: superseded_by\n"
        "    target: B\n"
        "  - type: relates_to\n"
        "    target: B\n"
        "---\n\nbody\n"
    )
    (tmp_path / "decisions" / "B.md").write_text("---\nid: B\n---\n\nbody\n")
    return tmp_path


def test_superseded_by_inverts_to_supersedes(tmp_path):
    """(a) `A superseded_by B` => stored row `supersedes` with subject=B,target=A."""
    repo = _synthetic_repo(tmp_path)
    db = agentlogs.connect(tmp_path / "lc.db")
    try:
        lc.build_edges(db, repo)
        rows = db.execute(
            "SELECT subject, type, target, traversable FROM lifecycle_edges "
            "WHERE type = 'supersedes'"
        ).fetchall()
    finally:
        db.close()
    assert len(rows) == 1, f"expected one supersedes row, got {[dict(r) for r in rows]}"
    r = rows[0]
    assert (r["subject"], r["target"]) == ("B", "A"), (
        f"invert must swap: A superseded_by B => supersedes B->A, got "
        f"{r['subject']}->{r['target']}"
    )
    assert r["traversable"] == 1, "supersedes is a lifecycle edge (traversable)"


def test_relates_to_never_traversable(tmp_path):
    """(b) no relates_to row is traversable=1 — in the synthetic repo AND the live one."""
    # Synthetic: the relates_to edge we authored must land weak.
    repo = _synthetic_repo(tmp_path)
    db = agentlogs.connect(tmp_path / "lc.db")
    try:
        lc.build_edges(db, repo)
        bad_synth = db.execute(
            "SELECT COUNT(*) FROM lifecycle_edges "
            "WHERE type = 'relates_to' AND traversable = 1"
        ).fetchone()[0]
        # Live repo: same invariant over the real decision corpus.
        lc.build_edges(db, REPO)
        bad_live = db.execute(
            "SELECT COUNT(*) FROM lifecycle_edges "
            "WHERE type = 'relates_to' AND traversable = 1"
        ).fetchone()[0]
    finally:
        db.close()
    assert bad_synth == 0, "synthetic relates_to leaked into the traversable set"
    assert bad_live == 0, "live relates_to leaked into the traversable set"


def test_resolver_spans_decisions_and_research(tmp_path):
    """(c) resolver resolves a decisions/ slug AND a research/ stem (non-dangling)."""
    nodes = lc.collect_nodes(REPO)

    # A known decisions/ slug (frontmatter id), the Phase-C gate-3 branch target.
    dec_slug = "2026-06-07-verifier-conditional-autonomy"
    assert dec_slug in nodes, f"decisions/ slug {dec_slug!r} did not resolve"
    assert nodes[dec_slug]["source"] == "decision"

    # A known research/ stem (filename-derived node id).
    res_stem = "2026-06-18-plan-contract-frontend-synthesis"
    assert (REPO / "research" / f"{res_stem}.md").exists(), \
        f"fixture research file missing: research/{res_stem}.md"
    assert res_stem in nodes, f"research/ stem {res_stem!r} did not resolve"
    assert nodes[res_stem]["source"] == "research"

    # The two sources are distinct — proves the resolver is not decisions-only.
    assert {nodes[dec_slug]["source"], nodes[res_stem]["source"]} == {"decision", "research"}

    # And the live build resolves the gate-3 branches_from edge to a non-dangling row.
    db = agentlogs.connect(tmp_path / "lc.db")
    try:
        lc.build_edges(db, REPO)
        row = db.execute(
            "SELECT dangling FROM lifecycle_edges "
            "WHERE subject = ? AND type = 'branches_from' AND target = ?",
            ("2026-06-18-planning-lifecycle-contract", dec_slug),
        ).fetchone()
    finally:
        db.close()
    assert row is not None, "gate-3 branches_from edge missing"
    assert row["dangling"] == 0, "branches_from target should resolve (decisions/ node)"


# ── Phase B1: commit-body → commit --implements--> decision edges ───────────────
_IMPL_SLUG = "2026-06-18-phaseb-implements-trailer"  # date-slug decision id


def _synthetic_repo_with_decision_slug(tmp_path: Path) -> Path:
    """Synthetic repo whose decisions/ has a date-slug-id decision the commit pass
    can resolve a prose mention / trailer against."""
    repo = _synthetic_repo(tmp_path)
    (repo / "decisions" / f"{_IMPL_SLUG}.md").write_text(
        f"---\nid: {_IMPL_SLUG}\n---\n\nbody\n"
    )
    return repo


def _seed_commit(db, chash: str, body: str) -> None:
    """Insert a minimal agent-infra git_commits row carrying `body`."""
    db.execute(
        "INSERT INTO git_commits "
        "(hash, project, authored_at, author, subject, body) "
        "VALUES (?, 'agent-infra', '2026-06-18 00:00:00', 'T', 's', ?)",
        (chash, body),
    )


def test_commit_implements_trailer_emits_edge(tmp_path):
    """An explicit `Implements: <slug>` body trailer → a commit→decision edge with
    subject=commit-hash, type=implements, traversable=1, source='commit-trailer'."""
    repo = _synthetic_repo_with_decision_slug(tmp_path)
    db = agentlogs.connect(tmp_path / "lc.db")
    chash = "a" * 40
    try:
        _seed_commit(db, chash, f"some body text\n\nImplements: {_IMPL_SLUG}\n")
        lc.build_edges(db, repo)
        rows = db.execute(
            "SELECT subject, type, target, traversable, dangling, source "
            "FROM lifecycle_edges WHERE type = 'implements'"
        ).fetchall()
    finally:
        db.close()
    assert len(rows) == 1, f"expected one implements edge, got {[dict(r) for r in rows]}"
    r = rows[0]
    assert r["subject"] == chash, "subject must be the commit hash"
    assert r["target"] == _IMPL_SLUG, "target must be the decision slug"
    assert r["traversable"] == 1, "implements is a traversable lifecycle edge"
    assert r["dangling"] == 0, "trailer slug resolves to a decision node"
    assert r["source"] == "commit-trailer", "explicit trailer must be tagged"


def test_commit_prose_mention_resolves_to_edge(tmp_path):
    """A prose date-slug mention that RESOLVES to a decision → edge with
    source='commit-mention'; a NON-resolving date-slug mention is SKIPPED."""
    repo = _synthetic_repo_with_decision_slug(tmp_path)
    db = agentlogs.connect(tmp_path / "lc.db")
    chash = "b" * 40
    try:
        # One resolving mention + one slug-shaped string that does NOT resolve.
        _seed_commit(
            db, chash,
            f"FLIP per {_IMPL_SLUG}; also touched 2026-03-19-late (no such decision)\n",
        )
        lc.build_edges(db, repo)
        rows = db.execute(
            "SELECT subject, target, source, traversable FROM lifecycle_edges "
            "WHERE type = 'implements'"
        ).fetchall()
    finally:
        db.close()
    assert len(rows) == 1, (
        "exactly one edge — the resolving mention; the non-resolving slug is "
        f"skipped, got {[dict(r) for r in rows]}"
    )
    r = rows[0]
    assert (r["subject"], r["target"]) == (chash, _IMPL_SLUG)
    assert r["source"] == "commit-mention", "prose mention must be tagged"
    assert r["traversable"] == 1


def test_commit_trailer_and_mention_dedup_to_one(tmp_path):
    """A commit with BOTH an Implements: trailer AND a prose mention of the SAME
    slug yields ONE edge, preferring source='commit-trailer'."""
    repo = _synthetic_repo_with_decision_slug(tmp_path)
    db = agentlogs.connect(tmp_path / "lc.db")
    chash = "c" * 40
    try:
        _seed_commit(
            db, chash,
            f"work on {_IMPL_SLUG} prose mention\n\nImplements: {_IMPL_SLUG}\n",
        )
        lc.build_edges(db, repo)
        rows = db.execute(
            "SELECT source FROM lifecycle_edges WHERE type = 'implements' "
            "AND subject = ?", (chash,),
        ).fetchall()
    finally:
        db.close()
    assert len(rows) == 1, f"trailer+mention of same slug must dedup, got {len(rows)}"
    assert rows[0]["source"] == "commit-trailer", "dedup must prefer the trailer"


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        test_superseded_by_inverts_to_supersedes(Path(d) / "a")
    with tempfile.TemporaryDirectory() as d:
        test_relates_to_never_traversable(Path(d) / "b")
    with tempfile.TemporaryDirectory() as d:
        test_resolver_spans_decisions_and_research(Path(d) / "c")
    with tempfile.TemporaryDirectory() as d:
        test_commit_implements_trailer_emits_edge(Path(d) / "d")
    with tempfile.TemporaryDirectory() as d:
        test_commit_prose_mention_resolves_to_edge(Path(d) / "e")
    with tempfile.TemporaryDirectory() as d:
        test_commit_trailer_and_mention_dedup_to_one(Path(d) / "f")
    print("PASS")
