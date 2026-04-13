## CAID: Centralized Asynchronous Isolated Delegation for Multi-Agent SWE — Research Memo

**Question:** What is the CAID framework from CMU, and what are its specific mechanisms for multi-agent software engineering coordination?
**Tier:** Standard | **Date:** 2026-03-30
**Ground truth:** No prior research on this specific paper.

### Paper Identity

- **Title:** Effective Strategies for Asynchronous Software Engineering Agents
- **Authors:** Jiayi Geng, Graham Neubig (Carnegie Mellon University, Language Technologies Institute)
- **arXiv:** 2603.21489 (submitted 2026-03-23)
- **Code:** https://github.com/JiayiGeng/CAID (Python 97.3%, Shell 2.7%)
- **Semantic Scholar ID:** 48fcb1e947434c1d0fbe4fbe003bd7933ec329b4
- **Citations:** 0 (too new for scite/S2 coverage)

### Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | CAID achieves +26.3pp on PaperBench (MiniMax) | Paper Table 2: 10.4% -> 36.7% | HIGH | [arXiv:2603.21489 Table 2] | VERIFIED |
| 2 | CAID achieves +14.7pp on Commit0-Lite (MiniMax) | Paper Table 2: 42.3% -> 57.0% | HIGH | [arXiv:2603.21489 Table 2] | VERIFIED |
| 3 | Git worktree isolation beats soft isolation by 7.8pp | Paper Table 3: 55.5% -> 63.3% on PaperBench | HIGH | [arXiv:2603.21489 Table 3] | VERIFIED |
| 4 | Soft isolation HURTS vs single-agent on PaperBench | Table 3: 55.5% (soft) vs 57.2% (single) | HIGH | [arXiv:2603.21489 Table 3] | VERIFIED |
| 5 | Doubling single-agent iterations gives minimal gains | Figure 2: MiniMax 100->200 iters, small delta | HIGH | [arXiv:2603.21489 Fig 2] | VERIFIED |
| 6 | Multi-agent costs 3-5x more than single-agent | Paper cost analysis, e.g. 1.6 -> 4.5 cost units | HIGH | [arXiv:2603.21489] | VERIFIED |
| 7 | No wall-clock speedup from parallelism | Sequential merge-test cycles dominate | HIGH | [arXiv:2603.21489] | VERIFIED |
| 8 | Manager decomposition quality causes 4x variance | minitorch: 8.7% vs 34.3% on same task | HIGH | [arXiv:2603.21489 Fig 4] | VERIFIED |
| 9 | Optimal parallelism is 2-4 agents, not 8+ | Fig 3: Commit0 peaks at 4, PaperBench at 2 | HIGH | [arXiv:2603.21489 Fig 3] | VERIFIED |
| 10 | Round-manager-review gets highest accuracy (60.2%) | Figure 5, 9 Commit0 repos | HIGH | [arXiv:2603.21489 Fig 5] | VERIFIED |

### Framework Architecture

CAID maps software engineering primitives to coordination functions:

| SWE Primitive | Coordination Function |
|---|---|
| Dependency graph | Scheduling constraints |
| git worktree | Workspace isolation |
| git commit | Completion signaling |
| git merge | Output integration |
| Test suite | Verification gate |

**Three roles:**
1. **Central Manager** — decomposes task, builds dependency DAG, delegates work, merges results
2. **Engineer Agents** — execute tasks independently in isolated worktrees, self-verify
3. **Git primitives** — provide the coordination backbone (no custom message passing)

### Manager Agent: Dependency Graph Construction

The manager constructs a directed acyclic graph G=(V,E) where:
- **V** = work units (file-level or function-level tasks)
- **E** = dependency edges (unit j depends on unit i)
- A unit v_j is **Ready** at time t iff all predecessors are complete: `Ready_t(v_j) <=> for all (v_i, v_j) in E, v_i in C_t`

**Construction is prompt-engineered, not learned.** The manager LLM receives the full task specification and repository structure, then uses its code understanding to identify dependencies.

**Per-benchmark strategies:**
- **Commit0:** Manager analyzes import statements for file-level dependencies and examines test cases to understand required implementations. Tasks delegated at file or function level.
- **PaperBench:** Manager reads the research paper to infer implementation order from main contributions described. Tasks correspond to major components.

The manager splits work into at most N task groups (N = max parallel engineers). Groups are ordered by dependencies — within a group, tasks can run concurrently.

### Isolation Model: Git Worktrees

**Hard isolation via git worktree, not containers or instructions.**

