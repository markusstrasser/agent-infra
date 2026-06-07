# Harness-1: State-Externalizing Harnesses — Research Memo + Leverage Analysis

**Question:** What is Harness-1 (arXiv:2606.02373), and how can agent-infra leverage its core idea?
**Tier:** Deep | **Date:** 2026-06-07
**Primary sources:** full paper PDF (arXiv:2606.02373, 21pp, `pdftotext`) + repo source code (`pat-jj/harness-1`, read via `gh`/`curl`). Ablation table (Table 3) and the harness-alone result (Appendix P / Fig 7) are now retrieved and quoted below.

## TL;DR

The paper's value to us is **not the model** (a 20B GPT-OSS retrieval subagent we can't retrain and shouldn't host). It's an empirically-validated, sharper statement of our own Constitution Principle 1 ("Architecture over instructions"):

> **Move all *recoverable bookkeeping* out of the policy and into deterministic environment state. Leave the policy only the *semantic, non-recoverable* decisions.**

Harness-1 is RL-grade evidence that this split (a) works and (b) **generalizes out of domain** — the gains were strongest on held-out transfer benchmarks. That last part is the citable finding: externalizing state didn't just save context, it produced retrieval behavior that transferred.

This reframes a whole class of agent-infra *instruction* rules ("Recitation Before Reasoning", "Post-Synthesis Completeness Check", "Inventory before dispatch", "Recall before reasoning") as the **wrong layer** — they ask the policy to maintain state the harness should own.

---

## What the paper actually is

**Claim:** Search agents are usually trained as policies over a growing transcript — the model must simultaneously decide *how to search* AND remember *what it saw, which evidence matters, which constraints are open, which claims were checked*. That forces RL to optimize both semantic decisions and "recoverable bookkeeping that the environment can maintain more reliably." [SOURCE: arxiv abstract 2606.02373]

**Design.** A 20B retrieval subagent (GPT-OSS-20B base, harmony format) trained SFT→RL inside a **stateful harness**. The harness owns environment-side working memory; the policy keeps only semantic choices.

### The split (from primary source — `harness/` code)

**Harness owns (externalized, deterministic):**
| Component | Evidence in repo |
|---|---|
| Candidate pool | abstract; `trajectory.py` traversed-chunk tracking |
| Importance-tagged **curated set** | abstract; `curated recall` is the headline metric |
| Compact **evidence links** | abstract |
| **Verification records** | abstract |
| Compressed + **deduplicated** observations | `tasks.py` `nondeduplicated_traversed_chunk_ids` vs dedup'd output |
| **Budget-aware context rendering** | abstract; harness renders what the policy sees each turn |
| Append-only **memory `H_t`** = `{step, queries, reflection}` | `trajectory.py:Action.memory` docstring (verbatim) |

**Policy owns (semantic, left in the model) — the *entire* action surface is 5 tools:**
`search_corpus`, `grep_corpus`, `read_document`, `prune_chunks`, `multi_tool_use` [SOURCE: `harness/tools.py`]

The cleanest illustration of the principle is **`prune_chunks`**. Its implementation docstring (verbatim):

> "The tool is functionally a no-op, we detect its usage in the trajectory and prune the chunks from subsequent turns of the model."

The policy emits a *semantic judgment* ("these chunk IDs are irrelevant"); the harness performs the *mechanical bookkeeping* (actually removing them from rendered context going forward). Decision in the policy, execution in the environment. That is the whole paper in one tool.

### Reward / metrics
Reward is **curated recall** (RL optimizes the semantic curate/keep/discard/verify/stop decisions; the bookkeeping is deterministic harness code, so RL never spends gradient on it). Eval metrics computed by the harness, not the policy: `recall, precision, f1, trajectory_recall, final_answer_recall, prune_accuracy, rerank_recall`. [SOURCE: `harness/tasks.py`]
- `trajectory_recall` (everything traversed) vs `recall` (final curated set) — the gap measures curation quality.

