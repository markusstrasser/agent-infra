"""Replay verifier: rebuild graph.duckdb from annotations.jsonl and check
bit-exact projection.

Single pass — Phase A is pure-append-only so "current state" is a view at
query time, not a materialized projection.

The verifier exists BEFORE Phase A's schema migration because it IS the
baseline: a record's annotation_id must be byte-stable across
rebuild-from-JSONL. If Phase A accidentally mutates a stable_tuple field,
this verifier catches it loudly.

Phase F of .claude/plans/2026-05-27-knowledge-infra-next-foundations.md.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from .canonical import parse_jsonl_strict
from .index import index_annotation
from .store import store_root


# Columns compared between current graph.duckdb and the replay rebuild.
# Excludes recorded_at — that's local wall-clock at INSERT, NOT event-source
# data. Replay generates a fresh recorded_at; bit-exact comparison would
# always fail. Also excludes any columns Phase A adds (valid_from) — those
# default deterministically from existing fields, so equal-input → equal-
# output, but we keep the comparison list authoritative here so Phase A's
# migration explicitly extends it.
DEFAULT_COMPARE_COLUMNS: tuple[str, ...] = (
    "annotation_id",
    "source_id",
    "scope",
    "repo",
    "actor_id",
    "actor_type",
    "output_uri",
    "output_hash",
    "prompt_template_hash",
    "asserted_at",
    "status",
    "supersedes_annotation_id",
)


@dataclass(frozen=True)
class ReplayDiff:
    """Result of comparing a replay rebuild against the live graph.duckdb."""
    matched: int = 0
    missing_in_replay: int = 0   # in live, absent from replay
    extra_in_replay: int = 0     # in replay, absent from live
    mismatched: int = 0          # same annotation_id, different non-PK columns

    def is_clean(self) -> bool:
        return (
            self.missing_in_replay == 0
            and self.extra_in_replay == 0
            and self.mismatched == 0
        )

    def as_dict(self) -> dict[str, int]:
        return {
            "matched": self.matched,
            "missing_in_replay": self.missing_in_replay,
            "extra_in_replay": self.extra_in_replay,
            "mismatched": self.mismatched,
        }


def _iter_source_dirs(root: Optional[Path] = None) -> Iterable[Path]:
    """Walk corpus root in NFC-normalized, sorted dir-name order.

    APFS readdir returns hash-order; raw filesystem iteration is
    non-deterministic across runs even on a single machine. Sorting
    by the NFC-normalized name produces a stable iteration order
    regardless of whether source dirs were created via NFC or NFD.
    """
    root = root or store_root()
    if not root.is_dir():
        return
    entries = []
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        if not (entry / "annotations.jsonl").exists():
            continue
        entries.append(entry)
    entries.sort(key=lambda p: unicodedata.normalize("NFC", p.name))
    for e in entries:
        yield e


def _iter_records(jsonl: Path, *, tolerant: bool = False) -> Iterable[dict]:
    """Yield JSONL records in append order.

    Default strict mode: duplicate keys raise (writer bug). Tolerant
    mode: malformed lines logged via print, then skipped.
    """
    with open(jsonl, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield parse_jsonl_strict(line)
            except (json.JSONDecodeError, ValueError) as exc:
                if tolerant:
                    print(f"  ! {jsonl}:{lineno}: {exc}; skipping")
                    continue
                raise


def replay_to_temp_graph(
    *,
    src_root: Optional[Path] = None,
    tolerant: bool = False,
) -> Path:
    """Rebuild a fresh graph.duckdb from every annotations.jsonl under
    ``src_root`` (default: store_root()). Returns the path to the new
    temp DB; caller is responsible for unlinking.

    The rebuild calls ``index_annotation`` per record so the projection
    logic is single-source.
    """
    src_root = src_root or store_root()
    tmpdir = Path(tempfile.mkdtemp(prefix="corpus-replay-"))
    target = tmpdir / "graph.duckdb"
    # Materialize the target DB even when there are zero records so
    # downstream RO connections don't fail with "database does not
    # exist". index._connect applies the canonical schema_sql.
    from .index import _connect
    _connect(target).close()
    for entry in _iter_source_dirs(src_root):
        jsonl = entry / "annotations.jsonl"
        for record in _iter_records(jsonl, tolerant=tolerant):
            index_annotation(record, graph_db_path=target)
    return target


def verify_replay_matches_current(
    *,
    src_root: Optional[Path] = None,
    live_db: Optional[Path] = None,
    columns_to_compare: tuple[str, ...] = DEFAULT_COMPARE_COLUMNS,
    tolerant: bool = False,
) -> ReplayDiff:
    """Replay and compare against the live graph.duckdb.

    Returns a ReplayDiff; the caller decides what to do with non-zero
    counts. A clean run is ``ReplayDiff.is_clean() is True``.
    """
    import duckdb

    src_root = src_root or store_root()
    live_db = live_db or (src_root / "graph.duckdb")
    replay_db = replay_to_temp_graph(src_root=src_root, tolerant=tolerant)

    cols = ", ".join(columns_to_compare)
    try:
        live = duckdb.connect(str(live_db), read_only=True)
    except duckdb.IOException as exc:
        shutil.rmtree(replay_db.parent, ignore_errors=True)
        raise RuntimeError(f"live graph DB at {live_db} unreadable: {exc}") from exc
    try:
        live_rows = {r[0]: r for r in live.execute(f"SELECT {cols} FROM annotations").fetchall()}
    finally:
        live.close()

    rep = duckdb.connect(str(replay_db), read_only=True)
    try:
        rep_rows = {r[0]: r for r in rep.execute(f"SELECT {cols} FROM annotations").fetchall()}
    finally:
        rep.close()
    shutil.rmtree(replay_db.parent, ignore_errors=True)

    matched = mismatched = 0
    for ann_id, live_row in live_rows.items():
        rep_row = rep_rows.get(ann_id)
        if rep_row is None:
            continue
        if rep_row == live_row:
            matched += 1
        else:
            mismatched += 1
    missing = sum(1 for k in live_rows if k not in rep_rows)
    extra = sum(1 for k in rep_rows if k not in live_rows)
    return ReplayDiff(
        matched=matched,
        missing_in_replay=missing,
        extra_in_replay=extra,
        mismatched=mismatched,
    )


def replay_in_place(*, confirm: bool = False, src_root: Optional[Path] = None) -> None:
    """DESTRUCTIVE: rebuild graph.duckdb in place from JSONL.

    Requires confirm=True — accidental replay can blow away rows added
    by parallel writers between SELECT and replay completion. Always
    run ``verify_replay_matches_current`` first; if it returns clean,
    in-place replay is safe.
    """
    if not confirm:
        raise ValueError(
            "replay_in_place requires confirm=True; "
            "run verify_replay_matches_current() first to confirm safety"
        )
    src_root = src_root or store_root()
    replay_db = replay_to_temp_graph(src_root=src_root)
    target = src_root / "graph.duckdb"
    if target.exists():
        target.unlink()
    shutil.move(str(replay_db), str(target))
    shutil.rmtree(replay_db.parent, ignore_errors=True)


__all__ = [
    "DEFAULT_COMPARE_COLUMNS",
    "ReplayDiff",
    "replay_in_place",
    "replay_to_temp_graph",
    "verify_replay_matches_current",
]
