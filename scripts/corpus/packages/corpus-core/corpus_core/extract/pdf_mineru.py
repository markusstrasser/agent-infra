"""MinerU 3.x — high-fidelity scientific-PDF parser.

License: Apache-2.0 base + commercial-license trigger at 100M-MAU/$20M-MRR.
Drops in to replace Marker (GPL-3.0, broken on Apple Silicon at scale per
research/prior-art-2026-05-11/01-pdf-html-extractors.md).

Invocation: subprocess against the installed mineru CLI. Resolver order:
  1. $CORPUS_MINERU_BIN
  2. ~/.local/share/uv/tools/mineru/bin/mineru  (uv tool install location)
  3. shutil.which("mineru")
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


def _find_mineru_bin() -> str:
    candidates = [
        os.environ.get("CORPUS_MINERU_BIN", ""),
        str(Path.home() / ".local/share/uv/tools/mineru/bin/mineru"),
        str(Path.home() / ".local/bin/mineru"),
        shutil.which("mineru") or "",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    raise RuntimeError(
        "mineru not found. Install with: uv tool install mineru"
    )


def _mineru_version(bin_path: str) -> str:
    try:
        out = subprocess.check_output(
            [bin_path, "--version"], stderr=subprocess.STDOUT, text=True, timeout=15
        )
        m = re.search(r"(\d+\.\d+\.\d+)", out)
        if m:
            return m.group(1)
    except Exception:
        pass
    return "unknown"


def extract(
    pdf_path: Path,
    *,
    parser_config: Optional[dict] = None,
) -> ExtractResult:
    """Run mineru on `pdf_path`, return the resulting markdown + parser_id.

    parser_config supports:
        backend: "pipeline" (default) | "vlm-transformers" | "vlm-vllm-engine"
        method:  "auto" (default) | "txt" | "ocr"
        lang:    OCR hint, default "en"

    The pipeline backend is the Mac-friendly default. VLM backends are not
    bit-deterministic and produce different parser_id values — distinct
    parsed.<parser_id>/ dirs.
    """
    pdf_path = Path(pdf_path).resolve()
    bin_path = _find_mineru_bin()
    cfg = parser_config or {}
    backend = cfg.get("backend", "pipeline")
    method = cfg.get("method", "auto")
    lang = cfg.get("lang", "en")

    with tempfile.TemporaryDirectory(prefix="corpus-mineru-") as td:
        cmd = [
            bin_path,
            "--path", str(pdf_path),
            "--output", td,
            "--backend", backend,
            "--method", method,
            "--lang", lang,
        ]
        env = os.environ.copy()
        env.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
        subprocess.run(cmd, check=True, env=env, capture_output=True)

        # MinerU writes to <td>/<pdf_stem>/<backend>/{<stem>.md, <stem>_content_list.json, ...}
        stem = pdf_path.stem
        out_dirs = list(Path(td).glob(f"{stem}/*"))
        if not out_dirs:
            raise RuntimeError(
                f"mineru produced no output dir under {td} for {pdf_path}"
            )
        out_dir = out_dirs[0]
        md_path = out_dir / f"{stem}.md"
        if not md_path.exists():
            cands = list(out_dir.glob("*.md"))
            if not cands:
                raise RuntimeError(f"mineru produced no markdown under {out_dir}")
            md_path = cands[0]
        md = md_path.read_text(encoding="utf-8", errors="replace")

        # Capture content_list.json if present (MinerU's structured-block output)
        extras: dict = {}
        cl_path = out_dir / f"{stem}_content_list.json"
        if cl_path.exists():
            try:
                extras["content_list_block_count"] = len(json.loads(cl_path.read_text()))
            except json.JSONDecodeError:
                pass

    full_cfg = {"backend": backend, "method": method, "lang": lang, **cfg}
    cfg_md5 = config_md5(full_cfg)
    return ExtractResult(
        parser_id=f"mineru@{_mineru_version(bin_path)}+{backend}+cfg-{cfg_md5[:8]}",
        parsed_markdown=md,
        parser_config_md5=cfg_md5,
        char_count=len(md),
        extras=extras or None,
    )
