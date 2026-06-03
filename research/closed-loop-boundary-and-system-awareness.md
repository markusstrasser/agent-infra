---
title: "The Closed-Loop Boundary: Generation, Verification, Goals — and Where Our Systems Must Be Aware"
date: 2026-06-03
tags: [autonomy, verification, recursive-self-improvement, agent-architecture, system-design]
status: active
---

# The Closed-Loop Boundary

*Conceptual frame behind `decisions/2026-06-03-verifier-bound-autonomy.md`. Evidence in
`research/rsi-verification-bound.md` and `research/agentic-hygiene-plateau-reward-hacking.md`.*

## TL;DR

There is **one boundary** behind the daily friction of running these agents: a closed loop
of LLM(s) can only **re-weight within its learned distribution; only external information
moves the boundary.** This is shown directly for recursive self-improvement (RLVR
re-weights toward what the verifier certifies, it does not expand capability — Yue et al.,
arXiv:2504.13837) and holds by the same structure for *generation*, *verification*, and
*goal-setting*. The precise constraint is not "access to bits" — bits are free — but access
to **information correlated with the specific, unrecorded ground truth you need.** That kind
of information comes from only two places: **reality-contact** (running the thing, the
experiment, shipping and measuring) and a **decorrelated mind** (currently, the human).

## Part 1 — The one boundary

A model is a learned distribution. Any loop built only of that model (or same-lineage
models) — self-correction, self-brainstorm, self-scoring, a swarm of copies — is a closed
loop: it can resample, recombine, and re-weight what's already in the distribution, but it
cannot add information that isn't. Yue et al. make this concrete for self-improvement: under
RLVR, base models win at large pass@k; the loop **narrows** the reasoning boundary toward
what the verifier can certify. Capability that genuinely expands comes from *outside* —
pretraining data, distillation, an external verifier, reality.

**Precise statement (the loose version is "external information"):** the binding scarcity is
information with **mutual information about the specific unrecorded truth** at hand — is *my*
pipeline correct, what should *I* build next, did the refresh *I* depend on stop. None of
those are in any corpus. The boundary moves only with information that actually covaries with
that answer.

## Part 2 — Three points on the same boundary

Our two divergence/convergence skills sit at two of the three points; the human sits at the
third.

| Point | Skill | What's bounded | The escape | The residual |
|-------|-------|----------------|-----------|--------------|
| **Generation** | `/brainstorm` | Mode collapse / Artificial Hivemind — all frontier models sample the same modal idea-region | Off-distribution **conditioning**: structural perturbation (denial cascades, domain forcing, constraint inversion) + external input | Cross-lab barely helps here ("volume, not diversity") — the shared attractor *is* "the obvious good idea" |
| **Verification** | `/critique` | Correlated evaluators — same-lineage review shares the generator's blind spot | Decorrelated **evaluation**: cross-*lab* review + ground-truth filter | ~60% shared-wrong floor even cross-family; ~50% noise; rubber-stamps low-perplexity text; weakest on easy-looking tasks |
| **Goals** | *(you)* | Can't be verified, only chosen — the regress of "correct against what?" terminates here | Reality's feedback (slow) or an idiosyncratic mind (you) | A shrinking *frontier*, not a fortress (Part 4) |

**`/critique` is the antidote, not the disease.** The doomed thing is *intrinsic*
self-correction (same weights, same context). `/critique model` escapes it by going
cross-lab — and it works empirically: cross-family review hit 90.4% vs 59.1% same-model
(FINCH-ZK), and the genomics audit caught 5/5 bugs Opus missed. But it's a *better verifier,
not an oracle*: correlated floor, noise (the genomics `/critique close` run was
hallucination_rate 0.508 — it found the real critical bug buried in false ones), perplexity
rubber-stamping, and Reasoning Theater on easy tasks. So it produces **candidates, not
verdicts** — the adjudication still needs reality (run the test, read the primary source).
See `research/cross-model-review-failure-modes.md` for the measured failure catalogue.

