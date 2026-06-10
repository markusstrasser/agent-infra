# Corpus / Science-Graph Substrate — Architecture

> Descriptive map of the scientific knowledge substrate (the `corpus` store +
> `corpus-core` library + per-repo claim layers). Complements
> `system-architecture.md` (which covers the agent *harness*: hooks/skills/MCP/
> memory). Accurate as of 2026-06-01 (session fc1a3dd3).

## 1. Purpose
A single-operator scientific knowledge substrate: a durable, attributable,
*replayable* record of what the agent fleet concluded, about which sources, and
how those conclusions changed. "Rent cognition, own the correction plumbing."
**Not a product** — optimized for elegance, one-source-of-truth, and
error-correction at N=1, not for scale. Consumers are AI agents (via MCP), not
humans.

## 2. Repo layout — code vs data vs consumers

| Repo | Role | Git |
|---|---|---|
| `~/Projects/corpus` | **DATA**: one dir per source + `graph.duckdb`. | no (377M; see §10 seam) |
| `~/Projects/substrate` | Substrate **CODE**: the `corpus-core` package and shared corpus schemas. | yes |
| `~/Projects/agent-infra` | Meta/governance code: `corpus_mcp.py`, `audit_corpus_sync.py`, dashboards, hooks. | yes |
| `~/Projects/research-mcp` | Discovery + retrieval MCP (`fetch_paper`, RAG). Depends on `corpus-core`. | yes |
| `~/Projects/genomics`, `~/Projects/phenome` | Domain repos with per-repo claim layers; coupled directly by **the bridge**. | yes |
| `~/Projects/intel` | Separate (market/AI-narrative; 0 DOIs — deliberately not paper-shaped). | yes |

`corpus-core` is editable-installed into all four code repos from
`substrate/packages/corpus-core` (see §10 seam).

## 3. The store (`~/Projects/corpus`)
**Filesystem is the source of truth; `graph.duckdb` is a rebuildable projection.**

```
corpus/<source_id>/              # doi_… / pmid_… / sha_… (papers); db_/tool_/repo_ (non-paper)
  metadata.json                  # bibliographic + parsed_sha256 (active-parse pin)
  paper.pdf                      # if fetched
  parsed.<parser_id>/page.md     # immutable, parser-addressed parse (sole read entry point)
  parsed.<parser_id>/parsed.sha256
  citances_in.jsonl / citances_out.jsonl   # citation contexts (+ stance snippets)
  annotations.jsonl              # ← THE LEDGER: append-only attestation events (629 KB total)
corpus/graph.duckdb              # DERIVED projection (12 MB), rebuilt via `corpus maintain --rebuild-*`
```

`graph.duckdb` tables, by function:
- **Bibliographic + citation graph**: `papers`, `edges`, `co_citation_pairs`, `biblio_coupling_pairs`.
- **Attestation ledger**: `annotations` + `annotations_current` (chain-aware leaf view; supersession via `supersedes_annotation_id`).
- **Epistemic core**: `claim_relations` + `claim_relation_endpoints` (bidirectional) + `claim_relations_active` + `claim_relation_tombstones` (order-independent supersession) + `support_balance` (derived view).
- **Plumbing**: `source_identity_crosswalk`, `corpus_schema_meta` (version gates).

## 4. `corpus-core` — the package (modules by job)
- **Identity & paths**: `store` (`PaperRecord`, `store_root()`←`CORPUS_ROOT`, `paper_path`), `uri` (`KNOWN_PROJECT_SCHEMES`), `canonical`, `identity` (content-addressing), `identity_crosswalk`.
- **Ingest & extract (knowledge IN)**: `ingest` (PDF/URL→parse), `batch`, `extract_citances`, `resolve_references`, `parse_health` (parse-state derivation), `figure_extract` (on-demand vision extraction of figure DATA → `figure_extraction` annotations; type-dispatched: chart→table, diagram→node-edge, image→description — `corpus figures <id>`).
- **The ledger (heart)**: `annotate` (**sole writer** of annotations — append-only, namespaced, content-addressed, idempotent), `index` (projects JSONL→duckdb; `epistemic_surface` lives here), `outbox` (cross-repo transactional outbox + `drain`), `schema_version` (reader/writer compat gates), `maintain` (rebuilds), `replay`, `sync`.
- **Query**: `lookup`, `graph_cli`, `cli`, `annotate_cli`.

## 5. Two pipelines around the one store
- **Extraction (IN)**: `corpus ingest` → parse (marker-modal default for papers/preprints, on Modal) → per-repo claim extractors produce **claims**: genomics `claim_verdicts` (`genomics/data/knowledge/knowledge.duckdb`), phenome `assertions` + `contradiction_pairs` (`phenome/indexed/claims.duckdb`). Current: 209 papers, 157 parsed, 952 genomics verdicts.
- **Reasoning (OUT)**: per-repo contradiction detectors promote into the **one** `claim_relations` sink → `support_balance` derives a linear net-support scalar → the read-loop surfaces conflict back to agents.

