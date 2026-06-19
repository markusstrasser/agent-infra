---
date: 2026-06-19
status: accepted            # operator "go" 2026-06-19; adopted agent-infra-first
adopted_as: .claude/rules/canonical-answer-format.md
propagation: deferred       # global (all projects/vendors) propagation still open — operator chose agent-infra-first
type: decision
boundary: shared            # response format = global interaction style, 3+ projects → operator gate
reversibility: high         # prose spec + optional advisory hook; git
concept: canonical-answer-format
covers: [thoughtdump-C6, thoughtdump-C7]
relates:
  - feedback-shorter-reviewable-answers.md   # existing memo this sharpens into a spec
  - 2026-06-16-agent-question-convergence
---

# Canonical answer format — decisions up front, reasoning on demand

## The ask (operator voice-dump, 2026-06-19, #6/#7)
"Can we make the responses shorter so I review less information? … Ideas to
structure the response in a canonical format so I can quickly review the main
decision points + their reasoning, and have the reasoning I don't actually care
about NOT be part of the message."

## Measured baseline (agentlogs, claude, 7d)
- Per-run output tokens: median **1,160**, p90 **~14,900**, max 8.6M (headless/subagent runs skew the tail).
- Per-turn reply length (the unit he reviews) is **not cleanly materialized** — `events.role='assistant'`
  is streaming fragments (median 4 chars). Clean metric = concat assistant text between two user turns.
  → **follow-up:** a `v_assistant_turn` view that sessionizes per-turn replies; THEN length is trackable.
- Verdict: verbosity IS measurable; we just lack the per-turn rollup. Cheap to add.

## The canonical skeleton (every substantive reply)
```
<VERDICT / ACTION>          ← 1 line. The decision, or the done-state. Always first.
<DECISION POINTS>           ← table when ≥2 things he might veto: what | my call | 1-line why
<reasoning>                 ← ONLY the why that's load-bearing for a call he'd actually challenge
<OPEN / RISK>               ← only if a real fork, irreversible step, or unnamed assumption remains
```
- Tables/ASCII over prose (37% token win, measured; matches `feedback-shorter-reviewable-answers`).
- Evidence on demand: link the file/path, don't inline the proof unless it's the crux.

## The omit-list (what "reasoning he doesn't care about" means — DROP these)
1. Process narration ("First I'll read X, then Y…") — just do it; report the result.
2. Options-not-taken — unless the rejected fork is itself the decision he's making.
3. Restated context / recap of what he just said.
4. Self-justification & hedging ("I want to make sure…", "to be thorough…").
5. Re-derivation of facts already established in-thread.

## Enforcement posture (ties to his B4 question: hooks vs instructions)
- **Instruction-level now** — format is a semantic predicate; mostly unhookable.
- **One ADVISORY measurement hook (measure-before-enforce, P3):** a Stop hook that
  computes per-turn reply length + flags "no decision-first line / >Nk chars" — REPORT only,
  no block. Promote to anything stronger only on measured adherence data.
- Explicitly NOT a hard block (format false-positives would be high-friction).

## What I need from you (Phase-2 gate)
1. Approve the skeleton + omit-list as the canonical format? (edit freely)
2. Build the `v_assistant_turn` rollup + advisory length hook? (cheap, reversible) — or spec-only for now?
3. Scope: global (all projects, all vendors) or agent-infra-first then propagate?

Reversible either way (git). Default if you say "go": adopt skeleton, build the rollup + advisory hook, agent-infra-first.
