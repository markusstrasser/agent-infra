#!/usr/bin/env python3
"""Shared parallel fan-out + JSONL manifest for scout launchers."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, TypeVar

T = TypeVar("T")
R = TypeVar("R")


@dataclass
class ScoutResult:
    scout_id: str
    ok: bool
    artifact: str
    kind: str = "debug"
    message: str = ""
    meta: dict = field(default_factory=dict)


def run_parallel(
    items: list[T],
    fn: Callable[[T], R],
    *,
    workers: int = 3,
) -> list[R]:
    if not items:
        return []
    workers = max(1, min(workers, len(items)))
    out: list[R] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(fn, item): item for item in items}
        for fut in as_completed(futs):
            try:
                out.append(fut.result())
            except Exception as exc:
                item = futs[fut]
                label = item if isinstance(item, str) else getattr(item, "scout_id", "?")
                out.append(ScoutResult(str(label), False, "", message=f"job failed: {exc}"))  # type: ignore[misc]
    return out


def write_manifest(path: Path, *, run_id: str, repo: Path, kind: str, results: list[ScoutResult]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id,
        "repo": str(repo),
        "kind": kind,
        "ts": datetime.now(timezone.utc).isoformat(),
        "ok": sum(1 for r in results if r.ok),
        "total": len(results),
        "scouts": [asdict(r) for r in results],
    }
    with path.open("w") as fh:
        fh.write(json.dumps(payload) + "\n")
        for r in results:
            fh.write(json.dumps(asdict(r)) + "\n")
    return path


def read_manifest(path: Path) -> tuple[dict, list[ScoutResult]]:
    lines = [ln for ln in path.read_text(errors="replace").splitlines() if ln.strip()]
    if not lines:
        return {}, []
    header = json.loads(lines[0])
    scouts: list[ScoutResult] = []
    for ln in lines[1:]:
        d = json.loads(ln)
        scouts.append(ScoutResult(**d))
    return header, scouts
