1. Executive Thesis

Using your repo digest as primary evidence and official platform/spec docs only for current-state checks: the next 6–12 months belong to hosted runtime commoditization, not bespoke agent theater.

Anthropic is already shipping most of the substrate people were hand-building recently: an Agent SDK that exposes Claude Code’s agent loop and tools, native web search/fetch/code execution, structured outputs, memory, hooks/permissions, skills, plugins, and a beta MCP connector. OpenAI and Google are moving in the same direction with built-in tools, background execution, compaction/long-context management, structured outputs, agent SDKs or agent surfaces, and native eval/trace features. Even tool discovery is becoming native. ￼

MCP matters, but the interesting parts are still wet cement. Streamable HTTP is real. Tasks are still explicitly experimental in the 2025-11-25 spec. Task Continuity is a draft proposal from March 3, 2026, and skills work is still interest-group/proposal territory rather than something you should build your house on. ￼

That means the custom layer whose job is “help the model search, fetch, run code, juggle context, and call tools” is getting eaten. The layer whose job is “bind the system to evidence, resolution, safe action, and correction propagation” is not. Capability-compensating scaffolding shrinks with model/runtime improvement. Governance/accountability scaffolding becomes more valuable as autonomy rises.

So the right next-generation architecture is:

thin execution fabric, thick epistemic kernel.

Unify meta, intel, research, genomics, and future selve around one shared contract for case → claim → evidence → commitment → resolution → score → policy update. Do not unify raw ontologies, raw storage, or resolver logic. One schema, many resolvers.

High confidence: native tools, structured outputs, compaction, background execution, and agent eval/trace surfaces keep expanding. Medium confidence: MCP task continuity and richer multi-round flows matter later this year. Low confidence: skills-over-MCP or memory interchange become stable enough soon to be a foundation.

2. What Gets Eaten vs What Persists

component current role likely fate in 3-12 months reason action
claude -p subprocess lane execution engine for local orchestrators mostly eaten native SDKs now expose the loop directly migrate
custom search / fetch / generic code-exec wrappers fresh info and commodity compute mostly eaten server-side tools are becoming standard substrate compress
ad hoc compaction / context-survival hacks keep long tasks alive largely eaten compaction and long-context controls are becoming native compress
local skill / command packaging reusable workflows partially eaten native skills/plugins will carry more of the wrapper compress
markdown frontmatter as machine state queues, joins, statuses, control info in prose dead brittle for validation, health checks, and correction propagation kill
separate ledgers for claims / predictions / resolutions fragmented learning surfaces dead as silos shared IDs and resolver contracts matter more than separate files compress
reflective multi-agent orchestration compensate reasoning limits mostly liability overhead dominates without independent verifiers kill
hooks / permission checks / advisories deterministic enforcement durable this is governance, not capability compensation keep
queue / scheduler / budget / approval layer control execution, cost, and autonomy durable but thinner providers can run agents; they cannot own your policy boundary keep
epistemic telemetry (trace-faithfulness, pushback-index, safe-lite-eval, etc.) audit behavior and output quality durable vendor evals will not know your domain semantics keep
entity graphs / anomaly scanners / domain scoring actual domain intelligence durable moat domain semantics and resolution logic are yours keep
trade_outbox and other propose-only boundaries safe side-effects more important, not less autonomy without an action boundary is cosplay keep
provider-native memory / auto-memory cross-session hints useful but non-authoritative soft context, vendor-specific, drift-prone monitor

The blunt cut: rent cognition plumbing, own correction plumbing.

3. Unifying Architecture

The shared algebra is not “tasks” and not “memory.” It is the resolvable commitment loop:

observation -> evidence -> claim/hypothesis -> commitment -> action proposal -> resolution -> score -> policy update

A claim is a proposition. A commitment is a claim you score, act on, or use to govern behavior later. A claim that never resolves and never controls action is prose, not state.

Use single-agent control loops by default. Subagents are allowed only at compression boundaries: parallel retrieval, extraction, or transformation tasks that produce typed artifacts with receipts. No parliament of ghost agents debating each other into a fog.

