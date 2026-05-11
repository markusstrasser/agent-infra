"""Sample annotation factories for tests."""
from __future__ import annotations

from typing import Any

from corpus_core.annotate import annotate


def make_annotation(
    source_id: str = "doi_10_1234_test",
    *,
    repo: str = "agent-infra",
    actor_type: str = "service",
    actor_id: str = "urn:agent:service:test@0.0.1",
    scope: str = "test",
    **overrides: Any,
) -> str:
    """Convenience: write a minimal valid annotation, return its id.

    Honors CORPUS_ROOT (set the corpus_root fixture first). Overrides pass
    through to corpus_core.annotate.annotate().
    """
    # source dir must exist for annotate() to write annotations.jsonl
    from corpus_core.store import paper_path
    paper_path(source_id).mkdir(parents=True, exist_ok=True)
    return annotate(
        source_id,
        repo=repo,  # type: ignore[arg-type]
        actor_type=actor_type,  # type: ignore[arg-type]
        actor_id=actor_id,
        scope=scope,
        **overrides,
    )
