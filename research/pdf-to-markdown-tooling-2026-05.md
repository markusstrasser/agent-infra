## PDF → LLM-Friendly Markdown Tooling — Research Memo

**Question:** What tooling do we have / should we use to convert PDFs to LLM-friendly markdown with images extracted to a folder?
**Tier:** Standard | **Date:** 2026-05-11

### Ground Truth — What's Already Installed

Local inventory (`uv tool list`, `~/Projects/*`, grep across MCPs/skills):

| Where | What | Image extraction? |
|---|---|---|
| `research-mcp/src/research_mcp/papers.py` | **Gemini API** primary + **PyMuPDF (fitz)** raw-text fallback | No — text only |
| `~/.claude/skills/skill-authoring/EXAMPLES.md` | `pdfplumber` (referenced as example) | No |
| `uv tool list` | No marker, mineru, docling, olmocr, pymupdf4llm installed | — |

So today: text-only via Gemini, no image-folder pipeline anywhere.

### Claims Table — Current Best-in-Class (May 2026)

| # | Tool | Image folder? | OCR / scanned? | Speed | Install | Status |
|---|---|---|---|---|---|---|
| 1 | **Marker** (`datalab-to/marker`) | Yes — writes images to output dir alongside `.md`, with relative links | Yes (Surya OCR; GPU/MPS/CPU) | ~2 s/page (MPS) | `pip install marker-pdf` | VERIFIED [1][3] |
| 2 | **PyMuPDF4LLM** | Yes — `write_images=True`, `image_path=...` parameters | No (no OCR — native-text PDFs only) | Fastest, CPU-only | `pip install pymupdf4llm` | VERIFIED [4][6] |
| 3 | **MinerU** (`opendatalab/mineru`) | Yes, but reviewers note "sometimes crops images incompletely" | Yes (PaddleOCR + custom layout) | Fast, GPU-favored | `pip install mineru[core]` | VERIFIED [1][2] |
| 4 | **Docling** (IBM) | Yes (structured `DoclingDocument`, image refs preserved) | Yes | ~4 s/page — **slowest** of the four | `pip install docling` | VERIFIED [2][5] |
| 5 | **Mistral OCR API** | Yes (returns image dict) | Yes (best-in-class on some layouts) | API latency; ~$1 / 1K pages | API key | VERIFIED [7][8] |
| 6 | **olmOCR** (Allen AI) | Yes (markdown + per-page assets) | Yes; VLM-based | GPU heavy | `pip install olmocr` | [TRAINING-DATA] — not surfaced in 2026 reviews above |

### Benchmark Picture (LLM-as-judge across 375 docs, [7])
Marker **4.41** > Mistral OCR **4.32**. MinerU 2.5 leads OmniDocBench at **86.2** on layout-heavy CJK / complex docs [1].

### Recommendation — Two-Tier Default

**Tier A — native-text PDFs (95% of papers you grab from journals/arXiv):**
**`pymupdf4llm`**. Already adjacent to what `research-mcp` uses (PyMuPDF is the fallback), CPU-only, ~zero install footprint, native `write_images` / `image_path` support. Fastest path to "markdown + `./images/page-3-fig-1.png` linked inline."

```python
import pymupdf4llm
md = pymupdf4llm.to_markdown("paper.pdf", write_images=True, image_path="paper_images/", image_format="png", dpi=200)
```

**Tier B — scanned / complex-layout / multi-column / tables that matter:**
**`marker-pdf`** with MPS on this Mac. Image extraction is on by default; `--output_format markdown` writes `out/paper/paper.md` + `out/paper/*.png`. For the worst documents, add `--use_llm` and point it at Gemini (already wired into `research-mcp`).

```bash
uv tool install marker-pdf
marker_single paper.pdf --output_dir out/ --output_format markdown
# or with LLM cleanup:
marker_single paper.pdf --output_dir out/ --use_llm --llm_service marker.services.gemini.GoogleGeminiService
```

### What's Uncertain / Deferred Alternatives

