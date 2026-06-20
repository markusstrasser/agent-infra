**L2 Adversarial Review**

Target claim: [research/2026-06-20-paper-integration-plan.md](/Users/alien/Projects/agent-infra/research/2026-06-20-paper-integration-plan.md:97) says L2 should build local harness-eval lanes with env-grounded verifiers, held-out traces, token cost, and a model-by-harness grid, using these papers as templates.

**2601.11868 Terminal-Bench — VERDICT: NARROW**

Strongest objection: Terminal-Bench supports final-state, executable, containerized task evaluation, but only for tasks with objective tests, oracle solutions, dummy-fail checks, reproducible Docker state, repeated trials, and substantial audit effort. The plan overgeneralizes if it treats this as support for all local harness behavior evals, especially subjective/trace-behavior lanes like over-ask or governance quality where there may be no oracle final-state verifier.

Concrete correction: Rewrite its role as: “Terminal-Bench template applies only to local terminal tasks with executable verifiers; require oracle-pass, dummy-fail, anti-cheat audit, and repeated runs before admitting a task.”

**2605.10912 WildClawBench — VERDICT: NARROW**

Strongest objection: The model-by-harness claim is real but easy to misuse. WildClawBench compares OpenClaw, Claude Code, Codex, and Hermes inside pinned Docker images and a controlled tool-facing environment; it shows model capability is entangled with runtime/scaffold, not that a single-operator local Claude/Codex/Cursor setup can produce fair harness rankings without equalized permissions, tools, secrets, context policies, versions, and timeouts. It also does not cover Cursor, and its GPT-judge validation is narrow.

Concrete correction: Replace “model×harness grid” with “model-runtime pairing grid”; require a recorded capability envelope for each harness and report results as pair-specific, not intrinsic model or harness rankings. Add Cursor only as a local harness under test, not as paper-backed prior art.

**2606.09426 WeaveBench — VERDICT: NARROW**

Strongest objection: WeaveBench does support trajectory-aware, per-clause evidence judging and nine shortcut detectors, but its mechanism depends on hybrid GUI+CLI tasks, screenshot/action traces, isolated judge subprocesses, inspection tools, and Linux desktop state. In agent-infra’s mostly CLI/file-bus/local trace harness, reproducing their trajectory-aware judge is not automatic; the transferable idea is clause-to-evidence trace auditing, not their full GUI-heavy cheat catalog or channel non-substitutability claim.

Concrete correction: Change the plan to “build a local trace-aware verifier with per-claim evidence anchors and a locally derived shortcut catalog.” Only include WeaveBench’s GUI/screenshot detectors in lanes that actually capture GUI/browser evidence.

**2606.05342 SentinelBench — VERDICT: NARROW**

Strongest objection: SentinelBench supports a narrow wait-vs-poll eval pattern, not general harness evaluation. Its mechanism relies on deterministic synthetic web environments, scheduled events, SQL success queries, no-op tasks, and optional self-reported cost; the `wait_for` tool is a text-diff plus LLM condition judge and sometimes trades reaction time for lower cost. The plan should not let this paper justify broader `/eval` lanes beyond long-running monitoring behavior.

Concrete correction: Scope SentinelBench to one lane: “file-bus/session-log wait-vs-poll monitoring tasks with deterministic event schedules, no-op controls, success/reaction/cost metrics, and deterministic watchers before any LLM condition judge.”

**2606.20408 NRT-Bench — VERDICT: NARROW**

Strongest objection: NRT-Bench’s strongest contribution is objective simulator-derived harm plus fixed paired replay. That only transfers if the local eval has a recomputable objective outcome; historical agentlogs and human corrections are not equivalent to a simulator unless replay changes can be causally scored under the new harness. The plan risks smuggling in “objective-sim > LLM judge” for agent-infra traces that may only have retrospective labels or partial human judgments.

Concrete correction: Cite NRT only for fixed paired replay and objective-outcome scoring where a deterministic verifier/simulator exists. For historical traces, call them regression fixtures with observed labels, not objective simulations, unless the lane can recompute pass/fail from local state.

**Bottom Line**

No paper fully refutes L2, but all five constrain it. The faithful integration is not “build a broad benchmark because papers say evals work”; it is: build small local lanes only when each task has a declared verifier class, captured capability envelope, repeated-run protocol, cost accounting, and a clear separation between objective final-state checks, trace-aware proxy judging, and retrospective human-labeled fixtures.