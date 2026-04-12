#!/usr/bin/env python3
"""PostToolUse advisory for research paper quality cards.

Surfaces the persisted quality card after `mcp__research__fetch_paper` or
`mcp__research__get_paper` so the agent sees vetoes/flags immediately in the
next turn, even if it does not inspect the raw JSON carefully.
"""

from __future__ import annotations

import json
import sys
from typing import Any


def _load_event() -> dict[str, Any]:
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def _unwrap_response(tool_response: Any) -> dict[str, Any]:
    if isinstance(tool_response, dict):
        if isinstance(tool_response.get("result"), dict):
            return tool_response["result"]
        if isinstance(tool_response.get("structuredContent"), dict):
            wrapped = tool_response["structuredContent"]
            if isinstance(wrapped.get("result"), dict):
                return wrapped["result"]
            return wrapped
        if isinstance(tool_response.get("content"), list):
            for item in tool_response["content"]:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    try:
                        parsed = json.loads(item["text"])
                    except Exception:
                        continue
                    if isinstance(parsed, dict):
                        return parsed
        return tool_response
    if isinstance(tool_response, str):
        try:
            parsed = json.loads(tool_response)
        except Exception:
            return {}
        if isinstance(parsed, dict):
            return parsed
    return {}


def _render_quality_context(payload: dict[str, Any]) -> str | None:
    quality = payload.get("quality")
    if not isinstance(quality, dict):
        return None

    lines: list[str] = []
    title = payload.get("title") or payload.get("paper_id") or "paper"
    doi = payload.get("doi") or "unknown DOI"
    lines.append(f"Paper quality card for {title} ({doi}):")

    if quality.get("vetoed"):
        reasons = ", ".join(quality.get("veto_reasons") or []) or "unknown"
        lines.append(f"- Hard veto: {reasons}. Do not cite this as valid evidence without explicitly framing the veto.")
    else:
        reasons = ", ".join(quality.get("veto_reasons") or [])
        if reasons:
            lines.append(f"- Informational flags: {reasons}. Surface them when citing.")

    lines.append(
        "- Components: "
        f"design={quality.get('study_design', 'unknown')}, "
        f"n={quality.get('sample_size', 'unknown')}, "
        f"organism={quality.get('organism', 'unknown')}, "
        f"blinding={quality.get('blinding', 'unclear')}, "
        f"control={quality.get('control_type', 'unclear')}, "
        f"funding={quality.get('funding_source', quality.get('funding', 'unknown'))}"
    )

    if quality.get("retracted"):
        lines.append(f"- Retraction detail: {quality.get('retraction_detail', 'retracted')}")
    if quality.get("is_candidate_gene"):
        lines.append("- Candidate-gene risk detected. Treat single-gene association claims as presumptively non-replicating unless clearly PGx/mechanistic.")
    if quality.get("quality_status") == "unassessed":
        lines.append("- Quality status is unassessed.")

    lines.append("- If you write literature-direction or consensus claims from this paper, run `mcp__scite__search_literature` and append stance counts.")
    lines.append("- Before citing, prefer `mcp__research__get_paper` to inspect the persisted full card if the current output is truncated.")
    return "\n".join(lines)


def main() -> int:
    event = _load_event()
    tool_name = event.get("tool_name", "")
    if tool_name not in {"mcp__research__fetch_paper", "mcp__research__get_paper"}:
        return 0

    payload = _unwrap_response(event.get("tool_response"))
    context = _render_quality_context(payload)
    if not context:
        return 0

    print(json.dumps({"additionalContext": context}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
