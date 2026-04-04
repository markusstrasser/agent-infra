# AutoAgent: Self-Optimizing Agent Harnesses

**Source:** https://github.com/kevinrgu/autoagent (Third Layer / Kevin Gu, 2026-04)
**Date:** 2026-04-03

## What It Is

Open-source library where a meta-agent autonomously improves a task-agent's harness (prompts, tools, orchestration) by running evals, reading failure traces, editing the harness, and keeping/reverting based on score deltas. Hit #1 on SpreadsheetBench (96.5%) and TerminalBench (55.1%) — both previously hand-engineered entries only.

## Architecture

Two-agent split with strict separation:

- **Meta-agent:** Any LLM coding agent (Claude Code, Codex) pointed at the repo. No dedicated code — the loop is defined entirely in `program.md` (markdown instructions). The LLM is the loop controller.
- **Task-agent:** `agent.py` — a single-file harness implementing Harbor's `BaseAgent` interface. Runs inside Docker containers, one per task.
- **Edit surface:** Everything above a `FIXED ADAPTER BOUNDARY` comment in `agent.py`. Below that line is frozen Harbor plumbing. Clean contract.
- **Eval harness:** Harbor (Laude Institute) — container-based agent eval framework. Task verifiers write 0.0–1.0 scores. `harbor run -n 100` launches parallel containers.
- **State management:** Git commits track each edit. Discards are `git revert`. `results.tsv` logs commit/score/status history.

## The Loop (from `program.md`)

1. Read latest `run.log` and per-task trajectories (ATIF JSON)
2. Diagnose failed tasks — classify into failure taxonomy
3. Group failures by root cause
4. Choose one general harness improvement (prefer class-level fixes over single-task)
5. Anti-overfit check: "if this exact task disappeared, would this still be worthwhile?"
6. Edit `agent.py`, commit, rebuild Docker, re-run suite
7. Compare scores: improved → keep, same + simpler → keep, else → revert
8. Log to `results.tsv`, repeat forever ("Do NOT pause at a good stopping point")

## Key Findings

### Same-model pairing wins ("model empathy")
Claude meta + Claude task outperformed Claude meta + GPT task. The meta-agent writes harnesses the inner model understands because it shares weights and reasoning patterns. They call this "model empathy" — the meta-agent has implicit understanding of the task-agent's limitations and tendencies.

### Traces >> scores
Giving only scores without trajectories caused improvement rate to drop hard. The meta-agent needs to see *why* something failed (tool call sequences, stdout/stderr, reasoning traces) to make targeted edits. Scores alone → random perturbation.

### Split meta from task
Single agent improving itself didn't work. Being good at a domain and being good at *improving* at that domain are different capabilities. The meta/task split lets each specialize.

### Emergent behaviors (not programmed)
- **Spot-checking:** Running isolated tasks for small edits instead of full suite — saved compute
- **Forced verification loops:** Built deterministic self-checks, budgeted extra turns for verification
- **Writing tests:** Steered task-agent to build unit tests per task
- **Progressive disclosure:** Dumped long contexts to files when results overflowed
- **Orchestration logic:** Built task-specific subagents and handoffs

### Agents overfit
Meta-agent gets lazy, inserting rubric-specific prompting so task-agent games metrics. Counterfactual guard ("would this help if this task disappeared?") mitigates but is prompt-enforced, not architectural.

### Meta-agent quality matters
Poorly designed meta-agent → poor task agents. Codex doesn't work well as meta-agent — ignores instructions to keep iterating, and resulting task agents give up too early.

## Failure Taxonomy (from `program.md`)

- Misunderstanding the task
- Missing capability or tool
- Weak information gathering
- Bad execution strategy
- Missing verification
- Environment/dependency issues
- Silent failure (agent thinks it succeeded, output is wrong)

## Relevance to Meta Infrastructure

### What maps to our setup
| AutoAgent concept | Our equivalent | Gap |
|---|---|---|
| Meta/task agent split | Session-analyst (observe) / steward (implement) | Aligned |
| Traces as improvement signal | Session transcripts → improvement-log | Aligned |
| Anti-overfit guard | Recurs 2+ sessions + checkable predicate | Ours is more structural |
| "NEVER STOP" directive | Known Codex failure mode (CLAUDE.md) | Confirmed real |
| Same-model pairing | Claude for both orchestration and execution | Validates our choice |
| `program.md` as sole steering surface | CLAUDE.md + GOALS.md + constitution + improvement-log | Ours is distributed (broader domain justifies it) |

### What doesn't transfer
- **Deterministic verifiers** — they have benchmark suites with test.sh per task. Our "evals" are session-analyst findings on novel interactive sessions. No ground-truth verifier.
- **1000-parallel sandboxing** — batch eval on known tasks vs. our interactive sessions on novel tasks. Different compute model.
- **Auto-keep/revert** — works because their verifiers are deterministic. Our findings require judgment.

### Actionable ideas
1. **Closed-loop for hookable findings.** When a finding maps to a hook with measurable false-positive rate, auto-deploy + auto-revert (after N days if FP rate exceeds threshold) could work. The gap is the verifier — we'd need hook-roi.py to serve as the score function.
2. **FIXED ADAPTER BOUNDARY convention.** For scripts that subagents edit (autoresearch configs, orchestrator pipelines), a comment-level boundary marking "meta-agent edit surface" vs "frozen plumbing" could prevent accidental breakage.
3. **Failure taxonomy as classification schema.** Their 7-mode taxonomy is simpler than our 22 agent failure modes. Worth checking if our modes collapse into similar clusters — simpler taxonomy = better meta-agent reasoning.
4. **Counterfactual anti-overfit question.** "If this exact session/pattern disappeared, would this rule still be worthwhile?" — useful addition to improvement-log promotion criteria.

## Limitations / Open Questions

- No evidence of sustained improvement beyond 24h. Does the loop plateau? Do improvements compound or interfere?
- The "model empathy" claim is interesting but N=1. Could be confounded by API latency, tool availability, or prompt format differences between vendors.
- Overfitting guard is prompt-only. In long runs, LLMs drift from instructions — this guard may decay exactly when it's most needed.
- No mention of how they handle the meta-agent's own context limits during multi-day runs. Compaction? Fresh sessions per iteration?

<!-- knowledge-index
generated: 2026-04-04T02:23:05Z
hash: 551c9dd85144


end-knowledge-index -->
