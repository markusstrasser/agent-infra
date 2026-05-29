#!/usr/bin/env python3
"""Governance correction intake — UserPromptSubmit hook.

Captures explicit ground-truth governance corrections marked with the literal
tag `#f governance:` so they become first-class proposals in the governance
system instead of being lost as ad-hoc conversation.

Design constraints (deliberate, do not relax):
- Explicit tag ONLY. No semantic detection of "pushback"/"stance flips" — that
  is a known false-positive factory (depth-nudge classifier hit 67% FP).
- Writes to a QUARANTINE file, never to git, never to improvement-log directly.
- Fail open: any error → exit 0, never block the prompt. Exit 0 always.
- Safe with no tag present (the common case): exit 0 silently, write nothing.

Run as hook command:
    cd /Users/alien/Projects/agent-infra && uv run python3 scripts/gov_intake.py
"""

# Gov-ID: hook:gov_intake
# goal: capture #f governance corrections to quarantine
# verifier: null
# blast_radius: local

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Case-insensitive. Capture from the marker to END OF PROMPT (DOTALL) so a
# multi-line correction below the tag is not silently dropped, but STOP at a
# second `#f governance:` tag so two tags yield one clean capture each (we take
# the first). The quarantine is human-reviewed, so mild over-capture is safe;
# losing the body is not. Length-capped in _extract_correction.
_TAG_RE = re.compile(
    r"#f\s+governance:\s*(.+?)\s*(?=\n\s*#f\s+governance:|$)",
    re.IGNORECASE | re.DOTALL,
)
_MAX_CORRECTION_CHARS = 2000  # cap over-capture of a long trailing prompt


def _intake_dir() -> Path:
    return Path(os.path.expanduser("~/.claude/gov-intake"))


def _normalize(text: str) -> str:
    """Normalize for dedupe: collapse whitespace, lowercase, strip."""
    return re.sub(r"\s+", " ", text).strip().lower()


def _dedupe_hash(text: str) -> str:
    return hashlib.sha256(_normalize(text).encode("utf-8")).hexdigest()


def _extract_correction(prompt: str) -> str | None:
    """Return the first `#f governance:` span, or None. Max 1 per prompt."""
    if not prompt:
        return None
    m = _TAG_RE.search(prompt)
    if not m:
        return None
    correction = m.group(1).strip()[:_MAX_CORRECTION_CHARS].strip()
    return correction or None


def _existing_hashes(path: Path) -> set[str]:
    hashes: set[str] = set()
    if not path.exists():
        return hashes
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            h = rec.get("dedupe_hash")
            if isinstance(h, str):
                hashes.add(h)
    except Exception:
        pass
    return hashes


def capture(event: dict[str, Any]) -> dict[str, Any] | None:
    """Capture a tagged correction from a hook event. Returns the written
    record, or None if nothing was captured (no tag, or duplicate)."""
    prompt = event.get("prompt") or event.get("user_message") or ""
    correction = _extract_correction(prompt)
    if correction is None:
        return None

    session = str(event.get("session_id") or "unknown")
    project = str(event.get("cwd") or "")
    dedupe_hash = _dedupe_hash(correction)

    intake_dir = _intake_dir()
    intake_dir.mkdir(parents=True, exist_ok=True)
    target = intake_dir / f"{session}.jsonl"

    if dedupe_hash in _existing_hashes(target):
        return None

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "session": session,
        "project": project,
        "correction_text": correction,
        "dedupe_hash": dedupe_hash,
        "scope": "unknown",
        "generalization_risk": "unconfirmed",
        "requires_confirmation": True,
        "status": "pending",
    }
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def load_pending(session: str | None = None) -> list[dict]:
    """Read the quarantine queue for consumers (e.g. scripts/gov.py).

    Returns all pending records, optionally filtered to one session. Records
    with status != "pending" are excluded."""
    intake_dir = _intake_dir()
    if not intake_dir.exists():
        return []
    if session:
        files = [intake_dir / f"{session}.jsonl"]
    else:
        files = sorted(intake_dir.glob("*.jsonl"))
    out: list[dict] = []
    for path in files:
        if not path.exists():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("status", "pending") == "pending":
                out.append(rec)
    return out


def main() -> int:
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            return 0
        capture(event)
    except Exception:
        # Fail open: never block the prompt.
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