repo first-class commitment typical resolver
meta “hook/policy/evaluator X reduces error class Y” transcript analytics, canary suite, user corrections
intel forecast, thesis, trade proposal market outcomes, outbox execution, postmortems
research literature claim, thesis memo, open-question closure source verification, later evidence, manual adjudication
genomics pipeline conclusion, assay/variant hypothesis pipeline outputs, assays, curation, downstream evidence
selve decision or intervention hypothesis lived outcomes, journals, explicit feedback

Unify now: IDs, claim/commitment schema, evidence/source ledger, run receipts, outbox protocol, resolution state machine, scoring envelope, policy-promotion pipeline.

Keep separate: raw datasets, entity ontologies, resolver adapters, approval policies, domain scoring functions, physical storage.

Kill: duplicate ledgers, frontmatter state, open-ended reflective multi-agent machinery.

intel should be the first hard proving ground because it resolves faster than the others. Do not negotiate a universal schema in committee across all repos first. Use markets to break it.

4. Canonical Schema / Control Surface Proposal

Use append-only events underneath. Corrections append; they do not erase history. Materialize current views from those events.

case:
id
domain # meta | intel | research | genomics | selve
subject_ids[]
question
stakes
status

source:
id
kind # primary_doc | paper | web | dataset | market | self_report | assay
locator
captured_at
provenance_hash
default_grade

evidence:
id
case_id
source_id
claim_ids[]
polarity # supports | contradicts | null
excerpt_ref
grade
notes_ref

claim:
id
case_id
proposition
type # factual | causal | forecastable | policy_hypothesis
falsifiable
confidence
prior_class
status

commitment:
id
claim_id
kind # forecast | decision | plan | policy_hypothesis
confidence
horizon
preregistered_at
resolver_type
status

resolution:
id
commitment_id
outcome
resolved_at
resolver_ref
score

action_outbox:
id
commitment_id
channel # trade | writeback | alert | experiment | intervention
payload_ref
validation_hash
approval_state
execution_state

policy_delta:
id
derived_from # resolution / repeated error pattern
target # prior | hook | rule | skill | memory
delta
promotion_state

run_receipt:
id
case_id
provider
model
tools_used[]
artifacts_ref[]
trace_ref

What stays in markdown: narratives, memos, literature syntheses, preregistrations, postmortems, human argument, design notes. Markdown is the audit film, not the transaction log.

What becomes structured: IDs, statuses, timestamps, confidences, provenance pointers, source grades, resolution criteria, scores, queues, approval states, receipts.

How outcomes flow back:
resolution -> score -> prior-class update -> policy_delta candidate -> approve/reject -> hook/rule/skill/memory update

Soft memory should only hold hints. Hard behavioral changes belong in hooks, rules, outbox policy, or explicit priors. Anthropic’s own docs treat CLAUDE.md and auto-memory as context rather than enforced configuration; that is exactly why provider memory should be cache, not authority. ￼

Two control surfaces matter:

Execution controls: provider, model, effort, tool allowlist, MCP set, background flag, budget, sandbox.
Epistemic controls: verification threshold, source-grade floor, null-result requirement, disconfirmation requirement, preregistration requirement, action approval policy, promotion threshold.

5. Native-Leverage Strategy

Adopt native features where they collapse custom code without weakening receipts or boundaries. For Anthropic that means: use the Agent SDK as the first-class execution backend; use hooks/permissions for deterministic enforcement; use structured outputs for typed transport; use native web search/fetch/code execution for commodity retrieval and compute; use skills/plugins as packaging, not as the place truth lives. ￼

Defer building your core around MCP connector, MCP Tasks, or skills-over-MCP. Anthropic’s MCP connector is still beta, tool-call-only, remote HTTP/SSE only, and not ZDR-eligible. MCP Tasks are still experimental, and Task Continuity is still draft status. Skills-over-MCP is still exploratory. Provider memory also stays out of the authority path; it is soft context, not hard state. ￼

Hosted convenience also changes your data posture. Anthropic’s dynamic web fetch filtering relies on code execution and is not ZDR by default, and OpenAI background mode stores response data long enough to poll and is not ZDR-compatible. That means genomics and selve may keep more local execution than intel or generic research, even when native features exist. ￼

