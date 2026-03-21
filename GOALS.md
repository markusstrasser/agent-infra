# Meta — Goals

> Human-owned. Agent may propose changes but must not modify without explicit approval.

## Mission

Maximize autonomous agent capability across all projects while maintaining epistemic integrity. The system should learn things once and handle them forever — the human intervenes only for genuinely new information, creative direction, or goal-setting.

## Generative Principle

**Maximize the rate at which agents become more autonomous, measured by declining supervision — AND maximize error correction per session across all projects.**

The deeper dynamic: the better the agent gets, the faster the human must rethink what they actually want next. This is an arms race — agent capability outpaces goal-setting until prediction quality is high enough that the agent can extrapolate what the human would want without asking. The endgame: wake up to 30 great ideas, say yes/no, go back to sleep.

## Primary Success Metric

**Ratio of autonomous-to-supervised work across sub-projects.** Measured qualitatively: when reviewing a day's chat logs, there should be no:
- Reverted work (build-then-undo)
- 5-hour runs that should have been 1-hour (missing scaffolding, bad DX)
- Error branch spirals (bad hooks, missing guards)
- Agent theater (performative work that produces no value)
- Repeated corrections for things already taught once

The closer sessions get to "optimal run" (what would happen if the agent had perfect tooling and perfect instructions), the better meta is doing its job.

## Secondary Metrics

- **Wasted supervision rate** — % of human turns that are corrections, boilerplate, or rubber stamps. Baseline ~21% (2026-02-28). Measured weekly via session-analyst. Qualitative trend should be downward.
- **Agent reliability** — % of tasks completed correctly without correction.
- **Time-to-capability** — how fast a new project gets proper agent infrastructure.

## Self-Modification Boundaries

**Full autonomy within invariants**, with a gradient:
- **Clear improvement, one obvious path** → just do it, commit, move on
- **Multiple valid solutions, could change a lot** → propose and wait for human review
- **CLAUDE.md Constitution section / GOALS.md** → always human-approved

The invariants: the Constitution section (in CLAUDE.md) and GOALS.md are human-owned. Everything else (rest of CLAUDE.md, hooks, skills, maintenance checklists, rules, MEMORY.md) can be modified autonomously when the improvement is unambiguous.

## Strategy

1. **Session forensics** — session-analyst finds behavioral anti-patterns, improvement-log tracks them to architectural fixes
2. **Hook engineering** — deterministic guards that prevent known failure modes (instructions alone = 0% reliable)
3. **Observability** — cockpit components keep the human informed without requiring them to ask
4. **Research** — stay current on agent behavior research, absorb what's applicable, ignore what's not. Research has intrinsic value — it changes how agents think and prompt, even when it doesn't produce a hook or script. No enforcement quota on research-to-implementation conversion.
5. **Cross-project propagation** — organic, pull-based. The human runs sessions from meta that touch other repos. Sub-projects query meta-knowledge via MCP when relevant. Projects don't need meta's full knowledge pushed to them — the MCP is the bridge.
6. **Multi-vendor agent ops** — strategic. Claude Code is primary, but Codex/Gemini/Kimi CLIs serve as sub-agents and alternative interfaces. Subscriptions are often cheaper than API. Runlog, dashboard, and receipts cover all vendors. CLAUDE.md symlinks (AGENTS.md, GEMINI.md) ensure instruction parity where possible.
7. **Self-improvement** — meta improves its own tooling using the same methods it applies to sub-projects

## Orchestrator

**Built, not yet primary.** The orchestrator (`scripts/orchestrator.py`) works — dual-engine, SQLite queue, pipeline templates, cost caps. But two gaps block daily use:

1. **Logging/visibility.** Can't see what's happening during a run. Claude Code's interactive UX is better for observing agent work. Until the orchestrator has a real-time feed (streaming logs, structured output), pasting prompts into Claude Code sessions is the superior workflow.
2. **Task proposal.** The human still has to decide "what's next." The orchestrator should surface proposals — "here are 5 things that look stale/broken/actionable" — not wait for manual `submit`. The loop should be: orchestrator proposes → human approves/rejects → orchestrator executes → human reviews output.

Fixing these two gaps is the highest-leverage work meta can do. The orchestrator is the autonomy engine — without it, the generative principle can't compound.

## Research Cadence