- **MinerU** — measurably best on CJK + OmniDocBench, but image cropping issues reported. Reach for it only if Marker fails on a specific layout class. Found, deferred.
- **Docling** — semantic `DoclingDocument` is valuable for RAG hierarchies but ~2× slower than Marker; not worth it for "give me a markdown file." Found, deferred.
- **Mistral OCR** — paid, slightly worse than Marker on the cited benchmark. No reason to use over Marker unless you specifically want zero local install. Found, deferred.
- **Current Gemini-via-`research-mcp` path** — gives clean text but **discards images entirely**. If `papers.py` should grow image-folder support, the natural extension is to call `pymupdf4llm.to_markdown(..., write_images=True)` and keep Gemini for text-quality cleanup.

### Anti-Patterns to Avoid

- Don't install all four "to compare" — pick by tier, install one. Maintenance > setup cost.
- Don't reach for Mistral OCR or LlamaParse for personal-use conversion; both are paid APIs solving a problem your local M-series Mac can do for free with Marker.

---

## Empirical Head-to-Head (2026-05-11)

**Test paper:** *Vector2Variant: Discovery of Genetic Associations from ML Derived Representations* (Sooknah et al., medRxiv 2026.04.10.26350624) — 41-page bioRxiv-style preprint, 18MB, born-from-LaTeX with vector-composite figures.

**Setup:** `uv pip install pymupdf4llm marker-pdf` → pymupdf4llm 1.27.2.3, marker-pdf 1.10.2, surya-ocr 0.17.1, torch 2.11.0. M-series Mac.

### Numbers

| Metric | pymupdf4llm | marker (MPS) |
|---|---|---|
| 41 pages (full) — time | **42.6 s** (incl. Tesseract OCR on 8 pages) | ✗ crashes at page ~10 |
| 3 pages (text only, 0-2) — time | **0.8 s** | 21 s (+~13 s model load) |
| 1 page (figure page, 4) — time | 2.9 s | 19 s |
| 1 page — chars produced | 2,821 | 2,640 |
| 1 page — **figures extracted** | **0** | **1 × 72KB JPEG** |
| 1 page — image refs in `.md` | 0 | `![](_page_4_Figure_2.jpeg)` |
| Model load on first run | none | ~13 s (Surya layout + OCR models) |
| Install size | tiny (PyMuPDF C lib only) | ~3 GB (torch + surya + tesseract) |

**Speed:** pymupdf4llm is **~25–50× faster** for text. Marker pays a fixed ~13 s model-load tax then ~7 s/page.

### Image extraction — the categorical difference

This paper's Figure 1 is **rendered as vector primitives**, not a stored raster image object. Result:

- **pymupdf4llm** sees no image objects → extracts nothing → markdown has no figure reference. It only finds embedded raster images (logos, scanned inserts). On the full 41-page run it grabbed 9 trivial images totalling 33 KB — license badges and similar, no actual figures.
- **marker** renders the page to pixels, runs Surya layout detection, identifies the bbox as a `Figure` block, crops to JPEG, saves it, and inserts the markdown reference. Same goes for tables (`Table` block → rendered HTML inline).

If you want the figures of a typical LaTeX-built paper, **only marker delivers**. pymupdf4llm's `write_images=True` is the right knob for the wrong target — it dumps embedded image objects, not visually-detected figure regions.

### Output quality — same first 3 pages

Both produce correct text. Differences:

| Aspect | pymupdf4llm | marker |
|---|---|---|
| Repeated page-header boilerplate ("medRxiv preprint doi:…") | **Kept on every page** | **Stripped** (semantic `PageHeader` block) |
| Citation links | Flat `[1]`, `[2–5]` | Anchored `[\[1\]](#page-31-0)` |
| Italics | `_phenotype engineering_` | `*phenotype engineering*` |
| Super/subscripts | `[1*]`, ugly `_**[†]**_` | clean `<sup>1</sup>`, `<sup>†</sup>` |
| Semantic block types | none | Spans/Lines/Text/SectionHeader/PageFooter/Footnote in `paper_meta.json` |
| Tables | flat text | rendered as HTML in markdown |

### Marker's "extra LLM" — what `--use_llm` actually does

Marker is a Surya-based ML pipeline by default (no LLM). `--use_llm` is **optional, opt-in**, adds a post-processing pass through Gemini/Claude/OpenAI/Ollama via these processors:

- `LLMTableProcessor` — fixes mangled tables
- `LLMEquationProcessor` — fixes math
- `LLMImageDescriptionProcessor` — generates a caption for each extracted figure (great for RAG)
- `LLMPageCorrectionProcessor` — full-page rewrite for messy layouts
- `LLMComplexRegionProcessor`, `LLMHandwritingProcessor`, `LLMFormProcessor`, …

