"""Batch-ingest PDFs in parallel — fan out to Modal extractors, write locally.

The single-PDF path (corpus_core.ingest.ingest_pdf) handles one PDF at a time
synchronously. For larger jobs (a directory of PDFs from research-mcp drops,
or a list-file), this module fans out via Modal's `.starmap()`.

CLI:
    corpus ingest-batch --dir <path> [--glob "*.pdf"] [--parser marker-modal]
                        [--max-parallel 10] [--source-type paper]
    corpus ingest-batch --list <txt-file> [--parser marker-modal] ...

`--list` reads one PDF path per line.

Already-ingested PDFs (matching pdf_sha256 + any parsed.<parser_id>/ present)
are skipped — re-runs are idempotent.

The corpus annotation (scope='raw_fetch') is NOT written here — call sites
that own the fetch (research-mcp's fetch_paper) do that themselves. This is
pure ingest: bytes in, parsed.<parser_id>/ + metadata.json + annotations.jsonl
out.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Iterable, Optional

from . import SCHEMA_VERSION
from . import store as ps
from .store import CorpusStore
from .extract import ExtractResult
from .ingest import _ensure_jsonl, _has_any_parsed, _initial_metadata, _write_parsed


# ---------------------------------------------------------------------------
# Pre-flight: derive paper_id, skip if already ingested
# ---------------------------------------------------------------------------


def _enumerate_inputs(
    dir_path: Optional[Path] = None,
    list_file: Optional[Path] = None,
    glob_pattern: str = "*.pdf",
) -> list[Path]:
    paths: list[Path] = []
    if dir_path is not None:
        if not dir_path.is_dir():
            raise SystemExit(f"--dir not a directory: {dir_path}")
        paths.extend(sorted(dir_path.rglob(glob_pattern)))
    if list_file is not None:
        if not list_file.exists():
            raise SystemExit(f"--list not found: {list_file}")
        for line in list_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            paths.append(Path(line).expanduser().resolve())
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in paths:
        if p not in seen and p.exists() and p.suffix.lower() == ".pdf":
            seen.add(p)
            unique.append(p)
    return unique


def _resolve_paper_id_and_skip(
    store: CorpusStore,
    pdf_path: Path,
    *,
    doi: Optional[str] = None,
    pmid: Optional[str] = None,
) -> tuple[str, str, bool]:
    """Returns (paper_id, pdf_sha, already_ingested)."""
    pdf_sha = ps.sha256_file(pdf_path)
    paper_id = store.derive_paper_id(doi=doi, pmid=pmid, pdf_sha=pdf_sha)
    p_path = store.paper_path(paper_id)
    if store.exists(paper_id):
        existing = store.get(paper_id)
        if existing.metadata.get("pdf_sha256") == pdf_sha and _has_any_parsed(p_path):
            return paper_id, pdf_sha, True
    return paper_id, pdf_sha, False


# ---------------------------------------------------------------------------
# Write a remote ExtractResult to the local corpus store.
# ---------------------------------------------------------------------------


def _write_to_store(
    store: CorpusStore,
    pdf_path: Path,
    paper_id: str,
    pdf_sha: str,
    result: ExtractResult,
    *,
    source_type: str,
    title: Optional[str] = None,
    doi: Optional[str] = None,
    pmid: Optional[str] = None,
) -> dict[str, Any]:
    p_path = store.paper_path(paper_id)
    p_path.mkdir(parents=True, exist_ok=True)
    dest_pdf = p_path / "paper.pdf"
    if not dest_pdf.exists() or ps.sha256_file(dest_pdf) != pdf_sha:
        shutil.copy2(str(pdf_path), str(dest_pdf))

    metadata = _initial_metadata(
        paper_id, source_type=source_type, doi=doi, pmid=pmid, title=title,
        pdf_sha=pdf_sha, content_hash=pdf_sha, extra_metadata=None,
    )
    store.write_metadata(paper_id, metadata)

    parsed_dir = _write_parsed(p_path, result, source="pdf")
    metadata["parsed_sha256"] = (parsed_dir / "parsed.sha256").read_text().strip()
    metadata["parser"] = json.loads((parsed_dir / "parser.json").read_text())
    metadata["last_updated"] = ps._now()
    store.write_metadata(paper_id, metadata)
    _ensure_jsonl(p_path)
    return metadata


# ---------------------------------------------------------------------------
# Public API — batch ingest dispatch
# ---------------------------------------------------------------------------


def batch_ingest(
    store: CorpusStore,
    inputs: list[Path],
    *,
    parser: str = "marker-modal",
    parser_config: Optional[dict] = None,
    source_type: str = "paper",
    max_parallel: int = 10,
) -> dict[str, Any]:
    """Ingest a list of PDF paths in parallel via the chosen parser.

    For `marker-modal`: fans out via Modal's .starmap().
    For local parsers (mineru, pymupdf4llm, marker): processes sequentially
    on the local machine — parallel local extractors compete for CPU/MPS, no
    speedup. Use marker-modal for actual parallelism.
    """
    # Pre-flight: skip already-ingested
    candidates: list[tuple[Path, str, str]] = []
    skipped_already_done: list[str] = []
    for pdf in inputs:
        paper_id, pdf_sha, done = _resolve_paper_id_and_skip(store, pdf)
        if done:
            skipped_already_done.append(paper_id)
            continue
        candidates.append((pdf, paper_id, pdf_sha))

    print(f"[batch] {len(inputs)} input PDFs  |  "
          f"{len(skipped_already_done)} already ingested  |  "
          f"{len(candidates)} to process")

    if not candidates:
        return {
            "ok": True, "processed": [],
            "skipped_already_done": skipped_already_done,
            "errors": [],
        }

    processed: list[dict] = []
    errors: list[dict] = []

    if parser == "marker-modal":
        # Stream-process via Modal's starmap so back-pressure is handled
        from .extract.pdf_marker_modal import extract_batch_remote

        pdf_bytes_iter = (p.read_bytes() for (p, _, _) in candidates)
        for idx, result in extract_batch_remote(
            pdf_bytes_iter, parser_config=parser_config, max_parallel=max_parallel,
        ):
            pdf, paper_id, pdf_sha = candidates[idx]
            try:
                if isinstance(result, Exception):
                    errors.append({"pdf": str(pdf), "error": repr(result)})
                    continue
                if not result.get("ok"):
                    errors.append({
                        "pdf": str(pdf),
                        "error": f"{result.get('stage')}: {result.get('error')}",
                    })
                    continue
                # Convert remote result dict → ExtractResult
                import base64
                import io
                import zipfile
                import tempfile

                staging = Path(tempfile.mkdtemp(prefix="corpus-marker-modal-batch-"))
                zip_bytes = base64.b64decode(result["parsed_zip_b64"])
                image_paths: list[str] = []
                with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                    for info in zf.infolist():
                        if info.is_dir():
                            continue
                        dest = staging / info.filename
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(zf.read(info))
                        if any(info.filename.lower().endswith(ext)
                               for ext in (".jpeg", ".jpg", ".png")):
                            image_paths.append(str(dest))

                er = ExtractResult(
                    parser_id=result["parser_id"],
                    parsed_markdown=result["markdown"],
                    parser_config_md5=result["parser_config_md5"],
                    page_count=result.get("page_count"),
                    char_count=result.get("char_count"),
                    extras={
                        "image_paths": image_paths,
                        "meta": result.get("meta") or {},
                        "marker_version": result.get("marker_version"),
                        "image_count": result.get("image_count"),
                        "remote": "modal",
                    },
                )
                meta = _write_to_store(
                    store,
                    pdf, paper_id, pdf_sha, er,
                    source_type=source_type,
                )
                processed.append({"pdf": str(pdf), "paper_id": paper_id,
                                  "parser_id": meta["parser"]["parser_id"]})
                print(f"  ✓ {paper_id}  ({er.char_count} chars, "
                      f"{er.extras.get('image_count', 0)} figs)")
            except Exception as exc:  # noqa: BLE001
                errors.append({"pdf": str(pdf), "error": repr(exc)})
                print(f"  ✗ {pdf.name}: {exc}", file=sys.stderr)
    else:
        # Local sequential fallback for non-modal parsers.
        from .extract import extract as run_extract

        for pdf, paper_id, pdf_sha in candidates:
            try:
                er = run_extract(
                    content=pdf, source_type=source_type,
                    parser=parser, parser_config=parser_config,
                )
                meta = _write_to_store(
                    store,
                    pdf, paper_id, pdf_sha, er,
                    source_type=source_type,
                )
                processed.append({"pdf": str(pdf), "paper_id": paper_id,
                                  "parser_id": meta["parser"]["parser_id"]})
                print(f"  ✓ {paper_id}")
            except Exception as exc:  # noqa: BLE001
                errors.append({"pdf": str(pdf), "error": repr(exc)})
                print(f"  ✗ {pdf.name}: {exc}", file=sys.stderr)

    return {
        "ok": len(errors) == 0,
        "processed": processed,
        "skipped_already_done": skipped_already_done,
        "errors": errors,
        "counts": {
            "input": len(inputs),
            "skipped": len(skipped_already_done),
            "processed": len(processed),
            "errors": len(errors),
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def add_cli(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "ingest-batch",
        help="Ingest many PDFs in parallel (marker-modal) or sequentially (local parsers)",
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--dir", help="Directory; recursively glob for PDFs")
    src.add_argument("--list", dest="list_file",
                     help="Text file with one PDF path per line (# comments OK)")

    p.add_argument("--glob", default="*.pdf", help="Glob with --dir (default: *.pdf)")
    p.add_argument("--parser", default="marker-modal",
                   choices=["marker-modal", "marker", "mineru", "pymupdf4llm",
                            "gemini-flash-lite"],
                   help="Extractor (default: marker-modal — GPU-parallel via Modal)")
    p.add_argument("--source-type", default="paper")
    p.add_argument("--max-parallel", type=int, default=10,
                   help="Max concurrent Modal containers (marker-modal only)")
    p.add_argument("--gemini-model", default=None,
                   help="Override gemini_model_name in parser_config (marker* only)")
    p.add_argument("--json", action="store_true",
                   help="Emit JSON summary to stdout")
    p.set_defaults(func=_cmd_batch)


def _cmd_batch(args: argparse.Namespace) -> int:
    inputs = _enumerate_inputs(
        dir_path=Path(args.dir).expanduser().resolve() if args.dir else None,
        list_file=Path(args.list_file).expanduser().resolve() if args.list_file else None,
        glob_pattern=args.glob,
    )
    if not inputs:
        print("no PDFs to ingest", file=sys.stderr)
        return 1

    parser_config: dict = {}
    if args.gemini_model:
        parser_config["gemini_model_name"] = args.gemini_model

    report = batch_ingest(
        args.corpus_store,
        inputs,
        parser=args.parser,
        parser_config=parser_config or None,
        source_type=args.source_type,
        max_parallel=args.max_parallel,
    )

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        c = report["counts"]
        print()
        print(f"=== batch ingest summary ===")
        print(f"  input:     {c['input']}")
        print(f"  skipped:   {c['skipped']}  (already ingested)")
        print(f"  processed: {c['processed']}")
        print(f"  errors:    {c['errors']}")

    return 0 if report["ok"] else 1
