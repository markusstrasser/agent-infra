# Harness-1: State-Externalizing Harnesses — Research Memo + Leverage Analysis

**Question:** What is Harness-1 (arXiv:2606.02373), and how can agent-infra leverage its core idea?
**Tier:** Deep | **Date:** 2026-06-07
**Primary sources:** paper abstract + repo source code (`pat-jj/harness-1`, read directly via `gh`/`curl`). The HTML render of the paper (arxiv.org/html) is not yet available; ablation *magnitudes* below the abstract level are NOT retrieved — flagged `[UNVERIFIED]`.

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

### Headline results [SOURCE: abstract]
- **0.730 average curated recall** across 8 benchmarks (web, finance, patents, multi-hop QA).
- **+11.4 points** over the next strongest *open* search subagent; competitive with much larger frontier searchers.
- **Strongest gains on held-out transfer benchmarks** → "RL over explicit search state can produce retrieval behaviors that generalize beyond the training domains."

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

## Gaps / what I did not retrieve
- `[UNVERIFIED]` Exact **ablation deltas** isolating state-externalization from the policy (the paper has `inference/queue_browsecomp_ablation.py` + `harness/ultra_core.py`, and an ablations section, but the HTML render 404'd and I did not parse the PDF body). The abstract's transfer claim is the strongest evidence retrieved. If the exact ablation table matters for a Constitution evidence trailer, fetch the PDF next.
- `[UNVERIFIED]` Exact RL algorithm + reward shaping beyond "curated recall" (Tinker-based RL per repo; details in PDF body).

## Recommended next action
Single highest-leverage, in-scope move: a **decision-journal entry** proposing the §2 diagnostic lens as a standing review question for new behavioral rules, with **"Inventory before dispatch" → externalized candidate-pool/dedup check** as the one concrete, demand-cleared externalization to scope. Constitution evidence addition is **propose-and-wait** (human-protected). Offered as a plan, not executed.
