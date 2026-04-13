#!/usr/bin/env python3
"""PostToolUse hook: extract knowledge index from written/edited files.

Fires on Write|Edit for knowledge-eligible files. Deterministic extraction only
(regex — no LLM). Appends/updates <!-- knowledge-index --> block in the file.

High-precision extractions only (amendment A3):
- YAML frontmatter fields
- Source tags [GRADE: source]
- Cross-references to other docs
- Decision Claims table rows
- Correction blockquotes

Does NOT extract: entities via regex (precision untested), prose claims (requires LLM),
dependencies (requires semantic understanding).

EOF-safe injection (amendment A8): inserts before trailing footnotes/reference links.

Usage as hook:
  PostToolUse on Write|Edit, type: command, command: "python3 /path/to/this.py"
"""

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Knowledge-eligible directory patterns
ELIGIBLE_DIRS = {
    "analysis/entities",    # intel
    "docs/research",        # selve
    "docs/entities",        # selve
    "research",             # meta
    # decisions/ excluded — document choices, not claims; no source tags expected
}

# Source tag pattern: [GRADE: source] or [DATA: source] etc.
SOURCE_TAG_RE = re.compile(
    r"\[([A-F][1-6]|DATA|CALC|INFERENCE|TRAINING-DATA|ESTIMATED|PROVISIONAL)"
    r":?\s*(.*?)\]"
)

# Cross-reference pattern: relative paths to .md files
CROSSREF_RE = re.compile(
    r"(?:docs/|research/|entities/|analysis/|decisions/)\S+\.md"
)

# Correction blockquote pattern
CORRECTION_RE = re.compile(
    r"^>\s*\*\*(?:CORRECTION|RETRACTION|REVISED|UPDATE)\b(.*?)(?=\n[^>]|\Z)",
    re.MULTILINE | re.DOTALL,
)

# Knowledge index block delimiters
KI_START = "<!-- knowledge-index"
KI_END = "end-knowledge-index -->"

# Trailing markdown patterns (insert index BEFORE these)
TRAILING_RE = re.compile(
    r"\n(\[\^[^\]]+\]:|\[[^\]]+\]:\s*https?://)",
)


def is_eligible(file_path: str) -> bool:
    """Check if file path is in a knowledge-eligible directory."""
    if not file_path.endswith(".md"):
        return False
    for d in ELIGIBLE_DIRS:
        if f"/{d}/" in file_path or file_path.startswith(d + "/"):
            return True
    return False


def content_hash(text: str) -> str:
    """SHA256 of file content EXCLUDING knowledge-index block (amendment A4)."""
    # Remove existing knowledge-index block before hashing
    cleaned = re.sub(
        rf"{re.escape(KI_START)}.*?{re.escape(KI_END)}",
        "",
        text,
        flags=re.DOTALL,
    )
    return hashlib.sha256(cleaned.encode()).hexdigest()[:12]


def extract_frontmatter_fields(text: str) -> dict:
    """Extract key fields from YAML frontmatter."""
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    fields = {}
    for line in m.group(1).split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key in ("title", "ticker", "name", "status", "conviction",
                       "date", "last_reviewed", "summary"):
                fields[key] = val
            elif key == "tags":
                # Handle both list and comma-separated
                val = val.strip("[]")
                fields["tags"] = [t.strip() for t in val.split(",") if t.strip()]
    return fields


def extract_source_tags(text: str) -> list[str]:
    """Extract [GRADE: source] tags from prose."""
    tags = []
    for m in SOURCE_TAG_RE.finditer(text):
        grade, source = m.group(1), m.group(2).strip()
        if source:
            tags.append(f"{grade}: {source}")
    return tags


def extract_crossrefs(text: str) -> list[str]:
    """Extract cross-references to other markdown files."""
    refs = set()
    for m in CROSSREF_RE.finditer(text):
        ref = m.group(0)
        # Skip references inside the knowledge-index block itself
        if "@" not in ref:
            refs.add(ref)
    return sorted(refs)


def extract_corrections(text: str) -> list[str]:
    """Extract correction/retraction blockquotes."""
    corrections = []
    for m in CORRECTION_RE.finditer(text):
        # First line of the correction
        first_line = m.group(0).split("\n")[0]
        # Clean up markdown
        clean = re.sub(r"[>*]", "", first_line).strip()
        if len(clean) > 120:
            clean = clean[:117] + "..."
        corrections.append(clean)
    return corrections


def extract_table_claims(text: str) -> int:
    """Count claims in Decision Claims tables."""
    count = 0
    header_re = re.compile(r"^\|.*\bClaim\b.*\|", re.IGNORECASE)
    sep_re = re.compile(r"^\|[\s\-:]+\|")
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        if header_re.match(lines[i]):
            i += 1
            if i < len(lines) and sep_re.match(lines[i]):
                i += 1
            while i < len(lines) and lines[i].strip().startswith("|"):
                if not sep_re.match(lines[i]):
                    cells = [c.strip() for c in lines[i].split("|") if c.strip()]
                    if cells and not cells[0].startswith("---"):
                        count += 1
                i += 1
        else:
            i += 1
    return count


