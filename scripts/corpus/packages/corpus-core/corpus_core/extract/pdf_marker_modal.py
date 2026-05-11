"""Marker-on-Modal extractor — calls the deployed corpus-marker app.

Cross-project tool: any project that has `modal` Python lib installed and
authenticated can call this. The corpus CLI (uv tool installed globally)
wires it up as `corpus ingest --parser marker-modal`.

Deploy once:
    modal secret create gemini-api-key GEMINI_API_KEY=$GEMINI_API_KEY
    uv run modal deploy ~/Projects/agent-infra/scripts/corpus_marker_modal.py

Then from anywhere:
    corpus ingest --pdf <path> --parser marker-modal
    corpus ingest-batch --dir <path> --parser marker-modal --max-parallel 10
"""
from __future__ import annotations

import base64
import io
import zipfile
from pathlib import Path
from typing import Optional

from . import ExtractResult


_APP_NAME = "corpus-marker"
_FN_NAME = "extract_pdf"


def _lookup_fn():
    """Resolve the deployed Modal function. Cached at module level."""
    import modal  # type: ignore
    global _CACHED_FN
    try:
        if _CACHED_FN is not None:  # type: ignore[name-defined]
            return _CACHED_FN
    except NameError:
        pass
    fn = modal.Function.from_name(_APP_NAME, _FN_NAME)
    globals()["_CACHED_FN"] = fn
    return fn


def extract(
    pdf_path: Path,
    *,
    parser_config: Optional[dict] = None,
) -> ExtractResult:
    """Send the PDF bytes to Modal, unzip the returned parsed dir.

    Image crops (Marker's `_page_*.jpeg`/.png) are staged into a non-temp
    directory and returned via extras['image_paths'] for the caller
    (corpus_core.ingest._write_parsed) to copy into parsed.<parser_id>/.
    """
    import tempfile

    pdf_path = Path(pdf_path).resolve()
    pdf_bytes = pdf_path.read_bytes()

    fn = _lookup_fn()
    result = fn.remote(pdf_bytes, parser_config or {})

    if not result.get("ok"):
        raise RuntimeError(
            f"corpus-marker-modal failed at {result.get('stage')}: "
            f"{result.get('error', 'unknown error')}"
        )

    # Unzip the parsed dir into a staging directory; _write_parsed will copy
    # images out of it.
    staging = Path(tempfile.mkdtemp(prefix="corpus-marker-modal-"))
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

    return ExtractResult(
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


def extract_batch_remote(
    pdf_bytes_iter,
    *,
    parser_config: Optional[dict] = None,
    max_parallel: int = 10,
):
    """Yield (input_index, result_dict) pairs for parallel batch processing.

    Uses Modal's `.map()` for fan-out. `pdf_bytes_iter` yields raw PDF bytes;
    callers track the matching identity (path, source_id) by index.

    max_parallel caps concurrent Modal containers — keep modest for cost
    control. Modal's default is 100; we ask for 10.
    """
    fn = _lookup_fn()
    pdf_bytes_iter = list(pdf_bytes_iter)
    args = [
        (b, {**(parser_config or {}), "_batch_index": idx})
        for idx, b in enumerate(pdf_bytes_iter)
    ]
    # starmap unpacks (bytes, dict) tuples into the function's two args.
    # Do not preserve input order: one OCR-heavy/preempted PDF should not block
    # all completed siblings from being written to the local corpus.
    for result in fn.starmap(args, order_outputs=False, return_exceptions=True):
        if isinstance(result, Exception):
            yield -1, result
            continue
        idx = result.get("input_index")
        if idx is None:
            yield -1, result
            continue
        yield int(idx), result
