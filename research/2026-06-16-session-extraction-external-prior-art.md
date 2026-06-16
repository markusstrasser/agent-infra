# Session-Transcript Extraction: External Prior Art (2025–2026)

> Completed 2026-06-16. Researcher dispatch.

**Question:** What to extract from a corpus of AI-agent session transcripts/traces,
and how, to make the agent system better over time. **Hard constraint: we have
TRANSCRIPTS ONLY** (3.8 GB cross-vendor session DB: Claude/Codex/Cursor — full
event text, tool calls, git linkage). **No model internals / activations** (closed
APIs). The internals-vs-transcripts axis is the load-bearing filter throughout.

**Frontier-timeliness note:** behavioral properties move per-release; all primary
anchors below are 2025–2026. Pre-2025 work flagged. The METHOD transfers even when
the RATE doesn't (per global frontier rule).

---

## Axis 1 — Steering / activation / persona vectors from behavioral data

**Verdict: does NOT transfer to transcripts-only. These are activation-space
methods; they need model internals (open weights or at minimum residual-stream
access). What DOES transfer is the contrastive-prompt + behavioral-rubric
*protocol*, not the vector.**

| Method | What it extracts | Input needed | Maturity | Transfers to transcripts-only? |
|---|---|---|---|---|
| **Persona Vectors** (Anthropic, arXiv [2507.21509](https://arxiv.org/pdf/2507.21509); [anthropic.com/research/persona-vectors](https://www.anthropic.com/research/persona-vectors)) | A linear direction in activation space per trait (evil, sycophancy, hallucination, etc.); used to MONITOR drift + PREDICT/control trait shifts during training | **Internals.** Pipeline: auto-generate contrastive system-prompt pairs + eval questions + rubric, run model under +/- prompts, **diff mean residual-stream activations** | High (Anthropic, frontier-current) | **No for the vector.** Yes for the *generation pipeline*: the contrastive-prompt-pair + auto-rubric + behavioral-grading half is 100% transcript/API-derivable |
| **Contrastive Activation Addition (CAA)** (Rimsky et al., arXiv [2312.06681](https://arxiv.org/abs/2312.06681), 797 cites) | Steering vector = mean activation diff between +/- example pairs | **Internals** (residual stream) | Foundational (2023, pre-frontier but mechanism-robust; the lineage all 2025 work builds on) | No (needs activations) |
| **Role Vectors** (Potertì et al., arXiv [2502.12055](https://arxiv.org/abs/2502.12055)) | 29 role vectors from internal states; alternative to persona prompting | Internals | Low-med (2025) | No |
| **Feature Guided Activation Additions** (Soo et al., arXiv [2501.09929](https://arxiv.org/abs/2501.09929), 33 cites) | SAE-feature-guided steering, more interpretable/precise | Internals + SAE | Med (2025) | No |
| **Persona Vectors in Games** (Sun & Zhang, arXiv [2603.21398](https://arxiv.org/html/2603.21398), 2026) | Behavioral trait vectors (altruism, forgiveness) in game-theoretic settings | Internals | Low (2026) | No, but shows traits ARE measurable behaviorally |
| **Transmuting prompts into weights** (Mazzawi et al., arXiv [2510.08734](https://arxiv.org/abs/2510.08734)) | Converts a prompt into an equivalent weight/activation update | Internals | Low (2025) | No |

**The transfer reframe for us:** We cannot compute a steering *vector*. But the
upstream half of the persona-vectors pipeline — auto-generate contrastive
prompt pairs, run them, **grade behavior with a rubric** — is exactly a
transcript-graded behavioral eval. Black-box "steering" against closed APIs in
2025 is surrogate-model / prompt-engineering ([FlippedRAG](https://www.emergentmind.com/topics/black-box-persona-manipulation)),
not vector arithmetic. So the actionable residue from Axis 1 is: **trait
monitoring as a behavioral classifier over our transcripts** (is the agent
drifting sycophantic / hallucinating / apathetic across sessions?) — Anthropic
even frames persona vectors as a *deployment-time MONITORING* tool, and the
monitoring signal (trait present in output) is transcript-observable even though
the vector is not. This is the one piece of Axis 1 worth building, and it's a
classifier/projection, not steering.

---

## Axis 2 — Reasoning / decision / rationale extraction from traces

**Verdict: transcripts-only NATIVE. This is LLM-as-judge structured extraction
over the trace text — exactly what we can do. Mature pattern, watch for judge
bias.**

- **Structured extraction via LLM-judge DAGs** ([Confident AI guide](https://www.confident-ai.com/blog/why-llm-as-a-judge-is-the-best-llm-evaluation-method)):
  organize extraction as a DAG where each node is a judge handling one decision
  (extract items, detect echoing, position-in-list, "did this argument cause a
  decision change?"). Directly applicable: extract decisions + alternatives +
  why-nots as typed fields per session. Our repo already mirrors this with
  `Rejected:` commit trailers and decision-journal frontmatter — extraction
  would BACKFILL these from raw traces.
- **Reasoning-tree auditing** (Auditing Multi-Agent Reasoning Trees, arXiv
  [2602.09341](https://arxiv.org/html/2602.09341v1)) — auditing the reasoning
  structure outperforms majority-vote and flat LLM-as-judge. Signal: don't grade
  the final answer; extract and grade the *decision tree* (branches considered,
  pruned).
- **Caveat (frontier rule):** judges have measurable position/length/self-
  preference bias — see our own `research/2026-06-11-frontier-judge-bias-measured.md`
  and [2509.03647](https://arxiv.org/abs/2509.03647) (activation mitigation of
  self-preference, internals-only so not for us). Mitigation that DOES transfer:
  blind IDs, controlled length ratios, cross-model judge.

What to extract: per-session **decision records** (the choice, alternatives
considered, why-not, what evidence moved the agent) — the raw material our
decision-journal and `Rejected:` trailers want but currently depend on the agent
remembering to write. The corpus already has git linkage, so decisions can be
joined to their resulting commit/diff.

---

## Axis 3 — Failure / mistake / correction mining

**Verdict: transcripts-only NATIVE and the HIGHEST-yield axis for us. Active,
well-benchmarked 2025 subfield. Our git linkage + cross-vendor breadth is a
genuine edge here.**

| Method | What it extracts | Input | Maturity | Notes |
|---|---|---|---|---|
| **Who&When / "Which Agent Causes Task Failures and When?"** (Zhang et al., arXiv [2505.00212](https://arxiv.org/abs/2505.00212), **93 cites**) | Automated **failure attribution**: which agent + which STEP caused failure. Defines the task + benchmark | Transcripts (conversation logs) | High, foundational for the subfield | Step-level accuracy is HARD (<17% baseline) — see below |
| **AgenTracer** (arXiv [2509.03312](https://arxiv.org/abs/2509.03312), 51 cites) | Failure-inducing agent/step in agentic systems | Transcripts | High | |
| **Abduct-Act-Predict (AAP)** (arXiv [2509.10401](https://arxiv.org/abs/2509.10401)) | Causal scaffolding for failure attribution; lifts step-level accuracy above the <17% pattern-matching floor | Transcripts | Med | The "naive judge over long logs fails; add causal structure" lesson |
| **GraphTracer** (arXiv [2510.10581](https://arxiv.org/abs/2510.10581)) | Graph-guided root-cause tracing when errors propagate across turns | Transcripts | Med | Error-propagation modeling |
| **Spectrum-analysis attribution** (arXiv [2509.13782](https://arxiv.org/abs/2509.13782), 21 cites) | Failure attribution via spectrum analysis on Who&When | Transcripts | Med | |

**Key lesson for us:** naive LLM-as-judge over long logs gets <17% step-level
attribution — the field's fix is *causal/graph structure over the trace*, not a
bigger model. Our differentiator: **git linkage = a ground-truth verifier the
academic benchmarks lack.** "What the human had to fix" is recoverable from the
diff between agent-produced state and the next human commit. This is the
supervision-mining signal our own constitution's declining-supervision objective
needs (blindspot-miner, supervision-kpi already gesture at this). Failure mining
+ git ground truth is the place where transcripts-only is a STRENGTH, not a
limitation.

---

## Axis 4 — Experience / skill distillation from traces

**Verdict: transcripts-only NATIVE. This is the richest 2025–26 subfield and the
one the framing names (ACE). High value, but watch context-collapse / brevity-
bias failure modes that the field already documented.**

| Method | What it extracts | Input | Maturity | Notes |
|---|---|---|---|---|
| **ACE — Agentic Context Engineering** (Zhang et al., arXiv [2510.04618](https://arxiv.org/abs/2510.04618), ICLR 2026; code [github.com/ace-agent/ace](https://github.com/ace-agent/ace)) | Contexts as evolving **playbooks**: generate → reflect → curate strategies via **structured INCREMENTAL deltas** (not full rewrites) | Transcripts + task feedback | High (ICLR'26, named in our framing) | +10.6% agents / +8.6% finance; ReAct+ACE 59.4% ≈ IBM CUGA 60.3% on AppWorld with a smaller model. **Two named failure modes to design against: brevity bias (drops domain insight for concise summaries) and context collapse (iterative rewrite erodes detail).** Append-incremental, not rewrite — aligns with our append-only constitution |
| **Self-Generated In-Context Examples** (Sarukkai et al., arXiv [2505.00234](https://arxiv.org/abs/2505.00234), 16 cites) | Agent's OWN successful trajectories → in-context examples for future tasks; no task-specific engineering | Transcripts (own rollouts) | Med-high | The cleanest "trajectory → reusable example" recipe; transcript-native |
| **Trajectory-Informed Memory Generation** (Fang et al., arXiv [2603.10600](https://arxiv.org/abs/2603.10600), 2026, 6 cites) | Memory items from execution traces so agents stop repeating inefficient patterns / recover from prior errors | Transcripts | Med (2026) | Directly the "learn from our own session corpus" framing |
| **Audited Skill-Graph Self-Improvement** (Huang & Huang, arXiv [2512.23760](https://arxiv.org/abs/2512.23760), 2025) | Skill graph + experience synthesis + continual memory, gated by **verifiable rewards** | Transcripts + verifier | Med | "Audited"/verifiable-reward gating matches our verifier-conditioned autonomy |
| **CLEANER — Self-Purified Trajectories** (arXiv [2601.15141](https://arxiv.org/abs/2601.15141), 2026) | Filters noisy/failed trajectories before learning from them | Transcripts | Med | Trajectory QUALITY filter — don't distill from junk |
| **Datarus-R1** (arXiv [2508.13382](https://arxiv.org/abs/2508.13382)) | Trains on full analytical TRAJECTORIES (reasoning+code+correction), not Q-A pairs | Trajectories → training data | Med | The "trajectory → fine-tune data" path (needs training, not our default) |
| **Voyager (lineage)** — skill library of reusable code from agent experience (2023, pre-frontier; cited as the ancestor) | Executable skills accumulated from successful runs | Transcripts + env | Foundational | The ancestor of skill-library distillation; mechanism transfers |

**Key lesson:** the field has converged on **incremental, structured, append-not-
rewrite** context evolution (ACE) + **quality-filtering trajectories before
distilling** (CLEANER) + **verifier-gated** skill accretion. Distilling
successful trajectories into reusable skills/examples is the highest-upside use
of a session corpus — but only over trajectories a verifier blessed (we have
git/tests as that verifier). This is the constructive twin of Axis 3.

---

## Axis 5 — Agent observability / telemetry projection systems (what production projects out of traces)

**Verdict: this is the SCHEMA layer. The industry has standardized on
OpenTelemetry GenAI semantic conventions — adopt the schema vocabulary, don't
reinvent span/attribute names.**

**The standard (adopt this):** **OpenTelemetry GenAI Semantic Conventions**
([gen-ai-agent-spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/),
[gen-ai-spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/),
[attribute registry](https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/)).
Defines `gen_ai.*` attributes: `gen_ai.agent.{id,name,description}`,
operation/tool spans, session-level metrics, `gen_ai.provider.name` as the
format discriminator. Adopted by Datadog/Honeycomb/New Relic; emitted natively
by LangChain/CrewAI/AutoGen. Arize Phoenix uses **OpenInference** conventions on
top of OTel. **For us: map our cross-vendor event text into these attribute
names so projections speak a standard vocabulary** (and so anything we build is
portable).

**What production platforms PROJECT out of a trace corpus** (the view catalog to
copy):

| Tool | What it extracts/projects | Relevant pattern for us |
|---|---|---|
| **LangSmith** ([comparison](https://anudeepsri.medium.com/langsmith-vs-arize-vs-braintrust-e397e4728a76)) | **Topic clustering** (auto-categorize behaviors), **insights agent** that prioritizes improvements by **frequency × impact** | The frequency×impact ranking = our constitution's "recurs 2+ sessions → becomes a rule" rendered as a projection |
| **Arize Phoenix** ([latitude](https://latitude.so/blog/best-ai-agent-observability-tools-2026-comparison)) | OTel/OpenInference-native; 50+ metrics (faithfulness, relevance, safety, toxicity, hallucination); **trajectory analysis, trace clustering, anomaly detection** | Trace clustering + anomaly detection over OUR corpus = surfacing outlier sessions |
| **Braintrust** ([guide](https://www.braintrust.dev/articles/best-llm-tracing-tools-2026)) | **Trace-to-eval**: production failures auto-become eval cases; CI gates | "Failure → eval case" pipeline = our Axis-3 failures → regression tests |
| **AgentOps / MLflow** ([mlflow](https://mlflow.org/top-5-agent-observability-tools/)) | Session replay, cost/latency rollups, step-level spans | Standard rollup views |

**Key lesson:** production systems converge on (a) the OTel `gen_ai.*` schema,
(b) **clustering** (topic/behavior/trajectory), (c) **anomaly/outlier
detection**, (d) **frequency×impact ranking** of issues, and (e)
**failure→eval-case** promotion. We already have several of these in spirit
(improvement-log frequency rule, blindspot-miner, audit-corpus-sync); the gap is
a standard schema and the clustering/anomaly projections.

---

## SYNTHESIS — What's worth extracting from a transcripts-only corpus, ranked by value/feasibility

Ranking axis = (value to the declining-supervision objective) × (feasibility
given transcripts-only + our git linkage). Our git/test linkage is the
differentiator: it gives a ground-truth VERIFIER the academic transcript
benchmarks lack, which is exactly what turns several "noisy LLM-judge" methods
into reliable extractors.

**TIER 1 — build these (transcript-native, high value, we have the verifier):**

1. **Failure + human-correction mining with git ground truth** (Axis 3). Extract
   per-session: where the agent erred, what the human had to fix (diff between
   agent state and the next human commit), error category. This IS the
   declining-supervision signal. Method: causal/graph-structured attribution
   (Who&When/AAP/GraphTracer lineage), NOT flat LLM-judge (<17% floor). Git
   linkage = the verifier the benchmarks wish they had. **Highest ROI.**

2. **Verifier-gated skill / playbook distillation from successful trajectories**
   (Axis 4). Distill blessed (test-passing / committed-and-not-reverted)
   trajectories into reusable skills/examples. Use **ACE's incremental-delta,
   append-not-rewrite** discipline (avoids brevity-bias + context-collapse;
   matches our append-only constitution) and **CLEANER's** trajectory
   quality-filter (don't distill from junk). Constructive twin of #1.

3. **Decision / rationale extraction → backfill decision records** (Axis 2).
   LLM-judge DAG extracting (decision, alternatives, why-not, evidence-that-
   moved-it), joined to the resulting commit. Backfills our `Rejected:` trailers
   and decision-journal from raw traces. Cheap, native, immediately useful.

**TIER 2 — adopt the schema + projections (medium value, mostly plumbing):**

4. **OTel GenAI `gen_ai.*` schema mapping** (Axis 5). Map cross-vendor events to
   the standard attribute vocabulary so every projection is portable and we stop
   inventing span names. Prerequisite for clean #5/#6.

5. **Frequency × impact issue ranking** (Axis 5, LangSmith pattern). Render the
   constitution's "recurs 2+ sessions → rule" as a standing projection over the
   failure-mining output from #1. We have the rule; make it a view.

6. **Behavioral / trace clustering + anomaly detection** (Axis 5, Phoenix
   pattern). Cluster sessions by behavior; surface outliers. Cheap with
   embeddings we already have; good for "what's weird this week."

**TIER 3 — monitor only, don't try to replicate the mechanism:**

7. **Trait/persona drift MONITORING as a behavioral classifier** (Axis 1, the
   ONLY transferable piece). We cannot compute steering vectors (need internals).
   But the persona-vectors *monitoring* framing transfers: a classifier over
   transcripts for sycophancy/hallucination/apathy drift across sessions. Reuse
   the contrastive-prompt + rubric *protocol*, drop the activation diff. Lower
   priority — overlaps existing sycophancy work; build only if drift is observed.

**DO NOT BUILD:** activation/persona/role steering vectors, CAA, SAE-feature
steering, prompt→weight transmutation (Axis 1 mechanisms) — all require model
internals we do not have on closed Claude/Codex/Cursor APIs. The vector is
unreachable; only the behavioral protocol and the monitoring signal transfer.

**Cross-cutting design rules the field already learned (free lessons):**
- Flat LLM-judge over long logs is weak (<17% step attribution) → add causal/
  graph structure (AAP, GraphTracer).
- Context evolution must be incremental + append-not-rewrite → brevity bias and
  context collapse are real, documented failure modes (ACE).
- Filter trajectory quality before distilling (CLEANER).
- Judges carry position/length/self-preference bias → blind IDs, controlled
  ratios, cross-model judge (matches our existing judge-bias memo).
