---
id: 2026-05-26-cross-attestation-substrate-v2
concept: cross-project-attestation
repo: agent-infra
decision_date: 2026-05-26
recorded_date: 2026-05-26
provenance: contemporaneous
status: accepted
initial_leaning: Land record_verdict for real in phenome and intel (Option a) — preserve the cross-repo ritual framing, finish what substrate v1 started.
relations:
  - type: supersedes
    target: 2026-05-11-cross-attestation-substrate
---

# 2026-05-26: Cross-Attestation Substrate v2 — Gateway Invariant + Per-Repo Natural Emission

## Context

Substrate v1 (`2026-05-11-cross-attestation-substrate.md`) defined a 2-call agent ritual: `<repo>_mcp.record_verdict(...)` followed by `corpus_mcp.corpus_attest(...)`. A PostToolUse hook (`posttool-corpus-attest-remind.sh`) reminded the agent of step 2 whenever step 1 fired. A daily audit (`audit_corpus_sync.py`) reported drift.

Empirical forensics over the 12-day post-launch window (research/substrate-usage-forensics-2026-05-26.md):

- `mcp__*__record_verdict` invocations: **0** (in 9 months of indexed agentlogs).
- `mcp__corpus__corpus_attest` invocations: **0**.
- All three `record_verdict` MCP tools were stubs returning `not_implemented_yet` / `unsupported`. Step 1 of the ritual was a no-op everywhere.
- All 360 genomics annotations on 2026-05-11 came from a one-shot migration script importing `corpus_core.annotate` directly — not via MCP.
- Real verdict-write path: Bash → `cli.py drain` → `MutationGateway.write_verdict()` (260 such invocations during the window, all bypassing MCP entirely).
- Hook fired 3 times total, all in one test session on 2026-05-15.
- 166-row standing drift in corpus annotations table relative to `claim_verdicts` (verdicts written via the gateway path that never reached corpus).

**The ritual never ran in production.** Demand existed (459 verdicts written during the window); the contract was at the wrong layer.

## Alternatives considered

### Architecture (where enforcement lives)

1. **Keep ritual; land `record_verdict` for real in all three repos.** Preserves the cross-repo agent-discipline framing. Each repo's gateway gains an MCP wrapper that calls the gateway then returns; the hook then reminds for step 2.
   - Pros: matches the v1 spec; least conceptual change.
   - Cons: per CLAUDE.md Principle 1 (architecture > instructions), agent discipline is 0% reliable. Instructions shift intercept, not slope (SlopCodeBench, arXiv:2603.24755). Reinforces a known failure mode.

2. **Gateway invariant via transactional outbox.** Each repo's mutation gateway INSERTs annotation intent into a `pending_corpus_attestations` table inside the verdict's BEGIN/COMMIT span. Post-commit, the gateway flushes the outbox to corpus filesystem. Failures retry; ≥3 retries → abandoned. Audit catches crash-gap rows.
   - Pros: zero agent discipline required. Atomic intent + verdict. Orphan annotations impossible. Drain failure decoupled from verdict write. Matches Principle 1.
   - Cons: each repo with a gateway must implement the outbox + drainer. Couples corpus_core to gateways at runtime (corpus is now a hard dep of writes).

3. **Fire-and-forget async drain.** Same as 2 but drain happens in a background thread. Lowest write latency.
   - Pros: lowest latency.
   - Cons: harder to test, harder to observe, hides failure timing. Overkill at single-user scale.

### Cross-repo shape (what other repos do)

a. **All three repos implement verdict-shaped attestation.** Wire `record_verdict` MCPs for real in phenome + intel. Forces verdict-shape on cert-stack and theses-graph abstractions.
   - Pros: uniform shape; one cross-repo concept.
   - Cons: category error. Phenome's primitive is `claim_certificate_events`; intel's is `contradiction_resolutions_log`. Forcing verdict shape distorts both.

b. **Genomics-only producer.** Document that only genomics emits attestations. Phenome/intel never participate.
   - Pros: minimal scope.
   - Cons: loses the cross-repo readable annotations index — the original value prop of corpus_core's global annotations table.

