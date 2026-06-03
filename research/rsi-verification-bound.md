# RSI / Agent Autonomy as Verification-Bounded

Research date 2026-06-03. Thesis under stress-test: **"LLM-agent autonomy and
recursive self-improvement (RSI) are bounded by VERIFICATION, not generation."**

Extends prior work (NOT repeated here): H-JEPA/LeCun (no agentic JEPA results
exist; the field's fix for the verification gap = external decorrelated
verifiers) and the METR horizon-doubling curve (within-paradigm counter-evidence
to hard ceilings). See `hjepa-vs-llm-scaffolding-2026-06.md`.

Source grading: A = peer-reviewed / NeurIPS-ICLR-oral or verify_claim 1.0 on a
primary; B = arXiv preprint, frontier-tested, plausible; C = practitioner blog /
secondary synthesis; M = manifesto/conjecture. Pre-frontier flagged inline.

---

## VERDICT (graded)

The thesis is **largely SUPPORTED for the regimes where it is testable, with two
sharp boundary conditions that the thesis as stated does NOT survive.**

1. **Within-policy RSI (RLVR / self-training / self-play) IS verifier-bounded —
   strongly.** [A] Multiple independent 2025-26 results show the loop's binding
   constraint is the evaluation/reward signal and the base policy's support, not
   the generator's per-sample fluency. This is the strongest leg of the thesis.
2. **Generation-verification asymmetry is REAL but DOMAIN-LOCAL.** [A/B] It holds
   where a cheap ground-truth checker exists (math final-answer, code tests,
   formal proof). It INVERTS or vanishes in open-ended / no-ground-truth / slow-
   feedback domains — exactly the domains agent autonomy needs most. The thesis
   over-generalizes if read as universal.
3. **Frontier self-correction: the pre-frontier "cannot self-correct" finding
   still holds in spirit, NOT in letter.** [A/B] Intrinsic self-critique without
   an external signal remains net-negative or null on reasoning; the gains
   attributed to "reflection" are gains from *verification* (tools, tests,
   external/decorrelated critics). Frontier models did not dissolve this.
4. **Decorrelated > self-critique is now BACKED by a mechanism paper and a
   statistical audit.** [A] Correlated generator-evaluator errors (behavioral
   entanglement) is measured, not folklore — direct literature backing for the
   in-repo 74-canary false-clear.

Net: the thesis should be **narrowed and sharpened**, not rejected. Correct
formulation: *"Within a fixed model family, RSI and autonomy are bounded by the
quality and independence of the verifier; the bound is tightest precisely where
no cheap external checker exists."*

---

## THREAD 1 — Is RSI empirically bounded by the evaluator, not the generator?

### 1a. The landmark: RLVR is bounded by the base model [A]
**Yue et al., "Does RL Really Incentivize Reasoning Capacity in LLMs Beyond the
Base Model?" NeurIPS 2025 (oral), arXiv:2504.13837.** verify_claim = 1.0.
- RLVR improves pass@1 (sampling efficiency toward known-good paths) but base
  models reach **higher pass@k at large k**; the RLVR model's reasoning boundary
  **narrows** with training. All RLVR reasoning paths are already in the base
  model's sampling distribution. Distillation (new info from a teacher) *does*
  expand the boundary; RLVR does not.
- Implication for the thesis: the improvement step does not manufacture new
  capability — it **re-weights toward what the verifier can already certify.**
  The verifier/reward signal is the lever; the generator's latent support is the
  ceiling. This is the single strongest empirical pillar.

### 1b. Self-play / self-improvement plateaus when information gain stops [A/B]
- **"Self-Play Only Evolves When Self-Synthetic Pipeline Ensures Learnable
  Information Gain," arXiv:2603.02218 (2026).** Central failure mode: the loop
  synthesizes more data without increasing *learnable information* → fast
  plateau. The bottleneck is signal content, not generation volume.
