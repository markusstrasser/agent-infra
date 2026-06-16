---
date: 2026-06-16
status: accepted
concept: agent-question-convergence
supersedes: []
related:
  - decisions/2026-06-16-governance-clash-detection.md
  - decisions/2026-06-16-curated-governance (plan .claude/plans/992ed156-…)
provenance: user-directed (/decide, 2026-06-16) — "a back-queue for an agent to ask me
  questions about updating goals/tools/hooks"
---

# Agent→human question convergence — a VIEW, not a STORE

## Decision

The single async surface where agents ask the human about updating goals/tools/hooks is
a **focused VIEW that aggregates the question-class items from the stores that already
exist** — NOT a new queue/store. Feeders keep writing to their own stores; the view
filters + presents; the human reviews async. Concretely: extend the existing `act_drain`
aggregator + SessionStart surfacing to (a) include the promoted clash-hook output and
(b) render a focused **"Questions for you"** section, instead of minting a 5th store.

## Axis + the assumption the inventory falsified

The first framing — "build a unified back-queue" — assumed **no queue exists**. The
read-before-plan inventory **falsified that**: `act_drain.py` already aggregates
`steward-proposals/` (tool/hook proposals) + the disposition queue + RSI-pending into
`~/.claude/act-drain-digest.md`, surfaced at SessionStart by `act-drain-surface.sh`
(one of 4 surfacing hooks). The stores and the aggregation+surfacing **already exist**.

So the real axis is **STORE vs VIEW**. What is actually missing is not a place to put
questions — it is (1) the **clash-hook feeder** (the message-monitor, just built, ADR
2026-06-16-governance-clash-detection) and (2) a **focused review framing** (the
question-class items are currently mixed into loop-funnel metrics).

## Divergent options + why rejected (so they're not re-proposed)

| # | Mechanism | Verdict |
|---|---|---|
| 1 | **New unified store** (`agent-questions/`), migrate steward+decisions-pending in | **Reject** — 5th store + migration; violates native-first and the speculative-extraction veto until fragmentation is *proven* painful. |
| 2 | Aggregating view over existing stores (standalone) | Viable, but redundant with the act-drain aggregator that already does this. |
| 3 | **Extend act-drain** + clash-feed + a "Questions for you" section | **Selected** — reuses the live aggregator + surfacing; adds no store; reversible. |
| 4 | Status-quo + measure | Honest, but the user explicitly asked to decide; the clash-feeder is a real gap regardless. |
| 5 | No-queue, just-in-time contextual surfacing | **Reject** — does not give the async, batch, "ask me when I want" review the user asked for. |
| 6 | `/inbox` paging review-UI over existing stores | Deferred — a nicer review *ergonomics* layer; build only if the digest section proves too dense. |
| 7 | Scheduled-push digest | Already exists (act-drain launchd) — subsumed by (3). |

## Invariants this decision must preserve

1. **No new store.** Feeders (steward, decisions-pending, clash-hook, disposition) write
   to their existing stores; the view only reads/filters. (A view is reversible; a store
   + migration is not — that is why the axis matters.)
2. **The clash-hook output is the new feeder** — once promoted out of shadow, its flagged
   clashes become "Questions for you" rows (the message-monitor → back-queue loop).
3. **Focused, not mixed.** The question-class items (pending decisions, tool/hook
   proposals, promoted clash-flags) render as ONE section, separate from loop-funnel
   counts — that focus is the actual deliverable, not a new container.
4. **Resolution feeds governance evolution** (append-only): an answered question that is
   an override supersedes the stale principle (gov-shrink), per the clash-detection ADR.

## Stop condition

This decision is closed when critique stops overturning the VIEW-not-STORE spine and only
resolves HOWs (which fields the section shows, where the `/questions` entry point lives).
Those HOWs are the build tasks; they do not reopen the spine.

## Critique outcome (Phase 4 — `just critique`, dogfood of the de-biased engine)

One cross-model round (Gemini×2 + GPT×2 + Composer scout). **11 confirmed, 0 corrected,
18 hallucinated, 34 inconclusive — and ZERO architecture reversals.** Every confirmed
finding is a robustness HOW about the *existing* `act_drain` aggregator the view extends,
not a case for a store. Per the arc's success criterion (reversals, not count), the
VIEW-not-STORE spine **held**. Decision closed after one round (escalating to find more
HOWs would over-specify).

**Verify-before-fold catch:** the "synchronous SessionStart aggregation blocks startup"
cluster (#14/#44/#62) is misframed — `act-drain-surface.sh` does `cat
~/.claude/act-drain-digest.md`, a precomputed READ; aggregation runs offline via launchd.
HELD against (rejected): the code shows a `cat`, no new fact. Latency applies to the
offline job, not startup.

**Folded as build requirements (the verified HOWs):**
1. Parser-robust aggregation — a malformed feeder item is skipped + noted, never crashes
   the whole digest (#13/#16/#34).
2. Fail-loud, not silent — aggregator errors surface a `[DEGRADED]` marker, not silence
   (#18; epistemic P8).
3. Atomic digest write (temp + rename) (#53).
4. A formal **question-envelope schema** for feeder items (id, source, category
   goal/tool/hook, prompt, created) so the "Questions for you" section renders uniformly
   across feeders (#15) — this is the one finding that sharpens the view's contract.
5. De-dup repeated questions across runs (#20).

These are the build tasks; the spine is unchanged. Plan:
`.claude/plans/992ed156-agent-question-convergence.md`.
