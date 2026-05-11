"""Marker — LLM-enhanced PDF extraction (opt-in, GPL-licensed).

⚠ License + stability caveats:
  - Marker is GPL-3.0. Per SCHEMA.md the corpus toolkit is Apache/MIT-preferred;
    Marker is OPT-IN only and MUST NOT be the default parser. Users explicitly
    select it via `corpus ingest --pdf … --parser marker`.
  - Marker has confirmed bugs on Apple Silicon MPS (surya layout encoder #993,
    table decoder #967, ~20× slowdown since v1.9.0 #960). Crashes at p.10 of
    41-page preprints observed today. Chunked invocation (chunk_pages=3) is
    the standing workaround.
  - MinerU benchmarks higher on academic PDFs (OmniDocBench composite 93.04
    vs Marker 78.44). Prefer `--parser mineru` unless you specifically need
    Marker's `--use_llm` + figure-extraction combo.

Install separately (NOT a corpus-core runtime dep, to avoid GPL contamination):
    uv tool install marker-pdf
    GEMINI_API_KEY=… corpus ingest --pdf … --parser marker

parser_config keys (passed via JSON to marker's --config_json):
    use_llm: bool           Enable Gemini cleanup pass (default: True).
    extract_images: bool    Write figure crops to parsed dir (default: True).
    chunk_pages: int        Chunk large PDFs at N-page boundaries to dodge
                            the MPS bug (default: 3; pass 0 to disable).
    llm_service: str        Marker LLM backend (default: GoogleGeminiService).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from . import ExtractResult
from ._common import config_md5

_DEFAULT_CONFIG = {
    "use_llm": True,
    "extract_images": True,
    "chunk_pages": 3,
    "llm_service": "marker.services.gemini.GoogleGeminiService",
    "gemini_model_name": "gemini-3.1-flash-lite",
}


def _find_marker_bin() -> str:
    candidates = [
        os.environ.get("CORPUS_MARKER_BIN", ""),
        str(Path.home() / ".local/share/uv/tools/marker-pdf/bin/marker_single"),
        str(Path.home() / ".local/bin/marker_single"),
        shutil.which("marker_single") or "",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    raise RuntimeError(
        "marker_single not found. Install with: uv tool install marker-pdf"
    )


def _marker_version(bin_path: str) -> str:
    try:
        out = subprocess.check_output(
            [bin_path, "--help"], stderr=subprocess.STDOUT, text=True, timeout=30
        )
        m = re.search(r"marker[- ]?(\d+\.\d+\.\d+)", out)
        if m:
            return m.group(1)
    except Exception:
        pass
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
    try:
        from pypdf import PdfReader  # type: ignore
        return len(PdfReader(str(pdf_path)).pages)
    except Exception:
        raw = pdf_path.read_bytes()
        matches = re.findall(rb"/Type\s*/Page[^s]", raw)
        return max(1, len(matches))


def _run_chunk(
    bin_path: str,
    pdf_path: Path,
    output_dir: Path,
    cfg_json: Path,
    page_range: Optional[str] = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        bin_path,
        str(pdf_path),
        "--output_dir", str(output_dir),
        "--output_format", "markdown",
        "--config_json", str(cfg_json),
        "--disable_multiprocessing",
    ]
    if page_range:
        cmd += ["--page_range", page_range]
    env = os.environ.copy()
    env.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
    subprocess.run(cmd, check=True, env=env)


def _stitch(chunk_outputs: list[Path], pdf_stem: str) -> tuple[str, dict, list[Path]]:
    """Stitch per-chunk Marker outputs into (markdown, meta, image_paths)."""
    md_chunks: list[str] = []
    meta_chunks: list[dict] = []
    image_paths: list[Path] = []
    for chunk in chunk_outputs:
        inner = chunk / pdf_stem
        if not inner.is_dir():
            inner = chunk
        md_path = inner / f"{pdf_stem}.md"
        if not md_path.exists():
            cands = list(inner.glob("*.md"))
            if cands:
                md_path = cands[0]
        meta_path = inner / f"{pdf_stem}_meta.json"
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
        for fig in inner.glob("_page_*.jpeg"):
            image_paths.append(fig)
        for fig in inner.glob("_page_*.png"):
            image_paths.append(fig)

    merged_meta: dict = {"pages": []}
    for m in meta_chunks:
        if isinstance(m.get("pages"), list):
            merged_meta["pages"].extend(m["pages"])
        for k, v in m.items():
            if k == "pages":
                continue
            merged_meta.setdefault(k, v)

    return "\n\n".join(md_chunks), merged_meta, image_paths


def extract(
    pdf_path: Path,
    *,
    parser_config: Optional[dict] = None,
) -> ExtractResult:
    """Run Marker against `pdf_path`, return markdown + parser_id.

    Chunks the PDF at `chunk_pages` boundaries (default 3) as the standing
    workaround for the surya MPS bug. Image crops are NOT inlined into the
    ExtractResult — they're staged in extras['image_paths'] so the caller
    (corpus_core.ingest._write_parsed) can copy them into
    parsed.<parser_id>/.
    """
    pdf_path = Path(pdf_path).resolve()
    bin_path = _find_marker_bin()

    cfg = {**_DEFAULT_CONFIG, **(parser_config or {})}
    chunk_pages = int(cfg.pop("chunk_pages", 3))
    # Build the config Marker actually consumes
    marker_cfg = {k: v for k, v in cfg.items() if k in {
        "use_llm", "extract_images", "llm_service",
        "gemini_model_name",
        "force_ocr", "format_lines", "redo_inline_math",
    }}

    full_cfg_md5 = config_md5({**marker_cfg, "chunk_pages": chunk_pages})

    with tempfile.TemporaryDirectory(prefix="corpus-marker-") as td:
        td_path = Path(td)
        cfg_path = td_path / "marker_config.json"
        cfg_path.write_text(json.dumps(marker_cfg), encoding="utf-8")

        chunk_outputs: list[Path] = []
        if chunk_pages > 0:
            npages = _pdf_page_count(pdf_path)
            for start in range(0, npages, chunk_pages):
                end = min(start + chunk_pages - 1, npages - 1)
                chunk_dir = td_path / f"chunk_{start:04d}_{end:04d}"
                _run_chunk(
                    bin_path, pdf_path, chunk_dir, cfg_path,
                    page_range=f"{start}-{end}",
                )
                chunk_outputs.append(chunk_dir)
        else:
            single = td_path / "single"
            _run_chunk(bin_path, pdf_path, single, cfg_path, page_range=None)
            chunk_outputs.append(single)

        md, meta, image_paths = _stitch(chunk_outputs, pdf_path.stem)

        # Image paths live in the tempdir — copy out before it cleans up.
        # The caller (_write_parsed) can move them; we return their CURRENT
        # paths in extras and trust the caller to handle quickly OR we copy
        # them out now to a non-temp staging path.
        # Choosing the latter for correctness.
        staging = Path(tempfile.mkdtemp(prefix="corpus-marker-images-"))
        staged_images: list[str] = []
        for img in image_paths:
            dest = staging / img.name
            shutil.copy2(str(img), str(dest))
            staged_images.append(str(dest))

    parser_id = (
        f"marker@{_marker_version(bin_path)}"
        f"+{'llm' if marker_cfg.get('use_llm') else 'nollm'}"
        f"+cfg-{full_cfg_md5[:8]}"
    )
    return ExtractResult(
        parser_id=parser_id,
        parsed_markdown=md,
        parser_config_md5=full_cfg_md5,
        page_count=len(meta.get("pages") or []) or None,
        char_count=len(md),
        extras={
            "image_paths": staged_images,
            "meta": meta,
            "chunk_pages": chunk_pages,
        },
    )
