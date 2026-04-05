---
title: "CORAL: Multi-Agent Evolution with Shared Persistent Memory"
date: 2026-04-05
tags: [multi-agent, memory-architecture, coordination, evolutionary-search, agent-infrastructure]
status: complete
---

# CORAL: Multi-Agent Evolution with Shared Persistent Memory

**Paper:** arXiv:2604.01658 (submitted 2 Apr 2026)
**Authors:** Ao Qu, Han Zheng, Zijian Zhou + 14 co-authors (MIT, NUS, MiniMax, McGill)
**Tier:** Standard

## What CORAL Does

CORAL is a multi-agent evolutionary search framework where LLM agents autonomously explore solution spaces for open-ended optimization problems (math, systems engineering). Unlike fixed evolutionary search (OpenEvolve, ShinkaEvolve, EvoX) that uses hard-coded mutation/crossover heuristics, CORAL delegates all search decisions --- what to explore, when to pivot, what knowledge to record --- to autonomous LLM agents. Agents share state through a filesystem-based persistent memory (the "Hub") and coordinate indirectly by reading each other's attempts and notes. The instruction prompt states: "You are fully autonomous. Do not ask for permission." On 11 benchmark tasks, CORAL establishes SOTA on 8 with 3-10x higher improvement rates and convergence in 5-20 evaluations vs 60-100 for fixed methods. [SOURCE: arXiv:2604.01658]

## Memory Architecture

### The Hub: Shared Filesystem as Memory

CORAL's shared persistent memory M is a plain filesystem organized into three directories:

```
.coral/public/
  attempts/     # JSON records keyed by git commit hash
  notes/        # Markdown files with YAML frontmatter, hierarchical by topic
  skills/       # Reusable procedures as natural-language descriptions + executable artifacts
```

Each agent gets an isolated git worktree with symbolic links pointing to the shared directories. This gives filesystem-level read access to shared state while preventing accidental cross-agent commits. [SOURCE: arXiv:2604.01658]

**Attempts** are the primary coordination mechanism. Each evaluation writes a JSON record keyed by commit hash containing: score, agent ID, status (improved/not), and textual evaluation feedback. Agents browse attempts to find high-performing solutions and use them as starting points. This is the leaderboard --- agents can sort by score and inspect the code behind any top attempt.

**Notes** are markdown files with YAML frontmatter, organized hierarchically with synthesis subdirectories. Agents write notes to record insights, dead ends, and hypotheses. The heartbeat mechanism (below) triggers periodic consolidation of notes.

**Skills** are reusable procedures --- natural-language descriptions paired with executable artifacts. Agents distill repeated patterns into skills during consolidation heartbeats. This is the notes-to-skills pipeline: raw observations crystallize into actionable procedures.

### Formal Notation

The paper uses lightweight notation without heavy formalism:
- **M_t**: shared persistent memory at search step t
- **M-hat_t**: working context constructed as a subset of M_t (progressive disclosure)
- **C_t^(i)**: local context maintained by agent i

No formal mathematical definition of the Hub structure is provided --- it's a filesystem, described operationally.

### Memory Access Patterns

- **No locking.** Unique filenames (commit-hash keys for attempts, agent-generated unique names for notes/skills) prevent conflicts. The paper states: "Because agents operate asynchronously and each attempt is written to a unique file keyed by commit hash, no explicit locking is required for attempt recording. Notes and skills use unique filenames to minimize write conflicts. In practice, we observe no file-level conflicts across agents." [SOURCE: arXiv:2604.01658]
- **Progressive disclosure.** Agents load context incrementally from shared memory rather than ingesting the entire repository upfront. Working memory M-hat_t is constructed as a needed subset of full memory M_t.
- **Asynchronous writes.** Agents write back to shared memory without coordination. No message-passing or explicit synchronization.
- **Checkpoint after evaluation.** After each `coral eval` call, the system snapshots shared persistent memory (notes, skills) with a hash for versioning. No details on retention or pruning of old snapshots.

### Heartbeat-Driven Knowledge Consolidation

Three heartbeat types inject structured reflection prompts into agent context C_t -> C_t':

