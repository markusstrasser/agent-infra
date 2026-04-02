---
title: FutureHouse GitHub Org Scan — April 2026 Update
date: 2026-04-02
---

# FutureHouse GitHub Org Scan — April 2026 Update

**Date:** 2026-04-02
**Tier:** Standard
**Prior memo:** `futurehouse-technical-analysis.md` (2026-03-19, 7 repos, PaperQA2 architecture focus)

## What Changed Since March 2026

### Major: Edison Scientific Spinout + PaperQA3

FutureHouse spun out **Edison Scientific** in November 2025 as a for-profit commercialization vehicle. $70M seed at ~$250M valuation. [SOURCE: ucstrategies.com, intuitionlabs.ai]

- FutureHouse remains the nonprofit research org
- Edison operates **Kosmos** (the next-generation platform agent, successor to Robin) and exposes agents via the **Edison API** (`edison-client` Python package)
- The edison-client-docs repo (6 stars, created 2025-02-27, last push 2026-02-17) documents the API

**PaperQA3** is referenced in Edison's job types (`LITERATURE`, `LITERATURE_HIGH`) but exists only as a hosted service — no open-source repo. The open-source `paper-qa` repo remains PaperQA2 (CalVer since Dec 2025, latest release `v2026.03.18`). PaperQA3 appears to be the multimodal + reasoning-enhanced variant running inside Edison's platform. No technical paper or separate codebase published.

**Kosmos platform claims** (from Edison marketing, not independently verified):
- 292 independent analysis trajectories/day
- Reads 1,500 papers, runs 42K+ lines of code per run
- 80% reproducibility rate, 79.4% accuracy vs human review
- "6 months of research in 24 hours"

### Repo Inventory (15 public repos, was 7 in prior memo)

| Repo | Stars | Last Push | Status | Notes |
|------|-------|-----------|--------|-------|
| **paper-qa** | 8,334 | 2026-03-20 | Active | CalVer, monorepo with pluggable PDF readers |
| **robin** | 289 | 2025-11-24 | Dormant | Multi-agent discovery (ripasudil finding) |
| **aviary** | 247 | 2026-03-18 | Active | Agent gym, v0.34.0 |
| **ether0** | 159 | 2025-10-26 | Dormant | 24B chemistry model, no recent activity |
| **ldp** | 127 | **2026-04-02** | Active | Agent framework, Python 3.14 support today |
| **LAB-Bench** | 103 | 2025-09-27 | Dormant | Biology benchmark, no updates in 6 months |
| **BixBench** | 85 | 2025-10-06 | Dormant | Computational biology benchmark, 205 questions from 60 notebooks |
| **LitQA** | 45 | 2024-12-18 | Dormant | Literature QA eval set (~250 questions) |
| **data-analysis-crow** | 44 | 2025-09-30 | Dormant | Jupyter-based data science agent |
| **WikiCrow** | 38 | 2024-10-24 | Dormant | Gene summary generation |
| **edison-client-docs** | 6 | 2026-02-17 | Low activity | API docs for Edison platform |
| **llm-client** | 2 | 2025-02-23 | Dormant | Internal LLM routing |
| **trl** | 1 | 2025-03-12 | Fork | HuggingFace TRL fork for RL training |
| **FH-Fellows-Tutorials** | 1 | 2025-09-19 | Dormant | Fellowship onboarding |
| **feathers** | 0 | 2025-12-06 | Internal | Design system |
| **SWE-bench** | 0 | 2024-07-24 | Fork | Upstream fork |

**New repos not in prior memo (8):** BixBench, LAB-Bench, LitQA, data-analysis-crow, edison-client-docs, trl fork, FH-Fellows-Tutorials, feathers. Of these, only BixBench and edison-client-docs are technically interesting.

### paper-qa: What's Actually New

The `paper-qa` repo moved to a **monorepo structure** with four pluggable PDF reader packages:
- `paper-qa-docling` — IBM Docling model-based reader (tables, figures, equations)
- `paper-qa-nemotron` — NVIDIA Nemotron-parse (model-based)
- `paper-qa-pymupdf` — PyMuPDF (fast, rule-based)
- `paper-qa-pypdf` — PyPDF (lightweight fallback)

Other changes since March memo:
- CalVer versioning (no more semver)
- Multimodal: media objects in contextual summarization, embedding space enrichment via LLM captions
- Non-English language support
- httpx consolidation (dropped aiohttp)
- ClinicalTrials.gov integration (`sources/clinical_trials.py`)
- Zotero and OpenReview contrib modules
- Retraction checking client (`clients/retractions.py`)
- LiteLLM monkeypatches module (compatibility layer)

The core RCS pipeline is unchanged. No MCP server in the official repo.

