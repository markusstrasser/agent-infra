# Agent Observability / Eval / Gateway Dev-Tools Scout

**Date:** 2026-06-20  
**Window prioritized:** May 20-June 20, 2026  
**Sources:** Exa MCP primary; primary URLs only. No Brave used.

## Ranked Findings

### 1. Datadog Labs Trajectory
**URL:** https://github.com/datadog-labs/trajectory  
**Date:** created 2026-05-22; latest release v0.5.14 on 2026-06-19  
**Claim:** Local coding-agent observability for Claude Code, Codex, Cursor, Gemini, Pi, OpenCode, etc., with local timelines, Datadog LLM traces, metrics, and YAML “Markers.”  
**Demonstrated vs asserted:** Demonstrated repo, releases, docs, client plugin assets; adoption still tiny.  
**Maturity:** 4 stars; last push 2026-06-19; Apache-2.0.  
**Why it matters:** Best direct fit: local single-operator agent sessions become queryable traces and marker metrics without adopting a hosted multi-agent service.

### 2. Braintrust Topics GA
**URL:** https://www.braintrust.dev/blog/topics-ga  
**Date:** 2026-06-01  
**Claim:** Braintrust Topics is GA: continuously clusters production traces into Task/Issues/Sentiment/custom facets, writes SQL-queryable labels, and feeds datasets/evals/scorers.  
**Demonstrated vs asserted:** Product GA asserted by official blog; workflow and SQL examples shown; customer PR/day claims are vendor assertions.  
**Maturity:** SaaS feature; no repo stars applicable.  
**Why it matters:** The steal is not the SaaS, it is the pattern: trace cluster → label → promote cluster to regression dataset → scorer/gate.

### 3. HarnessFix / HTIR Paper
**URL:** https://arxiv.org/html/2606.06324v1  
**Date:** 2026-06-04  
**Claim:** Converts failed agent trajectories + harness code into a Harness-aware Trace IR, diagnoses harness-layer flaws, and applies scoped repairs; reports 15.2%-50.0% held-out gains.  
**Demonstrated vs asserted:** Paper evidence; results need replication.  
**Maturity:** arXiv:2606.06324v1.  
**Why it matters:** Strong conceptual blueprint for our session-trace layer: normalize traces into a typed IR before diagnosis, instead of reviewing raw transcripts.

### 4. Langfuse MCP Evaluator / Evaluation-Rule Tools
**URL:** https://github.com/langfuse/langfuse/releases/tag/v3.182.0  
**Date:** 2026-06-10  
**Claim:** Langfuse exposed unstable evaluator and evaluation-rule tools through MCP, plus fixes around trace-scoped observation eval jobs.  
**Demonstrated vs asserted:** Demonstrated in release notes and PR references.  
**Maturity:** 29K stars; release v3.182.0; last-push not exposed in release metadata.  
**Why it matters:** MCP-accessible eval primitives are worth copying locally: agent can inspect and manipulate eval rules as tools, not dashboard clicks.

### 5. Phoenix PXI Trace-Debugging / Span Annotation / Eval Harness Upgrade
**URL:** https://github.com/Arize-ai/phoenix/releases/tag/arize-phoenix-v16.4.0  
**Date:** 2026-06-01  
**Claim:** Phoenix added PXI agent features: trace debugging skill, span annotation tool, dynamic page-context actions, and eval harness with message history.  
**Demonstrated vs asserted:** Demonstrated release notes.  
**Maturity:** 10K stars; release v16.4.0; last-push not exposed in release metadata.  
**Why it matters:** Span annotation + message-history-aware evals map cleanly to local transcript review: annotate exact spans, not whole sessions.

### 6. LangSmith Pi Coding Agent Extension
**URL:** https://github.com/langchain-ai/langsmith-pi-extension  
**Date:** created 2026-06-01; last push 2026-06-17  
**Claim:** Traces Pi Coding Agent sessions into LangSmith with turns, tool calls, token usage, individual LLM invocations, metadata, and replica destinations.  
**Demonstrated vs asserted:** Demonstrated repo and README config.  
**Maturity:** 0 stars; last push 2026-06-17; MIT.  
**Why it matters:** Shows the extension pattern for coding-agent telemetry: per-client shim writes standardized traces; relevant to Claude/Codex/Cursor parity.

### 7. LangSmith Guided Tour / Online Evals Via Webhook
**URL:** https://github.com/langchain-samples/langsmith-guided-tour  
**Date:** created 2026-05-26; last push 2026-06-08  
**Claim:** New self-directed notebooks cover tracing, failure-mode discovery, offline evals, online eval run rules, annotation queues, and gateway policy.  
**Demonstrated vs asserted:** Demonstrated repo/notebook syllabus.  
**Maturity:** 0 stars; last push 2026-06-08.  
**Why it matters:** Useful as a checklist for our local harness: trace query DSL, online scorers, annotation queues, and gateway policies should be first-class workflows.

### 8. OpenLLMetry / Traceloop SDK v0.61.0
**URL:** https://github.com/traceloop/openllmetry/blob/HEAD/CHANGELOG.md#v0610-2026-05-31  
**Date:** 2026-05-31  
**Claim:** Added OpenAI Agents GenAI semantic-convention compliance, `responses.parse()` tracing, reasoning/cache token attributes, MCP protocol error attributes, and broader exception status handling.  
**Demonstrated vs asserted:** Demonstrated via release notes surfaced in downstream dependency PRs.  
**Maturity:** traceloop-sdk v0.61.0; repo stars/last-push not returned by Exa result.  
**Why it matters:** Standards substrate: local traces should preserve MCP tool errors, structured-output parsing, reasoning-token/cached-token fields.

### 9. Azure AgentOps Accelerator v0.3.x
**URL:** https://github.com/Azure/agentops/commit/ba4fe4e86f92d2ce1d19fccd314e15f43b7c2823  
**Date:** 2026-06-01  
**Claim:** Adds preflight RBAC for eval runs and distinguishes grader execution errors from quality-gate failures.  
**Demonstrated vs asserted:** Demonstrated commits, changelog diffs, unit-test additions.  
**Maturity:** 8 stars; active June 2026 commits.  
**Why it matters:** Steal the error taxonomy: eval gate failure must separate “grader could not execute” from “agent quality failed.”

### 10. Helicone Tiered Cost Tracking Fixes
**URL:** https://github.com/Helicone/helicone/pull/5691  
**Date:** 2026-06-06  
**Claim:** Fixes tiered pricing for OpenAI/Azure/OpenRouter/Helicone providers where long-context requests were under-costed.  
**Demonstrated vs asserted:** Demonstrated PR with concrete before/after math; PR was open in Exa result.  
**Maturity:** 6K stars; PR open as of 2026-06-06 result.  
**Why it matters:** Local cost dashboards need model-tier-aware cost logic; otherwise eval/runtime “cost regressions” are false.

## Dropped / Low Relevance

AgentOps-AI hosted product did not surface credible new primary May-June 2026 changes in this pass; Exa mostly found Azure’s separate AgentOps Accelerator.  
Generic buyer guides and comparison posts were not used as findings.  
Pre-2026 staples were skipped unless there was a concrete 2026 release.

## TOP STEALS

1. Build a local trace IR: session → turn → tool/span → error/cost/eval labels, then diagnose against that, not raw logs.  
2. Add trace-cluster-to-regression flow: recurring failure cluster becomes dataset row plus scorer/gate.  
3. Treat eval failures as typed: quality regression, grader execution error, auth/config error, stale cost model.