| Type | Trigger | Effect |
|------|---------|--------|
| Per-iteration reflection | Every 1 evaluation | Encourages note-taking during ongoing work |
| Periodic consolidation | Every 10 evaluations (global) | Review progress, organize notes, distill reusable skills |
| Stagnation redirection | After 5 non-improving evaluations | Reassess strategy, consider pivoting to fundamentally different approach |

Heartbeats are prompt injections, not task reassignment. They modify agent context to steer behavior. This is the closest thing to an "external scheduler" --- but it steers cognition, not task allocation.

### The Evaluation Pipeline

When an agent runs `coral eval -m "what changed and why"`:

1. Stage and commit changes via git
2. Dynamically load grader from private directory (hidden from agents)
3. Execute grader in isolated child process with timeout (default 300s)
4. Compare score against agent's personal best to determine status
5. Write Attempt JSON record with commit-hash key
6. Checkpoint shared persistent memory with version hash
7. Increment global evaluation counter

The grader returns a ScoreBundle with numeric score and textual feedback. The textual feedback is critical --- agents read it to understand WHY something scored well or poorly, not just the number.

## Coordination Protocol

### Indirect Coordination Through Shared State (Stigmergy)

No explicit task allocation exists. Agents independently decide what to explore based on inspection of shared memory. The agent workflow is:

1. **Plan** --- Review leaderboard rankings, inspect top attempts, check notes and skills from other agents
2. **Edit** --- Make focused changes, one idea per evaluation
3. **Evaluate** --- `coral eval -m "what you changed and why"`
4. **Read results and iterate**
5. **Share knowledge** --- Write notes and skills directly to shared directory

This is stigmergic coordination: agents leave traces in the environment (attempts, notes, skills) that influence other agents' behavior. No direct agent-to-agent communication channel exists.

### Cross-Agent Information Transfer (Key Evidence)

The quantitative evidence for coordination value is the strongest part of the paper:

**Kernel Engineering** (596 total attempts across 4 agents):
- 36% of attempts use another agent's commit as their parent
- Cross-agent transfers improve at 17% vs 9% overall rate
- **66% of new record improvements originate from cross-agent parents**
[SOURCE: arXiv:2604.01658]

**Polyominoes** (67 attempts):
- Direct code transfer in 12% of cases but 50% improvement rate (vs 19% average)
- 87% of rounds referenced knowledge from other agents
[SOURCE: arXiv:2604.01658]

The 66% figure is the headline: two-thirds of breakthroughs came from building on another agent's work, not from solo exploration. This is strong evidence that shared persistent memory isn't just nice-to-have --- it's where most of the value is generated in multi-agent settings.

### What the Coordination Protocol Lacks

- No message passing between agents
- No role differentiation (all agents initialized identically --- acknowledged as limitation)
- No explicit conflict resolution
- No priority system or task queue
- No agent-to-agent communication channel
- No heterogeneous agent specialization

## Results That Matter

### Single-Agent Ablation: Knowledge Accumulation

Disabling note and skill creation degrades performance:

| Task | With Knowledge | Without Knowledge | Regression |
|------|---------------|-------------------|-----------|
| Kernel Engineering | 1,350 cycles | 1,601 cycles | 18.6% |
| Polyominoes | 80.2 score | 77.3 score | -3.6% |
| Transaction Scheduling | 4,566 | 4,444 | -2.7% |

[SOURCE: arXiv:2604.01658, Table 3]

The 18.6% regression on Kernel Engineering is substantial --- removing the ability to take notes and distill skills costs almost a fifth of the performance.

### Multi-Agent: Co-evolution vs Independent Runs

| Task | 4-Agent Co-evolution | 4-Agent Independent | Delta |
|------|---------------------|--------------------|----|
| Kernel Engineering | 1,103 cycles | 1,180 cycles | 6.5% better |
| Polyominoes | 84.2 | 80.8 | 4.2% better |
| Transaction Scheduling | 4,694 | 4,629 | 1.4% better |

Co-evolution (shared memory) outperforms independent runs (no sharing), confirming gains come from knowledge-sharing, not just additional compute. [SOURCE: arXiv:2604.01658]

