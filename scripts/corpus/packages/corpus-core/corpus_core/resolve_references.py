"""Phase B of the graph layer — resolve reference-section entries to (doi, pmid).

Reads the active parsed markdown (``parsed.<parser_id>/page.md`` via
``PaperRecord.parsed_markdown_path``), locates the reference section, splits it
into entries, queries Crossref for the non-inline-DOI tail, and writes
``references_resolved.json``.

Network resolution is gated behind ``--online`` so the smoke test runs offline;
the offline path still extracts reference strings with
``unresolved_reason="offline"``.
"""
from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from typing import Optional

from . import store as ps


# Header: tolerate marker's `## <span id=...></span>REFERENCES` (HTML tags) and
# `# **References**` (markdown emphasis), plus trailing content (no `$` anchor);
# `\b` ends the keyword.
REF_HEADERS = re.compile(
    r"^\s{0,3}#{1,6}\s+(?:[*_`]+|<[^>]*>\s*)*"
    r"(references|bibliography|works\s+cited|literature\s+cited)\b",
    re.IGNORECASE | re.MULTILINE,
)
# Numbered or bracketed reference entries (fallback path for non-marker markdown)
REF_ENTRY = re.compile(
    r"^\s*(?:\[(\d+)\]|(\d+)[\.\)])\s+(.+?)(?=^\s*(?:\[\d+\]|\d+[\.\)])\s|\Z)",
    re.MULTILINE | re.DOTALL,
)
DOI_IN_TEXT = re.compile(r"\b(10\.\d{4,9}/[^\s\)\]<>\"']+)", re.IGNORECASE)

# Marker renders references as markdown list items. Match the bullet, then strip
# an optional leading number / span tag downstream.
_BULLET = re.compile(r"^\s*[-*]\s+(.*\S.*)$")
_NUM_PREFIX = re.compile(r"^(\d{1,4})[.)]\s+(.*)$")
_MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")
_HTML_TAG = re.compile(r"<[^>]+>")
_SECTION_HEADER = re.compile(r"^\s{0,3}#{1,6}\s")


def _clean_reference_text(s: str) -> str:
    """Collapse marker markdown to plain reference text, preserving DOIs.

    Pulls DOIs out of link hrefs into the text (marker often hides the DOI in
    the URL while the visible text is truncated), drops HTML/span tags, flattens
    `[text](url)` to `text`, and normalizes whitespace.
    """
    def _link(m: "re.Match[str]") -> str:
        text, url = m.group(1), m.group(2)
        doi = re.search(r"10\.\d{4,9}/[^\s)\"'>]+", url)
        return f"{text} {doi.group(0)}" if doi else text
    s = _MD_LINK.sub(_link, s)
    s = _HTML_TAG.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


def extract_reference_section(paper_md: str) -> Optional[str]:
    """Return the substring from the references heading to the end of paper.md."""
    m = REF_HEADERS.search(paper_md)
    if not m:
        # Fallback: tail-search for plain "References" line
        for pattern in (r"\nReferences\n", r"\nREFERENCES\n", r"\nBibliography\n"):
            m2 = re.search(pattern, paper_md)
            if m2:
                return paper_md[m2.end():]
        return None
    return paper_md[m.end():]


def extract_entries(ref_section: str) -> list[dict]:
    """Split the reference section into entries.

    Marker renders references as a markdown bullet list — that is the primary
    path (numbered `- 9. Buss`, span-tagged `- <span/>1. [t](u)`, or unnumbered
    Vancouver `- Zhang Z`). A clean numbered-entry fallback covers non-bulleted
    markdown. There is deliberately NO blank-line/paragraph heuristic: it matched
    stray digits in acknowledgment/copyright text and produced ~0% real recall.
    """
    # --- Primary: markdown bullet list (marker-modal) ---
    items: list[list[str]] = []
    cur: list[str] | None = None
    for line in ref_section.split("\n"):
        if _SECTION_HEADER.match(line):
            break  # the next section header ends the reference list
        bullet = _BULLET.match(line)
        if bullet:
            if cur is not None:
                items.append(cur)
            cur = [bullet.group(1)]
        elif cur is not None and line.strip():
            cur.append(line.strip())  # wrapped continuation of the current entry
    if cur is not None:
        items.append(cur)

    entries: list[dict] = []
    for i, parts in enumerate(items, start=1):
        text = _clean_reference_text(" ".join(parts))
        numbered = _NUM_PREFIX.match(text)
        if numbered:
            label, text = f"[{numbered.group(1)}]", numbered.group(2).strip()
        else:
            label = f"[{i}]"
        if len(text) >= 20:
            entries.append({"ref_label": label, "raw_text": text})
    if entries:
        return entries

    # --- Fallback: bare numbered/bracketed entries (non-bulleted markdown) ---
    for m in REF_ENTRY.finditer(ref_section):
        label = m.group(1) or m.group(2)
        text = _clean_reference_text(m.group(3))
        if len(text) >= 20:
            entries.append({"ref_label": f"[{label}]", "raw_text": text})
    return entries