def build_knowledge_index(text: str) -> str:
    """Build the knowledge-index block content."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    h = content_hash(text)

    fm = extract_frontmatter_fields(text)
    sources = extract_source_tags(text)
    crossrefs = extract_crossrefs(text)
    corrections = extract_corrections(text)
    table_claims = extract_table_claims(text)

    lines = [f"{KI_START}"]
    lines.append(f"generated: {now}")
    lines.append(f"hash: {h}")
    lines.append("")

    # Frontmatter summary
    if fm.get("title") or fm.get("ticker"):
        title = fm.get("title") or fm.get("ticker", "")
        lines.append(f"title: {title}")
    if fm.get("status") or fm.get("conviction"):
        lines.append(f"status: {fm.get('status') or fm.get('conviction', '')}")
    if fm.get("tags"):
        lines.append(f"tags: {', '.join(fm['tags'])}")

    # Cross-references
    if crossrefs:
        lines.append(f"cross_refs: {', '.join(crossrefs)}")

    # Source provenance
    if sources:
        lines.append(f"sources: {len(sources)}")
        for s in sources[:10]:  # Cap at 10
            lines.append(f"  {s}")

    # Table claims count
    if table_claims:
        lines.append(f"table_claims: {table_claims}")

    # Corrections
    if corrections:
        lines.append("")
        for c in corrections:
            lines.append(f"@correction | {c}")

    lines.append("")
    lines.append(KI_END)
    return "\n".join(lines)


def inject_index(text: str, index_block: str) -> str:
    """Insert or replace knowledge-index block in file content.

    EOF-safe: inserts before trailing footnotes/reference links if present.
    """
    # Remove existing block if present
    text = re.sub(
        rf"\n*{re.escape(KI_START)}.*?{re.escape(KI_END)}\n*",
        "\n",
        text,
        flags=re.DOTALL,
    ).rstrip()

    # Find trailing footnotes/reference links
    trailing_match = TRAILING_RE.search(text)
    if trailing_match:
        pos = trailing_match.start()
        return text[:pos] + "\n\n" + index_block + "\n" + text[pos:]
    else:
        return text + "\n\n" + index_block + "\n"


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = hook_input.get("tool_name", "")
    if tool_name not in ("Write", "Edit"):
        sys.exit(0)

    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not is_eligible(file_path):
        sys.exit(0)

    # Read current file content
    try:
        text = Path(file_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        sys.exit(0)

    # Check frontmatter — warn if missing on eligible files
    fm_warning = ""
    if not re.match(r"^---\n.*?\n---", text, re.DOTALL):
        fm_warning = "WARNING: No YAML frontmatter. Add --- block with title, date, status fields."

    # Check if index exists and hash matches (no update needed)
    existing_match = re.search(rf"{re.escape(KI_START)}(.*?){re.escape(KI_END)}", text, re.DOTALL)
    if existing_match:
        existing_block = existing_match.group(1)
        hash_match = re.search(r"hash:\s*(\S+)", existing_block)
        if hash_match and hash_match.group(1) == content_hash(text):
            sys.exit(0)  # Content unchanged, index is current

    # Build and inject the knowledge index
    index_block = build_knowledge_index(text)
    new_text = inject_index(text, index_block)

    # Write back
    Path(file_path).write_text(new_text, encoding="utf-8")

    # Log telemetry (amendment A5)
    try:
        log_entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": "knowledge_index_updated",
            "file": file_path,
            "tool": tool_name,
        }
        log_path = Path.home() / ".claude" / "hook-triggers.jsonl"
        with open(log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except OSError:
        pass

    # Return additionalContext
    fm = extract_frontmatter_fields(text)
    sources = extract_source_tags(text)
    crossrefs = extract_crossrefs(text)
    corrections = extract_corrections(text)
    summary = f"Knowledge index updated: {len(sources)} sources, {len(crossrefs)} cross-refs"
    if fm.get("title") or fm.get("ticker"):
        summary += f" [{fm.get('title') or fm.get('ticker')}]"

    # Only inject context when there's something actionable.
    # Success messages ("index updated") are noise — agent doesn't act on them.
    # Warnings ("no frontmatter") are actionable — agent can fix.
    # Correction advisory is actionable — agent can run propagation check.
    if fm_warning:
        output = {"additionalContext": fm_warning}
        print(json.dumps(output))
    elif corrections:
        # Check if corrections are new (not in prior index block)
        prior_corrections = []
        if existing_match:
            for line in existing_match.group(1).split("\n"):
                if line.strip().startswith("@correction"):
                    prior_corrections.append(line.strip())
        new_corrections = [f"@correction | {c}" for c in corrections]
        if set(new_corrections) != set(prior_corrections):
            output = {
                "additionalContext": (
                    f"CORRECTION detected in {file_path}. "
                    f"Run: uv run python3 /Users/alien/Projects/agent-infra/scripts/propagate-correction.py --from {file_path}"
                )
            }
            print(json.dumps(output))


if __name__ == "__main__":
    main()
