"""Shared contracts for orchestrator-model tooling (LLM class, paths, exclusions)."""

from __future__ import annotations

import os
import sys
from enum import Enum
from pathlib import Path

NO_LLM_ENV = "ORCHESTRATOR_TOOLS_NO_LLM"


class LlmClass(str, Enum):
    NONE = "none"
    OPTIONAL = "optional"
    REQUIRED = "required"


GATE_GREEN = "GREEN"
GATE_RED = "RED"
GATE_UNKNOWN = "UNKNOWN"
GATE_SKIPPED = "SKIPPED"

ARTIFACT_EXCLUDE_PREFIXES = (
    "artifacts/",
    ".brainstorm/",
    ".cache/",
    ".model-review/",
    ".cursor/",
)

ARTIFACT_EXCLUDE_NAMES = (
    "commit-plan",
    "commit-slice-planning",
    "baseline-since-last-green",
)


def llm_denied() -> bool:
    return os.environ.get(NO_LLM_ENV, "").lower() in ("1", "true", "yes")


def print_llm_header(llm_class: LlmClass, detail: str = "") -> None:
    line = f"llm: {llm_class.value}"
    if detail:
        line += f" ({detail})"
    print(line, file=sys.stderr)


def deprecation(old: str, new: str) -> None:
    print(f"DEPRECATED: {old} → use `{new}` (removal after 2026-07-19)", file=sys.stderr)


def is_excluded_path(path: str) -> bool:
    p = path.replace("\\", "/")
    if any(p.startswith(prefix) for prefix in ARTIFACT_EXCLUDE_PREFIXES):
        return True
    parts = Path(p).parts
    return any(part in ARTIFACT_EXCLUDE_NAMES for part in parts)


def detect_default_gate(repo: Path) -> str:
    jf = repo / "justfile"
    if not jf.is_file():
        return "smoke"
    text = jf.read_text(errors="replace")
    for gate in ("canary", "health", "harness-eval", "smoke"):
        if f"{gate}:" in text:
            if gate == "harness-eval" and "canary:" in text:
                continue
            return gate
    return "smoke"


def repo_state_dir(repo: Path, tool: str) -> Path:
    return repo / "artifacts" / tool
