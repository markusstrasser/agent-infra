# Canonical Answer Format

<!-- Gov-ID: rule:canonical-answer-format
goal: substantive replies lead with the decision; reasoning the operator won't challenge is omitted, not narrated
verifier: evals/graders/governance/answer_format.py  # null until built; advisory length hook measures first
blast_radius: local   # agent-infra-first; global propagation deferred (operator gate)
-->

Every substantive reply follows this skeleton. Trivial/conversational turns are exempt.

```
<VERDICT / ACTION>     ← 1 line, FIRST. The decision, or the done-state.
<DECISION POINTS>      ← table when ≥2 things the operator might veto: what | call | 1-line why
<reasoning>            ← ONLY the why that's load-bearing for a call he'd actually challenge
<OPEN / RISK>          ← only if a real fork, irreversible step, or unnamed assumption remains
```

Tables/ASCII over prose. Link evidence by `path:line`; don't inline the proof unless it's the crux.

**Omit (this is "the reasoning he doesn't care about"):**
1. Process narration ("First I'll read X, then Y…") — just do it; report the result.
2. Options-not-taken — unless the rejected fork IS the decision he's making.
3. Restated context / recap of what he just said.
4. Self-justification & hedging ("to be thorough…", "I want to make sure…").
5. Re-derivation of facts already established in-thread.

Enforcement: instruction + an advisory length/structure Stop hook (measure-before-enforce, P3) —
never a hard block (format false-positives are high-friction). Source: `decisions/2026-06-19-canonical-answer-format.md`.
