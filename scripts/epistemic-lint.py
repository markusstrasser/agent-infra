#!/usr/bin/env python3
"""Epistemic Lint — static analysis for unsourced verifiable claims.

Scans research files for verifiable claims (dollar amounts, percentages,
dates, proper nouns + numbers) without nearby provenance tags.

Usage: uv run python3 scripts/epistemic-lint.py [--project intel|genomics|selve|meta|all] [--days N] [--verbose]
"""

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

from config import METRICS_FILE, PROJECT_ROOTS, RESEARCH_DIRS, PROSE_EXTENSIONS, log_metric

# Provenance tag pattern — any of these within PROXIMITY lines counts as sourced
TAG_PATTERN = re.compile(
    r"\[SOURCE:|\[DATABASE:|\[DATA\]|\[INFERENCE\]|\[SPEC\]|\[CALC\]"
    r"|\[QUOTE\]|\[TRAINING-DATA\]|\[PREPRINT\]|\[FRONTIER\]|\[UNVERIFIED\]"
    r"|\[[A-F][1-6]\]"
)

# Verifiable claim patterns with severity weights
# CRITICAL: high-impact claims that must have sources
# MEDIUM: important but less dangerous if wrong
# LOW: contextual, less likely to mislead
CLAIM_PATTERNS = [
    (re.compile(r"\$[\d,.]+\s*(billion|million|trillion|[BMK])\b", re.I), "dollar_amount", "CRITICAL"),
    (re.compile(r"\$[\d,.]+"), "dollar_figure", "CRITICAL"),
    (re.compile(r"\b\d{1,3}(\.\d+)?%"), "percentage", "MEDIUM"),
    (re.compile(r"\b(19|20)\d{2}-\d{2}-\d{2}\b"), "iso_date", "MEDIUM"),
    (re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}", re.I), "written_date", "LOW"),
    (re.compile(r"\b(according to|per|cited by|reported by|found that|study by)\b", re.I), "attribution", "CRITICAL"),
    (re.compile(r"\b\d+\.\d+x\b"), "multiple", "MEDIUM"),  # 2.5x, 3.0x
]

SEVERITY_WEIGHTS = {"CRITICAL": 3, "MEDIUM": 2, "LOW": 1}

PROXIMITY = 3  # Lines above/below to look for tags

# File-type strictness:
# research/ = strict (all claim types flagged)
# plans/, docs/ = lenient (only CRITICAL flagged)
# .model-review/ = lenient
STRICT_DIRS = {"research", "analysis", "briefs", "entities", "investments"}
LENIENT_DIRS = {"plans", ".claude", ".model-review"}


def find_research_files(root: Path) -> list[Path]:
    """Find prose files in research directories."""
    files = []
    for dir_name in RESEARCH_DIRS:
        search_dir = root / dir_name
        if search_dir.exists():
            for ext in PROSE_EXTENSIONS:
                files.extend(search_dir.rglob(f"*{ext}"))
    return sorted(files)


def get_file_strictness(path: Path) -> str:
    """Determine strictness level based on file location."""
    parts = set(path.parts)
    if parts & STRICT_DIRS:
        return "strict"
    if parts & LENIENT_DIRS:
        return "lenient"
    # Default: research-adjacent dirs get strict
    return "strict"


def proximity_score(lines: list[str], claim_line: int) -> float:
    """Compute proximity-weighted provenance score (0-1).

    1.0 = tag on same line, decays with distance.
    0.0 = no tag within PROXIMITY lines.
    """
    for dist in range(PROXIMITY + 1):
        for offset in (claim_line - dist, claim_line + dist):
            if 0 <= offset < len(lines):
                if TAG_PATTERN.search(lines[offset]):
                    return 1.0 - (dist / (PROXIMITY + 1))
    return 0.0


def lint_file(path: Path) -> list[dict]:
    """Find unsourced verifiable claims in a file."""
    try:
        lines = path.read_text().splitlines()
    except (OSError, UnicodeDecodeError):
        return []

    strictness = get_file_strictness(path)
    findings = []
    in_code_block = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Track code blocks
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        # Skip blank lines, headers, table separators
        if not stripped or stripped.startswith("#") or re.match(r"^\|[\s\-:]+\|", stripped):
            continue

        for pattern, claim_type, severity in CLAIM_PATTERNS:
            # In lenient mode, only flag CRITICAL claims
            if strictness == "lenient" and severity != "CRITICAL":
                continue

            matches = pattern.finditer(line)
            for match in matches:
                prox = proximity_score(lines, i)

                # If there's a nearby tag (score > 0), skip
                if prox > 0:
                    continue

                findings.append({
                    "line": i + 1,
                    "claim_type": claim_type,
                    "severity": severity,
                    "weight": SEVERITY_WEIGHTS[severity],
                    "text": match.group()[:60],
                    "context": stripped[:100],
                    "proximity_score": prox,
                })
                break  # One finding per line is enough

    return findings


