---
title: "Trending Scout — April 5, 2026"
date: 2026-04-05
tags: [trending-scout, vendor-updates, claude-code, microsoft, research]
status: complete
---

# Trending Scout — 2026-04-05

**Window:** 2026-04-03 to 2026-04-05
**Sources:** WebFetch (CC changelog, Kimi changelog, alphaXiv), Exa, Brave, GitHub API
**Findings:** 3 new, 3 version bumps, 4 research papers, 5 already known (filtered)

---

## New Findings (ranked by value - maintenance)

### 1. Microsoft Agent Framework 1.0 GA (April 2)

| Field | Content |
|-------|---------|
| Source | [github.com/microsoft/agent-framework](https://github.com/microsoft/agent-framework/releases/tag/dotnet-1.0.0) (9K stars) |
| What it does | Semantic Kernel + AutoGen unified into a single production SDK. .NET and Python. A2A + MCP support, declarative YAML agents, sequential/concurrent/handoff/group-chat/Magentic-One orchestration, middleware hooks, pluggable memory (Mem0/Redis/Neo4j), DevUI browser debugger, checkpointing. Preview features: **Claude Code SDK integration** (wrap CC as an agent in multi-agent workflows), Agent Harness (shell/filesystem access), AG-UI/CopilotKit adapters. |
| Why relevant | The Claude Code SDK preview means someone can orchestrate CC alongside Azure OpenAI/Gemini agents in the same workflow — Microsoft treating CC as a first-class agent harness, not just a competitor. The "Skills" concept (instructions + scripts + resources) mirrors our skills architecture. A2A support means their agents can interop with ours via protocol if we ever expose A2A. |
| Integration path | **Watch.** The Claude Code SDK integration is preview-only. We already have our own orchestration (orchestrator.py + Agent SDK). If the CC SDK preview stabilizes and offers something our SDK `query()` doesn't (e.g., native multi-agent coordination), reassess. The declarative YAML agent pattern is interesting but we're already invested in Skills. |
| Current overlap | orchestrator.py (task queue), Agent SDK (programmatic CC control), skills (reusable capabilities) |
| Maintenance cost | High if adopted (new framework dep, Python package, Azure tie-in) |
| Verdict | **Watch** — pattern extraction only. Claude Code SDK preview is the trigger to revisit. |

### 2. pydantic-deepagents 0.3.3 — Deep Agent Defaults (April 2)

| Field | Content |
|-------|---------|
| Source | [github.com/vstorm-co/pydantic-deepagents](https://github.com/vstorm-co/pydantic-deepagents/releases/tag/0.3.3) (616 stars) |
| What it does | Pydantic-AI-based framework where **all subagents are deep agents by default** (filesystem + web + memory + eviction). 0.3.3 ships: thinking support (`"high"` default), token eviction (`20_000` limit, saves to files), `compact_conversation` tool, 5 lifecycle hooks (BEFORE/AFTER_RUN, error, model request), ACP adapter for Zed, 3-tier skill discovery (built-in/user/project), `approve_tools` config, AGENTS.md/SOUL.md context files. |
| Why relevant | Several patterns parallel our architecture: (1) eviction to files when tool output exceeds threshold (our hooks do similar), (2) 3-tier skill precedence (our symlinked skills), (3) context file convention (AGENTS.md vs CLAUDE.md). The "subagents are deep agents by default" philosophy is the inverse of CC's lightweight subagents. Their ACP (Agent Client Protocol) adapter for Zed is interesting for editor integration. |
| Integration path | **Extract patterns.** The `compact_conversation` tool (agent-initiated compaction) and `approve_tools` config (per-tool approval lists) are worth evaluating as CC feature requests or hook implementations. |
| Current overlap | Skills (3-tier), CLAUDE.md (context files), hook output >50K to disk (eviction) |
| Maintenance cost | N/A — pattern extraction only |
| Verdict | **Extract pattern** — agent-initiated compaction and per-tool approval config |

### 3. Claude Code v2.1.92 — Stop Hook Fix + Cost Breakdown (April 4)

| Field | Content |
|-------|---------|
| Source | [code.claude.com/docs/en/changelog](https://code.claude.com/docs/en/changelog) |
| What it does | Key changes: (1) **Prompt-type Stop hook fix** — `ok:false` from fast model no longer incorrectly fails the hook; `preventContinuation:true` semantics restored for non-Stop prompt hooks. (2) **Per-model + cache-hit cost breakdown** in `/cost` for subscription users. (3) `forceRemoteSettingsRefresh` policy (fail-closed startup). (4) Interactive Bedrock setup wizard. (5) Prompt cache expiry footer hint. (6) tmux subagent fix (pane count detection after window kill). (7) Edit after Bash with `sed -n`/`cat` (from 2.1.91). (8) `/tag` and `/vim` commands removed. (9) Write tool diff 60% faster on files with tabs/`&`/`$`. |
| Why relevant | **The Stop hook fix is critical.** Our prompt-type Stop hooks (`stop-verification.sh`) use the fast model for claimed-work verification. If `ok:false` was being treated as a hook failure rather than a "don't stop" signal, our stop hooks may have been silently malfunctioning. Need to verify behavior before and after 2.1.92. The per-model cost breakdown improves our dashboard's cost tracking. |
| Integration path | **Adopt immediately.** Already on 2.1.92. Verify stop hook behavior is correct now. Update dashboard cost parsing if `/cost` output format changed. |
| Current overlap | Direct upgrade of existing infrastructure |
| Maintenance cost | None — already upgraded |
| Verdict | **Adopt** — verify stop hook fix, update cost parsing |

---

## Research Papers

### 4. SKILL0: In-Context Agentic RL for Skill Internalization (2604.02268)

| Field | Content |
|-------|---------|
| Source | [arxiv.org/abs/2604.02268](https://arxiv.org/abs/2604.02268) (519 views on alphaXiv) |
| What it does | Framework for LLM agents to internalize skills into model parameters via in-context RL. 87.9% success on ALFWorld, **5x token cost reduction** vs few-shot prompting. Skills start as in-context demonstrations, then get "compiled" into the model through self-play + reward. |
| Why relevant | Our skills are instruction-only (SKILL.md + context). SKILL0's "skill internalization" is the fine-tuning analog — moving from prompt-time skill injection to parameter-time. The 5x token reduction is significant given our context pressure. Not directly actionable (requires fine-tuning access) but validates the trajectory: skills as a training signal, not just a prompt. |
| Verdict | **Watch** — validates skill architecture direction, not actionable without fine-tuning access |

### 5. CORAL: Autonomous Multi-Agent Evolution (2604.01658)

| Field | Content |
|-------|---------|
| Source | [arxiv.org/abs/2604.01658](https://arxiv.org/abs/2604.01658) (135 views on alphaXiv) |
| What it does | Multi-agent system where agents autonomously control discovery and collaborate through **shared persistent memory**. SOTA on 8/11 optimization tasks. Agents evolve their own collaboration protocols. |
| Why relevant | The "shared persistent memory" mechanism parallels our MEMORY.md + improvement-log pattern (agents read/write shared state across sessions). Worth reading for their memory architecture — do they solve staleness/conflict better than our file-based approach? |
| Verdict | **Read** — shared memory architecture comparison |

### 6. Think Anywhere in Code Generation (2603.29957)

| Field | Content |
|-------|---------|
| Source | [arxiv.org/abs/2603.29957](https://arxiv.org/abs/2603.29957) (891 views on alphaXiv) |
| What it does | THINK-ANYWHERE enables token-level reasoning interleaved with code generation (not just before). 70.3% average pass@1, +9.3% absolute across four benchmarks. |
| Why relevant | Background context for understanding how reasoning models generate code. The finding that reasoning *during* generation (not just planning) helps is relevant to our extended thinking routing guidance. Not directly actionable but informs when to use thinking models for code tasks. |
| Verdict | **Note** — informs reasoning routing, not actionable |

### 7. Scale AI: Agentic Rubrics + ResearchRubrics (April 2-5)

| Field | Content |
|-------|---------|
| Source | [labs.scale.com/papers/agentic-rubrics](https://labs.scale.com/papers/) + [ResearchRubrics](https://labs.scale.com/papers/researchrubrics) |
| What it does | Scale Labs publishing on contextual verification rubrics for SWE agents and research agents. Rubrics as verifiers — generating task-specific evaluation criteria rather than using fixed benchmarks. |
| Why relevant | Our session-analyst already does rubric-like evaluation (anti-pattern detection, behavioral scoring). Scale's approach of generating rubrics per-task rather than using a fixed checklist could improve our epistemic evals. Worth reading the full papers. |
| Verdict | **Read** — evaluation methodology for session-analyst |

---

## Version Bumps

| Tool | Previous | Current | Notable Changes |
|------|----------|---------|-----------------|
| Claude Code | 2.1.91 | **2.1.92** | Stop hook fix (critical), per-model cost breakdown, Bedrock wizard, cache expiry hint, Write diff 60% faster. See finding #3. |
| Claude Agent SDK | 0.1.55 | **0.1.56** | Bundles CC 2.1.92. No new SDK features. |
| Kimi CLI | 1.29.0 | **1.30.0** | Session resilience (malformed context tolerance, interrupted turn events), `kimi export` preview, Grep `include_ignored` param, sensitive file protection for Grep/Read, 300s approval timeout |
| Google: Gemini 3.1 Flash-Lite | — | **preview** | `gemini-3.1-flash-lite-preview` available on Vertex AI. Pricing/benchmarks TBD. |

---

## Already Known (filtered out)

- Self-Distillation for Code (2604.01193) — already in research index (`self-distillation-code-generation-2026-04.md`)
- Meta-Harness (2603.28052) — already in research index (`meta-harness-deep-dive-2026-03.md`)
- Microsoft Agent Framework RC — tracked in `agent-ecosystem-weekly-2026-03-26.md`, now updated to 1.0 GA
- CrewAI 1.13.0a5-a7 — pre-release alphas, no notable stable changes
- OpenAI Agents SDK 0.13.4 — minor bugfix (sanitize AnyLLM responses)
- Codex CLI — still at 0.118.0 (March 31), no April releases
- Gemini CLI — still at 0.36.0 (April 1), no changes in window

## Actionable Summary

1. ~~**Verify stop hook behavior under CC 2.1.92**~~ — **DONE. Not affected.** The fix is for prompt-type Stop hooks only. All our Stop hooks (6 global: subagent-synthesis-gate, plan-gate, uncommitted-warn, verify-claims, debrief, notify) are command-type. The only prompt-type hook in the entire setup is a PreToolUse guard in Anki (unrelated).
2. ~~**Update vendor-versions baseline**~~ — **DONE.** Kimi CLI 1.26.0 → 1.30.0 (`uv tool upgrade`). Agent SDK 0.1.55 → 0.1.56 (`uv pip install --upgrade`).
3. **Read CORAL (2604.01658)** — shared persistent memory architecture, compare to our MEMORY.md approach.
4. **Read Scale Agentic Rubrics** — evaluation methodology for session-analyst improvement.
5. **Note MS Agent Framework 1.0 Claude Code SDK** — watch for preview → stable promotion.

## Search Log

| Source | Query | Useful? |
|--------|-------|---------|
| WebFetch | code.claude.com/docs/en/changelog | Yes — definitive CC 2.1.92 changelog |
| GitHub API | anthropics/claude-agent-sdk-python/releases | Yes — confirmed 0.1.56 is CC bundle only |
| Exa (advanced) | AI agent framework release April 2026 | Yes — MS Agent Framework 1.0, pydantic-deepagents |
| Brave | OpenAI Codex CLI changelog April 2026 | Confirmed no April releases |
| Exa (GitHub) | trending AI repos April 2026 | Oversized result (115K chars), needed contextMaxCharacters |
| Brave | Gemini CLI update April 2026 | Confirmed 0.36.0 still current |
| WebFetch | alphaXiv trending | Yes — 5 relevant papers, good SNR |
| Exa (papers) | LLM agent benchmark April 2026 | Oversized (195K chars), extracted Scale Labs + IBM ICSE papers |
| Brave | Kimi CLI April 2026 | Found 1.30.0 release |
| WebFetch | Kimi CLI changelog | Yes — full 1.30.0 details |

<!-- knowledge-index
generated: 2026-04-05T22:59:11Z
hash: bda3b253c7aa

title: Trending Scout — April 5, 2026
status: complete
tags: trending-scout, vendor-updates, claude-code, microsoft, research

end-knowledge-index -->
