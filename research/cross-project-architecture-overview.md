---
title: Cross-Project Architecture Overview — phenome × genomics × intel × agent-infra
date: 2026-05-11
tags: [architecture, cross-project, attestation, mcp, history, orientation]
status: active
---

# Cross-Project Architecture Overview

Durable reference. If you are an agent walking into phenome, genomics, intel, or agent-infra and need to understand the shape of the whole — start here. Compiled 2026-05-11 from a 5-agent archaeology sweep (subagent reports in `research/cross-project-synthesis-2026-05-11/`). Revisit when you observe drift; revise rather than rebuild.

## The constellation

Four repos under `~/Projects/`, owned by one user, evolving in parallel:

| Repo | Role | Defining stance |
|---|---|---|
| **phenome** | Personal knowledge manifold (89K entries / 25 sources) + clinical/genomics KG + cert-stack proof-carrying answers + Synthoria business research. ~50K LOC. | **Correctness-maximal.** Schema-level invariants beat caller discipline. Breaking-refactors-by-default. Append-only with inline annotation, never deletion. |
| **genomics** | Personal WGS interpretation (Nebula 30x + PacBio + Illumina blood) → variant calling → annotation → trait/PGx/blood-group/oncology → clinical-grade review packets. Modal-backed stage DAG, DuckDB knowledge ledger. ~700 scripts. | **Event-sourced, model-attributed, source-versioned.** Single-writer gateway + lints + audit. Bitemporal verdicts. Direction-E "rederivation infrastructure" is the current workstream. |
| **intel** | Adversarial intelligence service for public-market investing. 2 GB DuckDB (658 tables / 672 views) joining ~610 datasets (CMS, NPPES, SEC EDGAR, FAERS, ClinicalTrials.gov, FDA, OSHA, EPA, BLS, USAspending, OpenSanctions, Companies House, IRS 990s, ...). 397 scripts. 343 entity files (tickers). 21 themes. Own MCP (`intel-theses`). | **Markdown-canonical, DB-derivable, error-correction-by-market-feedback.** 12-axis closure FSM gates entry-readiness. Source-grade-on-write (`[A1]`–`[F6]`). Scoring framework just hard-stripped 2026-05-10. |
| **agent-infra** | "Thinking about thinking" repo. Plans/tracks improvements to the other three. Constitution + governance layer. Hooks/skills/rules that propagate to the others. `/observe` retros, improvement-log, decisions journal, runlog DB. | **Architecture over instructions** (instructions-alone ≈ 0% reliable). Filter by maintenance, not effort. Cross-model review for non-trivial decisions. |

Plus the shared substrate they all depend on:

- `~/Projects/skills/` — skill definitions, hooks symlinked into each repo's `.claude/`. ~40 skills (analyze, bio-verify, browse, brainstorm, census-data, critique, data-acquisition, entity-management, life-science-research, modal, observe, profiles, research, research-ops, scientific-drawing, sweep, trending-scout, upgrade, ...).
- `~/Projects/research-mcp/` — the cross-project paper/source MCP (`research_mcp` package). Caches at `data/`. Registered in phenome and intel `.mcp.json`. Heavily used by phenome, **registered but ~unused by intel** (highest-ROI bridge gap).
- `~/Projects/biomedical-mcp/` — sibling repo, editable install, exposes ClinVar/gnomAD/PharmGKB/dbSNP/Ensembl/PanelApp/HPO tools to genomics' `bio-verify`.

## The three attestation systems (the keystone)

All three scientific repos independently evolved an "attestation" pattern — record what model did what work when, against what content, using what context — to prevent silent rework, model drift, and untraceable claim edits. They are now close enough to unify, but they are not the same.

### genomics — `claim_verdicts` (event-sourced, bitemporal)

- DB: `~/Projects/genomics/data/knowledge/knowledge.duckdb`, schema `migrations/2026-05-09-knowledge-tables.sql`.
- Core table `claim_verdicts` (492 rows, INSERT-only):
  ```
  verdict_id, claim_id, support_state, review_status,
  model_version, prompt_template_hash, canary_window_id,
  asserted_at, valid_from,                  -- bitemporal pair
  evidence_event_id,
  verdict_projection_hash,
  evidence_projection_hash,
  claim_binding_hash
  ```