## 6. Cross-repo attestation (substrate v2) — architectural, not a ritual
```
repo mutation gateway (e.g. genomics MutationGateway.write_verdict)
  └─ INSERT attestation intent into pending_corpus_attestations   ← inside BEGIN/COMMIT
  └─ after commit + lock release: corpus_core.outbox.drain → corpus_core.annotate (SOLE writer)
        └─ append to corpus/<src>/annotations.jsonl   (source of truth)
        └─ project into graph.duckdb
```
`annotate` is the only writer of corpus annotations — enforced per-repo by
`lint_no_direct_corpus_writes.py`. Endpoints are namespaced:
`corpus:<src>` / `repo:phenome:assertion:<uuid>` / `repo:genomics:claim:<id>` / `local:markus`.

**Distinct from the bridge.** genomics↔phenome also exchange *data* through a
direct, hash-verified **bridge** (`genomics/scripts/bridge_artifact.py` →
`phenome/src/phenome/bridge/` + the `genomics-consumer` MCP) that feeds personal
genome findings into phenome's self-profile. **The bridge owns cross-repo data
flow; the corpus owns cross-repo attestation.** They are separate by design — and
this is why a corpus-mediated cross-repo *contradiction* layer was not built
(`decisions/2026-06-01-cross-repo-contradiction-layer-not-built.md`).

## 7. The epistemic core
- **`claim_relation`**: a first-class, append-only, multi-party, namespaced contradiction/refutation record, ridden *inline* on a `scope='claim_relation'` annotation (no sidecar; the substrate owns the content-addressed `relation_id`). Deep representation (5-class relation enum, all endpoints stored).
- **`support_balance`**: a derived **linear** view (refute −1, qualify −0.5, support +1, extend +0.5). Deliberately never P(true) — a transparent tally, not a fake posterior. (Simple inference over deep representation.)
- **Read-loop**: `epistemic_surface(source)` → active verdict attestations + active relations + support_balance + conflict flag. Surfaced on **`corpus_lookup`** *and* **`fetch_paper`** — an agent about to read a source is shown if it is under refutation, deterministically.

## 8. MCP surface
- **corpus** (`corpus_mcp.py`): `corpus_lookup` (source + epistemic status), `corpus_graph_query` (citations / contradictions / ego-graph), `corpus_annotate`.
- **research** (`research-mcp`): `search_papers`, `fetch_paper` (+`epistemic_status`), `ask_papers` (Gemini-1M RAG), `save_source`, `search_preprints`, `verify_claim`, `traverse_citations`.
- **agent-infra**: session search, hook metrics, improvement-log.

## 9. Integrity guards (architecture over instructions)
- `audit_corpus_sync.py` (daily, launchd `com.agent-infra.audit-corpus-sync`): verdict↔annotation drift + relation↔home-table drift + parse-health advisory + outbox drain. **Exit code keys off drift.**
- Hooks: append-only guard (protects the ledger), knowledge-index, paper-quality, corpus-drain-health.
- `schema_version.py`: min-reader / min-writer gates block incompatible code from corrupting the shared DB.

## 10. Known seams (honest)
- **`corpus-core` lives under `agent-infra/scripts/`** but is a genuine shared library (5 consumers: agent-infra, research-mcp, genomics, phenome, intel). Cohesion would improve in a dedicated `corpus` library repo with its own version history; functionally identical (editable-install either way). Deliberate cross-repo refactor, not urgent — plan at `.claude/plans/2026-06-01-seam-b-corpus-core-standalone-repo.md` (Seam B, deferred to a quiescent window).
- **Correction semantics are guarded, not yet fully designed.** `annotation_id` is content-addressed (lifecycle fields — `status`, `supersedes_annotation_id`, `source_content_hash` — deliberately excluded so replays keep their id). A same-content correction (a status-only retraction, or re-attesting a verdict against a re-parsed source) therefore used to be silently swallowed as an idempotent no-op. As of 2026-06-01 `annotate()` rejects this **loud** (raises, pointing the caller to fork the id with a new output_uri/output_hash) — a cross-model-review finding, verified latent (0/655 annotations ever corrected). What's still open: the concrete supersession-with-same-content path is unbuilt, deliberately, until the first real retraction is written and its semantics are concrete. (The ledger itself is now git-tracked — Seam A — so "every correction is a commit" is literal.)
- **Shipped + hardened, unproven in use.** 2 live claim_relations (both intra-phenome on a virtual source); 0 real-paper relations. The relation layer + read-loop are correct and tested but not yet exercised by real data — acceptance-contract item #5 (a relation provably changed a decision) is not yet met.

## 11. Scale note (N)
Built "simple inference over deep representation" so data volume does not force
redesign. At N≈1000 papers nothing changes: DuckDB (12 MB → ~60 MB) and the
filesystem are trivially within range, and full-scan ops (rebuild / audit /
parse_health, all O(N)) stay sub-5s. Real thresholds are far out: incremental
audits ~10K sources; 128-bit `relation_id` ~1e5 relations
(`decisions/2026-06-01-…` F1 trigger). The not-built decisions (cross-repo
contradiction layer, A1 enforcement hook) were gated on *demand* and
architecture-fit, not on N — more papers does not create cross-repo demand.
What N *does* change: more claims → more within-repo contradictions → the
relation layer finally gets exercised (validation, not redesign).
