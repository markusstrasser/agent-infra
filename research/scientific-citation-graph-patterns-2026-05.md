## Scientific Citation Graph Patterns — Research Memo

**Question:** How do production scientific citation graphs (OpenAlex, Semantic Scholar, Scite, OpenCitations) model citances, classify citation intent, and store the graph? Which patterns transfer to a personal-scale shared papers store?

**Tier:** Standard | **Date:** 2026-05-11 | **Companion:** `~/Projects/agent-infra/.claude/plans/2026-05-11-shared-papers-store.md`

### Ground truth (already known from genomics codebase)

- `bundle_adjudicate.py` already consumes scite citation context with stance counts (supporting/contrasting/mentioning) via `citation_context_adapter.emit_for_source`. ANY-positive retraction across providers. No citance-level snippets exposed to the quorum today.
- Internal classifier doesn't exist; classification is delegated to scite via its MCP.

### Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|---|---|---|---|---|
| 1 | OpenAlex stores 257M works + 2.1B citation edges as a heterogeneous directed graph with `referenced_works: [OpenAlexID]` on each Work. Abstracts stored as **inverted-index** (word → positions) for legal reasons. | OpenAlex docs + arxiv 2205.01833 | HIGH | [docs.openalex.org/api-entities/works/work-object](https://docs.openalex.org/api-entities/works/work-object) | VERIFIED |
| 2 | Semantic Scholar Academic Graph (S2AG): 205M papers, 2.5B citation edges, monthly snapshots + open API. Surfaces SPECTER2 embeddings, citation classifications, field-of-study tags, TLDR summaries. | S2AG paper (Companion Proc. WWW 2022) | HIGH | [dl.acm.org/doi/10.1145/3487553.3527147](https://dl.acm.org/doi/10.1145/3487553.3527147) | VERIFIED |
| 3 | Scite trains a deep learning classifier over **citation statements** (the actual snippet around a citation marker) labeling each as supporting / contrasting / mentioning with confidence. 880M classified statements, 25M full-text articles parsed via **GROBID + biblio-glutton** pipeline. | Nicholson et al., QSS 2021 | HIGH | [direct.mit.edu/qss/article/2/3/882](https://direct.mit.edu/qss/article/2/3/882/102990/scite-A-smart-citation-index) | VERIFIED |
| 4 | CiTO (Citation Typing Ontology, SPAR family) defines `cito:cites` with **41 sub-properties** capturing factual + rhetorical intent: `cito:supports`, `cito:disagreesWith`, `cito:extends`, `cito:usesMethodIn`, `cito:obtainsSupportFrom`, `cito:reviews`, etc. | CiTO spec, J Biomed Semantics 2010 | HIGH | [sparontologies.github.io/cito/current/cito.html](https://sparontologies.github.io/cito/current/cito.html) | VERIFIED |
| 5 | `cito:supports` and `cito:obtainsSupportFrom` are **separate, non-inverse properties** — direction is load-bearing. Citation A→B with stance "A supports B" is not the same shape as "B is supported by A". | CiTO spec | HIGH | same | VERIFIED |
| 6 | OpenCitations COCI is the DOI-to-DOI index over Crossref's open citation data. Uses CiTO as the typing vocabulary. Free, downloadable as RDF dumps. | OpenCitations docs | HIGH | [opencitations.net](https://opencitations.net) | VERIFIED |
| 7 | All four production systems store edges in **columnar/relational** form (parquet snapshots, S3 dumps, monthly archives), not native graph DBs. Neo4j-style property graphs are conspicuously absent from the top-tier scholarly-graph stack. | OpenAlex on AWS, S2AG snapshots, OpenCitations RDF | HIGH | [registry.opendata.aws/openalex](https://registry.opendata.aws/openalex/) | VERIFIED |
| 8 | SPECTER2 (Allen AI, 2026) — citation-informed paper embeddings via transformer. API: `(paper_id, title, abstract) → 768-d vector`, batch ≤ 16. Adapts to multiple fields and task formats. | Allen AI blog 2026; Cohan et al. ACL 2020 | HIGH | [allenai.org/blog/specter2-adapting-scientific-document-embeddings](https://allenai.org/blog/specter2-adapting-scientific-document-embeddings-to-multiple-fields-and-task-formats-c95686c06567) | VERIFIED |

### Key Findings — what transfers, what doesn't

**1. CiTO is the right citance-type vocabulary, not a custom enum.**
Scite's 3-class (supporting/contrasting/mentioning) is a coarse projection of CiTO. For biomedical claims where the distinction between "method use", "data reuse", "result confirmation", and "interpretation extension" matters, CiTO's 41 sub-properties give real handles. The plan's normalized citance schema should store:
```
stance: "cito:supports" | "cito:disagreesWith" | "cito:usesMethodIn" | ... | null
stance_class: "supporting" | "contrasting" | "mentioning"   # scite 3-class projection
stance_confidence: 0.0–1.0
stance_source: "scite" | "local_classifier" | "operator"
```
The 3-class projection is what the quorum prompt and the gate logic key on; the CiTO sub-property is finer-grained context the operator (and a smarter quorum) can use.

**2. Direction is two edges, not one with a flag.**
OpenCitations explicitly models `cito:supports` and `cito:obtainsSupportFrom` as separate properties. Our `citances_in.jsonl` / `citances_out.jsonl` split aligns with this (each paper's directory holds both directions for locality). The DuckDB graph index should preserve direction; never collapse `A→B` and `B←A` into one symmetric edge.

**3. Columnar/relational storage at production scale validates DuckDB.**
None of the major scholarly graphs use Neo4j or other native graph DBs for primary storage. OpenAlex serves 2.1B edges from S3 parquet. S2AG ships monthly snapshots. OpenCitations distributes RDF dumps. The pattern: **edges are rows, queries are SQL with recursive CTEs for traversal**. At our personal-scale (100k–1M edges), DuckDB handles this trivially with sub-second graph traversal. Neo4j would be operational overhead with no query advantage.

**4. GROBID + biblio-glutton is the production reference-extraction pipeline; marker doesn't include it.**
Scite's pipeline parses PDFs with GROBID specifically because GROBID's bibliography parser produces structured reference entries that biblio-glutton then resolves to canonical IDs (DOI, PMID). Marker's strength is layout-aware text extraction; it doesn't resolve references to IDs out of the box. For `citances_out` extraction, the plan needs a **reference resolver step**:
- Parse marker's reference section (regex or LLM-tagged)
- Query Crossref / OpenAlex / PubMed by author + year + title to get back DOI/PMID
- Cache the resolution at `~/Projects/papers/<paper_id>/references_resolved.json`
- Only then construct `citances_out.jsonl` with `cited_paper_id` populated

**5. Inverted-index abstracts don't apply at our scale.**
OpenAlex stores inverted-index abstracts for legal reasons (can't redistribute publisher copyright). For our personal use of papers we've already downloaded, we have the full text in `parsed/paper.md`. Skip.

**6. SPECTER2 embeddings are valuable but out of scope for v1.**
Citation-informed paper embeddings would give us a "semantic similarity" edge type — "this paper is similar to that paper via vector cosine" — useful for cluster discovery and "show me related work I haven't read." But the API is rate-limited and the value is downstream of having the citation graph working. Defer to a future plan.

### What's Uncertain

- **CiTO classifier availability locally.** Scite's classifier is closed-source. Open alternatives (e.g., MultiCite, ACL 2022) exist but are pre-frontier. Practical recipe: use scite for stance via MCP; supplement with an LLM (Gemini Flash) for CiTO sub-property classification on a per-citance basis when finer signal is needed.
- **Resolution rate for marker → Crossref reference resolution.** GROBID + biblio-glutton claims ~90% resolution on biomedical literature. Marker's reference output quality has not been measured for this purpose; need a probe.

### Design implications applied to the plan

- Adopt CiTO sub-properties as the optional fine-grained stance field, with scite's 3-class as the always-populated coarse field.
- Keep `citances_in.jsonl` / `citances_out.jsonl` as separate directional edges per paper.
- Confirm DuckDB as the graph index; document the recursive CTE traversal pattern.
- Add a `references_resolved.json` artefact and a reference-resolver step to the ingest pipeline.
- Store stance confidence and source explicitly on every citance.
- Defer SPECTER2 / semantic-similarity edges to a future plan.

### Sources

1. [OpenAlex Work object schema](https://docs.openalex.org/api-entities/works/work-object) — referenced_works, inverted-index abstract, OpenAlexID schema
2. [OpenAlex paper (arXiv:2205.01833)](https://arxiv.org/abs/2205.01833) — full system description
3. [Scite paper, QSS 2021 (Nicholson et al.)](https://direct.mit.edu/qss/article/2/3/882/102990) — GROBID + biblio-glutton + deep learning classifier, 1.6B+ statements at publication
4. [CiTO spec](https://sparontologies.github.io/cito/current/cito.html) — 41 sub-properties of `cito:cites`
5. [CiTO paper, J Biomed Semantics 2010](https://jbiomedsem.biomedcentral.com/articles/10.1186/2041-1480-1-S1-S6)
6. [S2AG, WWW 2022 Companion](https://dl.acm.org/doi/10.1145/3487553.3527147) — 205M papers, 2.5B citations, SPECTER2, classifications
7. [OpenCitations / COCI](https://opencitations.net) — DOI-to-DOI index over Crossref
8. [SPECTER2, Allen AI 2026](https://allenai.org/blog/specter2-adapting-scientific-document-embeddings-to-multiple-fields-and-task-formats-c95686c06567) — citation-informed embeddings
9. [Citation graph from OpenAlex (Illinois Experts dataset)](https://experts.illinois.edu/en/datasets/a-citation-graph-from-openalex-works/) — 256.9M nodes, 2.1B edges scale figure

<!-- knowledge-index
generated: 2026-05-11T04:14:07Z
hash: 5268965403cc

table_claims: 8

end-knowledge-index -->
