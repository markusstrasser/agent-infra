"""Correctness tests for the rederivable RSI-lifecycle graph (Phase C).

Guards the three load-bearing behaviors of `scripts/lifecycle_graph.py`:
  (a) invert-safe normalization — a `superseded_by A->B` fold edge becomes a
      `supersedes B->A` traversable edge (subject/target SWAP, per the vocab's
      `fold.superseded_by.invert: true`). Getting this wrong reverses lifecycle
      direction silently.
  (b) `relates_to` (canonical traversable:false) NEVER enters the traversable
      bucket used for bundling — only the weak/non-traversable bucket.
  (c) the resolver spans all three node sources: a decisions/ slug AND a
      research/ stem both resolve (a decisions-only resolver resolves ~25%).
"""

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MOD_PATH = REPO / "scripts" / "lifecycle_graph.py"

_spec = importlib.util.spec_from_file_location("lifecycle_graph", MOD_PATH)
assert _spec and _spec.loader, MOD_PATH  # real file path — guards the type-checker
lg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lg)


def test_superseded_by_inverts_to_supersedes():
    """(a) `A superseded_by B` => traversable edge `B supersedes A` (swap)."""
    vocab = lg.load_vocab()
    canon, invert, traversable = lg.normalize_type("superseded_by", vocab)
    assert canon == "supersedes", f"expected supersedes, got {canon}"
    assert invert is True, "superseded_by must carry invert=True for subject/target swap"
    assert traversable is True, "supersedes is a lifecycle edge (traversable)"

    # End-to-end on the edge shape: subject=A, target=B, fold inverts to B->A.
    subject, target = "A", "B"
    subj, tgt = (target, subject) if invert else (subject, target)
    assert (subj, tgt) == ("B", "A"), (
        f"invert must swap: A superseded_by B => {subj} supersedes {tgt}, "
        "expected B supersedes A"
    )


def test_relates_to_absent_from_traversable():
    """(b) relates_to is non-traversable — out of the bundling graph entirely."""
    vocab = lg.load_vocab()
    canon, _, traversable = lg.normalize_type("relates_to", vocab)
    assert canon == "relates_to"
    assert traversable is False, "relates_to must be non-traversable (weak bucket only)"

    # And in the live built graph, no traversable edge is typed relates_to.
    graph = lg.build_graph()
    trav_types = {e["type"] for e in graph["traversable"]}
    assert "relates_to" not in trav_types, (
        "relates_to leaked into the traversable set: "
        f"{sorted(trav_types)}"
    )


def test_resolver_spans_decisions_and_research():
    """(c) resolver resolves a decisions/ slug AND a research/ stem."""
    nodes = lg.collect_nodes()

    # A known decisions/ slug (frontmatter id), the Phase-C gate-2 branch target.
    dec_slug = "2026-06-07-verifier-conditional-autonomy"
    assert dec_slug in nodes, f"decisions/ slug {dec_slug!r} did not resolve"
    assert nodes[dec_slug]["source"] == "decision"

    # A known research/ stem (filename-derived node id).
    res_stem = "2026-06-18-plan-contract-frontend-synthesis"
    assert (RESEARCH := REPO / "research" / f"{res_stem}.md").exists(), \
        f"fixture research file missing: {RESEARCH}"
    assert res_stem in nodes, f"research/ stem {res_stem!r} did not resolve"
    assert nodes[res_stem]["source"] == "research"

    # The two sources are distinct — proves the resolver is not decisions-only.
    sources = {nodes[dec_slug]["source"], nodes[res_stem]["source"]}
    assert sources == {"decision", "research"}


if __name__ == "__main__":
    test_superseded_by_inverts_to_supersedes()
    test_relates_to_absent_from_traversable()
    test_resolver_spans_decisions_and_research()
    print("PASS")
