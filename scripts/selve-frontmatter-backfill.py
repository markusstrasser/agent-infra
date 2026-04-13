#!/usr/bin/env python3
"""Backfill YAML frontmatter on selve research memos that lack it.

Deterministic — infers title from H1, date from file content or mtime,
status from content keywords, tags from heading keywords.

Usage:
    uv run python3 scripts/selve-frontmatter-backfill.py [--dry-run] [--limit N]
"""

import argparse
import re
from datetime import datetime
from pathlib import Path

SELVE_ROOT = Path.home() / "Projects" / "phenome"
RESEARCH_DIR = SELVE_ROOT / "docs" / "research"


def has_frontmatter(text: str) -> bool:
    return text.startswith("---\n")


def infer_title(text: str, filename: str) -> str:
    """Infer title from first H1 heading or filename."""
    m = re.search(r"^#\s+(.+)", text, re.MULTILINE)
    if m:
        title = m.group(1).strip()
        # Clean markdown formatting
        title = re.sub(r"[*_`]", "", title)
        return title
    # Fallback: filename
    return filename.replace("_", " ").replace("-", " ").replace(".md", "").title()


def infer_date(text: str, path: Path) -> str:
    """Infer date from content or file mtime."""
    # Look for Date: or date: in first 20 lines
    for line in text.split("\n")[:20]:
        m = re.match(r">\s*Date:\s*(\d{4}-\d{2}-\d{2})", line)
        if m:
            return m.group(1)
        m = re.match(r"date:\s*(\d{4}-\d{2}-\d{2})", line, re.IGNORECASE)
        if m:
            return m.group(1)
    # Look for YYYY-MM-DD in filename
    m = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    if m:
        return m.group(1)
    # Fallback: file mtime
    mtime = path.stat().st_mtime
    return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")


def infer_status(text: str) -> str:
    """Infer status from content keywords."""
    lower = text.lower()
    if "retracted" in lower or "RETRACTION" in text:
        return "retracted"
    if "superseded" in lower:
        return "superseded"
    if "## Decision Claims" in text or "## Key Findings" in text:
        return "complete"
    if "draft" in lower[:200]:
        return "draft"
    return "complete"


def infer_tags(text: str) -> list[str]:
    """Infer tags from content headings and keywords."""
    tags = set()
    # Check for common topic keywords
    topic_keywords = {
        "genomics": ["variant", "gene", "ACMG", "VUS", "ClinVar", "gnomAD", "WGS"],
        "pharmacogenomics": ["CYP", "PharmCAT", "drug", "metabolizer", "PGx"],
        "prs": ["PRS", "polygenic", "percentile"],
        "supplement": ["supplement", "mg/day", "dosage"],
        "health": ["blood", "biomarker", "cortisol", "sleep", "diet"],
        "causal": ["causal", "mechanism", "pathway", "DAG"],
        "mental-health": ["psychiatric", "anxiety", "depression", "ADHD", "ACE"],
    }
    for tag, keywords in topic_keywords.items():
        if any(kw.lower() in text.lower() for kw in keywords):
            tags.add(tag)
    return sorted(tags)[:5]  # Cap at 5


def infer_summary(text: str) -> str:
    """Infer summary from first substantive paragraph or scope line."""
    # Look for Scope: line
    for line in text.split("\n")[:20]:
        m = re.match(r">\s*Scope:\s*(.+)", line)
        if m:
            return m.group(1).strip()
    # First paragraph after H1
    m = re.search(r"^#\s+.+\n\n(.+?)(?:\n\n|\n#)", text, re.MULTILINE | re.DOTALL)
    if m:
        para = m.group(1).strip().replace("\n", " ")
        if len(para) > 120:
            para = para[:117] + "..."
        return para
    return ""


def build_frontmatter(title: str, date: str, status: str,
                       tags: list[str], summary: str) -> str:
    """Build YAML frontmatter string."""
    lines = ["---"]
    lines.append(f"title: \"{title}\"")
    lines.append(f"date: {date}")
    lines.append(f"status: {status}")
    if tags:
        lines.append(f"tags: [{', '.join(tags)}]")
    if summary:
        lines.append(f"summary: \"{summary}\"")
    lines.append("---")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    if not RESEARCH_DIR.exists():
        print(f"Directory not found: {RESEARCH_DIR}")
        return

    files = sorted(RESEARCH_DIR.glob("*.md"))
    missing = []
    for f in files:
        if f.name.startswith("_") or f.name in ("README.md", "MEMO_CONTRACT.md"):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not has_frontmatter(text):
            missing.append(f)

    print(f"Files without frontmatter: {len(missing)} / {len(files)}")

    if args.limit:
        missing = missing[:args.limit]

    for f in missing:
        text = f.read_text(encoding="utf-8", errors="replace")
        title = infer_title(text, f.name)
        date = infer_date(text, f)
        status = infer_status(text)
        tags = infer_tags(text)
        summary = infer_summary(text)

        fm = build_frontmatter(title, date, status, tags, summary)

        if args.dry_run:
            print(f"\n  {f.name}:")
            print(f"    title: {title}")
            print(f"    date: {date}")
            print(f"    status: {status}")
            print(f"    tags: {tags}")
        else:
            new_text = fm + "\n\n" + text
            f.write_text(new_text, encoding="utf-8")
            print(f"  Added frontmatter: {f.name}")

    if not args.dry_run and missing:
        print(f"\nDone. Added frontmatter to {len(missing)} files.")
        print("Run: cd ~/Projects/phenome && git add -A && git commit -m '[docs] Backfill frontmatter on research memos'")


if __name__ == "__main__":
    main()
