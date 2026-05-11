"""Marker on Modal — GPU-accelerated PDF → markdown with Gemini LLM cleanup.

The local Marker path (corpus_core/extract/pdf_marker.py) is CPU-only and slow
on this Mac (surya MPS bugs #993/#967/#960, ~20× slowdown since v1.9.0). This
Modal app runs Marker on a T4 GPU with surya weights pre-baked into the image.

Cost model (verified pricing 2026):
  - T4: $0.59/hr → ~$0.005-0.013 per 41-page PDF (cold) / ~$0.0025 (warm)
  - Cold start: ~30s with pre-baked weights (vs ~3 min cold-downloading them)
  - scaledown_window=120 → stays warm 2 min after last call, so batch ingests
    hit warm pricing
  - min_containers=0 (default) → idle cost = $0

Deploy:
  modal secret create gemini-api-key GEMINI_API_KEY=$GEMINI_API_KEY
  uv run modal deploy scripts/corpus_marker_modal.py

Use (cross-project — corpus CLI is uv tool installed globally):
  corpus ingest --pdf <path> --parser marker-modal
  corpus ingest-batch --dir <path> --parser marker-modal --max-parallel 10
"""
from __future__ import annotations

import modal


# ---------------------------------------------------------------------------
# Image — pre-bake Marker + surya weights so cold starts skip the ~3 min DL.
# ---------------------------------------------------------------------------

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install(
        "libgl1",
        "libglib2.0-0",
        "libsm6",
        "libxext6",
        "libxrender1",
        "fonts-liberation",
        "ghostscript",
    )
    .pip_install(
        "marker-pdf>=1.10.0",
        "pypdf>=4.0",
        "google-genai>=1.0",
    )
    .env({
        # CUDA on Modal — kill any leftover MPS-fallback heuristics.
        "PYTORCH_ENABLE_MPS_FALLBACK": "0",
        # HuggingFace cache lives in the image (read-only at runtime, that's fine)
        "HF_HOME": "/root/.cache/huggingface",
    })
    # Pre-download all Marker/surya model weights into the image so cold-start
    # containers don't fetch them on every spawn. `create_model_dict()` is
    # Marker's canonical "load everything" entrypoint.
    .run_commands(
        "python -c 'from marker.models import create_model_dict; create_model_dict()'",
    )
)

app = modal.App(
    "corpus-marker",
    image=image,
    secrets=[modal.Secret.from_name("gemini-api-key")],
)


# ---------------------------------------------------------------------------
# Core function — single PDF → markdown + figure crops, all returned in-band.
# ---------------------------------------------------------------------------


