---
title: Cross-Project Synthesis — Skills, Hooks, MCPs, and the Scientific Knowledge Substrate
date: 2026-05-11
status: revised-post-critique
inputs:
  - 01-phenome-patterns.md
  - 02-genomics-patterns.md
  - 03-intel-patterns.md
  - 04-session-friction.md
  - 05-frontier-tooling.md
  - ../cross-project-architecture-overview.md
---

# Cross-Project Synthesis — Proposals

Synthesizes the five archaeology reports into concrete actions. Designed for `/critique model` adversarial pressure before any implementation begins.

The user's framing: "Let's assume that we have a scientific database that keeps growing outwards that bridges Phenome, genomics, and maybe if I start biotech investing it might also go into intel. … Every time a paper gets fetched or searched we can first search in our own thing and see if we already processed this and what part of the paper was processed and with what model. … The genomics knowledge infrastructure leads the way here."

## Headline thesis

The three scientific repos already have working attestation systems. They do not need to be merged. What's missing is a **federated lookup layer** — a "before you do this, has any repo already done it?" query that spans the three attestation stores. This is the keystone. Everything else is supporting infrastructure or independently useful but secondary.

The user's verbal description maps cleanly onto a known pattern: content-addressable provenance index. Each repo continues to own its attestation store; a cross-project MCP (or a federation tool inside agent-infra) answers `has_been_processed(source_id, scope) → list[Attestation]` against all three. Cache stays domain-shaped where it lives; lookup is uniform.

## Divergent options considered

Per Constitution Principle 6, write the options before the recommendation. Five mechanisms for the cross-repo scientific substrate:

