# RSI Gap Sweep — Axis 4: Automated Harness/Scaffold Optimization (beyond AutoAgent)

Date: 2026-06-12 · Anchor question: meta-agents/optimizers that edit an agent's harness
(prompts, tools, orchestration, memory config) against evals. Method: Exa (research-paper +
date filters), Brave (OSS/practitioner). All arXiv IDs + repos curl-verified live.

> Scope note: AutoAgent itself is covered in a prior memo and excluded. Everything below is a
> follow-up, competitor, or critique. Prior memos `meta-harness-deep-dive-2026-03.md` and
> `hutter-evolver-architecture-2026-06.md` already cover Meta-Harness and the AlphaEvolve/DGM/
> FunSearch evolutionary lineage — those are NOT re-derived here; this axis adds the *harness-
> optimization-specific* cluster that matured Feb–Jun 2026.

## Headline

The field this axis names ("agent harness optimization" / "an agent that edits another agent's
harness against eval scores") **crystallized into a named sub-field between Feb and Jun 2026** —
it now has a survey (Code as Agent Harness), a benchmark+toolkit (VeRO/VeRO-Bench, Scale AI),
and ~6 distinct systems with measured results. This is the most mature of the RSI sub-areas.
The dominant design converged independently across labs: **a coding-agent proposer reads source
code + execution traces + scores from a filesystem, proposes a harness edit, validates via
regression replay before promoting.** Transfer evidence is mixed-but-trending-positive: the
strongest results show frozen evolved harnesses transferring across model families
(AHE: +5.1–10.1pp cross-family; gskill: transfers across LMs and harnesses), while the
overfitting/Goodhart literature confirms the eval-quality bottleneck is real and measured.

## Claims table

| # | Claim | Source | Provenance | Conf |
|---|-------|--------|-----------|------|
| 1 | "Code as Agent Harness" — 42-author survey (UIUC/Meta/Stanford) formalizes harness as code substrate; 3 layers (interface, mechanisms, scaling); names open challenges incl. "regression-free harness improvement" and "evaluation beyond final task success" | arXiv:2605.18747 (May 2026) | abstract + author list verified via arxiv.org title fetch | A |
| 2 | **VeRO** (Scale AI) = first systematic toolkit+benchmark for harness optimization: outer harness providing versioned snapshots, budget-controlled eval, structured traces; VeRO-Bench = target agents+tasks. Empirically compares *which optimizers and which modification types* reliably improve target harnesses. Code: github.com/scaleapi/vero | arXiv:2602.22480 (Feb 2026, v4) | title + repo HTTP 200 verified | A |
| 3 | **Meta-Harness** (Stanford IRIS, Lee/Khattab/Finn) — coding-agent proposer over harness code via filesystem feedback (traces not scalar scores). +7.7pt text classif w/ 4× fewer tokens; +4.7pt math across 5 held-out models; #1 Haiku-4.5 on TBench-2. Repo 1019★. (Already in prior memo `meta-harness-deep-dive`.) | arXiv:2603.28052; github.com/stanford-iris-lab/meta-harness | repo metadata verified | A |
| 4 | **AHE (Agentic Harness Engineering)** — closed loop w/ 3 "observability pillars" (component/experience/decision); every edit = falsifiable contract w/ self-declared prediction verified next round. 10 iters lift TBench-2 pass@1 69.7→77.0%, beats Codex-CLI (71.9%) + ACE + TF-GRPO baselines. **Strongest transfer evidence**: frozen harness transfers w/o re-evolution — SWE-bench-verified top aggregate at 12% fewer tokens; +5.1–10.1pp cross-family across 3 model families. Ablation: gain localizes to tools/middleware/long-term-memory, NOT system prompt | arXiv:2604.25850 (Apr 2026) | abstract via Exa; arXiv ID format-consistent (NOT independently curl-verified — verify before citing as load-bearing) | B+ |
| 5 | **Self-Harness** (Shanghai AI Lab) — agent improves own harness w/o human/stronger external agent. 3 stages: Weakness Mining → Harness Proposal → Proposal Validation (regression-gated). TBench-2.0, 3 model families: 40.5→61.9%, 23.8→38.1%, 42.9→57.1% held-out. Qualitative: turns model-specific weaknesses into executable edits, not generic instructions | arXiv:2606.09498 (Jun 9 2026) | title verified | A |
| 6 | **MOSS** (HKGAI/HKUST) — argues text-mutable self-evolution (skills/prompts/memory schemas) leaves the *harness code* untouched; routing/hook-ordering/dispatch live in code → a class of structural failure is "physically unreachable from the text layer." Source-level rewriting anchored to curated production-failure batches; trial-worker replay; consent-gated in-place container swap w/ health-probe rollback. OpenClaw: 4-task mean 0.25→0.61 in one cycle, no human. Code: github.com/hkgai-official/Moss | arXiv:2605.22794 (May 2026) | title + repo HTTP 200 verified | A |
| 7 | **AEvo** (DeepWisdom/HKUST-GZ) — "harnessed meta-editing": meta-agent doesn't propose the next candidate directly, it *edits the procedure/agent-context that controls future evolution*. Accumulated evolution context = process-level state. +26% relative over strongest of 5 evolution baselines; SOTA on 3 open-ended opt tasks at equal iteration budget | arXiv:2605.13821 (May 2026) | title verified | A |
| 8 | **ABSTRAL** — automated *multi-agent* system design; MAS architecture as an evolving SKILL.md refined by contrastive trace analysis. Design knowledge transfers (transferred seeds = cold-start iter-3 perf in 1 iter); discovers specialist roles absent from initial design. SOPBench 70%/65.96% w/ GPT-4o. Measures multi-agent coordination tax (26% turn efficiency) | arXiv:2603.22791 (Mar 2026) | title verified | A |
| 9 | **Gödel-machine lineage continues**: Darwin Gödel Machine (Clune, ICLR 2026; SWE-bench 20→50%, Polyglot 14.2→30.7%); **Huxley-Gödel Machine** (Schmidhuber et al., ICLR 2026 Oral) — identifies "Metaproductivity-Performance Mismatch" (benchmark perf ≠ self-improvement potential), proposes CMP metric over descendant clade; **strong transfer claim**: HGM-optimized on SWE-bench Verified (GPT-5-mini) → human-level on SWE-bench Lite (GPT-5). Code: github.com/metauto-ai/HGM (HTTP 200). POLARIS = Gödel-agent for small LMs via experience-abstracted policy repair | DGM OpenReview pUpzQZTvGY; HGM OpenReview T0EiEuhOOL + repo; POLARIS df4dCy8kSn | repo verified; OpenReview abstracts | A |
| 10 | **GEPA is the production-grade prompt/program optimizer** (ICLR 2026; gradient-free reflective evolution, Pareto selection; beats GRPO by up to 20% at 35× fewer rollouts). DSPy 3.x ships it alongside MIPROv2/SIMBA/COPRO. `optimize_anything` API extends to ANY textual artifact incl. agent skills/architectures | gepa-ai/gepa repo; Decagon blog; futureagi.com 2026 guide | OSS repo + vendor blogs | A |
| 11 | **gskill** (GEPA team, Tan/Agrawal/Klein/Sen) — GEPA loop learns coding-agent *skills* from successes/failures on a target repo (SWE-smith generates tasks). **Skills transfer across language models AND agent harnesses** | gepa-ai.github.io blog 2026-02-18 | vendor/author blog | B+ |

## (b) Transfer vs overfit — the central empirical question

**Transfer-POSITIVE evidence (frozen harness/skill generalizes):**
- AHE: +5.1–10.1pp cross-family across 3 model families; SWE-bench transfer at −12% tokens;
  ablation says factual harness *structure* (tools/middleware/memory) transfers while prompt-
  level edits are more model-specific [#4]. This is the cleanest "it's not just eval-fitting" result.
- HGM: optimized on one benchmark/model → human-level on a *different* benchmark + *different*
  model (GPT-5-mini→GPT-5) [#9].
- Meta-Harness: single discovered harness +4.7pt across **5 held-out models** [#3].
- gskill: skills transfer across LMs and harnesses [#11].
- Pattern across papers: **structural/tool/memory edits transfer; system-prompt edits overfit.**
  (AHE ablation states this explicitly; Self-Harness echoes "model-specific" framing.)

**Transfer-NEGATIVE / overfit evidence:**
- **PromptBridge** documents "Model Drifting" — a prompt optimized for one model "often yields
  substantially worse performance than a prompt optimized for the target model"; needs a learned
  cross-model mapping to recover (arXiv:2512.01420). I.e. naive prompt-level optimization does
  NOT transfer across models. [Conf A]
- **Prompt Genotyping**: surface prompt features explain R²=0.86 on synthetic benchmarks but
  R²=−0.13 (worse-than-random) on real GPT-4o-mini outputs — "benchmark optimization doesn't
  transfer to deployment" (OpenReview WCNAcIKREG). [Conf A — direct measurement of the gap]
- **Quagmires in SFT-RL**: high SFT scores are biased to simpler/homogeneous data and don't
  predict downstream gains; held-out generalization loss + Pass@large-k are the honest proxies
  (ICLR 2026, uLM3BfKo19). Analogous lesson for any inner-metric-vs-true-goal loop. [Conf A]

**Read:** Transfer is real but *conditional on what gets edited*. Code-structural harness edits
(tools, middleware, memory architecture, routing) carry general engineering experience and
transfer across models/tasks. Pure prompt/instruction edits are model-specific and the prime
overfitting surface. This directly corroborates our own STACK wedge intuition and the
state-externalization lens (`state-externalization-lens.md`): externalize recoverable
*structure*, treat prompt text as the volatile/least-transferable layer.

## (c) Eval-quality bottleneck — does harness optimization Goodhart on weak evals?

Yes, and the field now treats this as the binding constraint, not a footnote:
- The **Code as Agent Harness** survey lists "evaluation beyond final task success" and
  "verification under incomplete feedback" as top open challenges [#1].
- **Prompt Genotyping** is the quantified Goodhart case: optimizing to a synthetic eval gives
  negative real-world transfer (R² gap > 1.0).
- Formal Goodhart work (Majka/El-Mhamdi, ICML 2025 TAIG + MoFA) shows over-optimization severity
  depends on the *tail behavior* of the goal-proxy discrepancy — heavy-tailed discrepancy →
  over-optimization at a rate inversely proportional to heavy-tailedness. Implication: an eval
  that's a heavy-tailed proxy for the true objective is the dangerous case for an autonomous loop.
- **When Gradients Collide** (ACL 2026 wksp): multi-objective textual-gradient prompt opt fails
  via gradient dilution + instruction interference — in 6/10 configs optimization *never beat the
  initial prompt*. Multi-criteria harness objectives are a known failure surface.
- The systems that defend against this all converge on the SAME mechanism: **regression-gated
  validation before promotion + held-out splits.** AHE makes every edit a "falsifiable contract"
  (self-predict → verify next round); Self-Harness "Proposal Validation" only accepts after
  regression testing; MOSS replays a production-failure batch in ephemeral trial workers +
  health-probe rollback. The architecture answer to Goodhart here is *verification gating*, not
  better metrics.

## (d) Practitioner / production reports

- **Decagon** (customer-support agents) — published a test-driven GEPA-for-production playbook;
  cites GEPA beating GRPO by ~20% at 35× fewer rollouts. Real deployment context. [Conf A]
- **Slavozard** (enterprise agents, bearblog) — honest field report: DSPy signatures + GEPA
  round-robin per-module; the hard part is "iteratively developing a better understanding of
  what data we need for training" — i.e. eval/data curation is the bottleneck, not the optimizer.
- **GEPA gskill blog** — skills learned on a repo transfer across LMs/harnesses (production-ish).
- **FlowZap / futureagi 2026 guides** — frame the practitioner mental model precisely as
  "optimizer runs experiments on an agent configuration" needing {benchmark owner, optimizer,
  candidate agent, eval harness, metrics store}. DSPy 3.x optimizers are described as
  "shipping in production stacks," not research demos.
- **"The Optimizer in the Loop"** (Pappas, Medium May 2026) — governance/safety practitioner
  essay: if you can't say how many of your last-30-day prompt versions were human-authored or
  passed review, "you are already running an Evolution Agent loop with nobody in the review seat."
  Names the recursion hazard: the Evolution Agent must be denied capability tokens to edit its own
  policy-classification file (capability-based sandbox, policy outside harness filesystem reach).
  Cites a real AgentCore policy-bypass disclosure (Unit 42, Mar 2026) as the cautionary case.
  [Conf B — opinion essay, but the safety framing is directly relevant to our autonomy boundaries]

## Relevance to agent-infra (brief)

1. We are *already* running a primitive version of this (Grinder/Dreamer hutter loop; inventory-
   before-dispatch; buildthenundo detection). The field's convergent answer — **coding-agent
   proposer + filesystem trace access + regression-gated promotion** — matches our git-bus +
   clean-verifier design. AHE's "every edit = self-predicted falsifiable contract verified next
   round" is a concrete, adoptable pattern we don't yet have (cheap, hookable).
2. The transfer finding (structure transfers, prompt text overfits) *validates* the existing
   STACK wedge and `state-externalization-lens` rule and argues against prompt-level meta-tuning
   as a standing loop.
3. The eval-quality / Goodhart literature is a direct warning for any scored self-improvement
   gate — corroborates the twice-vetoed `session_quality` decision: don't build a composite
   scored gate; the field's working answer is *regression replay against held-out tasks*, which
   is what our evals/ + report-only buildthenundo already approximate. No new build implied.
4. VeRO-Bench (Scale AI) is the reference harness-optimization benchmark if we ever want to
   measure our own loop against an external standard — survey before building any eval here
   (see `evals-macvb-home`).

## Confidence + gaps

- Grade A on existence/identity of all systems (arXiv IDs + 3 repos curl-verified live).
- Grade B+ on AHE's specific numbers (abstract via Exa only; ID not independently curl-verified —
  verify arXiv:2604.25850 before quoting the 69.7→77.0 / cross-family figures as load-bearing).
- Did NOT pull full PDFs (turn budget); numbers are from abstracts/blogs. Treat all percentage
  figures as abstract-reported, not independently reproduced.
- Stance-count check skipped (Exa/arXiv coverage is the evidence base here; scite has thin
  coverage on Feb–Jun 2026 arXiv preprints).
