# AI Literature Tools — Schema Patterns for a Personal Papers Store

Date: 2026-05-11. Scope: data-model patterns I'd consider lifting into a personal-scale shared papers store. Per-tool sections ordered by architectural concreteness (most concrete first). Tools with only marketing material are flagged and skipped.

## Ai2 Asta / ScholarQA — most concrete

Open-source repo `allenai/ai2-scholarqa-lib` exposes the actual Pydantic models [D1 official-repo].

**Schema (verbatim field names from `models.py`):**
- `CitationSrc { id, paper: PaperDetails, snippets: List[str], score: float, snippet_metadata: List[Dict] }`
- `GeneratedSection { title, tldr, text, citations: List[CitationSrc], table: Optional[TableWidget] }`
- `TaskResult { report_title, sections: List[GeneratedSection], cost, tokens }`
- `PaperDetails { corpus_id: int, title, year, venue, authors, n_citations, score }`

**Pipeline (from the engineering blog, verbatim) [D1]:** retrieval (Vespa, BM25 + dense embeddings over 8M papers) → rerank to top 50 → LLM "quote extraction" picks relevant snippets → LLM plans section headers and clusters quotes per section → report generated section-by-section with TLDR + attribution back to quotes. Comparison tables get a separate two-step decomposition: (1) schema generation (column = `{display_name, definition}`), (2) value generation conditioned on full text "mapping supporting snippets back to the actual sentences in the paper."

**Persistence:** Asta is account-bound (PaperFinder + ScholarQA history); no public schema for personal libraries beyond per-task `TaskResult` records. MCP-based Scientific Corpus Tool exposes the underlying S2 index to agents [D1 asta/resources/mcp].

**Ingenious idea:** Decompose tables into `column = {display_name, definition}` BEFORE generating cell values, and store `snippet_metadata` per citation alongside the snippet string itself. The `definition` field is the durable schema; the cell value is per-paper evidence. This is the schema move I'd actually steal.

**Verdict:** Strongest reference model. Caveat: a published Spanish critique (Revista Panamericana de Comunicación, 2025) found citation instability across identical queries [D3 third-party-critique] — the *output* isn't reproducible even when the schema is clean.

## scite — most concrete on citation evidence

**Schema (from MIT Press paper, Nicholson et al. 2021, QSS 2(3):882) [D1 peer-reviewed]:** every Smart Citation is `{citing_paper_doi, cited_paper_doi, statement_text, section_of_citing_paper, classification ∈ {supporting, contrasting, mentioning}, confidence}`. Only DOI-bearing papers ingested. 1.6B+ statements indexed [D2 vendor-page]. Base rate: 92.6% mentioning / 6.5% supporting / 0.8% contrasting [D1].

**Persistence:** Collections (DOI lists imported from Zotero/Mendeley/CSV) are first-class. Collections emit alerts when new supporting/contrasting citations arrive or a paper gets a retraction/erratum [D2 features-page]. This is the *only* tool in the survey with a real "living view" abstraction on personal libraries.

**Ingenious idea:** Decoupling rhetorical function from sentiment (their docs are explicit: "not classified by positive/negative keywords") [D1 help-center]. Stance ≠ vibe. Two-of-two human reviewers must agree before a user-flagged misclassification is overturned — operationalized correction loop, not just a feedback button.

**Verdict:** Steal the citation triple + section + confidence + flagging-with-2-reviewer-quorum. The supporting/contrasting/mentioning trichotomy is the floor for any personal evidence store.

## Elicit — concrete on extraction, opaque on internals

**Schema (inferred from product docs):** the unit of synthesis is the *extraction table*: rows = papers, columns = user-defined questions. Each cell stores `{value, supporting_quote, reasoning}` ("data extraction columns, supporting quotes, and reasoning") [D2 support-article 4168449]. Implicit PICO schema for clinical work [D2 third-party guide]. No published JSON schema.

**Persistence:** Notebooks + tagging + saved columns persist across sessions. Systematic-Review module preserves screening criteria and column instructions as editable artifacts of the report.

**Ingenious idea:** Storing `reasoning` as a first-class field next to `value` and `supporting_quote`. Most tools throw the LLM's reasoning trace away after extraction; Elicit keeps it as part of the row, which makes downstream auditing tractable.

**Verdict:** Adopt the `{value, quote, reasoning}` triple as the cell schema. Adopt "column instructions" as a stored, editable artifact rather than an ephemeral prompt.

## Connected Papers — concrete on graph construction

**Schema:** force-directed graph where edge weight = co-citation + bibliographic-coupling similarity over the S2 corpus [D2 third-party + founder Reddit AMA]. Nodes carry `{paper_id, year, citation_count}`, edge weight is the only learned object. No content embedding [D2 founder]. Shortest path to origin in similarity space is highlighted on hover.

