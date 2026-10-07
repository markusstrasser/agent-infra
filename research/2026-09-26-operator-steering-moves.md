---
title: "Operator steering moves: what he adds, what the skills already hold, and whether a catalog lets agents anticipate him"
date: 2026-09-26
status: complete
tags: [steering, taste, operator-model, research-skills, luna, eval, autonomy]
---

**Verdict:** Across 3,916 operator prompts in six research projects, GPT-6 Luna extracted 2,662 steering moves; 96% of their quotes were verified against the source. Merged and curated, they form a catalog of 18 angle generators, 29 checks, 10 moves for running the research, and four domain packs: `~/Projects/skills/research/references/follow-up-moves.md`.

The skills already hold most of the checks. Of 84 graded catalog units, 13 exist as levers and 61 in part; 10 are new. The operator's edge is mostly *when* he fires a check: the moment a result appears. The skills keep theirs in specialist skills someone must invoke and in a pre-publication gate, while the mid-work research path has one generic test step. His other edge is the frame moves (28% of his steering): reframes, scope shifts, "which field is this", "swing bigger". Agents make these only partly on their own.

A held-out test on 54 real checkpoints found that loading the catalog does not make the agent anticipate his next move: 11% with it, 9% without, 0% for a generic control. It changes which moves the agent proposes, not how often one of them is his. So the catalog is linked from /research and the research-ops generate step as a menu. It is not a mandatory pass. [SOURCE: evals `steering_anticipation` (prereg 31c67f6, results 02b6c0f); coverage grades `.scratch/operator-steering-2026-09-26/coverage_result.md`]

## 1. How the operator steers

About two in three of his prompts carry a steering move; the rest are logistics, relays and approvals. By family:

