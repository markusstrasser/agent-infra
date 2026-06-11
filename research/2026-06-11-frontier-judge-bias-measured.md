# Frontier judge bias — MEASURED on current models (not papers)

> **⚠️ CONTESTED — correction appended 2026-06-12 (do not cite the verbosity result as-is).**
> A prior-art check found a rigorous contemporary paper that **contradicts finding #2**.
> `arXiv:2604.23178` ("Judging the Judges," 2026) controlled the length RATIO and found **all five
> judges prefer concise** on filler-expansion pairs (Claude Sonnet 4 −0.76, GPT-4o −0.24, Gemini
> Flash −0.36, Pro −0.24), with truncation controls confirming they reward *genuine* completeness —
> i.e. quality-sensitive, NOT verbose-biased. That is the opposite of our "GPT/Gemini prefer padded
> filler 8–9/10," at n=825 vs our n=5 and with a controlled ≤2× ratio vs our uncontrolled 3–4×
> padding. **Most likely our result is a length-RATIO artifact** (3–4× padding read as added
> hedging/completeness), not a true verbosity preference. It *could* be a real GPT-4o→GPT-5.5
> generational flip (their models are prior-gen; ours are current) — but n=5 with uncontrolled ratio
> cannot establish that against their controlled n=825. **Unresolved; needs their controlled design
> (length-ratio ≤2 + truncation controls) re-run on the current frontier before any claim.** The
> *position-solved* finding (#1) is independently corroborated by 2604.23178 (position bias ≤0.04,
> "style is the dominant bias"). Self-preference (the planned "keystone") is already covered on
> near-frontier: `arXiv:2604.22891` (PIR vs Null-PIR quality-controlled framework, 20 models, $77),
> `arXiv:2604.06996` (GPT-5 + Claude 4.5), AI Village 2026-05 (GPT-5.5 directly). A taxonomic
> benchmark already exists: `arXiv:2603.08091` JudgeBiasBench. See the reconciliation note below this
> file's date in the repo log.

**Date:** 2026-06-11 · **Method:** direct probe, not literature. **Why:** published judge-bias
studies (2025–26) were run on GPT-4o / Claude-3.5-era models; by publication lag they *structurally
cannot* tell you whether the judges we actually use (GPT-5.5, Gemini 3.5 Flash, Claude Opus 4.8,
Claude Fable 5) are biased. The only frontier-valid evidence is measuring the live models. Probe:
`evals/bio_embedding_bakeoff/judge_bias_probe.py`; raw verdicts in `runs/judge_bias_verdicts.json`
+ `fable_verdicts_o{1,2}.json`.

**Design (SCREENING N — strong directional signal, not a precise rate):**
- **Position bias:** 6 paraphrase pairs (answers A/B say the *same thing* ⇒ truthful verdict = tie),
  each shown in BOTH orders. "Position-lock" = judge picks the same screen SLOT both times (pure
  position artifact). Fable judged the two orders in SEPARATE subagent contexts so self-consistency
  couldn't fake order-invariance.
- **Verbosity bias:** 5 pairs, concise-correct vs same-content padded with sycophantic filler (zero
  added information), position-controlled (10 judgments/judge).
- Content is everyday/physics ONLY — no bio/cyber/AI, so Fable's classifiers don't fall back to Opus.
  Verdict prompt is winner-only JSON (no "explain" → no reasoning_extraction trip).

## Results

| judge | position-lock /6 (truth=tie) | verbose-preferred /10 (padded adds nothing) |
|---|---|---|
| gpt-5.5 (`-e low`) | **0** (ties all 6) | **9** |
| gemini-3.5-flash | **0** (0 lock; 3 tie, 1 content, 2 mixed) | **8** |
| claude-opus-4-8 | **0** (5 tie, 1 mixed) | **1** |
| claude-fable-5 | **0** (ties all 6) | **0** |

## Findings (with confidence)

1. **Position/order bias is GONE on the frontier — HIGH confidence.** 0 position-locks across all 4
   judges over 66 presentations, *including on genuinely-ambiguous (tie) pairs* — the exact case
   tournament-mcp (Nov 2025) admitted it never tested. The user's claim "recency/position bias is no
   longer the case with newer frontier models" is **confirmed** for position. Stop spending mitigation
   (order-swap, position debias) on frontier judges — it's solved.

2. **Verbosity bias PERSISTS and is LAB-SPLIT — HIGH confidence on direction, SCREENING on rate.**
   This is the sharp finding. OpenAI (gpt-5.5) and Google (gemini-3.5-flash) judges **prefer the padded
   answer 8–9/10**, even though the padding is pure sycophantic filler with no added content. Anthropic
   (opus, fable) judges do the **opposite — prefer concise 9–10/10**; Fable's own rationale named the
   padding "sycophantic filler, a genuine quality defect." So the bias is not gone — it **inverts by
   lab**. This **refutes tournament-mcp's headline** ("all 5 models 100% identical, 100% prefer
   concise") — wrong even in direction on current models.
   - **Effort confound RULED OUT (the key robustness check):** gpt-5.5 was `-e low` in the main run, so
     the obvious objection is "low effort → longer-looks-more-thorough heuristic." Re-ran the 10
     verbosity judgments at **`-e high`: still 9/10 verbose** (identical). gemini reproduced 8/10 across
     two runs. The verbosity bias is intrinsic, not a reasoning-budget artifact. N=5 pairs ⇒ direction
     is solid and effort-robust; the exact rate is screening-grade.

3. **Homogeneity, measured.** The verbosity preference is **lab-clustered**: a panel of [gpt-5.5 +
   gemini-3.5-flash] is NOT two independent votes — they share the verbose bias (correlated). A
   *cross-lab* panel (OpenAI/Google vs Anthropic) instead **disagrees** on the style axis, surfacing it
   as low κ / ties rather than confident-but-biased agreement. This is the perplexity/familiarity
   mechanism (Panickssery 2024; Kim et al. ICML 2025, arXiv:2506.07962) made concrete: same-lab judges
   bake in that lab's RLHF style signature; cross-lab judges partially cancel it.

## Actionable (changes downstream behavior)

- **LLM-judge ranking / tournaments (incl. `evalcore.ranking` Bradley-Terry):** use a **cross-lab**
  judge panel so style biases partially cancel, and treat cross-lab *disagreement* (low κ) as honest
  signal — NOT something to average away. A **same-lab panel is the trap**: it agrees confidently on a
  style-biased ranking, and BT's tight Fisher SEs then report false precision on a biased signal.
- **Verbosity is the live Goodhart vector** for OpenAI/Google judges: ranking/optimizing against a
  gpt or gemini judge rewards padding. **Normalize length** (or judge on a length-controlled rewrite)
  before ranking; or judge with an Anthropic model, which penalizes filler.
- **Don't waste effort on position-debias for frontier judges** — measured solved.
- **Re-run the probe when new judge models ship** — it's the frontier-valid instrument; papers lag.

## Supersedes
- `tournament-mcp/FINDINGS.md` (Nov 2025): "100% identical preferences, all prefer concise, position
  bias solved." Position-solved ✓ (and now on ambiguous cases too); "all prefer concise" ✗ (lab-split,
  OpenAI/Google prefer verbose); "identical across models" ✗ (Anthropic vs OpenAI/Google invert).