- Surrounding tables: `assertions` (predicate-registry-pinned, empty pending backfill), `evidence_bindings`, `source_observations`, `knowledge_releases`, `rederivation_triggers` (1980 rows: hygiene_defect/cascade/rebind), `trigger_drain_events`, `canary_windows/results`, `verdict_supersedings`.
- Write path: `scripts/knowledge/mutation_gateway.py` is the sole writer. Two-phase commit across DuckDB + FS sidecars (`config/source_retrievals/*_provenance.json`). File lock at `data/knowledge/writer.lock`.
- Enforcement: `lint_no_direct_writes.py` (bans `INSERT` outside gateway) + `audit_immutability.py` (periodic). Five custom lints total — every "instructions" guardrail got promoted to architecture after failing.
- Settling signal: all 492 verdicts have `model_version='direction-d-router-stub'`. The schema is real; real-model attribution is upcoming.

### phenome — cert-stack (composable typed certificates)

- Code: `src/phenome/{bridge,certificates,answerability,identity,diagnostics,explain,upstream}/`.
- Four cert types, all content-addressed (`UUID5` or sha256 over canonical slot tuples, with `CANONICAL_HASH_EXCLUSIONS` for wall-clock + per-emission UUIDs):
  - `KGAttestation` — wraps any MCP-emitted KG-derived data. Constants like `source_authority="third_party_aggregated_kg"`, `safe_for_unqualified_use=False` cannot be relaxed by callers.
  - `ClaimClosureCertificate` — per-assertion proof.
  - `BridgeSnapshotCertificate` — content-addressed substrate snapshot.
  - `AnswerabilityVerdict` — composes the others via lattice meet: `SURFACE_ERROR < CANNOT_CERTIFY < CANNOT_ANSWER_FROM_LOCAL_REPO < ANSWERABLE_WITH_WARNINGS < CERTIFIED`.
- Seam: `CertifiableDependency` protocol (`bridge/kg.py:27`) — uniform interface so all four compose.
- 8-plan architectural spike at `.claude/plans/8799d138-cert-stack-{00..08}`. Every plan needed multiple `/critique close finding #N` commits.
- Productization (`Synthoria`) was deferred (`d170c92`), reopened with 90-day evidence gate (`a1e3c8a`). Treat as opinionated; verify the gate before promoting heavily.

### intel — theses graph + closure FSM (predicates + entry-readiness gate)

- Code: `tools/theses/` — `predicates.py` (33 predicates × 9 families), `slot_vocab.py` (18 slots), `closure/` (12-axis entry FSM + 6-axis monitoring), `schema.sql`, `rebuild.py`, `extract_frontmatter.py`, `upstream_daemon.py`.
- DB: `intel/intel/indexed/theses.duckdb` — note the nested `intel/intel/` path. Derived from markdown frontmatter (`analysis/entities/{TICKER}.md`, `analysis/themes/*.md`). Markdown canonical, DB rebuildable.
- MCP: `intel-theses` (`scripts/theses_mcp.py`). Replaces legacy `knowledge-substrate` MCP.
- Source grading lives in the markdown body itself (`[A1]`–`[F6]` NATO Admiralty + `[DATA]` for own-DuckDB). Not in a separate table.
- The closure FSM is the analog of genomics' `claim_verdicts.review_status` enum — it gates whether an entity is "entry-ready" against a `ProspectiveState = DB ∪ proposed_delta`.

### Side-by-side

| Axis | genomics | phenome | intel |
|---|---|---|---|
| Storage | DuckDB event log | Python dataclasses + DuckDB claim store | Markdown frontmatter, DuckDB derived |
| Identity | `verdict_id` content-hash | `UUID5` over canonical slot tuple | Ticker symbol + ISO market |
| Model attribution | First-class (`model_version`, `prompt_template_hash`, `canary_window_id`) | Second-class (provenance in cert body) | Implicit (per-edit git author, not per-claim) |
| Bitemporal | Yes (`asserted_at` + `valid_from`) | No | No |
| Source grading | `evidence_grade` (A1/A2/B/...) × `stake_tier` (clinical/behavioral/exploratory) | Source authority enum on `KGAttestation` | `[A1]`-`[F6]` NATO Admiralty inline |
| Write enforcement | Gateway + lint + audit (3 layers) | Pretool-append-only-guard hook | Same hook + closure FSM |
| Read for "did we do this" | `project_verdicts.py`, `as_of.py` | `bridge/kg.py` callers | Entity file glob + DuckDB query |

The unification target is **not** to merge these into one — each fits its repo's tempo. The target is to surface them through a **common cross-project lookup**: "before fetching/processing X, has any repo already attested to it?"

## Cross-repo touchpoints (current)

