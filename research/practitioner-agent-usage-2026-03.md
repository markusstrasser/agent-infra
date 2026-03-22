---
title: "How Practitioners Actually Use AI Agents — March 2026 Landscape"
date: 2026-03-21
status: active
tags: [agents, practitioner, best-practices, workflows, multi-agent, cost, autonomy]
---

# How Practitioners Actually Use AI Agents — March 2026 Landscape

**Date:** 2026-03-21
**Tier:** Deep
**Ground truth:** Existing memos on agent scaffolding (2026-03-10), Symphony assessment, multi-agent coordination evidence, agent failure modes (22 documented).

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Reducing from 16 agents to 2 lost zero meaningful capability | Practitioner deployment, before/after metrics | HIGH | [SOURCE: dgeorgiev.biz] | VERIFIED |
| 2 | Skills for MCP tools reduce token usage by 87-98% | Controlled measurement, 5 scenarios | HIGH | [SOURCE: seroter.com] | VERIFIED |
| 3 | Combined Claude Code + Cursor cuts implementation time ~40% vs either alone | 30 tracked sessions | MEDIUM | [SOURCE: blakecrosley.com] | SINGLE-PRACTITIONER |
| 4 | 65% of "agentic" workflow nodes run as pure deterministic code | 14 production workflows analyzed | HIGH | [SOURCE: tomtunguz.com] | VERIFIED |
| 5 | Only 48% of developers consistently review AI code before commit | Stack Overflow / survey data | MEDIUM | [SOURCE: addyo.substack.com] | CITED-SURVEY |
| 6 | High-adoption teams merge 98% more PRs but review times balloon 91% | Faros AI / DORA 2025 report | HIGH | [SOURCE: addyo.substack.com, citing DORA] | VERIFIED |
| 7 | Average brownfield productivity gain is 1-2x, not 10x | Practitioner experience across multiple projects | MEDIUM | [SOURCE: dennybritz.com] | PRACTITIONER |
| 8 | No closed-loop experiment has produced 100% autonomous completion | Multiple controlled experiments | HIGH | [SOURCE: codemanship.wordpress.com] | VERIFIED |
| 9 | $120/month covers 200+ daily LLM calls with 5-model routing | Detailed cost tracking | HIGH | [SOURCE: ianlpaterson.com] | VERIFIED |
| 10 | Model chaining (Codex → Opus) produces 6x cumulative speedup on optimization tasks | Benchmarked Rust ML implementations | HIGH | [SOURCE: minimaxir.com] | VERIFIED |
| 11 | L1/L2/L3 memory hierarchy eliminated memory failures by day 7 | 10-day deployment with tracking | MEDIUM | [SOURCE: sukany.cz] | SINGLE-PRACTITIONER |
| 12 | Filesystem polling replaces unreliable message-based agent coordination (20-30% delivery failure rate) | Measured delivery reliability | HIGH | [SOURCE: sukany.cz] | VERIFIED |
| 13 | ~$6,000/week for heavy multi-agent orchestration (800 commits, 100+ PRs) | Practitioner cost tracking | MEDIUM | [SOURCE: zachwills.net] | SINGLE-PRACTITIONER |
| 14 | AGENTS.md/CLAUDE.md is "the main differentiator between good and bad results" | Multiple independent practitioners | HIGH | [SOURCE: minimaxir.com, g.money, multiple] | CONVERGED |
| 15 | Configuration required to make agents useful: ~1,000 lines across 8 files | 10-day deployment tracking | MEDIUM | [SOURCE: sukany.cz] | SINGLE-PRACTITIONER |
| 16 | Bimodal adoption: 44% write <10% manually, vast majority >90% manual | Armin Ronacher poll | MEDIUM | [SOURCE: addyo.substack.com, citing Ronacher] | CITED-SURVEY |
| 17 | Voice-to-text prompting naturally produces more context than typed prompts | Multiple practitioners independently | MEDIUM | [SOURCE: zachwills.net, kovyrin.net] | CONVERGED |
| 18 | 68% of production tool failures = incorrect parameters, 21% = wrong tool | Production deployment analysis | MEDIUM | [SOURCE: cited in scaffolding-landscape memo] | VERIFIED |
| 19 | Planning + spec development (PRD-first) transforms agent output quality | Multiple independent practitioners | HIGH | [SOURCE: kovyrin.net, markptorres.com, zachwills.net] | CONVERGED |
| 20 | Pre-structured templates outperform blank files + instructions for agent deliverables | Multi-agent system experience | MEDIUM | [SOURCE: davide.im] | PRACTITIONER |