### Adaptive Knowledge Creation (Emergent Behavior)

The most striking finding: agents spontaneously scale knowledge artifact creation with task difficulty.

- **Standard tasks:** 0.05 artifacts per attempt, +2 percentage points improvement from knowledge access
- **Advanced tasks:** 0.55-0.68 artifacts per attempt (10-13x more), 55% improvement rate with knowledge access vs 26% on standard tasks

Agents create 10x more knowledge when problems are harder --- no explicit routing or difficulty detection needed. The infrastructure enables it; the agent decides when to use it. [SOURCE: arXiv:2604.01658]

### Convergence Speed

CORAL converges in 5-20 evaluations vs 60-100 for fixed evolutionary search. Improvement rate 3-10x higher. SOTA on 8 of 11 tasks. The 11 tasks span: 6 mathematical (circle packing, signal processing, Erdos minimum overlap, MMD variants, autocorrelation) and 5 systems (EPLB, PRISM, LLM-SQL, transaction scheduling, cloudcast), plus 2 stress tests (Anthropic kernel engineering, polyominoes). [SOURCE: arXiv:2604.01658]

### Acknowledged Limitations

1. **Frontier model dependency** --- requires frontier LLMs, making local deployment difficult
2. **Homogeneous agents** --- all agents initialized identically; no bootstrapped diversity
3. **Evaluator assumption** --- requires well-specified computable evaluators; "for many important open-ended problems, evaluators are themselves difficult to obtain, incomplete, or even fundamentally ambiguous"

## Comparison to Our Architecture

### Structural Alignment Table

| Dimension | CORAL | Our Infrastructure |
|-----------|-------|-------------------|
| **Memory format** | Filesystem: markdown notes + JSON attempts + skills | Filesystem: MEMORY.md + improvement-log.md + git commits |
| **Memory types** | 3 directories (attempts/notes/skills), untyped within each | Typed entries (user/feedback/project/reference) with frontmatter |
| **Coordination** | Stigmergy (read/write shared files) | Stigmergy (read/write shared files + git) |
| **Concurrency control** | Unique filenames, no locking | Git commits, file-level convention, worktree isolation |
| **Knowledge consolidation** | Heartbeat-triggered (every N evals) | Manual + session-analyst (periodic post-hoc review) |
| **Staleness handling** | Tolerated by design; eval validates results | 90-day decay model, 50-entry cap, verification before citing |
| **Agent differentiation** | None (acknowledged limitation) | None (all agents read same CLAUDE.md) |
| **Task allocation** | Autonomous exploration of solution space | Autonomous within human-defined session scope |
| **Evaluation** | Programmatic scoring (ScoreBundle with numeric + textual) | Mix of programmatic (tests, hooks) and human review |
| **Persistence** | Within single evolutionary run | Across sessions indefinitely |
| **Rule enforcement** | Heartbeats (prompt injection) | Hooks (command/prompt/stop, some blocking) |

### What CORAL Does Better

1. **Structured attempt registry.** JSON records keyed by commit hash with score, agent ID, status, and feedback. Purpose-built for machine consumption --- an agent can query "top-5 attempts sorted by score" and get structured results. Our improvement-log is append-only prose; querying it requires reading the whole file and pattern-matching.

2. **Heartbeat-driven consolidation.** Periodic forced reflection (every 10 evals) and stagnation detection (after 5 non-improving) are architectural, not instructional. Our session-analyst runs periodically post-hoc but doesn't inject consolidation prompts into active agent sessions. CORAL's heartbeats are closer to our hooks --- architectural enforcement of reflection.

3. **Skill distillation from notes.** Explicit pipeline: notes -> consolidation heartbeat -> skills. Raw observations crystallize into reusable procedures. Our improvement-log captures findings, but the "distill into reusable skill" step is manual (human decides what becomes a skill, per Constitution principle requiring 2+ session recurrence).

4. **Cross-agent parent tracking.** Each attempt records which commit (and therefore which agent) it was derived from. The 36% cross-pollination rate with commit-level provenance enables analysis of knowledge flow. We have git commits but no structured "this attempt was based on that agent's work" tracking.

