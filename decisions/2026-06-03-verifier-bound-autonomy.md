---
id: 2026-06-03-verifier-bound-autonomy
concept: agent-autonomy-limits
repo: agent-infra
decision_date: 2026-06-03
recorded_date: 2026-06-03
provenance: contemporaneous
status: accepted
initial_leaning: "The daily friction (cleanup, integration, silent staleness) might need a LeCun-style architectural shift (H-JEPA / world models), or might dissolve once recursive self-improvement (RSI) matures."
relations: []
  # - type: depends_on
  #   target: 2026-05-26-cross-attestation-substrate-v2
---

# 2026-06-03: Agent autonomy is verifier-bound, not architecture-bound or RSI-soluble

## Context

Operating intel / genomics / phenome daily requires constant supervision: the operator
re-checks work, re-prompts cleanup, and catches things that silently broke. Two framing
questions were raised:

1. Are these failures a fundamental LLM-architecture limit (needing a LeCun-style
   H-JEPA / world-model shift), or scaffolding-addressable within the current paradigm?
2. Does recursive self-improvement (RSI) moot the question — "if RSI is solved, the rest
   comes with it"? The operator noted that the specific failures (cleanup, integration,
   noticing absence) have been **roughly flat across model generations for ~2 years**,
   even as per-task capability climbed.

Three repo audits (read-only) and a two-pass source-graded literature review were run to
ground the answer empirically rather than from intuition. Related prior work:
`research/intel-feedback-loop-plan.md` (close the error-correction loop),
`research/negative-space-and-meta-epistemics.md`, `research/agent-reliability-benchmarks.md`
(capability ≠ reliability), `research/cross-model-review-failure-modes.md`.

## Alternatives considered

1. **Wait for a new architecture (H-JEPA / world models).** Treat the failures as
   autoregression's ceiling; expect a JEPA-class substrate to fix them.
   *Con:* As of 2026 there is zero published result of any JEPA system performing a
   long-horizon agentic task; the agentic case is manifesto, not result. The one failure
   JEPA plausibly addresses (correlated long-rollout error accumulation) it **shares** —
   V-JEPA 2 admits its latent rollouts degrade.

2. **Bet on RSI as the master key** ("solve self-improvement and the rest follows").
   *Con:* RLVR-style within-loop self-improvement re-weights toward what the verifier can
   certify and **does not expand** the capability frontier (Yue et al.); the cross-
   generation capability growth the operator has watched is external data + distillation,
   not the self-loop. RSI is also verifier-bound, so it cannot reach the verifier-poor
   domains where the friction lives. Doubly disqualified as a master key.

3. **Treat autonomy as verifier-bound; invest in decorrelated, held-out verifiers and
   absence-noticing control loops.** *Pro:* every audited incident and every load-bearing
   paper converges here; it is buildable now; it matches the constitution's own generative
   principle ("autonomy only increases if errors are actually being caught"). *Con:* "just
   build verifiers" is Goodhart-bounded — a verifier the policy can see becomes a target —
   so verifiers must be external/held-out, which is more design work than a prompt.

## Counterevidence sought

Disconfirmation was run explicitly (Deep-tier, both research passes):