## Key Findings

### 1. The Great Consolidation: More Agents ≠ Better Results

The strongest signal across practitioner write-ups: people who started with many agents converged to fewer.

**Daniel Georgiev** ran 16 agents on a single VPS with 23 cron jobs, 5 Discord bots, and a peer-routing system. After months of production, he cut to 2 agents and 2 cron jobs — with "zero meaningful capability loss." The reduction was 87.5% across every metric (agents, cron jobs, config entries), with weekly debugging hours dropping from "hours" to "~0." [SOURCE: dgeorgiev.biz]

**Root cause:** Agent count creates quadratic complexity, not linear. Each agent needs non-conflicting instructions, routing rules, security permissions, memory management, and cron scheduling. Every agent pair creates new interaction surface area.

**Failure modes from scaling agents too fast:**
- **Session conflicts**: Multiple agents sharing CLI backends deadlock silently (2+ min hangs)
- **Identity confusion**: Agents reading shared chat history adopt other agents' identities
- **Backlog death spirals**: Slow model + passive listening + bot-to-bot visibility = 200+ second response latency
- **Infinite bot loops**: Two agents with `requireMention: false` + `allowBots: true` = infinite response cycles
- **Configuration drift**: Live config diverges from repo; deployments silently revert intentional changes

**Tom Tunguz's hybrid state machine analysis** across 14 production workflows found 65% of nodes run as pure deterministic code. Only 14% of workflows are genuinely "fully agentic." The rest are mostly code with LLM handling extraction/synthesis in 1-3 turns. [SOURCE: tomtunguz.com]

**Takeaway for us:** Our constitutional principle "architecture over instructions" is validated by every practitioner who scaled agents. The number of agents is a measure of complexity, not sophistication. Our 2-agent approach (orchestrated tasks + interactive sessions) is closer to the practitioner convergence point than most starting points.

### 2. Context Engineering Is the Actual Skill

The single most impactful lever across all practitioner reports: controlling what goes into the context window.

**Richard Seroter** measured a controlled experiment: raw MCP tools consumed 328,083 tokens across 29 turns. Adding a single Skill (domain-encapsulating the query pattern) dropped to 39,622 tokens in 5 turns — **87.9% reduction.** Pairing a single relevant MCP with a skill achieved 97.8% savings. [SOURCE: seroter.com]

The mechanism: Skills act as a **lossy compression layer** for MCP capabilities. By narrowing the problem space, agents spend fewer tokens on tool selection and exploration. "All necessary information is contained within this document" prevents second-guessing.

**Jaime Jiménez** independently developed a three-tier skill loading system: [SOURCE: jaime.win]
- **Base tier** (~50 lines, always loads): filesystem paths, shell commands, safety constraints
- **Skill descriptions** (~50 tokens each): trigger rules with explicit negative scope
- **Skill body + references**: on-demand loading (~80 lines)

This kept overhead under 1,500 tokens/message while enabling thousands of available instructions. **Key insight:** negative scope ("Do NOT use for X") prevents ambiguous inputs from loading conflicting skills.

**Martin Sukany** built an L1/L2/L3 memory hierarchy inspired by CPU caches: [SOURCE: sukany.cz]
- L1 (`NOW.md`): <1.5KB, current tasks only
- L2 (`MEMORY.md`): <5KB, curated long-term facts, nightly pruning
- L3: Daily log archive accessed via BM25 + semantic search

Selective memory loading reduced per-session overhead by 60%. By day 7, zero memory failures.

**Takeaway for us:** Our tiered context approach (rules files < CLAUDE.md < research memos < full corpus) maps to these practitioner patterns. The Seroter finding validates our skill architecture — Skills aren't just convenience, they're the primary cost and quality lever. Our negative-scope patterns in skill descriptions are independently validated. The L1/L2/L3 pattern is strikingly similar to our NOW.md (checkpoint) / MEMORY.md / daily logs approach.

### 3. Planning Dominance: 70% Specs, 30% Execution

Multiple independent practitioners converged on the same ratio: **invest heavily in planning, let execution be mechanical.**

**Oleksiy Kovyrin** developed a PRD-driven workflow with three phases: [SOURCE: kovyrin.net]
1. **PRD creation** (20-30 min voice-to-text brain dump → model asks clarifying questions → refined PRD)
2. **Task list** (two-phase: high-level decomposition → junior-engineer-level granularity)
3. **Step-by-step execution** (fresh agent per task, clean context each time)

