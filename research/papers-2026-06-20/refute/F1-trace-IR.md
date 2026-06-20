**F1 Adversarial Review**

Overall: **F1 survives only as a modest local forensic projection, not as “HTIR gains transferred to session-trace.”** The strongest correction is to split the claim: HTIR supports a typed trace diagnostic substrate; the 15.2-50.0% gains belong to the full HarnessFix loop with diagnosis agents, scoped repair operators, patch generation, validation-set acceptance, and enough failed trajectories.

1. **2606.06324 HTIR / HarnessFix — VERDICT = NARROW**

Strongest objection: HTIR really does define `TraceStep` plus provenance/control-flow/artifact-state evidence, but the paper’s gains are not from “compile transcripts into typed IR” alone. The paper’s own method is four LLM agents plus harness-code access, repair specs, candidate patches, validation splits, regression bounds, and harness memory; the held-out gains are for full HarnessFix, not the IR substrate by itself ([txt](</Users/alien/Projects/agent-infra/research/papers-2026-06-20/txt/2606.06324.txt:203>), [results](</Users/alien/Projects/agent-infra/research/papers-2026-06-20/txt/2606.06324.txt:921>)).

Correction: rewrite F1 “Measured” to: “HarnessFix reports 15.2-50.0% held-out gains for a full repair loop; the typed IR ablation shows trace-grounded diagnosis contributes but does not isolate the IR alone.” Add preconditions: rich tool/env logs, harness-code access, recurring failures, held-out validation tasks, and recomputable target-flaw metrics.

2. **2605.01920 ACDL — VERDICT = NARROW**

Strongest objection: ACDL is a descriptive language for LLM context windows, not a diagnostic trace IR. The paper explicitly says it does not describe state production, agentic logic, tool implementations, retrieval, or model behavior, and it leaves provider `tools` fields outside the formal language ([txt](</Users/alien/Projects/agent-infra/research/papers-2026-06-20/txt/2605.01920.txt:287>)). Its empirical evidence is a small GPT-4-Turbo MINT appendix, with the authors noting stronger models were largely insensitive on that benchmark ([txt](</Users/alien/Projects/agent-infra/research/papers-2026-06-20/txt/2605.01920.txt:791>)).

Correction: keep ACDL only as support for a `context_shape` subview inside `session-trace`, not as evidence for full typed execution IR or held-out diagnostic gains.

3. **2606.11213 pi-CWL — VERDICT = NARROW**

Strongest objection: CWL’s mechanism depends on live agent-authored episode boundaries and explicit dependency declarations through a delimiter tool, plus host-level token accounting and context eviction. The paper says the alternative, inferring structure post-hoc, is exactly what makes compaction fragile; our offline agentlogs projection lacks the paper’s core precondition unless future harnesses emit those annotations live ([txt](</Users/alien/Projects/agent-infra/research/papers-2026-06-20/txt/2606.11213.txt:214>), [limits](</Users/alien/Projects/agent-infra/research/papers-2026-06-20/txt/2606.11213.txt:382>)).

Correction: in F1, describe CWL-derived edges as “inferred forensic hints, not causal ground truth.” Do not cite CWL as support for reliable dependency edges unless the local harness adds explicit episode/dependency emission.

4. **2606.12329 PROJECTMEM — VERDICT = NARROW**

Strongest objection: PROJECTMEM supports typed event logs and deterministic pre-action warnings, but it is not evidence for a general session-trace IR. Its event types are coarse project-memory records (`issue`, `attempt`, `fix`, `decision`, `note`) and its measured evidence is usage/self-study plus token estimates, not demonstrated diagnostic accuracy or failures prevented ([txt](</Users/alien/Projects/agent-infra/research/papers-2026-06-20/txt/2606.12329.txt:292>), [evidence caveat](</Users/alien/Projects/agent-infra/research/papers-2026-06-20/txt/2606.12329.txt:561>), [limits](</Users/alien/Projects/agent-infra/research/papers-2026-06-20/txt/2606.12329.txt:695>)).

Correction: move PROJECTMEM out of F1’s “typed IR” evidence and cite it under F2/F3: typed failure/fix projection plus pre-action gate with raw trace backlinks.

5. **2605.26494 MiniMax-M2 — VERDICT = REFUTED**

Strongest objection: The plan smuggles in MiniMax as if `(state, action, observation, artifact, reward)` were a local trace-IR mechanism. In the paper, that tuple is an RL training MDP abstraction for model training at scale, with the LLM policy optimized over state/action pairs; it is not a proposed diagnostic IR for a single-operator Claude/Codex/Cursor harness ([txt](</Users/alien/Projects/agent-infra/research/papers-2026-06-20/txt/2605.26494.txt:1235>)). Black-box support still assumes collection of exact request-stream training tuples into an RL service, not just post-hoc transcript analysis ([txt](</Users/alien/Projects/agent-infra/research/papers-2026-06-20/txt/2605.26494.txt:1531>)).

Correction: remove MiniMax from F1 support. At most cite it elsewhere as weak background for “artifact-aligned rewards and exact request-stream logging matter,” not as evidence for session-trace typed IR.

**Required Plan Fix**

Change F1 from “5-way triangulated typed IR with HTIR gains” to:

“HTIR is the only direct support for a diagnostic typed trace IR. ACDL supports context-shape rendering; CWL supports live episode annotations but only if emitted explicitly; PROJECTMEM supports typed failure/fix memory events; MiniMax does not support this bolt-on except as distant RL vocabulary. Build F1 as a minimal derived forensic view, label inferred edges, and do not claim paper-reported gains until a local predict-then-falsify eval shows the mechanism fired.”