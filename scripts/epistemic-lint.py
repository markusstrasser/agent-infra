#!/usr/bin/env python3
"""Epistemic Lint — static analysis for unsourced verifiable claims.

Scans research files for verifiable claims (dollar amounts, percentages,
dates, proper nouns + numbers) without nearby provenance tags.

Usage: uv run python3 scripts/epistemic-lint.py [--project intel|genomics|selve|meta|all] [--verbose]
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

METRICS_FILE = Path.home() / ".claude" / "epistemic-metrics.jsonl"

PROJECT_ROOTS = {
    "intel": Path.home() / "Projects" / "intel",
    "genomics": Path.home() / "Projects" / "genomics",
    "selve": Path.home() / "Projects" / "selve",
    "meta": Path.home() / "Projects" / "meta",
}

# Research paths to scan (relative to project root)
RESEARCH_DIRS = ["docs", "analysis", "research", "entities", "briefs"]

# File extensions to check
PROSE_EXTENSIONS = {".md", ".txt", ".rst"}

# Provenance tag pattern — any of these within PROXIMITY lines counts as sourced
TAG_PATTERN = re.compile(
    r"\[SOURCE:|\[DATABASE:|\[DATA\]|\[INFERENCE\]|\[SPEC\]|\[CALC\]"
    r"|\[QUOTE\]|\[TRAINING-DATA\]|\[PREPRINT\]|\[FRONTIER\]|\[UNVERIFIED\]"
    r"|\[[A-F][1-6]\]"
)

# Verifiable claim patterns
CLAIM_PATTERNS = [
    (re.compile(r"\$[\d,.]+\s*(billion|million|trillion|[BMK])\b", re.I), "dollar_amount"),
    (re.compile(r"\$[\d,.]+"), "dollar_figure"),
    (re.compile(r"\b\d{1,3}(\.\d+)?%"), "percentage"),
    (re.compile(r"\b(19|20)\d{2}-\d{2}-\d{2}\b"), "iso_date"),
    (re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}", re.I), "written_date"),
    (re.compile(r"\b(according to|per|cited by|reported by|found that|study by)\b", re.I), "attribution"),
    (re.compile(r"\b\d+\.\d+x\b"), "multiple"),  # 2.5x, 3.0x
]

PROXIMITY = 3  # Lines above/below to look for tags


def find_research_files(root: Path) -> list[Path]:
    """Find prose files in research directories."""
    files = []
    for dir_name in RESEARCH_DIRS:
        search_dir = root / dir_name
        if search_dir.exists():
            for ext in PROSE_EXTENSIONS:
                files.extend(search_dir.rglob(f"*{ext}"))
    return sorted(files)


def lint_file(path: Path) -> list[dict]:
    """Find unsourced verifiable claims in a file."""
    try:
        lines = path.read_text().splitlines()
    except (OSError, UnicodeDecodeError):
        return []

    findings = []

    for i, line in enumerate(lines):
        # Skip blank lines, headers, code blocks
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("```"):
            continue

        for pattern, claim_type in CLAIM_PATTERNS:
            matches = pattern.finditer(line)
            for match in matches:
                # Check proximity for provenance tags
                start = max(0, i - PROXIMITY)
                end = min(len(lines), i + PROXIMITY + 1)
                context = "\n".join(lines[start:end])

                if not TAG_PATTERN.search(context):
                    findings.append({
                        "line": i + 1,
                        "claim_type": claim_type,
                        "text": match.group()[:60],
                        "context": stripped[:100],
                    })
                    break  # One finding per line is enough

    return findings


def main():
    project_filter = "all"
    verbose = False

    args = sys.argv[1:]
    if "--project" in args:
        idx = args.index("--project")
        if idx + 1 < len(args):
            project_filter = args[idx + 1]
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

    all_findings: dict[str, list[dict]] = {}
    file_count = 0

    for proj_name, root in projects.items():
        if not root.exists():
            continue
        files = find_research_files(root)
        for path in files:
            file_count += 1
            findings = lint_file(path)
            if findings:
                rel = str(path.relative_to(root))
                key = f"{proj_name}/{rel}"
                all_findings[key] = findings

    total_claims = sum(len(f) for f in all_findings.values())
    files_with_issues = len(all_findings)

    # Print report
    print(f"{'=' * 55}")
    print(f"  Epistemic Lint")
    print(f"{'=' * 55}")
    print()
    print(f"  Files scanned:      {file_count}")
    print(f"  Files with issues:  {files_with_issues}")
    print(f"  Unsourced claims:   {total_claims}")
    if file_count > 0:
        print(f"  Issue rate:         {files_with_issues/file_count:.0%} of files")
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

    # Top files
    if all_findings:
        print("  Top files by unsourced claims:")
        ranked = sorted(all_findings.items(), key=lambda x: -len(x[1]))
        for path, findings in ranked[:10]:
            print(f"    {path:<45} {len(findings):>3}")
        print()

    if verbose and all_findings:
        print("  Details:")
        for path, findings in sorted(all_findings.items()):
            print(f"\n  {path}:")
            for f in findings[:5]:
                print(f"    L{f['line']:>4} [{f['claim_type']}] {f['text']}")
            if len(findings) > 5:
                print(f"    ... and {len(findings) - 5} more")
        print()

    # Log metrics
    metric = {
        "ts": datetime.now().isoformat(),
        "metric": "epistemic_lint",
        "project": project_filter,
        "files_scanned": file_count,
        "files_with_issues": files_with_issues,
        "unsourced_claims": total_claims,
        "issue_rate": round(files_with_issues / max(file_count, 1), 4),
        "by_type": type_counts,
    }
    with open(METRICS_FILE, "a") as f:
        f.write(json.dumps(metric) + "\n")
    print(f"  Logged to {METRICS_FILE}")


if __name__ == "__main__":
    main()
