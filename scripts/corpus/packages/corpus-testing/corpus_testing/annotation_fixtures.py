"""Sample annotation factories for tests."""
from __future__ import annotations

from typing import Any

from corpus_core.annotate import annotate
from corpus_core.store import CorpusStore


def make_annotation(
    store: CorpusStore,
    source_id: str = "doi_10_1234_test",
    *,
    repo: str = "agent-infra",
    actor_type: str = "service",
    actor_id: str = "urn:agent:service:test@0.0.1",
    scope: str = "test",
    **overrides: Any,
) -> str:
    """Convenience: write a minimal valid annotation, return its id.

    Overrides pass through to corpus_core.annotate.annotate().
    """
    store.paper_path(source_id).mkdir(parents=True, exist_ok=True)
    return annotate(
        source_id,
        store=store,
        repo=repo,  # type: ignore[arg-type]
        actor_type=actor_type,  # type: ignore[arg-type]
        actor_id=actor_id,
        scope=scope,
        **overrides,
    )