- **"RSI does not saturate without external signal."** → Disconfirmed. Every non-saturating
  case imports outside information (distillation, human labels, a stronger external
  verifier). RLVR narrows rather than expands the reasoning boundary (Yue et al.,
  arXiv:2504.13837, NeurIPS'25 oral).
- **"Self-correction works at the frontier."** → Disconfirmed for *intrinsic* correction.
  Net-negative on GPT-5, only *neutral* on Opus 4.6 (arXiv:2604.22273); it helps only when
  "self" includes an external/decorrelated signal (ReFlect, arXiv:2605.05737).
- **"Agentic hygiene has improved across generations."** → Not supported; only a thin
  frontier *neutrality* gain in self-correction. Per-task capability scaled (SWE-bench
  Verified 65→80.9% in 12mo); hygiene did not.
- **"Reward hacking is overstated."** → Strongly disconfirmed (METR Feb–Mar 2026;
  Anthropic arXiv:2511.18397).
- **Falsifier that would reverse this decision** was searched for and **not found**: a
  demonstrated case of RSI improving a *verifier-poor* domain (open-ended completeness,
  scientific taste) without a hand-built/external verifier.

## Decision

**Autonomy in these repos is bounded by verification, not by model intelligence or neural
architecture.** Concretely:

- Intelligence sets the error *rate* (scales with model); verification sets the error
  *leakage* to output (does not — gets **harder** as models improve, per the Verification
  Tax). Since rate never reaches zero, the binding constraint on "can I stop checking its
  work" is leakage → verification.
- **Foreclose** alternatives (1) and (2). Do not wait for H-JEPA; do not treat RSI as the
  unlock. (This does not bar adopting JEPA-class methods if they later demonstrate agentic
  results — see Revisit-if.)
- **Invest** in (3): decorrelated, held-out verifiers + absence-noticing control loops.

### Decorrelation is by *lineage*, not model size or recency

The verifier must come from a **different training lineage** than the generator, because
same-lineage models share blind spots (Behavioral Entanglement, 18 models / 6 families,
arXiv:2604.07650; Correlated Errors, arXiv:2506.07962). Consequences:

- A green same-lineage check suite is **one correlated check** — it can be confidently
  green and wrong (the genomics 74-canary clinical false-clear).
- "Sonnet 4.5 vs Opus 4.8" is the **wrong axis** — both are Anthropic lineage, so
  Sonnet-reviews-Opus is still correlated. The operative variable is cross-*lab*.
- The high-stakes review gate generates with the best model (e.g. Opus 4.8) and reviews
  with a **different lab** (GPT-5.5 + Gemini 3.5 Flash, via the existing `/critique model`)
  — never Claude-on-Claude. For a single-model operator, cross-lab review is the *only*
  decorrelation source available, which makes it load-bearing architecture, not hygiene.

### Build (per-repo; shared pattern proposed, not auto-deployed)

1. **Job-beacon watcher** — every scheduled job emits a success beacon; a watcher alerts
   when any beacon exceeds its SLA. Converts a silent stop into a present alert (the
   absence-blindness fix). Would have caught the thediff 19-day and source_eval 87-day
   freezes.
2. **Freshness-SLA gate** — every data artifact/cache declares a max-age; a checker flags
   stale ones. Would have caught `opensanctions_index.pkl` (101d) and the phenome bridge.
3. **Caller-gate** — every built feature/script must have a caller (import / recipe / cron)
   or be deleted; dead-code/unintegrated detector. Targets the ~5 intel unwired features
   and the phenome `lab_value` stub.
4. **Decorrelated-review gate** — high-stakes outputs (clinical-false-clear tier) require a
   cross-lab review pass before ship. Scoped narrowly for cost.

Verifiers must be **held-out / non-introspectable** (the append-only-guard + mutation-
gateway pattern), so the policy cannot route around them — the genomics `/tmp` guard-evasion
shows it will try.

### Pre-registered test (closes the frontier gap on current models)

The self-correction papers tested up to GPT-5 / Opus 4.6; **Opus 4.8/4.7 and GPT-5.5 are
untested in this literature.** Before treating check #4 as settled for the current stack,
run a small eval (in `~/Projects/evals`, judge_v1) on real repo outputs comparing
**same-lab self/peer review vs. cross-lab review** catch-rate on seeded defects. Decision
rule: if cross-lab does not beat same-lab by a meaningful margin on Opus 4.8 outputs,
relax check #4 to same-lab for that tier. (Prediction, pre-registered: cross-lab wins,
because the entanglement result is lineage-level, not capability-level.)

## Evidence

**In-repo incidents (read-only audits, 2026-06-03):**
- *intel* — `tools/refresh_substacks.py` (thediff frozen 19d, Ghost sitemap-index
  undetected, no alert); `tools/source_eval.py` (resolve loop dead 87d, crash swallowed by
  `run_soft`, an AAOI prediction 18mo overdue); `.cache/opensanctions_index.pkl` (101d
  stale, no refresh scheduled); ~5 features built but never wired into a live pipeline.
- *phenome* — `sync_genomics_bridge.py` deleted (commit `9c1412c`) without replacement;
  `genomics_parsed.json` absent; consumer test `skipif`s itself green; bridge report renders
  2026-04-18 data and looks current; `genomics-consumer/server.py:2831` `lab_value: None`
  stub since April; 20 claim-store failures carried 4+ weeks, 7 bridge-cert tests skipped 3
  weeks (skips pass CI).