c. **Per-repo natural emission points.** Each repo emits to corpus_core.annotate from its natural mutation primitive: genomics from `MutationGateway.write_verdict` with `scope="verdict"`; phenome from `claim_certificate_events` insertion with `scope="cert_event"`; intel from `contradiction_resolutions_log` insertion with `scope="contradiction"`. Same outbox pattern per repo.
   - Pros: preserves cross-repo annotations table; respects each repo's actual primitive; same architectural pattern (gateway invariant) per repo; no fake common ontology.
   - Cons: each repo's gateway implementation is bespoke; no shared abstraction.

## Counterevidence sought

For Option 2 (gateway invariant) + Option c (per-repo natural emission) — the leading combination:

- **Searched for prior gateway-side-effect patterns that regressed.** Found none. The genomics MutationGateway already has staged-write filesystem patterns inside the gateway (`_PendingFsRename`, two-phase commit); adding a second post-commit side-effect (corpus drain) is the same architectural shape, already proven in this codebase.
- **Searched for cases where agent-orchestrated 2-call rituals worked.** None in this codebase's history. Every cross-repo "agent must call X then Y" rule recorded in 9 months of agentlogs has 0 organic invocations.
- **Searched for incidents where corpus FS outage caused verdict-write outage.** None. The fail-soft outbox prevents this by design.
- **Searched for cases where the per-repo verdict-shape forcing would surface a real abstraction.** None. Phenome and intel's primitives are genuinely different; pretending otherwise is the rejected pattern from 2026-03-17-shared-knowledge-substrate.md.

**The cross-evidence convergence**: GPT-5.5 and Gemini 3.5 Flash, in the model review for `plans/2026-05-26-substrate-rewiring.md`, independently arrived at the same combination (Option 2 + Option c) without prompting. See `.model-review/2026-05-26-substrate-rewiring-cecf32/disposition.md` findings 1/5/11/12/16.

## Decision

**Selected: Option 2 (gateway invariant) + Option c (per-repo natural emission).**

Each repo's mutation gateway is the sole writer of corpus attestations for its scope:

| Repo | Gateway | Scope | Status |
|---|---|---|---|
| genomics | `MutationGateway.write_verdict` | `verdict` | **Shipped 2026-05-26** (Phase 2 of `plans/2026-05-26-substrate-rewiring.md`) |
| phenome | TBD (cert-stack gateway) | `cert_event` (or similar) | **Out of scope for v2.** Needs separate plan when phenome's gateway-emission lands. |
| intel | TBD (theses-graph gateway) | `contradiction_resolution` (or similar) | **Out of scope for v2.** Needs separate plan when intel's gateway-emission lands. |

**Concrete shipped (2026-05-26):**

- Genomics: `MutationGateway.write_verdict` enqueues annotation intent into `pending_corpus_attestations` inside the BEGIN/COMMIT span. After `__exit__` releases the writer lock, gateway drains the outbox via `corpus_core.annotate`. Narrow exception types; ≥3 retries → `status='abandoned'`.
- `audit_corpus_sync.py` drains the outbox across all known repos on each run, surfaces abandoned-row counts.
- All five `record_verdict` MCP stubs deleted (genomics, phenome, intel; evals and agent-infra never had implementations).
- `posttool-corpus-attest-remind.sh` hook deleted.
- `~/.claude/settings.json` matcher block removed.
- Legacy migration scripts (`migrate_genomics_phase5.py`, `migrate_phenome_source_records.py`) deleted — substrate-v2 backfill is the SQL outbox migration.
- 166-row standing drift closed via `migrations/2026-05-26-backfill-pending-corpus-attestations.sql`.

**Deferred (separate plans, not blocking v2):**

- Phenome cert-stack gateway emission.
- Intel theses-graph gateway emission.
- Lint enforcement (`lint_no_direct_corpus_writes.py`) forbidding `corpus_core.annotate` imports outside repo mutation gateways. To land in Phase 7-companion work after v2 stabilizes for ~1 session.

## Evidence

