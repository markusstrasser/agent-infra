---
title: "Scope — CAS-as-RLVR-Verifier Probe (does a compiled CAS beat sympy at fixing false negatives?)"
date: 2026-06-08
tags: [scope, probe, rlvr, verifier, symbolic, experiment-design]
status: active
---

# Scope: CAS-as-RLVR-Verifier Probe

**Origin:** open seam from `symbolic-engines-in-frontier-training-2026-06-07.md` (claim 12, UNSOURCED) and `2026-06-08-symbolic-vs-neural-trajectory.md`. Thesis to test: a compiled, embeddable CAS doing canonical/Schwartz–Zippel equivalence checking is a better RLVR verifier than the status-quo regex/sympy-lite answer-matcher, by structurally eliminating false negatives.

**This is a research probe, not agent-infra tooling. Read the "Is this ours?" section before committing time.**

## The question, decomposed into falsifiable claims

The prior memo collapsed "rule-based verifier" and "sympy" into one baseline. They are not the same, and the real crux is the marginal gain *over sympy used properly*, not over regex.

| H | Claim | Why it's the crux |
|---|-------|-------------------|
| **H1 (recall)** | A CAS canonical-equivalence checker has a lower false-negative (FN) rate than regex/string answer-matching | Almost certainly true — but trivial; regex is a strawman |
| **H2 (marginal-over-sympy)** | CAS reduces FN **beyond what `sympy.simplify`/`.equals` already catches** | **THE decisive claim.** If sympy already closes the gap, a CAS is only a throughput play, not an accuracy one |
| **H3 (throughput)** | At equal accuracy, JIT-CAS + random-point Schwartz–Zippel is faster per check than sympy-in-a-sandbox | Determines whether the throughput play is even real at RL batch sizes |
| **H4 (downstream)** | Lower FN rate → measurable RL training improvement (faster convergence / higher final acc) | TinyV showed this for an *LLM* recall-fix (+10%); question is whether a *deterministic* CAS gets it cheaper and un-gameably |

## What already exists (reuse, do not rebuild)

The "no benchmark exists" framing in the prior memo was about the *CAS arm specifically*. The surrounding scaffolding is already built and open:

| Asset | What it gives | Source |
|-------|---------------|--------|
| **Big-Math-RL-Verified** + TinyV analysis | Labeled set with a measured **>38% false-negative rate** baseline; the FN problem quantified | uw-nsl/TinyV (code released); arXiv 2505.* / TMLR 7235 |
| **hkust-nlp/RL-Verifier-Robustness** | A rule-based vs model-based verifier **comparison harness** + HF `rl-verifier-pitfalls` data + equivalence-failure analysis | github.com/hkust-nlp/RL-Verifier-Pitfalls (25★, MIT); arXiv:2505.22203 |
| **eth-sri/llm-verifier-noise** | RLVR noise-injection training framework (TPR/FPR mixup) for Stage 2 | github.com/eth-sri/llm-verifier-noise (MIT); arXiv 2604.* |
| **Symbolica** | The CAS engine — **JIT-compiled evaluator now default in Python** (commit 4e56243, 2026-03), **arbitrary-precision eval 2× faster** (509b983, 2026-04), symjit machine-code bridge. Exactly the primitives the thesis needs | github.com/symbolica-dev/symbolica (757★, Rust; single maintainer benruijl — bus-factor risk, commercial license) |
| **sympy** | The baseline to actually beat (the real H2 control) | stdlib of the field |

**So the probe is: add a CAS arm to an existing verifier-comparison harness on an existing labeled set.** Not a from-scratch build.

## Stage 1 — the cheap, decisive probe (NO RL training)

Pure offline verifier comparison on labeled (model_answer, reference, is_equivalent) triples from the TinyV / RL-Verifier-Robustness data.

**Four arms:**
1. `regex` — string/normalized match (the weak baseline TinyV exposed)
2. `sympy` — `simplify(a-b)==0` / `.equals()` with a sane timeout (**the real control**)
3. `cas` — Symbolica canonical form + multi-precision Schwartz–Zippel random-point check
4. `tinyv` — the existing LLM recall-fix (the comparison point for "is a deterministic fix as good as the LLM one?")

**Measure per arm:** FN rate, FP rate, wall-clock per check, and **coverage** (% of pairs the symbolic arm can even parse — CAS only covers the formalizable-in-algebra slice; word problems, set/combinatorial/proof answers fall outside).

**Decision rule (the actual deliverable):**
- `sympy ≈ cas` on FN → CAS adds **nothing on accuracy**; only H3 throughput remains. If sympy is fast enough at batch scale → **NO BUILD**. *(My prior: this is the most likely outcome.)*
- `cas ≫ sympy` on FN **and** `cas` faster → genuine win → consider Stage 2.
- `cas ≈ tinyv` on FN, but CAS is **deterministic, cheaper, and un-gameable** (no FP reward-hacking surface that model-based verifiers have — RL-Verifier-Robustness shows model verifiers get hacked) → **strongest case for CAS**: same recall as the LLM fix without the hacking risk.

