---
title: Scientific KG schema standards for personal papers store
date: 2026-05-11
scope: schema selection for ~/Projects/papers/ citance + annotation + graph layer
provenance: official org docs (D1), peer-reviewed paper abstracts (D2), wikipedia/blog (D3)
---

# Scientific KG schema standards — verdict for personal scale

## Verdict table

| Standard | Adopt? | How | Confidence |
|---|---|---|---|
| **CiTO** (Citation Typing Ontology) | **Adopt — URIs as `stance_cito`** | Store full URI `http://purl.org/spar/cito/supports` etc. as enum value | D1, high |
| **FaBiO** (FRBR-aligned bibliographic) | **Adopt — class only** | Tag papers as `fabio:JournalArticle`, `fabio:Preprint`, `fabio:ConferencePaper` | D1, high |
| **PRO** (Publishing Roles) | Adopt-lite | `pro:author`, `pro:editor` if you need role typing beyond Wikidata `P50` | D1, med |
| **DoCO** (Document Components) | Skip | Section-level structure (intro/methods/results) — overkill unless doing rhetorical mining | D1, high |
| **DEO** (Discourse Elements) | Skip | Same as DoCO, even more granular | D1, high |
| **BiRO**, **PSO**, **PWO** | Skip | Bibliographic-record-as-entity, publishing workflow — publisher-side concerns | D1, high |
| **FRBR-in-OWL** | Skip | Work/Expression/Manifestation/Item distinction is wasted at personal scale | D1, high |
| **ORKG schema** (Resources/Predicates/Contributions/Comparisons) | **Steal vocabulary, not infrastructure** | Borrow the `Contribution` node concept; don't try to align URIs | D1, med |
| **Nanopublications** | **Skip as primary; optional export** | Four-graph TriG (head/assertion/provenance/pubinfo) too heavyweight for daily reading workflow | D1/D2, high |
| **Wikidata** (`wdt:P2860`, `wd:Q13442814`) | **Adopt as cross-link backbone** | Store Wikidata QIDs for papers/authors when resolvable; lets you join external | D1, high |
| **SciKGTeX** | Skip | LaTeX-author-side tool for embedding contributions in PDF XMP — wrong end of the pipe | D2, high |
| **OpenAlex schema** (already in use) | Keep | flat `referenced_works`, inverted-index abstracts — already pragmatic | D1, high |
| **scite 3-class stance** | Skip vocabulary, **reuse data** | Their `supporting/contrasting/mentioning` collapses to CiTO; use scite citances as input, don't store as native enum | D1/D3, high |

## Rationale per row

**CiTO.** The 41 sub-properties of `cito:cites` (`supports`, `disagreesWith`, `usesMethodIn`, `extends`, `obtainsBackgroundFrom`, `citesAsAuthority`...) are the de facto standard for stance-typed citation edges. OpenCitations COCI already emits them. Storing the full PURL (`http://purl.org/spar/cito/supports`) as a string in your `stance_cito` column buys you (a) zero ontology server dependency, (b) machine-readable interop with COCI/OpenCitations dumps, (c) ability to widen the vocabulary later without schema migration. *Adopt directly.*

**FaBiO class subset.** Useful narrow win: a 6-8 value enum (`fabio:JournalArticle`, `fabio:Preprint`, `fabio:ConferencePaper`, `fabio:BookChapter`, `fabio:Thesis`, `fabio:ResearchPaper`, `fabio:Dataset`, `fabio:Software`) gives type-tagging without committing to the full FRBR machinery. Cheap.

**ORKG.** Founded by TIB Hannover (Auer, Stocker, Jaradeh; flagship paper Jaradeh et al. K-CAP 2019). Internal schema is a property graph: `Resource` (R-prefixed IDs), `Predicate` (P-prefixed), `Class`, `Statement` (s,p,o triple), with `Paper` and `Contribution` as conventional Resource classes. URIs are minted under `orkg.org/resource/Rxxx`, not aligned with any external ontology by default — each Predicate optionally has a `uri` field pointing to external RDF. **Implication for you:** ORKG's URI namespace is centralised and not stable for personal mirroring; don't try to import their IDs. But the **conceptual move** — modelling a paper as a container of N atomic `Contribution` nodes with structured key-value properties — is exactly the right abstraction for an annotation-rich store. Steal that idea; mint your own local URIs.