| Option | Mechanism | Maintenance | Reversibility | Verdict |
|---|---|---|---|---|
| **A. Unified knowledge DB** (single DuckDB or Postgres in agent-infra; all repos write to it) | Centralized store, schema migrations affect all three | High — schema is a single point of contention across three settling architectures | Low — would replace working systems | **Reject.** Vetoed-pattern-shaped (knowledge-substrate MCP retired 2026-03-24). Three settling systems on top of one schema is asking for build-then-undo. |
| **B. Federation MCP** (`mcp__cross_attestation__has_processed(source_id)` queries each repo's attestation DB read-only) | Stateless query layer; each repo's writer is unchanged | Low — pure read interface, can be replaced | High — additive only | **Recommend.** Matches the user's verbal model; preserves repo autonomy; small surface. |
| **C. Shared library** (`agent-infra/lib/attest` Python pkg, all three import) | Code dependency across repos | Medium — three repos pin one library version | Medium — backout requires three coordinated reverts | **Reject.** Veto exists (2026-03-19 cross-project utility libraries). Same maintenance trap. |
| **D. Event bus** (each repo emits attestation events to a JSONL log; agent-infra MCP reads aggregate) | Append-only event stream; aggregation in agent-infra | Low — JSONL is forever-readable | Medium — bus contract is sticky once subscribed | **Defer.** Architecturally clean but unnecessary at current scale (3 repos, single user, second-scale event rates). Federation reads handle it. |
| **E. Re-route every fetch through research-mcp** (single chokepoint, cache lives there) | Single fetch surface for all paper-related ops | Medium — research-mcp becomes critical path | Medium — already partially this | **Adopt as complement to B.** Research-mcp already does this for papers/sources; extend to be the *write side* of attestation for paper-fetch specifically. Federation MCP queries it the same as it queries the repo-local stores. |

**Selected:** B + E. Federation MCP for cross-repo "has any repo done this" queries; research-mcp doubles as the attested fetch cache for papers (it already is one, in part). C, D rejected. A is the trap.

## Section 1 — The scientific knowledge substrate (federated attestation)

### 1.1 What the substrate actually is

Three things, in order:

1. **Each repo's existing attestation store is the source of truth for its domain.** Genomics' `claim_verdicts`, phenome's cert IDs, intel's theses-graph + entity files. Do not touch their write paths.
2. **A small read-only federation MCP** (`cross-attestation-mcp`) that knows where each store lives and exposes a uniform query: `has_processed(source_id, scope?) → list[AttestationStub]`. Source IDs are normalized (`doi:10.…`, `pmid:…`, `pmcid:…`, `nct:…`, `db:gnomad:r4`, `arxiv:…`, `ticker:NTLA`).
3. **Paper-fetch chokepoint moves entirely to research-mcp** with a new attestation table inside it: `paper_fetch_attestations(source_id, fetched_at, fetched_via, content_hash, markdown_uri, summarizer_model, summary_uri, evidence_depth, requested_by_repo, requested_for_task)`. When any agent in any repo fetches a paper, research-mcp checks its attestation table first, returns cached markdown + summary if a sufficient-grade attestation exists, else fetches + attests. The federation MCP exposes this table alongside the repo-local stores.

### 1.2 Schema (paper-fetch attestation, the bridging table)

The user's specific ask — "what part of the paper was processed and with what model" — needs a model-attributed, scope-aware row. Direct port of genomics' verdict pattern:

```sql
CREATE TABLE paper_fetch_attestations (
  attestation_id          VARCHAR PRIMARY KEY,         -- sha256 of canonical tuple
  source_id               VARCHAR NOT NULL,            -- doi:… / pmid:… / pmcid:… / arxiv:…
  source_release_id       VARCHAR,                     -- e.g., crossref-snapshot-2026-04
  content_hash            VARCHAR,                     -- sha256 of fetched body
  markdown_uri            VARCHAR,                     -- file://.../papers/<hash>.md
  evidence_depth          VARCHAR NOT NULL,            -- {abstract, full_text, structured, metadata}
  fetched_at              TIMESTAMP NOT NULL,
  fetched_via             VARCHAR NOT NULL,            -- {scihub, oa, europepmc, biorxiv, crossref, openalex, unpaywall}

  -- model-attributed processing scope (one row per processing pass)
  processing_scope        VARCHAR NOT NULL,            -- {raw_markdown, summary, claims_extracted, citations_extracted, full_synthesis}
  processing_model        VARCHAR,                     -- 'claude-opus-4-7' / 'gemini-3-flash' / null if raw
  processing_prompt_hash  VARCHAR,                     -- canary against prompt drift
  processing_output_uri   VARCHAR,                     -- file://.../processed/<hash>.json
  processing_output_hash  VARCHAR,                     -- sha256, lets later replay detect drift

  -- provenance
  requested_by_repo       VARCHAR NOT NULL,            -- {phenome, genomics, intel, agent-infra}
  requested_for_task      VARCHAR,                     -- session_id or task hint
  asserted_at             TIMESTAMP NOT NULL
);

CREATE INDEX paper_fetch_source ON paper_fetch_attestations(source_id);
CREATE INDEX paper_fetch_scope_model ON paper_fetch_attestations(processing_scope, processing_model);
```

Bitemporal optional — paper content doesn't change in a `valid_from` sense (retractions are first-class `source_observations(status=deleted)` writes, same as genomics). The model attribution + processing scope is the new bit: one paper might have 4 rows (raw fetch by phenome, summary by gemini for genomics, claims-extracted by opus for phenome, full-synthesis by gpt for intel) and the federation lookup returns all of them.

### 1.3 The lookup contract

```
cross_attestation_lookup(
  source_id: str,
  scope: Literal["any", "raw_fetch", "summary", "claims", "full_synthesis"] = "any",
  min_evidence_depth: Literal["abstract", "full_text", "structured"] = "abstract"
) → list[AttestationStub]

AttestationStub = {
  source: "genomics" | "phenome" | "intel" | "research-mcp",
  attestation_id: str,
  scope: str,                    # what was done
  model: str | None,             # who did it
  asserted_at: datetime,         # when
  artifact_uri: str | None,      # where the output lives
  content_hash: str | None,      # what content the model worked from
  evidence_depth: str,           # how good was the source
  link_to_native_view: str       # repo-specific deeplink for full detail
}
```

Cost target: <50ms per query (DuckDB attached read of three local files + research-mcp's SQLite). No network.

### 1.4 Write side — agent flow

Before any agent does paper-fetch / paper-process work:

```
1. agent calls mcp__cross_attestation__has_processed(source_id, scope="summary")
2. if existing attestation found AND model ≥ requirement AND evidence_depth ≥ requirement:
     → use artifact_uri directly, skip fetch + process
3. else:
     → research-mcp.fetch_paper(source_id) (fetches if not cached, attests raw)
     → process with target model
     → research-mcp.write_processing_attestation(source_id, scope, model, output)
```

This is the user's exact verbal model. Genomics, phenome, intel all benefit immediately. Intel benefits most because it currently does no paper-fetch attestation at all and is the cold-start case.

### 1.5 What this is NOT

- Not a knowledge graph. The federation surface is presence/provenance, not semantic claims.
- Not a replacement for repo-local attestations. It's a *thin* federation layer on top of them.
- Not write-coordinated. Each repo writes to its own store on its own schedule. Read view is unified.
- Not auth-aware. Single-user system; all queries are local-file reads.

## Section 2 — Skills to extract

Concrete proposals ranked by ROI (value / maintenance). All are skill-level, not project-level — they live in `~/Projects/skills/` and propagate to all repos.

### 2.1 `citation-audit` (HIGH ROI — strongest candidate from the sweep)

**Problem:** Phenome has 9 partially-overlapping verifier scripts (`audit_citations.py`, `extract_citation_ids.py`, `verify_citation_ids.py`, `audit_research_memo_contract.py`, `validate_genomics_citations.py`, `verify_quantitative_claims.py`, `verify_variant_claims.py`, `verify_pgx_consistency.py`, `verify_protocol_claims.py`). All do DOI/PMID/PMCID/NCT extract → CrossRef/NCBI/S2 resolve → context diff. Genomics and intel both do equivalent work ad hoc.

**Skill contract:**
```
skill: citation-audit
inputs: file_path | text_block
outputs: report of {citation_id, resolution_status, title_match, year_match, author_overlap, drift_warnings}
checks:
  - DOI/PMID/PMCID/NCT regex extraction
  - resolve via CrossRef / NCBI E-utils / S2 / OpenAlex (cached 7d)
  - title token-overlap < 0.5 → drift warning
  - PMID > current frontier → ceiling-check failure (hallucinated citation)
  - context paragraph compared against abstract / first 500 words → context-mismatch warning
backends: research-mcp.verify_claim, research-mcp.search_papers, scite if available
```

**Migration plan:** Build skill in `~/Projects/skills/citation-audit/`, delete the 9 phenome scripts, point genomics' `validate_genomics_citations.py` callers at the skill. One commit per delete.

**Maintenance:** Low. The regex pack hasn't changed in years; backends are existing MCPs.

### 2.2 `attest-before-fetch` (HIGH ROI — wires the substrate into agent flow)

**Problem:** Agents fetch papers they've fetched before because they don't know to look.

**Skill contract:**
```
skill: attest-before-fetch
description: |
  Use before any paper/source fetch operation. Queries the cross-attestation
  federation for prior work. If a sufficient-grade attestation exists, return
  its artifact_uri instead of fetching. If not, proceed to fetch and register
  a new attestation row.
inputs: source_id (doi:/pmid:/etc), required_scope, required_model_grade
outputs: {action: "use_cached" | "fetch_fresh", artifact_uri?, attestation_id?}
```

This skill *is* the federation MCP's primary user. Bundle them.

**Maintenance:** Low if Section 1 ships. Otherwise pointless.

### 2.3 `cleanup-and-close` (MEDIUM ROI — addresses friction Cat. "Post-Implementation Closeout Loop")

**Problem:** Friction report flagged 5 sessions where post-task closeout (`/critique close` + docs regen + index regen + git commit) was a multi-step manual ritual.

**Skill contract:**
```
skill: cleanup-and-close
description: |
  Run after the user signals task completion ('done', 'lgtm', 'ship it').
  Chains: (1) regenerate codebase/research indexes; (2) regenerate any
  fingerprinted docs; (3) run repo-specific 'just sync-docs' equivalents;
  (4) propose granular commits; (5) if multi-phase plan, mark phase complete
  in plan file.
```

This is a workflow skill, not a thinking skill. Worth it because the same five-step chain happens hundreds of times.

**Maintenance:** Medium — each repo has slightly different sync commands. Solved by per-repo `just close` recipes that the skill calls.

### 2.4 `phase-gate` (MEDIUM ROI — addresses friction Cat. 3 "Premature Build")

**Problem:** Agent treats overall plan approval as approval for all phases. Result: phase 2 starts before phase 1 is reviewed, requires revert.

**Mechanism:** Not a skill, a hook. After any plan-file write/edit, scan for phase markers. After tool call within a plan-mode session, check current phase ≤ approved phase. If violation, block with advisory "Phase 2 not approved — current approval is Phase 1 only."

Implement as hook in `~/Projects/skills/hooks/pretool-phase-gate.sh`. Already partially described in Constitution Principle "multi-phase plans" — gap is runtime enforcement.

### 2.5 `dont-route-around-hooks` (LOW ROI but BLOCKING)

**Problem:** Friction Cat. 8 — when spinning-detector blocks an MCP tool, agents direct-import the underlying library to bypass.

**Mechanism:** PreToolUse hook on Python script execution (Bash with `uv run`): if the spinning-detector has fired in the last N turns AND the script imports a module from the same MCP server family, surface advisory. Soft block (advisory, not hard fail).

This is the harder version: the bypass is *invisible* to current hooks because the import path doesn't pass through MCP. Detection needs a Python AST scan, not a string match.

Defer until measured — only 2 confirmed incidents in the friction report. Note as a known gap.

### 2.6 Skills that already exist — migrate, don't rebuild

- **PDF → markdown:** phenome's report claimed a `markitdown` skill exists. It does not under `~/Projects/skills/` (verified). The pattern (PDF→markdown→structured rows) is repeated 3× in phenome (`extract_lab_pdfs.py`, `extract_medical_pdfs.py`, `ingest_pdf.py`). Build the skill: `pdf-to-markdown`. Or fold into research-mcp's `fetch_paper`.
- **`entity-management`** exists and is shared. The frontmatter contract is the convention. Don't duplicate.
- **`bio-verify`** exists and is genomics-led. Could generalize to "hardcoded-constant audit" but defer until a non-bio caller actually wants it.

## Section 3 — Hooks to add

Friction-informed. Each is one specific predicate.

| Hook | Trigger | Action | Severity |
|---|---|---|---|
| `pretool-phase-gate.sh` | Tool call in plan-mode session past last-approved phase | Advisory block with current phase number | Advisory |
| `pretool-attest-before-fetch.sh` | research-mcp.fetch_paper or any paper-URL fetch | Inject reminder to query `cross_attestation_lookup` first | Advisory |
| `posttool-paper-fetch-register.sh` | research-mcp.fetch_paper completes | Auto-write attestation row | Silent (architecture-level) |
| `stop-execution-loop-watchdog.sh` | Agent emits status-without-action for 2+ turns on same delegated task | Advisory "you can run it" | Advisory (addresses Cat. 1) |
| `pretool-quantitative-claim-check.sh` | Tool output contains `costs X` / `takes Y seconds` keywords without a measuring tool call in the last 5 turns | Advisory "this looks like an estimate, not a measurement" | Advisory (addresses Cat. 5) |
| `pretool-dispatch-delete-guard.sh` | Edit/Write deletes a dispatch script (gemini/codex/etc.) | Force re-read of vetoed-decisions.md, ask "is this transport or capability?" | Advisory (addresses Cat. 6) |
| `posttool-genomics-pipeline-sync.sh` | Edit to genomics pipeline files | Run `just regen-clinical-sink-graph` + `just sync-generated-docs` | Auto-fix |

All advisory by default. Promote to blocking only with measured ROI.

## Section 4 — MCP servers

### 4.1 New: `cross-attestation-mcp`

Lives in `~/Projects/agent-infra/scripts/cross_attestation_mcp.py`. Read-only federation across the three repos + research-mcp.

Tools:
- `has_processed(source_id, scope?, min_evidence_depth?) → list[AttestationStub]`
- `list_processing_history(source_id) → list[AttestationStub]` — full chain for one source
- `find_unprocessed_in_scope(source_ids: list, scope, model) → list[str]` — bulk gap query
- `find_duplicated_work(window_days=7) → list` — diagnostic, finds same-source same-scope re-processings

Backed by DuckDB attached-database reads across:
- `~/Projects/genomics/data/knowledge/knowledge.duckdb` (read-only)
- `~/Projects/phenome/indexed/claims.duckdb` (read-only)
- `~/Projects/intel/indexed/theses.duckdb` (read-only)
- `~/Projects/research-mcp/data/papers.duckdb` (read-write — owns `paper_fetch_attestations` table)

### 4.2 Extend: `research-mcp`

Add the `paper_fetch_attestations` table and three new tools:
- `register_processing_attestation(...)` — write side
- `get_cached_processing(source_id, scope, min_model)` — read side
- `replay_processing(attestation_id)` — diff old vs new for the same source/prompt to detect drift

### 4.3 Adopt: `intel-theses` → start consuming research-mcp

Intel registers research-mcp but doesn't use it. Concrete first call site: `analysis/themes/genetic_medicine_modality_stack.md` references. Wire one biotech entity's literature lookups through research-mcp + cross-attestation-mcp as a pilot. If the attestation cache catches even one duplicate fetch within a week, the bridge is paying.

### 4.4 Defer: `biomedical-mcp`, `paperclip`, `scite`, `duckdb`, `parallel`, `agent-infra-mcp`

All exist and are fine. No changes proposed.

## Section 5 — Frontier feature adoption (from 05-frontier-tooling)

Five things to evaluate in concrete pilot orderings:

### 5.1 Claude Code task budgets (`task-budgets-2026-03-13` beta) — **PILOT THIS WEEK**

Model gets a running token countdown for the whole agentic loop. Directly replaces the instruction-only "stop searching at 70% of turns" rule that the dispatch hook enforces. If it works, the hook becomes belt-and-suspenders.

Pilot: enable on one researcher subagent dispatch, observe whether the stop-at-70% behavior improves vs the hook-blocked instruction.

### 5.2 Codex `/goal` mode (CLI 0.128.0, 2026-04-30) — **PILOT FOR ORCHESTRATOR QUEUE**

Persistent objectives survive interrupts. Maps onto `scripts/orchestrator.py` queue items that are currently run manually. Pilot: wrap the next "monthly research sweep" or "weekly trending scout" as a Codex `/goal` and compare to running it under our orchestrator.

Caveat: docs lag implementation as of 2026-05-04. Don't migrate critical workflows yet.

### 5.3 `PostToolUse updatedToolOutput` for all tools (2026-04 onward) — **ADOPT WHEN A USE CASE LANDS**

Hook can now rewrite Bash/Read/Edit output mid-flight (previously MCP-only). Concrete use: a postwrite source-tagging pass that auto-injects `[A1]`-style grades on Edit operations to research/decisions files. Build when the source-grading pass becomes the bottleneck.

### 5.4 OpenCode as fallback harness — **EVALUATE WHEN RATE-LIMITED**

Reads existing `CLAUDE.md` + skills natively, MIT-licensed, 75+ providers. Not a migration; a fallback when Claude Code / Codex are throttled. One Modal genomics session as a test.

### 5.5 Streamable HTTP transport for new MCPs — **CONVENTION FOR NEW WORK ONLY**

Stdio is fine for existing MCPs. New MCP work (including `cross-attestation-mcp` above) should be Streamable HTTP if there's any chance of cross-machine or cross-project sharing.

## Section 6 — Anti-patterns to surface for /critique model

Things this proposal might be wrong about. Adversarial pressure points:

1. **Is the federation MCP the right call vs. a unified DB?** The veto on knowledge-substrate MCP is from a different context (no real attestation stores existed then). With three actual attestation stores in production, the trade-off may differ. **Adversarial prompt:** "Argue that the three attestation stores should be merged into a single DuckDB owned by agent-infra. What does that buy that federation doesn't?"

2. **Is `paper_fetch_attestations` the right grain?** Could be claim-level instead of paper-level. Trade-off: paper-level matches the user's verbal model; claim-level matches genomics' existing schema. **Adversarial prompt:** "Why not just extend genomics' `claim_verdicts` to be cross-project and let phenome/intel write to it?"

3. **Is "model attribution at scope level" enough?** Or do we need per-token / per-section attribution? **Adversarial prompt:** "When two models process the same paper for the same scope and produce different summaries, what does the attestation layer surface? Is one canonical?"

4. **Skill vs MCP boundary for citation-audit.** Could equally live in research-mcp. **Adversarial prompt:** "Why is citation-audit a skill not an MCP tool?"

5. **Is the friction Cat. 1 fix right?** Stop-execution-loop-watchdog could itself become noise. **Adversarial prompt:** "Construct a session where this hook fires wrongly and the user actually did want a check-in."

6. **Are we under-investing in Direction-E / cert-stack productization?** Both are settling. Both could absorb the new substrate. **Adversarial prompt:** "Argue that we should wait 30 days before any cross-project substrate work and let direction-E and cert-stack stabilize first."

## Section 7 — Phasing

| Phase | Scope | Duration | Gate |
|---|---|---|---|
| **Phase 0 — review** | This memo through `/critique model`, revise cosigned/deferred/rejected list, write `decisions/2026-05-XX-cross-attestation.md` | This week | User approves selection-rationale.md before any code |
| **Phase 1 — citation-audit skill** | Build `~/Projects/skills/citation-audit/`, migrate phenome's 9 scripts, validate on a research memo | 1-2 sessions | Skill produces same output as the existing scripts on 10 sample memos |
| **Phase 2 — research-mcp paper_fetch_attestations table** | Schema + register tool + cache lookup tool, wire into research-mcp's existing `fetch_paper` | 1-2 sessions | Re-fetching a known paper returns cached markdown without network call |
| **Phase 3 — cross-attestation-mcp federation server** | DuckDB attached-DB read across three repos + research-mcp; `has_processed` and `list_processing_history` tools | 2-3 sessions | Query returns expected results for 5 known cross-repo source IDs |
| **Phase 4 — attest-before-fetch skill** | Workflow skill wiring the above into agent decision flow; per-repo CLAUDE.md updates pointing to it | 1 session | One intel biotech entity lookup successfully short-circuits a duplicate phenome fetch |
| **Phase 5 — friction hooks** | Phase-gate, stop-execution-loop-watchdog, posttool-genomics-pipeline-sync | 1-2 sessions | Each hook measures fewer than 5 false-positive triggers per week |
| **Phase 6 — frontier pilots** | Task-budgets beta on one subagent; Codex `/goal` on one orchestrator item; OpenCode session for genomics modal work | Parallel with phases 1-5 | Each pilot produces a written assessment in `decisions/` |

Each phase is its own commit. Critique-close after each. Don't bundle.

## Section 8 — Explicit non-decisions

Things the user mentioned that this synthesis explicitly does NOT decide:

- **Whether to migrate from Claude Code to OpenCode.** Out of scope; just propose pilot.
- **Whether biotech investing actually happens.** Bridges are architected so intel benefits without requiring it; the question can be deferred.
- **Whether the cert-stack productization (Synthoria) survives the 90-day evidence gate.** Independent decision; the federation MCP doesn't depend on it either way.
- **Whether to retire `scripts/orchestrator.py` for Codex `/goal`.** Pilot first; don't commit.

## Section 9 — One paragraph for the user

You already have three working attestation systems. Genomics' is the most mature schema-wise, phenome's is the most ambitious cert-shape-wise, intel's is the most operationally polished. None of them needs to be merged. What you described — "every time a paper gets fetched, see if we already processed this and with what model" — is a thin federation MCP across the three stores plus a paper-fetch attestation table inside research-mcp. Five-line lookup contract, one new MCP, one extended MCP, one new skill, three friction-informed hooks. The hardest part is the chess game with `direction-E` and `cert-stack` both still settling — propose to wait on schema-level integration with their internals, build only the federation surface. Skills like citation-audit and cleanup-and-close are immediately worth extracting independent of the substrate work. Frontier features (task budgets, Codex `/goal`, OpenCode) are pilots, not migrations.

## For the /critique model pass

Reviewer: please pressure-test specifically the six adversarial prompts in Section 6, plus:

1. Is the option matrix in "Divergent options considered" complete or is there a sixth mechanism I missed?
2. Does the schema in 1.2 collapse under stress (model produces different output for same input due to non-determinism — how do we represent "two valid attestations for the same scope")?
3. Is Phase 4 too early — should attestation-before-fetch ship before any agent flow uses it?
4. Are any of the proposed hooks already implemented under different names that I missed?
5. Is the federation MCP write side missing — should it support write-through to repo-local stores, or is read-only correct?

Cosign, defer, or reject each proposal in Sections 1-5. Flag schema risks. Flag adoption risks. The user values "no" answers — say so if so.

---

## Revisions — 2026-05-11 post-critique

Sections 1-7 above are the original proposal. This block supersedes the rejected/reframed pieces after `/critique model` (74 findings, Gemini Pro + Gemini-arch + GPT-5.5 + Gemini Flash mechanical). Disposition artifacts live at `.model-review/2026-05-11-cross-project-attestation-substrate-b397f6/`.

User decisions (2026-05-11):
1. **Defer federation work ~1 week.** Direction-E agent is actively executing in genomics; do not introduce read-side coupling against its schema while it's settling. Phase 0 measurement proceeds independently.
2. **Revisions appended in place** rather than as a separate memo.
3. **Phase 0 opportunity logger ships now** to validate the duplicate-fetch premise empirically.

### What changed

**Superseded (do not build as originally specified):**

- **§1.2 `paper_fetch_attestations` public schema — REJECTED.** Fetching a paper is a provenance event, not knowledge. It would split-brain with genomics' `source_observations` + `evidence_bindings`. **Replace with:** transparent internal cache inside `research-mcp.fetch_paper()`. No new semantic public schema.
- **§1.4 attest-before-fetch agent flow — REJECTED as skill+hook architecture.** Was "architecture by advisory." **Replace with:** cache lookup INSIDE `research-mcp.fetch_paper()`. Delete the proposed `attest-before-fetch` skill, the `pretool-attest-before-fetch.sh` hook, and the `posttool-paper-fetch-register.sh` hook. The tool itself decides.
- **§2.1 `citation-audit` as a Claude skill — REJECTED.** DOI/PMID resolution is network + rate-limit + persistent cache work; a Bash/regex-driven skill is a fragile three-turn loop. **Replace with:** MCP tool `research_mcp.audit_citations(text_block)`. Phenome's 9 scripts migrate to call it (with a grep/import-graph proof before any deletion — Finding #7 in disposition).
- **§3 `stop-execution-loop-watchdog.sh` — DROPPED.** Would false-positive on long Modal/WGS jobs that legitimately poll for hours. The underlying premature-pause friction (Cat. 1) needs tool-managed job state (IDs, status, polling contract, cancellation), not an advisory watchdog. Defer concrete fix until either Claude Code task-budgets pilot or Codex `/goal` adoption gives us the right primitive.
- **§3 `pretool-quantitative-claim-check.sh` (text-matching version) — DROPPED.** Phrase matching on "costs X" / "takes Y" produces too many false positives on quotes/abstracts. Phenome already has `verify_quantitative_claims.py`; if this hook is ever built, it reuses that verifier — not duplicates it.
- **§2.5 `dont-route-around-hooks` — DEFERRED.** Only 2 confirmed incidents; AST-scanning PreToolUse hooks are brittle and slow. Re-evaluate after 10+ incidents.
- **§4.1 standalone `cross-attestation-mcp` HTTP/stdio server — REJECTED in favor of a single MCP tool.** All four repos live on one Mac. A DuckDB `ATTACH '~/Projects/genomics/data/knowledge/knowledge.duckdb' AS gen` plus equivalent for the other repos gives federation in ~30 lines. **Replace with:** one tool `cross_attestation_lookup(source_id)` inside `agent-infra-mcp`, not a new server.

**Reframed (build as revised):**

- **Cache + alias resolver inside `research-mcp.fetch_paper()`.** New Phase 0.5: DOI ↔ PMID ↔ PMCID alias clustering via CrossRef + NCBI eutils. Canonicalize to one cluster ID before any cache hit / miss decision. Without this, lookup-by-one-ID misses duplicate work recorded under another alias (disposition #6).
- **Federation contract = read-only views with fail-soft locking.** Each repo exposes `claim_verdicts` / `kg_attestations` / `theses` through stable read-only DuckDB views; federation tool reads views, never internal tables. Read timeouts → "unknown" stub return rather than blocking the agent turn (disposition #17, #55 — `~/Projects/genomics/data/knowledge/writer.lock` confirmed present 2026-05-11).
- **OpenAlex as default resolver; S2 fallback only.** S2 rate-limits aggressively. Already a known gotcha in `~/.claude/rules/llmx-routing.md`; promote to *default* policy in citation-audit.
- **Sci-Hub removed from `fetched_via` enum.** Not a stable API. Keep as best-effort/unsupported only.

**Cosigned (build unchanged):**

- `cleanup-and-close` skill — standardized end-of-loop automation.
- `phase-gate` + `pretool-phase-gate` hook — mechanically enforces Constitution Principle on multi-phase plans.
- `pretool-dispatch-delete-guard` — deletion protection around dispatch scripts.
- `posttool-genomics-pipeline-sync` — auto-run `just regen-clinical-sink-graph` + `just sync-generated-docs` after pipeline edits.
- Intel-theses → research-mcp bridge — high-ROI gap. Wire one biotech entity's literature lookups through research-mcp + the alias resolver as the pilot.
- Frontier feature pilots — Claude Code task budgets, Codex `/goal`, OpenCode — with isolated blast radius, written assessments in `decisions/`.

**Mechanical corrections to the original text:**

- **§1.2 / §4.1: research-mcp is SQLite, not DuckDB.** Verified: `~/Projects/research-mcp/src/research_mcp/db.py` uses `sqlite3`; store is `data/papers.db`. The original `data/papers.duckdb` reference is wrong throughout.
- **§4.1: `cross-attestation-mcp` no longer applies** — collapsed into a single tool. See "Revised architecture" below for the canonical name.
- **§1.3 / §1.2: enum mismatch.** Lookup contract used `raw_fetch / summary / claims / full_synthesis`; schema used `raw_markdown / summary / claims_extracted / full_synthesis`. With the schema rejected, the enum collapses to whatever the resolver tool returns.
- **§5.2: `scripts/orchestrator.py` was archived 2026-04-24.** The original §5.2 framed it as currently-running. Codex `/goal` pilot now replaces "compare to running it under our orchestrator" with "compare to a manual baseline."
- **§ source-dispatches in the overview**: `04-session-friction.md` was marked pending; it has landed.

### Revised architecture (canonical)

```
research-mcp (SQLite at ~/Projects/research-mcp/data/papers.db)
├── fetch_paper(source_id)        # transparent cache + alias resolution INSIDE the tool
├── audit_citations(text_block)   # NEW: MCP tool, formerly proposed as a skill
└── fetch_log                     # NEW: Phase 0 measurement table (7-day premise validation)

agent-infra-mcp
└── cross_attestation_lookup(source_id) → list[AttestationStub]
                                  # NEW: single tool, DuckDB ATTACH-based,
                                  # reads stable views in genomics/phenome/intel,
                                  # fail-soft on writer.lock contention
                                  # (NOT built this week — waits for direction-E)
```

### Revised phasing

| Phase | Scope | Status |
|---|---|---|
| **0** | `fetch_log` table in research-mcp + `analyze_fetch_log.py` — measures duplicate-fetch rate over 7 days | **Ship now (2026-05-11)** |
| **0.5** | DOI ↔ PMID ↔ PMCID alias resolver inside research-mcp | Ships after Phase 0 row count justifies; ~1 session of work |
| **1** | `research_mcp.audit_citations()` MCP tool, migrate phenome's 9 scripts (after grep/import-graph proof) | Independent of attestation work; can ship anytime |
| **2** | Transparent cache inside `fetch_paper()` keyed on canonical cluster ID | Gated on Phase 0 measurement: build only if duplicate rate ≥ 10% |
| **3** | Cosigned hooks: phase-gate, dispatch-delete-guard, genomics-pipeline-sync | Ship in parallel; each its own commit |
| **4** | `cleanup-and-close` skill | Ship in parallel |
| **5** | Frontier pilots: task-budgets / Codex `/goal` / OpenCode | Parallel; one written `decisions/` assessment per pilot |
| **6** | `cross_attestation_lookup` tool — DuckDB ATTACH federation over stable views | **Hold ~1 week** until genomics direction-E quiesces. Re-evaluate after Phase 0 data is in. |

### Divergent question — resolution

The reviewer divergence (wait 30 days vs build behind stable views now) is resolved by user direction: **wait ~1 week, decide empirically from Phase 0 data**. The architecture is "build behind stable read-only views eventually"; the timing is "after direction-E quiesces so we're not federating against a moving target." The 7 days of measurement is the bridge.

### What's deliberately NOT decided yet

- Whether to retire `scripts/orchestrator.py` permanently or reactivate it after Codex `/goal` pilot.
- Whether OpenCode becomes a fallback harness or just a pilot.
- Whether intel ever attests against the substrate (gated on Phase 0 finding cross-repo overlap on DOI/PMID lookups; disposition #74 flagged that ticker workflows may have ~0 overlap with phenome/genomics).
- Whether the read-only views in genomics get a versioned contract (e.g., `v_claim_verdicts_v1`) or stay un-versioned. Decide when actually building Phase 6.

### Open finding to surface explicitly

**Cross-repo entity resolution beyond DOI/PMID is out of scope for v1.** Intel-phenome bridge needs ticker→gene→trial→paper. The federation tool only handles paper-identity. The entity bridge is a separate, later, harder problem. Mark and move on.

<!-- knowledge-index
generated: 2026-05-11T04:31:34Z
hash: 8953604af827

title: Cross-Project Synthesis — Skills, Hooks, MCPs, and the Scientific Knowledge Substrate
status: revised-post-critique
cross_refs: analysis/themes/genetic_medicine_modality_stack.md, decisions/2026-05-XX-cross-attestation.md
table_claims: 2

end-knowledge-index -->