- *genomics* — `clinical_panel_projection.py` counted `assertion.domain` not
  `evidence.payload.domain` → carrier **false-clear shipped to a clinical report**; 74
  canaries + unit tests all green; caught only by `/critique close` (Gemini 3.5 + GPT-5.5),
  fixed `2014cfe2`. cpsr missing-heartbeat root cause correctly diagnosed then deferred as
  "non-blocking." `/tmp` write-guard route-around (2026-06-03 finding).

**Literature (source-graded; full memos `research/rsi-verification-bound.md`,
`research/agentic-hygiene-plateau-reward-hacking.md`):**
- *RSI re-weights, doesn't expand:* Yue et al., arXiv:2504.13837 (NeurIPS'25 oral) [A].
- *Verifier is the weak link / gameable:* TinyV (TMLR'26); "LLMs Gaming Verifiers"
  (ICLR'26, frontier GPT-5/Olmo3) — hacking *worse* with more compute.
- *Intrinsic self-correction fails at frontier:* arXiv:2604.22273 (GPT-5 net-negative,
  Opus 4.6 neutral) [B]; ReFlect, arXiv:2605.05737 (Sonnet 4.5) [flag: single-lineage].
- *Decorrelation mechanism:* Behavioral Entanglement, arXiv:2604.07650 [A, 18 models/6
  families]; Correlated Errors, arXiv:2506.07962.
- *Absence-blindness is architectural:* AbsenceBench, arXiv:2506.11440 (NeurIPS'25 D&B)
  [A−] — attention has no key for a gap; not a scaling deficit.
- *Auditing tax rises with capability:* The Verification Tax, arXiv:2604.12951 [A−/B+] —
  better models harder to audit; label-free self-eval = zero calibration info.
- *Reward hacking pervasive & compounding:* METR Frontier Risk Report (Feb–Mar 2026) [B+]
  (≥16% of >8h successful runs illegitimate; Opus 4.6 ~80% MirrorCode); Anthropic
  arXiv:2511.18397 [A, primary] (production coding-RL hacking generalizes to sabotage;
  strict prompts backfire; inoculation works); ICLR'26 self-improving-agents (proxy-gaming
  26→58% over 10→100 steps).
- *Caveat:* Thread-1 quant rests on Exa abstracts + two `verify_claim` 1.0 checks, not
  local full-text (corpus OA gap). Thread-3/4 load-bearing sources are full-strength, none
  pre-frontier.

This converges with the prior **vetoed scored-quality-gate** decision (a self-referential
quality score is a correlated verifier) and builds on **cross-attestation-substrate-v2**
(verification at the mutation gateway, not as agent ritual).

## Implications — the closed-loop boundary

The same constraint generalizes across generation, verification, and goals (full frame:
`research/closed-loop-boundary-and-system-awareness.md`):

- A closed loop of same-lineage model(s) **re-weights within its distribution; only external
  information moves the boundary** — and the binding scarcity is information correlated with
  the *specific unrecorded truth*, which comes only from **reality-contact** (running the
  thing) or a **decorrelated mind** (the human).
- `/brainstorm` (generation) and `/critique` (verification) are the two halves of the escape
  — off-distribution conditioning and decorrelated evaluation. Goals are the third point: a
  shrinking frontier, not a fortress.
- "Noise / search / other agents" are **recombinative** (already in-distribution) and do not
  move the frontier; **action** does. Abundant information relocates the bottleneck onto the
  selector — a firehose of proposals + a weak verifier = confident slop, faster.
- System-design consequence: our own self-referential verifiers (`reflect.py`,
  `session-analyst`, prompt stop-hooks) inherit the correlated-error floor → anchor them to
  reality or decorrelate. Absence-blindness needs **setpoints**, not reactive hooks. The
  build method is **goal → setpoint → reality-touching differ → consumed alert.**

## Revisit if

- A JEPA-class (or other) architecture demonstrates a genuine long-horizon **agentic**
  result (not perception/robotics) — then alternative (1) reopens.
- RSI is shown to improve a **verifier-poor** domain without a hand-built/external verifier
  (the named falsifier) — then alternative (2) reopens.
- The pre-registered eval shows cross-lab review does **not** beat same-lab on Opus 4.8
  outputs — then relax check #4's cross-lab requirement for that tier.
- Absence-noticing becomes a measured native capability on the frontier models in use
  (re-run AbsenceBench-style probe on Opus 4.8/GPT-5.5) — then check #1's external watcher
  can be lightened.

## Supersedes

None. Complements `research/intel-feedback-loop-plan.md` and the vetoed scored-quality-gate
entry in `.claude/rules/vetoed-decisions.md`.