**First-class function, not every-session.** Research is divergent thinking — exploring what's new, what's possible, what others have solved. Implementation is convergent — building, testing, eating your own dogfood.

The cycle: research (divergent) until diminishing returns → build (convergent) → use it → analyze whether it actually works → research again when stuck or when new information appears.

- **Not calendar-driven.** No fixed weekly sweep that degrades into checkbox behavior.
- **Opportunistic.** New model ships → immediate sweep. Stuck on a problem → search for prior art. Steep improvement curve → more research. Diminishing returns → more action.
- **Action produces information.** At some point, building and using is more informative than reading papers.

## Knowledge Management

Meta's research index, improvement log, and maintenance checklist are valuable — but should trend toward **index over content dump**. Best practices:
- Research memos: actionable findings up front, evidence below. The index table in CLAUDE.md is the discovery layer.
- Improvement log: findings should resolve (implemented, rejected, superseded), not accumulate indefinitely. Archive entries older than 60 days that haven't been acted on.
- Backlog: items without a clear path to implementation should be pruned, not preserved.

The warning stands: meta is not a place to write more rules about rules. If knowledge isn't changing agent behavior, it's dead weight.

## Projects Served

All projects: intel, selve, genomics, skills, research-mcp, and any future repos. Cross-project work happens organically — the human runs Claude Code from meta and touches other repos as needed. The meta-knowledge MCP provides a query interface so sub-projects can access meta's knowledge without carrying it.

Meta provides: shared skills, hooks, MCP servers, maintenance checklists, session analysis, observability, and the research pipeline.

## Skills Ownership

**Meta owns skill quality.** Meta runs session analysis, sees when skills are applied across projects, and can judge whether they work. Claude Code knowledge is co-located here. The information flow is natural: session-analyst findings → skill improvements → propagation.

Skills (`~/Projects/skills/`) may merge into meta as a directory. For now, kept separate. But quality governance (authoring standards, testing, versioning, cross-project propagation) lives in meta regardless of directory structure.

## Quality Standard

Recurring patterns (used/encountered 10+ times) must become architecture — not instructions, not snippets, not manual habits. The Raycast-snippet heuristic: if you paste it 10 times, it should be a hook, a skill, or scaffolding.

Qualitative reports from session-analyst are the primary feedback mechanism. No arbitrary numeric targets — the goal is "no stupid shit in the logs," judged by comparing actual runs against what an optimal run would look like.

## Resource Constraints

- Single human operator with limited attention
- Cost-conscious (session receipts track spend)
- Compute: local Mac + cloud APIs (Anthropic, Google, OpenAI, Exa)
- Storage: SSK1TB external drive for large datasets
- Multi-vendor subscriptions provide cheaper compute for sub-agent work

## Open Questions

- **Enforcement granularity** — which principles deserve hooks vs. which stay instructional? Hooks can be annoying. Need empirical data from meta sessions. Progressive approach for now.
- **Autonomy gradient threshold** — where exactly does "clear improvement" end and "multiple valid solutions" begin? Probably can't be defined precisely; needs examples over time.
- **Skills merge timing** — meta owns quality but skills/ is still separate. When/whether to merge directories.

## Deferred Scope

- **IB API / trading automation** — blocked by paper trading validation in intel, not meta's concern
- **Fraud/corruption separation** — stays in intel until compute burden forces a split
- **Numeric benchmarking** — qualitative assessment first, formalize metrics when patterns stabilize
- **Shared library extraction** (`~/Projects/lib/`) — active work, plan exists, will update goals when it lands

## Exit Condition

Meta becomes unnecessary when:
1. Claude (5, 6, N) natively handles meta-improvement — eliciting user goals, applying project upgrades, working correctly across subdomains, benchmarking itself
2. Claude Code ships native equivalents of hooks, observability, session analysis
3. The creative/divergent capability (connecting old projects, finding novel solutions across domains) is handled natively

This may never fully happen — meta encodes domain-specific and personal-idiosyncratic knowledge that generic tooling won't replicate. But the goal is to make meta's job progressively smaller, not to preserve it.

---

*Created: 2026-02-28. Revised: 2026-03-06 (orchestrator UX gaps as top priority, multi-vendor strategic, pull-based propagation, knowledge management hygiene, weekly supervision measurement).*