Each engineer agent receives a physically separate git worktree — an actual separate working directory backed by git, each on its own branch. This is not a "virtual workspace" or sandboxed context.

**Three isolation levels tested:**

| Level | Mechanism | PaperBench | Commit0-Lite |
|---|---|---|---|
| None (single agent) | One agent, one workspace | 57.2% | 53.1% |
| Soft isolation | Verbal instructions ("handle src/models/") | 55.5% | 56.1% |
| Hard isolation (worktree) | Separate git worktree per engineer | **63.3%** | **59.1%** |

**Critical finding:** Soft isolation is WORSE than single-agent on open-ended tasks (PaperBench: -1.7pp). The paper argues this is because instruction-level boundaries are insufficient for longer trajectories — agents drift into each other's territory. Physical filesystem separation forces clean interfaces.

### Merge and Conflict Resolution

1. Engineer completes work and self-verifies (runs tests in own worktree)
2. Engineer commits to its branch
3. Manager attempts `git merge` into main branch sequentially
4. On conflict: the engineer who produced the conflicting commit resolves it — pulls latest main, resolves locally, resubmits
5. Main branch remains the single source of integrated state throughout

Merges are **sequential, not parallel** — this is a key bottleneck. The manager merges one engineer's work at a time and runs the full test suite after each merge. This sequential merge-test cycle is why multi-agent execution doesn't reduce wall-clock time despite parallel task execution.

### Verification Strategies

Three strategies compared on 9 Commit0 repositories:

| Strategy | Pass Rate | Runtime (s) | Description |
|---|---|---|---|
| Round-Manager Review | **60.2%** | 3689.1 (slowest) | Manager reviews each merge, can reject and reassign |
| Engineer Self-Verification | 55.1% | 2243.9 | Engineer runs tests locally, iterates until pass, then commits |
| Efficiency-Prioritized | 54.0% | 1908.6 (fastest) | Minimal verification, optimize for speed |

Self-verification is the default balance point. Round-manager review achieves highest accuracy but at 1.6x the runtime cost.

### Communication Schema

Manager-engineer communication uses **structured JSON** with defined schemas, not natural language. The paper uses an async event loop that enables immediate reassignment when engineers finish early.

**Context management:** Uses `LLMSummarizingCondenser` to manage context growth for long tasks — this is an OpenHands component that periodically summarizes conversation history to stay within context limits.

### Benchmark Results (Full)

**PaperBench (2 engineers optimal):**

| Model | Single-Agent | CAID | Delta |
|---|---|---|---|
| Claude Sonnet 4.5 | 57.2% | 63.3% | **+6.1pp** |
| MiniMax 2.5 | 10.4% | 36.7% | **+26.3pp** |
| GLM 4.7 | 38.0% | 45.4% | **+7.4pp** |

**Commit0-Lite (4 engineers optimal):**

| Model | Single-Agent | CAID | Delta |
|---|---|---|---|
| Claude Sonnet 4.5 | 53.1% | 59.1% | **+6.0pp** |
| MiniMax 2.5 | 42.3% | 57.0% | **+14.7pp** |
| GLM 4.7 | 42.8% | 46.5% | **+3.7pp** |

**Combined Single+Multi strategy** (PaperBench, Claude): 66.8% score — route some tasks to single agent, others to multi. But runtime increases from 2080.4s to 3883.9s and cost from 9.3 to 12.6.

**Note on reported "+26.7 on PaperBench":** The actual delta is +26.3pp (MiniMax 2.5, 10.4% -> 36.7%). The +14.3 on Commit0 matches +14.7pp (MiniMax 2.5, 42.3% -> 57.0%). The user's numbers are approximately correct but slightly off — the headline gains are specific to MiniMax 2.5, not Claude.

### Ablation Studies

**1. Iteration budget is not the bottleneck.** Doubling single-agent iterations (100 -> 200) gives minimal improvement. MiniMax on PaperBench shows "only a small change" vs CAID's >25pp gain. This argues the gains are from decomposition and isolation, not just more compute.

**2. Parallelism has diminishing returns.** Commit0-Lite peaks at 4 engineers (59.1%), declining at 8 engineers due to integration overhead and conflict resolution cost. PaperBench shows minimal gains beyond 2 engineers.

**3. Manager decomposition quality is the critical variable.** On the minitorch task: CAID Run 1 achieved 8.7% pass rate, Run 2 achieved 34.3%. The difference: whether the manager assigned the critical dependency (autodiff.py) correctly or gave an engineer unrelated files. This is a 4x variance from decomposition alone.

### Cost and Latency