**Effort:** ~1–2 days. Data + harness + engine all exist; the work is wiring the Symbolica arm and a parsing/canonicalization adapter.

## Stage 2 — only if Stage 1 is strongly positive (likely NOT us)

Swap the verifier in a real GRPO loop on a small model (Qwen 4–7B) via the eth-sri or verl harness; measure convergence speed + final accuracy vs the sympy baseline. **This is real GPU training, outside agent-infra's operational scope** — it's a collaboration/paper, not infra we'd run. Don't start it without an explicit decision to do frontier-adjacent research.

## Is this ours? (constitution check — read before building)

- **Consumer:** NOT agent-infra. We don't run RLVR. Per the "name the consumer before building" rule, the honest consumer is *a paper / an intellectual answer*, not our pipeline. Our only transferable use — the judge-panel robustness lens (isomorphic perturbation) — is already captured.
- **Disconfirming prior (caps the upside):** "An Imperfect Verifier is Good Enough: Learning with Noisy Rewards" (arXiv:2604.07666, 2026-04) — RLVR tolerates ≤15% verifier noise within ~2pp of clean; conclusion: **prioritize precision over perfect recall.** A CAS is a *recall* fix. So the ceiling on H4's payoff is bounded; TinyV's +10% is the optimistic end, and the marginal-over-sympy slice is plausibly small.
- **Coverage ceiling (from prior memo):** verifier *coverage*, not speed, is repeatedly the binding constraint. A faster/sharper CAS does nothing for word-problem setup or natural-language answers.

## Recommendation

Stage 1 is cheap (~1–2 days), genuinely decisive, and intellectually clean — worth doing **iff** you want the answer for its own sake or a short note/paper. Lead with **H2** (marginal-over-sympy), because that's the question the prior memo glossed and the one most likely to kill the thesis. Most probable result: *"sympy already catches the equivalences; Symbolica is a throughput optimization that doesn't move accuracy"* — a clean, publishable negative. The one result that would be genuinely interesting: **CAS matches the LLM-verifier's recall deterministically and un-gameably** (the H3+hacking-immunity case), which would be a real argument for deterministic symbolic recall-fixes over TinyV-style LLM patches.

**Do NOT** jump to Stage 2 or a "build a CAS verifier service." Frame any work as the offline probe, with the go/no-go gate at the Stage 1 decision rule.

## De-risk results (2026-06-08) — both gates PASS

- **Symbolica:** installs (`uv add symbolica` → v2.0.0, 23 MB), runs **restricted single-core without any license key** (banner only; fine for offline batch). Confirmed `(1+x)^2 − (1+2x+x^2)` expands to `0`. License is **source-available, NOT open** (no redistribution); free hobbyist/academic/non-commercial-single-core tiers.
- **Dataset:** `zhangchenxu/HardVerify-Math` (TinyV benchmark, 250 rows) has built-in labels — no download needed (HF datasets-server stream). Each row: `ground_truth` + `fn_output` (should be EQUIVALENT — the false-negative traps) + `tn_output` (should be NOT equivalent — the true negatives). **= 500 labeled pairs.**
- **Early signal that sharpens H2:** the benchmark is dominated by answer *types* where CAS algebra is only partially applicable — functional-equation results (`f(x)=2x`), **unordered sets of integer tuples** (`(6,3),(9,3),...`). Tuple-set equality is set-normalization, not Schwartz–Zippel; `f(x)=2x` vs `f(x)=2 x` is whitespace/parse. So the **coverage ceiling will likely show loudly**: the CAS's algebraic edge may be confined to a small slice (e.g. `1/(1+x)^2` vs `(1+x)^-2`), while sympy + a set/tuple normalizer handles the rest equally. Report coverage per answer-type, not just aggregate.
- **Revised cost:** 500 pairs (not thousands) → Stage 1 is ~2 hrs agent wall-clock, low single-digit $. The LLM (TinyV) arm over 500 pairs is trivial.

## Key sources
- TinyV (FN >38%, +10% from recall-fix) — uw-nsl/TinyV; OpenReview HMGsqApBM3
- From Accuracy to Robustness (rule vs model verifiers; model verifiers get hacked) — arXiv:2505.22203; hkust-nlp/RL-Verifier-Pitfalls
- An Imperfect Verifier is Good Enough (≤15% noise OK; precision>recall) — arXiv:2604.07666
- Symbolica (JIT default, arbitrary-precision 2×) — github.com/symbolica-dev/symbolica commits 4e56243, 509b983
- eth-sri/llm-verifier-noise (RLVR noise-injection harness) — arXiv 2604.*