Critical innovation: mandatory reflection after each task. Agent writes learnings into the task document, creating institutional memory across sessions. "The task list is a living document, not a rigid contract."

**Mark Torres** built a 14-step orchestration workflow with hard gates: [SOURCE: markptorres.com]
- Plan Approved (before any coding)
- Spec Compliance Passed (after testing)
- Report Linked (comprehensive validation)

All decisions, evidence, and outcomes live in version-controlled markdown alongside code, not in chat history. Torres calls this "spec-driven development" — shift workload upstream.

**Zach Wills'** Rule #1 from managing 20 agents: "Align on the plan, not just the goal." Rule #2: "A long-running agent is a bug, not a feature" — extended execution means context exhaustion and intent drift. Kill and restart rather than hope for self-correction. [SOURCE: zachwills.net]

**Addy Osmani:** "Spend 70% effort on specs, 30% on execution. Guide goals, not methods." Fresh-context code review (same model reviews its own code in new window) catches mistakes pre-human review. [SOURCE: addyo.substack.com]

**Takeaway for us:** Our plan-mode workflow aligns with this. But practitioners are more aggressive about fresh context per task than we are. Kovyrin's "reflection at task completion" pattern maps to our checkpoint system but adds learning accumulation. Torres' hard gates with durable artifacts are a more formalized version of our orchestrator pipeline steps. We should consider mandatory reflection prompts in orchestrator pipeline steps.

### 4. The Permission Frontier: Default-Deny Everywhere

Practitioners universally converged on restrictive-first permission models.

**Georgiev:** Three-tier permission system — `deny` (no shell), `allowlist` (approved binaries), `full` (infrastructure agent only). Added from day one, prevented "several accidental rm -rf situations." [SOURCE: dgeorgiev.biz]

**Eric Ma:** Auto-approve only non-destructive operations (grep, find, cat, pytest, mypy). Never auto-approve state mutations (rm, mv, git commit, git push, package installs). [SOURCE: ericmjl.github.io]

**Jiménez:** Two-layer containment — OS sandbox (macOS `sandbox-exec`, ~55 lines of code) + prompt-level policy. When sandbox blocks needed capability, adapt tooling rather than widen permissions (SSH→HTTPS, GPG→disable signing, Keychain→file tokens). [SOURCE: jaime.win]

**Sukany's Anti-Dory Registry:** Tracks every cancelled action with timestamp. External services check this before executing, preventing repeated re-derivation of vetoed decisions. [SOURCE: sukany.cz] This solves a real problem: agents re-derive cancelled decisions after context loss. The agent re-enabled a cancelled Twitter integration after a session restart because context loss allowed it to re-derive the same conclusion.

**Colin Walters:** "Strong and clearly delineated barrier between tooling/AI agents acting 'as me' and my ability to approve and push code." Fine-grained, ephemeral credentials per task. [SOURCE: blog.verbum.org]

**Takeaway for us:** Our hook system (pretool guards, append-only protection) maps to the practitioner consensus. The Anti-Dory Registry is a pattern we don't have explicitly — our improvement-log and decisions journal serve a similar purpose but aren't checked programmatically before action. The two-layer containment (OS sandbox + prompt policy) is more rigorous than our hook-only approach.

### 5. Cost: The 5-Model Reality

Sophisticated practitioners don't use one model — they route across 3-5 models by task type.

**Ian Paterson** runs 200+ daily LLM calls for $120/month across 5 models: [SOURCE: ianlpaterson.com]

| Model | Use Case | Quality | Cost/call |
|-------|----------|---------|-----------|
| Claude Sonnet | Interactive coding, debugging | 100% | $0.20 |
| Claude Opus | Complex reasoning | 100% | $0.69 |
| GPT-5.2 Codex | Cross-checking | 98.3% | (ChatGPT Plus) |
| Gemini Flash | Research, web lookups | Free | $0 |
| Qwen 3.5 local | Overnight batch, sensitive data | 85.8% | $0 |

**Routing heuristic:** "If the gap between free and paid exceeds 10 percentage points, pay for frontier." Extraction and simple code show 0-3% gaps (use cheapest). Reasoning/planning show 25-44% gaps (pay for frontier).

**Critical latency finding:** Thinking models add 10-25s per call. In agentic loops with 50+ sequential calls, thinking overhead compounds to ~24 minutes vs ~1.7 minutes with Haiku at 2s/call.