| Family | Share | What it looks like | Agent could have made it itself (Luna's self-fire rating) |
|---|---|---|---|
| Frame (reframe, scope shift, telos check, new direction, cross-domain transfer, lessons) | 28% | "What's the field actually?", "swing bigger", "check what the prize rewards" | yes 29% · partial 54% · no 17% |
| Validity (construct, premise, primary source, magnitude, decomposition, consistency) | 24% | same rules for the reference group, "did you look at the traces?", remove the contested component | yes 51% · partial 42% · no 7% |
| Process (running the agents and the loop) | 21% | "why is discovery my gate?", "7 hours is not a feedback loop" | yes 55% · partial 26% · no 19% |
| Test (falsification, rival explanation, adversarial, quantify, method import) | 13% | "how would you know?", what else must be true, run the multiverse | yes 35% · partial 57% · no 8% |
| Inputs (pasted data, lived observation) | 10% | a neighborhood observation, a portfolio fact, a pasted paper | yes 25% · partial 35% · no 40% |
| Output (presentation, cut) | 5% | plain explanation, one chart per question | yes 42% · partial 43% · no 14% |

The projects differ. Fiscal and psychometric work leans on validity (31% and 37%). The compression loop leans on process (42%): he steers the autonomous loop more than the science. Agent benchmark research and investment research lean on framing (29% each).

Across all moves, Luna rated 41% as ones the agent could have made on its own, 43% as partly and 16% as not. The "not" share concentrates in inputs, where the operator holds state the agent lacks.

The distinctive part is a set of angle generators that recur across projects and that agents rarely produce unprompted:

- ask what else must be true if the result holds;
- run the model's rules on the reference group;
- hunt the counterexample group;
- rank the opposition from weakest to strongest;
- ask which field the problem really belongs to;
- recast the plan through a named expert;
- sweep for blind spots on both sides;
- invert a load-bearing assumption;
- run the multiverse;
- remove the contested component;
- find the cleanest test or purest exposure;
- swing bigger;
- check what the objective rewards;
- ask whether failure is in generation or in selection.

Of the 90 moves Luna merged across projects, 73 recur in two or more projects. The catalog's twelve habits summarize the dispositions behind the moves: raw evidence before aggregates, small decisive tests, widening when a lane stalls, firsthand experience as validity data, symmetric rules, and the expectation that the agent discovers and experiments without asking.

## 2. What the skills already hold

A grading subagent checked each of the 84 catalog units against /research and its references, /analyze and its lenses, /doe, /brainstorm, /critique, research-ops, /decide, /figure, /eval, the global CLAUDE.md and the global rules, reading each in full. [SOURCE: `coverage_result.md`, file:line cites per unit]

| Grade | Units | Meaning |
|---|---|---|
| HAD-LEVER | 13 | The text prescribes the move for the same trigger; he still had to push it |
| HAD-PARTS | 61 | 10 lack only the right stage or firing point, 21 are prescribed for a narrower scope, 30 cover part of the action |
| NOVEL | 10 | No text prescribes it |

The pattern that matters: the levers sit in specialist texts (/eval, /doe, /analyze lenses, /figure, `--adversarial`) and in the pre-publication quant-bias gate. The research path that runs mid-work has one generic test-the-answer step (`research/references/topic-review.md:23`). So a check like "state the bound and the reversal condition" exists (quant-bias item 14, memo template), but fires when a memo is written, not when the number first appears in a report. That is where he fires it.

The ten novel units:

- recast through a named expert;
- ask for the operator's firsthand observation;
- test a fix on a second case;
- five investing moves: merit before portfolio fit, valuation on explicit scenarios, the real alternative use of capital, leverage against survival, leading demand indicators;
- scoring goal discovery separately from execution;
- developmental-stage control.

The grader also flagged four counter-levers, texts that push against one of his moves. On reading the lines, two are not real conflicts:

- `brainstorm/SKILL.md:172` bans expert personas during *generation* and moves expertise to the convergent stage, which is how he uses the named-expert lens.
- `research/SKILL.md:14` forbids *silently* turning a research question into an experiment, and proposing the test is compatible with it.

Two remain live tensions:

- `decide/SKILL.md:67` ("get a read from the user") against "don't gate discovery on the operator".
- `~/.claude/CLAUDE.md` plus `wakeup-cadence.md`, which push orthogonal work while results are pending, against his "don't open new fronts near a decisive result". He pushes both, so this is his call, not a text fix.

## 3. Does the catalog let an agent anticipate him?

Preregistered in evals `steering_anticipation` (31c67f6). Before any clustering, 60 checkpoints were frozen out of the catalog's inputs. Each had a high-impact move the agent could at least partly have made; six session-opening records had no preceding report and were dropped, leaving 54 in 38 sessions.

The SUT was claude-opus-5-5 at medium effort with `claude -p --safe-mode --tools ""`. It saw the project blurb, the previous request and its own report, then listed five next moves. Arms differed only in appended system text: none, an instruction to anticipate the owner's pushback, or that instruction plus the catalog. A constant generic reply served as the control. Two cross-family judges (GPT-6 Astra, Grok 4.7) decided whether a proposal made the operator's actual move and had to quote it verbatim.

| Arm | consensus hit@5 | GPT judge | Grok judge | median input tok | median output tok (incl. thinking) |
|---|---|---|---|---|---|
| none | 5/54 (9%) | 15% | 9% | 3,616 | 465 |
| instruction | 5/54 (9%) | 19% | 9% | 3,681 | 517 |
| catalog | 6/54 (11%) | 19% | 13% | 10,326 | 524 |
| generic control | 0/54 | 0% | 0% | — | — |

Catalog − none: +1.9 pp, cluster-bootstrap 95% CI −7.4 to +12.0 pp. Judge agreement: κ 0.67. All arms fall within 5 pp, which the locked rule reads as no effect: the catalog stays documentation, linked, not mandated.

The treatment took. The catalog arm named catalog moves 78 times across 54 items, mostly the generators, but its extra hits and misses fell on different items than the plain arm's (4 vs 3 discordant). His next move depends on state he holds (private data, lived observation, portfolio, what he already knows) and on which of many valid angles he picks. A bigger menu does not select his pick.

What the test cannot say is whether the catalog's extra moves are ones he would value. That needs him as the verifier. The cheap follow-up is a blinded preference rating: about 20 checkpoints, with the plain and catalog proposals shown side by side in random order.

## 4. What changed

- **Catalog** (skills b0b06df): `research/references/follow-up-moves.md`, linked from the /research route table ("choosing the next move in a research project, or stalled") and from the research-ops generate step (lane text and Dreamer prompt). Its header carries the eval result: a menu, not a predictor.
- **Placement** (the "merge into" question): one reference under /research, not a new skill, and not folded into /analyze or /doe.
  - The coverage grades show the gap is firing time, not missing text. A new skill would be one more thing that must be invoked, which is the failure the grades found.
  - /research is where research reports are produced, and the research-ops generate lane is where new angles are consumed.
  - The eval set the strength of the wiring.
- **Classifier fixes** (4aa25ee, cbea570): Claude Code stamps local-command stdout echoes as human, so they passed the operator predicate. Nine Codex and Cursor harness envelopes also passed as operator text in every taste and prior-context miner. The live DB relabel moved 150 rows in 65 sessions.
- **Exporter**: `scripts/operator_prompts_export.py` exports operator prompts with the agent turns around them, per project, from raw Claude/Codex transcripts plus the SSD archive and Cursor rows. It is the primitive for any later taste or steering mining.
- **Eval**: evals `steering_anticipation` (prereg 31c67f6, harness aad783a, fix 2be02b2, results 02b6c0f; DECISIONS row `steering-anticipation`).

## 5. Method

**Sources.** Every operator-typed prompt in the research repos, from each project's first archived transcript to 2026-09-26: investment research from 2026-05-25, compression 06-13, agent benchmark research 06-19, fiscal economics 06-24 and psychometrics 07-06.

- Claude transcripts come from `~/.claude/projects` plus the SSD archive (`/Volumes/2TBPNY/agentlogs-archive/claude`; the live directory keeps 30 days).
- Codex rollouts come from the live sessions plus the archive, interactive originators only.
- Cursor rows come from agentlogs.db.
- Authorship uses the shared predicates: `scripts/common/transcript_text.is_operator_authored` for Claude, and `agentlogs.authorship.is_injected_user_text` plus the Codex `user.text` content kind for the others.
- Counts: 3,916 prompts, split as agent benchmark 1,778; investment 1,404; fiscal 528; compression 135; psychometrics 50; one-off research 21.

**Extraction.**

- Each prompt was paired with the tail of the agent report before it (900 chars) and the head of the reply after it.
- The pairs were rendered into 18 chronological packets of about 95K tokens.
- GPT-6 Luna (`llmx -p codex-cli --subscription -m gpt-6-luna -e high`) emitted one JSON object per steering move. Each object carries a verbatim quote, one of 25 move types, a domain-free move with its trigger, a self-fire rating, impact and a skill home.
- Logistics prompts were counted, not listed.

**Checks on the extraction.**

- Quotes, matched mechanically: 91.9% are exact substrings of the source, 96.4% are exact or near (difflib ≥ 0.88), and 87.3% are exact within the cited record.
- Precision: I read the source record for 10 random moves; all 10 were faithful abstractions.
- Recall: I read long prompts that produced no move. The misses were pasted content without commentary, relays and a session-end template.

**Merge.**

- Luna declined one-shot clustering of about 1,070 ids, so stage 1 clustered per project × move family in batches of ≤250 moves: 24 batches, 423 clusters, 94.7% of the 2,598 non-held-out moves assigned.
- Stage 2 merged the clusters across projects into 90 moves with 12 habits. Its prompt ranked distinctiveness above coverage, after a dry run came out generic.
- Luna assigned many clusters to more than one merged move, so its recurrence counts are inflated. Stage 2 was an input to curation, not the catalog.

**Curation (parent).**

- Merged the stage-2 moves with distinctive moves from reading the raw prompts and clusters.
- Dropped one-offs and licensing items.
- Moved finance, fiscal, benchmark and measurement moves into domain packs.
- Paraphrased every example neutrally.

**Holdout discipline.**

- The 60 eval records' moves were removed before the merge.
- At freeze, three mechanical checks passed: no held-out gold quote appears in the catalog, no 5-word run is shared with any held-out prompt, and every hand-added move traces to a non-held-out record.
- Two examples that traced only to held-out records were replaced.
- The coverage grader flagged one duplicate after the freeze. It was removed from the skills copy; the eval tested the frozen copy in `arms/catalog.md`.

## 6. Cost

All mining and judging ran on subscription lanes ($0 metered).

| Step | Calls | Input tok (cached) | Output tok (reasoning) | Wall |
|---|---|---|---|---|
| Luna extraction | 19 | 1.96M (0.18M) | 0.61M (0.06M) | 3–17 min per packet, 6 in parallel |
| Luna stage-1 merge | 25 | 0.71M (0.29M) | 0.15M (0.07M) | minutes per batch, 6 in parallel |
| Luna stage-2 merge (dry + final) | 2 | 0.10M (0.03M) | 0.04M (0.005M) | 266 s + 501 s |
| Eval SUT (3 arms × 54) | 162 | 0.94M | 92K (incl. thinking) | 7.5–8.8 s median per call |
| Eval judges (full + probe) | 480 | ~1.5–3K per call | not captured | about 30 min at 12 workers |

The coverage grader was one Opus subagent.

## 7. Limitations

- The moves are Luna's reading of his prompts. Quotes verify at 96%, and a 10-move precision sample was clean, but move types and self-fire ratings are one model's judgment.
- The catalog is curated by the parent. Its selection is taste, and the operator should prune it.
- The eval is SCREENING (N = 54, low base rate). It cannot exclude a modest true effect (up to +12 pp) and measures only exact anticipation within the same projects. Compound gold moves and process pushes ("why do you need me to sign off?") are hard for every arm.
- The coverage grades come from one model reading the skill text at one commit, with uncommitted peer edits to quant-bias-checklist.md in the tree. Project rules and memory were out of scope; they hold near-levers for three units.

## 8. Artifacts and reproduction

- Catalog: `~/Projects/skills/research/references/follow-up-moves.md`. Eval: `~/Projects/evals/steering_anticipation/` (EXPERIMENT.md has the tables and reproduction commands).
- Scratch (gitignored; it holds private transcript text): `.scratch/operator-steering-2026-09-26/`.
  - `raw/`: exported prompts. `packets/`: extraction packets. `luna/`: raw and verified extractions. `agg/`: moves, summary.
  - `merge1/`, `stage2/`: clusters and merged moves. `coverage_result.md`: per-unit grades with cites.
  - `holdout_final.json`, `cases.jsonl`: eval set.
  - Scripts `extract_steering.py` through `leak_check.py`, and the Luna prompts.
- Re-run the export: `uv run python3 scripts/operator_prompts_export.py --projects arc-agi intel --out DIR`.