### ldp: Most Active Right Now

ldp (Language Decision Processes) had commits today (2026-04-02) — Python 3.14 support, torch 2.11.0. Active release cadence: v0.43.2 through v0.45.1 in the last 2 months.

Architecture: agents as POMDPs with natural language actions/observations. Key components:
- `SimpleAgent` with `init_state()` / `get_asv()` (action, state, value)
- Stochastic Computation Graphs for gradient-based training (differentiable agent parameters)
- Redis support for distributed instances
- Loosened action types (March 2026: actions can be plain `Message`, not just tool calls)

No MCP integration. No explicit RL training loop in the open-source code — that capability appears to live in Edison's closed platform.

### aviary: Stable

v0.34.0 (March 2026). Agent gym with scientific task environments. Recent work focused on API loosening (accepting `Message` type actions). Five reference environments documented in the arXiv paper (2412.21154). No new environments added recently.

### BixBench: New Benchmark Worth Noting

205 questions from 60 published Jupyter notebooks. Tests multi-step computational biology analysis: dataset exploration, code execution (Python/R/Bash), hypothesis generation. Apache 2.0. No public leaderboard yet. Stale since October 2025.

## Agent Architecture Summary (Platform vs Open Source)

| Component | Open Source | Closed (Edison) |
|-----------|------------|-----------------|
| Literature RAG | PaperQA2 (paper-qa) | PaperQA3 (multimodal, reasoning-enhanced) |
| Agent framework | ldp + aviary | Kosmos orchestrator |
| Chemistry | ether0 weights (HF) | Phoenix agent |
| Literature Q&A | - | Crow |
| Deep review | - | Falcon |
| Prior-work detection | - | Owl |
| Data analysis | data-analysis-crow (basic) | Finch |
| Multi-agent discovery | Robin (dormant) | Kosmos |

The strategic pattern: FutureHouse open-sources the infrastructure (ldp, aviary, paper-qa) but keeps the domain agents and orchestration closed. Edison monetizes the closed stack.

## What's Missing / Not Found

- **No MCP server** in any FutureHouse repo. A community MCP wrapper exists (`menyoung/paperqa-mcp-server`, 1 star, MIT, March 2026) but is trivial.
- **No PaperQA3 paper or open-source release.** The name appears only in Edison marketing and API docs.
- **No training loop code** in ldp despite the SCG (Stochastic Computation Graph) abstraction being designed for it. The actual RL training likely runs on Edison's internal infra.
- **Robin is dormant** (last push Nov 2025). The ripasudil finding was the showcase; Kosmos appears to be the successor.
- **ether0 dormant** since Oct 2025. Weights on HuggingFace but no active development.
- **No protein engineering agent** open-sourced (mentioned as planned in marketing).

## Transferable Patterns (Delta from March Memo)

1. **Pluggable PDF reader monorepo** — paper-qa's approach of packaging readers as separate pip-installable packages with a common interface. Clean pattern for optional heavy dependencies (Docling requires PyTorch, Nemotron requires NVIDIA APIs).

2. **CalVer for research tools** — Date-based versioning acknowledges that research tools evolve by capability accretion, not breaking API changes. Matches our own research-mcp evolution pattern.

3. **Clinical trials integration** — paper-qa added `clinical_trials.py` as a source alongside S2/Crossref/OpenAlex. Relevant for our research-mcp: ClinicalTrials.gov as a first-class data source alongside academic papers.

4. **Retraction checking** — `clients/retractions.py` as a standard pipeline stage. We do this via scite's editorial notices, but a dedicated client is cleaner.

## Assessment

The FutureHouse open-source ecosystem is **stable but not expanding**. The interesting work (PaperQA3, Kosmos, domain agents) is moving behind Edison's paywall. For our purposes:

- **paper-qa remains the best open-source literature RAG** — the monorepo/pluggable reader pattern is worth studying, but the core RCS pipeline (our main interest from March) hasn't changed.
- **ldp is actively maintained** but the training capabilities we'd want (RL loops, expert iteration) aren't in the open code.
- **Edison API** ($unknown/call) could be useful for benchmarking our research-mcp against a commercial baseline, but there's no public pricing.
- **BixBench** is a potential eval target if we extend to computational biology agent tasks.

Net: nothing in the open-source repos warrants immediate action. The March memo's transferable patterns (RCS pipeline, calibrated refusal, citation traversal) remain the most valuable extractions. Update the agent-memory reference with Edison/PaperQA3 context.

<!-- knowledge-index
generated: 2026-04-02T18:11:11Z
hash: b8078aa8e508

title: FutureHouse GitHub Org Scan — April 2026 Update

end-knowledge-index -->
