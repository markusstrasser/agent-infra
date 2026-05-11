"""Ingest a PDF into the canonical store.

Single CLI: `papers ingest --pdf <path> [--doi ... --pmid ...]`
            `papers ingest --revise --pdf <new> --paper-id <id>`

Marker is run as a subprocess (the installed CLI), chunked at 3 pages to work
around the surya MPS bug (datalab-to/marker#993). A pre-patched venv at
/tmp/pdf-bench/.venv/bin/marker_single is preferred when present; otherwise
falls back to plain `marker_single`.

Outputs per paper:
    paper.pdf
    parsed/paper.md
    parsed/paper_meta.json
    parsed/_page_*_Figure_*.jpeg
    parsed/parser.json
    parsed/parsed.sha256
    metadata.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from . import SCHEMA_VERSION
from . import paper_store as ps


CHUNK_PAGES = 3  # surya MPS workaround
DEFAULT_MARKER_BIN = "/tmp/pdf-bench/.venv/bin/marker_single"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_marker_bin() -> str:
    candidates = [
        os.environ.get("PAPERS_MARKER_BIN", ""),
        DEFAULT_MARKER_BIN,
        shutil.which("marker_single") or "",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    raise RuntimeError(
        "marker_single not found. Set PAPERS_MARKER_BIN, install marker, or "
        "use /tmp/pdf-bench/.venv/bin/marker_single."
    )


def _marker_version(bin_path: str) -> str:
    try:
        out = subprocess.check_output(
            [bin_path, "--help"], stderr=subprocess.STDOUT, text=True, timeout=30
        )
        m = re.search(r"marker[- ]([\d.]+)", out)
        if m:
            return m.group(1)
    except Exception:
        pass
    # Try `pip show marker-pdf` in the marker venv
    venv = Path(bin_path).parent
    pip = venv / "pip"
    if pip.exists():
        try:
            out = subprocess.check_output(
                [str(pip), "show", "marker-pdf"], text=True, timeout=10
            )
            m = re.search(r"^Version:\s*(\S+)", out, re.MULTILINE)
            if m:
                return m.group(1)
        except Exception:
            pass
    return "unknown"


def _pdf_page_count(pdf_path: Path) -> int:
    """Lightweight page count using pypdf if available, else regex over raw bytes."""
    try:
        from pypdf import PdfReader  # type: ignore
        return len(PdfReader(str(pdf_path)).pages)
    except Exception:
        pass
    # Crude fallback: count /Type /Page (not /Pages) — sufficient for chunking
    raw = pdf_path.read_bytes()
    matches = re.findall(rb"/Type\s*/Page[^s]", raw)
    return max(1, len(matches))


def _run_marker_chunk(
    bin_path: str,
    pdf_path: Path,
    output_dir: Path,
    page_range: str,
    llm_service: Optional[str] = None,
    extra_args: Optional[list[str]] = None,
) -> None:
    """Run marker_single for a single page range. Writes into output_dir/<stem>/."""
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        bin_path,
        str(pdf_path),
        "--output_dir", str(output_dir),
        "--output_format", "markdown",
        "--page_range", page_range,
        "--disable_multiprocessing",
    ]
    if llm_service:
        cmd += ["--use_llm", "--llm_service", llm_service]
    if extra_args:
        cmd += extra_args
    env = os.environ.copy()
    env.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
    print(f"  ▸ marker pages {page_range}", flush=True)
    subprocess.run(cmd, check=True, env=env)


def _stitch_chunks(chunk_outputs: list[Path], dest_parsed: Path, pdf_stem: str) -> None:
    """Stitch per-chunk marker outputs into a single parsed/ directory.

    Each chunk output is at output_dir/<stem>/{paper.md,paper_meta.json,_page_*.jpeg}.
    """
    dest_parsed.mkdir(parents=True, exist_ok=True)
    md_chunks: list[str] = []
    meta_chunks: list[dict] = []
    for chunk in chunk_outputs:
        inner = chunk / pdf_stem
        if not inner.is_dir():
            # Marker sometimes writes directly to chunk root depending on version
            inner = chunk
        md_path = inner / f"{pdf_stem}.md"
        meta_path = inner / f"{pdf_stem}_meta.json"
        if not md_path.exists():
            # Try without stem prefix
            cands = list(inner.glob("*.md"))
            if cands:
                md_path = cands[0]
        if not meta_path.exists():
            cands = list(inner.glob("*_meta.json"))
            if cands:
                meta_path = cands[0]
        if md_path.exists():
            md_chunks.append(md_path.read_text(encoding="utf-8", errors="replace"))
        if meta_path.exists():
            try:
                meta_chunks.append(json.loads(meta_path.read_text()))
            except json.JSONDecodeError:
                pass
        # Copy figures
        for fig in inner.glob("_page_*.jpeg"):
            shutil.copy2(str(fig), str(dest_parsed / fig.name))
        for fig in inner.glob("_page_*.png"):
            shutil.copy2(str(fig), str(dest_parsed / fig.name))

    (dest_parsed / "paper.md").write_text("\n\n".join(md_chunks), encoding="utf-8")
    # Merge meta: concatenate `pages` lists if present
    merged_meta: dict = {"pages": []}
    for m in meta_chunks:
        if isinstance(m.get("pages"), list):
            merged_meta["pages"].extend(m["pages"])
        # Keep first non-pages fields
        for k, v in m.items():
            if k == "pages":
                continue
            merged_meta.setdefault(k, v)
    (dest_parsed / "paper_meta.json").write_text(
        json.dumps(merged_meta, indent=2), encoding="utf-8"
    )


def _run_marker_chunked(
    pdf_path: Path,
    dest_parsed: Path,
    *,
    llm_service: Optional[str] = None,
    chunk_pages: int = CHUNK_PAGES,
    extra_args: Optional[list[str]] = None,
) -> dict:
    """Run marker over the whole PDF in chunks of `chunk_pages`. Returns parser metadata."""
    bin_path = _find_marker_bin()
    npages = _pdf_page_count(pdf_path)
    pdf_stem = pdf_path.stem
    with tempfile.TemporaryDirectory(prefix="papers-marker-") as td:
        td_path = Path(td)
        chunk_outputs: list[Path] = []
        for start in range(0, npages, chunk_pages):
            end = min(start + chunk_pages - 1, npages - 1)
            chunk_dir = td_path / f"chunk_{start:04d}_{end:04d}"
            _run_marker_chunk(
                bin_path,
                pdf_path,
                chunk_dir,
                page_range=f"{start}-{end}",
                llm_service=llm_service,
                extra_args=extra_args,
            )
            chunk_outputs.append(chunk_dir)
        _stitch_chunks(chunk_outputs, dest_parsed, pdf_stem)

    return {
        "marker_version": _marker_version(bin_path),
        "surya_version": "unknown",
        "llm_service": llm_service,
        "page_range_chunk": chunk_pages,
        "pages_total": npages,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def ingest_pdf(
    pdf_path: Path,
    *,
    doi: Optional[str] = None,
    pmid: Optional[str] = None,
    llm_service: Optional[str] = None,
    title: Optional[str] = None,
    extra_metadata: Optional[dict] = None,
    skip_parse: bool = False,
) -> dict:
    """Ingest a single PDF. Returns the final metadata dict.

    Idempotent on (pdf_sha256, parser config). If the paper already exists with
    the same pdf_sha256 and a current parsed_sha256, this is a no-op.
    """
    pdf_path = Path(pdf_path).expanduser().resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if not pdf_path.suffix.lower() == ".pdf":
        raise ValueError(f"Expected .pdf, got: {pdf_path}")

    pdf_sha = ps.sha256_file(pdf_path)
    paper_id = ps.derive_paper_id(doi=doi, pmid=pmid, pdf_sha=pdf_sha)
    p_path = ps.paper_path(paper_id)
    p_path.mkdir(parents=True, exist_ok=True)

    # Idempotency: same PDF + current parsed/ → no-op
    if ps.exists(paper_id):
        existing = ps.get(paper_id)
        existing_pdf_sha = existing.metadata.get("pdf_sha256")
        if existing_pdf_sha == pdf_sha and (p_path / "parsed" / "parsed.sha256").exists():
            print(f"  ✓ {paper_id} already ingested (pdf_sha256 match) — no-op")
            return existing.metadata
        if existing_pdf_sha and existing_pdf_sha != pdf_sha:
            # Caller used plain ingest on a revised PDF — refuse; require --revise
            raise ps.PaperStoreError(
                f"{paper_id} already has a different pdf_sha256 "
                f"({existing_pdf_sha[:16]} vs new {pdf_sha[:16]}). "
                "Use `papers ingest --revise` to record a revision."
            )

    # Copy PDF into store
    dest_pdf = p_path / "paper.pdf"
    if not dest_pdf.exists() or ps.sha256_file(dest_pdf) != pdf_sha:
        shutil.copy2(str(pdf_path), str(dest_pdf))

    # Initial metadata (parser fields filled after parse)
    metadata = {
        "paper_id": paper_id,
        "schema_version": SCHEMA_VERSION,
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
        "contributions": [],
        "used_by_repos": [],
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    ps.write_metadata(paper_id, metadata)

    if skip_parse:
        print(f"  ✓ {paper_id} ingested (skip_parse=True)")
        return metadata

    # Parse
    parsed_dir = p_path / "parsed"
    if parsed_dir.exists():
        shutil.rmtree(parsed_dir)
    config = {
        "chunk_pages": CHUNK_PAGES,
        "output_format": "markdown",
        "llm_service": llm_service or "",
    }
    config_md5 = ps.make_config_md5(config)
    parser_info = _run_marker_chunked(pdf_path, parsed_dir, llm_service=llm_service)
    parser_id = ps.make_parser_id(
        parser_info["marker_version"], parser_info["surya_version"],
        llm_service, config_md5,
    )
    parser_json = {
        "parser_id": parser_id,
        "config_md5": config_md5,
        "ts": ps._now(),
        **parser_info,
    }
    (parsed_dir / "parser.json").write_text(json.dumps(parser_json, indent=2))

    parsed_sha = ps.compute_parsed_sha(parsed_dir)
    (parsed_dir / "parsed.sha256").write_text(parsed_sha + "\n")

    metadata["parsed_sha256"] = parsed_sha
    metadata["parser"] = parser_json
    metadata["last_updated"] = ps._now()
    ps.write_metadata(paper_id, metadata)

    # Initialize empty derived files so consumers can rely on their presence
    for fname in ("citances_in.jsonl", "citances_out.jsonl", "annotations.jsonl"):
        path = p_path / fname
        if not path.exists():
            path.touch()

    print(f"  ✓ {paper_id} ingested  parsed_sha={parsed_sha[:16]}")
    return metadata


def revise_pdf(paper_id: str, new_pdf_path: Path, *, llm_service: Optional[str] = None) -> dict:
    """Archive current, install new PDF, re-parse. Returns new metadata."""
    new_pdf_path = Path(new_pdf_path).expanduser().resolve()
    res = ps.register_revision(paper_id, new_pdf_path)
    # Re-parse the now-current paper.pdf
    p_path = ps.paper_path(paper_id)
    parsed_dir = p_path / "parsed"
    config = {"chunk_pages": CHUNK_PAGES, "output_format": "markdown", "llm_service": llm_service or ""}
    config_md5 = ps.make_config_md5(config)
    parser_info = _run_marker_chunked(p_path / "paper.pdf", parsed_dir, llm_service=llm_service)
    parser_id = ps.make_parser_id(
        parser_info["marker_version"], parser_info["surya_version"],
        llm_service, config_md5,
    )
    parser_json = {
        "parser_id": parser_id,
        "config_md5": config_md5,
        "ts": ps._now(),
        **parser_info,
    }
    (parsed_dir / "parser.json").write_text(json.dumps(parser_json, indent=2))
    parsed_sha = ps.compute_parsed_sha(parsed_dir)
    (parsed_dir / "parsed.sha256").write_text(parsed_sha + "\n")

    meta = ps.update_metadata(
        paper_id,
        parsed_sha256=parsed_sha,
        parser=parser_json,
    )
    print(f"  ✓ {paper_id} revised  new_pdf_sha={res.new_pdf_sha256[:16]}  parsed_sha={parsed_sha[:16]}")
    return meta


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------


def add_cli(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("ingest", help="Ingest a PDF into the store")
    p.add_argument("--pdf", required=True, help="Path to the PDF")
    p.add_argument("--doi", default=None)
    p.add_argument("--pmid", default=None)
    p.add_argument("--title", default=None)
    p.add_argument("--llm-service", default=None,
                   help="e.g. marker.services.gemini.GoogleGeminiService")
    p.add_argument("--revise", action="store_true",
                   help="Treat this as a revision; --paper-id required")
    p.add_argument("--paper-id", default=None, help="Required with --revise")
    p.add_argument("--skip-parse", action="store_true",
                   help="Copy PDF + write metadata, skip marker (useful for tests)")
    p.set_defaults(func=_cmd_ingest)


def _cmd_ingest(args) -> int:
    pdf = Path(args.pdf)
    if args.revise:
        if not args.paper_id:
            print("--revise requires --paper-id", file=sys.stderr)
            return 2
        revise_pdf(args.paper_id, pdf, llm_service=args.llm_service)
        return 0
    ingest_pdf(
        pdf,
        doi=args.doi,
        pmid=args.pmid,
        title=args.title,
        llm_service=args.llm_service,
        skip_parse=args.skip_parse,
    )
    return 0