- Forensics: `research/substrate-usage-forensics-2026-05-26.md` (0 invocations / 9 months; 166-row drift; gateway as actual write path).
- Cross-model review: `.model-review/2026-05-26-substrate-rewiring-cecf32/` (Gemini 3.5 Flash + GPT-5.5 converged on outbox + per-repo emission independently).
- Plan: `plans/2026-05-26-substrate-rewiring.md` (executed Phases 1-5).
- Atomicity tests: `genomics/tests/test_mutation_gateway_atomicity.py` (21 scenarios green; 5 outbox-specific cases verify rollback semantics).
- Drift verification: `audit_corpus_sync.py` reports `missing_ann=0` for genomics post-backfill (was 166).

## Revisit if

- Cross-repo source overlap > 0 starts mattering for real (currently 0 — `cross_attestation_lookup` returns no shared source_ids across genomics/phenome/intel).
- Phenome or intel adds a verdict-shaped primitive (would reopen the verdict-shape question).
- Agent organic usage of `corpus_lookup` MCP rises significantly (the cross-repo readable annotations table becomes load-bearing in agent workflows).
- The outbox abandoned-row count climbs (would indicate persistent corpus FS issues, not architecture issues).

## Supersedes

`decisions/2026-05-11-cross-attestation-substrate.md` (substrate v1: agent-orchestrated 2-call ritual). Empirically unimplemented in all 5 target MCPs; replaced by gateway invariant.

## Update — 2026-05-27 — deferred items closed; outbox extracted to corpus_core

Executed `plans/2026-05-27-substrate-v2-deferred-items.md`:

