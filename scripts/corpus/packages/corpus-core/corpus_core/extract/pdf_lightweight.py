"""pymupdf4llm — fast native-text PDF extraction.

License: AGPL-3.0 (or Artifex commercial). Acceptable for local-only personal
use per SCHEMA.md license invariant. NOT for public network deployment.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from . import ExtractResult
from ._common import config_md5


def extract(
    pdf_path: Path,
    *,
    parser_config: Optional[dict] = None,
) -> ExtractResult:
    import pymupdf4llm  # type: ignore

    pdf_path = Path(pdf_path)
    md = pymupdf4llm.to_markdown(str(pdf_path), **(parser_config or {}))
    version = getattr(pymupdf4llm, "__version__", "unknown")
    return ExtractResult(
        parser_id=f"pymupdf4llm@{version}+cfg-{config_md5(parser_config)[:8]}",
        parsed_markdown=md,
        parser_config_md5=config_md5(parser_config),
        char_count=len(md),
    )
