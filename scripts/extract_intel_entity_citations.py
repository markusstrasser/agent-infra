#!/usr/bin/env python3
"""Intel entity citation extraction (manual corpus annotation backfill).

Walks ~/Projects/intel/analysis/{entities,themes}/*.md, extracts DOI/PMID
citations with their adjacent admiralty grade marker (e.g. [A1]–[F6]), and
writes one corpus annotation per citation.

This is a backfill/CLI writer: it calls corpus_core.annotate (the sole
annotation writer) directly with actor_type='human' — the v2-sanctioned manual
path. There is no corpus_attest MCP tool (retired under substrate v2; routine
attestation is automatic via each repo's mutation-gateway outbox).

For each citation:
  - Derive source_id (doi_<slug> | pmid_<n> | pmcid_<id>)
  - Ensure <corpus-root>/<source_id>/ exists (lazy metadata-only entry)
  - Append a corpus annotation (corpus_core.annotate):
      repo='intel', actor_type='human', actor_id='urn:agent:human:markus',
      scope='annotation', tool='entity-file-citation',
      source_content_hash=sha256(entity_file_bytes)

The annotation is keyed on the (entity_file, source_id, admiralty_grade)
tuple via corpus_core's stable_tuple → idempotent on re-run.

Run from agent-infra (intel session-write guard rejects foreign edits to
intel/ — but corpus/ is the substrate's home, so writes there are fine).
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

INTEL_ROOT = Path.home() / "Projects" / "intel"
ENTITIES_DIR = INTEL_ROOT / "analysis" / "entities"
THEMES_DIR = INTEL_ROOT / "analysis" / "themes"

CORPUS_PKG = (
    Path.home() / "Projects" / "agent-infra" / "scripts"
    / "corpus" / "packages" / "corpus-core"
)
sys.path.insert(0, str(CORPUS_PKG))

from corpus_core.annotate import annotate as corpus_annotate
from corpus_core.identity import derive_source_id, slug_doi, sha256_hex
from corpus_core.store import CorpusStore

# ---------------------------------------------------------------------------
# Citation extraction
# ---------------------------------------------------------------------------

# DOI: 10.<registrant>/<suffix> — broad pattern, then rstrip punctuation.
_DOI_RE = re.compile(r"\b10\.\d{4,9}/[\w.\-()/:;]+\b", re.IGNORECASE)
# PMID: explicit pubmed prefix (avoids false positives on bare digits).
_PMID_RE = re.compile(
    r"\b(?:pubmed[/.]|pmid[:\s]+)(\d{6,9})\b", re.IGNORECASE
)
_PMCID_RE = re.compile(r"\bPMC\d+\b", re.IGNORECASE)
# Admiralty grade: [A-F][1-6] within ~80 chars of the citation.
_GRADE_RE = re.compile(r"\[([A-F][1-6])\]", re.IGNORECASE)


def _scrub_doi_tail(doi: str) -> str:
    return doi.rstrip(".,;:)\"'>")


def _grade_near(text: str, span: tuple[int, int], window: int = 80) -> str | None:
    """Find the closest [A-F][1-6] grade within `window` chars of `span`."""
    start = max(0, span[0] - window)
    end = min(len(text), span[1] + window)
    chunk = text[start:end]
    matches = list(_GRADE_RE.finditer(chunk))
    if not matches:
        return None
    # Closest by absolute distance to the citation
    cite_local = (span[0] - start, span[1] - start)
    matches.sort(key=lambda m: min(abs(m.start() - cite_local[1]),
                                   abs(m.end() - cite_local[0])))
    return matches[0].group(1).upper()


def _iter_files() -> list[Path]:
    files: list[Path] = []
    for d in (ENTITIES_DIR, THEMES_DIR):
        if d.is_dir():
            files.extend(sorted(d.glob("*.md")))
    return files


def extract_citations(path: Path) -> list[dict]:
    """Return list of {source_id, grade, raw} citations found in this file."""
    text = path.read_text(encoding="utf-8", errors="replace")
    seen: set[str] = set()
    out: list[dict] = []

    for m in _DOI_RE.finditer(text):
        doi = _scrub_doi_tail(m.group(0))
        sid = f"doi_{slug_doi(doi)}"
        if sid in seen:
            continue
        seen.add(sid)
        out.append({
            "source_id": sid, "raw": doi,
            "grade": _grade_near(text, m.span()),
        })

    for m in _PMID_RE.finditer(text):
        pmid = m.group(1)
        sid = f"pmid_{pmid}"
        if sid in seen:
            continue
        seen.add(sid)
        out.append({
            "source_id": sid, "raw": f"pmid:{pmid}",
            "grade": _grade_near(text, m.span()),
        })

    for m in _PMCID_RE.finditer(text):
        pmcid = m.group(0).upper()
        sid = f"pmcid_{pmcid.lower()}"
        if sid in seen:
            continue
        seen.add(sid)
        out.append({
            "source_id": sid, "raw": pmcid,
            "grade": _grade_near(text, m.span()),
        })

    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="Extract intel entity-file citations into corpus annotations"
    )
    parser.add_argument("--commit", action="store_true",
                        help="Apply writes. Without this, dry-run only.")
    parser.add_argument("--limit-files", type=int, default=None,
                        help="Process only the first N files (debug/test).")
    parser.add_argument("--corpus-root", required=True, type=Path,
                        help="Explicit corpus store root for --commit writes.")
    args = parser.parse_args(argv)
    corpus_store = CorpusStore(args.corpus_root)

    files = _iter_files()
    if args.limit_files:
        files = files[: args.limit_files]
    print(f"scanning {len(files)} files under {ENTITIES_DIR.parent}")

    total_citations = 0
    files_with_citations = 0
    annotations_written = 0
    annotations_skipped = 0
    sources_lazy_created = 0
    grade_distribution: dict[str, int] = {"none": 0}

    for path in files:
        cites = extract_citations(path)
        if not cites:
            continue
        files_with_citations += 1
        total_citations += len(cites)
        # Per-file content hash for the source_content_hash field
        file_sha = sha256_hex(path.read_bytes())

        for c in cites:
            grade = c["grade"] or "none"
            grade_distribution[grade] = grade_distribution.get(grade, 0) + 1

            if not args.commit:
                continue

            # Lazy-create the source dir + minimal metadata.json if absent.
            p_dir = corpus_store.paper_path(c["source_id"])
            if not p_dir.exists():
                p_dir.mkdir(parents=True)
                meta_path = p_dir / "metadata.json"
                from datetime import datetime, timezone
                import json
                meta = {
                    "schema_version": "1.0.0",
                    "source_id": c["source_id"],
                    "source_type": "paper",
                    "content_hash": "",
                    "doi": c["raw"] if c["raw"].startswith("10.") else None,
                    "pmid": c["raw"][5:] if c["raw"].startswith("pmid:") else None,
                    "pmcid": c["raw"] if c["raw"].startswith("PMC") else None,
                    "title": None,
                    "retrieved_at": datetime.now(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"),
                    "retraction_status": "unknown",
                    "revisions": [],
                }
                meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True))
                sources_lazy_created += 1

            # Bake the admiralty grade into the tool name so the stable_tuple
            # differentiates two grades on the same (file, source) pair.
            tool_label = f"entity-file-citation/{grade}"
            try:
                aid = corpus_annotate(
                    c["source_id"],
                    store=corpus_store,
                    repo="intel",
                    actor_type="human",
                    actor_id="urn:agent:human:markus",
                    scope="annotation",
                    tool=tool_label,
                    source_content_hash=file_sha,
                )
                # corpus_annotate is idempotent on stable_tuple — a re-run
                # appends nothing. We can't easily distinguish "wrote new" vs
                # "no-op" here without an extra read, so just count attempts.
                annotations_written += 1
            except Exception as exc:
                print(f"  ! annotate failed {path.name} {c['source_id']}: {exc}",
                      file=sys.stderr)
                annotations_skipped += 1

    print()
    print("=== Phase 6.5 results ===")
    print(f"  files scanned:           {len(files)}")
    print(f"  files with citations:    {files_with_citations}")
    print(f"  total citations:         {total_citations}")
    print(f"  grade distribution:      {grade_distribution}")
    if args.commit:
        print(f"  sources lazy-created:    {sources_lazy_created}")
        print(f"  annotations written:     {annotations_written}")
        print(f"  annotations skipped:     {annotations_skipped}")
    else:
        print()
        print("--- DRY RUN — no writes. Re-run with --commit to apply. ---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
