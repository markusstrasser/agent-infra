---
id: 2026-05-11-cross-attestation-substrate
concept: cross-project-attestation
repo: agent-infra
decision_date: 2026-05-11
recorded_date: 2026-05-11
provenance: contemporaneous
status: accepted
initial_leaning: Build a federated cross-attestation MCP across phenome/genomics/intel with a new paper_fetch_attestations schema, an attest-before-fetch skill, two new hooks, and a standalone federation MCP server.
relations: []
---

# 2026-05-11: Cross-project attestation substrate — defer federation ~1 week, ship Phase 0 measurement now

## Context

User asked for a cross-project view of phenome, genomics, intel and proposals for shared skills/hooks/architecture. Five-agent archaeology pass revealed three independently-evolved attestation systems (genomics `claim_verdicts`, phenome cert-stack, intel theses-graph+closure-FSM). Synthesized into `research/cross-project-synthesis-2026-05-11/06-synthesis-and-proposals.md` proposing a federated attestation MCP, four new skills, three friction-informed hooks, and frontier-feature pilots.

The user's verbal model: "Every time a paper gets fetched or searched we can first search in our own thing and see if we already processed this and what part of the paper was processed and with what model."

## Alternatives considered

1. **Unified knowledge DB** in agent-infra, all repos write to it. Rejected — vetoed-pattern-shaped (knowledge-substrate MCP retired 2026-03-24). Forcing three settling architectures onto one schema courts build-then-undo.
2. **Federation MCP** as a standalone HTTP/stdio server querying each repo's attestation DB read-only. Original recommendation. Reviewer collapsed this to "one MCP tool, not a server" (option 5 below).
3. **Shared library** `agent-infra/lib/attest` imported by all repos. Rejected — vetoed 2026-03-19, cross-project utility libraries trade maintenance for too little benefit at this scale.
4. **Event bus** — JSONL events aggregated in agent-infra. Deferred — architecturally clean but overkill for 3-repo single-user second-scale event rates.
5. **Single MCP tool `cross_attestation_lookup(source_id)` inside `agent-infra-mcp`, DuckDB ATTACH over read-only views.** Reviewer-favored simplification. Selected.
6. **Re-route fetches through research-mcp with transparent internal cache.** Selected (complements option 5; replaces the proposed standalone `paper_fetch_attestations` public schema).
7. **Option F — ripgrep over standardized markdown frontmatter** (introduced by reviewer post-hoc). Worth piloting; if every research/decision file carries `processed_by:` and `attested_models:` frontmatter, `rg --json` does federation with zero infrastructure. Mark as future evaluation alongside option 5.

## Counterevidence sought

Searched for prior incident history justifying *new* federation infrastructure. Found:

