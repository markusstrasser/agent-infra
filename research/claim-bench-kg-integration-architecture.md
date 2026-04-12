---
title: claim_bench → Knowledge Graph Integration Architecture
date: 2026-04-11
tags: [claim-bench, knowledge-graph, architecture, discovery]
status: active
---

# claim_bench → Knowledge Graph Integration Architecture

**Context:** Architectural discussion during the v2.2 post-sweep audit session about whether claim_bench is the right substrate for scientific discovery, and how it connects to a future knowledge graph.

**Key insight:** claim_bench is a governance/accounting substrate, not a discovery substrate. Discovery needs a reasoning layer on top that reads the ledger and asks relational questions the ledger can't express alone.

## Three-layer architecture

```
Entity files (markdown, human-readable, the narrative source of truth)
    ↕ extraction / back-annotation
Claim records (structured content: dict, the unit of verification)
    ↕ projection
Graph (derived, disposable, the substrate for discovery queries)
```

**Layer 1 — Entity files.** Already exist in `~/Projects/phenome/docs/entities/genes/` (22 gene pages), genomics claim registry (973 claims), phenome research memos. Markdown with YAML frontmatter. Human-readable, hook-protected. Don't replace with a database.

**Layer 2 — Claim records.** The claim_bench `ClaimRecord` with `content: dict` typed per adapter. NOT triples. Real claims are high-dimensional:

```python
# Genomics adapter claim
content = {
    "gene": "CYP2D6", "variant": "*4/*4",
    "drug": "codeine", "phenotype": "reduced_analgesia",
    "direction": "loss_of_function",
    "mechanism": "reduced CYP2D6-mediated O-demethylation",
    "population_context": "personal_genome",
    "source_entity_file": "phenome/docs/entities/genes/CYP2D6.md",
}

# Phenome adapter claim
content = {
    "intervention": "magnesium_glycinate_400mg",
    "outcome": "sleep_latency", "direction": "decreased",
    "temporal_context": "2024-Q3",
    "source": "self-reports/2024-sleep-protocol.md",
    "co_factors": ["no_caffeine_after_14h", "consistent_wake_time"],
}
```

"Gene C in Context D affecting Thing E" is at minimum a 5-tuple, not a triple. Context (variant combo, drug, dose, co-factors, population) is load-bearing, not decorative. Flattening to subject-predicate-object is actively misleading for pharmacogenomics.

**Layer 3 — Derived graph.** Claim-centric graph (not edge-centric):

- **Two node types:** entities (gene, drug, phenotype, intervention, outcome) and claims
- **Two edge types:** entity-to-claim role bindings (subject_gene, target_phenotype, context_drug, ...) and claim-to-claim relationships (supports, contradicts, refines, prerequisite — per Rasheed arXiv:2602.13855)
- **Edge weight** from DecisionGate verdict + verification freshness from the JSONL ledger

This is a hypergraph in bipartite form: each claim connects N entities via typed roles. DuckDB + NetworkX handles this at current scale (<100K edges). Graph is disposable — derived from the ledger, rebuilt on demand.

## What the graph enables that the ledger can't

| Query type | Ledger alone | Ledger + graph |
|---|---|---|
| Per-claim verification status | Yes | Same |
| Path traversal (MTHFR → folate → homocysteine → cardiovascular) | No | Yes — entity-to-claim-to-entity hops |
| "Which unverified claims resolve the most uncertainty?" | No | Betweenness centrality on unverified claim nodes |
| Cross-project contradiction detection | Manual grep | Contradiction edges across shared entity nodes |
| "What should I investigate next?" | No | Info-gain ranking on unverified high-centrality claims |
| Gap detection ("no claim covers gene X + drug Y") | No | Missing-edge query over entity pairs |

## What needs to be built (future, not in current plan)

1. **Content schema conventions per adapter** — so the graph extractor knows which `content` dict fields are entities and which are context. ~1 day.
2. **Entity resolution across projects** — "is phenome's CYP2D6 the same as genomics' CYP2D6?" Trivially yes for genes (HGNC symbols); harder for phenotypes (sleep_latency vs reduced_sleep_onset_time). Needs a shared entity namespace or a reconciliation pass. ~1 day.
3. **`graph_projection.py`** — reads JSONL ledger + content schemas → NetworkX DiGraph with claim nodes and entity nodes. ~200 lines. Disposable read model, rebuilt from ledger on demand (ESAA pattern).
4. **Back-annotation hook** — when a claim gets verified, stamp its source entity file with the verification date. A phenome PostToolUse hook could do this. ~50 lines.
5. **Discovery queries** — path traversal, contradiction surface, gap detection, next-best-verification ranking. The actual value layer. Scope TBD.

## What the current plan already provides for this

- `ClaimRecord.content: dict` — the right seam for per-adapter typed content
- `ClaimRecord.stable_id` — join key between entity files, claims, events, and graph nodes
- `VerificationEvent.claim_id` — joins events to claims (and thus to graph edges)
- `VerificationEvent.parent_event_ids` — meta-claim chains are already DAG structure
- `AuthorityClass` + `evidence_modality` — edge-weight inputs for the graph
- Adapter pattern — each project defines its content schema without the core needing to know

The one thing that will eventually need to exist: typed content schemas per adapter (so the graph extractor can identify entity fields). The plan's `content: dict` is the right choice NOW because it doesn't force a graph schema before the data shape is known. The schema conventions come later, after Phase E and Phase F have proven what the content actually looks like in practice.

## Architectural anti-patterns to avoid

- **Don't build a general-purpose KG.** The vetoed-decisions list retired the knowledge substrate MCP (4 reads / 60 writes in 7 days). A claim graph is a typed projection of structured verification data, not a retrieval system. It answers "what connects X to Y and is the path verified?" not "find me the file about X."
- **Don't force triples.** Real claims have 5-10 contextual fields. A triple store loses the context that makes claims meaningful. Claim-centric hypergraph or nothing.
- **Don't make the graph the source of truth.** The JSONL ledger is the source of truth. The graph is a disposable derived view. If the graph dies, rebuild from ledger.
- **Don't build the discovery layer before the accounting layer.** Discovery queries over unverified, unstale-checked, un-authority-weighted claims are worse than no queries. Ship claim_bench first, then project the graph, then build discovery on verified data.

## Prior art for this architecture

- **ESAA (arXiv:2602.23193)** — event store → deterministic projection → read model. The claim_bench ledger → graph projection follows this exactly.
- **Rasheed Semantic Provenance Graph (arXiv:2602.13855)** — typed claim/source/reasoning nodes with 4-class edges. The claim-centric bipartite graph is a simplified version of this.
- **ElephantBroker (arXiv:2603.25097)** — property graph with `G = (N, E, φ)` where `N = {facts, actors, goals, ...}` and scoring traverses `Evidence→Claim→Fact` chains. Similar architecture at higher complexity.
- **Gilda & Gilda (arXiv:2601.21116)** — evidence dependency chains with WLNK (weakest-link) aggregation. Their Gamma Invariant Quintet constrains how verification confidence propagates through the graph.

<!-- knowledge-index
generated: 2026-04-12T03:35:24Z
hash: d0c1bb05ef9d

title: claim_bench → Knowledge Graph Integration Architecture
status: active
tags: claim-bench, knowledge-graph, architecture, discovery
cross_refs: docs/entities/genes/CYP2D6.md
table_claims: 5

end-knowledge-index -->