5. **Textual evaluation feedback in attempt records.** The ScoreBundle includes not just the score but WHY something scored well or poorly. Agents read this feedback to understand the evaluation landscape, not just the leaderboard position.

### What We Do Better

1. **Typed memory with decay.** Our MEMORY.md has typed entries (user, feedback, project, reference) with 90-day staleness model and 50-entry cap. CORAL has no memory decay, pruning, or cleanup --- fine for bounded optimization runs (hours to days) but would accumulate noise in persistent infrastructure (months).

2. **Rule enforcement via hooks.** Our hook system (command hooks, prompt hooks, stop hooks) provides real-time behavioral guardrails, some blocking. CORAL has heartbeats (prompt injection, advisory only) but no equivalent to blocking hooks that prevent bad actions.

3. **Human governance layer.** Our Constitution requires 2+ session recurrence before findings become rules. CORAL is fully autonomous with programmatic evaluation --- no human quality gate on what becomes institutional knowledge.

4. **Cross-session persistence.** Our MEMORY.md and improvement-log persist across sessions indefinitely with typed entries and provenance (git trailers, Session-ID). CORAL's memory lives within a single evolutionary run --- no mechanism for carrying knowledge across different problem runs.

5. **Conflict-tested isolation.** Our git worktree isolation is battle-tested across concurrent agent sessions (CAID finding: +7.8pp over soft isolation). CORAL's "no conflicts observed" claim covers 4 agents and ~600 attempts --- limited stress testing.

### Convergent Design Decisions

Both systems independently arrived at:
- Filesystem-as-memory (not a database, not an API)
- Markdown + YAML frontmatter for knowledge artifacts
- Git-based isolation of agent workspaces
- Stigmergic coordination (no message passing)
- Tolerance of staleness (validation/evaluation as the safety net)
- Unique naming to avoid conflicts
- Agents reading other agents' work as primary coordination mechanism

This convergence across independent implementations (MIT research system vs personal infrastructure) suggests these are durable patterns, not accidents.

## Transferable Patterns (Ranked)

### 1. Structured Attempt Registry --- ADOPT

**What:** JSON/JSONL records per attempt with: commit hash, session ID, task description, score/outcome, status, evaluation feedback, parent commit.

**Why:** Our improvement-log is append-only prose. A structured registry would let agents programmatically query "what was tried, what scored well, what failed." CORAL's data: 66% of new records originate from cross-agent parents, and cross-agent transfers improve at 17% vs 9% baseline. Structured access to prior attempts directly enables this cross-pollination.

**How:** Add an `attempts.jsonl` file (or SQLite table in runlogs.db) with fields: `{commit_hash, session_id, task, score, status, feedback, parent_commit}`. Write on commit via hook; query via existing scripts or MCP. This extends rather than replaces improvement-log.

**Maintenance cost:** Low. One JSONL file, one write hook, one query script.

### 2. Stagnation-Triggered Redirection --- ADOPT

**What:** After N non-improving evaluations/commits, inject a prompt urging strategy reassessment ("try a fundamentally different approach").

**Why:** We have no equivalent. Sessions can spin on one approach without architectural nudging to pivot. CORAL's 5-eval stagnation trigger is simple and effective.

**How:** Maps to our stop hook system. Track consecutive non-improving commits (failed tests, repeated patterns, no score improvement) and inject advisory prompt: "5 consecutive non-improving attempts detected. Consider reassessing your strategy." Implementation: git log parsing in a stop hook.

**Maintenance cost:** Low. One stop hook, counting logic.

### 3. Periodic Consolidation Heartbeat --- EXTRACT PATTERN

**What:** Every N evaluations, pause and consolidate: review accumulated notes, organize, distill skills.

**Why:** Our session-analyst does post-hoc analysis. CORAL's in-session consolidation is more timely --- agents organize knowledge while context is fresh. However, our sessions are shorter (single-task, minutes to hours) vs CORAL's long evolutionary runs (hours to days). The pattern is useful but the trigger mechanism doesn't map directly.

**How:** Could be a `/loop` consolidation step: every Nth loop iteration, run note consolidation. Or a time-based stop hook for long-running sessions (>30 min) that prompts knowledge organization. Lower priority than #1 and #2 because our session length makes mid-session consolidation less critical.