**`/brainstorm` is the harder case.** Same root (shared distribution), generation side, and
*tighter* — because verification hunts a specific present error (idiosyncratic to the
artifact; different families catch different needles) while brainstorm operates *at* the
shared attractor where all frontier models overlap most. Model-diversity barely moves you;
only perturbation or external input does. The skill already knows this ("volume, not
diversity").

The symmetry: `/brainstorm` injects off-distribution **conditioning**; `/critique` injects
decorrelated **evaluation**. They are the two halves of the same escape.

## Part 3 — Recombinative vs. reality-contact

"Can't an AI just get external information — noise, internet search, other agents?" Yes, and
almost none of it moves the boundary, because it's all the *recombinative* kind:

- **Noise** has zero mutual information with the answer. Temperature widens sampling of the
  *same* distribution. It's useful only paired with a selector that keeps the good samples —
  and the selector is the verifier. Noise without a fitness function is drift.
- **Internet search** retrieves *recorded* knowledge — increasingly the models' own output
  mirrored back (contamination). It reaches the edge of what's written down; it cannot cross
  it. The unrecorded truth you need about *your* artifact isn't there.
- **Other agents**: same-lineage = correlated = a martingale (no expected gain). Cross-lineage
  = `/critique`, with its floor. A swarm from one distribution is still a closed loop at the
  population level — and labs are converging, so the residual decorrelation is shrinking.

The **tell**: these are cheap *precisely because they don't touch reality.* Free information
is free because it's already in the distribution.

The genuine external channel is **action**: a code agent acquires real ground truth by
*running* the code — the interpreter is the external source. That's why autonomy works best
in code: a fast, cheap, faithful verifier. **Action gives ground truth only as fast as
reality returns the verdict** — milliseconds in code, months in science, never cleanly in
art or "what's worth wanting." Same gradient as everything else.

So abundant information doesn't dissolve the bound — it **relocates it onto the selector.**
A firehose of proposals (high temperature, deep search, an agent swarm) + a weak verifier =
*confident slop, faster.* That is the operative risk, not under-supply of ideas.

## Part 4 — Goals as the terminus

Verification needs a standard ("correct against what?"); the standard is the goal; the goal
can't be verified by another verifier without infinite regress. So goals are the last human
context. But three honest caveats:

1. Goal-setting is the *next* automation frontier — preference learning compresses "specify"
   into "correct" (the yes/no on 30 ideas is training signal for predicting the 31st).
2. Goal-inference has brainstorm's bound — it regresses toward the *modal* goal and misses
   your idiosyncratic ones.
3. It bottoms out in verifier-poverty — where reality gives fast, faithful feedback, goals
   self-bootstrap (AlphaZero against the win condition). The human is irreducible *only*
   where reality's feedback is slow, expensive, or absent.

Net: goals are a **frontier, not a fortress** — the set of objectives both idiosyncratic
enough to escape prediction *and* in domains reality hasn't yet adjudicated. It shrinks as
models predict you better, and persists only because new capability generates new wants
faster than the system learns the old ones. That is the constitution's "arms race," and this
is its mechanism.

## Part 5 — Where our systems must be aware

The frame is not abstract; it indicts specific parts of our own infrastructure.

### 5.1 Self-referential verifiers inherit the floor
Every place we use a model to judge model output is a **correlated verifier** and carries
the ~60% shared-blind-spot floor:
- `reflect.py` / the session-learning loop (Claude judging Claude sessions)
- `session-analyst`, and any **prompt-type stop-hook** (Haiku judging the transcript)
- any "is this done / is this good" self-assessment

**Rule:** anchor to reality where possible (git state, test pass/fail, actual metrics,
file-exists) rather than model-judgment; **decorrelate** (cross-lab) where judgment is
irreducible; and **never let a self-score be the gate** — which is exactly why the scored
session-quality gate was vetoed (a self-score is one correlated check). A model grading its
own family's work is a thermometer made of the same fever.

### 5.2 Absence-blindness needs setpoints, not reactive hooks
Our hooks are almost all **reactive** — they fire on an action the agent *takes*. They are
structurally blind to the action the agent *fails* to take (the refresh that didn't run, the
feature that wasn't wired). Catching omission requires a **standing setpoint + differ**: a
declaration of what should be true, and a watcher that diffs reality against it and alerts on
the delta. AbsenceBench (arXiv:2506.11440) shows this is architectural, not a scaling
deficit — attention has no key for a gap. We must supply the key externally.

### 5.3 The method: goal → setpoint → verifier
The unifying answer to "better systems, or better goals?" is **both, via one move.** A
standing goal ("stay fresh," "leave it integrated," "no clinical false-clear") is
unverifiable as stated and invisible to an absence-blind agent. Convert it:

```
implicit goal  →  explicit setpoint (what must be true)  →  differ that touches reality  →  alert routed to a consumer
"stay fresh"   →  "source X updated ≤ N days"            →  check actual data mtime        →  beacon / gate
```

A goal you don't encode as a setpoint is a goal the agent won't hold. A setpoint with no
reality-touching differ is decoration. An alert nobody consumes is absence-blindness one
level up (the report that exists but is never read).

### 5.4 Prefer action over reasoning-about
Design for **reality-contact**: the agent that *runs* the thing beats the agent that reasons
or searches about it. Where the domain has a fast verifier (code), lean all the way into
autonomy. Where it doesn't (research synthesis, taste, strategy), accept that the human or
slow reality is the rate-limiter — and don't paper over it with more recombinative
information, which only manufactures confident slop.

## See also
- `decisions/2026-06-03-verifier-bound-autonomy.md` — the decision + build plan
- `research/rsi-verification-bound.md`, `research/agentic-hygiene-plateau-reward-hacking.md`
- `research/cross-model-review-failure-modes.md`, `research/negative-space-and-meta-epistemics.md`
- `research/intel-genomics-verifier-diagnosis.md` — applying this to the two repos