```
              ┌──────────────────────────────────────────────────────┐
              │              ~/Projects/skills/  (symlinked)         │
              │  entity-management, bio-verify, research, modal,     │
              │  observe, critique, brainstorm, sweep, hooks/        │
              └──────────────────────────────────────────────────────┘
                             ▲          ▲           ▲          ▲
                             │          │           │          │
                       ┌─────┴───┐ ┌────┴─────┐ ┌───┴────┐ ┌───┴───┐
                       │ phenome │ │ genomics │ │  intel │ │  meta │
                       └────┬────┘ └────┬─────┘ └────┬───┘ └───┬───┘
                            │           │            │         │
                            │           │            │         │
            ┌───────────────┼───────────┼────────────┘         │
            │               │           │                      │
            ▼               ▼           ▼                      ▼
    research-mcp         biomedical-mcp                  research/
   (papers, sources)    (ClinVar, gnomAD,                improvement-log
                        PharmGKB, dbSNP,                 decisions/
                        Ensembl, PanelApp,
                        HPO — used by
                        genomics' bio-verify)

  phenome → genomics:  genomics_bridge (deleted) → genomics-consumer MCP (live)
  genomics → phenome:  none direct (data flows through bridge contract files)
  intel    → phenome:  none (research-mcp registered but unused — bridge gap)
  intel    → genomics: none direct
  meta     → all:      observe artifacts at artifacts/observe/, MCP at agent-infra
```

Concrete artifacts:

- **phenome consumes genomics** via `genomics-consumer` MCP and bridge contract files in `phenome/scripts/`: `materialize_genomics_bridge_report.py`, `sync_genomics_bridge.py`, `export_genomics_phenotype_contract.py`, `build_genomics_registry.py`. The `genomics_bridge.py` wrapper was deleted (`eba7145`) after cert-stack landed.
- **intel registers `research-mcp`** in `.mcp.json` but search across `analysis/` finds essentially zero invocations of `search_papers`, `ask_papers`, `prepare_evidence`, `verify_claim`. Citations come from out-of-band Exa/Perplexity/scite or training data. NEJM DOIs in `NTLA.md` are pasted, not fetched-and-attested.
- **All three** load skills from `~/Projects/skills/` and hooks via symlinks under `~/Projects/skills/hooks/`.
- **All three** are indexed in `~/.claude/runlogs.db` (vendor-normalized session/commit log) and surfaced via `agent-infra-mcp`.
- **`/observe` artifacts** at `~/Projects/agent-infra/artifacts/observe/{sessions, architecture-2026-05-11-2d, supervision, session-retro}/` contain pre-clustered findings from earlier session analyses — use as structured starting layer.

## Patterns worth knowing (recurring across repos)