**Maintenance cost:** Medium. Needs trigger tuning for our session patterns.

### 4. Cross-Agent Parent Tracking --- WATCH

**What:** Record which agent's commit was the starting point for each new attempt.

**Why:** The 36%/66% cross-pollination numbers are compelling evidence. But our agents rarely build directly on each other's commits --- they share state via files, not code lineage. This matters more for evolutionary code search than our infrastructure pattern.

**How:** Would require `Source:` git trailer discipline (convention already exists) plus a query tool. Low priority unless we start doing more autoresearch-style evolutionary work.

### 5. Adaptive Knowledge Creation --- OBSERVE

**What:** Agents spontaneously create 10x more knowledge artifacts on harder tasks.

**Why:** Interesting emergent behavior. Validates our design: provide the tools (MEMORY.md, improvement-log), don't mandate usage. Agents self-regulate. No action needed.

## Verdict: EXTRACT PATTERN

**Not adopt wholesale.** CORAL is an evolutionary search framework for bounded optimization problems, not a general agent infrastructure. Its memory architecture is designed for single multi-agent runs (hours to days), not persistent cross-session knowledge management (months). The six-module architecture (config, agent system, grader, workspace, hub, core types) is clean but solves a different problem.

**Adopt two patterns:**
1. **Structured attempt registry** --- the strongest transferable idea. Machine-readable records of what was tried and what worked.
2. **Stagnation-triggered redirection** --- simple stop hook, bounded implementation, directly useful.

**Extract one pattern:**
3. **Periodic consolidation** --- useful concept but needs adaptation to our shorter session model.

**Observe one emergent behavior:**
4. **Adaptive knowledge creation** --- validates our "provide tools, don't mandate" approach.

**Ignore:** Evolutionary search mechanics (mutation/crossover via LLM), the benchmark suite, comparison to OpenEvolve/ShinkaEvolve. Domain-specific to optimization-as-search.

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | SOTA on 8/11 tasks with 3-10x improvement rate | Benchmark results, Table 2 | HIGH | arXiv:2604.01658 | VERIFIED (from paper) |
| 2 | 66% of new records from cross-agent parents | Kernel Engineering analysis, 596 attempts | HIGH | arXiv:2604.01658 | VERIFIED (from paper) |
| 3 | 18.6% regression when disabling knowledge | Ablation Table 3 | HIGH | arXiv:2604.01658 | VERIFIED (from paper) |
| 4 | No file-level conflicts across agents | Authors' observation | MEDIUM | arXiv:2604.01658 | SELF-REPORTED, limited scale (4 agents) |
| 5 | 10x more knowledge creation on hard tasks | Standard vs advanced task comparison | HIGH | arXiv:2604.01658 | VERIFIED (from paper) |
| 6 | Filesystem+markdown is convergent design | CORAL + our infra independently arrived at same pattern | MEDIUM | [INFERENCE] | Inference from two implementations |

## Search Log

| Step | Tool | Query | Result |
|------|------|-------|--------|
| 1 | search_papers (S2) | "CORAL autonomous multi-agent evolution" | Found paper 0f1156bd... |
| 2 | web_search_exa | "CORAL Towards Autonomous Multi-Agent Evolution arxiv 2604.01658" | arXiv HTML, HuggingFace, papers.cool |
| 3 | save_paper | 0f1156bd... | Saved to corpus |
| 4 | fetch_paper (URL) | arxiv.org/pdf/2604.01658 | 81,666 chars, ~20K tokens |
| 5 | WebFetch (pass 1) | arxiv HTML --- memory arch, coordination, results | Full architecture extraction |
| 6 | WebFetch (pass 2) | arxiv HTML --- agent prompts, heartbeats, limitations | Workflow, benchmarks, caveats |

<!-- knowledge-index
generated: 2026-04-05T23:50:31Z
hash: 5d8058db25a3

title: CORAL: Multi-Agent Evolution with Shared Persistent Memory
status: complete
tags: multi-agent, memory-architecture, coordination, evolutionary-search, agent-infrastructure
table_claims: 6

end-knowledge-index -->
