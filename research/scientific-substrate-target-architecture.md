---
title: Scientific Substrate Target Architecture
date: 2026-05-11
tags: [architecture, target-state, breaking-refactor, papers, attestation, federation]
status: revised-post-critique
audience: AI Agent developers and maintainers
inputs:
  - cross-project-architecture-overview.md
  - cross-project-synthesis-2026-05-11/06-synthesis-and-proposals.md
  - ~/Projects/papers/SCHEMA.md
  - decisions/2026-05-11-cross-attestation-substrate.md
---

# Scientific Substrate Target Architecture

The long-term shape of the personal scientific knowledge system that bridges phenome, genomics, intel, research-mcp, and agent-infra. **Breaking refactor, no compatibility shims, no wrappers, no legacy** (per Constitution Principle 14 and explicit user direction). Designed for AI agent developers and maintainers — the next agent walking in cold should grok this without spelunking history.

This memo supersedes the federation-MCP design in `cross-project-synthesis-2026-05-11/06-synthesis-and-proposals.md` §Revisions. That intermediate sketch added complexity (a separate `cross_attestation_lookup` tool, a `paper_fetch_attestations` schema) that this memo collapses into existing primitives.

---

## Generative principle

**The canonical source store is the cross-repo federation.** No separate federation layer. No DuckDB ATTACH tool. No `cross_attestation_lookup` MCP. The store's per-source `annotations.jsonl` (append-only) is the attestation surface. To answer "who has processed source X?" — read one file.

This principle collapses three of the four MCP tools I previously proposed into a single read of an artifact the canonical store schema already specifies. It also matches the way every existing scientific corpus pattern works (PubMed Central, Crossref, Wikidata) — one identity per source, attestation as metadata against that identity, NOT as a separate cross-database query layer.

---

## The four primitives

```
LAYER 1  CANONICAL SOURCE STORE       ~/Projects/corpus/<source_id>/
         bytes + parses + metadata + annotations + references + revisions
         IDENTITY: content-addressable (doi_<slug>, pmid_<id>, db_<slug>, sha_<hash16>)
         WRITERS: research-mcp.fetch_paper, papers CLI, per-repo extractors
         READERS: all MCPs; agents via lookup tool
         ATTESTATION SURFACE: per-source annotations.jsonl (append-only JSONL)

LAYER 2  PER-REPO CLAIM STORES        {genomics,phenome,intel}/.../claims.duckdb
         Domain-shaped assertions about sources.
         REFERENCE: source_id ONLY. Never duplicate bytes or metadata.
         Each repo owns predicates, slot vocabulary, lifecycle states.

LAYER 3  PER-REPO VERDICT STORES      claim_verdicts (bitemporal, single-writer)
         Reviews on claims. Model-attributed (model_version, prompt_template_hash).
         Each repo's existing pattern stays: genomics' verdicts, phenome's
         cert-stack, intel's closure-FSM. Same SHAPE, different SEMANTICS.

LAYER 4  MCP SURFACE                  one MCP per concern, narrow tools
         corpus-mcp        layer-1 ops (lookup, graph, ingest, fetch)
         genomics-mcp      layer-2/3 ops over genomics' knowledge.duckdb
         phenome-mcp       layer-2/3 ops over phenome's claims store
         intel-mcp         layer-2/3 ops over intel's theses graph
         agent-infra-mcp   markdown sections over docs/guides/memos (UNCHANGED)
```

No layer 5. No federation server. No cross-DB query tool. The composition pattern: agent calls `corpus.lookup(source_id)`, reads the returned `annotations` list to see which repos have processed it, then calls the relevant per-repo MCP for the claim/verdict detail. **Two hops, no magic.**

---

## Decisions made

User answered five open questions in the prior turn. Recording the calls and reasoning here.

### Q1 — Non-paper sources in the canonical store? **YES**

Genomics tracks `db:gnomad:r4`, `tool:hirisplex_s`, `repo:gene_panel_dementia_rare_variant` as source_observations rows. These ARE sources — they have identity (release version + content hash) and produce evidence. They belong in the canonical store under the same schema.

**Consequence:** the directory `~/Projects/papers/` is a misnomer. Per the "no cruft" directive, **rename to `~/Projects/corpus/`** as part of the migration. One word, accurate, what scientific work calls it. Ripples across:
- research-mcp `DEFAULT_DATA_DIR`
- papers CLI (renamed to `corpus`)
- papers skill (renamed)
- pretool-papers-store-remind.sh hook (renamed)
- SCHEMA.md path
- MCP tool names: `papers_lookup → corpus_lookup`, `papers_graph_query → corpus_graph_query`
- All hardcoded paths across ~30 files (sed-scriptable)

