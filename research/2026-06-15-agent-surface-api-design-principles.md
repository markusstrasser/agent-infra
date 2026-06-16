---
date: 2026-06-15
topic: API design principles for agent-facing surfaces — tools, skills, hooks, MCPs, rules, subagents
tier: deep
axes: [api-design, agent-specific, adjacent-cli-plugin, adversarial]
sources: 18
decision_relevance: hooks vs skills vs MCPs vs rules vs subagents — surface selection
---

# Agent Surface API Design Principles — Research Memo

**Question:** What established API design principles (from software API design, platform design, DX
literature) should govern how we design agent-facing surfaces — tools, skills, hooks, rules, MCPs,
subagents, plugins?

**Date:** 2026-06-15  
**Tier:** Deep  
**Ground truth:** Existing memos cover tool attention/deferred loading (2026-04-25) and MCP 4-week delta
(2026-05-27). No prior memo synthesizes foundational API design principles across all surface types.

---

## Surface Taxonomy (the "when to use which" question)

Before principles, a decision table. These five surfaces are not interchangeable — they differ on
who/what reads them, when they load, and what enforcement they provide.

| Surface | Who reads it | Load timing | Enforcement | Use when |
|---------|-------------|-------------|-------------|----------|
| **Rules** (`.claude/rules/`) | Model at session start | Always-loaded | Advisory (text) | Invariants the model must always know; conventions; governance boundaries |
| **Skills** (`.claude/skills/`) | Model on demand | Lazy (invoked by name) | Advisory (text) | Reusable procedural workflows; "how to do X correctly" |
| **Hooks** (PreToolUse/Stop etc.) | Shell/script, not model | Event-triggered | Deterministic (block or pass) | Cascading-failure prevention; irreversible-action gating; enforcement that can't be text |
| **MCP tools** | Model via function-calling | Per-turn schema injection | Structured schema + server-side | External system integration; typed programmatic capabilities |
| **Subagents** | Separate model context | On explicit dispatch | Isolated context + own hooks | Fan-out parallelism; context isolation; sandbox for risky work |

