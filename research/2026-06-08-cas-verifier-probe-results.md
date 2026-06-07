---
title: "RESULTS — CAS-as-RLVR-Verifier Probe (Stage 1): a faster CAS is a throughput win, not a recall fix"
date: 2026-06-08
tags: [results, probe, rlvr, verifier, symbolic, experiment]
status: complete
---

# RESULTS: CAS-as-RLVR-Verifier Probe (Stage 1)

**Scope:** `2026-06-08-cas-verifier-probe-scope.md` · **Code/data:** `experiments/cas-verifier-probe/`
**Benchmark:** `zhangchenxu/HardVerify-Math` (TinyV), 250 rows → **500 labeled pairs** (250 equivalent `fn_output`, 250 wrong `tn_output`, vs `ground_truth`). Adversarially curated to be *hard for rule-based verifiers* — it IS the false-negative tail.
**Arms (4):** `regex` (string baseline) · `sympy` · `symbolica` (Symbolica 2.0, JIT + Schwartz–Zippel numeric fallback) · `llm` (gpt-5.5, batched, structured). sympy and symbolica share ONE structural wrapper (set/tuple/equation handling); only the algebra engine differs — isolates the CAS-vs-sympy question.

## Verdict
**The CAS-as-verifier thesis is a throughput optimization, not a recall fix.** On this hard-tail benchmark, a compiled CAS does **not** close the false-negative gap that matters — only the LLM does. The interesting branch from the scope ("CAS matches the LLM's recall deterministically and un-gameably") is **FALSE**: Symbolica's FN is 55.6% vs gpt-5.5's 6.8%. What the CAS *does* deliver, unambiguously, is **~180× faster checks** than sympy.

## Headline numbers (overall, 500 pairs)

| arm | coverage | FN rate | FP rate | acc(covered) | ms/pair |
|-----|----------|---------|---------|--------------|---------|
| regex | 100% | 89.6% | 0.0% | 55.2% | 0.01 |
| sympy | 65.2% | 66.0% | 0.6% | 66.9% | 18.38 |
| symbolica | 49.4% | 55.6% | 2.4% | 70.9% | **0.10** |
| **llm (gpt-5.5)** | **100%** | **6.8%** | 1.2% | **96.0%** | 144.9* |

\*LLM ms/pair is wall-clock incl. network; the real cost is $ + latency, not CPU.

## The three hypotheses from the scope, resolved

- **H1 (beats regex):** ✅ trivially — both CAS engines beat regex's 89.6% FN. (Regex was always a strawman.)
- **H2 (CAS reduces FN *beyond sympy*):** ⚠️ **NOT a clean win.** Symbolica's lower nominal FN (55.6% vs 66.0%) is **confounded**: it abstains more (49% vs 65% coverage — it declines the hard ones) and accepts more numerically (FP 2.4% vs 0.6%). Accuracy-on-covered is close (70.9% vs 66.9%). It's a *different operating point* (abstain-more + numeric-accept-more), not a categorical recall improvement. On the algebraic home turf (expression+numeric) both are terrible: sympy 86.4% FN / symbolica 80.5% FN.
- **H3 (throughput):** ✅ **large, clean CAS win.** Symbolica **0.10 ms/pair vs sympy 18.38 ms — ~180×**. Matches the thesis (JIT-compiled evaluator + arbitrary-precision). At RL throughput (millions of checks) this is real.

## Why both CAS engines fail on recall (per-kind)
The unsolved equivalences are **semantic/notational, not algebraic** — exactly the slice a CAS can't reach:
- **numeric** (78 pairs): FN ~95% for both — dominated by **rounded decimals** (`600/7` vs `85.71`). Exact arithmetic says "not equal"; the benchmark (and the LLM) accept it.
- **interval** (8): intervals vs inequalities (`(-∞,-5)` vs `k<-5`) — symbolica 0% coverage.
- **set/tuple/list** (176): order-independent set equality is handled by the *wrapper*, not the CAS; ~50-56% FN from messy candidates (prose, alt-notation).
- **equation/function** (82): the one place symbolica's algebra helped — FN 28% vs sympy 42%.
- **matrix** (6): ~0% coverage for both.

gpt-5.5 handles all of these (interval↔inequality, rounded decimals, prose-described sets, functional forms) → 6.8% FN at full coverage.

## Honesty caveats
1. **Benchmark is adversarial.** HardVerify-Math is the curated hard tail. On random RL rollouts deterministic coverage would be far higher and the LLM's marginal benefit smaller — so these FN rates are a *worst case* for the symbolic arms, and the LLM's dominance is *upper-bounded* here.
2. **Deterministic arms are a reasonable wrapper, not a maximally-tuned `math_verify`.** Absolute deterministic numbers are a floor; the *controlled* sympy-vs-symbolica comparison (same wrapper) and the LLM-dominance gap are the robust parts.
3. **Symbolica's small FP edge was mostly wrapper artifacts** (over-aggressive RHS-stripping on `y+1=...`, LaTeX-command dropping on `\rho\sin\theta`), **not** Schwartz–Zippel numeric coincidence — the numeric fallback behaved well (0 obvious numeric FPs in the audit). So the CAS doesn't *inherently* trade more FP.

## The actual deployment implication: a cascade (not "swap the verifier")
Deterministic arms have **low FP** (a deterministic "equivalent" is trustworthy) but **high FN** (they miss). So: **trust a deterministic TRUE; route deterministic-FALSE/abstain to the LLM.** Measured cascade (symbolica∨sympy TRUE trusted, else gpt-5.5): **acc 95.6%, FN 6.4%, FP 2.4%** — i.e. ~LLM accuracy. On *this* benchmark it only saved 12% of LLM calls (the hard tail resolves almost nothing deterministically), **but that 12% is a worst-case floor** — on a normal rollout distribution the deterministic front resolves the easy majority for free/fast, and the cascade saves most LLM calls while shrinking the LLM-verifier's reward-hacking surface (the documented failure of pure model-based verifiers). Symbolica's 180× speed makes it the right *front* of that cascade.

## Bottom line for the original question
This closes the open seam from `symbolic-engines-in-frontier-training-2026-06-07.md` (claim 12): **a dedicated fast CAS does not out-recall sympy in a way that matters, and neither closes the gap to an LLM judge.** The recall fix is the model (TinyV's own conclusion); the CAS's contribution is *speed* and *determinism/precision as a cheap front filter*, not accuracy. Consistent with the disconfirming prior ("An Imperfect Verifier is Good Enough", arXiv:2604.07666: prioritize precision over perfect recall). **No build recommended; Stage 2 (RL training) not warranted** on this evidence.

## Reproduce
```bash
cd experiments/cas-verifier-probe
uv run python3 fetch_data.py   # -> pairs.jsonl (no dataset download; HF datasets-server)
uv run python3 run.py          # -> results.md, results.json  (needs OPENAI_API_KEY for the llm arm)
```
Cost: ~$ low single digits (gpt-5.5 over 500 pairs, reasoning_effort=low). Symbolica runs free restricted single-core.