**Max Woolf** discovered model chaining produces compounding speedups: Codex achieves 1.5-2x optimization, then Opus improves that already-optimized code further — 6x cumulative across all tested Rust projects. [SOURCE: minimaxir.com]

**Zach Wills** spent ~$6,000/week on heavy multi-agent orchestration. That produced 800 commits and 100+ PRs in one week but also "complete mental exhaustion after ~3 hours." [SOURCE: zachwills.net]

**Sukany** spent $16-21 over 10 days with disciplined tiered selection: Haiku for background (~$2.16), Sonnet for general (~$9.25), Opus for complex (~$5-7.50). 22 scheduled cron jobs were the quiet cost accumulator. [SOURCE: sukany.cz]

**Takeaway for us:** Our llmx routing (Gemini CLI free, GPT API, Claude subscriptions) maps to the Paterson model. We're already doing tiered routing. The model chaining finding (Codex → Opus) is new and applicable to our autoresearch engine — sequential model passes could compound improvements. The cron cost accumulation warning is directly relevant to our 22+ orchestrator pipelines.

### 6. The Comprehension Debt Crisis

The most concerning finding across multiple practitioners: agent-written code creates understanding gaps.

**Osmani's survey synthesis:** [SOURCE: addyo.substack.com]
- Only 48% consistently review AI code before commit
- 38% find AI logic review requires MORE effort than human code
- 66% cite "almost right, not quite" as primary frustration
- 45% report debugging AI code takes longer than manual writing
- High-adoption teams merge 98% more PRs but review times balloon 91%
- PR size increased 154%
- **No overall workload decrease** despite 10+ hours/week saved (Atlassian survey)

**Denny Britz** identifies a hidden cost: manual coding provided "continuous background thinking" — an automatic learning loop. Agents eliminate this, requiring deliberate effort to build understanding. Parallel agents create "mental fatigue and fragmented attention" similar to smartphone distraction. [SOURCE: dennybritz.com]

**Bimodal adoption (Ronacher poll):** 44% write <10% manually; vast majority >90% manual. The gap is widening, not converging. [SOURCE: cited by Osmani]

**Takeaway for us:** This validates our constitutional principle that supervision must scale with autonomy. The 91% review time inflation is alarming — more code doesn't mean more value if review becomes the bottleneck. Our session-analyst + improvement-log feedback loop is a direct response to comprehension debt. The finding that no overall workload decreases despite efficiency gains is Jevons Paradox in action — exactly what our `agent-economics-decision-frameworks.md` predicted.

### 7. The Agent Configuration Threshold

Multiple practitioners independently discovered: unconfigured agents are chatbots. Configured agents are infrastructure.

**Sukany:** "An AI agent without customization is a chatbot. With customization, it's infrastructure." Required ~1,000 lines across 8 files (22 cron jobs, 24 pipeline types, web safety layer, priority hierarchy). [SOURCE: sukany.cz]

**Woolf:** AGENTS.md files are "the main differentiator between those getting good and bad results." They include formatting rules, tool preferences, code style, validation commands. [SOURCE: minimaxir.com]

**gmoney:** 25 lessons distilled to: CLAUDE.md is foundational, SOUL.md for personality, deliberate permission profiles, Skills as reusable workflows. [SOURCE: g.money]

**Crosley:** Combined workflow produced 95 hooks and 44 skills. [SOURCE: blakecrosley.com]

**Ferrari:** Pre-structured markdown templates with embedded guidance outperform blank files plus instructions. "Instructions get diluted by the time the agent is deep in a task; structure embedded directly in the file stays visible throughout." [SOURCE: davide.im]

**Takeaway for us:** Our CLAUDE.md (600+ lines), 15+ hooks, 30+ skills, and rules files put us at the high end of practitioner configuration. The Ferrari finding about embedded structure vs instructions validates our approach of putting guidance directly in templates and skill files rather than relying on CLAUDE.md alone.

### 8. Filesystem as Coordination Substrate

Practitioners who tried message-based agent coordination abandoned it for filesystem-based patterns.

**Sukany:** Measured 20-30% unreliable delivery on message-based coordination. Replaced with filesystem polling (workers check for output files every 5s over 5min window). Files either exist or don't — no delivery windows or timeouts. Pipeline progress survives orchestrator crashes. Sequential research pipelines went from ~6 min to ~4 min. [SOURCE: sukany.cz]

**Georgiev:** Git-tracked markdown memory survived crashes and system resets. Rollback via `git revert`. Human-readable, no database lock-in. [SOURCE: dgeorgiev.biz]

