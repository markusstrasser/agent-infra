---
title: Scientific Corpus Libraries — Standalone Usability Audit
date: 2026-05-11
scope: PaperQA2, Aviary, OpenScholar, ASReview, pyzotero
question: Can any existing library serve as corpus_core foundation, or is hand-rolled correct?
---

# Scientific Corpus Libraries — Standalone Usability

## TL;DR

| Library | License | Standalone corpus? | Verdict |
|---|---|---|---|
| **PaperQA2** (`Future-House/paper-qa`) | Apache-2.0 | **Partial.** `Docs` class technically importable but extra="forbid" Pydantic with mandatory embedding/LLM coupling for default path. Metadata clients are the gem and ARE separable. | Adopt `clients/` pattern (or import directly); hand-roll the Docs container. |
| **Aviary** (`Future-House/aviary`) | Apache-2.0 | **No.** It's a "language agent gym" (env/task framework), not a corpus library. Irrelevant. | Skip. |
| **LDP** (`Future-House/ldp`) | Apache-2.0 | **No.** Agent framework (Language Decision Processes). No corpus module. | Skip. |
| **OpenScholar** (`AkariAsai/OpenScholar`) | Apache-2.0 | **No.** Research code organized as `run.py + retriever/ + training/ + src/`, dormant since 2025-08-13, no library API surface. Designed to reproduce a paper, not be imported. | Skip. |
| **ASReview** | Apache-2.0 | **No** for corpus management; **Yes** for a different problem (active-learning prioritization of titles/abstracts during screening). No DOI/PMID/PMCID dedup designed for. | Skip for corpus_core. Revisit only if/when triage queue becomes the bottleneck. |
| **pyzotero** | MIT-equivalent (BSD-3) | **Read-only client to Zotero's REST API.** Confirmed: not a corpus manager — it's an HTTP client. | Skip unless we choose Zotero-as-storage-backend (we won't; lock-in). |

## PaperQA2 deep-dive (the candidate)

### What `Docs` actually is

From `src/paperqa/docs.py` (722 lines) and `src/paperqa/types.py` (1384 lines):

```python
class Docs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID = Field(default_factory=uuid4)
    docs: dict[DocKey, Doc | DocDetails] = Field(default_factory=dict)
    texts: list[Text] = Field(default_factory=list)
    docnames: set[str] = Field(default_factory=set)
    texts_index: VectorStore = Field(default_factory=NumpyVectorStore)
    name: str = Field(default="default")
    deleted_dockeys: set[DocKey] = Field(default_factory=set)
```

Key observations:

1. **It IS structured as a corpus container.** Has `docs` dict keyed by `DocKey` (which defaults to MD5 content hash), `deleted_dockeys` for soft delete, `clear_docs()`, `delete(dockey)`, `_get_unique_name()` for disambiguation. The container semantics we want exist.

2. **DOI-based dedup is in there.** `compute_unique_doc_id(doi, content_hash)` in `utils.py` produces stable IDs. `DocDetails.lowercase_doi_and_populate_doc_id` validator normalizes DOIs and populates `doc_id`/`dockey`. This is good prior art.

3. **`Doc` extends `Embeddable` from `lmi`.** Not an in-house base — depends on FutureHouse's `lmi` package. To use `Doc` standalone you take on `lmi` as a transitive dep (which transitively depends on `litellm`, `openai`, `anthropic`, ...).

4. **`Docs.aadd()` default path makes 2 LLM calls per document**:
   - One to parse a citation string from peeked first chunk (line ~196)
   - One to extract structured DOI/title/authors (line ~228)
   - Both bypassable: pass `citation=` explicitly → skips call 1; set `parse_config.use_doc_details=False` → skips call 2. But the API is built around them.

5. **`texts_index: VectorStore = NumpyVectorStore`** is a mandatory field — `Docs` is conceptually a "documents + their text chunks + embedding index". You can't get just the doc registry without paying for the texts list and vector store machinery. `extra="forbid"` prevents subclassing extension fields easily.

### What lives on disk

PaperQA2 does NOT have an opinionated on-disk layout. `Docs` is a Pydantic model — you serialize with `docs.model_dump()`/`model_dump_json()` and the user picks where to put it. There is `paths.py` (config dir helpers) but no `corpus.save(dir)` / `corpus.load(dir)` library API. The agent path saves the whole Pydantic blob.

Practical implication: their persistence is "pickle/json the whole Pydantic tree". For a long-lived corpus with many sources, that's a single-blob model — fine for sessions, awkward for ours where each paper has its own directory.

### The `clients/` directory — this is the actual gem

`src/paperqa/clients/` is a mostly-standalone metadata enrichment layer:

- `crossref.py` — DOI → bibliographic record
- `openalex.py` — fallback / additional metadata
- `semantic_scholar.py` — S2 records, citation counts
- `unpaywall.py` — OA PDF location
- `retractions.py` — Retraction Watch lookup
- `journal_quality.py` — venue scoring
- `client_models.py` — `DocMetadataClient` orchestrator
- `client_data/` — bundled offline data (journal lists, etc.)

These hit external APIs, return `DocDetails`, and don't require an LLM at all. `DocMetadataClient.query(doi=...)` returns enriched metadata. **If we adopt anything from PaperQA2, it's this.** It's 90% the value at 10% of the coupling.

### Coupling map (importing what costs what)

| Want to use | Drags in |
|---|---|
| `Doc` (just the dataclass) | `aviary.core.Message`, `lmi.Embeddable`, `pybtex`, `tiktoken` |
| `Docs` container | All of above + `NumpyVectorStore` + LLM/embedding settings + `paperqa.settings` (which loads YAML/env config) |
| `DocMetadataClient` | `aiohttp`, the client modules; **no LLM, no embeddings** |
| `compute_unique_doc_id` (the dedup ID function) | Just `paperqa.utils` |
| `Doc` validators (DOI normalization, etc.) | `paperqa.types` + `lmi` + `pybtex` |

The dependency cone narrows sharply as you go down. Top of the table is "you've adopted PaperQA2 as a framework". Bottom is "you've imported a 10-line function".

### Maintenance and bus factor

- 8,469 stars, 864 forks, last push 2026-03-20, Apache-2.0, ~136 open issues.
- Edison Scientific spinout (Nov 2025) means commercialization arm is paid; open-source `paper-qa` is the freemium upstream. Pattern from prior research memo: "infrastructure open-sourced, domain agents closed behind Edison paywall." Open path likely continues; not zero-risk.
- Monorepo (Mar 2026) with PDF readers split out as separate packages (`paper-qa-docling`, `paper-qa-nemotron`, `paper-qa-pymupdf`, `paper-qa-pypdf`). Suggests they're thinking about pluggability — but they did NOT split out a `paper-qa-core` (data model only) from `paperqa` (the QA agent). The split they chose is along pluggable readers, not along corpus-vs-agent. That tells us where their boundaries are.

## Aviary / LDP

These are NOT corpus libraries. From prior research (`futurehouse-research.md`, 2026-03-19) confirmed by repo descriptions today:

- **Aviary** = "A language agent gym with challenging scientific tasks." Env framework with task definitions; the closest thing to "corpus" is the scientific task corpora used as benchmark fixtures (HotpotQA, LitQA2). No reusable document store.
- **LDP** = "Framework enabling modular interchange of language agents, environments, and optimizers." Agent/RL plumbing. No document store.

Confirmed mismatched scope. Skip both.

## OpenScholar (Allen AI / Akari Asai)

Repo layout: `run.py`, `src/`, `retriever/`, `training/`, `requirements.txt` (not `pyproject.toml`). This is the canonical signature of "PhD/postdoc research code published to reproduce a paper", not "library to be imported by your project". Last push **2025-08-13** — 9 months stale, no signs of being maintained as a library. No package on PyPI.

The interesting parts of OpenScholar (retrieval over 45M open-access papers, citation-attributable synthesis) live behind their retrieval index, which they don't ship. The repo gives you scripts to run their experiments, not a Pythonic corpus API. Skip.

## ASReview / Rayyan

ASReview is real software (895 stars, actively maintained, Apache-2.0, in `asreview/` package layout). But its problem domain is **screening prioritization during systematic reviews** — given 10K abstracts, learn which to read first using active learning. It owns:

- An import layer for RIS/BibTeX/CSV (and Rayyan, EndNote)
- A SQLite-backed project file (`.asreview` zip with state)
- Labeling UI / API
- Active learning model wrappers

What it does NOT own well:
- DOI/PMID/PMCID-canonical dedup as a first-class concern (it dedups within an import, not across sources over time)
- Non-paper sources (database releases, blog posts, software docs) — schema is paper-centric
- A long-lived corpus that grows from heterogeneous inputs

If we needed a triage queue over a growing inbox, ASReview's prioritization model would be relevant. As a base for *corpus_core* (canonical store + ID resolver), it's the wrong shape.

Rayyan is closed-source SaaS — not evaluated.

## pyzotero

Confirmed: pyzotero is a thin Python wrapper around the Zotero Web API (HTTP GET/POST against api.zotero.org). It's a *client*, not a *manager*. To use it as our backend we'd be using Zotero-the-service (or a self-hosted Zotero) as the storage of record — which introduces:

- Vendor lock-in to a small NPO
- Auth complexity (API keys per user)
- Latency on every read/write
- A schema designed for human reference managers (citation styles, collections, tags), not for sources like "GTEx v9 release" or "PharmGKB allele table snapshot"

Skip unless we explicitly want Zotero-as-source-of-truth.

## Verdict

**Hand-roll `corpus_core`, but cherry-pick from PaperQA2.** Specifically:

1. **Adopt the ID model.** Copy or import `paperqa.utils.compute_unique_doc_id(doi, content_hash)` and the DOI normalization validator from `paperqa.types.DocDetails`. This is well-trodden ground — re-deriving it produces the same answer 6 weeks later.

2. **Consider adopting `paperqa.clients` as an optional dependency** for metadata enrichment if we want Crossref/OpenAlex/S2/Unpaywall/Retraction lookups. The `DocMetadataClient` does NOT require LLM/embedding machinery and is the most leveraged piece of the codebase per LOC. Alternative: write thin Crossref/OpenAlex async clients ourselves (~200 LOC total) — they're standard REST. Adopt-vs-rewrite call depends on whether we'll use *all* of (Crossref + S2 + OpenAlex + Unpaywall + Retraction Watch) or just one.

3. **Do NOT adopt `Docs` as our corpus container.** Reasons:
   - `extra="forbid"` Pydantic with mandatory `texts_index: VectorStore` field means we can't extend it cleanly for non-paper sources (database releases, blog posts, software docs).
   - Hard dep on `lmi` (their LLM abstraction) which pulls in litellm and friends — large cone for a personal local-filesystem corpus.
   - In-memory model with whole-tree serialization. We want per-source directories so `git log <source>` works.
   - Their on-disk story is unopinionated; we don't gain a persistence layer by adopting.

4. **Source heterogeneity is the deciding factor.** PaperQA2's data model is paper-shaped (`Doc`/`DocDetails` with citation/DOI/journal/authors). Personal-corpus needs to also store: database releases (GTEx, PharmGKB, ClinVar snapshots), blog posts, software/method docs, internal notes. Trying to subclass `DocDetails` to fit these is more work than starting from a domain-appropriate base.

5. **Constitution Principle 8 ("filter by maintenance, not effort") applies.** Hand-rolling a corpus container is ~300-500 LOC for a single-user local-filesystem case. Adopting PaperQA2 wholesale buys ~5K LOC of features we mostly won't use + maintenance burden of tracking their CalVer releases. Maintenance budget says hand-roll.

### Recommended hybrid

```
corpus_core (hand-rolled, ~400 LOC):
  - Source base class (paper | database_release | webpage | notes | software_doc)
  - DOI/PMID/PMCID/content-hash dedup using compute_unique_doc_id pattern
  - Per-source directory layout (one source = one dir = one git-trackable unit)
  - Manifest file per source (YAML or JSON)

corpus_core.enrichment (optional):
  - Wrap paperqa.clients OR thin custom Crossref/OpenAlex clients
  - Decoupled from container — fed a DOI/PMID, returns metadata
```

If `paperqa.clients` proves heavy or has surprising deps, swap to ~150 LOC of `httpx` + `pydantic` calling the same APIs. The interface (DOI → metadata) is stable; the implementation is replaceable.

## What we'd lose by NOT adopting PaperQA2's corpus piece

Honestly: very little for our use case.

- **Lose: a battle-tested in-memory paper-only registry with a vector store baked in.** We don't want this; we want per-source directories and the vector store is a separate layer.
- **Lose: `Docs.aadd()` ergonomics** (point at a PDF, get citation parsed + metadata enriched + chunks embedded in one call). Convenient for QA UIs, but it bundles concerns we want separated. Easy to write a 50-line ingestion function that orchestrates the same steps explicitly.
- **Lose: their soft-delete (`deleted_dockeys`) and docname-disambiguation logic.** Both <30 LOC each to reimplement.
- **Lose: implicit alignment with PaperQA2 users.** Nobody else is building on top of our corpus_core, so this is zero-value.

What we'd keep by importing selectively from `paperqa.utils` / `paperqa.clients`:
- The DOI normalization and unique-ID derivation logic (the bit that's actually a research artifact).
- Battle-tested metadata enrichment if we choose to take the dep.

## Contribute upstream?

Question is moot — there's nothing to contribute back to a personal-corpus-shaped fork of PaperQA2 because PaperQA2's authors do not want the paper-centric `Doc` model generalized to non-papers (that would break their QA agent's assumptions about citation strings). Their boundaries — confirmed by the package split they chose (PDF readers split out, `Docs` left tightly coupled to the agent) — say "we are an answer-questions-about-papers system, not a personal scientific corpus framework". Different product, fine to be different.

## Sources

- `Future-House/paper-qa` repo, default branch `main` as of 2026-05-11 (pushed 2026-03-20):
  - `src/paperqa/docs.py` (722 lines, contains `class Docs`)
  - `src/paperqa/types.py` (1384 lines, contains `Doc`, `DocDetails`, `Text`, `PQASession`, validators including `lowercase_doi_and_populate_doc_id`)
  - `src/paperqa/clients/` (Crossref, OpenAlex, Semantic Scholar, Unpaywall, Retractions, journal quality)
  - `packages/{paper-qa-docling,paper-qa-nemotron,paper-qa-pymupdf,paper-qa-pypdf}/` (the chosen pluggability boundary)
  - License: Apache-2.0, 8469 stars, 864 forks
- `Future-House/aviary` repo (260 stars, Apache-2.0, "language agent gym")
- `Future-House/ldp` repo (133 stars, Apache-2.0, agent framework)
- `AkariAsai/OpenScholar` repo (1471 stars, Apache-2.0, last push 2025-08-13 — dormant; `run.py + retriever/ + training/` layout = research code)
- `asreview/asreview` repo (895 stars, Apache-2.0, active; active-learning for screening prioritization — wrong shape for corpus_core)
- `urschrei/pyzotero` repo (1303 stars; HTTP client to Zotero Web API, not a corpus manager)
- Prior memo: `/Users/alien/Projects/meta/research/futurehouse-technical-analysis.md` (2026-03-19) and `futurehouse-org-scan-2026-04.md` (2026-04-02) — confirms Edison Scientific spinout pattern and CalVer release cadence.

<!-- knowledge-index
generated: 2026-05-11T07:30:07Z
hash: ca776bf3971b

title: Scientific Corpus Libraries — Standalone Usability Audit
cross_refs: research/futurehouse-technical-analysis.md

end-knowledge-index -->
