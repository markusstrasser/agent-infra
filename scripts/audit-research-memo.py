#!/usr/bin/env python3
"""
Audit whether research memos follow the required output contract.

Checks for presence of required sections by Markdown headings (YAML frontmatter,
Decision Claims, Disconfirmation, Verification Log, Search Log). Intentionally
lightweight — checks structure, not scientific correctness.

Usage:
    uv run python3 scripts/audit-research-memo.py
    uv run python3 scripts/audit-research-memo.py --target ~/Projects/phenome/docs/research
    uv run python3 scripts/audit-research-memo.py --target ~/Projects/genomics/docs --fail
    uv run python3 scripts/audit-research-memo.py --required "Decision Claims,Search Log"

Source: selve/scripts/audit_research_memo_contract.py
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from config import PROJECT_ROOTS, RESEARCH_DIRS, PROSE_EXTENSIONS
from common import con


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


# ── File discovery ───────────────────────────────────────────

def find_research_files(root: Path) -> list[Path]:
    """Find prose files in research directories under a project root."""
    files = []
    for dir_name in RESEARCH_DIRS:
        search_dir = root / dir_name
        if search_dir.exists():
            for ext in PROSE_EXTENSIONS:
                files.extend(search_dir.rglob(f"*{ext}"))
    return sorted(set(files))


def collect_files(target: Path | None) -> list[Path]:
    """Collect files to scan based on CLI args."""
    if target:
        if target.is_file():
            return [target]
        return sorted(p for p in target.rglob("*.md") if p.is_file())

    # Default: scan all project roots
    files = []
    for name, root in PROJECT_ROOTS.items():
        if root.exists():
            files.extend(find_research_files(root))
    return sorted(set(files))


# ── Contract checking ────────────────────────────────────────

def normalize_heading(text: str) -> str:
    """Normalize heading text for comparison."""
    cleaned = text.lower()
    cleaned = cleaned.replace("\u2013", "-").replace("\u2014", "-")
    cleaned = re.sub(r"[^a-z0-9\s\-]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


@dataclass(frozen=True)
class ContractCheck:
    path: Path
    missing: list[str]
    present: list[str]


def check_file(path: Path, required: list[str]) -> ContractCheck:
    try:
        lines = path.read_text(errors="replace").splitlines()
    except Exception as e:
        return ContractCheck(path=path, missing=required, present=[f"ERROR: {type(e).__name__}: {e}"])

    headings: list[str] = []
    for line in lines:
        m = HEADING_RE.match(line)
        if not m:
            continue
        headings.append(normalize_heading(m.group(2)))

    present: list[str] = []
    missing: list[str] = []
    for req in required:
        req_norm = normalize_heading(req)
        if any(req_norm in h for h in headings):
            present.append(req)
        else:
            missing.append(req)
    return ContractCheck(path=path, missing=missing, present=present)


# ── Main ─────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit research memos for required contract sections"
    )
    parser.add_argument("--target", type=Path, help="Directory or file to scan (overrides default cross-project scan)")
    parser.add_argument(
        "--required",
        default="Decision Claims,Disconfirmation,Verification Log,Search Log",
        help="Comma-separated required sections (matched by heading substring)",
    )
    parser.add_argument(
        "--fail",
        action="store_true",
        help="Exit with code 1 if any file is missing required sections",
    )
    args = parser.parse_args()

    files = collect_files(args.target)
    if not files:
        con.fail("No files found to scan")
        return 1

    required = [s.strip() for s in args.required.split(",") if s.strip()]
    if not required:
        con.fail("--required produced empty set")
        return 2

    checks = [check_file(fp, required) for fp in files]
    missing_any = [c for c in checks if c.missing]
    ok_count = len(files) - len(missing_any)

    con.header("Research Memo Contract Audit")
    con.kv("Files scanned", str(len(files)))
    con.kv("Required sections", ", ".join(required))
    con.kv("Passing", f"{ok_count}/{len(files)}")

    if missing_any:
        print()
        rows = []
        for c in missing_any:
            rows.append([str(c.path.name)[:45], ", ".join(c.missing)])
        con.table(
            ["File", "Missing Sections"],
            rows,
            widths=[47, 60],
        )

    if not missing_any:
        con.ok(f"All {len(files)} files pass contract check")
    else:
        con.warn(f"{len(missing_any)} files missing required sections")

    if args.fail and missing_any:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