**Persistence:** ephemeral per-graph; no user library.

**Ingenious idea:** Citation-graph similarity without content embedding. Two papers that have never cited each other can score high if they share co-citers. For a personal store this is cheap to compute (just paper IDs + reference lists) and adds a "neighborhood" without any LLM cost.

**Verdict:** Adopt as a derived view, not a primary representation.

## Inciteful — concrete and open

Rust backend over OpenAlex; on-the-fly graph builds up to ~200k nodes / 3-4M edges from a seed bibliography [D2 founder HN comment]. Open source. Multiple ranked-table views (different graph algorithms) instead of a single "the graph." API designed for sub-second graph build on uploaded bibliographies.

**Ingenious idea:** Same graph, *N* algorithmic projections (most-important-paper, similar, classic, etc.) presented as ranked tables. Don't force the user to pick a single similarity metric — compute several and let them sort. Easy to mimic with DuckDB + a few SQL views.

**Verdict:** Closest open-source analogue to what a personal store should look like at the graph layer.

## Consensus — moderately concrete

**Schema [D2 vendor help-center]:** Meter operates on top-20 retrieved papers; each gets a stance label `∈ {Yes, No, Possibly, Mixed}` plus per-paper metadata used in Meter 2.0 (study design, recency, journal, impact). "Mixed" added explicitly to capture subgroup-conditional findings ("worked for X, not Y").

**Persistence:** "My Library" with custom collections; threads persist with per-citation stance color [D2 changelog].

**Ingenious idea:** Meter 2.0's reweighting by study design + recency + venue — stance count alone is misleading when an N=1 case report and a Cochrane review each cast one vote. This is the move I haven't seen elsewhere on a stance aggregator.

**Verdict:** Steal the {Yes, No, Possibly, Mixed} quadrichotomy and the study-design weighting; the rest is a thinner scite.

## Undermind — partly concrete (whitepaper exists)

Whitepaper (Hartke & Ramette, undermind.ai/whitepaper.pdf) [D2 vendor whitepaper]: GPT-4 as reasoning engine + classifier inside a "structured exploration" loop that mimics expert citation-trail following, with exponential decay of relevant-find rate as exploration deepens (their benchmark plot). 10x recall vs Google Scholar self-reported. No data-model documentation beyond per-paper relevance score + inline-citation traceback.

**Ingenious idea:** Modeling and reporting the *exponential decay rate* of relevant-paper discovery — a stopping criterion derived from the agent's own returns curve rather than a fixed budget.

**Verdict:** Pattern (decay-curve-based stopping) is portable; their schema isn't public enough to copy.

## ResearchRabbit — marketing-heavy, one structural fact

Underlying corpus: OpenAlex + S2 + PubMed [D2 vendor + library guides]. Collections persist across sessions; the 2025 revamp adds explicit "rabbit hole" checkpoint history [D2 Aaron Tay analysis]. No published schema, no API. Skip for schema-lifting purposes.

## Synthesis: what to lift

| Pattern | Source | What to store |
|---|---|---|
| Rhetorical-function trichotomy + confidence | scite | `{citing_id, cited_id, statement, section, stance, conf}` |
| Cell = `{value, quote, reasoning}` | Elicit | Replace flat extraction cells with this triple |
| Column = `{display_name, definition}` | ScholarQA | Durable schema separate from cell evidence |
| `snippet_metadata` per citation | ScholarQA | Persist offsets/page anchors next to text |
| Collections that *alert* on new supporting/contrasting cites | scite | Living-view abstraction over a static DOI list |
| Stance + design + venue + recency weighting | Consensus 2.0 | Don't aggregate stance by count alone |
| Co-citation + biblio-coupling edges (no embedding) | Connected Papers | Cheap derived graph view |
| Multiple ranked projections of one graph | Inciteful | N SQL views, not one canonical similarity |
| Decay-curve stopping | Undermind | Returns-based budget, not fixed budget |

Provenance grades: D1 = official engineering docs / peer-reviewed; D2 = vendor product pages / help-center; D3 = third-party.

Cross-cutting observation: every tool with a credible schema stores `snippet_text` + `paper_id` + some form of `anchor` (section name or character span) + a typed label (stance, relevance, or column-definition). The personal-scale store should treat that quadruple as the primitive and build collections / graphs / tables as views on top.

<!-- knowledge-index
generated: 2026-05-11T04:18:31Z
hash: 5893e2e29cd7

sources: 17
  D1: official-repo
  D1: asta/resources/mcp
  D3: third-party-critique
  D1: peer-reviewed
  D2: vendor-page
  D2: features-page
  D1: help-center
  D2: support-article 4168449
  D2: third-party guide
  D2: third-party + founder Reddit AMA

end-knowledge-index -->
