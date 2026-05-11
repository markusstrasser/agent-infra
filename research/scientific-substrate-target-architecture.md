---
title: Scientific Substrate Target Architecture
date: 2026-05-11
tags: [architecture, target-state, breaking-refactor, papers, attestation, federation]
status: revised-post-critique
audience: AI Agent developers and maintainers
inputs:
  - cross-project-architecture-overview.md
  - cross-project-synthesis-2026-05-11/06-synthesis-and-proposals.md
  - ~/Projects/corpus/SCHEMA.md
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
- Each `attest()` writes BOTH the repo's local claim/verdict row AND the corpus annotations.jsonl entry — **⚠ 2026-05-11 final-critique update: SUPERSEDED. See §J. Per-repo MCPs do not have `attest()`. Agent explicitly orchestrates two calls (per-repo `record_verdict` + `corpus_mcp.corpus_attest`).**
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
- Move `papers_lookup` + `papers_graph_query` from agent_infra_mcp.py → **⚠ 2026-05-11 final-critique update:** corpus-mcp (the new standalone process from Phase 3), NOT research-mcp. research-mcp stays as third-party discovery; corpus-mcp owns L1 lookup tools.
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
| `annotation_id` = sha256 of full line | `annotation_id` = `ann_<sha256[:16](idempotency_key)>`; `idempotency_key` = sha256 of stable tuple `(source_id, repo, scope, actor_id, prompt_template_hash, output_hash, output_uri)` | retries are now idempotent (critique #14). **`output_uri` added 2026-05-11** after Phase 5 close-review revealed scope='verdict' annotations collapsed when multiple verdicts shared the same projection (`output_hash`); the original 6-field tuple matched the "one annotation per content projection" intent but contradicted §J.3's "one annotation per verdict" cardinality. Including `output_uri` makes every distinct addressable output its own annotation while keeping true retries (same agent, same URI) idempotent. |
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

### Extraction pipelines — `corpus_core.extract`

`corpus_core.extract` provides source-type-routed extractors. Each emits to `corpus/<source_id>/parsed.<parser_id>/` (immutable directory per critique #28). The extractor registry is a small dict; adding a new format is one entry + one module.

| `parser_id` form | Backend | Use for | Cost | Determinism |
|---|---|---|---|---|
| `marker@<version>` | `marker_single` subprocess | `source_type ∈ {paper, preprint}` — multi-column scientific PDFs | Slow (minutes/PDF on MPS), no API | Mostly deterministic; `--use_llm` is not |
| `pymupdf4llm@<version>` | `pymupdf4llm` Python lib | `source_type ∈ {database_release, regulatory_filing, tool_output}` — simple-layout PDFs | Fast (ms/PDF), no API | Fully deterministic |
| `trafilatura@<version>` | `trafilatura` + `httpx` | `source_type ∈ {webpage, blog_post, news}` — HTML | Fast, no API | Deterministic |
| `gemini-flash-lite@<date>` | Gemini 3.1 Flash Lite API | LLM fallback when above fail | $0.0001/page-ish | NON-deterministic — `parsed.<parser_id>/` immutability is the protection |

Routing default by `source_type` (override via `--parser` CLI flag or `parser=` kwarg):

```python
DEFAULT_PARSER = {
  "paper":             "marker",
  "preprint":          "marker",
  "database_release":  "pymupdf4llm",       # if PDF; trafilatura if HTML
  "regulatory_filing": "pymupdf4llm",
  "tool_output":       "pymupdf4llm",
  "webpage":           "trafilatura",
  "blog_post":         "trafilatura",
  "news":              "trafilatura",
  "other":             "pymupdf4llm",       # safest fast default
}
```

The Gemini LLM extractor exists today inside `research-mcp.papers.py:_extract_with_gemini`. It moves into `corpus_core.extract.pdf_llm()` with explicit `parser_id="gemini-flash-lite@<YYYY-MM-DD>"` so re-runs go to a fresh parsed.<parser_id>/ directory. No in-place overwrite.

**Marker venv stabilization (kills the `/tmp/pdf-bench` runtime dependency):**
- Install via `uv tool install marker-pdf` → resolves at `~/.local/share/uv/tools/marker/` (survives reboot).
- Resolver order in `corpus_core.extract.pdf_marker._find_marker_bin()`:
  1. `$PAPERS_MARKER_BIN` env var (user override)
  2. `~/.local/share/uv/tools/marker/bin/marker_single`
  3. `shutil.which("marker_single")`
  4. Error with installation instructions
- The `/tmp/pdf-bench/.venv/bin/marker_single` fallback is dropped entirely (developer artifact, not infrastructure).

**Public surface in `corpus_core`:**

```python
# corpus_core/extract/__init__.py
def extract(source_id: str, *, content: bytes | str | Path,
            source_type: str, parser: str | None = None,
            parser_config: dict | None = None) -> ExtractResult
# Dispatches to the right extractor module. Returns ExtractResult with
# parsed_markdown, parser_id, parser_config_md5, page_count, char_count.

# corpus_core/extract/pdf_marker.py     — Marker
# corpus_core/extract/pdf_lightweight.py — pymupdf4llm
# corpus_core/extract/html_trafilatura.py — trafilatura (handles bytes, str, or URL)
# corpus_core/extract/pdf_llm.py        — Gemini Flash Lite fallback
```

`corpus_core.ingest.from_url(url, source_type="webpage")` calls `extract.html_trafilatura.fetch_and_extract(url)`, writes `corpus/<source_id>/parsed.trafilatura@<v>/page.md` + metadata, returns paper_id-equivalent.

**Migration consequence:** research-mcp's `papers.db.sources` table (today stores raw web-page content provided by callers via `save_source`) gets unified into corpus during Phase 7. Each existing row becomes a corpus entry with `source_type: "webpage"`, parser_id="caller-provided" (since trafilatura didn't run on it). Going forward, agents calling `save_source` route through `corpus_core.ingest.from_url` instead; the `sources` table is dropped.

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

---

## Prior-art validation — 2026-05-11

Sanity-checked the design against the OSS ecosystem via 4 parallel research dispatches (`research/prior-art-2026-05-11/`). Synthesis: `00-synthesis.md`. Three changes are critical, one is a deferred-but-noted future direction.

### A. Extractor stack flips: Marker → MinerU (CRITICAL)

**Marker is GPL-3.0** — violates the MIT/Apache license policy. AND empirically broken on Apple Silicon (4 open issues: surya MPS #993, table-decoder no MPS #967, 20× slowdown #960, CLI #966; today's parallel-agent benchmark crashed at p.10 of a 41-page preprint).

**Switch to MinerU 3.1.0** for the high-fidelity paper lane:
- Apache-2.0-derivative license (with 100M-MAU / $20M-MRR commercial trigger — ~8 orders of magnitude below us, irrelevant)
- +14.6 OmniDocBench points over Marker (93.04 vs 78.44) on academic_literature subset
- CPU-runnable pipeline backend (DocLayout-YOLO + UniMERNet), Apple Silicon supported per README
- Formulas → LaTeX, tables → HTML, multi-column reading order is the documented strength

**Other lanes confirmed:**
- **pymupdf4llm stays** for fast non-paper PDFs (25-50× faster than MinerU on native-text). Note: AGPL-3.0 — fine for personal-local use, AGPL network clause activates if served behind a public endpoint. Document the boundary.
- **trafilatura stays** for HTML (F1 0.909, Apache-2.0, no contender since 2022).
- **No single library** does PDF + HTML + Office well in 2026. Docling is closest (MIT) but trades ~5-8 OmniDocBench points and ~2× speed.
- **GROBID** noted as the citation-graph specialist (TEI-XML; used by S2/scite); different niche from markdown extractors. Add only if/when citation graph quality matters more than the current Marker-emitted citances.

**License policy invariant (add to SCHEMA.md):**
> Apache-2.0 / MIT / BSD preferred. AGPL-3.0 acceptable for local-only personal use ONLY (no network service serving the AGPL code to others). GPL-3.0 prohibited.

### B. Annotation schema: stay bespoke, borrow RO-Crate vocab (MEDIUM)

None of the surveyed standards (PROV-O, RO-Crate, OpenLineage, SLSA/in-toto, OpenTelemetry GenAI, MLflow/DataHub/Marquez, DVC, sigstore) fits cleanly. **Closest semantically:** RO-Crate Process Run Crate (`CreateAction` with `agent`/`instrument`/`object`/`result`/`endTime`). **Closest architecturally:** OpenLineage (file transport, JSONL).

Recommendation from the survey: stay bespoke, align names with RO-Crate, add `conformsTo` + flat namespace keys. Specifically:

| Earlier field | Final (RO-Crate-aligned) | Notes |
|---|---|---|
| `actor_type` + `actor_id` | KEEP — use `agent` for human/service/cli; `instrument` for model/tool | RO-Crate distinguishes `Person` vs `SoftwareApplication`; we map cleanly |
| `tool` | `instrument.name` | |
| `output_uri` + `output_hash` | `result.uri` + `result.hash` | Nested under `result` |
| `asserted_at` | KEEP + add `endTime` alias | RO-Crate uses `endTime`; keep both for export compat |
| (new) | `conformsTo` | per-record schema version URI (`https://schema.local/corpus/annotation/v1.0.0`) |
| (style) | Flat namespace keys for nested fields | OpenTelemetry pattern: `agent.id`, `agent.type`, `result.uri`, `result.hash` |
| (new) | Stable URI-form agent IDs | `urn:agent:claude-opus-4-7@2026-04-16`, `urn:agent:research-mcp@0.1.2` |

What we keep that no standard offers: `recorded_at ≠ asserted_at`, `idempotency_key` from stable tuple, `supersedes_annotation_id` as first-class field. These are legitimate workflow needs (the academic literature — Information Systems 2025 paper, Werder et al. — validates "extend the standard, map to PROV-O via SKOS" as the convergent practitioner pattern).

**Explicitly NOT adopted:** JSON-LD `@context`/`@graph` wrapper (RO-Crate ceremony with no current return at our scale).

### C. Build corpus_core (don't adopt PaperQA2's `Docs`); cherry-pick its identity convention (MEDIUM)

Audited PaperQA2, Aviary, LDP, OpenScholar, ASReview, pyzotero. Verdict: **build `corpus_core` (~400 LOC).**

PaperQA2's `Docs` container is structurally close but:
- `extra="forbid"` Pydantic — hard to extend
- Mandatory `texts_index: VectorStore` field — can't use the container without embedding machinery
- `Doc` extends `Embeddable` from `lmi`, transitively pulling `litellm`+`openai`+`anthropic`
- `Docs.aadd()` default makes 2 LLM calls per document (bypassable but API-shaped around them)
- No opinionated on-disk layout — single-blob `model_dump_json()` persistence

**What's worth borrowing from PaperQA2** (Apache-2.0):
- **`compute_unique_doc_id(doi, content_hash)` from `utils.py`** — stable ID derivation. Vendor (~10 LOC, with attribution comment) for cross-tool ID interop.
- **`DocDetails.lowercase_doi_and_populate_doc_id` validator** — DOI normalization rules.
- **`paperqa.clients/` directory** is the actual gem: `crossref.py`, `openalex.py`, `semantic_scholar.py`, `unpaywall.py`, `retractions.py`, `journal_quality.py` + `DocMetadataClient` orchestrator. No LLM dep, returns enriched `DocDetails`. **Treat as optional enrichment dependency** — when `corpus_core.enrich.metadata(source_id)` is needed, the call is between (a) `paperqa-clients` import vs (b) 150 LOC of homegrown REST clients. Deferred until metadata enrichment is actually wired in.

Other libraries: Aviary/LDP (wrong category — agent gym + decision process), OpenScholar (research code, dormant 2025-08-13), ASReview (screening prioritization, wrong problem), pyzotero (HTTP client to Zotero — wrong abstraction).

### D. Packaging: uv workspace, 5 packages, Claude Code plugin (DEFERRED — Phase 8)

The 2026 standard verified across PaperQA2, DVC, mem0, cognee, fastmcp: **single repo, `uv` workspace, multiple PyPI packages, Claude Code plugin bundle on top.**

Target shape when published (Phase 8, post-migration):

```
~/Projects/corpus/                  (standalone repo, eventually)
├── pyproject.toml                  (workspace root: tool.uv.workspace = ["packages/*"])
├── packages/
│   ├── corpus-core/                pip install corpus-core      schemas + IDs + store layout
│   ├── corpus-cli/                 pip install corpus-cli       CLI
│   ├── corpus-mcp/                 uvx corpus-mcp               MCP server
│   ├── corpus-extractors/          opt-in extractor adapters
│   └── corpus-plugin-claude/       Claude Code plugin bundle (skills + hooks + .mcp.json)
├── schemas/                        versioned JSON Schema (bundled with packages)
├── data/                           gitignored — canonical store
└── tests/
```

**MCP distribution:** PyPI + `uvx corpus-mcp` (2026 standard across `mcp-server-git`, `aws-mcp`, `cognee-mcp`). NO Docker as primary distribution. Bundle MCP into the Claude Code plugin via `.mcp.json` for one-line install.

**Config resolution layers:** explicit kwarg → `CORPUS_ROOT` env → `[tool.corpus]` in pyproject.toml → `platformdirs.user_data_dir("corpus")` default.

**Per-repo schema registration:** Entry-points (`[project.entry-points."corpus.schemas"]`). Each scientific repo registers its claim/verdict schema versions with `corpus_core` at install time.

**Today's reality (Phase 0.5–7 of plan):** Code lives in `agent-infra/scripts/corpus/` (renamed from `scripts/papers/`). Reshape `scripts/corpus/` as a workspace-ready monorepo from the start (workspace root pyproject.toml + `packages/corpus-core/`) so the eventual Phase 8 extraction is a `git filter-repo` and PyPI publish, not a restructure.

**Phase 8 (NEW, deferred):** Extract `agent-infra/scripts/corpus/` to its own repo at `~/Projects/corpus/`. PyPI publish the 5 packages. Build the Claude Code plugin bundle. Trigger condition: >1 user OR explicit decision to open-source.

### E. Negative findings (what the survey did NOT find)

- **No 2026 convergence on "agent annotations"** as a standardized schema. The space is bespoke. Our schema can become a convergent answer in this niche.
- **No drop-in scientific-corpus-manager** handling paper + non-paper + provenance + extractor dispatch. The niche is unfilled.
- **No mature Apple-Silicon-first PDF extractor.** Most tools are NVIDIA-first; MinerU works on MPS but isn't optimized for it. Expect performance ceiling on Mac.
- **No emerging MCP** that does what `corpus-mcp` will. The personal-scientific-substrate niche is genuinely empty in 2026 OSS.

This means: the build path is justified (no existing solution), AND the work could become reusable infrastructure if open-sourced later. Phase 8 is the optional offramp.

### G. Inherit phenome's identity invariants (in-house prior art)

User flagged correctly that phenome has substantial identity infrastructure we'd be reinventing. Audited 2026-05-11:

- **`phenome/identity/canonicalize.py`** ("Plan 01 identity overlay") — `IDENTITY_KEY_VERSION = 1`, `IdentityBasis` enum (CANONICAL / NEEDS_REVIEW / UNRESOLVABLE), invariant **`sha256_hex(canonical_json(...))`**, inverse-predicate collapse (`metabolizes` ≡ `metabolized_by`).
- **`phenome/claims/identity.py`** (v4) — `IDENTITY_VERSION = 4`, namespace UUIDs for assertion/document/span/citation_block/assertion_evidence, `uuid5(namespace, canonical_tuple)` pattern, unit normalization for quantitative claims.
- **`phenome/claims/canonicalize.py`** — canonicalization rules.
- **`phenome/claims/relations/`** — typed scientific-graph edges with `vocabulary.py`. V1 has variant_in_gene + inverse mirror.
- **`phenome/claims/predicates.py`** — 56 typed predicates × 9 families.
- **`phenome/claims/schema.sql` + `views.sql`** — actual DDL.

**corpus_core inherits this — does NOT reinvent and does NOT cherry-pick PaperQA2 over it.** Specifically:

| Layer | Phenome already has | corpus_core's job |
|---|---|---|
| `canonical_json(...)` + `sha256_hex(...)` invariant | Yes — `phenome/identity/canonicalize.py` | Use the same invariant. Optionally pull into corpus_core as the canonical contract (Phase 8 candidate). |
| `uuid5(namespace, tuple)` pattern | Yes — `phenome/claims/identity.py` v4 with stable namespace UUIDs | Use same pattern. corpus_core defines new namespaces for source-level: `SOURCE_NAMESPACE`, `ANNOTATION_NAMESPACE` (assertion namespaces stay phenome-owned) |
| Inverse-predicate collapse | Yes — phenome's canonicalize | N/A (corpus_core deals with sources, not predicates) |
| Unit normalization for quantitative claims | Yes — `UNIT_RE` in phenome | N/A (sources don't carry units) |
| Typed predicate registry | Yes — `phenome/claims/predicates.py` (56 × 9 families) | N/A (corpus_core doesn't own predicates) |
| Typed scientific-graph edges with vocabulary | Yes — `phenome/claims/relations/` | N/A (corpus_core has citation graph only; predicate/relation graph stays per-repo) |
| **DOI/PMID slug derivation** | **NO** — phenome doesn't have it | **corpus_core OWNS** (`doi_<slug>`, `pmid_<id>`, `db_<slug>`, etc.) |
| **Cross-repo source identity** | **NO** — phenome tracks `primary_sources` rows per-repo, not canonical | **corpus_core OWNS** (`source_id`, `canonical_source_id`, content-addressable) |
| **Annotation provenance ledger** | **NO** — phenome has `audit_log` for claim verdicts, not source attestation | **corpus_core OWNS** (`annotations.jsonl` per source) |

**Reversal of finding C (PaperQA2 cherry-pick):** PaperQA2's `compute_unique_doc_id` was a useful hint but phenome's identity pattern is the right cite. Phase 1 plan:
- `corpus_core/identity.py` mirrors `phenome/identity/canonicalize.py`'s `sha256_hex(canonical_json(...))` invariant
- Use phenome's UUID5-with-namespace pattern (define new namespaces for source/annotation; assertion namespaces stay phenome-owned)
- DOI/PMID slug rules are genuinely new — corpus_core defines them, cites neither phenome nor PaperQA2
- Document in `corpus_core/identity.py` docstring: "follows phenome v4 identity convention; see phenome/claims/identity.py"
- **DO NOT vendor PaperQA2's `compute_unique_doc_id`** — phenome's pattern is more sophisticated and already battle-tested in our codebase

### H. Round-2 prior-art findings (6 additional axes)

After round 1, dispatched 6 more parallel agents for the remaining open questions. All reports converged (no contradictions). Synthesis: `research/prior-art-2026-05-11-round2/00-synthesis.md`. Key changes:

**1. Schema versioning — switch to SchemaVer.** `schema_version: "1.0.0"` → `"1-0-0"` (MODEL-REVISION-ADDITION). SemVer doesn't describe schema compatibility; SchemaVer does. Path: `~/Projects/corpus/schemas/v{N}/`. JSONL never rewritten — Pydantic v2 discriminated-union upcasters run at read time. DuckDB projection rebuilt only on MODEL bumps. Per-repo MCPs on different schema versions resolve via adapter. Reject: Avro/Protobuf/Iceberg-direct (binary breaks grep-ability), W3C VC `@context` (dead weight), SemVer-for-schemas.

**2. Graph storage — DuckDB confirmed; Kuzu out.** Kuzu archived on GitHub 2025-10-10 after Apple acquired the team (verified 1.0 confidence via The Verge, BetaKit, MacRumors, Waterloo CS). DuckPGQ extension is the upgrade path (same engine, no migration). At our scale (100K nodes / 2.4M edges): bounded triangle 7.7-28.8 ms, multi-hop 16.5-67.7 ms. Lance consolidates toward DuckDB SQL — cohabitation when semantic-similarity edges land.

**3. Annotation ID — REVERSAL: use sha256, not UUID5.** Round 1 aligned annotation IDs to phenome's UUID5-with-namespace pattern. Round 2 correctly distinguishes: phenome's UUID5 is a historical compromise for the assertion-ID namespace (3622 existing rows; migration cost > upgrade value). UUID5 uses SHA-1 truncated to 122 bits — strictly weaker than direct sha256. **For corpus_core's NEW ID space, use `annotation_id = "ann_" + sha256_hex(canonical_json(stable_tuple))[:16]`.** Phenome's INVARIANT (`sha256_hex(canonical_json(...))`) is what we inherit; the UUID5 wrapper is layer-specific.

**4. Content addressing — stay plain sha256.** No 2026 consumer wants CIDs (Zenodo = DOIs, HuggingFace = git-LFS hash, S2 = sequential int, Crossref/DataCite/arXiv same). sha256 IS already a multihash — `to_cidv1_b32()` is a 5-line view function the day a consumer asks. **Add `rfc8785.py` (Trail of Bits JCS impl) as dev-dep property test only** — assert phenome's `canonical_json` produces byte-identical output to JCS for our actual input types. Don't swap runtime. Rejected: W3C VC Data Integrity, Sigstore/Rekor, CBOR canonical.

**5. On-disk layout — stay native, stamp metadata.json with RO-Crate JSON-LD shell.** Layout itself unchanged. Add ~11 fields to `metadata.json` for export-compat: `@context`, `@graph`, `@type: Dataset`, `identifier`, `name`, `datePublished`, `license` (URI), `author[]` (ORCID URIs), `relatedIdentifier[]` (DOI/PMID aliases), `hasPart[]` (component files with per-file sha256), `corpus:*` custom namespace. Cost: ~30 LOC; retroactive migration painful. Reject OCFL (petabyte-scale 100-year preservation, wrong scale), Frictionless/Croissant/BIDS/DCAT (wrong domain). **BagIt is the right EXPORT format, not the live layout** — `corpus export --format bagit` (Phase 8) wraps RO-Crate in a Bag (bagit-ro pattern); manifests mechanically computable from per-file sha256.

**6. Annotation storage at scale — JSONL+DuckDB confirmed; DuckLake is the upgrade path.** Per-source JSONL canonical + DuckDB projection. **Critical invariant for SCHEMA.md:** Annotation records MUST be ≤4096 bytes when serialized. Records exceeding MUST reference large blobs by hash to a content-addressed store, not inline. Writers MUST use `os.open(path, O_WRONLY | O_APPEND | O_CREAT) + single os.write(line.encode() + b"\n")`. **Migration trigger if projection bottlenecks:** DuckLake (DuckDB Labs, 1.0 April 2026) — designed for 50GB-2TB, small writes, data inlining. **Reject Iceberg** (DuckDB-Iceberg schema evolution broken — issue #805, column-add crashes against old files). **Reject Lance** (loses human-grokkability, ecosystem still vector-flavored). Cognee/Mem0/paperclip RFC #801 all converge on the same architecture as ours — pattern validated.

**7. Skill/MCP DX — ship test fixtures, OTel from day one, lint stdio prints.** Bake into `corpus_core` from start:
- **`corpus_core.testing` module** exporting FastMCP `Client(server)` async fixture + copy-paste `conftest.py` template. 5-line fixture, 3-6 lines per test, sub-ms execution. THE highest-leverage gift to downstream MCP authors.
- **OpenTelemetry from day one** — FastMCP emits MCP semantic conventions natively. Zero config. Downstream observability = point an OTLP endpoint at it.
- **Lint against `print()` from stdio MCPs** — runtime check in `corpus_core` rejects stdout outside JSON-RPC stream. Bites every new MCP author.
- **Tool budget invariant: 5-15 tools/MCP, hard cap 20.** Speakeasy: 95% accuracy at 20 → near-0 at 107. Industry: GitHub Copilot 40→13, Block Linear 30+→2.
- **Don't reinvent** skill scaffolder (use Anthropic's `skill-creator` plugin), MCP server scaffolder (`mcp-server-dev`), typed-client codegen (export schemas via `just export-schemas`, let downstream codegen).
- **Hello-world install:** `/plugin marketplace add <url>` → `/plugin install corpus@corpus-marketplace` → `/reload-plugins`.

**Note:** genomics-mcp has ~30 tools today, above the accuracy cliff. Audit candidate for Phase 4 follow-up (not blocking this migration).

### I. Hot-path optimization candidates (profile-before-swap)

Surfaced for completeness; not blocking. Architectural picks are converged; these are library-swap optimizations inside `corpus_core` if profiling shows a hot path.

| Concern | Default in plan | Faster candidate | Trigger to swap |
|---|---|---|---|
| JSON Schema validation | `jsonschema` (pure Python) | `fastjsonschema` (~10× faster) | Validation in top-3 hot paths |
| JSON serialization | stdlib `json` (matches phenome) | `orjson` (Rust, ~10× faster) | Byte-identical output test must pass first |
| Pydantic validators | Pydantic v2 (already fast) | `msgspec` (~3-5× faster, smaller ecosystem) | Only if Pydantic v2 is the bottleneck |
| Python sqlite | stdlib `sqlite3` | `apsw` (more features, similar speed) | Need apsw-specific features |
| In-memory graph algos | (not in plan) | `rustworkx` (Apache-2.0, IBM/Qiskit-backed; NetworkX replacement, 10-100×) | When PageRank/centrality/community ops are needed — future Phase 9 |
| Annotation storage at >100K-1M scale | per-source JSONL + DuckDB | DuckLake (DuckDB Labs, 1.0 April 2026) | When single-file DuckDB projection bottlenecks |

These are profile-driven, not research-driven. The plan ships with the defaults; profiling/optimization happens after.

### F. Plan changes triggered by prior-art

| Change | Phase | Severity |
|---|---|---|
| Marker → MinerU swap; `corpus_core/extract/pdf_mineru.py` (was `pdf_marker.py`) | 1.5 | Critical |
| Drop `/tmp/pdf-bench/.venv/bin/marker_single` fallback | 1.5 | Critical |
| Document AGPL local-only carve-out + license policy invariant | 1 | Medium |
| Rename annotation fields to RO-Crate vocab + `conformsTo` + flat keys + URN agent IDs | 1 | Medium |
| Reshape `scripts/papers/` → workspace-ready `scripts/corpus/packages/corpus-core/` (not just rename) | 0.5 / 1 | Medium |
| Vendor PaperQA2's `compute_unique_doc_id` pattern in `corpus_core/identity.py` (~10 LOC + attribution) | 1 | Low |
| Defer `paperqa.clients` import decision until enrichment is wired | future | Low |
| Add Phase 8 (deferred): repo extraction + PyPI publish + Claude plugin bundle | 8 | Low (future) |
| GROBID as optional citation lane | future | Low |

---

## §J — Final critique reconciliation (2026-05-11)

Third and final `/critique model --axes deep` returned 9 findings. Artifacts: `.model-review/2026-05-11-substrate-arch-final-b0329b/`. One CRITICAL flagged for verification (#3 — verified safe; phenome's `assertion_id` does NOT include `primary_source.id`; canonical tuple is `{v, predicate, entities, slots}`).

Substantive findings applied:

### J.1 — Per-repo MCP interface: NO `attest()` (high)

Earlier text said per-repo MCPs implement `claims_for_source`, `verdicts_for_claim`, **`attest()`**. The hybrid contradicts the explicit "agent calls two MCPs separately, no MCP-to-MCP" pattern. Final interface:

```
Per-repo MCPs (genomics-mcp, phenome-mcp, intel-mcp):
  claims_for_source(source_id)  → list[Claim]      # READ
  verdicts_for_claim(claim_id)  → list[Verdict]    # READ
  record_verdict(...)           → verdict_id       # WRITE to local claim_verdicts DB only

corpus-mcp (SOLE annotation writer):
  corpus_attest(source_id, repo, agent.id, scope, ...) → annotation_id
  corpus_lookup, corpus_graph_query, corpus_annotations_query, corpus_ingest, corpus_dashboard
```

Agent flow:
```
1. agent calls genomics_mcp.record_verdict(...) → verdict_id
2. agent calls corpus_mcp.corpus_attest(source_id=..., repo="genomics",
       scope="verdict", output_uri=f"genomics://verdicts/{verdict_id}", ...)
```

Two explicit calls. **No `attest()` on per-repo MCPs.** No MCP-to-MCP. `audit_corpus_sync.py` (Phase 4) catches the case where step 2 is skipped.

### J.2 — corpus-mcp owns L1 lookup tools (medium)

Earlier text in Phase 5 said move `papers_lookup` and `papers_graph_query` to `research-mcp/server.py`. This contradicts the §D Phase 3 decision that corpus-mcp is the standalone owner. **Final:** corpus-mcp owns all L1 corpus tools. research-mcp stays third-party discovery (`search_papers`, `fetch_paper`, `audit_citations`, `verify_claim`, `prepare_evidence`, etc).

### J.3 — Phase 5 backfill: 492 verdicts → 492 annotations (high)

Phase 5 SourceRecord migration UPDATEs 492 verdicts in-place. After Phase 4 ships `audit_corpus_sync.py`, those 492 verdicts would immediately appear as "missing annotation" drift. **Add to Phase 5:** as part of `migrate_source_record_paths`, write a corresponding `corpus_attest` annotation for each verdict (`agent.id = "urn:agent:service:phase-5-migration"`, `scope = "verdict"`, `output_uri = "genomics://verdicts/<verdict_id>"`, `asserted_at = original verdict's asserted_at`, `recorded_at = migration time`).

### J.4 — Split corpus_core.testing → separate `corpus-testing` package (medium)

Earlier text put FastMCP test fixtures inside `corpus_core.testing`. Reviewer correctly flags: testing utilities are NOT the storage contract — they're utility helpers, which the veto applies to.

**Final:** add `packages/corpus-testing/` to the workspace alongside corpus-core. Contains FastMCP Client fixtures, conftest.py templates, sample annotation factories. Downstream MCPs declare `corpus-testing` as a `dev` dependency. `corpus-core` itself imports ZERO testing frameworks — pure contract.

This sidesteps the veto without losing the highest-leverage DX gift.

### J.5 — Defer RO-Crate JSON-LD generation to export time (medium)

Earlier text said stamp `metadata.json` with the 11-field RO-Crate JSON-LD shell at ingest time. Reviewer correctly flags: ORCID lookups + license URI resolution + `hasPart[]` per-file sha256 are EXPORT concerns, not INGEST concerns. Forcing ingest to query Crossref/OpenAlex bloats the fetch path.

**Final:**
- Live `metadata.json` is intrinsic facts only: `source_id`, `source_type`, `doi`, `pmid`, `pmcid`, `title`, `authors` (when known from fetch), `year`, `retrieved_at`, `content_hash`, `parsed_sha256`, `pdf_sha256`, `retraction_status`. Plus `corpus:*` namespace flat keys.
- The RO-Crate JSON-LD shell (`@context`, `@graph`, `@type: Dataset`, `relatedIdentifier[]`, `hasPart[]` with per-file sha256, etc.) is **generated dynamically** by `corpus export --format ro-crate` and `corpus export --format bagit` — both Phase 8 deliverables. ORCID/license URI enrichment happens at export time (optional flag, may call out to research-mcp clients).
- Phase 1 stays simple. Phase 8 gets a clear export pipeline.

### J.6 — Don't build permanent SchemaVer upcasters speculatively (low)

Earlier text said Phase 1 ships Pydantic v2 discriminated-union upcasters for read-time schema-version dispatch. Reviewer flags: the existing Phase 5 path migration is a one-time SQL UPDATE — runtime upcasters are redundant.

**Final:**
- Phase 1 ships schema v1 ONLY (no upcaster machinery built yet).
- The SchemaVer convention (`"1-0-0"` MODEL-REVISION-ADDITION) and `schemas/v{N}/` layout convention STAY — these are the design contract.
- When v1→v2 eventually happens (separate session), THAT plan builds upcasters or a one-time migration script. Build the migration when there's a v2 to migrate to.

### J.7 — Prompt-level enforcement in CLAUDE.md (medium)

Earlier interface change relies on the agent remembering both calls. Reviewer correctly flags: agents will forget. Add Phase 4 step:

Update agent-infra `CLAUDE.md` cross-project section with a hard rule:

> **When recording a claim or verdict against a source:**
> 1. Call the relevant per-repo MCP's `record_verdict(...)` (writes to repo-local claim_verdicts).
> 2. **MUST also call `corpus_mcp.corpus_attest(...)`** (writes the provenance annotation to the canonical corpus store).
>
> Skipping step 2 leaves provenance incomplete. `audit_corpus_sync.py` detects drift within 24h, but the prompt-level rule prevents drift entering the system in the first place.

### J.8 — Phase 6 verification check (low)

Reviewer's flagged-CRITICAL on phenome UUIDs was verified safe (`primary_source.id` does NOT participate in `assertion_id` derivation). Add belt-and-suspenders verification anyway to Phase 6:

```bash
sqlite3 phenome.claims.duckdb "SELECT MD5(group_concat(id, ',')) FROM assertions ORDER BY id" > before.md5
# … migrate primary_sources, repoint assertion_evidence to canonical_source_id …
sqlite3 phenome.claims.duckdb "SELECT MD5(group_concat(id, ',')) FROM assertions ORDER BY id" > after.md5
diff before.md5 after.md5  # MUST be empty
```

### J.9 — Memo + plan internal consistency (medium)

Done in this commit. Stale references to `attest()` on per-repo MCPs and "move tools to research-mcp" flagged inline with `**⚠ 2026-05-11 final-critique update:**` markers (append-only convention).

<!-- knowledge-index
generated: 2026-05-11T19:00:09Z
hash: 4998f60d0ae7

index:title: Scientific Substrate Target Architecture
index:status: revised-post-critique
index:tags: architecture, target-state, breaking-refactor, papers, attestation, federation
cross_refs: decisions/2026-05-11-cross-attestation-substrate.md, research/prior-art-2026-05-11-round2/00-synthesis.md

end-knowledge-index -->