**Torres:** All decisions, evidence, outcomes in version-controlled markdown alongside code. Not in chat history. [SOURCE: markptorres.com]

**Ferrari:** Each agent gets a prepared workspace with three file types: `scratchpad.md` (thinking), `findings.md` (internal workpaper), `section-draft.md` (client-facing output). [SOURCE: davide.im]

**Takeaway for us:** Our filesystem-based approach (checkpoint files, plan files, research memos, git-tracked memory) aligns perfectly with practitioner convergence. The Ferrari three-file workspace pattern is worth considering for orchestrator tasks. Our orchestrator already uses filesystem artifacts, but the explicit scratchpad/findings/draft separation could improve output quality.

### 9. Voice-to-Text as Underrated Input Method

Two independent practitioners discovered voice prompting produces better agent results.

**Zach Wills:** Voice-to-text for prompting "naturally includes more context and reasoning compared to typed optimization-for-brevity approach." [SOURCE: zachwills.net]

**Oleksiy Kovyrin:** Uses MacWhisper for 20-30 minute brain dumps during PRD creation. Captures reasoning, context, preferences, and uncertainties that typed prompts omit. [SOURCE: kovyrin.net]

The mechanism: typed prompts are optimized for brevity (humans minimize typing effort). Voice prompts naturally include reasoning chains, context, and hedges that improve model understanding.

**Takeaway for us:** Not directly applicable to orchestrated pipelines, but relevant to interactive sessions. Worth noting as a user workflow pattern.

### 10. The Autonomy Ceiling

**Codemanship** ran rigorous closed-loop experiments: extensive read-only planning, then full autonomy (yes to everything), measured by pre-baked acceptance tests. "No set-up has produced 100% autonomous completion, or anything close." [SOURCE: codemanship.wordpress.com]

Failure mechanism: **doom loops** when problems fall outside training distribution. Agents "throw the dice again and again" hoping for different outcomes. Multiple agents create integration problems — "every change has to go through the same garden gate of integration at the end."

Successful practitioners use **"short, controlled bursts" with thorough checking** between cycles. Not continuous autonomy.

**Denny Britz:** Consistent ~1.5x gain. Range 0.1x to 10x depending on task. Average brownfield: 1-2x (not 10x). Best for: well-tested codebases with mechanical refactors, greenfield with standard boilerplate, throwaway data analysis. [SOURCE: dennybritz.com]

**Grapeot:** 2 minutes of instruction → 45 minutes of autonomous work = 5% cognitive investment controlling 100% output. But this only works with: testing-first success criteria, self-contained prompts, and work divided across sub-agents. [SOURCE: grapeot.me]

**Takeaway for us:** Our 15-turn orchestrator limit aligns with the "short bursts" pattern. Our stall detection (anyio.fail_after 600s) prevents doom loops. The 1-2x brownfield gain is a useful expectation calibrator — our tools are optimized for the right regime (infrastructure automation, research, analysis) rather than trying to hit 10x on brownfield coding.

## What's Uncertain

1. **Long-term comprehension debt trajectory.** The 91% review time inflation is alarming, but no longitudinal studies exist. Will tooling adapt (better diffs, better review UIs) or will the debt compound?

2. **Model chaining generalizability.** Woolf's 6x compounding optimization is impressive but tested only on Rust ML algorithms. Unknown whether this transfers to other domains.

3. **Scale limits of filesystem coordination.** Works for 2-20 agents. Unknown whether it holds at 100+ concurrent agents or with high-frequency coordination needs.

4. **Voice prompting effectiveness.** Two practitioners report it independently, but no controlled measurement. Could be survivorship bias from people who think well verbally.

5. **The 65% deterministic finding.** Tunguz's analysis is one team's 14 workflows. Unknown whether this ratio holds across industries and use cases.

## Disconfirmation Results

**Searched for:** "AI agents worse than manual coding", "agent workflow failures", "why I stopped using AI coding agents"

