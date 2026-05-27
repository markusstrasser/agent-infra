"""Phase B — source identity crosswalk."""
from __future__ import annotations

import pytest

from corpus_core.identity_crosswalk import (
    STRONG_IDENTITY_LINKS,
    insert_crosswalk,
    resolve_corpus_to_repos,
    resolve_repo_to_corpus,
)


def test_insert_resolve_round_trip(corpus_root):
    insert_crosswalk(
        repo="intel",
        repo_local_id="01HM9F-1234-5678",
        corpus_source_id="doi_10_1097_fpc_xyz",
        link_type="mainEntityOfPage",
        asserted_by="urn:agent:service:test",
    )
    out = resolve_repo_to_corpus("intel", "01HM9F-1234-5678")
    assert out == "doi_10_1097_fpc_xyz"


def test_composite_pk_idempotency(corpus_root):
    """Re-insert with same (repo, local_id, corpus_id, link_type) is no-op."""
    for _ in range(3):
        insert_crosswalk(
            repo="phenome",
            repo_local_id="doc_001",
            corpus_source_id="pmid_12345678",
            link_type="sameAs",
            asserted_by="urn:agent:service:test",
        )
    pairs = resolve_corpus_to_repos("pmid_12345678")
    assert len(pairs) == 1


def test_multiple_link_types_for_same_pair(corpus_root):
    """Same (repo, local_id, corpus_id) can carry BOTH mainEntityOfPage
    AND cites — they're DIFFERENT facts about the relationship."""
    insert_crosswalk(
        repo="intel",
        repo_local_id="filing_xyz",
        corpus_source_id="doi_10_1234_abc",
        link_type="mainEntityOfPage",
        asserted_by="urn:agent:service:test",
    )
    insert_crosswalk(
        repo="intel",
        repo_local_id="filing_xyz",
        corpus_source_id="doi_10_1234_abc",
        link_type="cites",
        asserted_by="urn:agent:service:test",
    )
    pairs = resolve_corpus_to_repos("doi_10_1234_abc")
    types = {p[2] for p in pairs}
    assert types == {"mainEntityOfPage", "cites"}


def test_resolve_corpus_to_repos_cross_repo(corpus_root):
    """Multiple repos pointing at the same corpus source surface in the
    reverse lookup."""
    for repo, local in [("intel", "f_1"), ("phenome", "d_1"), ("genomics", "v_1")]:
        insert_crosswalk(
            repo=repo,
            repo_local_id=local,
            corpus_source_id="doi_shared",
            link_type="mainEntityOfPage",
            asserted_by="urn:agent:service:test",
        )
    pairs = resolve_corpus_to_repos("doi_shared")
    assert sorted(p[0] for p in pairs) == ["genomics", "intel", "phenome"]


def test_link_type_check_rejects_invented_enum(corpus_root):
    with pytest.raises(ValueError, match="unknown link_type"):
        insert_crosswalk(
            repo="intel",
            repo_local_id="x",
            corpus_source_id="doi_x",
            link_type="hasFor",  # not in CHECK
            asserted_by="urn:agent:service:test",
        )


def test_link_type_is_required(corpus_root):
    """REQUIRED kwarg — no default."""
    with pytest.raises(TypeError):
        insert_crosswalk(  # type: ignore[call-arg]
            repo="intel",
            repo_local_id="x",
            corpus_source_id="doi_x",
            asserted_by="urn:agent:service:test",
        )


def test_asserted_by_must_be_urn(corpus_root):
    with pytest.raises(ValueError, match="urn:agent"):
        insert_crosswalk(
            repo="intel",
            repo_local_id="x",
            corpus_source_id="doi_x",
            link_type="mainEntityOfPage",
            asserted_by="alice",
        )


def test_resolve_default_excludes_weak_links(corpus_root):
    """Default link_types only include sameAs + mainEntityOfPage.
    A 'cites' relation should NOT resolve as identity."""
    insert_crosswalk(
        repo="intel",
        repo_local_id="f_cites_only",
        corpus_source_id="doi_cites_target",
        link_type="cites",
        asserted_by="urn:agent:service:test",
    )
    assert resolve_repo_to_corpus("intel", "f_cites_only") is None
    # Caller can broaden:
    assert resolve_repo_to_corpus(
        "intel", "f_cites_only", link_types=("cites",)
    ) == "doi_cites_target"


def test_resolve_returns_none_when_missing(corpus_root):
    assert resolve_repo_to_corpus("intel", "no_such_id") is None
    assert resolve_corpus_to_repos("doi_no_such") == []


def test_strong_identity_links_constant():
    """Default safety: don't broaden silently in a future commit."""
    assert STRONG_IDENTITY_LINKS == ("sameAs", "mainEntityOfPage")


def test_slug_doi_parity_with_store():
    """CRH: intel sync derives slugs via corpus_core.identity.slug_doi;
    if anyone reimplements the slug in intel, this test should catch
    divergence on the corpus side."""
    from corpus_core.identity import slug_doi
    from corpus_core.store import _slug_doi
    sample = "10.1097/FPC.0000000000000456"
    assert slug_doi(sample) == _slug_doi(sample)