### Headline results [SOURCE: PDF §3.2, Table 2]
- **0.730 average curated recall** across 8 benchmarks (web, finance, patents, multi-hop QA); higher than GPT-5.4, Sonnet-4.6, Kimi-K2.5, GPT-OSS-120B under the protocol — only Opus-4.6 ahead on average.
- **+11.4 points** over the next strongest *open* subagent (Tongyi DeepResearch 30B).
- **Transfer (Fig 3) is the headline mechanism evidence:** mean gain over Context-1 is **+7.9 pts on source-family** benchmarks but **+17.0 pts on held-out transfer** (LongSealQA/Seal0QA/FRAMES/HotpotQA) — a **2.2× larger** gain on data furthest from training. The opposite of the standard ML prior.

### The two numbers that matter for a no-training shop

**(A) Component ablation — Table 3** (BrowseComp+, 100 paired queries, *same trained checkpoint, disabled at inference, no retraining*; ∆ is relative to full):

| Disabled mechanism | ∆Recall | ∆FA |
|---|---|---|
| Full Harness-1 (Recall 0.584, FA 0.667) | — | — |
| − Importance tags (binary curate, FIFO eviction) | −4.1% | −7.9% |
| − Sentence-BM25 compression (raw chunks) | +0.2% | −7.0% |
| − Auto-seed on first search | −0.3% | −6.4% |
| − Evidence graph hidden in observations | −2.6% | −5.4% |
| − verify returns "unavailable" | −3.1% | −3.9% |
| − review docs returns "unavailable" | +2.4% | −3.9% |
| − Content-fingerprint dedup | +4.6% | +1.6% (token-budget mechanism, not recall) |
| **All harness mechanisms disabled** | **−12.2%** | **−6.4%** |

Key interpretive quote: *"Removing a state mechanism does not just lose information — the trained policy reverts to a wide, shallow, search-dominated mode and never converges... the harness is where per-turn search bandwidth is converted into a discriminative curated set."* (search_corpus calls rise 3–7 pts, read/verify drop 2–6× when state is removed.)

**(B) Harness-alone, FIXED model, ZERO training — Appendix P / Fig 7** (the result that transfers to us). Same LLM (GPT-5.4), swap only the harness:

| Harness | Curated Recall | FA Recall |
|---|---|---|
| Naive search-add | 0.511 | 0.612 |
| Context-1 harness | 0.807 | 0.821 |
| Harness-1 harness | 0.849 | 0.876 |

*"A +4.2 point recall gain is available to GPT-5.4 simply by switching from Context-1's harness to Harness-1's, without any RL training. This validates the central thesis: the harness is a compute-allocation mechanism that materially changes how much a fixed model can discover."* The bigger jump is naive→structured (**+29.6 pts**): the value of externalizing state *at all*, before any harness sophistication.

> **This is the load-bearing finding for agent-infra.** We run fixed frontier models via prompts and cannot retrain. (B) says harness quality is a *compute-allocation lever on a fixed model* — independent of training — worth tens of recall points. Our leverage is entirely on the harness axis, and the paper proves that axis pays off without touching weights.

**Authors:** Pengcheng Jiang, Zhiyi Shi, Kelly Hong, Xueqiang Xu, Jiashuo Sun, Jimeng Sun, Hammad Bashir, Jiawei Han (UIUC Han group + collaborators). [SOURCE: arxiv]

---

## How agent-infra can leverage it

### 1. Citable evidence for Constitution Principle 1 (highest value, lowest maintenance)
Principle 1 currently rests on SlopCodeBench (instructions shift intercept, architecture shifts slope). Harness-1 adds an orthogonal, RL-grade data point with a **transfer/generalization** result our current evidence lacks. Worth a one-line evidence addition — but the Constitution is human-protected, so this is **propose, not apply**.

The sharper formulation it licenses: not just "if it matters, enforce with a hook," but **"if it's recoverable state, the agent should never be asked to hold it in-context at all."** Hooks *block*; this is about *offloading working memory*. Different axis.

### 2. A diagnostic lens: which of our rules are at the wrong layer?
The paper's split gives a clean test for every behavioral rule we maintain:

> *Is this rule asking the policy to maintain recoverable state? If yes, it belongs in the harness, not the prompt.*