- `improvement-log.md` records no incident where phenome and genomics actually duplicated paper-fetch work (Finding #16 in disposition — "Lack of evidence for duplicate fetch volume"). The premise was user-asserted, not measured.
- Vetoed-decisions list rejects building speculative cross-project infrastructure without incident history (Constitution Pre-Build Check #1).
- Direction-E (genomics) and cert-stack (phenome) are actively being rewritten. Federation against moving schemas is precisely the failure mode the vetoed `knowledge-substrate` MCP exhibited.

Found no incident-history evidence that the cross-fetch problem is currently costing material API/Modal spend. **This is the reason Phase 0 ships first as measurement, not infrastructure.**

Searched for prior attempt at "cache lookup as agent ritual via skill+hook" pattern. Found: phenome's `entity-management` skill works *because* the file structure does the work — the skill describes the contract, the filesystem enforces it. Skills as agent-side rituals over a database have no precedent that succeeded. This is the reason the original `attest-before-fetch` skill + two hooks was rejected by reviewers and accepted here as dropped.

## Decision

**Defer the federation tool ~1 week** until genomics direction-E quiesces. Genomics currently has an actively-executing agent writing to `data/knowledge/knowledge.duckdb`; building read-side coupling against its schema now would mean re-doing the federation after the schema settles.

**Ship Phase 0 immediately:** add `fetch_log` table to research-mcp + a one-shot analysis script. After ~7 days, count duplicate fetches per source_id. If duplicate rate ≥ 10%, Phase 2 (transparent cache inside `fetch_paper`) is justified. If <10%, the substrate is over-engineering and the premise is wrong.

**Adopted reviewer reframes** (full list in `06-synthesis-and-proposals.md` §Revisions):
- Cache lookup INSIDE `research-mcp.fetch_paper()`, not via skill+hooks.
- `citation-audit` as MCP tool inside research-mcp, not a Claude skill.
- Single MCP tool `cross_attestation_lookup` over DuckDB ATTACH, not a standalone server.
- Federation contract reads stable read-only DuckDB views, never internal tables; fail-soft on writer.lock contention.
- DOI ↔ PMID ↔ PMCID alias resolver (Phase 0.5) is a prerequisite for any cache lookup.
- OpenAlex as default identifier resolver; S2 fallback only.
- Sci-Hub dropped from any `fetched_via` enum.

**Dropped entirely:**
- `stop-execution-loop-watchdog.sh` — would false-positive on long Modal/WGS jobs.
- `pretool-quantitative-claim-check.sh` text-matching version — duplicates phenome's existing `verify_quantitative_claims.py`.
- `dont-route-around-hooks` AST scanning — brittle, only 2 confirmed incidents.

**Cosigned (build unchanged):** `cleanup-and-close`, `phase-gate`, `pretool-dispatch-delete-guard`, `posttool-genomics-pipeline-sync`, intel→research-mcp bridge, frontier-feature pilots with isolated blast radius.

## Consequences

- Phase 0 logger lands in research-mcp this session. Independent of genomics direction-E.
- No federation MCP exists yet. Re-evaluate in ~7 days when (a) genomics direction-E has settled, (b) Phase 0 data is in.
- The original §1.2 `paper_fetch_attestations` public schema is dead. Any reader of the original memo should consult §Revisions for the canonical architecture.
- Phenome's 9 citation verifier scripts stay in place until `research_mcp.audit_citations()` ships AND a grep/import-graph proof shows no external callers (Finding #7).
- Intel's research-mcp registration → first-actual-use bridge can proceed independently of all the above. Highest-ROI lone-wolf piece.

## Update — 2026-05-11 evening (Phase 6 shipped)

Genomics direction-E agent reported "structurally complete — every phase shipped infrastructure + probe results" with deferred bulk drains parked behind operator-budgeted runs. With direction-E quiescent (no active writer modifying `claim_verdicts` shape), Phase 6 of the revised phasing was unblocked and shipped.

- **`cross_attestation_lookup(source_id)` MCP tool** added to `agent_infra_mcp.py`. Read-only DuckDB connections to genomics `knowledge.duckdb`, phenome `claims.duckdb`, intel `theses.duckdb`. Fail-soft on lock contention — one repo's IO error returns `{status: "locked", error}` without sinking others.
- Source-id normalizer handles DOI (with/without prefix), PMID (bare digits), PMCID, NCT. Lookup queries genomics' `source_observations`, phenome's `primary_sources` (separate doi/pmid/pmcid columns), intel's `filings_and_datasets`.
- Smoke-tested against 5 real source_ids in current corpora — all returned correct presence/absence and capped at LIMIT 10 hits.
- Path correction applied: intel's DB lives at `intel/intel/indexed/theses.duckdb` (nested), not `intel/indexed/theses.duckdb` as the original overview claimed.

Phase 6 was originally gated to ~1-week wait. It shipped early because direction-E reached a quiet point first. Phase 0 measurement (fetch_log) continues to run independently.

What's still deferred:
- Phase 0.5 (DOI/PMID/PMCID alias resolver) — small but not yet justified by data
- Phase 2 (cache inside `fetch_paper`) — gated on Phase 0 measurement
- Phase 3 (cosigned hooks)
- Phase 4 (cleanup-and-close skill)
- Phase 5 (frontier pilots)

## Provenance

- 5-agent archaeology dispatch (subagent reports `research/cross-project-synthesis-2026-05-11/{01..05}-*.md`)
- Cross-model review via `/critique model --axes deep` (Gemini Pro domain + Gemini arch + GPT-5.5 formal + Gemini Flash mechanical), 74 findings, 2 cross-model agreements. Artifacts at `.model-review/2026-05-11-cross-project-attestation-substrate-b397f6/`.
- User decisions captured 2026-05-11: wait ~1 week on federation; ship Phase 0 now; revise memo in place.
- Verified: research-mcp uses SQLite (`papers.db`), not DuckDB; `~/Projects/genomics/data/knowledge/writer.lock` exists; phenome `verify_quantitative_claims.py` exists.