**Finding:** Skeptics exist (Codemanship, Britz's measured skepticism) but even skeptics acknowledge 1-2x gains on suitable tasks. No practitioner who invested in configuration reported returning to fully manual workflows. The criticism is about expectations (10x → 1.5x) rather than absolute capability.

**Absent finding:** No practitioner reports achieving sustained fully autonomous operation on production codebases. Every practitioner describing success is actively supervising, reviewing, and redirecting. The "autonomous agent" framing is marketing; the reality is "supervised agent with graduated autonomy."

## Verification Log

| Claim | Verified via | Result |
|-------|-------------|--------|
| Seroter 87% token reduction | Direct measurement in post | Confirmed with exact numbers |
| Osmani survey data (48% review rate) | References Stack Overflow 2025 | Cited, not independently verified |
| Paterson $120/month cost | Detailed breakdown in post | Internally consistent |
| Georgiev 16→2 agents | Before/after metrics table | Confirmed |
| Britz 1.5x productivity | Stated as practitioner assessment | Practitioner claim |
| Woolf 6x model chaining | Benchmarked Rust implementations | Published with code |
| DORA 2025 98% more PRs / 91% review time | Cited by Osmani | Not independently fetched |

## Search Log

| Query | Tool | Results | Signal |
|-------|------|---------|--------|
| Practitioner agent workflows | Exa neural, personal site | 15 results | HIGH (failed first, succeeded on retry axis) |
| Agent failure post-mortems | Exa neural, personal site | 15 results | HIGH |
| Multi-agent orchestration patterns | Exa neural, personal site | 15 results | HIGH |
| Autonomy supervision boundaries | Exa neural, personal site | 15 results | HIGH |
| Agent cost management | Exa neural, personal site | 15 results | MEDIUM-HIGH |
| Claude Code Cursor daily usage | Exa neural, excl. prior domains | 10 results | MEDIUM |
| Full article reads | WebFetch | 19 articles | PRIMARY SOURCE |

## Actionable Takeaways for Our Infrastructure

### Validate (already doing, practitioners confirm)
1. **Filesystem-based coordination** (checkpoint files, plan files, git-tracked memory)
2. **Tiered context loading** (rules < CLAUDE.md < research memos < full corpus)
3. **Default-deny security model** (hooks blocking destructive operations)
4. **Planning-first workflow** (plan mode → execution)
5. **Short burst autonomy** (15-turn orchestrator limit, stall detection)
6. **Model routing** (llmx across Gemini/GPT/Claude by task type)

### Adopt (practitioners converged, we haven't implemented)
1. **Anti-Dory Registry** — programmatic check of cancelled/vetoed decisions before re-executing. Our decisions journal and improvement-log are the data source; we need a lookup function that agents check.
2. **Three-file workspace pattern** — scratchpad/findings/draft separation for orchestrator tasks. Currently our tasks write to a single output location.
3. **Mandatory reflection at task completion** — Kovyrin's pattern of writing learnings back into the task document. Our orchestrator could inject a reflection prompt at pipeline step completion.
4. **Negative scope in skill descriptions** — "Do NOT use for X" prevents ambiguous trigger. Some of our skills have this; should be systematic.
5. **Model chaining for optimization** — Sequential passes through different model families for code optimization tasks. Applicable to autoresearch engine.

### Investigate (promising signal but uncertain)
1. **OS-level sandboxing** (macOS sandbox-exec) as second containment layer beyond hooks
2. **Voice-to-text for PRD/planning** phases of interactive work
3. **Fresh-context self-review** — same model reviews its own output in clean context window
4. **Comprehension debt metrics** — measuring how well we understand agent-written code over time

### Contradict (practitioners disagree with potential assumptions)
1. **More agents ≠ better.** Every practitioner who scaled up later consolidated. Our approach of fewer, well-configured agents over many specialized ones is correct.
2. **10x productivity is not the norm.** Average brownfield gain is 1-2x. Our value comes from automation of tasks humans wouldn't do at all (overnight research, session analysis, code review sweeps), not from doing the same tasks 10x faster.
3. **100% autonomy is an asymptote.** Even heavy users remain in the loop. Our declining-supervision metric should target diminishing supervision rate, not zero supervision.

---

**Sources read in full (19):** dgeorgiev.biz, minimaxir.com, addyo.substack.com, dennybritz.com, zachwills.net, seroter.com, ianlpaterson.com, jaime.win, ericmjl.github.io (×2), kovyrin.net, markptorres.com, sukany.cz (×2), codemanship.wordpress.com, blog.verbum.org, timdettmers.com, davide.im, grapeot.me, williamr.dev, reactiverobot.com, g.money, blakecrosley.com, tomtunguz.com

**Sources scanned via highlights (36+):** Additional results from 5 Exa sweeps (55+ total results), filtered to above based on signal quality.

<!-- knowledge-index
generated: 2026-03-22T01:40:47Z
hash: 4cf3119371bd

title: How Practitioners Actually Use AI Agents — March 2026 Landscape
status: active
tags: agents, practitioner, best-practices, workflows, multi-agent, cost, autonomy
table_claims: 27

end-knowledge-index -->
