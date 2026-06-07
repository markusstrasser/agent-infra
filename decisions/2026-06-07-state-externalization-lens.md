---
id: 2026-06-07-state-externalization-lens
concept: architecture-over-instructions
repo: agent-infra
decision_date: 2026-06-07
recorded_date: 2026-06-07
provenance: contemporaneous
status: accepted
initial_leaning: treat Harness-1 as an interesting-but-external paper, file the memo, move on
relations:
  - type: depends_on
    target: 2026-05-26-cross-attestation-substrate-v2
---

# 2026-06-07: Adopt the state-externalization lens; scope inventory-before-dispatch as the first externalization

## Context
Harness-1 (arXiv:2606.02373) gives RL-grade evidence for a sharper version of Constitution Principle 1: move *recoverable bookkeeping* out of the policy into deterministic environment state; leave the policy only *semantic, non-recoverable* decisions. The load-bearing result for us is Appendix P / Fig 7: on a **fixed** model (GPT-5.4, zero retraining), swapping only the harness moves curated recall 0.511 (naive) → 0.807 (Context-1) → 0.849 (Harness-1). Harness quality is a compute-allocation lever *independent of training* — exactly the axis a prompt-only, no-training shop like agent-infra operates on. Full analysis: `research/2026-06-07-harness1-state-externalization.md`.

The fork: does this paper change anything we do, or is it just confirmatory reading?

