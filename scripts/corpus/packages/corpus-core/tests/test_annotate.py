"""Annotation writer: schema validation, idempotency, atomic concurrent append, supersedes."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from corpus_core.annotate import (
    ANNOTATION_RECORD_CEILING_BYTES,
    AnnotationError,
    AnnotationSchemaError,
    AnnotationTooLargeError,
    annotate,
)
from corpus_core.store import paper_path


SOURCE_ID = "doi_10_1234_test"
ACTOR_ID = "urn:agent:service:test@0.0.1"


@pytest.fixture
def corpus_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "corpus"
    root.mkdir()
    monkeypatch.setenv("CORPUS_ROOT", str(root))
    # Ensure the source dir exists for annotate() to write into
    (root / SOURCE_ID).mkdir()
    return root


def _read_lines(corpus_root: Path) -> list[dict]:
    path = corpus_root / SOURCE_ID / "annotations.jsonl"
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]


# --- happy path + record shape ---


def test_writes_one_record(corpus_root):
    aid = annotate(
        SOURCE_ID, repo="agent-infra", actor_type="service", actor_id=ACTOR_ID,
        scope="raw_fetch",
    )
    assert aid.startswith("ann_")
    rows = _read_lines(corpus_root)
    assert len(rows) == 1
    r = rows[0]
    assert r["annotation_id"] == aid
    assert r["source_id"] == SOURCE_ID
    assert r["agent"]["id"] == ACTOR_ID
    assert r["agent"]["type"] == "service"
    assert r["scope"] == "raw_fetch"
    assert r["status"] == "active"
    assert r["schema_version"] == "1-0-0"
    assert r["conformsTo"] == "https://schema.local/corpus/annotation/v1.0.0"


# --- idempotency ---


def test_idempotent_same_tuple(corpus_root):
    a1 = annotate(
        SOURCE_ID, repo="agent-infra", actor_type="service", actor_id=ACTOR_ID,
        scope="raw_fetch",
    )
    a2 = annotate(
        SOURCE_ID, repo="agent-infra", actor_type="service", actor_id=ACTOR_ID,
        scope="raw_fetch",
    )
    assert a1 == a2
    rows = _read_lines(corpus_root)
    assert len(rows) == 1


def test_different_scope_different_id(corpus_root):
    a1 = annotate(
        SOURCE_ID, repo="agent-infra", actor_type="service", actor_id=ACTOR_ID,
        scope="raw_fetch",
    )
    a2 = annotate(
        SOURCE_ID, repo="agent-infra", actor_type="service", actor_id=ACTOR_ID,
        scope="parse",
    )
    assert a1 != a2
    rows = _read_lines(corpus_root)
    assert len(rows) == 2
    assert {r["annotation_id"] for r in rows} == {a1, a2}


# --- schema validation ---


def test_unknown_repo_rejected(corpus_root):
    with pytest.raises(AnnotationError, match="unknown repo"):
        annotate(
            SOURCE_ID, repo="bogus", actor_type="service", actor_id=ACTOR_ID,
            scope="x",
        )


def test_unknown_actor_type_rejected(corpus_root):
    with pytest.raises(AnnotationError, match="unknown actor_type"):
        annotate(
            SOURCE_ID, repo="agent-infra", actor_type="alien", actor_id=ACTOR_ID,
            scope="x",
        )


def test_actor_id_must_be_urn(corpus_root):
    with pytest.raises(AnnotationError, match="urn:agent"):
        annotate(
            SOURCE_ID, repo="agent-infra", actor_type="service",
            actor_id="markus", scope="x",
        )


def test_invalid_output_uri_scheme_caught_by_schema(corpus_root):
    with pytest.raises(AnnotationSchemaError):
        annotate(
            SOURCE_ID, repo="agent-infra", actor_type="service", actor_id=ACTOR_ID,
            scope="x", output_uri="https://example.com/bogus", output_hash="a" * 16,
        )


# --- record ceiling (16KB; raised from 4KB for inline claim_relations) ---


def test_record_ceiling_enforced(corpus_root):
    # scope long enough to push the serialized record past the 16KB ceiling
    # (scope appears in both the top-level field and the idempotency_key → ~2x)
    huge_scope = "x" * 20000
    with pytest.raises(AnnotationTooLargeError):
        annotate(
            SOURCE_ID, repo="agent-infra", actor_type="service", actor_id=ACTOR_ID,
            scope=huge_scope,
        )


def test_just_under_ceiling_succeeds(corpus_root):
    # Tuned so the full record stays under 4096 bytes after JSON framing.
    # Each scope char becomes ~2 bytes in the serialized record (it appears in
    # both the top-level scope field AND the embedded idempotency_key).
    scope = "x" * 1700
    aid = annotate(
        SOURCE_ID, repo="agent-infra", actor_type="service", actor_id=ACTOR_ID,
        scope=scope,
    )
    rows = _read_lines(corpus_root)
    assert len(rows) == 1
    # Serialized line length ≤ ceiling
    line_len = (corpus_root / SOURCE_ID / "annotations.jsonl").stat().st_size
    assert line_len <= ANNOTATION_RECORD_CEILING_BYTES


# --- supersedes chain ---


def test_supersedes_link_recorded(corpus_root):
    a1 = annotate(
        SOURCE_ID, repo="agent-infra", actor_type="service", actor_id=ACTOR_ID,
        scope="verdict",
    )
    a2 = annotate(
        SOURCE_ID, repo="agent-infra", actor_type="model",
        actor_id="urn:agent:model:claude-opus-4-7@2026-04-16",
        scope="verdict",
        supersedes_annotation_id=a1,
        status="active",
    )
    rows = _read_lines(corpus_root)
    second = next(r for r in rows if r["annotation_id"] == a2)
    assert second["supersedes_annotation_id"] == a1
    assert second["status"] == "active"


# --- lifecycle-aware idempotency: a same-content correction must not be swallowed ---


def test_same_content_retraction_not_silently_dropped(corpus_root):
    """A correction reusing the same content tuple but flipping status must NOT
    be swallowed as an idempotent no-op — that would erase the correction from
    the append-only trail. status is excluded from annotation_id, so pre-guard
    this returned the original id with no write and no error (silent swallow).
    Red-handed: raises only with the lifecycle guard in place.
    """
    a1 = annotate(
        SOURCE_ID, repo="agent-infra", actor_type="service", actor_id=ACTOR_ID,
        scope="verdict",
    )
    # Same actor/scope/repo/output → same stable_tuple → same annotation_id;
    # only status differs. Must fail loud, not silently drop.
    with pytest.raises(AnnotationError, match="status"):
        annotate(
            SOURCE_ID, repo="agent-infra", actor_type="service", actor_id=ACTOR_ID,
            scope="verdict", status="retracted",
        )
    rows = _read_lines(corpus_root)
    assert len(rows) == 1
    assert rows[0]["annotation_id"] == a1
    assert rows[0]["status"] == "active"


def test_source_content_hash_change_not_dropped(corpus_root):
    """Re-attesting the same verdict (same output) against a re-parsed source
    (new source_content_hash) is a correction, not a no-op — must raise."""
    annotate(
        SOURCE_ID, repo="agent-infra", actor_type="service", actor_id=ACTOR_ID,
        scope="verdict", source_content_hash="a" * 64,
    )
    with pytest.raises(AnnotationError, match="source_content_hash"):
        annotate(
            SOURCE_ID, repo="agent-infra", actor_type="service", actor_id=ACTOR_ID,
            scope="verdict", source_content_hash="b" * 64,
        )


def test_identical_lifecycle_still_idempotent(corpus_root):
    """Regression guard: a true re-append (content AND lifecycle identical) stays
    a silent no-op — the guard must not break legitimate idempotency."""
    a1 = annotate(
        SOURCE_ID, repo="agent-infra", actor_type="service", actor_id=ACTOR_ID,
        scope="verdict", status="active", source_content_hash="c" * 64,
    )
    a2 = annotate(
        SOURCE_ID, repo="agent-infra", actor_type="service", actor_id=ACTOR_ID,
        scope="verdict", status="active", source_content_hash="c" * 64,
    )
    assert a1 == a2
    assert len(_read_lines(corpus_root)) == 1


# --- atomic concurrent append (50 writers, no torn lines, no duplicates beyond idempotency) ---


def test_atomic_concurrent_append(corpus_root, tmp_path):
    """50 subprocesses each write a UNIQUE annotation; expect 50 distinct ids
    on 50 valid JSONL lines.
    """
    script = tmp_path / "writer.py"
    script.write_text(
        "import os, sys\n"
        "os.environ['CORPUS_ROOT'] = sys.argv[1]\n"
        "from corpus_core.annotate import annotate\n"
        "from corpus_core.store import paper_path\n"
        "paper_path(sys.argv[2]).mkdir(parents=True, exist_ok=True)\n"
        "print(annotate(sys.argv[2], repo='agent-infra', actor_type='service',\n"
        "               actor_id='urn:agent:service:writer-' + sys.argv[3],\n"
        "               scope='concurrent_test'))\n"
    )
    procs = []
    for i in range(50):
        p = subprocess.Popen(
            [sys.executable, str(script), str(corpus_root), SOURCE_ID, str(i)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        procs.append(p)
    ids = []
    for p in procs:
        out, err = p.communicate(timeout=30)
        assert p.returncode == 0, f"writer failed: {err}"
        ids.append(out.strip())

    rows = _read_lines(corpus_root)
    # 50 distinct stable tuples → 50 distinct annotation_ids → 50 lines
    assert len({r["annotation_id"] for r in rows}) == 50
    assert len(ids) == 50
    assert set(ids) == {r["annotation_id"] for r in rows}
    # No torn lines: every line parsed as valid JSON
    raw = (corpus_root / SOURCE_ID / "annotations.jsonl").read_text()
    for line in raw.splitlines():
        if line.strip():
            json.loads(line)