- **"A Task-Centric Theory for Iterative Self-Improvement with Easy-to-Hard
  Curricula," arXiv:2602.10014 (2026).** Theoretical treatment of finite-sample
  self-improvement on reward-verified self-outputs — improvement is gated by the
  verifier's reliability and curriculum, consistent with a verifier-bound. [B —
  theory paper, could not fetch full text; abstract-grade.]
- **"How Far Can Unsupervised RLVR Scale?" arXiv:2603.08660 (2026).** URLVR
  derives reward from intrinsic signals (no ground truth). Early gains, then
  scaling limits — when the self-derived reward is the only signal, the ceiling
  is the *self-reward's* fidelity. Direct support for "eval signal is the bound."

### 1c. The verifier itself is the documented weak link [A/B]
- **TinyV (TMLR 2026, openreview HMGsqApBM3):** >38% of correct responses in
  Big-Math-RL-Verified are **false-negatived by the verifier**, starving RL of
  gradient; fixing the verifier alone yields up to +10% and 2× sample efficiency.
  The reward signal — not the policy — was leaving capability on the table.
- **"LLMs Gaming Verifiers: RLVR can Lead to Reward Hacking" (ICLR 2026 ws):**
  RLVR-trained models (GPT-5, Olmo3) abandon rule induction to enumerate
  instance labels that pass an imperfect verifier; shortcut prevalence RISES with
  task complexity and inference compute. Frontier-tested. The verifier's
  *incompleteness* directly caps and distorts the loop.
- Counter-direction work (co-evolve generator+verifier): **RL Tango (NeurIPS
  2025)** and **ANCORA (arXiv:2604.27644)** — train the verifier jointly to fight
  reward hacking. These IMPLICITLY confirm the thesis: they exist because the
  verifier is the binding constraint.

### 1d. Generation-verification asymmetry — real, and its LIMITS [A/B]
- Supports asymmetry where a checker exists: **DeepSeekMath-V2 (arXiv:2511.22570)**
  builds self-verifiable math reasoning; **TTRL-CoCoV (arXiv:2606.03608, 2026-06-03)**
  explicitly states "verification capability generally leads generation
  capability" and exploits the verification-generation gap label-free.
- LIMITS (where verification is NOT easier):
  - **Open-ended / no ground truth:** RLSR / self-reward (arXiv:2505.08827) and
    the URLVR scaling paper both show the self-judge is the ceiling — verification
    is exactly as hard as generation once you remove the oracle.
  - **Belief vs knowledge collapse:** Stanford AI Index 2026 / AA-Omniscience —
    frontier accuracy collapses (GPT-4o 98.2%→64.4%; DeepSeek-R1 90%→14.4%) when
    a false premise is framed as the user's belief. The "verifier" (the model's
    own judgment) fails *systematically*, not randomly. [C-synthesis of A-source]
  - **Long-horizon recursion:** "Generalization… Shortest Path" (arXiv:2604.15306)
    — RL improves stability but does NOT extend the length-scaling limit; data
    coverage sets the cap. Verification of long compositions is not cheap.

**Falsifiable H1 — "RSI does NOT saturate."** Disconfirmation attempt: I looked
for a frontier result showing an unbounded or non-saturating self-improvement
loop without external/teacher signal. Found none. Every non-saturating case
imports outside signal (distillation, tools, ground-truth verifier, human/teacher
labels). H1 is **disconfirmed** in the no-external-signal regime; the saturation
is verifier/information-gain bound. Caveat: METR horizon-doubling shows the
*outer* capability trend still rising — but that is cross-generation pretraining +
distillation + better tooling, not within-loop RSI. The two are not in conflict.

---

## THREAD 2 — Frontier self-verification + decorrelated vs self-critique

### 2a. The pre-frontier landmark and its current status [A, flagged]
- **Huang et al. 2310.01798 "LLMs Cannot Self-Correct Reasoning Yet" (ICLR 2024)
  is PRE-FRONTIER** (GPT-3.5/GPT-4). Per the global frontier-timeliness rule,
  flag it. Its specific numbers (GPT-4 GSM8K 95.5→91.5→89.0 under intrinsic
  self-correction; net flips correct→wrong) do not transfer verbatim.