Token counts surface in `paper_meta.json` per page (`llm_request_count`, `llm_tokens_used`). Pick provider via `--llm_service marker.services.gemini.GoogleGeminiService` (or `.claude`, `.openai`, `.ollama`).

### The MPS gotcha (real, hit it during this test)

With torch 2.11 + surya 0.17.1, marker crashes on Apple Silicon GPU with `torch.AcceleratorError: index N is out of bounds` during Surya layout encoder. **Root cause:** PyTorch MPS bug in boolean-masked indexing in `surya/common/surya/__init__.py:embed_ids_boxes_images` and in `.max().item()` on small tensors. Tracked at [datalab-to/marker#993](https://github.com/datalab-to/marker/issues/993).

**Workarounds tested here:**

| Approach | Result |
|---|---|
| `TORCH_DEVICE=cpu` | Works, ~10× slower (≈70 s/page on this hardware per upstream report) |
| `PYTORCH_ENABLE_MPS_FALLBACK=1` | Does **not** fix it (the buggy op is "supported", just wrong) |
| `--page_range 0-2` (chunks of 3) | Works reliably on MPS |
| `--page_range 0-9` (chunks of 10) | Crashes ~30% of the time |
| Patching `.max().item()` → `.cpu().max().item()` in surya | Partial fix; deeper bug in image-token boolean mask still fires on figure-heavy pages |

**Practical recipe for a 41-page paper today:** loop `marker_single ... --page_range $i-$((i+2))` in chunks of 3 and concat the markdowns. Or accept CPU speed.

### Verdict (revised after measurement)

- **Use pymupdf4llm** for fast bulk text. It is genuinely 25–50× faster, runs anywhere, no GPU drama. **Skip if you need figures** — its `write_images` only grabs embedded raster objects, which most academic PDFs do not contain.
- **Use marker** when you need figures-as-files-with-references, table HTML, or `--use_llm` cleanup. Budget the install (~3 GB), the model load (~13 s), and the MPS instability. Run in 3-page chunks until upstream fixes #993, or accept CPU.
- **For `research-mcp`:** keep the current Gemini-for-text path; add marker (chunked) as an optional `--with-figures` mode that writes to a sibling `figures/` dir. pymupdf4llm doesn't add anything we don't already get from PyMuPDF + Gemini.

### Artifacts on disk

- `/tmp/pdf-bench/out_pymupdf4llm/paper.md` — 130 KB, full 41 pages
- `/tmp/pdf-bench/out_pymupdf4llm/images/` — 9 trivial PNGs (33 KB total)
- `/tmp/pdf-bench/out_marker_fig/paper/paper.md` — page 4 with `![](_page_4_Figure_2.jpeg)`
- `/tmp/pdf-bench/out_marker_fig/paper/_page_4_Figure_2.jpeg` — 72 KB, actual Figure 1 of the paper

### Sources

1. [Best Open-Source PDF-to-Markdown Tools in 2026 — Menon Lab](https://themenonlab.blog/blog/best-open-source-pdf-to-markdown-tools-2026)
2. [Jimmy Song — Marker vs MinerU vs MarkItDown (2026)](https://jimmysong.io/blog/pdf-to-markdown-open-source-deep-dive/)
3. [datalab-to/marker — GitHub](https://github.com/datalab-to/marker)
4. [PyMuPDF4LLM docs — write_images / image_path](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/)
5. [PDF to Markdown — Mistral vs Docling implementation (Pappé)](https://felix-pappe.medium.com/pdf-to-markdown-simplified-implementation-and-comparison-of-mistral-and-docling-5c70b6f9a8f0)
6. [pymupdf/pymupdf4llm — GitHub](https://github.com/pymupdf/pymupdf4llm)
7. [Parsio — Mistral OCR Tested vs Marker (LLM-judge, 4.32 vs 4.41)](https://parsio.io/blog/mistral-ocr-test-review/)
8. [Mistral OCR 3 launch — Mistral AI](https://mistral.ai/news/mistral-ocr-3)

<!-- knowledge-index
generated: 2026-05-11T03:47:27Z
hash: d72c2ef44e57


end-knowledge-index -->