The migration path that avoids thrash: 1. Build a vendor-neutral RuntimeAdapter with capability flags: search, fetch, sandbox, structured_output, background, compaction, remote_mcp, soft_memory. 2. Swap execution engines behind that adapter. Start with meta and intel. 3. Keep receipts, outbox semantics, and policy gates unchanged. 4. Dual-run canaries on old subprocess path and new native path. 5. Retire custom wrappers only after parity on task success, epistemic metrics, and cost.

I would only move MCP Tasks from monitor to build-against after it exits experimental status and at least two real host/server stacks implement continuity sanely.

6. Epistemic Stack Strategy

Claim verification
Keep it. Trigger by stakes, novelty, or actionability. Do not verify every sentence like a deranged hall monitor. Verify the claims that can move capital, conclusions, or policy.

Source grading
Keep it and centralize it. Use one generic envelope plus domain adapters: primary/secondary, provenance completeness, recency, conflict risk, directness; then Admiralty for intel, study-design quality for research/genomics, self-report reliability for selve.

Null result tracking
Keep it and elevate it. null_result and pertinent_negative should be structured evidence types, not just advisory prose. This is one of the cheapest ways to reduce self-flattering nonsense.

Fold detection / sycophancy detection
Keep it, but stop worshipping pushback counts. Model commitment revisions as events: hold, fold, evidence_update, pressure_override. Pre-register positions where possible. Score changes by trigger.

Trace faithfulness
Keep it as receipt audit. Compare claimed tool/evidence use against actual run receipts. Do not chase inaccessible chain-of-thought. Faithfulness is observable at the interface.

Canary calibration
Keep it. Every provider/model/runtime migration should hit the same canary set: forecasts, evidence tasks, fold probes, verification tasks, and action-boundary tests. Native platforms are also productizing eval and trace surfaces, which is useful, but you still need your own canaries tied to real resolution. ￼

Process supervision / PRM-style evaluation
Do not build a grand learned PRM now. Research reasoning labels are too noisy. Use narrow process receipts instead: did search behavior match stated uncertainty? did the agent seek disconfirming evidence? was the resolution criterion defined before outcome? did the action remain inside the outbox? That is tractable. The giant universal reasoning overseer is nerd incense.

7. 30 / 90 / 180 Day Plan

30 days 1. Carve out a tiny shared epistemic-core package under meta or beside it: IDs, schema, receipts, resolution state machine. 2. Generalize trade_outbox into a typed action_outbox. 3. Move machine state out of markdown/frontmatter into SQLite operational tables; keep DuckDB for analytics where it already shines. 4. Unify intel claims, predictions, and resolutions under shared IDs and forecast classes. 5. Refactor meta evaluators (trace-faithfulness, pushback-index, safe-lite-eval, epistemic-lint) to read shared receipts and claim IDs. 6. Add RuntimeAdapter; pilot Claude Agent SDK alongside current subprocess execution.

90 days 1. Extend the same schema to research and genomics with domain-specific resolvers. 2. Add source ledger, null-result evidence, stance-revision events, and correction propagation. 3. Stand up a model/provider canary suite and make upgrades fail closed. 4. Route generic search/fetch/code through native tools with explicit allowlists and receipts. 5. Package repeated workflows as skills/plugins only after the underlying state/control path is stable. 6. Rebuild dashboards around resolved commitments, calibration, and correction propagation.

180 days 1. Bring selve onto the same loop as a slow, noisy, higher-approval resolver. 2. Expose stable domain services through your own gateway/MCP facade; keep protocol separate from semantics. 3. Pilot background/task-continuity features only behind the adapter and only if stability improves. 4. Retire remaining duplicate ledgers and old subprocess paths. 5. Decide which custom scaffolding still earns rent.

Kill list
• markdown-only machine state
• separate ledgers without shared IDs
• reflective multi-agent debate stacks
• homegrown generic search/fetch wrappers once native parity is proven
• pushback word counts as KPI

Don’t build this yet
• full skills-over-MCP dependency
• one mega ontology across all repos
• learned end-to-end PRM for research
• provider-native memory as truth store
• fully autonomous execution without outbox + approval policy