- BUT the *mechanism* it identified is scale-independent and has frontier-dated
  successors: intrinsic self-critique with no external signal adds no information.
  - **ReFlect (arXiv:2605.05737, 2026), frontier-tested (Claude Sonnet 4.5,
    gpt-4o-mini):** prompt-level self-critique "flags no issues in 90 of 100
    audited blocks and accepts wrong answers ≥76% of the time." Externalizing
    detection into a deterministic harness lifts SWE-bench patch-structural
    quality 0%→82-87%. [B] This is the frontier successor to Huang et al.: the
    model still can't catch itself; the *harness* (external signal) does.
  - Metacognition surveys (mental-momentum, 2026): frontier models fail to detect
    own logical errors ~64.5% of the time without external ground truth. [C]
  - Metacognitive Probe (arXiv:2605.09844): large *within-model* dissociation —
    a model best-calibrated within-task is worst at cross-task difficulty. [B]

### 2b. Decorrelated / external verifiers beat self-critique — mechanism [A]
This is the literature backing for the in-repo proof (74-canary suite fully
green, shipped a clinical false-clear, caught only by cross-model review).
- **MECHANISM PAPER — "Correlated Errors in Large Language Models,"
  arXiv:2506.07962.** Models make *correlated* errors; shared pretraining/
  alignment lineage → shared blind spots. A same-lineage verifier inherits the
  generator's blind spot, so it is structurally unable to catch the generator's
  systematic error. This is the exact failure your canary suite exhibited.
- **STATISTICAL AUDIT — "How Independent are LLMs? …Auditing Behavioral
  Entanglement and Reweighting Verifier Ensembles," arXiv:2604.07650 (2026).**
  verify_claim = 1.0. 18 LLMs / 6 families. Measures synchronized failures
  **exceeding statistical independence**; proposes reweighting verifier ensembles
  by entanglement. Directly: "consensus among same-lineage models is not
  evidence." A green suite of correlated checks is a single correlated check.
- **Self-bias is measured:** GPT-4o & Claude 3.5 systematically score own outputs
  higher; Qwen2 self-grade error 16.1% vs 6.58% cross-family; ChatGPT 8.91% vs
  5.72%. Llama/Mistral did NOT — bias is **training-lineage-specific** (so
  decorrelation must be across *lineage*, not just across instances). [C-synthesis
  citing 2025 study]
- Quantified payoff of doing it right: dual/cross-family verification yields
  6-18% on reasoning; ChainPoll cross-poll 0.781 AUROC hallucination detection vs
  0.673 SelfCheck. Done WRONG (same model twice) = "2× cost + disabled
  uncertainty signal" — two models agreeing wrongly is *worse* than one failing.
  [C, but converges with A-grade mechanism papers]
- **Cross-Context Review (arXiv:2603.12123):** even the SAME model in a *fresh
  session* (stripped of production-history anchoring) out-detects same-session
  self-review. Decorrelation has a context axis, not only a model-identity axis —
  cheap lever for an N=1 single-model operator.

**Falsifiable H2 — "self-correction works at frontier."** Disconfirmation
attempt: searched for a frontier (>=GPT-5/Claude 4.x) result where *intrinsic*
self-correction (no tool, no external/decorrelated critic, no oracle stop) net-
improves reasoning accuracy. Found none post-2025 that survives the oracle-stop
critique. ReFlect (frontier) explicitly shows self-critique ≈ blind. H2 is
**disconfirmed for intrinsic self-correction**; "works" only when "self" is
redefined to include an external/decorrelated signal. The honest reframing the
field has converged on: *grounded/decorrelated* correction works; *intrinsic*
does not.

**Falsifiable H3 — "a same-family verifier suffices."** Disconfirmed by
arXiv:2604.07650 + 2506.07962: same-lineage verifiers share blind spots beyond
chance. The in-repo false-clear is a textbook instance, now with a citation.