| Phase | Status | Anchor |
|---|---|---|
| 1 — `pick_canonical_source` semantic priority (close-review #20) | Shipped | genomics@b50ffc2d |
| 2 — Outbox lifecycle (supersedes_annotation_id, annotation_status) (close-review #18) | Shipped — 493 superseded verdicts in live data validated the need | genomics@1f36e57e + agent-infra@b42befd |
| 2.5 — Extract `corpus_core.outbox` shared primitive | Shipped — net -124 lines | agent-infra@3135d0e + genomics@e0b7fc54 |
| 3 — Phenome cert-stack gateway emission (`scope='cert_event'`) | Shipped — single chokepoint at `claim_closure.py:_persist_certificate` | phenome@2930dc9 |
| 4 — Intel theses-graph emission | **STOPPED at preflight** — intel uses `filings_and_datasets.filing_or_dataset_id` UUIDs, not corpus's `doi_*`/`pmid_*`/`db_*` slug shape; `entry_readiness_certificates` has zero INSERT sites in code; `contradiction_resolutions_log` doesn't link to source. Source-id alignment is a separate prerequisite plan, not part of substrate-v2-deferred. Plan explicitly anticipated this STOP. | n/a |
| 5 — Audit/lint propagation + decision update | Shipped (this update) | (this commit) |

**Substrate-v2 reality, post-deferred-items:**

- **One sole writer of corpus annotations across all repos: `corpus_core.outbox.drain`.** The genomics `MutationGateway.__exit__` and `audit_corpus_sync.py` both delegate to it (path-based API; lock-friendly 3-phase pattern: RO fetch → unlocked FS emit → short RW DELETE/UPDATE). Phenome's cert-stack does not invoke drain locally — relies on `audit_corpus_sync` as the sole drain path (no writer-lock pattern in phenome's call surface).
- **Outbox table shape standardized via `corpus_core.outbox.outbox_schema(natural_key)`.** Per-repo natural keys: genomics=`(verdict_id,)`, phenome=`(cert_event_id,)`. Lifecycle columns inline for greenfield, idempotent ALTER (`ensure_lifecycle_columns`) for legacy.
- **Per-repo lint deployed:** `genomics/scripts/lint_no_direct_corpus_writes.py`, `phenome/scripts/lint_no_direct_corpus_writes.py` (AST-based, bans direct `corpus_core.annotate` imports outside the gateway).
- **Per-repo emission table:**

| Repo | Where enqueue happens | Scope | Drain path |
|---|---|---|---|
| genomics | `MutationGateway._enqueue_corpus_attestation` (inside write_verdict txn) | `verdict` | Post-lock-release in `__exit__` + audit (both via `corpus_core.outbox.drain`) |
| phenome | `_enqueue_cert_attestations` (inside `_persist_certificate`, sequential after event INSERT) | `cert_event` | audit-only (no in-process drain — eventual consistency via retry idempotency) |
| intel | not yet emitting (Phase 4 STOPPED — prerequisite source-id alignment) | n/a | n/a |

**Atomicity contract differs per repo by design:**

- **genomics**: writer.lock + BEGIN/COMMIT → event + outbox in one transaction (strong atomicity).
- **phenome**: shared-connection-across-threads use case (regression test races 4 workers); BEGIN/COMMIT would segfault DuckDB. Event INSERT and outbox INSERT are individually idempotent (uniq_cce_issued + composite PK); crash between them leaves drift that the audit detects + operator re-runs idempotently.

The audit drain (`audit_corpus_sync.py --drain-only`) handles the cross-process safety net for both repos.

**Audit/lint generalization closes close-review #14 and #21:** `audit_corpus_sync.VERDICTS_SOURCES` per-repo entries now carry `scope` and `natural_key_cols` keys instead of hardcoded `'verdict'` strings. Adding a new repo (e.g. intel once source-id alignment lands) is one dict append.

### Why intel was deferred

Per plan §4 preflight: intel's `filings_and_datasets` table uses UUIDs as primary identity. corpus uses slug-namespaced source IDs (`doi_*`, `pmid_*`, `db_*`, `guideline_*`, etc.) per the corpus_core source-id namespace. There's no current mapping from intel's UUIDs to corpus slugs — `filings_and_datasets.doi` is optional metadata, not a primary identity. Wiring emission without first aligning source identity would either:

- Write attestations using UUIDs as source IDs (breaks the cross-repo lookup contract — corpus's `cross_attestation_lookup` would never match across repos)
- Synthesize fake corpus slugs (loses the deterministic stable_tuple property)

Both are worse than not emitting. The right next step is a separate plan: "Intel source-identity alignment with corpus." That plan unblocks Phase 4. Until then, intel stays a placeholder in `VERDICTS_SOURCES` with the audit reporting `verdicts=0`.

## Update — 2026-05-31 — corpus_attest MCP tool removed; v1 doc surfaces scrubbed

The v2 cleanup (lines 90-93) deleted the `record_verdict` MCP stubs, the reminder
hook, and the settings matcher — but **missed the `corpus_mcp.corpus_attest` tool
itself**, the one surviving v1 surface. It was an MCP-exposed direct writer of
`annotations.jsonl`: a dual-write backdoor around the gateway-outbox invariant (an
agent could attest outside any gateway transaction). 0 invocations in 9 months.

Removed (agent-infra@95acb61): the tool + corpus_mcp's now-unused `corpus_core.annotate`
import — which makes corpus_mcp compliant with v2's own "only gateways import the
sole writer" rule (corpus_mcp is now read-only for annotations). The sanctioned
manual path for a standalone observation is the `corpus annotate` CLI (routes
through the sole writer); the drain path is `audit_corpus_sync --drain-only`.
Scrubbed the v1-ritual docs that still taught the dead two-call flow:
`skills/corpus` + `skills/entity-management` (skills@94b72d5) and phenome
`substrate_tools.py` docstring (phenome@94f6cfd).

**Best-practices re-confirmation** (web-grounded; `.scratch/attestation-best-practices-research.md`):
the shipped outbox design is best-of-breed for its scale — atomic enqueue,
content-hash+natural-key idempotency, `abandoned`+daily-audit as the dead-letter
strategy, polling (not CDC) — all canonical; `schema_version` already present.
Single-writer is the universal invariant and the manual path correctly routes
through the sole writer (a CLI), not a parallel MCP writer. Two 2026 systems
(ESAA arXiv:2602.23193, Athenaeum) independently re-derived the same "one writer,
safety from structure not trust" invariant. No architecture change warranted —
deleting the parallel writer moves the system toward canonical correctness.

**Still open (flagged, not blocking):** phenome still registers the v1 verdict-shape
READ interface (`substrate_tools.py`: `claims_for_source`/`verdicts_for_claim`) —
a retirement candidate (v2 cross-repo reads come from `corpus_lookup`). Stale
v1-ritual COMMENTS remain in genomics `genomics_mcp.py`/`new_claim.py` and intel
`theses_mcp.py` — left untouched this session (active agents in both repos).
