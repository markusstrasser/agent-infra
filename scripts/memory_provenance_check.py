#!/usr/bin/env python3
"""Memory provenance drift check — read-only.

Scans MEMORY files under ~/.claude/projects/-Users-alien-Projects-agent-infra/memory/
and warns when:
  1. A file body or description CLAIMS a rule/hook (mentions "rule"/"hook" or references
     a .md under rules/ or a .py under hooks/) but has NO provenance.links_rule.
  2. provenance.links_rule is present but the referenced path does not exist on disk.
  3. provenance.lifecycle is present but not one of the three allowed values.

Always exits 0 (advisory only).

Usage:
  uv run python3 scripts/memory_provenance_check.py
  uv run python3 scripts/memory_provenance_check.py --json
"""

# Gov-ID: hook:memory-provenance-drift
# goal: warn when a MEMORY lesson claims a rule/hook but carries no auditable provenance link
# verifier: null
# blast_radius: local

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Allow CLAUDE_DIR override for tests
import os
_default_claude = Path.home() / ".claude"
CLAUDE_DIR = Path(os.environ.get("CLAUDE_DIR", str(_default_claude)))

MEMORY_DIR = CLAUDE_DIR / "projects" / "-Users-alien-Projects-agent-infra" / "memory"
REPO_ROOT = Path(__file__).parent.parent

ALLOWED_LIFECYCLE = {"active", "superseded", "invalidated"}

# Patterns that suggest the file is claiming a rule or hook
_CLAIM_PATTERNS = [
    re.compile(r'\brule\b', re.IGNORECASE),
    re.compile(r'\bhook\b', re.IGNORECASE),
    re.compile(r'rules/[\w.-]+\.md'),
    re.compile(r'hooks/[\w.-]+\.py'),
]


def _extract_frontmatter(text: str) -> tuple[dict, str]:
    """Return (parsed_yaml_dict, body_text). Skips non-YAML or missing frontmatter."""
    try:
        import yaml
    except ImportError:
        # yaml not available — return empty
        return {}, text

    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm_text = text[3:end].strip()
    body = text[end + 4:].strip()
    try:
        data = yaml.safe_load(fm_text) or {}
    except Exception:
        data = {}
    return data, body


def _claims_rule_or_hook(description: str, body: str) -> bool:
    """Return True if either the description or body references a rule/hook."""
    combined = f"{description}\n{body}"
    return any(p.search(combined) for p in _CLAIM_PATTERNS)


def _check_file(path: Path) -> list[dict]:
    """Return a list of warning dicts for this memory file. Empty = clean."""
    text = path.read_text(encoding="utf-8", errors="replace")
    fm, body = _extract_frontmatter(text)
    description = str(fm.get("description", ""))

    warnings: list[dict] = []

    provenance = fm.get("provenance", {}) or {}

    # Rule 1: claims rule/hook but missing links_rule
    if _claims_rule_or_hook(description, body) and not provenance.get("links_rule"):
        warnings.append({
            "file": str(path.name),
            "code": "MISSING_LINKS_RULE",
            "detail": "body or description mentions rule/hook but provenance.links_rule is absent",
        })

    # Rule 2: links_rule present but path not found on disk
    links_rule = provenance.get("links_rule")
    if links_rule:
        rule_path = REPO_ROOT / links_rule
        if not rule_path.exists():
            warnings.append({
                "file": str(path.name),
                "code": "DANGLING_LINKS_RULE",
                "detail": f"provenance.links_rule={links_rule!r} does not exist at {rule_path}",
            })

    # Rule 3: lifecycle present but not one of 3 allowed values
    lifecycle = provenance.get("lifecycle")
    if lifecycle is not None and lifecycle not in ALLOWED_LIFECYCLE:
        warnings.append({
            "file": str(path.name),
            "code": "INVALID_LIFECYCLE",
            "detail": f"lifecycle={lifecycle!r} not in {sorted(ALLOWED_LIFECYCLE)}",
        })

    return warnings


def run(memory_dir: Path, json_out: bool = False) -> int:
    """Scan all *.md files (skipping MEMORY.md). Return warning count."""
    if not memory_dir.exists():
        msg = {"error": f"memory dir not found: {memory_dir}"}
        if json_out:
            print(json.dumps(msg))
        else:
            print(f"  ! {msg['error']}")
        return 0

    files = sorted(p for p in memory_dir.glob("*.md") if p.name != "MEMORY.md")
    all_warnings: list[dict] = []

    for f in files:
        all_warnings.extend(_check_file(f))

    n_files = len(files)
    n_warn = len(all_warnings)

    if json_out:
        print(json.dumps({"files": n_files, "warnings": n_warn, "details": all_warnings}, indent=2))
    else:
        for w in all_warnings:
            print(f"  ! [{w['code']}] {w['file']}: {w['detail']}")
        print(f"\n  {'✓' if n_warn == 0 else '!'} {n_files} memory files, {n_warn} drift warnings")

    return n_warn


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--memory-dir", type=Path, default=MEMORY_DIR,
                        help="override memory directory (default: %(default)s)")
    args = parser.parse_args()

    run(args.memory_dir, json_out=args.json)
    sys.exit(0)  # always advisory


if __name__ == "__main__":
    main()
