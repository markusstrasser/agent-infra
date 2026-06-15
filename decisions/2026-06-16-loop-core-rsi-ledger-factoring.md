---
concept: cross-project RSI loop factoring (loop-core as composable roles)
decision_date: 2026-06-16
status: proposed
relates_to:
  - research/2026-06-15-critique-slow-and-unreliable.md
  - research/2026-06-14-leverage-hunt-rsi-system.md
  - research/2026-06-12-agents-rsi-gap-sweep.md
  - decisions/2026-06-07-state-externalization-lens.md
affects: [hutter, anim-workbench, substrate/corpus-core, substrate/ledger-core, intel, genomics, agent-infra]
---

# loop-core — composable RSI loop roles over a shared append-only ledger

> **Breaking refactor / full migration. No compat shims, wrappers, or legacy paths.**
> Maintained by AI agents; optimize for the deepest, most inspectable representation,
> NOT for SWE cost. Phase-2 ADR (deep revision — supersedes the coarse field-list draft).
> Sibling decision **A** (dispatch surface) is settled separately: `just <verb>` recipes for
> **templated** work, subagents for **artisanal** work; execution coordinates with the
> concurrent surface-governance session.

## Context

Every advanced project hand-rolls the same propose→verify→accept→ledger loop: hutter
(Grinder/Dreamer, compression), anim-workbench (grow/shrink, render-gates), agent-infra
`/improve` + prediction-ledger. They have already **drifted on the load-bearing component** —
the accept-gate (hutter greedy vs anim-workbench auditor) — which is the proof that an
un-factored invariant silently diverges. Factor the common substrate **deeply, as composable
roles**, not a coarse field-list.

## The real axis

Which parts of the loop are common **roles** (factor as swappable, inspectable interfaces) vs
domain mechanics (plug). Established by reading the two most-advanced instances (Explore digs,
2026-06-16) and the `corpus_core` ledger writer — not by theorizing.

## Decision — loop-core is a composition of inspectable ROLES over a shared ledger

```
        ┌────────── ledger (append-only · DuckDB · shared mechanics w/ corpus_core) ──────────┐
        │  every role appends its output → the run is fully replayable / debuggable           │
        ↓                                                                                      │
 Proposer ──→ Runner ──→ Verifier ──→ Auditor ──→ Accept-gate ──→ (append verdict) ────────────┘
 (Dreamer)   (Grinder)               (Heretic)
```

| Role | What it is | Generic (loop-core ships this) | Plug (per-project) |
|---|---|---|---|
| **Proposer** (Dreamer) | ledger-signal → candidates | queue-drain · self-gen via **clade-yield** (rank parents by descendant-acceptance, not own-score) · beam-K fan-out | candidate representation; domain hypothesis generation |
| **Runner** (Grinder) | candidate → raw measurement | dispatch/execute harness; resource caps | build/run mechanics |
| **Verifier** | measurement → score + hard pass/fail gate | interface contract: **deterministic only, never LLM-judged** | the scorer (compression bytes / render-gate) |
| **Auditor** (Heretic) | adversarial pre-accept check | oracle-ratio · real-reject-rate · idea-fuel-exhaustion | domain oracle-bias checks |
| **Accept-gate** | (verifier, auditor) → ACCEPT / REJECT | policy interface | greedy \| conjunctive \| PACE e-process |
| **Ledger** | append-only durable memory + inspection surface | `ledger-core` DuckDB mechanics (below) | domain columns |

**Dreamer = the Proposer role; Heretic = the Auditor role** — separate from the Accept-gate it
feeds. The coarse draft that buried both inside "accept-gate policy" is explicitly rejected below.

**The ledger is the inspection surface.** Every role appends its output (proposal · measurement ·
verifier-score · auditor-verdict · accept-decision), so any loop run is fully replayable and
debuggable from the ledger alone. Each role is an independently testable interface; loop-core
ships reference implementations of the generic strategies (clade-yield proposer, heretic auditor,
e-process gate) that projects compose and override. This is the classic propose-evaluate-select
loop (genetic / active-learning) decomposed into its natural roles, with durable memory.

## Ledger — shared `ledger-core` mechanics on DuckDB (DECIDED — was deferred)

`corpus_core` and `loop-core` are **siblings** that both build on ONE extracted **`ledger-core`**
mechanics contract on **DuckDB**: append-only · content-addressed IDs · supersession-not-mutation
· per-file JSONL source-of-truth + rebuildable index projection · monotonic schema-version bump
guard · **derived scalars as views, never columns** (overwriting destroys the replayable moat).
`corpus_core`'s `graph_schema.sql` is the **reference embodiment** — extract its mechanics into
`ledger-core`; `loop-core` consumes it with its own domain schema:
`(ts, variant, git_sha, parent_id, predicted, actual, verifier_score, auditor_verdict,
accept_verdict, tags, metrics)`. The belief-graph domain (claim_relations / support_balance)
stays in corpus_core; the experiment-trial domain stays in loop-core. Shared mechanics, distinct
schemas.

## Invariants to preserve

1. **Verifier is ground-truth, never LLM-judged** (a bad eval is worse than none — Goodhart).
2. **The Auditor role is mandatory** even when the Accept-gate policy is greedy (PACE: greedy
   alone = self-p-hacking; the auditor is the anti-self-dealing component).
3. **Falsifiable contract is non-tautological** (anim's `grow-ledger` already enforces this).
4. **Append-only / supersession-not-mutation** — overwriting destroys the replayable moat.
5. **Every role traces to the ledger** — inspectability is an invariant, not a feature.

## Rejected alternatives

- **Coarse field-list factoring** (the prior draft: propose/auditor buried in "accept-gate
  policy") — rejected: it hides the two roles that most need to be first-class + swappable
  (Dreamer, Heretic). Shallower than the structure that actually exists in the code.
- **Jam experiment trials into corpus_core's `annotations` table** — rejected: different domain;
  pollutes the belief graph (field-compare evidence: `predicted/actual/verdict` vs
  `status/relation_class`).
- **One mega "RSI framework"** owning everything as a monolith — rejected: roles are independently
  swappable interfaces, not a framework that dictates control flow (over-centralization, principle 9).
- **Status quo (hand-rolled per project)** — rejected: it is the consumption-over-autonomy disease;
  the loops already drifted on the accept-gate.
- **Any backward-compat shim / wrapper / dual-path** — rejected by directive: breaking refactor,
  full migration.

## Concrete first win (no loop-core needed)

**hutter adopts anim-workbench's Heretic auditor** (the Auditor role) onto its greedy `s < base`
gate — hutter's gate is the weakest of the three (observational-only anti-p-hack), a live PACE
self-p-hacking hole. Same-day, in a hutter worktree, independent of the full factoring.

## Open (Phase 3)

- Home: `substrate/packages/loop-core` + `substrate/packages/ledger-core`, beside `corpus-core`.
- Migration order: (1) hutter Heretic-auditor win → (2) extract `ledger-core` from corpus_core →
  (3) loop-core roles → (4) migrate hutter + anim-workbench onto them, delete the hand-rolled loops.
- Read corpus_core's append/rebuild **code** (not just schema) before extracting `ledger-core`.
