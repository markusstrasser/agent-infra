# Extending the /brainstorm Axes — New Creativity Research (Mar–May 2026)

**Question:** Is there new research (last ~2 months) that could extend the perturbation axes in the `/brainstorm` skill (denial cascades, domain forcing, constraint inversion) to increase divergent-ideation quality?
**Tier:** Deep | **Date:** 2026-05-30
**Date anchor:** Mar–May 2026 (AI/ML is fast-moving; biased to last 90 days). Tool: Exa (S2 returns empty for ML topics).

## Ground Truth — what the skill cites today

`/brainstorm` rests on three perturbation axes plus a multi-model-is-volume-not-diversity stance:
- **Denial cascade** — NEOGAUGE (NAACL 2025): "novelty rises continuously with denial depth."
- **Domain forcing** + **constraint inversion** — analogical/assumption perturbation.
- **Mode discipline** (generate in Steps 2–3, evaluate in 4–5) — backed by HAIExplore v2 (2512.18388): execution-first interfaces cause premature convergence / design fixation.
- **Perspective-guided divergence** — STORM (+25% org, +10% breadth).
- Stance: *"the prompting structure does the work; model choice is for volume and availability, not diversity."*

The new literature **strongly validates that stance** and offers **two genuinely new prompt-level axes** the skill does not yet have, plus refinements to the dispatch model.

## Claims Table