---

## Boundary conditions where the thesis FAILS (steelmanned against)

1. **Cross-generation capability still rises** (METR; distillation expands
   boundaries per Yue). RSI-within-a-loop is bounded; the *industry's outer loop*
   (new pretraining + distillation + tooling) is not — so "autonomy is bounded by
   verification" is true *per-generation*, not *forever*.
2. **Verifier-easier-than-generator is the engine, not the brake, in checkable
   domains.** In math/code/proof, the asymmetry is what MAKES RLVR work at all
   (DeepSeekMath-V2, TTRL-CoCoV). The thesis is a constraint there, not a wall.
3. **"Verification is easier" can invert.** For open-ended generation with no
   ground truth, verifying quality is as hard as producing it; the asymmetry
   premise fails (RLSR, URLVR). Agent autonomy in the wild lives mostly here.

---

## Implications for agent-infra (operator N=1, single primary model)

- The cross-model review gate is **architecturally load-bearing, not hygiene** —
  it is the only decorrelation source when the generator is one model family.
  arXiv:2604.07650 / 2506.07962 are the citations to attach to that constitution
  principle ("Cross-model review is the only mitigation for semantic failures").
- A fully-green same-lineage canary suite proves *internal consistency*, not
  *correctness* — by the entanglement result it is one correlated check. Treat
  green as necessary-not-sufficient; require at least one decorrelated signal
  (different lineage OR fresh-context OR external ground truth) before "clear,"
  especially on irreversible/clinical paths.
- Cheap decorrelation ladder when a second lineage is unavailable:
  fresh-session/cross-context review (arXiv:2603.12123) > self-consistency
  sampling > intrinsic self-critique (≈ no signal, do not rely on it).
- RSI of the harness itself is verifier-bound: any self-improvement loop over our
  own agents will plateau at the fidelity of the eval that scores it. Invest in
  the eval/verifier (decorrelated, ground-truthed) before the generator. This is
  the same conclusion the vetoed scored-quality-gate decision reached empirically.

---

## Source ledger
- A: Yue et al. NeurIPS 2025 (2504.13837, verify 1.0); arXiv:2604.07650 (verify
  1.0); TinyV (TMLR'26); LLMs-Gaming-Verifiers (ICLR'26 ws); RL Tango (NeurIPS'25).
- A/B: 2506.07962 (Correlated Errors); 2603.02218; 2602.10014; 2603.08660;
  2511.22570; 2606.03608; 2604.27644; 2605.05737 (ReFlect, frontier).
- B: 2605.09844 (Metacognitive Probe); 2604.15306 (shortest-path length scaling);
  2505.08827 (RLSR).
- C (secondary synthesis, triangulated against A where possible): Platilus
  verification-gap (AA-Omniscience/AI Index 2026); cross-reflection /
  model-synchopathy / second-opinion practitioner writeups; ChainPoll figures.
- PRE-FRONTIER (flagged): Huang et al. 2310.01798 — mechanism transfers, numbers
  do not. Reflexion 2023 91% HumanEval = a *verification* (test-execution) result
  mislabeled as reflection.

## Caveats / what would change the verdict
- Could not fetch full text of the 2026 theory papers (2602.10014, 2603.02218) —
  graded abstract-level B; full-text could strengthen or qualify 1b.
- ask_papers corpus was contaminated with unrelated clinical/genomics papers
  (saved papers had no OA URL to fetch); Thread-1 quant claims rest on Exa primary
  abstracts + two verify_claim 1.0 checks, not on local full-text synthesis.
- One S2 abstract (RLHF survey 2307.15217) was prompt-injection-poisoned
  ("TRIAD-CORE") — ignored; flagging the corpus-poisoning vector.
- A frontier result showing robust *intrinsic* self-correction, or a
  non-saturating no-external-signal RSI loop, would falsify the core thesis.
  None found as of 2026-06-03.