def extract_inline_doi(text: str) -> Optional[str]:
    m = DOI_IN_TEXT.search(text)
    if not m:
        return None
    doi = m.group(1).rstrip(".,;)")
    return doi.lower()


def resolve_via_crossref(text: str, timeout: float = 10.0) -> Optional[dict]:
    """Best-effort Crossref query by free-text. Returns top hit dict or None."""
    q = urllib.parse.quote(text[:300])
    url = f"https://api.crossref.org/works?query.bibliographic={q}&rows=1"
    req = urllib.request.Request(url, headers={"User-Agent": "corpus-core/0.1 (mailto:markus@synthoria.bio)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except Exception as exc:  # pragma: no cover — network
        return {"_error": str(exc)}
    items = ((data.get("message") or {}).get("items") or [])
    if not items:
        return None
    top = items[0]
    return {
        "doi": (top.get("DOI") or "").lower() or None,
        "title": (top.get("title") or [None])[0],
        "year": (top.get("issued", {}).get("date-parts", [[None]])[0][0]),
        "score": top.get("score"),
    }


def resolve_references(paper_id: str, *, online: bool = False) -> dict:
    rec = ps.get(paper_id)
    parsed_md = rec.parsed_markdown_path()
    if parsed_md is None:
        raise FileNotFoundError(
            f"{paper_id} is not parsed (no parsed.<parser_id>/page.md)"
        )

    parsed_sha = rec.metadata.get("parsed_sha256") or ""
    out_path = rec.path / "references_resolved.json"

    # Idempotency: skip if parsed_sha matches stored value
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text())
            if existing.get("parsed_sha256") == parsed_sha and existing.get("online") == online:
                print(f"  ✓ {paper_id} references already resolved (cache hit)")
                return existing
        except json.JSONDecodeError:
            pass

    md = parsed_md.read_text(encoding="utf-8")
    ref_section = extract_reference_section(md) or ""
    entries = extract_entries(ref_section)

    resolved: list[dict] = []
    for e in entries:
        inline_doi = extract_inline_doi(e["raw_text"])
        record = {
            "ref_label": e["ref_label"],
            "raw_text": e["raw_text"][:1500],
            "resolved_doi": inline_doi,
            "resolved_pmid": None,
            "resolved_paper_id": (
                ps.derive_paper_id(doi=inline_doi, check_collision=False) if inline_doi else None
            ),
            "confidence": 1.0 if inline_doi else 0.0,
            "source": "inline_doi" if inline_doi else None,
            "unresolved_reason": None if inline_doi else ("offline" if not online else None),
        }
        if not inline_doi and online:
            hit = resolve_via_crossref(e["raw_text"]) or {}
            if hit.get("doi"):
                record["resolved_doi"] = hit["doi"]
                record["resolved_paper_id"] = ps.derive_paper_id(doi=hit["doi"], check_collision=False)
                record["confidence"] = float(hit.get("score") or 0.0) / 100.0
                record["source"] = "crossref"
            else:
                record["unresolved_reason"] = "no_crossref_hit"
        resolved.append(record)

    result = {
        "paper_id": paper_id,
        "parsed_sha256": parsed_sha,
        "online": online,
        "entries": resolved,
        "stats": {
            "total": len(resolved),
            "with_doi": sum(1 for r in resolved if r["resolved_doi"]),
        },
    }
    out_path.write_text(json.dumps(result, indent=2))
    rate = (result["stats"]["with_doi"] / max(1, result["stats"]["total"])) * 100
    print(f"  ✓ {paper_id} references: {result['stats']['with_doi']}/{result['stats']['total']} resolved ({rate:.0f}%)")
    return result


def add_cli(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("resolve-references", help="Resolve a paper's reference list")
    p.add_argument("--paper-id", required=True)
    p.add_argument("--online", action="store_true", help="Query Crossref for unresolved entries")
    p.set_defaults(func=lambda args: (resolve_references(args.paper_id, online=args.online), 0)[1])