| # | Claim | Evidence | Conf | Source | Status |
|---|-------|----------|------|--------|--------|
| 1 | Asking the model to emit N responses **with explicit probabilities** ("verbalize a distribution") relieves typicality pressure and raises creative-writing diversity **1.6–2.1×** vs direct prompting; training-free; *more capable models benefit more*. | ICML 2026 poster, multi-task (poems/stories/jokes, dialogue, synthetic data, open QA) | HIGH | Verbalized Sampling, Zhang et al., [icml.cc/virtual/2026/poster/60489](https://icml.cc/virtual/2026/poster/60489) | VERIFIED |
| 2 | Mode collapse has a **data-level root cause**: typicality bias in preference data (annotators favor familiar text). Not just an algorithmic artifact. | Theoretical + empirical on preference datasets | HIGH | Verbalized Sampling (same) | VERIFIED |
| 3 | A **single planning call that stratifies generations across broad semantic directions** gives the best diversity–quality–compute frontier for idea pools — beats seed-anchored regeneration under full token accounting. "Population-referential divergence" (diverge from the population, not a seed) is a strong low-cost baseline. | 3 creative task families, anchorless vs anchored baselines | HIGH | Anchorless Diversification, Ibrahim et al., [arxiv 2605.30150](https://arxiv.org/pdf/2605.30150) | VERIFIED |
| 4 | Under matched prompt conditioning, **single-agent generation beats multi-agent systems on semantic diversity**. A **Multi-Output strategy** (one agent, many responses in one pass) gives the highest diversity without losing validity. Cause: "information visibility" — a serial agent conditions on its own history to avoid redundancy; parallel agents converge. | Controlled study, divergent-thinking tasks | HIGH | Single-Agent > MAS, [openreview ZQVnJXLMkR](https://openreview.net/forum?id=ZQVnJXLMkR) | VERIFIED |
| 5 | In multi-agent ideation, **expert/authority personas suppress semantic diversity**; junior-dominated/independent interactions explore broader. Larger groups + denser communication accelerate **premature convergence**. Diversity collapse comes from *interaction structure*, not model weakness. | Systematic empirical study, scientific-proposal testbed, expert-validated metrics | HIGH | Empirical Diversity in MAS Ideation, [openreview YL4alzSQIl](https://openreview.net/forum?id=YL4alzSQIl) | VERIFIED |
| 6 | Closed-loop multi-LLM systems exhibit **robust semantic collapse** over 200–1000 rounds; **12 intervention strategies** (decoding, prompt design, agent composition, activation engineering, RL) **all fail** to restore diversity. Consistent with intrinsic properties of autoregressive generation. | Cross-family simulations, mechanistic analysis | HIGH | Multi-LLM Semantic Collapse, [arxiv 2605.17193](https://arxiv.org/abs/2605.17193v1) | VERIFIED (disconfirmation) |
| 7 | Separating **unconstrained divergent generation from convergent constraint selection** (ReDNA) beats prior methods; under "immediate convergence pressure" frontier LLMs fall into **action fixation**. | MUTATE interactive benchmark, frontier LLMs | HIGH | Beyond One Path / ReDNA, [arxiv 2605.28465](https://arxiv.org/html/2605.28465v1) | VERIFIED (confirms mode discipline) |
| 8 | Creativity capability is **jagged**: gains in general creativity don't transfer uniformly to scientific ideation; the same model bursts on some prompts/domains and stalls on others. | SciAidanBench, 19 base models / 30 variants / 8 providers | HIGH | LLM Jaggedness, [arxiv 2605.10574](https://arxiv.org/html/2605.10574v2) | VERIFIED |
| 9 | **No existing creativity test reliably predicts scientific-ideation ability**; high performance on one creativity dimension (quality/novelty/diversity) rarely generalizes to others. | Large-scale test-validity study; CreativityPrism (17 models) | HIGH | Assessing LLM Creativity [arxiv 2605.13450](https://arxiv.org/pdf/2605.13450); CreativityPrism [openreview 3pfsQcEtNC](https://openreview.net/forum?id=3pfsQcEtNC) | VERIFIED (caveat) |
| 10 | Evolutionary "explore–expand–evolve" over a scientific-concept network with a reviewer-aligned critic reaches publication-quality ideas (~81.5% above top-AI-conf acceptance scores). | Deep-Ideation; also EvoSci (2605.24018), Evolving Idea Graphs (2605.04922) | MED | [openreview fS7GMmYu3d](https://openreview.net/forum?id=fS7GMmYu3d) | VERIFIED (convergent, not divergent) |

## Key Findings — mapped to the skill

### Two genuinely new prompt-level axes (orthogonal to denial/domain/constraint)

**A. Verbalized / distribution sampling [claims 1–2].** All three current axes perturb the *content space* (ban paradigms, swap domains, flip constraints). Verbalized Sampling perturbs the *output distribution* directly via prompt — "give me N approaches **and their probabilities**" — which decompresses the low-probability tail that alignment squashes. It is training-free, composes with every existing axis, and its benefit *grows with model capability* (directly relevant to running this on Opus). This is the single cleanest, best-evidenced addition. Candidate new axis `--axes distribution`, or fold the "emit probabilities" framing into the Step 2 initial-generation prompt and every denial/domain prompt.

**B. Semantic-direction stratification [claim 3].** A *single upfront planning call* that lays out broad semantic directions, then generates within each, beat seed-anchored regeneration on the diversity–quality–compute frontier. This is a structured, *a-priori* version of what denial does reactively (denial escapes the basin after you've seen it; stratification partitions the space before you enter it). Could restructure Step 2 ("Initial Generation") rather than add an axis — replace "cast wide" with "plan K semantic directions, then fill each."

### Refinements to the multi-model dispatch model [claims 4–6] — the strongest practical correction

The skill already says model diversity isn't the mechanism. The new evidence sharpens this into **actionable dispatch defaults**:
- **Prefer Multi-Output single-agent over parallel multi-agent** for the diversity pass [claim 4]. Parallel independent agents *converge* (overlapping ideas); a serial agent conditioning on its own history avoids redundancy. The current `llmx-dispatch` parallel-fan-out is optimized for volume but is *diversity-negative* relative to one agent producing many self-aware outputs.
- **Keep dispatch groups small; avoid expert/authority personas in generation** [claim 5]. "Senior scientist" framing suppresses diversity; independent/junior framing broadens it. Larger groups → premature convergence.
- **Closed-loop iterative dispatch has a hard ceiling** [claim 6]: 12 interventions failed to stop semantic collapse over many rounds. Reinforces the existing late-stage / mature-frontier cutoff ("one strong survivor is enough") — *do not* add more dispatch rounds expecting more diversity.

### Confirmations of current architecture [claim 7]
ReDNA's generate/select separation independently re-derives the skill's **mode discipline** (and "action fixation under convergence pressure" is the same failure as the Codex 8/8 `rg`/`sed` collapse the gate was built for). No change needed — but it's a stronger, more recent citation than HAIExplore v2 for the same point.

### Caveats for the coverage/evaluation artifacts [claims 8–9]
- **Jaggedness** means *which* forced domain unlocks creativity is model- and prompt-specific — mild support for keeping domain-forcing breadth (multi-domain hedges the jagged profile), not for trimming it.
- **No creativity test predicts scientific ideation, and dimensions don't transfer.** The `matrix.json`/`coverage.json` artifacts measure *coverage/divergence*, which is **not** a proxy for idea *quality* or downstream ideation value. Worth a one-line caveat in the synthesis template so coverage counts aren't read as a quality signal.

### Parked: evolutionary ideation [claim 10]
Deep-Ideation / EvoSci / Evolving Idea Graphs (explore–expand–evolve + critic over a concept graph) are powerful but **convergent** — they belong on the `/model-review` / bridge-to-action side, not in the divergent skill. Note as a future cross-skill handoff, don't import into `/brainstorm`.

## What's Uncertain / Disconfirmation
- Verbalized Sampling's 1.6–2.1× is on creative writing / dialogue / QA, **not** specifically on architecture/infra ideation (this skill's main use). Transfer is plausible (mechanism is distributional, domain-agnostic) but **`[INFERENCE]`**, not measured here.
- Semantic-direction stratification was tested on "creative task families," not software-design ideation — same transfer caveat.
- Disconfirmation searched and found: multi-agent ≠ diversity (claims 4,6) is the *strongest* contrary evidence to any "dispatch more models" instinct — and it cuts *for* the skill's existing stance, not against it. No source found claiming denial/domain/constraint perturbation is ineffective; NEOGAUGE's denial result is not contradicted by anything in this window.

## Bottom line
Three concrete, well-evidenced changes are available — none speculative:
1. **Add distribution/verbalized sampling** (new axis or baked into every generation prompt). Best evidence, training-free, scales with Opus.
2. **Add semantic-direction stratification** to Step 2 (plan directions → fill), replacing undirected "cast wide."
3. **Flip the dispatch default**: Multi-Output single-agent + small groups + no authority personas; stop treating parallel fan-out as a diversity mechanism (it's volume only, and mildly diversity-negative).

Plus two doc-only updates: swap/augment the mode-discipline citation with ReDNA (2605.28465), and add a coverage≠quality caveat to the synthesis template (claims 8–9).

## Search Log
- Exa `research paper`, startPublished 2026-03-01, 4 axes (techniques / multi-agent / adversarial-critique / benchmarks), 3 queries each → ~40 results, ~14 distinct relevant papers.
- Exa, startPublished 2026-02-01: targeted "verbalized sampling / distribution prompting / typicality bias" → Verbalized Sampling (ICML 2026) confirmed.
- All primary claims read from abstracts/full-text returned inline by Exa; arXiv IDs 2603–2605 = Mar–May 2026.
- Not fetched to full PDF: numeric effect sizes beyond those quoted in abstracts (1.6–2.1×, 81.5%) are as-reported by authors, not independently recomputed.
