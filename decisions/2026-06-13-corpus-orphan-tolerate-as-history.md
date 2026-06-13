---
id: 2026-06-13-corpus-orphan-tolerate-as-history
concept: cross-attestation-substrate
repo: agent-infra
decision_date: 2026-06-13
recorded_date: 2026-06-13
provenance: contemporaneous
status: accepted
initial_leaning: supersede-on-delete — mirror genomics' gateway and enqueue a supersede when phenome cascade-deletes a verdict (the decisions-pending recommendation)
relations:
  - type: supersedes
    target: 2026-06-12-phenome-corpus-orphan-supersede
  - type: cross_repo_of
    target: phenome
---

# 2026-06-13: Corpus orphan annotations — tolerate as append-only history via compensation events, never physical delete

## Context
`audit_corpus_sync` reports 6 phenome **orphan annotations** (corpus annotations whose
backing verdict no longer exists), stable across runs. The job exits 1 on any drift, so
this surfaces as a persistent launchd "red". The decisions-pending item framed it as
"phenome cascade-deletes leave orphans → add supersede-on-delete to phenome's gateway,
mirroring genomics." Markus decided the question and **rejected that framing**.

## The framing error (Markus, the principal on the corpus contract)
The "cascade-delete leaves orphans" framing presupposes physical deletion is happening —
and **that** is the actual bug, not the orphan it leaves behind:

- A corpus annotation records a **true historical fact** — "claim X cited span Y at time
  T". That stays true after X is retracted. Hard-deleting the annotation *falsifies* the
  record; it does not correct it.
- A retracted claim should **also** not vanish: rank → deprecated/retracted via an
  append-only event (with a `replacement_assertion_id` if superseded), a tombstone, not a
  hole. If the claim tombstones, there is no cascade to *delete* — only a cascade to *mark*.

## Decision
**Tolerate as history. Retract via a compensation (detach) event, never a physical delete.**
The correct operation is not `DELETE annotation` — it is **emit a detach/retract event** that
marks the annotation superseded and points at the claim-retraction event that caused it. The
annotation row stays; its lifecycle (attached T1 → detached T2, because claim X retracted)
becomes queryable provenance.

Consequence for the audit: `audit_corpus_sync` must treat a post-retraction orphan **that
carries a detach/tombstone event** as **expected (a tombstone join), not drift** — so the red
clears for legitimately-retracted claims. An orphan **without** such an event is still real
drift (a bug) and must keep firing. The fix is therefore NOT "tolerate all orphans" — it is
"join on the compensation event."

## The one real distinction (changes mechanism, not conclusion)
- **Rederivable agent-derived projection** (e.g. an auto-attached, content-addressed citation
  a re-ingest reproduces byte-for-byte): the *content* carries "no protection" per the
  data-stream ownership rule — it may be dropped and rebuilt. But the **attach/detach event is
  still append-only**. The projection is rebuildable; the audit trail of having attached then
  detached it is not.
- **Human-judgment or staged annotation** (the auto-attached-citation case the constitution
  flags — "a 4% error floor on 1,500 auto-attachments is worse than a staging CLI clicked
  once"): belief data, unambiguously append-only.

## Counterevidence sought
The leaning was supersede-on-delete (mirror genomics). What falsifies it: the project's own
append-only invariant — "the trail of belief changes IS calibration data; overwrites destroy
it" (design stance + Medical Constitution P7) and the event algebra **closed under
compensation** (phenome ADR 0010 I4: every state-attach has a detach counterpart). Under those
commitments, physically removing the annotation on delete is a correctness violation, not a
cleanup. The leaning does not survive its own constitution. Searched genomics' reference
gateway: it enqueues *supersede intent inside the delete txn* — the right shape only if
"supersede" means a detach EVENT, not a row removal; the framing, not the mechanism, was the
error.

## Implementation (cross-repo; deferred until the rate-limit storm clears + phenome worktrees idle)
Ordered, coupled. **Step 0 first — `corpus_core`'s event surface was not confirmed this
session; do not assume a detach/supersede event type exists.**
1. **Verify the corpus event API.** Confirm `corpus_core` supports a detach/supersede/retract
   event (valid_to / superseded-by chain). If absent, that addition is the first unit of work.
   Probe before writing any consumer.
2. **phenome mutation gateway:** on claim retract, tombstone the claim (append-only,
   `replacement_assertion_id` if superseded) and emit a detach compensation event for its
   corpus annotation **inside the same transaction** — never a physical delete of claim or
   annotation. (Mirrors genomics `MutationGateway._enqueue_corpus_attestation`, but the enqueued
   intent is *detach*, not *delete*.)
3. **agent-infra `audit_corpus_sync`:** join orphans against detach/tombstone events. Orphan +
   detach event = expected (tombstone join), drop from `drift_total`. Orphan without = drift,
   keep firing. This is what stops the false red without blinding the audit.

Low urgency: 6 orphans, advisory-only, non-blocking, no data loss. Until implemented the red
persists — but it is now a **known-expected** red with a decided resolution, not an open fork.

## Revisit if
- A corpus annotation turns out to encode mutable state rather than a point-in-time fact (would
  reopen whether "attach at T" is really immutable).
- The orphan count grows fast enough that advisory-only is no longer acceptable before the
  gateway fix lands.

## Supersedes
`decisions-pending/2026-06-12-phenome-corpus-orphan-supersede.md` (resolved into this record).