Candidates from current always-loaded / path-scoped rules (all currently **instructions**, i.e. ~0% reliable per Principle 1):
- **"Recitation Before Reasoning"** / **"Recall before reasoning"** — asks the policy to re-hold evidence it already saw. Harness-1's answer: render the curated set deterministically; don't ask.
- **"Post-Synthesis Completeness Check"** ("does every input item appear in the output?") — this is *verification-record* bookkeeping. The harness should track input items and diff, not the policy.
- **"Inventory before dispatch"** (`git log` + grep before spawning subagents) — a *candidate-pool* / dedup check. Documented to have failed twice *as an instruction*. This is the strongest concrete candidate for externalization.
- **Subagent manifest convention** (files-included/skipped) — already half-externalized (the coordinator diffs against `git show --stat`). That diff IS the harness owning verification records. Paper validates the existing design.

### 3. What we ALREADY do right (the paper validates these)
- **Corpus attestation substrate** = Harness-1's *verification records*, externalized at the mutation gateway via transactional outbox, explicitly **not** an agent ritual. The substrate-v1→v2 decision (kill the 2-call agent ritual that had 0 invocations in 9 months; move it to the gateway) is *exactly* the policy→harness move this paper argues for. Strong post-hoc cross-validation of `decisions/2026-05-26-cross-attestation-substrate-v2.md`.
- **agentlogs** = the externalized, deduplicated *observation log* across vendors.
- **Knowledge-index hook** (100% coverage) beating the retired knowledge-substrate MCP = the same lesson at smaller scale.

### 4. Lower-confidence threads
- **Transfer result → evals.** "Reward over explicit state generalizes" is a hypothesis the `~/Projects/evals` harness could probe, but we don't train policies, so this is conceptual, not actionable. Note and park.
- **Harness-1 as a literal retrieval subagent** over research-mcp's corpus: *technically* possible (vLLM + GPU + Chroma over BrowseComp-Plus-style corpus) but a heavy hosting build for a repo that deliberately avoids infra sprawl and uses frontier models via prompts. **Deferred alternative, not recommended** — surfaced per the "surface deferred alternatives" rule. Cost: GPU hosting + corpus rebuild; benefit: marginal over frontier-model + research-mcp retrieval we already have.

---

## What NOT to do (pre-empting re-derivation)
- Do **not** deploy/host the 20B model. We can't retrain it; frontier-model + research-mcp already covers our retrieval.
- Do **not** start an RL training effort. No verifier-rich training loop exists here; out of scope and out of the autonomy boundary.
- Do **not** mass-convert instruction rules to scaffolding speculatively. The lens (§2) identifies candidates; each needs the standard demand check (has the problem recurred 2+ sessions? does externalization already exist?) before building. "Inventory before dispatch" is the one with documented recurrence — it clears the bar; the others are hypotheses.

## Retrieved on PDF read (2026-06-07, fills prior gaps)
- Ablation deltas: Table 3 above (full PDF §3.2 + Appendix M).
- Harness-alone-no-training result: Appendix P / Fig 7 above — the directly transferable finding.
- RL detail [SOURCE: PDF §2, ~line 364]: GRPO-style ("within-group advantage normalization") full-trajectory RL on the SEC train split (3,453 queries); SFT on 899 filtered trajectories. Total 4,352 unique training items — *far less* than Context-1 (~9,159) or Search-R1 (221K). The thesis: moving the behavioral prior into the stateful interface lets small SFT + focused RL transfer.
- A tool-diversity reward `w_div` is used in RL (Fig 5) to prevent tool-mode collapse — secondary to the state argument.

## Still not retrieved
- Per-mechanism failure-mode appendices (§M.1.x) read only at summary level; the qualitative case studies (Appendix Q) were skimmed, not fully parsed. Not load-bearing for the leverage claim.

## Recommended next action
Single highest-leverage, in-scope move: a **decision-journal entry** proposing the §2 diagnostic lens as a standing review question for new behavioral rules, with **"Inventory before dispatch" → externalized candidate-pool/dedup check** as the one concrete, demand-cleared externalization to scope. Constitution evidence addition is **propose-and-wait** (human-protected). Offered as a plan, not executed.
