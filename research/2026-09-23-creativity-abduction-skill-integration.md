---
title: "Creativity and abduction research (Jun–Sep 2026 + cognitive science) → /brainstorm and /analyze"
date: 2026-09-23
status: complete
tags: [brainstorm, analyze, creativity, abduction, hypothesis-generation, skills]
---

**Verdict:** Three research lanes (recent LLM creativity, LLM abduction and hypothesis generation, human cognitive science) produced edits to both skills. For /analyze, the finding that changes the procedure is that recall of the true explanation is fixed when hypotheses are generated; later ranking, debate and tournaments reorder the set but rarely add the missing cause. The hypotheses and causal lenses now generate across fixed slots with an `H_other` residual, build an observation inventory before any hypothesis, prune hypotheses that fail an observation, and reopen generation (or switch to probing) when the leader leaves an observation unexplained. For /brainstorm, nothing found refutes the existing mechanisms (verbalized sampling, denial, stratification, fan-out-is-volume). Five cheaper edits landed: one originality instruction, a standing ban on bridge/unify framings, problem reformulation before generation, one mid-distance domain in domain forcing, and gate-then-spread selection in place of novelty × feasibility ranking. The "without degrading" check is in §4. [SOURCE: lane memos and papers below]

Lane memos (full claims tables, search logs): `research/scratch/2026-09-23-creativity-abduction/{A-llm-creativity,B-llm-abduction,C-cogsci}.md`. Prior memos this extends: `brainstorm-creativity-axes-2026-05.md`, `divergent-convergent-thinking-llms.md`, `ai-reasoning-causal-abductive-deductive.md`.

## 1. /analyze: what the evidence says and what changed

| Finding | Source | Status | Edit |
|---|---|---|---|
| A cross-model review plus tournament raised hypothesis Match 2.4× but success@5 only 55.1% → 57.1%: selection adds precision, not coverage | Reconstruction, arXiv 2608.16645 (7 frontier models, n=643) | VERIFIED (parent read full text) | Slot-structured generation with `H_other` before ranking |
| Only 20% of 70B-class abductive hypotheses were consistent with the observations they were built from | GEAR, arXiv 2509.24096 | VERIFIED (lane); pre-frontier rate, scale-independent check | Prune any hypothesis that fails an inventoried observation |
| Narrative framing anchors diagnosis in all 7 models; CoT and debiasing instructions reduce it "only partially"; facts-first extraction cuts it to near zero | NarrativeShield, arXiv 2607.27384 | VERIFIED (parent read full text) | Observation inventory as bare facts; the explanation that arrived with the question is one hypothesis, not the frame |
| Information requested predicted diagnostic accuracy (R=0.69) but fell from 57% to 26% in the final round across 32 frontier models | arXiv 2607.10275 | VERIFIED (parent read full text) | Before committing, fetch the cheapest evidence that separates the leader from the runner-up |
| Guided reflection (supporting, contradicting, expected-but-absent findings per hypothesis) is the most consistent debiasing tool; gain is small (g=0.20) and appears on complex cases; "slow down" alone is inert (45.0% vs 44.5%) | Mamede 2008/2010; Lambe 2016; Staal 2022; Norman 2014 | ABSTRACT-ONLY | Step 4 columns in the hypotheses lens |
| Subjects who could not guess the rule found it only by generalizing from experiments | Klahr & Dunbar 1988 | ABSTRACT-ONLY | When generation yields only variants, run the cheapest splitting probe and induce |
| Six of seven documented responses to anomalous data discount it | Chinn & Brewer 1993 | ABSTRACT-ONLY | Dismissing a mismatch names the discounting move and its test (`reasoning-principles.md` §2) |
| Simplicity and scope inflate judged likelihood when base rates are missing | Lombrozo 2007 | SECONDARY | Loveliness-is-not-likeliness guard (`ibe-dominance-format.md`) |
| An alternative debiases only if it is plausible | Hirt & Markman 1995 | ABSTRACT-ONLY | Named alternatives must merit >=10% credence |

