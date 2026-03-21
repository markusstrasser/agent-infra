#!/usr/bin/env python3
"""Knowledge balance check — audit trail balance validator.

Like an accounting trial balance: every claim should have evidence,
every cross-reference should resolve, every hash should be current.

Usage:
    uv run python3 scripts/knowledge-balance-check.py [--project PROJECT] [--verbose]
"""

import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from config import (
    KNOWLEDGE_ELIGIBLE_PATTERNS,
    METRICS_FILE,
    PROJECT_ROOTS,
    extract_frontmatter,
    log_metric,
)

KI_START = "<!-- knowledge-index"
KI_END = "end-knowledge-index -->"


def content_hash(text: str) -> str:
    """SHA256 of content excluding knowledge-index block."""
    cleaned = re.sub(
        rf"{re.escape(KI_START)}.*?{re.escape(KI_END)}", "", text, flags=re.DOTALL
    )
    return hashlib.sha256(cleaned.encode()).hexdigest()[:12]


def find_eligible_files(project: str) -> list[Path]:
    """Find knowledge-eligible files for a project."""
    root = PROJECT_ROOTS.get(project)
    if not root or not root.exists():
        return []
    patterns = KNOWLEDGE_ELIGIBLE_PATTERNS.get(project, [])
    files = []
    for pattern in patterns:
        files.extend(root.glob(pattern))
    return sorted(files)


def check_file(path: Path, verbose: bool = False) -> list[dict]:
    """Run balance checks on a single file. Returns list of issues."""
    issues = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        issues.append({"severity": "error", "check": "readable", "msg": f"Cannot read {path}"})
        return issues

    # Check 1: frontmatter exists
    fm = extract_frontmatter(path)
    if not fm:
        issues.append({
            "severity": "warning",
            "check": "frontmatter_missing",
            "msg": f"No YAML frontmatter",
        })

    # Check 2: knowledge-index exists
    has_ki = KI_START in text
    if not has_ki:
        issues.append({
            "severity": "info",
            "check": "index_missing",
            "msg": f"No knowledge-index block",
        })
    else:
        # Check 3: hash freshness
        ki_match = re.search(rf"{re.escape(KI_START)}(.*?){re.escape(KI_END)}", text, re.DOTALL)
        if ki_match:
            hash_match = re.search(r"hash:\s*(\S+)", ki_match.group(1))
            if hash_match:
                expected = content_hash(text)
                if hash_match.group(1) != expected:
                    issues.append({
                        "severity": "warning",
                        "check": "hash_stale",
                        "msg": f"Knowledge index hash stale (got {hash_match.group(1)}, expected {expected})",
                    })

    # Check 4: cross-references resolve
    crossref_re = re.compile(r"(?:docs/|research/|entities/|analysis/|decisions/)\S+\.md")
    project_root = path
    # Walk up to find project root (has .git or CLAUDE.md)
    while project_root.parent != project_root:
        project_root = project_root.parent
        if (project_root / ".git").exists() or (project_root / "CLAUDE.md").exists():
            break

    for m in crossref_re.finditer(text):
        ref = m.group(0)
        ref_path = project_root / ref
        if not ref_path.exists():
            issues.append({
                "severity": "error",
                "check": "broken_crossref",
                "msg": f"Cross-ref not found: {ref}",
            })

    # Check 5: correction without propagation (if knowledge-index has @correction)
    if has_ki and ki_match:
        corrections = re.findall(r"@correction\s*\|(.+)", ki_match.group(1))
        if corrections:
            # This file has corrections — good that they're tracked
            if verbose:
                for c in corrections:
                    issues.append({
                        "severity": "info",
                        "check": "correction_tracked",
                        "msg": f"Correction: {c.strip()[:80]}",
                    })

    # Check 6: draft status exemption
    if fm and fm.get("status", "").lower() == "draft":
        # Filter out warnings for draft docs
        issues = [i for i in issues if i["severity"] == "error"]

    return issues


def main():
    project_filter = None
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    if "--project" in sys.argv:
        idx = sys.argv.index("--project")
        if idx + 1 < len(sys.argv):
            project_filter = sys.argv[idx + 1]

    projects = [project_filter] if project_filter else list(KNOWLEDGE_ELIGIBLE_PATTERNS.keys())

    totals = defaultdict(int)
    all_issues = []

    print(f"{'=' * 55}")
    print("  Knowledge Balance Check")
    print(f"{'=' * 55}")
    print()

    for project in projects:
        if project not in PROJECT_ROOTS:
            continue
        files = find_eligible_files(project)
        if not files:
            continue

        project_issues = []
        for f in files:
            file_issues = check_file(f, verbose)
            for issue in file_issues:
                issue["file"] = str(f.relative_to(PROJECT_ROOTS[project]))
                issue["project"] = project
            project_issues.extend(file_issues)

        totals["files"] += len(files)
        errors = [i for i in project_issues if i["severity"] == "error"]
        warnings = [i for i in project_issues if i["severity"] == "warning"]
        infos = [i for i in project_issues if i["severity"] == "info"]

        totals["errors"] += len(errors)
        totals["warnings"] += len(warnings)

        has_fm = sum(1 for f in files if extract_frontmatter(f) is not None)
        has_ki = sum(1 for f in files if KI_START in f.read_text(errors="replace"))

        print(f"  {project}:")
        print(f"    Files:        {len(files)}")
        print(f"    Frontmatter:  {has_fm}/{len(files)} ({has_fm/len(files):.0%})")
        print(f"    K-Index:      {has_ki}/{len(files)} ({has_ki/len(files):.0%})")
        if errors:
            print(f"    Errors:       {len(errors)}")
        if warnings:
            print(f"    Warnings:     {len(warnings)}")
        print()

        if verbose:
            for issue in project_issues:
                sev = issue["severity"].upper()
                print(f"    [{sev}] {issue['file']}: {issue['msg']}")
            if project_issues:
                print()

        all_issues.extend(project_issues)

    # Summary
    print(f"  Total: {totals['files']} files, {totals['errors']} errors, {totals['warnings']} warnings")
    print()

    # Log metric
    log_metric(
        "knowledge_balance_check",
        files=totals["files"],
        errors=totals["errors"],
        warnings=totals["warnings"],
        issues_by_check={
            check: sum(1 for i in all_issues if i["check"] == check)
            for check in set(i["check"] for i in all_issues)
        },
    )

    # Exit code: 1 if errors, 0 otherwise
    sys.exit(1 if totals["errors"] > 0 else 0)


if __name__ == "__main__":
    main()