Source-id namespace standardizes on slug form across types:
- `doi_<slug>` — DOI
- `pmid_<id>` — PMID
- `pmcid_<id>` — PMCID
- `db_<slug>` — database release (e.g., `db_gnomad_r4`, `db_clinvar_2026_03`)
- `tool_<slug>` — tool output (e.g., `tool_hirisplex_s_v2`)
- `repo_<slug>` — repo-internal source
- `sha_<hash16>` — fallback for no-DOI-no-PMID

Genomics' current `doi:10.1038/...` / `db:gnomad:r4` form gets re-slugified to `doi_10_1038_...` / `db_gnomad_r4` during the migration. One identity rule across the corpus.

### Q2 — annotations.jsonl: strict schema or loose append? **STRICTER**

Concrete write API, validated schema, not raw file appends. JSONL line schema:

```json
{
  "annotation_id": "ann_<sha256[:16]>",
  "source_id": "doi_10_1038_nature12345",
  "repo": "genomics",
  "tool": "bio-verify",
  "model": "claude-opus-4-7",
  "prompt_template_hash": "sha256:abc...",
  "scope": "claim_extraction",
  "output_uri": "file:///Users/alien/Projects/genomics/data/...",
  "output_hash": "sha256:def...",
  "asserted_at": "2026-05-11T18:42:00Z",
  "schema_version": "1"
}
```

Required: `source_id`, `repo`, `model`, `scope`, `asserted_at`, `schema_version`. Optional: everything else.

CLI: `corpus annotate --source-id <id> --repo <r> --model <m> --scope <s> [--output-uri <u>] [--prompt-hash <h>]`. Python API: `corpus.annotate(...)`. Both validate against the JSON schema, compute annotation_id, append atomically.

JSON schema lives at `~/Projects/corpus/schemas/annotation.v1.json`. Versioned. Schema v2 only with an explicit decision record.

### Q3 — Concurrency on annotations.jsonl? **POSIX `O_APPEND` atomic; document the line-size contract**

JSONL line ≤ 4096 bytes → atomic on macOS/Linux via `O_APPEND` (PIPE_BUF guarantee). Our annotation schema produces ~300-600 byte lines, well under the threshold. No file locks needed.

Contract documented in SCHEMA.md:
> Annotation lines MUST be ≤ 4096 bytes when serialized. Writers MUST use `O_APPEND` opens. Readers tolerate partial-line writes at EOF (last line may be in-progress).

