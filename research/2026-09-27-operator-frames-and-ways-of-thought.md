---
title: "Operator frames and ways of thought: the lenses behind his steering"
date: 2026-09-27
status: complete
tags: [steering, taste, operator-model, frames, research-skills, luna, autonomy]
---

**Verdict:** A second mining pass read 5,547 of the operator's prompts across ten areas. It covered the six research projects from the [steering-moves pass](2026-09-26-operator-steering-moves.md), plus agent infrastructure, biomedical pipelines, publishing and design, and private decisions. It looked for *how he thinks*: lenses, mental models, analogies, values, aesthetics, ambition, stances, decision rules and meta-thinking. GPT-6 Luna extracted 567 frames; 545 (96%) trace to a verified quote of his. They reduce to 31 signature frames in eight families, plus question forms, home fields, ways of thought, session arcs and tensions. The result lives at `~/Projects/skills/references/operator-frames.md`, linked as a menu from /research, follow-up-moves and the research-ops generate step.

Thirteen of the signatures name the lens behind a move the steering pass already catalogued. The other eighteen are new:
- how he reasons about growth, bottlenecks and who captures value;
- how he sizes bets and survives the path;
- his theory of learning (human sample efficiency, the compact kernel, interaction before language);
- his craft rules ("strictly better or no-op", one clean authority);
- his taste in design and writing;
- how he divides work with agents.

The first automated clustering failed in an instructive way: it converged on generic good-researcher virtues. The distinctive material survived only through a distinctiveness-first second pass plus reading the frames directly. The pass is not evaluated for anticipation; the blind preference rating from the steering eval (evals 6b5411d) is the pending test of whether mined operator material is worth wiring harder. [SOURCE: `.scratch/operator-frames-2026-09-27/` (gitignored): `agg/`, `merge/`, `spec.toml`, `evidence.md`]

## 1. What the frames show

Each signature has a *When*, a *Do* and a *Misfire* in the reference. Evidence is counted over his verified messages behind the member frames. Every signature has at least 6 sessions; 23 of 31 span two or more areas.

| Family | Signatures | Broadest evidence |
|---|---|---|
| Growth, bottlenecks and who gets paid | trajectories and derivatives; binding input and who captures it; compounding over people and time; marginal is not average | binding input: 42 messages, 22 sessions, 3 areas |
| Bets, budgets and reversibility | payoff shape and conviction sizing; survive the path; explicit prices on time, money and quota; reversible first, incumbent stays until beaten; grade by the real endpoint | reversible first: 6 areas |
| Intelligence and learning | generality over benchmark wins; humans as the yardstick; make priors fight the evidence; hunt the kernel; learning from interaction; early signs of life | generality: 72 messages, 33 sessions (one area) |
| Evidence, experts and contested questions | audit claims not reputations; contested hypotheses as empirical questions; beliefs in a dated ledger; what the number measures | ledger: 5 areas |
| Systems craft | one clean authority; strictly better or no-op; fix the writer not the mess; keep what cannot be rebuilt | strictly better or no-op: 7 areas |
| Taste in design and writing | visuals must carry meaning; match the feel of the reference; keep the character | visuals: 62 messages, 6 areas |
| Working with agents | his input should become redundant; he brings blind spots, creativity and taste while agents own the rest; upgrade your own cockpit | taste split: 6 areas |
| Ambition | step changes with a stopping rule; borrow mechanisms from far fields | step changes: 54 messages, 26 sessions |

Three patterns stand out beyond the list.

- **He thinks in questions.** 45% of the frames arrive as a question, including 26 of 38 borrowed-field lenses. A prompt like "is X an inspiration here?" is a hypothesis for the agent to evaluate and answer with a verdict. It is neither an order nor rhetoric.
- **His ambition comes paired with a stop rule.** Tenfold targets, a widened budget and "blue sky" runs sit next to "or say no-op" and "no is a valid answer". His bar for change, strictly better or no-op, is framed with the medical idea of iatrogenic harm and spans 7 of 10 areas.
- **Most of his lenses are economic or decision-theoretic, even outside finance.** He looks for incidence and rent capture, marginal versus average cost, convexity, survival and option value. He applies the same models to agent infrastructure (exchange rates between time, money and quota) and to research strategy (payoff shape of a research bet).

The single-area signatures (for example generality, payoff shape, marginal cost) are project stances, not habits of mind. The reference marks each one's areas so an agent can tell the difference.

## 2. Method

1. **Export.** `scripts/operator_prompts_export.py` exported 1,631 prompts from the non-research projects, with live transcripts only (see limitations). The six research projects reuse the 3,916-prompt export from the steering pass. Records and packets follow the steering pass's format (380K-character chronological packets, each record showing the agent's tail, his message and the agent's reply). The result was 25 packets.
2. **Extract.** Luna (`gpt-6-luna`, effort high, via the codex-cli subscription) ran once per packet. The prompt asked for frames in ten kinds with a verbatim quote, a domain-free claim, what the frame reveals, a transfer case and a distinctiveness label. It also asked for per-packet ways of thought (at most 12) and session arcs (at most 6), and it listed the steering-pass moves as do-not-repeat. All 25 calls succeeded on the first attempt, 91 to 276 seconds each.
3. **Verify.** Each quote was checked against his raw prompt, following the steering pass's R numbering. Of 567 frames, 91.4% match exactly somewhere in the group, 95.4% match exactly or near-verbatim, and 96.1% are grounded once elided fragments are allowed. Of the 22 that fail, 7 quote agent or pasted text Luna attributed to him, and 15 are not found as written. Only 77% cite the right record; most misses point to one of the frame's `also` records or are off by one, not a numbering offset.
4. **Cluster (failed).** One Luna call clustered the 545 grounded frames into 49 clusters. Two problems:
   - The clusters drifted to generic research virtues ("evidence must earn trust", "keep claims bounded"), many restating steering-pass checks.
   - Membership broke the partition rule: 497 frames were listed in more than one cluster and 4 in none.
   Luna's distinctiveness labels also proved uninformative: 509 of 567 frames are "characteristic" and 4 are "generic".