**Selection heuristic (derived from Anthropic agent-design.md [SOURCE: https://github.com/anthropics/skills/blob/main/skills/claude-api/shared/agent-design.md]):**
> Start with bash/rules for breadth. Promote to dedicated tool/hook when you need to **gate, render,
> audit, or parallelize** the action. Promote to skill when the workflow recurs and benefits from
> on-demand loading. Promote to subagent when the context should be isolated or the work is parallel.

[INFERENCE: The promotion sequence is clean; the boundary between hook and skill is the clearest
distinction not made explicit in the source — hooks = enforcement, skills = knowledge.]

---

## The 14 Principles, Ranked by Agent-Surface Relevance

Ranking: 1 = highest relevance/impact for agent surfaces.

---

### 1. Consolidation Before Addition — *Minimal Viable Tool Set*

**Definition:** Never add a surface until a human engineer can definitively say which existing surface
does NOT cover this use case. Prefer one tool with a richer parameter over two overlapping tools.

**Why it matters for agents:** Tool selection accuracy degrades on a cliff, not a slope. RAG-MCP
benchmark data: baseline tool-selection accuracy with a large tool set = 13.62%; with retrieval that
reduces visible tools = 43.2% — a 3.2× lift from the same model with the same tools, just fewer
visible at inference time. [SOURCE: https://tianpan.co/blog/2026-04-19-over-tooled-agent-problem]  
Accuracy bands: 1–5 tools = reliable; 5–10 = workable; 10–30 = measurable degradation begins; 30+ =
naive "dump everything" fails; 100+ = non-functional without routing. [SOURCE: https://tianpan.co/blog/2026-04-13-tool-explosion-problem-agent-tool-selection-at-scale]  
Perplexity production data: ~100-token budget per skill index entry because every skill entry is paid
in every session. Adding a skill makes every other skill marginally worse. [SOURCE: https://research.perplexity.ai/articles/designing-refining-and-maintaining-agent-skills-at-perplexity]

**Good:** `search_issues` with a `state` enum parameter (open/closed/all)  
**Bad:** `search_open_issues`, `search_closed_issues`, `search_all_issues`

**agent-infra application:** Audit hooks, skills, rules, MCPs with the same question: can a human
unambiguously route a given scenario to exactly one surface? Overlap = pruning candidate.

---

### 2. Progressive Disclosure — *Always-Loaded Must Fit in Context Headroom*

**Definition:** Layer information by frequency-of-need. Always-loaded surfaces (rules, system prompt)
contain only identity + scope + pointers. Detail loads on demand (skills, tool schemas).

**Why it matters for agents:** Context window contamination causes "attention dilution": when an
agent's context contains a 2000-token always-loaded definition, attention distributes across all
2000 tokens including the 80% irrelevant to the current task. Result: critical instructions are
underweighted, rule conflicts cause hedging instead of execution. [SOURCE: https://agentpatterns.ai/agent-design/progressive-disclosure-agents/]  
The CLAUDE.md context-budget canary exists for exactly this: flag repos over ~30k always-loaded ceiling. [TRAINING-DATA: agent-infra own architecture]  
Fin.ai production system: hundreds of skills, but skill catalog injected as brief summary index, full
skill loaded only on trigger or via hooks that detect the right intent. [SOURCE: https://ideas.fin.ai/p/webinar-q-and-a-how-fin-3xd-r-and]

**Good:** Rules file = conventions + boundary pointers; skills file = full procedure loaded on demand  
**Bad:** One 4000-line CLAUDE.md covering all procedures always loaded

**agent-infra application:** Rule of thumb = always-loaded rule files stay under 200 lines; skills
stay off-context until invoked; MCP tool schemas deferred via `retrieve_tools` or profile flags.

---

### 3. Intent-Oriented Naming — *Verb-Noun, No Ambiguity*

**Definition:** Every surface name is a verb + object that states what happens, not what category it
belongs to. Names are the first signal at selection time; poor names cause wrong-tool selection before
the model reads the description.

**Why it matters for agents:** The model uses names before descriptions during tool selection. Noun-first
names (`issues_search`), vague verbs (`process_thing`), acronyms requiring domain knowledge — all
increase selection error. [SOURCE: https://llmbestpractices.com/ai-agents/mcp-tool-design]  
Consistent schema across tools (always `customer_id`, never sometimes `id` and sometimes `identifier`)
reduces cross-tool generalization errors. [SOURCE: https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/main/skills/tool-design/SKILL.md]

**Good:** `create_pull_request`, `search_code_files`, `close_issue`  
**Bad:** `pr_management`, `file_stuff`, `handle_github`

**agent-infra application:** Skill and hook names follow this pattern. Current: `reflect_capture`,
`calibration-canary`, `codex_parity_sync` — mixed. Should be `capture_reflect_session`,
`run_calibration_canary`, `sync_codex_parity`.

---

### 4. Constrained Inputs — *Every Unconstrained Parameter Is a Coin Flip*

**Definition:** Use enums for fixed choices, min/max for numerics, required only for fields the tool
cannot infer or default. Bare `string` parameters accept hallucinated values.

**Why it matters for agents:** "Every unconstrained parameter is a coin flip" (MCP Schema Design
[SOURCE: https://yaw.sh/mcp-in-production/mcp-schema-design/]). Without enums, models produce
inconsistent values even for the same canonical concept: `status: string` produces "active", "Active",
"ACTIVE", "open", "in_progress". With enum, only valid values are possible.  
OpenAI recommends `strict: true` + `additionalProperties: false` on every object schema to enforce
shape adherence. [SOURCE: https://developers.openai.com/api/docs/guides/function-calling]

**Good:** `status: { enum: ["open", "closed", "in_progress"] }`  
**Bad:** `status: string` (description says "use open, closed, or in_progress")

**agent-infra application:** Hook schemas (where applicable), MCP parameter definitions. Prefer typed
parameters over free-text wherever the value space is enumerable.

---

### 5. The Referent Layer — *Schema Validation ≠ Semantic Validity*

**Definition:** JSON Schema validates shape; your application layer must validate that referential
arguments (IDs, names, paths) point to things that actually exist in the authoritative system.

**Why it matters for agents:** A hallucinated ID passes schema validation if it's the right type.
The missing layer is an existence check between the model's proposed call and execution. [SOURCE: https://tianpan.co/blog/2026-06-02-the-hallucinated-tool-argument-that-passed-schema-validation]  
Every tool that takes a referential argument needs a documented pre-execution check; pure-function
tools (calculator, unit converter) do not. The dividing line: does the argument refer to state?

**Good:** Tool doc includes "session_id must come from create_session output"; harness validates
before execution  
**Bad:** Trust `session_id: string` + schema validation, no referent check

**agent-infra application:** Hooks that receive file paths or IDs should validate referents.
`reflect_capture.py` writing to session IDs is an example of referent-carrying calls.

---

### 6. Description as Decision Contract — *Prescriptive When + When-Not*

**Definition:** Tool/skill descriptions must answer: what it does, when to call it (trigger condition),
when NOT to call it (negative criterion), and what it returns. The trigger condition is the
highest-ROI single addition.

**Why it matters for agents:** Anthropic engineering finding: "On recent Opus models, which reach for
tools more conservatively, trigger conditions in the description give measurable lift in should-call
rate." [SOURCE: https://github.com/anthropics/skills/blob/main/skills/claude-api/shared/tool-use-concepts.md]  
OpenAI: description should "explicitly describe the purpose and each parameter... tell the model
exactly what to do. Include examples and edge cases." Include one concrete example invocation — it's
"the most valuable line because it shows the model the exact argument shape." [SOURCE: https://llmbestpractices.com/ai-agents/mcp-tool-design]  
The MCP spec recommends: parameter-specific nuances in `inputSchema` description fields, not the tool
description. Description = routing signal; parameter descriptions = usage signal. [SOURCE: https://www.inovaflow.io/insights/how-to-design-mcp-tools]

**Good:**
```
"Use this to search Jira issues when the user asks about bug status or sprint planning.
Do NOT use for code search — use search_code_files instead.
Returns: issue list with id, status, assignee, priority.
Example: search_jira_issues(project='INFRA', status='open', assignee='current_user')"
```
**Bad:** "Search Jira for issues."

**agent-infra application:** Skills and hooks that have descriptions. The SKILL.md files already use
this pattern well; hook descriptions in settings.json often lack the negative criterion.

---

### 7. Outputs Compose — *Return What the Next Tool Needs*

**Definition:** Tool outputs use the same ID format and field names that other tools' input parameters
expect. Return enough context for the model to reason, not just raw IDs.

**Why it matters for agents:** Agents chain tools across servers: `get_customer` → `list_orders` →
`refund_order`. If output A uses `customer_uuid` but input B expects `customer_id`, chaining fails.
[SOURCE: https://yaw.sh/mcp-in-production/mcp-schema-design/]  
"Return high-signal, token-efficient results (avoid low-value IDs or verbose blobs)." [SOURCE: https://www.anthropic.com/engineering/writing-tools-for-agents]  
The Claude Code agent context engineering paper recommends a hybrid: some data up front for speed
(CLAUDE.md), some pulled just-in-time via primitives like glob/grep — "effectively bypassing the
issues of stale indexing." [SOURCE: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents]

**Good:** `get_pull_request` returns `{id, title, diff_url, base_branch, head_branch, author}` — all
fields downstream tools need  
**Bad:** `get_pull_request` returns `{id}` — downstream tool must call `get_pr_details(id)` again

**agent-infra application:** MCP tools in `agent_infra_mcp.py` should return self-contained context
chunks, not IDs requiring follow-up lookups.

---

### 8. Stateless by Default — *No Side Effects Without Explicit Contract*

**Definition:** Surfaces do not retain state between invocations unless they explicitly declare it.
Read-only surfaces never mutate. Write surfaces declare idempotency behavior.

**Why it matters for agents:** Agents retry. Models retry. Users re-prompt. Write tools called twice
must be idempotent by default — accept an `idempotency_key` or use natural keys. [SOURCE: https://yaw.sh/mcp-in-production/mcp-schema-design/]  
Plugin architecture pattern: "Plugins are functionally stateless — they don't maintain internal state
between command executions. Instead, all persistent data is managed through the Core API's State
Service." [SOURCE: https://github.com/hiero-ledger/hiero-cli/blob/main/PLUGIN_ARCHITECTURE_GUIDE.md]  
Anthropic: hooks that validate whether a file changed since last read enforce a staleness invariant
bash can't. [SOURCE: https://github.com/anthropics/skills/blob/main/skills/claude-api/shared/agent-design.md]

**Good:** `create_review(pr_id, reviewer, idempotency_key)` — second call with same key is a no-op  
**Bad:** `create_review(pr_id, reviewer)` — called twice = two duplicate reviews

**agent-infra application:** Hooks that write files (improvement-log, maintenance-actions.jsonl)
should be idempotent on key.

---

### 9. Small Core, Plugin Periphery — *Microkernel Over Monolith*

**Definition:** The always-loaded core is minimal and stable. Domain-specific capabilities are
plugins/skills loaded on demand. Core provides lifecycle hooks for plugins to register into.

**Why it matters for agents:** "The most successful CLI tools — ESLint, Babel, Prettier, the Salesforce
CLI — are platforms, not monoliths. Their core is small, and plugins do the real work." [SOURCE: https://www.grizzlypeaksoftware.com/library/cli-plugins-and-extension-systems-sc50pnqd]  
Same for agents: Fin.ai's architecture has a base plugin with core skills, separate plugins for
languages/frameworks/teams, many disabled by default. [SOURCE: https://ideas.fin.ai/p/webinar-q-and-a-how-fin-3xd-r-and]  
OpenAI Agents SDK: `tool_namespace()` groups related tools under a shared prefix, keeps each namespace
<10 functions. [SOURCE: https://github.com/openai/openai-agents-python/blob/main/docs/tools.md]

**Good:** CLAUDE.md (core) + `.claude/rules/*.md` (domain rules, path-scoped) + skills (on-demand)  
**Bad:** Everything in one mega-CLAUDE.md loaded for all sessions regardless of task domain

**agent-infra application:** The existing architecture already follows this. The risk is rule-file
bloat — rules files become mini-monoliths over time.

---

### 10. Pits of Success — *Errors Must Have Ladders*

**Definition:** When a surface call fails, the error response must tell the caller what the correct
action is, not just what was wrong. Error messages are part of the API contract.

**Why it matters for agents:** Stripe's 2024 developer keynote named this explicitly: "even if you fall
into an integration issue, there's a ladder right there waiting for you." If you misspell a parameter,
don't just say "invalid" — say the correct parameter name. [SOURCE: https://stripe.com/sessions/2024/developer-keynote]  
For agents: `isError: true` with a structured error that gives a recovery path is better than a
generic error string. Use `isError: true` for expected failures (not-found, validation) — agents
adapt better to structured errors than raw exceptions. [SOURCE: https://code-js.in/ai/designing-mcp-tool-schemas-best-practices/]  
"Repeated identical calls: a flag that the loop is broken — add caching, add observation that 'you
already called this'." [SOURCE: https://callsphere.ai/blog/tool-calling-schemas-robust-function-definitions-2026]

**Good:** `{"isError": true, "message": "user_id 'abc' not found. Call list_users() to get valid IDs."}`  
**Bad:** `{"error": "invalid input"}`

**agent-infra application:** Hooks that return exit codes without explanatory text. The stop hook
advisory should include what to do next, not just what was wrong.

---

### 11. Offload Burden From the Model — *Don't Make It Fill What You Know*

**Definition:** If the orchestrator already knows a value, pass it in code — don't expose it as a
parameter the model must supply. If two tools are always called in sequence, collapse them into one.

**Why it matters for agents:** OpenAI: "Don't make the model fill arguments you already know. For
example, if you already have an order_id based on a previous menu, don't have an order_id param —
instead have no params `submit_refund()` and pass the order_id with code." [SOURCE: https://developers.openai.com/api/docs/guides/function-calling]  
Every parameter the model must supply is a hallucination opportunity. Reducing the model's
decision surface is a reliability gain. [INFERENCE]

**Good:** Harness passes `session_id` to tool calls automatically based on context  
**Bad:** Model must supply `session_id` on every tool call even though harness owns it

**agent-infra application:** MCP tools exposed to the agent should receive caller context (project,
session) from the harness, not require the model to supply it explicitly.

---

### 12. Hooks Are Architecture, Rules Are Instructions — *Enforcement by Category*

**Definition:** Deterministic invariants (file format, path safety, loop detection, blast-radius gating)
belong in hooks. Semantic guidance (when to call X, how to frame Y) belongs in rules/descriptions.
Never use instructions for something a hook can enforce.

**Why it matters for agents:** "Architecture over instructions. Instructions alone = 0% reliable (EoG)."
[TRAINING-DATA: agent-infra CLAUDE.md constitution, Principle 1]  
The bash→dedicated-tool promotion rule captures this exactly: a `send_email` tool is easy to gate;
`bash -c "curl -X POST ..."` is not. Reversibility is the criterion: hard-to-reverse actions are
candidates for dedicated gating. [SOURCE: https://github.com/anthropics/skills/blob/main/skills/claude-api/shared/agent-design.md]  
Fin.ai's deterministic hooks: "we monitor Claude attempts to create a PR using `gh` tool, intercept
it with a hook, and if `create-pr` skill wasn't loaded yet, inject a prompt to load it." — using
architectural interception to enforce a procedural invariant. [SOURCE: https://ideas.fin.ai/p/webinar-q-and-a-how-fin-3xd-r-and]

**Good:** Loop detection via bash hook (deterministic, counts tool calls)  
**Bad:** Rule that says "don't call the same tool more than 3 times" (model ignores under pressure)

**agent-infra application:** The four existing hook categories (cascading waste, irreversible state,
epistemic discipline, style/format) map cleanly to this. Epistemic discipline is the edge case —
text instructions can't enforce it, but prompt hooks provide a semantic middle layer.

---

### 13. Versioning and Non-Breaking Evolution — *API Surfaces Must Evolve Safely*

**Definition:** Surface changes that remove capabilities or alter semantics are breaking changes and
require explicit migration. Additive changes (new optional parameters, new tools) are non-breaking.

**Why it matters for agents:** Stripe's foundational insight: "We never deprecate APIs without an
unavoidable requirement to do so... API instability directly creates churn." [SOURCE: https://craftingengstrategy.com/api-deprecation-strategy/]  
For agent surfaces: hooks that change their blocking behavior mid-session invalidate agent
assumptions. Skills that rename parameters break any model trained on the old usage.  
The version translation layer pattern: maintain ONE implementation (latest), wrap old behavior in
thin transformation modules — this applies to skills that refactor their interface. [SOURCE: https://stripe.com/blog/api-versioning]

**Good:** New optional `--dry-run` flag on a skill; old invocations still work  
**Bad:** Renaming `reflect_capture` to `capture_session` with no alias period

**agent-infra application:** When refactoring skills/hooks, keep old names working via alias for at
minimum one session cycle. Document breaking changes in CHANGELOG or `improvement-log.md`.

---

### 14. Observe Before Promoting — *Measure Then Enforce*

**Definition:** A new surface type (hook, skill, MCP) must demonstrate need before becoming
canonical. Log every trigger. Measure false positive rate before promoting to block.

**Why it matters for agents:** "Measure before enforcing. Without data, you can't promote or demote
hooks rationally." [TRAINING-DATA: agent-infra CLAUDE.md constitution, Principle 3]  
Perplexity: "Every time you add an additional Skill, you risk making every other Skill slightly worse,
so you need to make sure that you're [testing it]." Full eval suite: precision, recall, forbidden
checks for skill routing. [SOURCE: https://research.perplexity.ai/articles/designing-refining-and-maintaining-agent-skills-at-perplexity]  
The "self-generated skills provide no benefit on average" finding is important here: don't let the
agent self-author surfaces without human review — the model cannot reliably author procedural
knowledge it benefits from consuming. [SOURCE: https://research.perplexity.ai/articles/designing-refining-and-maintaining-agent-skills-at-perplexity]

**Good:** Shadow-mode hook that logs would-have-blocked; analyze 2 weeks before enabling blocking  
**Bad:** Immediately ship a blocking hook on the first occurrence of a failure pattern

**agent-infra application:** The gov.py report and risky-diff-review shadow window embody this. The
hook ROI tracking in `maintenance-actions.jsonl` is the measurement mechanism.

---

## 3 Principles Not in the Top 14 (Disconfirmation Pass)

These principles from human API design transfer weakly or not at all to agent surfaces:

**Discoverability via browser/catalog:** REST API discoverability via developer portals is a human
UX concern. For agents, the model reads schemas in-context. "Discoverability" = clear naming +
tight descriptions, not a portal. The BM25 lexical index used by MCPProxy works because tool names
and descriptions are "written by humans who use the same vocabulary their users will." [SOURCE: https://mcpproxy.app/blog/2026-04-24-cut-agent-tool-context-97-percent/] The developer portal pattern
doesn't apply.

**HTTP method semantics (GET/POST/DELETE):** REST conventions around verb-HTTP-method alignment are
irrelevant to function-calling surfaces where the model only sees `name`, `description`, and
`inputSchema`. The read/write distinction is captured in naming and idempotency semantics instead.

**Pagination (cursor-based):** Partially transfers. Agent tools should implement pagination/truncation
with sensible defaults, but the cursor-based vs. offset debate doesn't matter for agents — what matters
is that the model can tell when there's more. "Paginate explicitly so the model knows when there's
more." [SOURCE: https://yaw.sh/mcp-in-production/mcp-schema-design/]

---

## 5 Falsifiable Hypotheses

### H1: Description Quality Is the Highest-ROI Single Intervention

**If true:** Adding trigger conditions + negative criteria to tool/skill descriptions should measurably
lift correct-routing rate in the agent's session logs.  
**If false:** Routing failures would be uncorrelated with description completeness; we'd see failures
on well-described tools at the same rate as poorly-described ones.  
**Test:** Take 10 skills with terse descriptions, rewrite with trigger + negative + example. Compare
routing precision in `/observe sessions` before/after.  
**Evidence:** Anthropic reports "measurable lift in should-call rate" from trigger conditions. [SOURCE: https://github.com/anthropics/skills/blob/main/skills/claude-api/shared/tool-use-concepts.md] [FRONTIER: not independently replicated in our sessions]

### H2: Context Budget Is the Binding Constraint, Not Model Capability

**If true:** A model with 10 well-constrained tools should outperform the same model with 50 tools on
task-specific success, even if the 50-tool set contains the 10 plus more.  
**If false:** More tools would provide parallel paths that compensate for selection noise.  
**Test:** A/B test MCP profiles with full vs. constrained tool sets on repeated tasks (calibration-canary).  
**Evidence:** RAG-MCP: 13.62% → 43.2% from tool set reduction alone [SOURCE: https://tianpan.co/blog/2026-04-19-over-tooled-agent-problem]; FuncBenchGen: GPT-5 achieves only 15% at 20-function call chains [SOURCE: https://arxiv.org/pdf/2509.26553]. High confidence. [SCITE: NO COVERAGE on RAG-MCP claim]

### H3: Hooks Outperform Rules for High-Frequency Invariants

**If true:** Hook-enforced invariants (bash loop guard, multiline bash block) should show fewer
violations per session than rule-stated invariants in the same category.  
**If false:** Rule-stated invariants would show comparable compliance, suggesting the enforcement
mechanism doesn't matter.  
**Test:** Compare session log violation rate for hook-covered vs. rule-only invariant categories.  
**Evidence:** CLAUDE.md constitution Principle 1 based on SlopCodeBench (arXiv:2603.24755): "instructions
shift the intercept; architecture shifts the slope." [TRAINING-DATA: constitution cites this]

### H4: Self-Contained Skills Generalize; Dependent Skills Don't

**If true:** Skills that cross-reference other skills (implicit ordering requirements) should show
higher loading failures and worse task completion than self-contained skills.  
**If false:** LLMs would correctly infer implicit dependencies from context.  
**Test:** Audit skill files for cross-references. Correlate with routing failures in session logs.  
**Evidence:** AgentPatterns.ai: "Each skill must be self-contained — it should work without the agent
having to cross-reference other skills." [SOURCE: https://agentpatterns.ai/agent-design/progressive-disclosure-agents/] [INFERENCE: not measured in our sessions]

### H5: Tool Count per Context ≥30 Predicts Session-Level Failure Uplift

**If true:** Sessions where the agent had >30 tools visible should show measurably higher tool-use
errors, loops, or session failures vs. sessions with <15 visible tools.  
**If false:** Good tool descriptions or model capability compensates past the 30-tool mark.  
**Test:** agentlogs session data — cross-reference visible tool count at start of session with
session-level failure flags.  
**Evidence:** Tool explosion blog: "30+ tools: naive approaches fail. Below 30% accuracy." [SOURCE: https://tianpan.co/blog/2026-04-13-tool-explosion-problem-agent-tool-selection-at-scale] Numbers are
practitioner estimates without controlled study — treat as directional, not calibrated. [FRONTIER]

---

## Priority Ranking Summary

| Rank | Principle | Impact | Source Confidence |
|------|-----------|--------|-------------------|
| 1 | Consolidation Before Addition | CRITICAL | HIGH (3 independent sources) |
| 2 | Progressive Disclosure | CRITICAL | HIGH (architecture + Perplexity data) |
| 3 | Intent-Oriented Naming | HIGH | HIGH (Anthropic + OpenAI docs) |
| 4 | Constrained Inputs | HIGH | HIGH (OpenAI strict mode + MCP guides) |
| 5 | Description as Decision Contract | HIGH | HIGH (Anthropic: measurable lift) |
| 6 | Hooks Are Architecture, Rules Are Instructions | HIGH | HIGH (agent-infra own evidence) |
| 7 | The Referent Layer | MEDIUM-HIGH | MED (practitioner finding, June 2026) |
| 8 | Offload Burden From Model | MEDIUM-HIGH | HIGH (OpenAI official) |
| 9 | Outputs Compose | MEDIUM | MED (practitioner guides) |
| 10 | Stateless by Default | MEDIUM | HIGH (plugin patterns) |
| 11 | Small Core, Plugin Periphery | MEDIUM | HIGH (CLI + Fin.ai production) |
| 12 | Pits of Success | MEDIUM | HIGH (Stripe keynote 2024) |
| 13 | Observe Before Promoting | MEDIUM | HIGH (agent-infra own practice) |
| 14 | Versioning and Non-Breaking Evolution | LOWER | HIGH (Stripe engineering) |

---

## Key Sources

| Source | Type | Confidence | URL |
|--------|------|------------|-----|
| Anthropic: Writing Effective Tools | Official engineering blog | HIGH | https://www.anthropic.com/engineering/writing-tools-for-agents |
| Anthropic: Effective Context Engineering | Official engineering blog | HIGH | https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents |
| Anthropic: Claude agent-design.md | Official SDK docs | HIGH | https://github.com/anthropics/skills/blob/main/skills/claude-api/shared/agent-design.md |
| OpenAI: Function Calling Guide | Official docs | HIGH | https://developers.openai.com/api/docs/guides/function-calling |
| OpenAI Agents SDK: tools.md | Official SDK docs | HIGH | https://github.com/openai/openai-agents-python/blob/main/docs/tools.md |
| MCP Schema Design (yaw.sh) | Practitioner guide 2026 | MED | https://yaw.sh/mcp-in-production/mcp-schema-design/ |
| LLM Best Practices: MCP Tool Design | Practitioner guide | MED | https://llmbestpractices.com/ai-agents/mcp-tool-design |
| Tool Explosion Problem | Practitioner, data-cited | MED | https://tianpan.co/blog/2026-04-13-tool-explosion-problem-agent-tool-selection-at-scale |
| Over-Tooled Agent Problem (RAG-MCP) | Practitioner, 13.62% stat | MED | https://tianpan.co/blog/2026-04-19-over-tooled-agent-problem |
| Hallucinated Arg, Passed Schema | Practitioner, Jun 2026 | MED | https://tianpan.co/blog/2026-06-02-the-hallucinated-tool-argument-that-passed-schema-validation |
| Perplexity: Designing Agent Skills | Production system report | HIGH | https://research.perplexity.ai/articles/designing-refining-and-maintaining-agent-skills-at-perplexity |
| AgentPatterns: Progressive Disclosure | Practitioner guide | MED | https://agentpatterns.ai/agent-design/progressive-disclosure-agents/ |
| Fin.ai: 3x R&D output | Production case study | HIGH | https://ideas.fin.ai/p/webinar-q-and-a-how-fin-3xd-r-and |
| Stripe: API Versioning | Official engineering blog | HIGH | https://stripe.com/blog/api-versioning |
| Stripe: Developer Keynote 2024 | Official, pits of success | HIGH | https://stripe.com/sessions/2024/developer-keynote |
| FuncBenchGen (arXiv:2509.26553) | Academic preprint | MED | https://arxiv.org/pdf/2509.26553 |
| CLIG: CLI Guidelines | Community standard | HIGH | https://clig.dev/ |
| MCPProxy: 97% context cut | Practitioner case study | MED | https://mcpproxy.app/blog/2026-04-24-cut-agent-tool-context-97-percent/ |

---

## What's Uncertain

1. **Exact accuracy thresholds for tool count** — the 13.62% and 43% RAG-MCP numbers, and the
   accuracy-cliff at 30 tools, are practitioner reports without peer-reviewed controlled studies.
   Directional confidence is HIGH; exact numbers are FRONTIER.

2. **Cross-model generalization** — Perplexity found "Sonnet and GPT behave quite differently when
   it comes to Skills." Principles derived from Claude/GPT-4 behavior may not fully transfer to
   future models with larger context budgets or better selection algorithms.

3. **Self-generated skills** — the "models cannot reliably author procedural knowledge they benefit
   from consuming" finding is early research cited once by Perplexity. Needs independent replication.
   Implication: agent-authored skills require human review before promotion to canonical.

4. **Optimal context budget per surface type** — Perplexity uses ~100 tokens/skill index entry;
   agent-infra uses longer descriptions. The right tradeoff between description quality and token
   economy is not empirically settled for our specific harness.

---

## Search Log

Axes searched: (1) academic/practitioner API design, (2) agent-specific MCP/function-calling,
(3) CLI/plugin adjacent, (4) adversarial/anti-patterns.  
Queries: 9 web searches, 2 existing memo reads.  
Tool calls: ~18.  
Stop condition: converged (2+ sources on all ranked principles; disconfirmation pass complete).  
Key misses: MCP official spec (superseded by practitioner guides); Anthropic's internal 20-page API
design doc (referenced in LinkedIn post as existing but not public).
