"""Read-side helpers: source records, annotations.

Filesystem-walking implementations are sufficient for Phase 1 (corpus is small;
single user). Phase 2 introduces a `graph.duckdb` projection that supersedes
`by_repo` for reverse queries — but the JSONL files remain authoritative.
"""
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from .store import CorpusStore


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    store: CorpusStore
    metadata: dict[str, Any]
    annotations_path: Path

    @property
    def path(self) -> Path:
        return self.store.paper_path(self.source_id)

    def annotations(self) -> list[dict[str, Any]]:
        return _read_jsonl(self.annotations_path)


def lookup(store: CorpusStore, source_id: str) -> SourceRecord:
    """Read metadata.json + return a SourceRecord (annotations on demand).

    Raises FileNotFoundError if the source has no metadata.json.
    """
    p = store.paper_path(source_id)
    meta_path = p / "metadata.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"no metadata.json for {source_id} at {meta_path}")
    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    return SourceRecord(
        source_id=source_id,
        store=store,
        metadata=metadata,
        annotations_path=p / "annotations.jsonl",
    )


def annotations(store: CorpusStore, source_id: str) -> list[dict[str, Any]]:
    """Read all annotations for a source (preserving file order)."""
    return _read_jsonl(store.paper_path(source_id) / "annotations.jsonl")


def by_repo(
    store: CorpusStore, repo: str, *, since: datetime | None = None
) -> Iterator[dict[str, Any]]:
    """Walk every annotations.jsonl, yield records matching repo (+ optional since).

    Phase 1 scan; Phase 2 replaces with a graph.duckdb annotations table query.
    Use sparingly — O(N sources) on cold cache.
    """
    cutoff = since.isoformat() if since else None
    root = store.root
    if not root.is_dir():
        return
    for sid in store.iter_papers():
        path = root / sid / "annotations.jsonl"
        if not path.exists():
            continue
        for record in _read_jsonl_iter(path):
            agent = record.get("agent") or {}
            # Match by 'repo' field if present (annotation schema has no top-level repo,
            # but the stable_tuple includes it via idempotency_key — and the record
            # carries it implicitly through output_uri scheme prefix). For Phase 1 we
            # match on output_uri prefix `<repo>://` OR project-root://<repo>/.
            uri = record.get("output_uri") or ""
            in_repo = uri.startswith(f"{repo}://") or uri.startswith(f"project-root://{repo}/")
            if not in_repo:
                continue
            if cutoff and (record.get("recorded_at") or "") < cutoff:
                continue
            yield record


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return list(_read_jsonl_iter(path))


def _read_jsonl_iter(path: Path) -> Iterator[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                # Skip torn / partial lines silently — corpus rebuild will surface them.
                continue


__all__ = ["SourceRecord", "annotations", "by_repo", "lookup"]