def main():
    project_filter = "all"
    verbose = False
    days_filter = None

    args = sys.argv[1:]
    if "--project" in args:
        idx = args.index("--project")
        if idx + 1 < len(args):
            project_filter = args[idx + 1]
    if "--days" in args:
        idx = args.index("--days")
        if idx + 1 < len(args):
            days_filter = int(args[idx + 1])
    if "--verbose" in args:
        verbose = True

    projects = (
        PROJECT_ROOTS
        if project_filter == "all"
        else {project_filter: PROJECT_ROOTS[project_filter]}
        if project_filter in PROJECT_ROOTS
        else {}
    )

    if not projects:
        print(f"Unknown project: {project_filter}")
        print(f"Valid: {', '.join(PROJECT_ROOTS.keys())}, all")
        return

    cutoff = None
    if days_filter:
        cutoff = datetime.now() - timedelta(days=days_filter)

    all_findings: dict[str, list[dict]] = {}
    file_count = 0
    skipped_old = 0

    for proj_name, root in projects.items():
        if not root.exists():
            continue
        files = find_research_files(root)
        for path in files:
            # Filter by modification time if --days specified
            if cutoff:
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
                if mtime < cutoff:
                    skipped_old += 1
                    continue

            file_count += 1
            findings = lint_file(path)
            if findings:
                rel = str(path.relative_to(root))
                key = f"{proj_name}/{rel}"
                all_findings[key] = findings

    total_claims = sum(len(f) for f in all_findings.values())
    files_with_issues = len(all_findings)

    # Weighted score
    total_weight = sum(
        f["weight"] for findings in all_findings.values() for f in findings
    )
    critical_count = sum(
        1 for findings in all_findings.values()
        for f in findings if f["severity"] == "CRITICAL"
    )

    # Print report
    print(f"{'=' * 55}")
    header = "  Epistemic Lint"
    if days_filter:
        header += f" — files modified in last {days_filter} days"
    print(header)
    print(f"{'=' * 55}")
    print()
    print(f"  Files scanned:      {file_count}")
    if skipped_old:
        print(f"  Skipped (old):      {skipped_old}")
    print(f"  Files with issues:  {files_with_issues}")
    print(f"  Unsourced claims:   {total_claims}")
    print(f"  Weighted score:     {total_weight} (CRITICAL×3, MEDIUM×2, LOW×1)")
    print(f"  Critical claims:    {critical_count}")
    if file_count > 0:
        print(f"  Issue rate:         {files_with_issues/file_count:.0%} of files")
    print()

    # By severity
    sev_counts: dict[str, int] = {}
    for findings in all_findings.values():
        for f in findings:
            s = f["severity"]
            sev_counts[s] = sev_counts.get(s, 0) + 1
    if sev_counts:
        print("  By severity:")
        for s in ("CRITICAL", "MEDIUM", "LOW"):
            if s in sev_counts:
                print(f"    {s:<12} {sev_counts[s]:>4}  (×{SEVERITY_WEIGHTS[s]})")
        print()

    # By claim type
    type_counts: dict[str, int] = {}
    for findings in all_findings.values():
        for f in findings:
            ct = f["claim_type"]
            type_counts[ct] = type_counts.get(ct, 0) + 1

    if type_counts:
        print("  By claim type:")
        for ct, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            print(f"    {ct:<20} {count:>4}")
        print()

    # Top files (ranked by weighted score)
    if all_findings:
        print("  Top files by weighted score:")
        ranked = sorted(
            all_findings.items(),
            key=lambda x: -sum(f["weight"] for f in x[1]),
        )
        for path, findings in ranked[:10]:
            w = sum(f["weight"] for f in findings)
            crit = sum(1 for f in findings if f["severity"] == "CRITICAL")
            suffix = f"  ({crit} critical)" if crit else ""
            print(f"    {path:<45} {w:>3}w {len(findings):>3}c{suffix}")
        print()

    if verbose and all_findings:
        print("  Details:")
        for path, findings in sorted(all_findings.items()):
            print(f"\n  {path}:")
            for f in findings[:5]:
                print(f"    L{f['line']:>4} [{f['severity'][0]}:{f['claim_type']}] {f['text']}")
            if len(findings) > 5:
                print(f"    ... and {len(findings) - 5} more")
        print()

    # Log metrics
    log_metric(
        "epistemic_lint",
        project=project_filter,
        days_filter=days_filter,
        files_scanned=file_count,
        files_with_issues=files_with_issues,
        unsourced_claims=total_claims,
        weighted_score=total_weight,
        critical_claims=critical_count,
        issue_rate=round(files_with_issues / max(file_count, 1), 4),
        by_type=type_counts,
        by_severity=sev_counts,
    )
    print(f"  Logged to {METRICS_FILE}")


if __name__ == "__main__":
    main()