## Alternatives considered
1. **File the memo, no action.** Cheapest. Cons: discards a directly-applicable, empirically-backed lens that sharpens a core principle and names a concrete fix we already know recurs.
2. **Adopt a diagnostic lens + scope ONE demand-cleared externalization (chosen).** Add a standing review question for new behavioral rules — *"is this rule asking the policy to hold recoverable state? Then it belongs in the harness, not the prompt"* — and scope "Inventory before dispatch" (documented to have failed twice as an instruction) as the first concrete policy→harness move. Pros: small blast radius, demand-gated, reversible. Cons: one more review heuristic to remember (mitigated: it's a question, applied only on rule-authoring).
3. **Mass-audit all instruction rules and convert the wrong-layer ones now.** Over-reach. Violates the Pre-Build / self-improvement gate (each candidate needs its own 2+-recurrence demand check). Most candidates (Recitation Before Reasoning, Post-Synthesis Completeness Check) are hypotheses, not recurring documented failures. Rejected.
4. **Build a general agent working-memory harness** (candidate pool / curated set / verification records) as shared scaffolding for Claude Code sessions. Heavy, speculative, no demand signal, and shared infra touching 3+ projects → hard autonomy limit. The paper externalizes state *for a trained retrieval policy over a corpus*; our agents are general frontier models over a filesystem — the components don't port 1:1. Rejected as speculative; revisit only on a measured demand signal.

## Counterevidence sought
- **Did "Inventory before dispatch" actually recur as a failure, or am I inventing demand?** The global subagent rules state it verbatim: *"Two confirmed incidents of 3+ subagents rediscovering completed work (~9M tokens wasted). The rule was in MEMORY.md and failed twice — this is the enforcement location."* Recurrence is documented, not hypothetical. Clears the self-improvement gate.
- **Is it already externalized?** Partially — `agentlogs` (FTS5 over all vendors) and `git log` hold the *data*, but nothing *renders* a dedup/inventory check into the dispatching agent's context at dispatch time. The agent must remember to query, which is the instruction-layer failure the paper predicts. Gap is real.
- **Does this rebuild anything vetoed?** Checked `vetoed-decisions.md`: not the knowledge-substrate MCP (that was a retrieval layer; this is a narrow pre-dispatch check), not `session_quality`, not repo-tools MCP. A pre-dispatch inventory hook is the *kind* of thing that already worked here (knowledge-index hook at 100% coverage beat the retrieved-substrate MCP). No conflict found.
- **Would the lens itself just be more "rules about rules" (which this repo's CLAUDE.md warns against)?** Risk acknowledged. Mitigated by scoping it as a *question asked at rule-authoring time*, not a new always-loaded rule body, and by pairing it with one concrete build rather than leaving it abstract.

## Decision
1. **Adopt the state-externalization lens** as a standing review question when authoring/reviewing any behavioral rule or Stop-hook advisory: *does this ask the policy to maintain recoverable state? If yes, the target is harness/scaffolding, not prompt text.* Lives with the self-improvement governance, not as a new auto-loaded rule.
2. **Scope (not yet build) "Inventory before dispatch" as the first externalization.** Design sketch below. Build is the next session's plan, gated on the scope holding up.
3. **Propose — do not apply — a one-line evidence addition to Constitution Principle 1** citing Harness-1's fixed-model harness lift (Appendix P) as the generalization/transfer data point SlopCodeBench lacks. Constitution is human-protected → awaits Markus's approval.

### Scoped externalization: inventory-before-dispatch
- **State to externalize:** the set of recently-completed / in-flight work relevant to a planned subagent dispatch (topic, touched paths, recent commits).
- **Where:** a `PreToolUse` check on the Agent/Task dispatch tool (the harness layer), not a prompt instruction. Reuses existing data sources (`agentlogs`, `git log --oneline`, grep) — no new store.
- **What the agent sees:** at dispatch, the harness renders a compact "already-covered" digest (matching recent commits + active-agent topics) into the tool result, so the dispatching policy makes the *semantic* keep/skip/refine decision with the bookkeeping already done — the `prune_chunks` pattern (policy judges, harness supplies the state).
- **Failure mode it kills:** 3+ subagents rediscovering finished work (~9M tokens, 2 incidents).
- **Explicitly NOT:** a retrieval MCP, a quality score, or a general working-memory store. One narrow pre-dispatch digest.

## Evidence
- `research/2026-06-07-harness1-state-externalization.md` — primary-source read of paper PDF + repo code.
- Harness-1 Table 3 (all-mechanisms-disabled −12.2% recall, same checkpoint) and Appendix P / Fig 7 (fixed-model +29.6 pts naive→structured, +4.2 pts top-harness, zero training).
- Cross-validates `decisions/2026-05-26-cross-attestation-substrate-v2.md`: killing the 0-invocation agent attestation ritual and moving it to the mutation gateway is the same policy→harness move.

## Revisit if
- The inventory-before-dispatch scope fails a probe (e.g. the digest is too noisy to be actionable, or agentlogs/git latency makes it stale at dispatch time) → drop to a lighter form or abandon.
- A *measured* demand signal appears for a broader working-memory harness (≥3 sessions where general agents lose track of curated findings across compaction in a way scaffolding would fix) → reopen Alternative 4.
- Markus declines the Constitution evidence addition → keep the lens as governance-only, no constitutional status.

## Implementation (2026-06-07, same session)
All three decision items shipped:
1. Constitution Principle 1 evidence addition — **applied** with Markus's explicit approval (agent-infra@4275b7a). Harness-1 Appendix P / Fig 7 cited as the fixed-model, zero-training harness-lift data point.
2. Inventory-before-dispatch — **built** (skills@a6a63b3, wired ~/.claude@c1ac097), not deferred. `~/Projects/skills/hooks/pretool-inventory-dispatch.py`: PreToolUse:Agent advisory, git-log-in-cwd topic match, gated to research/exploration dispatches, skips worktree, fails open, ~0.3s. v1 is git-log-only; agentlogs FTS is the measured v2 enrichment (a single term matched 34k events in the 11GB index → needs recent-run/task-message scoping before it's low-noise). Tests in `test_inventory_dispatch.py`. Logs under `inventory-dispatch` for ROI measurement (Principle 3).
3. Diagnostic lens — recorded here as the standing rule-authoring review question.

**Measurement window:** revisit after ~2 weeks of `inventory-dispatch` trigger logs. Promote (e.g. add agentlogs v2) if it surfaces real overlaps; demote/retune if it's noise like the brainstorm/single-tool nags the subagent-gate dropped (82 warns/3d, 0 effect).
