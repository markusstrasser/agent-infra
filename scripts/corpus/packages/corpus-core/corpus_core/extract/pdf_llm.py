"""LLM-fallback PDF extraction via Gemini Flash-Lite.

Migrated from research-mcp src/research_mcp/papers.py (`_extract_with_gemini`)
per Phase 1.5 §LLM fallback. Use only when local parsers (MinerU, pymupdf4llm)
fail or produce empty output. Requires `GOOGLE_API_KEY` (or `GEMINI_API_KEY`).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from . import ExtractResult
from ._common import config_md5


# NEVER default to gemini-2.5 — operator policy: Flash 3 only.
# The 'latest' aliases (gemini-flash-lite-latest, etc.) currently resolve
# to 2.5 — explicit pin required.
_DEFAULT_MODEL = "gemini-3-flash-preview"
_DEFAULT_PROMPT = (
    "Extract the full text of this PDF as markdown. Preserve section "
    "headings, lists, tables (as GFM), and inline math (as LaTeX between "
    "$ delimiters). Drop running headers/footers. Do not summarize."
)


def extract(
    pdf_path: Path,
    *,
    parser_config: Optional[dict] = None,
) -> ExtractResult:
    """Upload PDF to Gemini, return extracted markdown.

    parser_config supports:
        model:  Gemini model id (default: gemini-3-flash-preview)
        prompt: extraction prompt (default: see _DEFAULT_PROMPT)
    """
    pdf_path = Path(pdf_path).resolve()
    cfg = parser_config or {}
    model = cfg.get("model", _DEFAULT_MODEL)
    prompt = cfg.get("prompt", _DEFAULT_PROMPT)

    # Local import — google-genai is a heavy dep; only loaded on fallback path.
    from google import genai  # type: ignore
    from google.genai import types  # type: ignore

    api_key = (
        os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
    )
    if not api_key:
        raise RuntimeError(
            "pdf_llm.extract requires GOOGLE_API_KEY or GEMINI_API_KEY env var"
        )
    client = genai.Client(api_key=api_key)
    upload = client.files.upload(file=str(pdf_path), config={"mime_type": "application/pdf"})
    response = client.models.generate_content(
        model=model,
        contents=[prompt, upload],
        config=types.GenerateContentConfig(temperature=0.0),
    )
    md = response.text or ""

    full_cfg = {"model": model, **cfg}
    cfg_md5 = config_md5(full_cfg)
    return ExtractResult(
        parser_id=f"{model}+cfg-{cfg_md5[:8]}",
        parsed_markdown=md,
        parser_config_md5=cfg_md5,
        char_count=len(md),
    )