Rejected for /analyze: "be diverse / avoid anchoring" prose (claims above show instruction-level fixes are partial); temperature changes; tournaments or debate as default (precision, not recall, at N× cost); POPPER-style sequential testing (validation machinery; its prompt-level content is already in ACH); treating verbalized probabilities over explanation sets as calibrated (no study measures this).

## 2. /brainstorm: what the evidence says and what changed

| Finding | Source | Status | Edit |
|---|---|---|---|
| "Be creative" vs "be effective" moved creativity dz=+1.40 across 18 frontier models, no quality loss; enabling reasoning moved it +0.34 | AGC-Bench, arXiv 2607.01152 | VERIFIED (parent read full text) | One originality line in Step 2 and in the generation and denial payloads |
| LLM research ideas use bridge/connection motivations 47.1–64.2% (humans 12.1%) and unification methods 22.5–38.7% (humans 5.1%), across 9 LLMs | arXiv 2607.01233 | VERIFIED (parent read full text) | Denial round 1 always bans bridge/unify; a blend that outputs "unify A and B" is a dry cell |
| LLM judges see a "novelty mirage" in generated research questions, stronger under pairwise judging; experts disagree; judges miss "narrow or source-bound" unless asked | arXiv 2606.12071 | VERIFIED (parent read full text) | Synthesis: gate on feasibility, then pick the largest mutually distinct set; judge novelty only against a reference; ask about narrowness directly |
| A pipeline optimizing a gated diverse-set objective beat the best baseline 2× (NB≥6) and 3.89× (NB≥7); the one-shot 10-idea list was second-most diverse with zero gated yield | IDEAgent, arXiv 2607.22375 | VERIFIED (parent read full text) | Same selection edit; Multi-Output qualified: for gated survivors, generate in short batches against signatures of kept ideas |
| Far analogies raise novelty and quality variance; too far hurts; field data link closer sources to better-rated ideas | Chan 2011; Fu 2013; Chan, Dow & Schunn 2015 | ABSTRACT-ONLY | One mid-distance domain (shared function or relational structure) plus far ones; replaces "the discomfort is the mechanism" |
| Problem construction predicts solution originality, most when cues conflict | Reiter-Palmon et al. 1997, 2018; Redmond 1993 | ABSTRACT-ONLY / SECONDARY | Step 1: three reformulations, generate against at least two |
| Idea exchange narrows the domains explored; examples cause pigeonholing even when correct | Kohn & Smith 2010; arXiv 2606.24267 | ABSTRACT-ONLY | No idea text between parallel workers before extraction; payloads carry paradigm labels, not example ideas |

No study found in the window refutes verbalized sampling, denial/NEOGAUGE, stratification or single-agent > matched multi-agent on frontier models (lane A searched for failures to replicate). No study directly shows that longer instructions hurt creative output; at o3-high, discussion structure barely mattered (range 0.023 vs 0.096 for GPT-4.1, arXiv 2605.17885), which argues against adding procedure.

Rejected or parked for /brainstorm: McCaffrey's generic-parts technique (67% more insight problems solved, one study, no replication found; parked as an opt-in axis candidate until a local run shows yield); serial-order "don't truncate" rule (robust but at most 3.5% of variance, Barbot 2026); incubation (no analogue between stateless calls); reasoning-effort or temperature as a diversity lever; importing IDEAgent/NOVA/parallel-tempering loops; random ordinary personas for fan-out (GPT-4o only).

## 3. Hindsight grading

| Find | Grade | Evidence |
|---|---|---|
| Consistency check of each hypothesis against all observations | HAD-PARTS | Proposed in `ai-reasoning-causal-abductive-deductive.md` §2 (March 2026), never shipped to the lens; IBE "explanatory scope" applied it only at scoring time |
| Coverage ≠ quality, judges unreliable on novelty | HAD-PARTS | `brainstorm-creativity-axes-2026-05.md` claims 8–9 added a caveat to the template but kept novelty × feasibility ranking |
| `H_other`, facts-first inventory, reopen/probe switch, reflection columns | NOVEL | No match in research/, decisions/ or the skill |
| Bridge/unify attractor, originality instruction, mid-distance domain, reformulation | NOVEL | No match |