**Nanopublications.** Still alive (Knowledge Pixels AG operates the registry; Biodiversity Data Journal, Pensoft, NFDI4ING actively publish them in 2024-2025; nanopub-java/python clients maintained). But the four-named-graph TriG structure (head/assertion/provenance/pubinfo, signed with RSA) is built for inter-org publishing with cryptographic provenance — not for your reading-and-annotating loop. **Decision:** keep an optional `to_nanopub.py` export if you ever want to publish a curated claim, but don't model your live store as nanopubs. The signing + decentralised-server overhead buys you nothing solo.

**Wikidata.** `P2860 (cites work)` + `Q13442814 (scholarly article)` are real and used at scale (Scholia, WikiCite). Millions of articles imported. Property set is rich: `P356` (DOI), `P698` (PMID), `P818` (arXiv), `P577` (publication date), `P50` (author), `P921` (main subject). **Adopt as a cross-link backbone:** store Wikidata QIDs when you can resolve them, so your local graph joins to the global one for free. Don't try to *be* a Wikidata mirror — you'd lose to OpenAlex on coverage.

**SciKGTeX** (Bless/Baimuratov/Karras, JCDL 2023). LaTeX package that embeds contribution metadata into PDF XMP at write-time for ORKG ingest. Wrong direction for you — you're a reader, not an author trying to ship structured metadata downstream. Skip.

**Personal KG patterns.** No rigorous standard exists. Obsidian/Logseq/Roam academic workflows (Zotero plugins, citance highlighting) are wikilink-based, not RDF-typed. The closest "personal scholarly KG with first-class typed annotations" prior art is essentially what you are building. Nothing to copy wholesale; the move is to compose **CiTO (edge stance) + FaBiO (paper class) + Wikidata QIDs (external join) + your own annotation table** rather than adopt one heavyweight framework.

## Concrete schema fragment for `~/Projects/papers/`

```sql
-- papers
fabio_class      TEXT  -- 'fabio:JournalArticle' | 'fabio:Preprint' | ...
wikidata_qid     TEXT  -- 'Q12345' nullable
openalex_id      TEXT  -- 'W4392...'
doi              TEXT

-- citances (paper A cites paper B with stance)
stance_cito      TEXT  -- full PURL: 'http://purl.org/spar/cito/supports'
                       -- or null if you only know it cites
quote_text       TEXT  -- the citance snippet (your annotation)
confidence       REAL  -- your confidence, 0-1

-- annotations (yours, on a paper or a claim within it)
claim_text       TEXT  -- atomic claim you extracted
my_stance        TEXT  -- 'agree' | 'disagree' | 'uncertain' | 'methodological'
```

Three URI namespaces total: `purl.org/spar/cito/`, `purl.org/spar/fabio/`, `wikidata.org/entity/`. All three are de-referenceable, stable since ~2010, zero infrastructure dependency.

## What this lets you skip

- No SPARQL endpoint, no triple store, no OWL reasoner.
- No nanopub signing keys, no decentralised server registration.
- No ORKG account / API rate limit dance.
- No DoCO/DEO rhetorical-section markup pipeline.

Provenance: D1 sparontologies.github.io, orkg.org docs, wikidata Source MetaData project page, nanopub.net/nanopub.readthedocs.io, github.com/Nanopublication, tibhannover.gitlab.io/orkg/orkg-backend/api-doc; D2 arxiv:2304.05327 (SciKGTeX), Jaradeh et al. K-CAP 2019 (ORKG, inferred from Wikipedia/secondary); D3 brave search snippets cross-checking activity.

<!-- knowledge-index
generated: 2026-05-11T04:18:40Z
hash: dcf9f1ef3791

title: Scientific KG schema standards for personal papers store

end-knowledge-index -->