@app.function(
    gpu="T4",
    timeout=900,
    scaledown_window=120,
    memory=8192,
    cpu=2,
)
def extract_pdf(pdf_bytes: bytes, parser_config: dict | None = None) -> dict:
    """Run Marker on `pdf_bytes`, return a self-contained result dict.

    Returns:
        {
          "ok": True,
          "markdown": str,           # the stitched page.md content
          "parsed_zip_b64": str,     # zipped parsed/ dir (all files, figures included)
          "parser_id": str,          # marker@<v>+gemini-<m>+cfg-<md5>
          "parser_config_md5": str,
          "page_count": int,
          "char_count": int,
          "image_count": int,
          "marker_version": str,
        }
    On failure:
        {"ok": False, "error": str, "stage": "models"|"convert"|"stitch"}
    """
    import base64
    import hashlib
    import io
    import json
    import os
    import re
    import subprocess
    import tempfile
    import zipfile
    from pathlib import Path

    cfg = {
        "use_llm": True,
        "extract_images": True,
        "llm_service": "marker.services.gemini.GoogleGeminiService",
        # Default Flash 3 (matches agent-infra canonical model ref). NEVER
        # default to 2.5 — operator policy.
        "gemini_model_name": "gemini-3-flash-preview",
        "force_ocr": False,
        "format_lines": False,
        "redo_inline_math": False,
        **(parser_config or {}),
    }
    # Marker reads GOOGLE_API_KEY from env; Modal secret provides GEMINI_API_KEY.
    if not os.environ.get("GOOGLE_API_KEY"):
        if os.environ.get("GEMINI_API_KEY"):
            os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

    cfg_keys = {
        k: v for k, v in cfg.items()
        if k in {
            "use_llm", "extract_images", "llm_service", "gemini_model_name",
            "force_ocr", "format_lines", "redo_inline_math",
        }
    }
    cfg_md5 = hashlib.md5(
        json.dumps(cfg_keys, sort_keys=True).encode()
    ).hexdigest()

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        pdf_path = td_path / "input.pdf"
        pdf_path.write_bytes(pdf_bytes)

        cfg_path = td_path / "marker_config.json"
        cfg_path.write_text(json.dumps(cfg_keys))

        out_dir = td_path / "out"
        out_dir.mkdir()

        cmd = [
            "marker_single",
            str(pdf_path),
            "--output_dir", str(out_dir),
            "--output_format", "markdown",
            "--config_json", str(cfg_path),
            "--disable_multiprocessing",
            "--disable_tqdm",
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=850)
        except subprocess.CalledProcessError as exc:
            return {
                "ok": False, "stage": "convert",
                "error": (exc.stderr or exc.stdout or str(exc))[-2000:],
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "stage": "convert", "error": "marker timeout (850s)"}

        # Marker writes out_dir/<stem>/{<stem>.md, _meta.json, _page_*.jpeg, ...}
        inner = out_dir / pdf_path.stem
        if not inner.is_dir():
            inner = out_dir
        md_candidates = list(inner.glob("*.md"))
        if not md_candidates:
            return {"ok": False, "stage": "stitch", "error": "marker produced no markdown"}
        md_path = md_candidates[0]
        md = md_path.read_text(encoding="utf-8", errors="replace")

        meta_path_candidates = list(inner.glob("*_meta.json"))
        meta = {}
        if meta_path_candidates:
            try:
                meta = json.loads(meta_path_candidates[0].read_text())
            except json.JSONDecodeError:
                meta = {}

        # Zip the whole inner/ dir for in-band return.
        zip_buf = io.BytesIO()
        image_count = 0
        with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for f in inner.rglob("*"):
                if f.is_file():
                    arcname = f.relative_to(inner).as_posix()
                    zf.write(f, arcname=arcname)
                    if re.search(r"_page_.*\.(jpe?g|png)$", f.name, re.IGNORECASE):
                        image_count += 1

    # Resolve marker version once. Marker exposes version via package
    # metadata (PEP 396), not a `__version__` attribute — the latter
    # returns "unknown" in the Modal container.
    try:
        from importlib.metadata import PackageNotFoundError, version
        try:
            marker_version = version("marker-pdf")
        except PackageNotFoundError:
            marker_version = "unknown"
    except ImportError:
        marker_version = "unknown"

    # The Gemini model name already carries the `gemini-` prefix
    # (e.g. `gemini-3-flash-preview`), so don't double-prefix in parser_id.
    parser_id = (
        f"marker-modal@{marker_version}"
        f"+{cfg.get('gemini_model_name', 'unknown').replace('.', '_')}"
        f"+cfg-{cfg_md5[:8]}"
    )

    return {
        "ok": True,
        "markdown": md,
        "parsed_zip_b64": base64.b64encode(zip_buf.getvalue()).decode("ascii"),
        "parser_id": parser_id,
        "parser_config_md5": cfg_md5,
        "page_count": len(meta.get("pages") or []) or None,
        "char_count": len(md),
        "image_count": image_count,
        "marker_version": marker_version,
        "meta": meta,
    }


# ---------------------------------------------------------------------------
# Local entrypoint — quick smoke test from CLI: `modal run scripts/corpus_marker_modal.py`
# ---------------------------------------------------------------------------


@app.local_entrypoint()
def smoke(pdf: str | None = None):
    """Smoke-test the deployed function on a single PDF.

    Usage:
        modal run scripts/corpus_marker_modal.py --pdf ~/Projects/corpus/<id>/paper.pdf
    """
    from pathlib import Path
    if pdf is None:
        pdf = str(Path.home() / "Projects/corpus/doi_10_1101_2026_04_10_26350624/paper.pdf")
    pdf_path = Path(pdf)
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")

    print(f"smoke test: {pdf_path}")
    result = extract_pdf.remote(pdf_path.read_bytes())
    if not result["ok"]:
        raise SystemExit(f"FAILED at {result['stage']}: {result['error']}")
    print(f"  parser_id:    {result['parser_id']}")
    print(f"  page_count:   {result['page_count']}")
    print(f"  char_count:   {result['char_count']}")
    print(f"  image_count:  {result['image_count']}")
    print(f"  markdown[:200]: {result['markdown'][:200]!r}")
