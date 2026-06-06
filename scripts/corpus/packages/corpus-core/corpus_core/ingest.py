"""Ingest a source (PDF, HTML/URL) into the canonical store.

CLI:
    corpus ingest --pdf <path> [--doi …] [--pmid …] [--parser mineru|pymupdf4llm|gemini-flash-lite]
    corpus ingest --url <url>  [--source-type webpage|blog_post|news]
    corpus ingest --html <path> --source-url <url>
    corpus ingest --revise --pdf <new> --paper-id <id>

Outputs per source:
    paper.pdf  (paper-typed sources only — copied bytes)
    parsed.<parser_id>/page.md
    parsed.<parser_id>/parser.json
    parsed.<parser_id>/parsed.sha256
    metadata.json
    annotations.jsonl  (initialized empty; appended by corpus_core.annotate)

Per the SCHEMA.md immutability rule, parsed dirs are addressed by `parser_id`
(MinerU version + backend + config_md5) — re-parses with new parser/config
write to a new dir, never mutate an existing one.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Optional

from . import SCHEMA_VERSION
from . import store as ps
from .store import CorpusStore
from .extract import DEFAULT_PARSER, ExtractResult, extract as run_extract


# ---------------------------------------------------------------------------
# Public API — PDF ingest
# ---------------------------------------------------------------------------


def ingest_pdf(
    store: CorpusStore,
    pdf_path: Path,
    *,
    doi: Optional[str] = None,
    pmid: Optional[str] = None,
    title: Optional[str] = None,
    parser: Optional[str] = None,
    parser_config: Optional[dict] = None,
    source_type: str = "paper",
    extra_metadata: Optional[dict] = None,
    skip_parse: bool = False,
) -> dict:
    """Ingest a single PDF. Returns the final metadata dict.

    Idempotent on (pdf_sha256, parser_id). If the paper already has a
    parsed.<parser_id>/ for the same PDF + parser config, this is a no-op.
    """
    pdf_path = Path(pdf_path).expanduser().resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected .pdf, got: {pdf_path}")

    pdf_sha = ps.sha256_file(pdf_path)
    paper_id = store.derive_paper_id(doi=doi, pmid=pmid, pdf_sha=pdf_sha)
    p_path = store.paper_path(paper_id)
    p_path.mkdir(parents=True, exist_ok=True)

    # Idempotency: same PDF + already-parsed → no-op (any parser_id satisfies)
    if store.exists(paper_id):
        existing = store.get(paper_id)
        existing_pdf_sha = existing.metadata.get("pdf_sha256")
        if existing_pdf_sha == pdf_sha and _has_any_parsed(p_path):
            print(f"  ✓ {paper_id} already ingested (pdf_sha256 match) — no-op")
            return existing.metadata
        if existing_pdf_sha and existing_pdf_sha != pdf_sha:
            raise ps.PaperStoreError(
                f"{paper_id} already has a different pdf_sha256 "
                f"({existing_pdf_sha[:16]} vs new {pdf_sha[:16]}). "
                "Use `corpus ingest --revise` to record a revision."
            )

    # Copy PDF into store
    dest_pdf = p_path / "paper.pdf"
    if not dest_pdf.exists() or ps.sha256_file(dest_pdf) != pdf_sha:
        shutil.copy2(str(pdf_path), str(dest_pdf))

    # Initial metadata
    metadata = _initial_metadata(
        paper_id, source_type=source_type, doi=doi, pmid=pmid, title=title,
        pdf_sha=pdf_sha, content_hash=pdf_sha,
        extra_metadata=extra_metadata,
    )
    store.write_metadata(paper_id, metadata)

    if skip_parse:
        _ensure_jsonl(p_path)
        print(f"  ✓ {paper_id} ingested (skip_parse=True)")
        return metadata

    # Parse via dispatch
    chosen_parser = parser or DEFAULT_PARSER.get(source_type, "pymupdf4llm")
    result = run_extract(
        content=dest_pdf, source_type=source_type,
        parser=chosen_parser, parser_config=parser_config,
    )
    parsed_dir = _write_parsed(p_path, result, source="pdf")

    # Update metadata
    metadata["parsed_sha256"] = (parsed_dir / "parsed.sha256").read_text().strip()
    metadata["parser"] = json.loads((parsed_dir / "parser.json").read_text())
    metadata["last_updated"] = ps._now()
    store.write_metadata(paper_id, metadata)
    _ensure_jsonl(p_path)

    print(f"  ✓ {paper_id} ingested  parser_id={result.parser_id}  "
          f"parsed_sha={metadata['parsed_sha256'][:16]}")
    return metadata


# ---------------------------------------------------------------------------
# Public API — URL / HTML ingest
# ---------------------------------------------------------------------------


def ingest_url(
    store: CorpusStore,
    url: str,
    *,
    source_type: str = "webpage",
    title: Optional[str] = None,
    parser: Optional[str] = None,
    parser_config: Optional[dict] = None,
    extra_metadata: Optional[dict] = None,
) -> dict:
    """Fetch a URL via httpx + extract via trafilatura. Returns metadata."""
    from .extract import html_trafilatura

    # Fetch first so we have content_hash before deriving the source_id
    import httpx  # type: ignore
    r = httpx.get(url, timeout=30.0, follow_redirects=True,
                  headers={"User-Agent": "corpus-core/0.1 (+local)"})
    r.raise_for_status()
    html_bytes = r.content
    return _ingest_html_bytes(
        store,
        html_bytes, url=url, source_type=source_type, title=title,
        parser=parser or "trafilatura", parser_config=parser_config,
        extra_metadata=extra_metadata,
    )


def ingest_html(
    store: CorpusStore,
    html_path: Path,
    *,
    source_url: str,
    source_type: str = "webpage",
    title: Optional[str] = None,
    parser_config: Optional[dict] = None,
    extra_metadata: Optional[dict] = None,
) -> dict:
    """Ingest a caller-provided HTML file (when fetch happens elsewhere)."""
    html_path = Path(html_path).expanduser().resolve()
    return _ingest_html_bytes(
        store,
        html_path.read_bytes(), url=source_url, source_type=source_type,
        title=title, parser="trafilatura", parser_config=parser_config,
        extra_metadata=extra_metadata,
    )


# ---------------------------------------------------------------------------
# Public API — revision
# ---------------------------------------------------------------------------


def revise_pdf(
    store: CorpusStore,
    paper_id: str,
    new_pdf_path: Path,
    *,
    parser: Optional[str] = None,
    parser_config: Optional[dict] = None,
) -> dict:
    """Archive current PDF, install new, re-parse with the chosen parser."""
    new_pdf_path = Path(new_pdf_path).expanduser().resolve()
    res = store.register_revision(paper_id, new_pdf_path)
    p_path = store.paper_path(paper_id)

    chosen_parser = parser or "mineru"
    result = run_extract(
        content=p_path / "paper.pdf", source_type="paper",
        parser=chosen_parser, parser_config=parser_config,
    )
    parsed_dir = _write_parsed(p_path, result, source="pdf")

    meta = store.update_metadata(
        paper_id,
        parsed_sha256=(parsed_dir / "parsed.sha256").read_text().strip(),
        parser=json.loads((parsed_dir / "parser.json").read_text()),
    )
    print(f"  ✓ {paper_id} revised  new_pdf_sha={res.new_pdf_sha256[:16]}  "
          f"parser_id={result.parser_id}")
    return meta


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _initial_metadata(
    source_id: str,
    *,
    source_type: str,
    doi: Optional[str], pmid: Optional[str], title: Optional[str],
    pdf_sha: Optional[str], content_hash: str,
    extra_metadata: Optional[dict],
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "source_id": source_id,
        "paper_id": source_id,  # back-compat alias for paper-typed consumers
        "source_type": source_type,
        "content_hash": content_hash,
        "doi": doi,
        "pmid": pmid,
        "title": title,
        "pdf_sha256": pdf_sha,
        "retrieved_at": ps._now(),
        "last_updated": ps._now(),
        "fabio_class": None,
        "wikidata_qid": None,
        "openalex_id": None,
        "retraction_status": "active",
        "revisions": [],
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    return metadata


def _write_parsed(p_path: Path, result: ExtractResult, *, source: str) -> Path:
    """Write a parsed.<parser_id>/ dir. Immutable per SCHEMA.md."""
    parsed_dir = p_path / f"parsed.{result.parser_id}"
    parsed_dir.mkdir(parents=True, exist_ok=True)
    (parsed_dir / "page.md").write_text(result.parsed_markdown, encoding="utf-8")

    # Copy any staged image crops (Marker emits _page_*.jpeg / .png in extras).
    extras = result.extras or {}
    for img_path_str in extras.get("image_paths") or []:
        img = Path(img_path_str)
        if img.exists():
            shutil.copy2(str(img), str(parsed_dir / img.name))

    # Persist extras without the image_paths field (paths reference temp dirs).
    extras_for_meta = {k: v for k, v in extras.items() if k != "image_paths"}
    parser_json = {
        "parser_id": result.parser_id,
        "parser_config_md5": result.parser_config_md5,
        "char_count": result.char_count,
        "page_count": result.page_count,
        "extras": extras_for_meta or None,
        "source": source,
        "ts": ps._now(),
    }
    (parsed_dir / "parser.json").write_text(
        json.dumps(parser_json, indent=2, sort_keys=True), encoding="utf-8"
    )
    parsed_sha = ps.compute_parsed_sha(parsed_dir)
    (parsed_dir / "parsed.sha256").write_text(parsed_sha + "\n")
    return parsed_dir


def _has_any_parsed(p_path: Path) -> bool:
    """True if any parsed.<parser_id>/ exists with a valid parsed.sha256."""
    for child in p_path.iterdir():
        if child.is_dir() and child.name.startswith("parsed."):
            if (child / "parsed.sha256").exists():
                return True
    return False


def _ensure_jsonl(p_path: Path) -> None:
    for fname in ("citances_in.jsonl", "citances_out.jsonl", "annotations.jsonl"):
        path = p_path / fname
        if not path.exists():
            path.touch()


def _ingest_html_bytes(
    store: CorpusStore,
    html_bytes: bytes,
    *,
    url: str,
    source_type: str,
    title: Optional[str],
    parser: str,
    parser_config: Optional[dict],
    extra_metadata: Optional[dict],
) -> dict:
    import hashlib
    from .extract import html_trafilatura

    content_hash = hashlib.sha256(html_bytes).hexdigest()
    # Source id for non-paper sources: sha_<content[:16]>
    source_id = f"sha_{content_hash[:16]}"

    p_path = store.paper_path(source_id)
    p_path.mkdir(parents=True, exist_ok=True)

    metadata = _initial_metadata(
        source_id, source_type=source_type, doi=None, pmid=None, title=title,
        pdf_sha=None, content_hash=content_hash,
        extra_metadata={"source_url": url, **(extra_metadata or {})},
    )
    store.write_metadata(source_id, metadata)

    # Save raw HTML alongside metadata for re-parsing later
    (p_path / "source.html").write_bytes(html_bytes)

    result = html_trafilatura.extract_from_bytes(
        html_bytes, parser_config=parser_config, url=url,
    )
    parsed_dir = _write_parsed(p_path, result, source="html")

    metadata["parsed_sha256"] = (parsed_dir / "parsed.sha256").read_text().strip()
    metadata["parser"] = json.loads((parsed_dir / "parser.json").read_text())
    metadata["last_updated"] = ps._now()
    store.write_metadata(source_id, metadata)
    _ensure_jsonl(p_path)

    print(f"  ✓ {source_id} ingested from {url}  "
          f"parser_id={result.parser_id}  chars={result.char_count}")
    return metadata


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def add_cli(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "ingest",
        help="Ingest a PDF / URL / HTML into the corpus store",
    )
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument("--pdf", help="Path to a PDF")
    grp.add_argument("--url", help="URL to fetch + extract via trafilatura")
    grp.add_argument("--html", help="Path to a local HTML file (use with --source-url)")

    p.add_argument("--source-url", help="Origin URL when ingesting --html")
    p.add_argument("--doi", default=None)
    p.add_argument("--pmid", default=None)
    p.add_argument("--title", default=None)
    p.add_argument("--source-type", default=None,
                   help="paper|preprint|database_release|regulatory_filing|tool_output|"
                        "webpage|blog_post|news|other  (default depends on input)")
    p.add_argument("--parser", default=None,
                   help="marker-modal|mineru|pymupdf4llm|trafilatura|marker|gemini-flash-lite "
                        "(override default). Papers/preprints default to marker-modal; "
                        "'marker' is GPL-3.0 + Mac-MPS-buggy; opt-in only.")
    p.add_argument("--revise", action="store_true",
                   help="Treat this as a revision; --paper-id required (PDF only)")
    p.add_argument("--paper-id", default=None, help="Required with --revise")
    p.add_argument("--skip-parse", action="store_true",
                   help="Copy bytes + write metadata, skip parsing")
    p.set_defaults(func=_cmd_ingest)


def _cmd_ingest(args: argparse.Namespace) -> int:
    if args.pdf:
        pdf = Path(args.pdf)
        if args.revise:
            if not args.paper_id:
                print("--revise requires --paper-id", file=sys.stderr)
                return 2
            revise_pdf(args.corpus_store, args.paper_id, pdf, parser=args.parser)
            return 0
        ingest_pdf(
            args.corpus_store,
            pdf,
            doi=args.doi, pmid=args.pmid, title=args.title,
            source_type=args.source_type or "paper",
            parser=args.parser,
            skip_parse=args.skip_parse,
        )
        return 0
    if args.url:
        ingest_url(
            args.corpus_store,
            args.url,
            source_type=args.source_type or "webpage",
            title=args.title,
            parser=args.parser,
        )
        return 0
    if args.html:
        if not args.source_url:
            print("--html requires --source-url", file=sys.stderr)
            return 2
        ingest_html(
            args.corpus_store,
            Path(args.html),
            source_url=args.source_url,
            source_type=args.source_type or "webpage",
            title=args.title,
        )
        return 0
    print("nothing to ingest", file=sys.stderr)
    return 2
