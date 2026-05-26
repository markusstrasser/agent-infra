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