Multi-agent CAID costs 3-5x more than single-agent execution. Wall-clock runtime is NOT reduced despite parallel execution (sequential merge-test cycles dominate).

Example (Commit0-Lite, MiniMax 2.5):
- Single-agent: 752.1s runtime, 1.6 cost units
- CAID (4 engineers): 1908.6s runtime, 4.5 cost units

The paper frames this as "paying more for accuracy, not speed."

### Implementation Details (from GitHub repo)

**Built on OpenHands** (open-source agent framework). Key structure:
- `core/` — core coordination implementation
- `prompts/` — LLM prompt templates (manager and engineer prompts)
- `tasks/base.py` — TaskModule interface with 6 abstract methods: `get_docker_image()`, `get_work_dir()`, `get_workspace_config()`, `load_task_data()`, `setup_workspace()`, `evaluate()`
- `tasks/` — Commit0Task and PaperbenchTask implementations
- `scripts/run_single.sh` and `scripts/run_multi.sh` — execution entry points

**Dependencies:** Python >= 3.12, uv, Docker (for OpenHands sandboxes), LiteLLM for model abstraction, `paperbench` and `preparedness-turn-completer` from OpenAI's frontier-evals.

**LLM backend:** LiteLLM model identifiers with `LLM_BASE_URL` and `LLM_API_KEY` env vars. Any LiteLLM-compatible backend works.

**Configuration knobs:**
- `task` — "commit0" or "paperbench"
- `model` — manager LLM identifier
- `subagent_model` — engineer model (defaults to manager)
- `max_subagents` — parallel worker count
- `sub_iterations` — per-agent iteration limit
- `rounds_of_chat` — task assignment rounds per engineer
- `max_iterations` — manager iteration limit

### Transferable Patterns (for our infrastructure)

1. **Worktree isolation > instruction isolation.** We already use `isolation: "worktree"` for Explore/analysis agents. This paper provides controlled evidence that physical isolation beats verbal boundaries by 7.8pp. Validates our existing approach.

2. **Sequential merge with test gates.** Our current approach of "commit after each logical edit" when multiple agents are active aligns with CAID's merge model. The paper confirms this is the right pattern — parallel merges cause more problems than they solve.

3. **Manager decomposition is the bottleneck.** 4x variance from decomposition quality alone. This maps to our experience with subagent dispatch — the dispatch prompt quality determines outcome more than the execution agent's capability. Invest in decomposition prompts.

4. **2-4 agents is the sweet spot.** Diminishing returns beyond 4 parallel agents. Aligns with our existing subagent patterns (typically 3-5 parallel).

5. **Soft isolation is a trap.** Verbal instructions like "you handle src/models/" actively hurt on open-ended tasks. If delegating, use actual filesystem isolation.

6. **Self-verification is the default.** Round-manager review is better but 1.6x slower. For most tasks, engineer self-verification (run tests, iterate) is the right tradeoff. Matches our existing pattern of subagents validating their own work.

### What's Uncertain

- **Generalization beyond Commit0 and PaperBench.** These are greenfield implementation tasks. The paper doesn't test maintenance, debugging, or refactoring — where dependency graphs are murkier.
- **Manager prompt details.** The decomposition prompts in `prompts/` are the most valuable artifact but not detailed in the paper — need to read the repo source.
- **Conflict resolution specifics.** The paper says the conflicting engineer resolves, but doesn't detail how complex multi-file conflicts are handled. In practice, merge conflicts from independent worktrees on separate files should be rare.
- **Scaling to real codebases.** Both benchmarks involve moderate-sized implementations. Production repos with thousands of files and implicit dependencies would stress the prompt-engineered dependency graph.
- **No scite citation data** — paper is 7 days old, zero citations. Cannot assess community reception yet. [SCITE: NO COVERAGE]

### Sources

| Source | Type | Used For |
|---|---|---|
| arXiv:2603.21489 (HTML full text) | [PREPRINT] | All technical details, benchmark numbers |
| arXiv:2603.21489 (PDF, 83K chars) | [PREPRINT] | Fetched via research-mcp |
| github.com/JiayiGeng/CAID | [SOURCE: repo] | Implementation structure, dependencies, configuration |
| bemiagent.com blog post | [SOURCE: blog] | Summary/cross-check of mechanisms |
| Semantic Scholar corpus | [DATABASE: S2] | Paper discovery and metadata |

<!-- knowledge-index
generated: 2026-03-31T03:08:57Z
hash: f4e54091c3ff

sources: 1
  DATA: BASE: S2
table_claims: 10

end-knowledge-index -->
