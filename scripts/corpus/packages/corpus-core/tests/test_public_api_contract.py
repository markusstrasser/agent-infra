"""Consumer-facing public API contract for corpus_core.

Why this exists: in 2026-06 a corpus_core refactor moved `exists`/`get`/
`paper_path`/`graph_db_path` from module-level functions onto the `CorpusStore`
instance, and added a required `store` argument to `ingest_pdf`/`annotate`/
`epistemic_surface`. The consumers (research-mcp, phenome, genomics, intel) were
NOT updated, so every `fetch_paper` died with
`module 'corpus_core.store' has no attribute 'exists'` — discovered only when an
agent hit it mid-task. No test caught the cross-repo drift.

This pins the exact surface those consumers depend on. If a future refactor
changes it incompatibly, THIS test fails here (in the producer), before it
silently breaks five downstream repos. It is a signature/shape contract — no
filesystem, network, or data required. When the contract is changed
deliberately, update this test in the same commit and bump consumers.
"""

from __future__ import annotations

import inspect

import corpus_core
from corpus_core import store as store_mod
from corpus_core.store import CorpusStore


# Instance methods consumers call on a CorpusStore handle (the ones that moved
# off the module in the breaking refactor). research-mcp/papers.py + server.py
# call exists/get/paper_path/graph_db_path; ingest.py uses derive_paper_id.
_REQUIRED_INSTANCE_METHODS = {
    "paper_path",
    "graph_db_path",
    "exists",
    "get",
    "derive_paper_id",
    "iter_papers",
    "write_metadata",
    "update_metadata",
    "register_revision",
}

# Module-level functions consumers still import directly.
_REQUIRED_MODULE_FUNCS = {"derive_paper_id", "sha256_file"}

# Error/record types consumers reference.
_REQUIRED_STORE_SYMBOLS = {
    "PaperStoreError",
    "PaperNotFoundError",
    "DOICollisionError",
    "PaperRecord",
    "RevisionResult",
}


def test_corpus_store_is_a_class_with_required_instance_methods():
    assert inspect.isclass(CorpusStore)
    for name in _REQUIRED_INSTANCE_METHODS:
        attr = getattr(CorpusStore, name, None)
        assert attr is not None, f"CorpusStore lost instance method {name!r}"
        assert callable(attr), f"CorpusStore.{name} is not callable"


def test_corpus_store_constructs_from_a_root():
    # The handle is `CorpusStore(root=...)` — boundary-injected, no global default.
    sig = inspect.signature(CorpusStore)
    assert "root" in sig.parameters, "CorpusStore must accept a `root`"


def test_store_module_exposes_funcs_and_types():
    for name in _REQUIRED_MODULE_FUNCS:
        assert callable(getattr(store_mod, name, None)), (
            f"corpus_core.store.{name} missing"
        )
    for name in _REQUIRED_STORE_SYMBOLS:
        assert getattr(store_mod, name, None) is not None, (
            f"corpus_core.store.{name} missing"
        )


def test_moved_methods_are_NOT_module_level():
    # Guards the exact regression direction: these must live on the instance, not
    # the module. If one reappears at module level a consumer may bind the wrong
    # one; if a consumer calls `store.exists(...)` (module) it must fail loudly,
    # which it does precisely because these are absent here.
    for name in ("exists", "get", "paper_path", "graph_db_path"):
        assert not hasattr(store_mod, name), (
            f"corpus_core.store.{name} reappeared at module level; consumers expect "
            f"it ONLY as a CorpusStore instance method"
        )


def test_ingest_pdf_takes_store_first():
    from corpus_core.ingest import ingest_pdf

    params = list(inspect.signature(ingest_pdf).parameters)
    assert params[0] == "store", (
        f"ingest_pdf(store, pdf_path, ...) expected; got {params[:2]}"
    )
    assert "pdf_path" in params


def test_annotate_requires_store_keyword():
    from corpus_core.annotate import annotate

    sig = inspect.signature(annotate)
    assert list(sig.parameters)[0] == "source_id"
    store_p = sig.parameters.get("store")
    assert store_p is not None and store_p.kind == inspect.Parameter.KEYWORD_ONLY, (
        "annotate(source_id, *, store, ...) — store must be keyword-only"
    )


def test_epistemic_surface_requires_store_keyword():
    from corpus_core.index import epistemic_surface

    sig = inspect.signature(epistemic_surface)
    assert list(sig.parameters)[0] == "source_id"
    store_p = sig.parameters.get("store")
    assert store_p is not None and store_p.kind == inspect.Parameter.KEYWORD_ONLY, (
        "epistemic_surface(source_id, *, store, ...) — store must be keyword-only"
    )


def test_schema_version_pinned():
    assert isinstance(corpus_core.SCHEMA_VERSION, str) and corpus_core.SCHEMA_VERSION