The HAD-PARTS pattern is a proposal written into a memo but never carried into the skill it named. No architecture fix is filed for it here; the eval below is the check that this round's edits carry through.

## 4. "Without degrading": measurements

**/brainstorm generation payload, old vs new (originality line added).** 3 design topics × 2 reps × 15 ideas per arm, claude-opus-5-5 at low effort (the dispatch default), `--safe-mode`, ideas embedded with `emb` (gte-modernbert). Diversity is the one signal with validated instruments (embedding metrics agreed with expert diversity judgments ≥80%, Vendi 87%, arXiv 2604.18005); LLM novelty judges were rejected by the same literature. Script: `research/scratch/2026-09-23-creativity-abduction/bs_diversity.py`.

| arm | mean pairwise cosine distance | Vendi | bridge/unify framing rate | out_tok |
|---|---|---|---|---|
| old payload | 0.361 | 4.48 | 0.00 | 2,797 |
| new payload | 0.354 | 4.37 | 0.03 | 2,970 |

Rep-to-rep spread within an arm is ±0.03 on distance, so the arms tie: no diversity loss, and no measurable gain on this metric. The +1.40 dz in AGC-Bench is judged originality, which this proxy does not measure; the line stays on the strength of that evidence. Reformulation, mid-distance domains, the bridge ban in denial rounds and gate-then-spread selection are unmeasured locally (no verifier short of the operator's judgment); each replaces or qualifies existing text rather than adding procedure. `brainstorm/SKILL.md` grew 17.9K → 19.9K chars.

**/analyze hypothesis recall** (`~/Projects/evals/analyze_hypothesis_recall`, preregistered at evals@490a587). 7 vignettes of real agent-infra misdiagnoses (the first hypothesis at the time was wrong: lock contention vs an unindexed self-referential FK; a pruned interpreter vs launchd log paths through a symlink; a 3.8 GB DB vs MCP import time; upload failures vs a stale seal; slow stages vs budget-killed zombies; a hash collision vs seq renumbering; nested `uv run` vs a hardcoded `--jobs=4`), each carrying the wrong explanation the investigator held. Three arms differ only in the skill text appended to the system prompt; claude-opus-5-5 medium, `--safe-mode`, 3 reps.

| arm | recall | top1 | p_true (keyword) | p_true (judge) | median out_tok |
|---|---|---|---|---|---|
| none | 1.000 | 0.857 | 0.705 | 0.679 | 1,947 |
| current (skills@7d44b37) | 1.000 | 0.857 | 0.672 | 0.636 | 2,684 |
| edited | 1.000 | 0.857 | 0.628 | 0.566 | 2,770 |

The edited arm passes the preregistered non-inferiority rule (Δp_true −0.044 against a −0.05 tolerance, recall tied, largest item drop −0.16) and ships. The eval is at ceiling on the construct the edits target: with the cue in the vignette, Opus 5.5 recovers the cause on every trial with or without any skill text, so recall cannot move. What the eval shows is the cost side: the mandated slots and `H_other` take 0.04 of the mass the model would otherwise put on the leader, on top of the 0.03 and +38% tokens the existing skill text already cost against no text. The benefit case (the true cause absent from the set, or closure before the discriminating data is requested, arXiv 2607.10275) needs vignettes whose cue is absent or must be gathered; those are the follow-up. Details, per-item table and limitations: `evals/analyze_hypothesis_recall/EXPERIMENT.md`.

**Net.** Both skills changed on evidence read in the primary where it decided an edit; the only local measurement that could move was the hedging cost in /analyze, and it stayed inside the tolerance set beforehand.
