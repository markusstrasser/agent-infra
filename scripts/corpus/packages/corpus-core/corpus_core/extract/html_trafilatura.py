"""trafilatura — HTML → markdown.

License: Apache-2.0 since v1.8. Verified best-of-class on Bevendorff 2023
F1 benchmark; adopted by HuggingFace, IBM, Microsoft Research, Stanford.
"""
from __future__ import annotations

from typing import Optional

from . import ExtractResult
from ._common import config_md5


_DEFAULT_HTTP_HEADERS = {"User-Agent": "corpus-core/0.1 (+local)"}


def extract_from_bytes(
    html_bytes: bytes,
    *,
    parser_config: Optional[dict] = None,
    url: Optional[str] = None,
) -> ExtractResult:
    """Extract markdown from raw HTML bytes."""
    import trafilatura  # type: ignore

    cfg = parser_config or {}
    md = trafilatura.extract(
        html_bytes,
        output_format="markdown",
        include_links=cfg.get("include_links", True),
        include_tables=cfg.get("include_tables", True),
        with_metadata=cfg.get("with_metadata", True),
        url=url,
    ) or ""
    version = getattr(trafilatura, "__version__", "unknown")
    return ExtractResult(
        parser_id=f"trafilatura@{version}+cfg-{config_md5(cfg)[:8]}",
        parsed_markdown=md,
        parser_config_md5=config_md5(cfg),
        char_count=len(md),
    )


def fetch_and_extract(url: str, *, parser_config: Optional[dict] = None,
                      timeout: float = 30.0) -> ExtractResult:
    """Fetch URL via httpx and extract."""
    import httpx  # type: ignore

    r = httpx.get(url, timeout=timeout, follow_redirects=True,
                  headers=_DEFAULT_HTTP_HEADERS)
    r.raise_for_status()
    return extract_from_bytes(r.content, parser_config=parser_config, url=url)
