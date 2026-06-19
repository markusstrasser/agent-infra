"""Parse debug scout FINDING blocks (shared by consolidation tools)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

FIELD_RE = re.compile(r"^- \*\*(?P<key>[^:]+):\*\* (?P<val>.*)\s*$")
JSON_FENCE = re.compile(r"```json\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def sev_rank(s: str) -> int:
    return {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(str(s).upper(), 9)


def parse_finding_block(block_id: str, lines: list[str], source: str) -> tuple[dict | None, str | None]:
    fields: dict[str, str] = {"id": block_id.strip(), "source": source}
    current_key: str | None = None
    for line in lines:
        if line.startswith("## "):
            break
        m = FIELD_RE.match(line)
        if m:
            current_key = m.group("key").strip().lower()
            fields[current_key] = m.group("val").strip()
        elif current_key and line.strip():
            fields[current_key] = fields.get(current_key, "") + " " + line.strip()
    if "claim" not in fields:
        return None, block_id
    fields["dedupe"] = hashlib.sha256(fields["claim"].lower().encode()).hexdigest()[:12]
    return fields, None


def parse_json_findings(text: str, source: str) -> list[dict]:
    out: list[dict] = []
    for m in JSON_FENCE.finditer(text):
        try:
            payload = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        items = payload if isinstance(payload, list) else payload.get("findings", [])
        for i, raw in enumerate(items):
            if not isinstance(raw, dict) or "claim" not in raw:
                continue
            item = dict(raw)
            item.setdefault("id", item.get("id", f"json-{i}"))
            item["source"] = source
            item["dedupe"] = hashlib.sha256(str(item["claim"]).lower().encode()).hexdigest()[:12]
            out.append(item)
    return out


def parse_findings(text: str, source: Path) -> tuple[list[dict], list[str]]:
    out: list[dict] = []
    skipped: list[str] = []
    out.extend(parse_json_findings(text, source.name))
    chunks = re.split(r"(?m)^## FINDING ", text)
    for chunk in chunks[1:]:
        lines = chunk.splitlines()
        if not lines:
            continue
        item, skip_id = parse_finding_block(lines[0], lines[1:], source.name)
        if item:
            out.append(item)
        elif skip_id:
            skipped.append(skip_id)
    return out, skipped