8. Failure Modes
   1. Building a universal agent brain instead of a shared commitment schema. Looks visionary. Produces glue code and fog.
   2. Treating vendor memory/skills/plugins as canonical state. Looks convenient. Buys silent drift and lock-in.
   3. Over-merging domains into one ontology or database. Looks elegant. Destroys resolver clarity. No cathedral linking stock tickers, assay results, and Tuesday moods.
   4. Letting markdown carry machine state because it feels auditable. Looks simple. Kills joins, validation, queues, and correction propagation.
   5. Optimizing citation counts, pushback rates, or benchmark scores instead of resolved error correction. Looks rigorous. Rewards theater.

9. Final Judgment

If I had to pick one controlling idea for the whole stack, it is this:

Build a commitment-resolution operating system.

A typed, resolvable commitment is the unit of durable intelligence. Claims, forecasts, policy hypotheses, and action proposals all collapse to that shape. Runtimes, models, tool APIs, skills packaging, and MCP transports will keep changing. Your commitments, resolvers, outboxes, receipts, and corrections are the durable layer.

⸻

A one-sentence governing principle

Own the typed commitment/resolution layer; rent the cognition/runtime layer.

A keep / compress / kill table

keep compress kill
action_outbox / approval boundaries execution engines via native SDKs markdown-only machine state
canonical claim/commitment schema search / fetch / generic code wrappers split ledgers without shared IDs
source ledger + null results skills/plugins as packaging reflective multi-agent debate
domain resolvers + scoring context/compaction hacks pushback-count metrics

A minimum shared schema sketch

case -> source -> evidence -> claim -> commitment -> resolution
\-> action_outbox
resolution -> score -> policy_delta
run_receipt attaches to every case/commitment run

Slightly less tiny:

case(id, domain, question, stakes, status)
source(id, kind, locator, provenance_hash, default_grade)
evidence(id, case_id, source_id, polarity, excerpt_ref, grade)
claim(id, case_id, proposition, type, confidence, prior_class, status)
commitment(id, claim_id, kind, confidence, horizon, resolver_type, status)
resolution(id, commitment_id, outcome, resolved_at, resolver_ref, score)
action_outbox(id, commitment_id, channel, payload_ref, approval_state, execution_state)
policy_delta(id, derived_from, target, delta, promotion_state)
run_receipt(id, case_id, provider, model, tools_used, trace_ref)

A 30 / 90 / 180 day action plan

30: land epistemic-core; generalize trade_outbox; move machine state into SQLite; unify intel IDs and forecast classes; refactor eval scripts onto shared receipts; pilot Agent SDK behind a runtime adapter.

90: extend schema to research and genomics; add source ledger, null-result evidence, fold/revision events, and correction propagation; stand up canaries; route commodity search/fetch/code to native tools; package repeated workflows as skills/plugins.

180: bring selve onto the same loop; expose stable services behind your own gateway/MCP facade; pilot background/task continuity only behind adapters; retire duplicate ledgers and leftover subprocess glue.

The single most dangerous architectural mistake to avoid

Confusing native runtime convenience with your system’s epistemic source of truth.

---

## Idea: Scite MCP for citation-stance search

**Source:** https://scite.ai/mcp — requires paid subscription.

**What it does:** Scite indexes 1.6B+ citations classified as *supporting*, *contrasting*, or *mentioning*. Their MCP exposes: literature search, Smart Citation data (stance-classified), citation tallies, DOI lookup, related articles.

**Unique capability vs current stack:** Citation stance classification. None of the current tools (S2, Exa, Brave, paper-search) can answer "which papers contradict this finding?" structurally. Currently this requires fetch_paper → ask_corpus with manual prompting, which is slow and incomplete.

**Where it fits:** Research repo’s disconfirmation mandate (Constitution §4). Literature audits, novelty audits, frontier refreshes. Also useful for the evidence.polarity field in the canonical schema — Scite’s supporting/contrasting/mentioning maps directly to supports/contradicts/null.

**Overlap:** Paper discovery, DOI lookup, related articles — all redundant with S2 and paper-search. Only the stance classification is new.

**Risk:** Coverage skews biomedical. Psychometrics, DIF, measurement invariance coverage likely thinner. Needs a trial run on actual research topics before committing to a subscription.

**Action:** Check if free tier or trial exists. Test queries on: "sex differences IRT DIF", "measurement invariance MTMM", "PISA mathematics gender". If stance-classified results are substantive, add to .mcp.json. If coverage is thin on our domains, skip.