1. **Append-only with inline annotation, never deletion.** Self-reports, research memos, entity pages, todos. Enforced by `~/Projects/skills/hooks/pretool-append-only-guard.sh`. Convention: completed-but-superseded items get an inline `**⚠ YYYY-MM-DD update:**` annotation. Phenome's `caf8867` (IL6R wrong PMIDs annotated inline) is canonical.
2. **Content-addressable IDs over canonical slot tuples.** `UUID5(namespace, canonical-tuple)` for claims (phenome `claims/identity.py`, `IDENTITY_VERSION=4`), `sha256` projection hashes for genomics verdicts. Same idea: re-ingest must not break references.
3. **Single-writer gateway + lint + audit.** Genomics' three-layer immutability is the reference. Phenome's pretool guard is the lighter version. Pattern: if the DB can refuse a bad state, make it refuse.
4. **Two-phase commit across DB + FS sidecars.** `MutationGateway.__exit__` in genomics: DuckDB BEGIN/COMMIT spans the gateway block, FS sidecars staged to tempfiles then `os.replace`d after DB commit. Recovery via `_reap_orphaned_staged_writes()` on next entry.
5. **SourceAdapter Protocol.** Genomics' `scripts/knowledge/adapters/{clinvar,clingen,pharmgkb,gnomad,pubmed,pmc,crossref,openalex,unpaywall}.py` are uniform — same fetch/parse/normalize seam. Phenome's research-mcp clients follow the same pattern. Intel's external-feed pulls do not (and should).
6. **Paper fetch fallback chain.** Sci-Hub → OA → EuropePMC → biorxiv-by-title. Lives in genomics `_bulk_fetch_via_research_lib.py`, `_last_resort_fulltext.py`, `_prefetch_fulltext_summaries.py`. Should be in research-mcp.
7. **Source grade × stake tier.** Decouples "how good is the source" from "how high are the stakes for this claim." `evidence_grade` × `stake_tier` in genomics; `[A1]`–`[F6]` × conviction in intel; phenome's `KGAttestation` constants do this implicitly.
8. **LLM-as-proposer, not committer.** `propose_attestation.py` writes to `proposals/attestation/`; `commit_proposed_attestation.py` is the gated entry. The same pattern: intel's `tools/theses/closure/` gates entity entry, phenome's stop-research-gate hook gates memo finalization.
9. **Bitemporal storage** (`asserted_at` = transaction time; `valid_from` = world time). Genomics has it; the others would benefit when claim semantics are versioned independently of when they were asserted.
10. **Markdown canonical, DB derivable.** Intel made this explicit; phenome and genomics both *do* this (`config/claim_registry.json` in genomics is sidecar to DuckDB), but it's not stated as policy.
11. **Predicate registry** for versioned claim semantics. Genomics' `config/claim_registry.json` predicate registry + `predicate_registry_version` + `predicate_slot_schema_hash`. Phenome's 56 typed predicates × 9 families in `claims/predicates.py`. Intel's 33 predicates × 9 families in `tools/theses/predicates.py`. **Three independent implementations of the same shape.**
12. **Fact-tag injection.** Phenome's `<!-- fact:name -->VALUE<!-- /fact -->` syncs from DB via `just sync-docs`. Cleanest solution to CLAUDE.md count drift.
13. **Frontmatter for search elevation.** `entity-management` skill is the contract. Same YAML keys (`title`, `tags`, `summary`, `last_reviewed`) across repos with intentional drift.
14. **Plan files per architectural spike** at `.claude/plans/{session_id[:8]}-{slug}.md`. Multi-phase plans. Critique-close commits after each phase.
15. **Skill hot-reload at `~/.claude/skills` and `.claude/skills`** (Claude Code v2.1.0+).
16. **Provenance preambles in research memos**, enforced by `stop-research-gate.sh`. "Provenance tags added to memo — stop hook compliance" appears 3× in phenome's last 100 commits.

## Vetoed approaches — do not re-propose

Listed in `~/Projects/agent-infra/.claude/rules/vetoed-decisions.md`. Highlights with reasoning:

- **Knowledge-substrate MCP rebuilds** (2026-03-24) — knowledge-index hook (100% coverage) solved the actual pain. Cao et al. retrieval paradox confirms retrieval layers hurt when native navigation dominates.
- **Repo-tools MCP** (2026-03-20) — retired at zero usage across 4,287 runs. Use CLI scripts via Bash.
- **Shared utility libraries across projects** — maintenance > value at current scale. Projects share skills/hooks/rules, not Python imports.
- **PyMC/ArviZ for telemetry** — 200MB dep for 75 data points. Use scipy/numpy.
- **Great Expectations / PageRank symbol graph / repomix whole-repo packing** — all assessed and rejected for our scale.
- **`finding-triage` SQLite DB** (2026-03-21) — inline improvement-log replaced it.
- **Compatibility shims by default** — unless a live external boundary is explicitly named, migrate callers and delete. (See `CLAUDE.md` Principle 14.)
- **Retry same Gemini model after 503** — switch to GPT or Flash for the session.
- **Reusing the older "use codex-cli sparingly" veto** — **superseded 2026-04-21**. Codex 0.121 added MCP disable flags. The `cli-lite` profile path is now open if measured <5K overhead.

## Open questions and work-in-progress

- **Genomics direction-E rederivation engine is still settling.** `assertions` table empty, `model_version='direction-d-router-stub'` on all verdicts, `source_summaries.duckdb` empty, 6+ backfill scripts in flight. Extract *patterns* now; wait on the full engine until real-model verdicts land and the assertion backfill completes.
- **Phenome cert-stack productization** opened/deferred/reopened cycle. The 90-day evidence gate post Roche/PathAI (`a1e3c8a`) is the live condition.
- **Intel just stripped its scoring framework** (2026-05-10 hard strip, archived at `.claude/rules/_archived/2026-05-10-full-strip/`). Constitution Principle 9 amended 2026-05-07 to remove parallel-portfolio tracking. Treat anything scoring-related in old commits as deprecated.
- **Bridge gap**: intel registers research-mcp but doesn't use it for biotech theses. Highest-ROI integration target.
- **Citation auditing is duplicated 9× inside phenome alone** (`audit_citations.py`, `extract_citation_ids.py`, `verify_citation_ids.py`, `audit_research_memo_contract.py`, `validate_genomics_citations.py`, `verify_quantitative_claims.py`, `verify_variant_claims.py`, `verify_pgx_consistency.py`, `verify_protocol_claims.py`). Same regex + resolvers each time.
- **PDF→markdown is done 3× in phenome** (`extract_lab_pdfs.py`, `extract_medical_pdfs.py`, `ingest_pdf.py`). Phenome's subagent report claimed a `markitdown` skill exists; it does not under `~/Projects/skills/`. Either it's named differently or the claim was wrong — verify before relying.

