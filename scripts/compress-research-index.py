#!/usr/bin/env python3
"""Compress research-index.md from fat 3-col table to thin pipe-delimited.

Reads the current fat format:
  | `file.md` | Topic description... | Consult before X, Y |

Produces thin format (8-12 word merged trigger):
  file.md | merged trigger from topic + consult-before

Usage:
    uv run python3 scripts/compress-research-index.py             # dry-run meta
    uv run python3 scripts/compress-research-index.py --write      # overwrite meta
    uv run python3 scripts/compress-research-index.py --project ~/Projects/selve
    uv run python3 scripts/compress-research-index.py --project ~/Projects/genomics
"""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

# Words to drop from triggers (low-information)
STOP_WORDS = {
    "a", "an", "the", "and", "or", "for", "of", "in", "on", "to", "with",
    "is", "are", "was", "were", "be", "been", "being", "has", "have", "had",
    "do", "does", "did", "will", "would", "could", "should", "may", "might",
    "that", "this", "these", "those", "it", "its", "our", "their", "we",
    "not", "no", "but", "if", "when", "how", "what", "which", "who",
    "than", "from", "about", "into", "through", "during", "before", "after",
    "between", "under", "above", "more", "most", "other", "some", "such",
    "can", "vs", "use", "using", "used",
}


def estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


def extract_trigger(topic: str, consult: str, max_words: int = 12) -> str:
    """Merge topic + consult-before into a compact trigger phrase."""
    # Strip markdown bold markers and backticks
    combined = f"{topic} {consult}"
    combined = re.sub(r"\*\*[^*]+\*\*\.?\s*", "", combined)  # remove **Core memo.** etc
    combined = combined.replace("`", "").replace("—", ",").replace("–", ",")

    # Split into words, deduplicate, remove stop words
    words = re.findall(r"[A-Za-z0-9_./-]+", combined.lower())
    seen = set()
    unique = []
    for w in words:
        if w not in STOP_WORDS and w not in seen and len(w) > 1:
            seen.add(w)
            unique.append(w)

    # Take first max_words, rejoin
    trigger = ", ".join(unique[:max_words])
    return trigger


def parse_fat_index(text: str) -> tuple[str, str, list[tuple[str, str, str]]]:
    """Parse fat 3-col index. Returns (frontmatter, header_text, [(file, topic, consult)])."""
    lines = text.split("\n")

    # Extract frontmatter
    frontmatter = ""
    body_start = 0
    if lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                frontmatter = "\n".join(lines[: i + 1])
                body_start = i + 1
                break

    # Find header text (everything before the table)
    header_lines = []
    table_start = body_start
    for i, line in enumerate(lines[body_start:], body_start):
        if line.startswith("| File"):
            table_start = i
            break
        header_lines.append(line)
    header_text = "\n".join(header_lines).strip()

    # Parse table rows
    entries = []
    for line in lines[table_start:]:
        if not line.startswith("|") or line.startswith("| File") or line.startswith("|--"):
            continue
        parts = [p.strip() for p in line.split("|")[1:-1]]
        if len(parts) >= 3:
            filename = parts[0].strip("`").strip()
            topic = parts[1].strip()
            consult = parts[2].strip()
            entries.append((filename, topic, consult))
        elif len(parts) == 2:
            filename = parts[0].strip("`").strip()
            topic = parts[1].strip()
            entries.append((filename, topic, ""))

    return frontmatter, header_text, entries


def build_thin_index(frontmatter: str, entries: list[tuple[str, str, str]]) -> str:
    """Build thin pipe-delimited index."""
    lines = []
    if frontmatter:
        lines.append(frontmatter)
        lines.append("")

    lines.append("# Research Index")
    lines.append("")
    lines.append("Consult before acting on the topic. Agent: grep file names or scan triggers.")
    lines.append("")

    for filename, topic, consult in entries:
        trigger = extract_trigger(topic, consult)
        lines.append(f"{filename} | {trigger}")

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Compress research index to thin format")
    parser.add_argument("--project", default=".", help="Project root (default: cwd)")
    parser.add_argument("--write", action="store_true", help="Overwrite the index file")
    parser.add_argument("--file", help="Explicit path to index file")
    args = parser.parse_args()

    # Find the index file
    if args.file:
        index_path = Path(args.file)
    else:
        project = Path(args.project).resolve()
        candidates = [
            project / ".claude" / "rules" / "research-index.md",
            project / ".claude" / "rules" / "research-docs-index.md",
        ]
        index_path = next((c for c in candidates if c.exists()), None)
        if not index_path:
            print(f"No research index found in {project}")
            return

    text = index_path.read_text(encoding="utf-8")
    frontmatter, header_text, entries = parse_fat_index(text)

    old_tokens = estimate_tokens(text)
    thin = build_thin_index(frontmatter, entries)
    new_tokens = estimate_tokens(thin)

    print(f"File: {index_path}")
    print(f"Entries: {len(entries)}")
    print(f"Old: {old_tokens:,} tokens")
    print(f"New: {new_tokens:,} tokens")
    print(f"Saved: {old_tokens - new_tokens:,} tokens ({(1 - new_tokens/old_tokens)*100:.0f}%)")
    print()

    if not args.write:
        # Show first 10 entries as preview
        for line in thin.split("\n")[:20]:
            print(f"  {line}")
        print("  ...")
        print(f"\nDry run. Use --write to overwrite {index_path.name}")
    else:
        index_path.write_text(thin, encoding="utf-8")
        print(f"Written to {index_path}")


if __name__ == "__main__":
    main()