The CLI `corpus annotate` writes via `open(path, "ab")` (Python's `O_APPEND` equivalent) and `write(line.encode() + b"\n")`. One syscall, atomic.

For lines > 4KB (won't happen at our schema, but theoretical): fall back to flock(LOCK_EX) on a sibling `.lock` file. Documented but not implemented until needed.

### Q4 — One MCP per repo, or abstract? **Per-repo MCPs, with a common interface contract**

Each scientific repo (genomics, phenome, intel) owns its MCP. Domain semantics differ too much for one MCP. BUT all per-repo MCPs implement the same **minimum interface contract**:

```python
# Every per-repo MCP exposes these tools with identical signatures:

claims_for_source(source_id: str) → list[Claim]
  # All claims this repo holds that reference source_id.

verdicts_for_claim(claim_id: str) → list[Verdict]
  # All verdicts (current + superseded) for a claim.

attest(source_id, scope, model, prompt_hash, output_uri) → annotation_id
  # Write to canonical corpus annotations.jsonl AND repo-local claim store.
  # Single call from extractors. Idempotent on (source_id, scope, model, prompt_hash).
```

Repo-specific tools (genomics' `pipeline_status`, intel's `theses_query`, etc.) stay. The shared three are the lingua franca.

Why not one mega-MCP: predicate registries differ (genomics has 56 bio predicates, intel has 33 finance/regulatory predicates, overlap is ~0). Lifecycle states differ (genomics has `needs_human` / `quarantined`; intel has 12-axis FSM). A common MCP would either be the union (bloat) or the intersection (useless).

Why a shared minimum interface: agents don't need to learn three different "list claims" tool shapes. The shared three give agents a uniform composition pattern.

### Q5 — fetch_log → annotations attribution? **fetch_log goes away after migration; annotations are the only ledger**

Phase 0 fetch_log (research-mcp `fb33e7c`) measures duplicate-fetch volume over 7 days. After the canonical corpus + annotations convention lands, fetch_log becomes redundant:

- "Did anyone fetch this source?" → `corpus_lookup(source_id)` returns `present: True` + list of annotations.
- "Which repo fetched it first?" → first annotation in the file (earliest `asserted_at`).
- "Was it processed?" → annotations with `scope != "raw_fetch"`.

`research-mcp.fetch_paper` writes its annotation at fetch time (`scope: "raw_fetch", model: null`). Done.

Phase 0 measurement stays running until migration complete. After cutover, the same questions are answered via corpus, fetch_log table is dropped.

---

## What gets deleted (breaking refactor scope)

Per "no cruft, no wrappers" directive:

### From agent-infra
- `cross_attestation_lookup` tool in `agent_infra_mcp.py` (commits `2fa2ce2`, `52678af`). Replaced by `corpus_lookup` returning annotations.
- `papers_lookup` and `papers_graph_query` MOVE to corpus-mcp (renamed). Removed from agent-infra-mcp.
- `agent_infra_mcp.py` returns to single-tool `search` (markdown sections only).

### From research-mcp
- The Phase 0 `fetch_log` table (commit `fb33e7c`) — after migration, when annotations cover the measurement question.
- The standalone `papers.db` SQLite (papers metadata, cache, sources). Migrates into the canonical corpus layout. The corpus IS the metadata store; SQLite cache becomes `corpus_response_cache.db` if still needed.
- The local `pdf_dir` was already removed (commit `8d28fb1`). Confirms the pattern.

### From genomics
- `source_observations.source_id` namespace (`doi:`, `db:`, `tool:`) → re-slugified to `doi_`, `db_`, `tool_` form. Same content, different identity rule.
- `SourceRecord` schema: path fields dropped, replaced with `canonical_source_id`. See §"Migration cost" below — this is the keystone change.

### From phenome
- `primary_sources` table (28 rows) — drop. References to papers move to `canonical_source_id` field in `assertion_evidence`.
- Cert-stack `BridgeSnapshotCertificate` paths to source bundles — re-pointed at `~/Projects/corpus/<source_id>/parsed/paper.md`.

### From intel
- `filings_and_datasets` is empty (0 rows) — schema either drops or pivots to reference corpus by `canonical_source_id`. No data migration.

### From skills
- `pretool-papers-store-remind.sh` → renamed `pretool-corpus-remind.sh`. Logic unchanged.
- `papers` skill → renamed `corpus` skill. Content unchanged beyond name and path references.

---

## Migration cost (sharp numbers)

The other agent's audit surfaced four real blockers. Reanalyzed under "no compat shims" directive:

### Block 1 — `claim_binding_hash` is path-coupled

**Audit said:** SourceRecord JSON has 6 path fields per paper. Moving files invalidates the hash for every verdict (492 rows). Two paths offered: schema-migrate SourceRecord OR full rebind drain (~$5-30).

**Reanalysis:** The audit's `$5-30` estimate assumes re-running the verifier through new bindings. That's the conservative reading. The MINIMUM-cost path is bulk SQL re-hash with the supersedes pattern, **zero model calls**:

1. Schema-migrate SourceRecord: drop path fields, add `canonical_source_id`.
2. For each of the 492 verdicts:
   - Read old SourceRecord
   - Resolve paths → canonical_source_id (paper_evidence/<slug>/ → doi_<slug>)
   - Recompute claim_binding_hash over the new SourceRecord
   - INSERT new verdict row (identical content, new hash) via `MutationGateway.write_verdict(supersedes_event=<old>)`
3. Old verdicts get `verdict_supersedings` edges pointing to the new rows.

Cost: **~$0 in API**, ~30 min of SQL + script time. The genomics gateway's `verdict_supersedings` table is built for exactly this — translation, not re-evaluation.

Optional hygiene: spot-check 10-20 verdicts by running the verifier on the new binding and confirming `support_state` is unchanged. ~$0.50. Catches translation bugs without the full drain.

The audit's $5-30 number is the upper bound (full re-verify drain). The user can choose: bulk re-hash ($0), spot-check (~$0.50), or full drain ($5-30). My recommendation: bulk re-hash + spot-check.

### Block 2 — 77 DOI-slug collisions in existing 248 genomics bundles

Old form: `10.1234.foo` (dots preserved). New form: `10_1234_foo`. Deterministic merge: pick the newer bundle's content per paper, archive the older one to `<slug>/revisions/`. ~1 hour scripted.

### Block 3 — 21/27 worktrees divergent or unmerged

Stale worktrees would orphan if we used `git filter-repo`. **Resolution:** don't use filter-repo. Migrate the live tree only via a script that walks current HEAD; stale worktrees stay stale. They were already stale before this refactor.

### Block 4 — 1 hardcoded genomics SHA in agent-infra

Trivial find/replace post-migration. Minute of work.

### Additional (not in original audit)
- ~30 file hardcoded path replacements (`~/Projects/papers/` → `~/Projects/corpus/`)
- 3 MCP tool renames (papers_*, cross_attestation_lookup) with consumer updates
- 28 phenome `primary_sources` rows → `canonical_source_id` references in `assertion_evidence`
- Pre-flight: ensure every existing source_id used by any repo has a corpus entry (or create one)

### Total cost estimate

| Item | Cost |
|---|---|
| Bulk re-hash of 492 verdicts | ~$0 + 30 min |
| 77 slug collision merges | 1 hour scripted |
| Path replacements + MCP tool renames | 2 hours |
| Phenome primary_sources migration (28 rows) | 30 min |
| Optional verifier spot-check | $0.50 |
| Optional full re-verify drain | $5-30 (NOT recommended) |
| **Total (recommended path)** | **~$0.50 + 4 hours focused work** |

---

## Migration sequence (phase-gated; per friction Cat. 3)

Each phase ends with explicit "Phase N complete — gate to N+1?" before continuing. No bundled multi-phase pushes.

**Phase 0 — Foundation (already partial)**
- ✅ Canonical corpus store at `~/Projects/papers/` (parallel agent shipped)
- ✅ papers CLI + Python API (parallel agent shipped)
- ✅ graph.duckdb + INDEX.json (parallel agent shipped)
- ✅ Phase 0 fetch_log running (this agent shipped)
- 🟡 Annotation schema, validator, CLI command — NEW; ship in Phase 1

**Phase 1 — Annotation primitive + canonical naming**
- Define `annotation.v1.json` schema
- `corpus annotate ...` CLI + Python API
- Rename `~/Projects/papers/` → `~/Projects/corpus/`
- Rename `papers` CLI → `corpus`, papers skill → corpus skill, papers hook → corpus hook
- Rename MCP tools (`papers_lookup → corpus_lookup`, etc.)
- Find/replace ~30 hardcoded paths
- Smoke test: existing entry still resolves, annotation CLI writes valid lines
- Gate

**Phase 2 — Per-repo MCP shared interface**
- Add `claims_for_source`, `verdicts_for_claim`, `attest` to genomics-mcp (genomics_mcp.py)
- Add same to a new phenome-mcp (currently consumed via genomics-consumer)
- Add same to intel-theses MCP
- Each `attest()` writes BOTH the repo's local claim/verdict row AND the corpus annotations.jsonl entry
- Smoke test: from agent-infra-mcp call corpus_lookup → see annotations from all three repos → call per-repo MCP via the shared interface
- Gate

**Phase 3 — Genomics SourceRecord migration**
- Schema-migrate SourceRecord: drop paths, add `canonical_source_id`
- Bulk re-hash claim_binding_hash for all 492 verdicts via the supersedes pattern
- Spot-check 10 verdicts with verifier (~$0.50)
- Migrate genomics' source_observations namespace to slug form
- Merge 77 DOI-slug collisions
- Gate

**Phase 4 — Phenome + intel migration**
- Drop phenome's primary_sources rows
- Repoint phenome's assertion_evidence at `canonical_source_id`
- Repoint phenome cert-stack `BridgeSnapshotCertificate` artifact paths at corpus
- Pivot intel's filings_and_datasets (or drop, since empty)
- Gate

**Phase 5 — Cleanup**
- Delete `cross_attestation_lookup` from agent_infra_mcp.py
- Move `papers_lookup` + `papers_graph_query` from agent_infra_mcp.py → research-mcp/server.py (renamed `corpus_lookup`, `corpus_graph_query`)
- Drop the `fetch_log` table from research-mcp (questions now answered via corpus annotations)
- Update CLAUDE.md fact-tags + architecture overview
- Final gate; declare migration complete

---

## Open design questions (for /critique model pressure-test)

These are the points where I'm least confident and where adversarial pressure should focus:

1. **Is `annotations.jsonl` actually load-bearing enough to be the federation?** It's just a JSONL file. What goes wrong at scale (10K+ sources, 100K+ annotations)? Where does it break before SQLite/DuckDB would?

2. **The shared MCP interface contract (`claims_for_source`, `verdicts_for_claim`, `attest`) — is it the right minimum?** What's missing that agents will routinely need? What's there that agents won't use?

3. **Should `attest()` be a per-repo MCP tool, or a global one in corpus-mcp that takes a `repo` argument?** Tradeoff: per-repo = repo owns its identity; global = one fewer MCP to call. The per-repo version still writes to corpus annotations as a side effect.

4. **Is renaming `papers/` → `corpus/` the right call?** Argument for: accurate name, non-paper sources fit. Argument against: 30+ file find/replace just shipped under `papers/`. "Long-term clarity beats short-term churn" is the user's stated stance, but is the churn cost > the clarity cost in this case?

5. **`claim_binding_hash` bulk re-hash via supersedes pattern — does it preserve the audit trail correctly?** My read: supersedes is exactly the type of edge for "translated form, same semantics." But the genomics gateway might enforce that supersede chains require a non-null `evidence_event_id` change or similar — needs verification against the actual mutation_gateway code.

6. **What about cross-source semantic identity?** Two papers can be the same work under different DOIs (preprint + journal version, retracted-then-re-published). DOI resolves these only one way. Does the canonical corpus need a `semantic_cluster_id` field, or is "one row per DOI/PMID/PMCID, agents disambiguate" enough?

7. **Per-repo MCPs reading the corpus directly (filesystem) vs. through corpus-mcp**. Today, papers_lookup reads files directly. After per-repo MCPs join the annotation party, they ALSO read files directly to attest. That's filesystem coupling across repos. Should they go through corpus-mcp as a service? Cost: latency + one more hop. Benefit: corpus-mcp can enforce annotation schema centrally.

8. **For `db:`, `tool:`, `repo:` sources — do they need full corpus entries (with parsed/, citances_in/out, graph_db rows), or a degenerate `metadata-only` form?** A `db_gnomad_r4` entry isn't a paper — it has no PDF, no parsed markdown, no citations. Just metadata + annotations. Schema needs to accommodate this without bloating paper entries.

---

## Why this is better than the current state

| Dimension | Current (post-parallel-agent + my cross-attestation) | This target |
|---|---|---|
| Federation tools | 1 (cross_attestation_lookup) | 0 (annotations file IS the federation) |
| Source-of-truth for "who processed X" | DuckDB query across 3 repos | One JSONL file per source |
| Source namespace | Two (`doi:` in genomics, `doi_` in canonical store) | One (`doi_` everywhere) |
| Source-byte location | `~/Projects/papers/` + 3 per-repo duplications | One canonical location |
| MCP tools doing paper-anything | 3 spread across 2 MCPs | 2 in corpus-mcp, 0 elsewhere |
| Adding a new scientific repo | Touch 3 MCPs, 3 DBs, 3 schemas | Touch 1 MCP (new repo's), follow the shared interface |
| Agent mental model | "Search agent-infra OR research-mcp OR call the federation, depending" | "Lookup in corpus, drill into per-repo MCP if needed" |
| Cost of moving a source's bytes | 492 verdicts rebind | None — `canonical_source_id` is path-free |

---

## Risk register

- **Risk:** Rebind translation bug. Mitigation: spot-check 10 verdicts post-bulk with verifier.
- **Risk:** Annotation writes from multiple agents racing. Mitigation: POSIX O_APPEND atomic for our line sizes; documented.
- **Risk:** Per-repo MCP interface drift — different repos implement `claims_for_source` differently and break agent expectations. Mitigation: shared JSON-schema for `Claim` and `Verdict` return shapes; tested across all three at Phase 2 gate.
- **Risk:** Phase 0 measurement window cut short by migration. Mitigation: Phase 0 fetch_log keeps running through Phase 4; only deleted at Phase 5 cleanup.
- **Risk:** Stale worktrees (21/27 divergent) reference old paths post-rename. Mitigation: documented as accepted breakage; user re-syncs if needed.
- **Risk:** Renaming `papers/` → `corpus/` breaks the parallel agent's just-shipped CLI + skill + hook before they've had any organic usage. Mitigation: rename is a single git commit per repo; the parallel agent's work is preserved, just under a different name.

---

## For /critique model

Reviewers: this is the target architecture for a personal scientific knowledge system across phenome / genomics / intel / research-mcp / agent-infra. Single user, four repos, no auth, no multi-tenant. The user explicitly wants a breaking refactor with no compatibility shims (Constitution Principle 14). Audience for the resulting system: AI agent developers and maintainers.

Pressure-test specifically:

1. The eight open design questions in §"Open design questions" above. Each one is where I'm least confident.
2. The migration sequence (Phases 0-5). Is the ordering right? Are there hidden dependencies that would break a phase mid-execution?
3. The claim_binding_hash re-hash claim — does the supersedes pattern actually preserve audit semantics, or am I waving hands? Inspect `genomics/scripts/knowledge/mutation_gateway.py` if possible.
4. The annotation schema. Is JSONL the right format, or should this be a SQLite table inside the source's directory (e.g., `~/Projects/corpus/<source_id>/annotations.db`)? Trade query power for write atomicity.
5. The shared MCP interface (claims_for_source / verdicts_for_claim / attest). Is the minimum genuinely minimal, or am I missing something every agent will want?
6. The rename `papers/` → `corpus/`. Pure clarity move or churn-for-no-benefit?

Cosign / defer / reject each per-phase decision. Flag schema risks. Flag adoption risks. Don't soften on "wait" or "rethink" — the user values explicit "no" answers and we have time to do this right.

Specifically NOT for review (already-decided):
- That the canonical store IS the federation (user agreed Q1).
- That annotations are strict-schemaed (Q2).
- That MCPs are per-repo with a shared interface (Q4).
- That fetch_log is transient measurement (Q5).
- The "no compat shims" directive (Constitution + user-explicit).

What I want back: cosign / defer / reject on the eight open questions and the migration sequence. Schema risks. Hidden coupling I missed.

---

## Post-critique revisions — 2026-05-11

`/critique model --axes deep` returned 61 findings (2 cross-model). Artifacts: `.model-review/2026-05-11-scientific-substrate-target-arch-7200c3/`. User directive: "longterm, strictly the best." This block supersedes the earlier text where they conflict.

### Reversal — claim_binding_hash migration mechanism

**Earlier text said:** bulk re-hash via `MutationGateway.write_verdict(supersedes_event=...)`.

**Verified against `~/Projects/genomics/scripts/knowledge/mutation_gateway.py`:** supersedes inserts a new `verdict_id` row and UPDATEs the old row's `review_status='superseded'`. Old IDs preserved, but every supersede creates a new row + new ID for an unchanged semantic verdict. Reviewers (Gemini arch + Gemini Pro, separately, CRITICAL) reject this for path-only migration:

- Pollutes the bitemporal audit trail. Supersedes semantically means "knowledge changed; verdict revised." Path translation is infrastructure. Different semantics, different log channel.
- Creates 492 new IDs for an infrastructure change. Phenome's `KGAttestation` references and `genomics_bridge` sync artifacts targeting old `verdict_id`s would chain through supersedes edges to find current versions. Avoidable.

**Corrected mechanism:** add a gateway method `migrate_source_record_paths(translator_fn)` that does in-place `UPDATE claim_verdicts SET claim_binding_hash=?, source_record_json=? WHERE verdict_id=?`, preserves `verdict_id`, and logs ONE event to `audit_log` ("infrastructure migration on date D translated all paths via fn F"). Gateway already has UPDATE patterns (line 507: `UPDATE claim_verdicts SET review_status='superseded'`), so extending is gateway-compliant. Cost: $0, single transaction, no orphaned references.

Verification gate before execution:
- Generate manifest mapping old SourceRecord paths → new canonical_source_ids
- DRY-RUN: print before/after, confirm `SELECT verdict_id FROM claim_verdicts` set is identical
- Optional spot-check 10 verdicts post-migration with verifier (~$0.50)

### Corpus-mcp home — selected option A (dedicated process)

Earlier memo contradicted itself: Layer 4 said new `corpus-mcp`, Phase 5 said `research-mcp/server.py`. **Decision: A — a new `corpus-mcp` process.** Reasoning per "longterm strictly best":

- Clean separation of concerns. research-mcp = discovery + third-party APIs (S2, OpenAlex, Exa). corpus-mcp = local store ops (lookup, graph, attest, ingest). Different write patterns, different audit needs.
- Adding to research-mcp now would make it the "everything papers" mcp; in five years that's a tangle. Two processes cost ~50 MB RAM; not a constraint.
- corpus-mcp is the ONLY writer of `annotations.jsonl` (per critique #11/#17 — see below). Making it a process with its own boundary enforces that.

### Cross-cutting library — `corpus_core`

Three independent reviewer findings converge: annotations.jsonl writes must go through ONE validated writer; per-repo MCPs MUST NOT write raw. Implementation: a Python package `corpus_core` at `~/Projects/agent-infra/scripts/papers/` (already exists — refactor in place):

- `corpus_core.annotate(source_id, *, repo, actor_type, actor_id, scope, ...) → annotation_id` — validated, atomic, idempotent
- `corpus_core.lookup(source_id) → SourceRecord` — reader
- `corpus_core.attest_dual(local_writer_fn, annotation_kwargs)` — orchestrates "write to local DuckDB then write annotation" with outbox-style failure capture
- Both `corpus-mcp` AND `research-mcp` depend on `corpus_core`. Both share the schema + writer.

**Veto exception clarified:** the 2026-03-19 veto on "shared utility libraries across projects" was about generic helpers. `corpus_core` is not generic — it's the implementation of the canonical store contract. Different category. Veto does not apply. Recording this exception in `vetoed-decisions.md` after migration ships.

### Annotation schema (revised, all reviewer corrections folded)

`~/Projects/corpus/schemas/annotation.v1.json` becomes:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://corpus.local/schemas/annotation.v1.json",
  "type": "object",
  "additionalProperties": false,
  "required": ["annotation_id", "source_id", "repo", "actor_type", "actor_id",
               "scope", "asserted_at", "recorded_at", "schema_version"],
  "properties": {
    "schema_version":        {"const": "1.0.0"},
    "annotation_id":         {"type": "string", "pattern": "^ann_[a-f0-9]{16}$"},
    "idempotency_key":       {"type": "string"},
    "source_id":             {"type": "string"},
    "source_content_hash":   {"type": ["string", "null"]},
    "repo":                  {"enum": ["genomics", "phenome", "intel", "agent-infra", "research-mcp"]},
    "actor_type":            {"enum": ["model", "human", "service", "cli"]},
    "actor_id":              {"type": "string"},
    "tool":                  {"type": ["string", "null"]},
    "prompt_template_hash":  {"type": ["string", "null"]},
    "scope":                 {"enum": ["raw_fetch", "metadata", "parse", "summary",
                                       "claim_extraction", "verdict", "citance",
                                       "annotation", "retraction_observed"]},
    "output_uri":            {"type": ["string", "null"], "pattern": "^(project-root://|corpus://)"},
    "output_hash":           {"type": ["string", "null"]},
    "asserted_at":           {"type": "string", "format": "date-time"},
    "recorded_at":           {"type": "string", "format": "date-time"},
    "supersedes_annotation_id": {"type": ["string", "null"]},
    "status":                {"enum": ["active", "superseded", "retracted"]}
  }
}
```

Field changes from earlier draft:

| Was | Now | Why |
|---|---|---|
| `model` required | `actor_type` (model/human/service/cli) + `actor_id` | fetch_paper writes `actor_type:"service", actor_id:"research-mcp"` — no schema violation for non-model actors (critique #5) |
| `annotation_id` = sha256 of full line | `annotation_id` = `ann_<sha256[:16](idempotency_key)>`; `idempotency_key` = sha256 of stable tuple `(source_id, repo, scope, actor_id, prompt_template_hash, output_hash)` | retries are now idempotent (critique #14) |
| (missing) | `source_content_hash` | binds annotation to source state at annotation time; detects upstream drift (critique #47) |
| (missing) | `recorded_at` (corpus-writer assigned, UTC) | resolves multi-agent clock drift on `asserted_at` (critique #42) |
| (missing) | `supersedes_annotation_id` + `status` | annotations themselves can be superseded/retracted (critique #18) |
| `output_uri: file:///Users/alien/...` | `output_uri: project-root://genomics/data/...` or `corpus://<source_id>/parsed/paper.md` | portable across machines (critique #25) |
| `schema_version: "1"` | `schema_version: "1.0.0"` (semver) | matches SCHEMA.md (critique #51) |
| (open) | `additionalProperties: false` throughout | prevents agent hallucinated metadata (critique #22) |

Large outputs (>4KB) live in sidecar files; annotation carries only `output_uri` + `output_hash` (critique #19). Schema validation enforces this by capping `output_hash` length.

### Concurrency — corrected

Earlier text claimed PIPE_BUF guarantees regular-file atomicity. **Wrong** — PIPE_BUF is for pipes/FIFOs. Reviewer #8 caught this.

Corrected contract:
- `corpus_core.annotate()` uses `os.open(path, O_WRONLY | O_APPEND | O_CREAT, 0o644)` + single `os.write(line.encode() + b"\n")` syscall + `os.close()`. No Python buffered IO.
- Lines ≤ 4096 bytes → empirically atomic on macOS/Linux local filesystems even though POSIX doesn't formally guarantee it. (Tested via concurrent-writer fixture in Phase 1.)
- For lines > 4KB: `fcntl.flock(LOCK_EX)` on a sibling `.lock` file. Documented but rarely needed.
- **Local POSIX only.** SCHEMA.md adds invariant: "The corpus store MUST live on a local POSIX filesystem. NFS/SMB are not supported." (critique #50)

### Global annotations index in graph.duckdb

Per-source `annotations.jsonl` is the source of truth for "who processed source X?" — but O(N) for "all phenome activity yesterday." Reviewers #6/#9/#13/#39 converge: add a derived `annotations` table to `graph.duckdb` projected from JSONL files.

- Phase 1 ships the projection script: `corpus maintain --rebuild-annotations-index` walks all sources, parses JSONL, inserts rows.
- Phase 2 makes `corpus_core.annotate()` write BOTH the JSONL line AND insert into `graph.duckdb.annotations` within a transaction. Failure modes: JSONL append succeeds, DB insert fails → JSONL has the truth, next index rebuild catches up. Vice versa is prevented by ordering (JSONL first).
- New `corpus-mcp` tool: `corpus_annotations_query(repo=?, scope=?, since=?, until=?, limit=N)` reads the table, not the filesystem. Fast.

### Source-type schema (non-paper sources)

Per critiques #10/#53: add `source_type` to `metadata.json`, make capability sections optional.

```json
{
  "schema_version": "1.0.0",
  "source_id": "db_gnomad_r4",
  "source_type": "database_release",   // paper | preprint | database_release | tool_output | repo_artifact | webpage | other
  "title": "gnomAD v4.0",
  "doi": null,
  "pmid": null,
  "retrieved_at": "2026-04-12T...",
  "content_hash": "sha256:...",
  // No paper.pdf, no parsed/ directory required for non-paper types
  // annotations.jsonl always present
}
```

Reviewer #53 cosigns: directory with only `metadata.json` + `annotations.jsonl` is valid for `source_type ∈ {database_release, tool_output, repo_artifact}`. No fabricated PDFs.

### DOI slug collisions — fail-closed with __sha_ disambiguation

Earlier text: "deterministic merge, pick newer." **Reviewer #15 rejects.** Picking newer can silently merge distinct papers when slugifier collapses different DOIs.

Corrected: on collision, BOTH papers keep their identity. Disambiguator appends `__sha_<source-content-hash[:8]>` to one of the slugs. Raw-DOI comparison is the collision detector (compare the canonical DOI field in metadata.json, NOT the slug). Documented in SCHEMA.md.

Migration script for the existing 77 collisions: for each collision pair (A, B), keep the lexicographically-smaller slug as-is and rename the other to `<slug>__sha_<hash8>`. Both retain their annotation histories.

### Cross-source semantic identity — explicitly deferred

Critiques #35 + #60 cosign: do NOT implement preprint/journal merging in Layer 1. Two papers with different DOIs stay as separate corpus entries. Higher-layer code (per-repo MCPs, agents) resolves preprint/journal relationships via citation graph edges, not via merged identity. When a recurring failure justifies it, revisit.

### Shared MCP interface — refined

Critique #36 cosigns the minimum (`claims_for_source`, `verdicts_for_claim`, `attest`). Critique #41 splits it: domain reads in per-repo MCPs, annotation writes in `corpus-mcp`. Reconciled:

```
Per-repo MCPs (genomics-mcp, phenome-mcp, intel-mcp):
  claims_for_source(source_id) → list[Claim]
  verdicts_for_claim(claim_id) → list[Verdict]
  record_verdict(...) → verdict_id           # writes ONLY to local DuckDB

corpus-mcp:
  corpus_attest(source_id, repo, actor_type, ...) → annotation_id   # the ONLY writer of annotations
  corpus_lookup(source_id) → SourceRecord
  corpus_graph_query(...)
  corpus_annotations_query(repo=?, scope=?, ...)
  corpus_ingest(...)
```

**Agent orchestration pattern (no MCP-to-MCP, per critique #49):**
```
1. agent calls genomics_mcp.record_verdict(claim_id, ..., observation_ids=[...])
2. agent calls corpus_mcp.corpus_attest(source_id, repo="genomics", scope="verdict",
                                       output_uri="genomics://...verdict_id", ...)
```
Two explicit calls. Backstop: `corpus maintain --audit-sync` reports verdicts without corresponding annotations.

### Parser immutability (Marker LLM non-determinism)

Critique #28: Marker with `--use_llm` via Gemini is not bit-deterministic across runs. The existing `parsed.<parser_id>/` immutability convention in SCHEMA.md is therefore mandatory, not optional. `corpus_core.ingest()` enforces: if `parsed/` exists, refuse re-parse with same parser_id; force a new parser_id (e.g., bumped `parser_config_md5`).

### Things deleted from the plan

Per "no cruft" directive, these earlier proposals are dropped:

- The bulk supersedes migration (replaced by in-place UPDATE; see Reversal above).
- "Pick newer" collision merge (replaced by __sha_ disambiguation).
- model field as required string (replaced by actor_type/actor_id).
- file:// absolute URIs (replaced by project-relative).
- Federated lookup as a tool (already deleted; the canonical store IS the federation).
- Phase 0 fetch_log persistence beyond migration (gets dropped at cleanup; corpus annotations subsume it).

### Things added to the plan

- `corpus_core` library (new package, ships in Phase 1)
- Global annotations table in graph.duckdb (Phase 2)
- audit_corpus_sync.py backstop (Phase 4 + onwards)
- Isolated Phase 0.5 rename (was bundled with Phase 1; now first and standalone, per critique #57)
- `migrate_source_record_paths` gateway method (genomics, Phase 5)
- Schema validation in CI for per-repo MCP returns (Phase 4)
- Documented invariant: "corpus store on local POSIX filesystem only"
- Intel entity-file `[A-F][1-6]` citation extraction → annotations (Phase 6.5, scripted)

### Open items NOT resolved by this review

- Cross-source semantic identity: deferred per #60. Will revisit if recurring confusion.
- Retraction propagation: critique didn't address. Sketch: Crossref Retraction Watch webhook → corpus_core write annotation with scope="retraction_observed" → per-repo MCPs poll annotations on read and surface retraction status. Add to a future plan.
- Network-filesystem support: out of scope per #50.
- Schema v2 migration path: agreed schema is versioned; concrete v1→v2 migration is a problem for v2.

<!-- knowledge-index
generated: 2026-05-11T07:11:50Z
hash: 4c3116f1028e

title: Scientific Substrate Target Architecture
status: revised-post-critique
tags: architecture, target-state, breaking-refactor, papers, attestation, federation
cross_refs: decisions/2026-05-11-cross-attestation-substrate.md

end-knowledge-index -->