## Where the bridges should attach (forward-looking, factual)

These are observation, not commitment. The synthesis memo in `research/cross-project-synthesis-2026-05-11/06-synthesis-and-proposals.md` proposes concrete actions; future agents should treat that as a separate decision artifact subject to its own cross-model review.

1. **Citation-audit** is the highest-confidence shared-infrastructure target. 9 verifier scripts in phenome alone; intel and genomics both touch DOI/PMID/PMCID/NCT. Extract: `citation-audit` skill or `mcp__citations__{extract,resolve,verify_context,detect_drift}`.
2. **Attestation as portable schema**. Each repo has its own. The unification is **not** one table but a common "lookup before do" cross-project query: `has any repo attested to this source-id/claim-id/entity?`. Implementation: extend the agent-infra MCP with a `cross_attestation_lookup` tool that queries genomics' `claim_verdicts`, phenome's cert IDs, intel's theses graph.
3. **Paper fetch pipeline lives in research-mcp**. Genomics has hardened the fallback chain; promote that variant. Intel should be calling research-mcp's `search_papers`/`fetch_paper`/`ask_papers` for biotech theses, not pasting from Exa.
4. **SourceAdapter Protocol generalizes** across scientific sources (genomics has it) and financial/regulatory sources (intel has equivalent but unsystematic). Worth standardizing in agent-infra.
5. **Predicate registry pattern** is implemented three times. Worth a shared schema (JSON-schema + Python dataclasses) in agent-infra, even if the predicate sets stay domain-specific.
6. **Frontier features to evaluate**: Claude Code task budgets (`task-budgets-2026-03-13` beta), Codex `/goal` mode (CLI 0.128.0) for orchestrator queue items, Streamable HTTP transport for new MCPs, OpenCode as a fallback harness (reads existing `CLAUDE.md` + skills natively).

## How to use this memo

- **Walking into one repo for the first time?** Read that repo's section above + the relevant attestation system + the patterns list.
- **Proposing new shared infrastructure?** Check the vetoed list first. If it survives, write a decision in `agent-infra/decisions/` and trigger `/critique model`.
- **Building anything that touches multiple repos?** Trace the touchpoints diagram first. Routes that aren't drawn are most likely missing on purpose.
- **Updating this memo?** Append-only with inline annotation. Use `**⚠ YYYY-MM-DD update:**` for material corrections. Major shifts → new `## Revisions` entry at the bottom.

## Source dispatches

This memo synthesizes:

- `research/cross-project-synthesis-2026-05-11/01-phenome-patterns.md` — phenome inventory
- `research/cross-project-synthesis-2026-05-11/02-genomics-patterns.md` — genomics attestation schema (canonical reference)
- `research/cross-project-synthesis-2026-05-11/03-intel-patterns.md` — intel maturity and bridge gap
- `research/cross-project-synthesis-2026-05-11/04-session-friction.md` — end-of-session correction patterns (pending at time of writing)
- `research/cross-project-synthesis-2026-05-11/05-frontier-tooling.md` — Claude Code / Codex / Gemini / OpenCode / MCP-ecosystem state 2026-Q2

Read those for primary detail. This memo is the index.

<!-- knowledge-index
generated: 2026-05-11T06:44:00Z
hash: 4fd7c64c7cf0

title: Cross-Project Architecture Overview — phenome × genomics × intel × agent-infra
status: active
tags: architecture, cross-project, attestation, mcp, history, orientation
cross_refs: analysis/entities/{TICKER}.md, analysis/themes/*.md, research/cross-project-synthesis-2026-05-11/01-phenome-patterns.md, research/cross-project-synthesis-2026-05-11/02-genomics-patterns.md, research/cross-project-synthesis-2026-05-11/03-intel-patterns.md, research/cross-project-synthesis-2026-05-11/04-session-friction.md, research/cross-project-synthesis-2026-05-11/05-frontier-tooling.md, research/cross-project-synthesis-2026-05-11/06-synthesis-and-proposals.md
table_claims: 6

end-knowledge-index -->
