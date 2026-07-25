---
title: Opus 5 on ARC-AGI — benchmark-targeting vs generalization (system-card read)
date: 2026-07-25
tags: [models, opus-5, arc-agi, benchmarks, eval-validity]
status: active
---

# Is Opus 5 RL'ed for ARC-AGI, or is it generalization?

**Source:** Claude Opus 5 System Card (194pp, Anthropic, 2026-07-24) — ingested to corpus
`sha_897768f0f6f1724f` (`~/Projects/corpus/sha_897768f0f6f1724f/`, pymupdf4llm parse; the
marker-modal path is unavailable — `modal` extra not installed in the research-mcp env).
§8.14 is the ARC section; §8.1 Table 8.1.A is the summary. Cross-checked against
[arcprize.org/results/anthropic-claude-opus-5](https://arcprize.org/results/anthropic-claude-opus-5)
and ARC Prize's own commentary.

## Verdict

**Split the benchmark family — the answer is different for each.**

| Bench | Read |
|---|---|
| ARC-AGI-1 (97.5) | **Saturated, ~zero information.** Public training set exists and is meant to be trained on. GPT-5.6 Sol ties at 97.5. |
| ARC-AGI-2 (90.4) | **Benchmark-targeted, discount heavily.** GPT-5.6 Sol *beats* it at 92.5. Two labs from different pipelines both at ~90 = the benchmark is being optimized against industry-wide, not a Claude-specific capability claim. |
| ARC-AGI-3 (30.2) | **The only real signal — and it reads as transfer, not ARC-specific RL.** 4× the best other model (GPT-5.6 Sol 7.8 @ max), 20× its own predecessor (Opus 4.8 1.5 @ high). |

Bottom line: **no ARC-directed RL is needed to explain the ARC-AGI-3 result** — general
agentic + visual long-horizon RL explains it, and four other benchmark families moved in
lockstep. But the generalization claim rests on *one* benchmark, vendor-arranged, unreplicated
by any independent party.

## Numbers (Table 8.1.A + §8.14, ARC Prize semi-private, verified by the Foundation)

```
                  Opus 5   Opus 4.8   GPT-5.6 Sol
ARC-AGI-1          97.5      92.5       97.5 (xhigh)
ARC-AGI-2          90.4      72.1       92.5
ARC-AGI-3          30.2      1.5         7.8 (max)
                  (high)    (high)
```
Opus 5 config: adaptive thinking @ max effort, 5 trials (ARC-AGI-3 at **high** — max "was not
available at the time of release"). ARC-AGI-2 at high effort = 88.3 (ARC Prize page).

## Five reasons ARC-AGI-3 reads as generalization

1. **Effort asymmetry.** 30.2% was set at **high**, with max unmeasured at release. A model
   tuned for a headline ARC number gets tuned at the top of its own effort ladder.
2. **The gain profile is agentic, not puzzle-shaped.** Everything that moved most in this
   release sits on the same axes ARC-AGI-3 lives on — interactive, visual, long-horizon:
   SWE-bench Multimodal 38.4→59.4 (+21pp), OSWorld 2.0 55.7→70.6 (+15pp), FrontierBench v0.1
   21.1→43.3 (2×), AutomationBench 17.0→26.0. Static-reasoning rows moved far less
   (HLE no-tools 49.8→56.3). ARC-AGI-3 is the intersection of the axes that all moved.
3. **Anthropic's own stated mechanism points away from puzzle priors.** §8.12: *"agentic
   tool-use is generally a more cost-effective method of scaling test-time compute than
   adaptive thinking by itself."* That is a claim about the lever they pulled.
4. **The described solving mechanism is transferable and legible.** ARC Prize's LLM-judge read
   of the `ar25` (Axis Reflect) transcript, quoted in §8.14.2: the model turned the visual
   puzzle into **explicit algebra** — derived a reflection equation by level 2, generalized to
   two-dimensional reflections by level 8, partitioned 60 targets into mirrored quadrants and
   computed every destination *before* executing; 100 score, 8 levels, 294 actions. It also
   showed hypothesis churn (elaborate unverified theories, then abrupt self-correction) —
   failed exploration updating the world model. That's build-a-symbolic-model-then-act, not a
   memorized grid prior. ARC Prize's public summary agrees: the gain comes from *"stronger
   logical reasoning, which enables more autonomous exploration, planning, and execution across
   unfamiliar environments."*
5. **A negative control inside the card.** §8.14.1 notes Opus **4.7** reported **75.83%** on
   ARC-AGI-2 at max — above Opus **4.8**'s 72.1. A lab directly optimizing ARC as a headline
   metric does not ship a regression on it between releases.

## Three reasons to keep the discount on ARC-AGI-1/2

1. **ARC-AGI-1/2 ship public training sets designed to be trained on** (Core Knowledge priors);
   only the private/semi-private eval sets are withheld. Every frontier lab uses them. "Trained
   on ARC" is the sanctioned baseline, not an accusation.
2. **The card gives no ARC decontamination statement.** The only blocklists in the card (§9.1,
   §9.2) are *URL blocklists for search tools* on HLE and BrowseComp — retrieval hygiene, not
   training-set exclusion. Absence of a claim, not evidence of contamination.
3. **Two labs at ~90 on ARC-AGI-2** is the classic saturation signature. Its remaining
   discriminative power for our routing decisions is approximately nil.

## What would change the verdict

- ARC-AGI-3 at **max** effort landing far below the high-effort 30.2 (would suggest tuning at a
  specific operating point rather than a capability).
- An independent (non-vendor-arranged) run reproducing the 4× gap.
- A same-family model with the agentic gains but *without* the ARC-AGI-3 gain — would break the
  co-movement argument.

## Caveats on the evidence itself

- Mechanism evidence is **n=1 game**, judged by an LLM reading one transcript.
- **RHAE** (Relative Human Action Efficiency) scores efficiency against human action baselines —
  a metric that mechanically rewards a model that plans before acting. The metric and the
  claimed capability are close to co-defined.
- The "five previously-unbeaten environments" claim is on the **public demo** set; the 30.2 is
  semi-private. Different sets.

## The finding that actually matters for our harness

Put §8.14.2 next to §2.2 (the 24h/$10k autonomous protein-design campaign, in
[2026-07-24-claude-opus-5-release.md](2026-07-24-claude-opus-5-release.md)): the *same model*
that explores an unknown interactive environment 4× better than anything else **shipped nothing
and went silent for 8 hours** on an open-ended design goal, stuck in self-verification loops.

The discriminator is the **verifier**. ARC-AGI-3 hands the model a dense environmental score on
every action; the protein campaign had no in-loop verifier at all. Opus 5's exploration gain is
real *and* it is verifier-conditioned — which is our own constitution's Regime 1 vs Regime 2
line, showing up as a measured capability split inside one release.

Operational consequence: for long autonomous runs, **the ROI on giving Opus 5 an in-loop
verifier is now higher than the ROI on giving it more effort.** A `/goal` run with a cheap
deterministic check per step should outperform the same run at higher effort without one.

## Sources

- Claude Opus 5 System Card, §8.1 (Table 8.1.A), §8.12, §8.14.1, §8.14.2, §9.1–9.2 — corpus `sha_897768f0f6f1724f`
- https://arcprize.org/results/anthropic-claude-opus-5
- https://arcprize.org/blog/arc-agi-2-technical-report (training/eval split policy)
- https://arxiv.org/html/2603.24621v1 (ARC-AGI-3 design)