5. **Signature pass.** A second Luna call received the generic clusters as a list to compress. It was asked for what distinguishes him from a generic careful researcher: signatures with members, question forms and home fields. It returned 30 signatures in 8 families.
6. **Parent curation.** I read about 420 of the 545 frames with quotes: all idiosyncratic, lens, analogy, ambition, question-form, stance, meta and aesthetic frames, plus the top value, decision-rule and mental-model frames. I rebuilt the signature set in `spec.toml`. Luna's 30 signatures reduce to 20 after merging seven overlapping pairs and dropping two generic ones ("compare like with like" and "separate merit from allocation"). I added 11 it missed. The additions are compounding and metabolism, marginal versus average cost, payoff shape and conviction sizing, humans as the yardstick, adversarial priors, the kernel hunt, auditing experts by track record, contested hypotheses as empirical questions, strictly better or no-op, the division of work with agents, and upgrading the agent's own cockpit. `build_reference.py` resolves every member by exact frame name and fails loudly on an ungrounded or unknown name; that caught one ungrounded member. It computes evidence and renders the reference plus a private evidence appendix.
7. **Fidelity check.** I read three quotes per signature. I dropped one frame whose quotes did not show its claim ("track the derivatives": the messages were about time-varying assumptions). I replaced Luna's pooled members with explicit names where the pool pulled in off-topic frames, and moved one member to a better-fitting signature.
8. **Privacy gate.** `leak_check_frames.py` fails on blocked project and person tokens, on private proper nouns from his prompts, and on any 6-word run shared with any of the 5,547 prompts. One of his phrasings was reworded, and the gate then passed with zero findings. The reference paraphrases throughout.

## 3. Status and wiring

- `~/Projects/skills/references/operator-frames.md` sits in the shared references because it serves more than one skill.
- It is linked from research/SKILL.md (a route line next to follow-up moves), from the follow-up-moves header (see also), and from the research-ops generate step (step 3, next to the follow-up-moves generators).
- The brainstorm skill is not wired. The reference suggests home fields as a mid-distance domain on his projects, but brainstorm's far-domain design argues against making that a default.
- The status is **menu**, the same as follow-up moves. The steering-pass eval showed that a mined catalog changes agents' proposals without raising anticipation (11% vs 9%). A frames arm on that harness would probably be similarly underpowered, so it was not run.
- The phase-2 blind preference rating (evals `steering_anticipation/PREREGISTRATION_preference.md`, page published 2026-09-27) asks the operator directly whether catalog-informed proposals are better. Its outcome decides the follow-up-moves wiring. It informs, but does not decide, whether frames should also move from menu to a report-time step.

## 4. Cost

29 Luna calls on the codex-cli subscription ($0 cash), from rollout usage (`luna_tokens_frames.py`):

| Phase | Calls | Input tok | Cached | Output tok | Reasoning tok |
|---|---|---|---|---|---|
| Extract | 25 | 2,581,722 | 204,544 | 169,403 | 72,434 |
| Cluster (failed) | 1 | 63,318 | 6,912 | 17,623 | 1,907 |
| Signature | 1 | 64,779 | 6,912 | 6,565 | 366 |
| Ways merge | 1 | 25,363 | 6,912 | 6,560 | 4,952 |
| Arcs merge | 1 | 24,630 | 6,912 | 5,329 | 4,210 |
| **Total** | 29 | 2,759,812 | 232,192 | 205,480 | 83,869 |

Wall time was about 13 minutes for extraction (six parallel calls) and about 10 minutes for the merges. The parent's reading and curation cost more attention than the model calls did.

## 5. Limitations

- **History window.** Claude transcripts cover about 30 days and Codex covers June to September 2026. The older archive on the external SSD is an encrypted volume that was locked during this run, so older prompts are missing.
- **Skew toward heavy projects.** Agent benchmarks produced 180 of the 567 frames and investing 120, so those projects' stances are over-represented among single-area signatures.
- **Said, not decided.** The frames are what he wrote to agents. They are not observed decisions, and prompts under-represent what he does without asking.
- **One extraction model.** No second model re-extracted the frames. Quote verification guards against fabrication, not against a skewed selection. The parent's reading of about 420 frames is the only check on selection.
- **No held-out validation.** Nothing here shows that loading the frames makes agents act more like him. The phase-2 rating is the nearest test, and it covers the moves catalog, not this file.

## 6. Artifacts and reproduction

- Scratch (gitignored): `.scratch/operator-frames-2026-09-27/`, which holds:
  - `raw/` and `packets/`, the export and the 7 non-research packets;
  - `luna_frames_prompt.md`, `run_frames.sh` and `luna/`, the extraction;
  - `verify_frames.py` and `agg/`, the verification and aggregation;
  - `merge/` (prompts, runner scripts and outputs), the clustering, ways, arcs and signature passes;
  - `spec.toml`, `spec_extra.toml` and `build_reference.py`, the curation and rendering;
  - `evidence.md`, the private quote appendix;
  - `leak_check_frames.py`, the privacy gate;
  - `luna_tokens_frames.py`, the cost tally.
- Rebuild: `uv run python3 verify_frames.py && uv run python3 build_reference.py && uv run python3 leak_check_frames.py operator-frames.md`, then copy `operator-frames.md` to `~/Projects/skills/references/`.
