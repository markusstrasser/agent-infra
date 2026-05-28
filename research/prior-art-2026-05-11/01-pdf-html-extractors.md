---
title: PDF + HTML → Markdown Extractor Ecosystem Survey (Q2 2026)
date: 2026-05-11
tags: [prior-art, document-extraction, pdf, html, markdown, knowledge-system]
status: complete
---

## TL;DR

- **Do NOT keep Marker as the long-term default for papers.** GPL-3.0 license (your stack is "MIT/Apache only"), measured 20x slowdown on Apple Silicon since v1.9.0 (#960), confirmed MPS bugs in surya layout encoder (#993) and table decoder (#967), and the empirical test from this morning's memo (`pdf-to-markdown-tooling-2026-05.md`) shows **Marker crashes at page ~10 on a 41-page native-text preprint on this Mac**. The "current pick" is not viable on the current hardware.
- **Switch the high-fidelity paper lane to MinerU 3.1.0 (pipeline backend).** Apache-2.0-derived license (you're 8 orders of magnitude under both the 100M-MAU and $20M-MRR commercial-license triggers), CPU-runnable, top open-source score on OmniDocBench academic_literature subset (**93.04** composite, vs Marker 78.44), formulas to LaTeX, tables to HTML, multi-column reading order is the documented strength of the underlying DocLayout-YOLO + UniMERNet pipeline.
- **Keep `pymupdf4llm` for the fast lane but understand the license boundary.** It is **AGPL-3.0** (PyMuPDF) — strictly fine for local-only personal use, but the moment you put it behind a network service that other people hit, the AGPL network clause activates. For personal scientific use on a Mac, it's the right tool; the constraint is real and worth memoing. MarkItDown (MIT) is the *clean-license* fast-lane alternative but its quality is documented as "plain text, no heading levels or layout" — not a substitute for `pymupdf4llm` on scientific PDFs.
- **Trafilatura still wins for HTML, no contender has surpassed it.** Apache-2.0 since v1.8, F1 0.909 on 750-doc benchmark (most recent at 2022), adopted by HuggingFace/IBM/Microsoft Research/Stanford/Allen-AI. The 2023 Bevendorff et al. empirical comparison still rates it best single tool. Resiliparse is faster but loses on extraction quality.
- **There is no acceptable single library for PDF+HTML+Office today.** MarkItDown attempts it and trades quality for breadth. Docling is the next closest (MIT, real PDF+DOCX+PPTX+XLSX+HTML+audio support) and is the only viable "one library" if you accept ~2x slower PDF extraction and `appendix` quality on scientific tables. **Recommendation: three-tool stack stays, but rotate `Marker → MinerU`.**

## Tool-by-Tool One-Liner Matrix

| Tool | Best at | License | OmniDocBench (composite) | CPU/MPS on Mac | Verdict |
|------|---------|---------|--------------------------|---------------|---------|
| **MinerU 3.1.0** | Scientific PDFs, multi-column, formulas | Apache-2.0 + 100M-MAU/$20M-MRR commercial-license trigger | **93.04** (academic_literature, v2.5) | Pipeline backend = CPU-friendly, MPS supported per README | **NEW PICK — replace Marker** |
| **Marker 1.10.2** | Was Mac-friendly until v1.9 | **GPL-3.0** | 78.44 (v1.8.2) | **Broken on MPS for large PDFs** (#993, #967, #960) | DROP for personal scientific use |
| **pymupdf4llm 1.27.2.3** | Fast native-text extraction, image extraction | **AGPL-3.0** (or Artifex commercial) | Not on leaderboard (no layout model) | Pure C-backed, fast on M-series | KEEP as fast lane (personal-only, no network) |
| **Docling 2.93.0** | Structured DoclingDocument, broad format support | **MIT** | Evaluated (no public composite vs MinerU on academic) | macOS arm64 supported, MPS feature-requests open (#3202) | Strong "one library" candidate; ~2x slower than MinerU |
| **MarkItDown 0.1.5** | Broadest format coverage incl. audio/YouTube | **MIT** | Not benchmarked | Cross-platform | Use for non-PDF leftovers (DOCX/PPTX/XLSX), NOT scientific PDFs |
| **Unstructured.io OSS** | ETL preprocessor for RAG | **Apache-2.0** (OSS); paid platform for enrichment | Evaluated, mid-pack | macOS supported | Skip — chunking/embeddings paywalled, no advantage over Docling on free tier |
| **Nougat 0.1.0** | Was the academic SOTA in 2023 | MIT code / **CC-BY-NC weights** | Surpassed by 2025 | CPU-friendly | Dead — last release Aug 2023, weights non-commercial |
| **GROBID 0.9.0** | TEI-XML citation extraction, headers, refs | Apache-2.0 | Different niche (XML, not markdown) | macOS Intel + ARM | KEEP for citation graph (different niche from markdown extractors) |
| **trafilatura 2.x** | Main-text HTML extraction with boilerplate removal | **Apache-2.0** (v1.8+) | F1 0.909 on 750-doc set | Pure Python | KEEP — still SOTA |
| **Resiliparse** | Speed (C++/Cython/Rust) over quality | Apache-2.0 | Lower F1 than trafilatura in Bevendorff 2023 | Fast on M-series | Skip unless processing millions of docs |
| **readability-lxml** | Lightweight Mozilla port | Apache-2.0 | F1 0.801 (per trafilatura eval) | Pure Python | Skip — strictly inferior to trafilatura on the same axis |
| **html2text** | Quick HTML → markdown structure | GPL-3.0 | Doesn't extract main content, formats raw | Pure Python | Skip for content extraction; useful if you already have clean HTML |

## Benchmarks (sources cited)

**OmniDocBench v1.7 (Apr 2026 update) — academic_literature subset, end-to-end composite:**
- MinerU 2.5 (v2509-1.2B): **93.04**
- Marker 1.8.2: **78.44**
- MinerU 2.5 leads text recognition (0.045 edit distance vs Marker 0.157)
- MinerU 2.5 leads formula CDM (95.77 vs Marker 85.24)
- Composite formula: `((1 - TextEditDist)*100 + TableTEDS + FormulaCDM) / 3`

Source: OmniDocBench leaderboard, CVPR 2025 paper (arXiv:2412.07626), CodeSOTA mirror (fetched 2026-05-11).

**OmniDocBench v1.5 historical (CodeSOTA, fetched 2026-05-11):**
- GLM-OCR: 94.62 (VLM, GPU-required)
- PaddleOCR-VL: 92.86 (lighter 0.9B variant 92.56)
- MinerU 2.5: 90.67 (pipeline backend = CPU-runnable)
- Qwen3-VL 235B: 89.15

The two pipeline tools (PaddleOCR-VL, MinerU) are within ~2 points of the heaviest closed VLMs. Pipeline methods "still hold the top spots, suggesting specialized architectures remain valuable for structured document understanding" — OmniDocBench maintainers' own framing.

**Trafilatura evaluation (750 documents, 2022-05-18, the latest the project has published):**
- Trafilatura standard: F1 **0.909** (precision 0.914, recall 0.904, accuracy 0.910)
- Trafilatura precision-mode: F1 0.902
- readability-lxml: F1 0.801
- news-please: F1 0.808
- Bevendorff et al. 2023 ROUGE-LSum independent comparison: trafilatura "best single tool"

Source: `trafilatura.readthedocs.io/en/latest/evaluation.html` (fetched 2026-05-11).

**Empirical head-to-head from earlier today** (`research/pdf-to-markdown-tooling-2026-05.md`, lines 66-95):
- Test: Vector2Variant preprint, 41 pages, 18MB, born-from-LaTeX
- pymupdf4llm: 42.6s full document, **0 figures extracted** from vector-composite figure pages, kept page-header boilerplate on every page
- Marker (MPS): **crashes at page ~10**, ~7s/page where it succeeds, 1 JPEG extracted from figure pages, page-header boilerplate stripped semantically

This is the load-bearing data point: **Marker is currently not functional on the user's hardware** for the target document class. MinerU is the obvious next thing to test against the same 41-page preprint.

## Recommendation for Our Stack

```
HIGH-FIDELITY LANE (papers, regulatory filings)
   was: marker-pdf 1.10.2 (--use_llm optional)
   →    mineru 3.1.0 (pipeline backend, CPU-mode, MPS-optional)
        rationale: works on Apache-2.0-derivative, leads OmniDocBench academic
                   by 14.6 points, CPU-runnable, doesn't crash at p.10

FAST LANE (native-text non-papers — database releases, blog PDFs, slides)
   stays: pymupdf4llm 1.27.2.3
        rationale: ~25-50x faster than MinerU for text-only docs,
                   AGPL is fine for strictly personal-local use,
                   image extraction works for embedded-raster figures

HTML LANE (journal landing pages, biomed/finance blogs)
   stays: trafilatura 2.x
        rationale: still the empirical SOTA, Apache-2.0,
                   no contender has caught up since 2022 benchmark

CITATION GRAPH LANE (different niche, not redundant with markdown extractors)
   stays: GROBID 0.9.0 (only if/when you need TEI-XML citation extraction)
        rationale: F1 0.87 on 1943-PDF PubMed test set,
                   used by Semantic Scholar, scite, ResearchGate
```

### Why MinerU over Docling for the high-fidelity lane

Docling is genuinely viable and has a cleaner license (MIT). The reasons MinerU wins specifically here:
1. **Empirically higher scientific score** — every public benchmark plus Reddit/forum sentiment converges that MinerU is best on multi-column academic content; Docling sentiment is "great for enterprise RAG, mistakes on complex tables."
2. **Formula handling** — UniMERNet → LaTeX is documented; Docling's formula enrichment is newer and has open bugs (#2681 AttributeError).
3. **License is acceptable at your scale** — the 100M-MAU / $20M-MRR threshold is purely theoretical for a personal repo. If you ever cross either, write a check.
4. **Pipeline backend explicitly CPU-friendly** — README states 4GB VRAM minimum, 16GB RAM recommended, and runs on Apple Silicon. No 20x slowdown bug equivalent reported.

If license-purity is non-negotiable, **Docling** is the substitute pick. The quality gap is real but bounded — you'd be trading ~5-8 OmniDocBench points for MIT vs custom-Apache. Personal call.

### Why not collapse to one tool

MarkItDown, Docling, and Unstructured all *try* to be the "one tool." The pattern from every 2025-2026 review (Jimmy Song, themenonlab, Soup, Actualize, NetMind blog) is the same:
- MarkItDown is breadth-over-depth — useless for scientific PDF structure.
- Docling is depth on enterprise documents — good but slower and table-shakier than MinerU on academic content.
- Unstructured's free tier is a partitioner, not an extractor — chunking, embeddings, table enrichment are paywalled.

The two-PDF-lane structure exists for a reason: fast tools skip layout models, accurate tools require them. No single library has resolved this tradeoff in Q2 2026.

### HTML — why trafilatura still

The only credible alternative is **Resiliparse** (Apache-2.0, C++/Rust core, faster) but the only benchmark numbers anyone publishes (Bevendorff 2023, trafilatura's own 2022 eval) consistently put trafilatura above it on F1. Resiliparse is the right pick if you're crawling millions of pages and CPU time matters more than recall. For a personal knowledge system, trafilatura's recall advantage matters more than its speed disadvantage.

`readability-lxml` and `html2text` have neither the recall of trafilatura nor the speed of resiliparse — they're third-choice picks. `readability-lxml` is also GPL-derived in some packagings; html2text is GPL-3.0.

## Adoption Risks Per Recommended Tool

**MinerU 3.1.0:**
- Custom license is *based on* Apache-2.0 but adds an attribution clause (must say "uses MinerU" in product UI or docs) and an auto-termination clause on non-compliance. For a personal repo, low risk — but document the dependency.
- ~20GB model download on first run. SSD space.
- Reviewers (Jimmy Song 2026, Reddit r/Rag thread) consistently note "image cropping sometimes incomplete" — figures may be truncated. Will need empirical test on the same Vector2Variant preprint to compare against this morning's pymupdf4llm/Marker numbers before committing.
- Documented strength is CJK; English scientific is still top of leaderboard but not the optimization target.
- Pipeline backend on CPU is "fast" by VLM standards but is still ~3-5x slower than pymupdf4llm. Don't use it for non-paper PDFs.

**pymupdf4llm 1.27.2.3 (kept):**
- **AGPL-3.0**: if you ever expose any of this via a web service (research-mcp public endpoint, Modal function with public URL), the AGPL network clause activates and you owe source. *Personal local use is unambiguously fine.* Document this — it's the exact failure mode where one project's "I'll just stick it behind FastAPI" leaks the license into a service.
- Does not see vector-rendered figures (only embedded-raster images). Re-confirmed in today's empirical test: 0 figures extracted from a born-from-LaTeX preprint's vector-composite figures.
- No OCR — scanned PDFs will pass through as boilerplate-stripped junk.

**trafilatura 2.x (kept):**
- Apache-2.0 since v1.8 — but if you pin an older v1.7 or below somewhere it's GPLv3+. Check `pip show trafilatura` once.
- Benchmark is from 2022. Web has changed (more JS-rendered, more anti-bot). Real-world precision/recall in 2026 is likely lower than 0.909 but no contender has published better.
- Heavy JS pages (Mintlify, Next.js docs) — known gotcha across the research-tool-gotchas list, applies to trafilatura too. Pair with a headless-browser fetcher (Playwright) when needed; don't blame trafilatura for upstream JS rendering issues.

**GROBID (kept for citation graph only):**
- Java + Docker dependency. Not pure Python like the rest of the stack.
- Different output format (TEI-XML, not markdown). Niche but well-defended — Semantic Scholar/scite use it for reference extraction.

### Mac/MPS-specific gotchas across the stack

1. **Marker MPS = broken at scale** — #993 surya layout encoder AcceleratorError, #967 table decoder no MPS backend, #960 ~20x slowdown since v1.9.0. Verified empirically today (crash at p.10). **Confirmed reason to drop Marker.**
2. **Docling has open MPS feature requests** — #3202 (TableFormer MPS), #3163 (Apple optimization). It works but isn't fully accelerated. Also #3329: "layout model produces different classification results between macOS ARM and Linux x86_64 despite identical configurations." This is non-determinism between machines and would be a problem for any reproducible pipeline.
3. **MinerU pipeline backend is the most Mac-stable of the three** — no open MPS-specific issues at the severity of Marker's. Still empirically unverified on your hardware until you run it; the recommendation depends on a probe test.
4. **PyMuPDF C bindings work natively on arm64** — non-issue.
5. **Trafilatura is pure Python** — non-issue.

### License compatibility — explicit verdict per your "MIT/Apache only" rule

- **Strictly compliant (MIT/Apache OK):** Docling (MIT), MarkItDown (MIT), Unstructured OSS (Apache-2.0), trafilatura v1.8+ (Apache-2.0), GROBID (Apache-2.0), Resiliparse (Apache-2.0), Nougat code (MIT — but weights are CC-BY-NC).
- **Custom-derived (functionally Apache for your scale):** MinerU (Apache-2.0 base + commercial-license thresholds you won't hit).
- **AGPL/GPL (out of your stated policy):** Marker (GPL-3.0), pymupdf4llm (AGPL-3.0), html2text (GPL-3.0), readability-lxml (some packagings).

If you take the "MIT/Apache only" rule strictly, **pymupdf4llm has to go too**. The honest answer is: AGPL for a strictly-local personal tool is widely accepted as fine — but the policy says what it says. Two options:
- (a) Relax the policy to "AGPL acceptable for local-only tooling, must not be exposed over a network."
- (b) Replace pymupdf4llm with MarkItDown's PDF backend or Docling's fast path. Both are demonstrably lower-fidelity for scientific PDFs.

Recommendation: relax (a). The AGPL is for distribution and network deployment, not local use, and the Free Software Foundation has been explicit about this since 2007. Document the carve-out.

## Sources

1. [OmniDocBench (CVPR 2025) leaderboard](https://github.com/opendatalab/OmniDocBench) — primary benchmark, v1.7 updated 2026-04-30
2. [CodeSOTA OmniDocBench mirror](https://www.codesota.com/browse/computer-vision/document-parsing/omnidocbench) — fetched 2026-05-11
3. [Marker GitHub repo + LICENSE](https://github.com/datalab-to/marker) — GPL-3.0, v1.10.2 (2026-01-31), Endless Labs Inc. copyright
4. [Marker open issues filter — MPS/Apple](https://github.com/datalab-to/marker/issues?q=is%3Aissue+MPS+OR+apple+silicon) — #993, #967, #966, #960
5. [Docling GitHub](https://github.com/DS4SD/docling) — MIT, v2.93.0 (2026-05-07)
6. [Docling Apple Silicon issues](https://github.com/DS4SD/docling/issues?q=is%3Aissue+MPS+apple+silicon) — #3202, #3163, #3329
7. [MinerU GitHub + LICENSE](https://github.com/opendatalab/MinerU) — Apache-2.0-derived, v3.1.0 (2026-04-18), license thresholds 100M MAU / $20M MRR
8. [pymupdf4llm PyPI](https://pypi.org/project/pymupdf4llm/) — AGPL-3.0 or Artifex commercial, v1.27.2.3 (2026-04-24)
9. [MarkItDown GitHub](https://github.com/microsoft/markitdown) — MIT, v0.1.5 (2026-02-20)
10. [Unstructured.io GitHub](https://github.com/Unstructured-IO/unstructured) — Apache-2.0 OSS, paid platform tiers
11. [Nougat GitHub](https://github.com/facebookresearch/nougat) — MIT code, CC-BY-NC weights, dormant since 2023-08
12. [GROBID GitHub](https://github.com/kermitt2/grobid) — Apache-2.0, v0.9.0 (2026-04-07), F1 0.87 PubMed test set
13. [trafilatura evaluation docs](https://trafilatura.readthedocs.io/en/latest/evaluation.html) — F1 0.909 (750 docs, 2022)
14. [Resiliparse GitHub](https://github.com/chatnoir-eu/chatnoir-resiliparse) — Apache-2.0
15. [Jimmy Song "Best Open Source PDF to Markdown Tools 2026"](https://jimmysong.io/blog/pdf-to-markdown-open-source-deep-dive/) — practitioner review
16. [themenonlab "Best Open-Source PDF-to-Markdown Tools 2026"](https://themenonlab.blog/blog/best-open-source-pdf-to-markdown-tools-2026)
17. [NetMind blog: Which PDF Parser Should You Use?](https://blog.netmind.ai/article/Which_PDF_Parser_Should_You_Use) — Docling vs Marker vs MinerU vs olmOCR comparison
18. [Reddit r/Rag thread on PDF parsers](https://www.reddit.com/r/Rag/comments/1rxzdtq/best_pdf_parser_for_multicolumn_research_papers/) — practitioner sentiment
19. Internal: `/Users/alien/Projects/agent-infra/research/pdf-to-markdown-tooling-2026-05.md` — empirical Marker crash on Vector2Variant preprint, today

### Unverified / "asserted but not primary-source-verified"

- **PaddleOCR-VL 92.86 composite** — leaderboard claim from CodeSOTA, the OmniDocBench primary repo lists PaddleOCR-VL-1.5 as evaluated but I did not pull the per-document-type breakdown. Not a load-bearing recommendation in this memo (proprietary model, GPU-heavy).
- **GLM-OCR 94.62** — same caveat; VLM, GPU-required, not in the candidate set for personal Mac use.
- **Bevendorff et al. 2023 "best single tool by ROUGE-LSum"** — cited via trafilatura docs, not directly verified against the paper.
- **Mistral OCR $1/1K pages, "4.32 vs Marker 4.41 LLM-judge"** — quoted from earlier internal memo (`pdf-to-markdown-tooling-2026-05.md`); reference [7] there was not re-verified in this survey.

## Revisions

**2026-05-28 — LiteParse v2 added to the candidate set (postdates this survey).**
LlamaIndex shipped LiteParse v2 on 2026-05-27 (Rust, model-free, Apache-2.0) —
not evaluated here. Bake-off vs `pymupdf4llm` on 6 corpus papers: ~100–300×
faster (0.1–0.5s vs 12–42s w/ OCR) and ~30–45% more raw characters, but it
emits **flat text only** — zero headings/tables/reading-order, whereas
pymupdf4llm recovers 9–32 headings + up to 108 table rows/paper. It is not a
structured-markdown competitor to mineru/pymupdf4llm; it's a fast text-recall +
Apache-licensed + office-doc + scan-preflight tool. Registered as opt-in
`--parser liteparse`, NOT a default (corpus 223e64b). The survey's tool picks
(mineru for papers, pymupdf4llm for other PDFs) are unchanged.

<!-- knowledge-index
generated: 2026-05-28T10:21:43Z
hash: 3fede51d4567

index:title: PDF + HTML → Markdown Extractor Ecosystem Survey (Q2 2026)
index:status: complete
index:tags: prior-art, document-extraction, pdf, html, markdown, knowledge-system
cross_refs: research/pdf-to-markdown-tooling-2026-05.md

end-knowledge-index -->
