"""liteparse — fast, model-free PDF/office/image text extraction (Rust core).

License: Apache-2.0 — unlike pymupdf4llm (AGPL-3.0), safe to run server-side.

Output is flat, spatially-projected page text, NOT semantic markdown: no
heading levels, no table reconstruction, no equation markup, no multi-column
reading-order guarantees. For structured markdown on papers, use `mineru` or
`marker`. LiteParse's niche here is speed (0.05-0.5s/paper vs minutes on a GPU),
Apache licensing, office-doc support, and as a cheap text-layer preflight
(empty output ⇒ scanned/image PDF ⇒ route to mineru/marker).

OCR (scanned PDFs) needs a working Tesseract + tessdata; the pip wheel does NOT
reliably bundle it ("Failed to initialize Tesseract"). Treat OCR as unsupported
unless `ocr_server_url`/`tessdata_path` is configured via parser_config.

Install: `pip install liteparse` (or `corpus` extra `liteparse`).
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
    import liteparse  # type: ignore
    from liteparse import LiteParse  # type: ignore

    pdf_path = Path(pdf_path)
    config = dict(parser_config or {})
    config.setdefault("quiet", True)
    result = LiteParse(**config).parse(str(pdf_path))

    pages = list(result.pages)
    text = "\n\n".join(p.text for p in pages).strip()
    version = getattr(liteparse, "__version__", "unknown")
    return ExtractResult(
        parser_id=f"liteparse@{version}+cfg-{config_md5(parser_config)[:8]}",
        parsed_markdown=text,
        parser_config_md5=config_md5(parser_config),
        page_count=result.num_pages,
        char_count=len(text),
        extras={"has_text_layer": len(text) > 200},
    )
