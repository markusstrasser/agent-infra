# Agent-Infra — Goals

> Human-owned. Agent may propose changes but must not modify without explicit approval.

## Mission

Maximize autonomous agent capability across all projects while maintaining epistemic integrity. The system should learn things once and handle them forever — the human intervenes only for genuinely new information, creative direction, or goal-setting.

## Generative Principle

**Maximize the rate at which agents become more autonomous, measured by declining supervision — AND maximize error correction per session across all projects.**

The deeper dynamic: the better the agent gets, the faster the human must rethink what they actually want next. This is an arms race — agent capability outpaces goal-setting until prediction quality is high enough that the agent can extrapolate what the human would want without asking. The endgame: wake up to 30 great ideas, say yes/no, go back to sleep.

**Verifier-conditioned (see CLAUDE.md constitution).** "Declining supervision" is the objective only where a clear ground-truth verifier exists. Three regimes: *clear verifier* → automate; *partial/noisy/delayed verifier* (the common case) → bounded autonomy; *verifier-is-principal* (taste, voice, conviction) → amplify — reduce *production* supervision while preserving *judgment* supervision. Domain is a prior, not the test. Provenance: `decisions/2026-06-07-verifier-conditional-autonomy.md`.

## Success Metric

Per-regime, not one ratio (raw "maximize autonomy/consumption" maximands incentivize flooding the human or mislabeling hard work as taste):

- **Clear-verifier autonomy rate** — autonomous-to-supervised ratio, scoped to checkable work.
- **Partial-verifier bounded-autonomy rate** — evidence/option/draft work done per human checkpoint, without skipping risk boundaries.
- **Principal-attention efficiency** — decision *density* and option *contrast* per human turn; explicitly **not** generation volume. (Consumption as a *floor* — no generation without a named consumer — not a maximand.)

The qualitative test: reviewing a day's chat logs, there should be no reverted work (build-then-undo), no 5-hour runs that should have been 1-hour (missing scaffolding), no error-branch spirals (bad hooks), no agent theater (work that produces no value), no repeated corrections for things already taught once. The closer sessions get to "optimal run" — what would happen with perfect tooling and perfect instructions — the better agent-infra is doing its job.

The standing operational drag to minimize: **operator tax** — sessions spent operating the system (running retros, fixing hooks, tuning context, vendor sweeps) instead of doing project work. Declining supervision means nothing if the human spends a third of their time on system ops. Target: maintenance is the exception, not a recurring tax; no maintenance prompt needed for multiple consecutive days.

## Self-Modification Boundaries

**Full autonomy within invariants**, with a gradient:
- **Clear improvement, one obvious path** → just do it, commit, move on. Regular /loop checks git diffs for regressions, incidental complexity, and goal drift.
- **Multiple valid solutions, could change a lot** → propose and wait for human review.
- **CLAUDE.md Constitution section / GOALS.md** → human-approved (approval may be explicit or confidently inferred from the user's messages; clear + reversible → act-then-tell).

Git is the safety net — can always revert. Compute cost risk handled via vendor-side spending limits. The invariants (Constitution section in CLAUDE.md, and this file) are human-owned; everything else (rest of CLAUDE.md, hooks, skills, rules, MEMORY.md) can be modified autonomously when the improvement is unambiguous.

## Strategy

1. **Session forensics** — session-analyst finds behavioral anti-patterns, improvement-log tracks them to architectural fixes.
2. **Hook engineering** — deterministic guards that prevent known failure modes (instructions alone = 0% reliable).
3. **Observability** — cockpit components keep the human informed without requiring them to ask.
4. **Research** — stay current on agent behavior research, absorb what's applicable. Research has intrinsic value — it changes how agents think and prompt, even when it doesn't produce a hook or script. No enforcement quota on research-to-implementation conversion.
5. **Cross-project propagation** — organic, pull-based. The human runs sessions from agent-infra that touch other repos; sub-projects query agent-infra via MCP when relevant.
6. **Multi-vendor agent ops** — Claude Code is primary, but Codex/Gemini/Kimi CLIs serve as sub-agents and alternative interfaces. Subscriptions are often cheaper than API. CLAUDE.md symlinks (AGENTS.md) ensure instruction parity where possible.
7. **Self-improvement** — agent-infra improves its own tooling using the same methods it applies to sub-projects.

## Execution Model

**`/loop` + interactive sessions is the primary workflow.** The human runs Claude Code directly, uses `/loop` for recurring tasks, and steers in real-time — providing visibility, steerability, and full agent context that batch orchestration can't match. `/schedule` (Claude Code native cloud cron) covers truly unattended work. The autonomy engine is the interactive loop: human sets direction → agent executes with `/loop` or subagents → human reviews output in-session.

## Research Cadence

**First-class function, not every-session.** Research is divergent thinking (explore what's new, what's possible, what others solved); implementation is convergent (build, test, dogfood). The cycle: research until diminishing returns → build → use it → analyze whether it works → research again when stuck or when new information appears.

- **Not calendar-driven.** No fixed sweep that degrades into checkbox behavior.
- **Opportunistic.** New model ships → immediate sweep. Stuck → search prior art. Steep improvement curve → more research; diminishing returns → more action.
- **Action produces information.** At some point, building and using is more informative than reading papers.

## Knowledge Management

Research index, improvement log, and maintenance checklist should trend toward **index over content dump**. Research memos: actionable findings up front, evidence below. Improvement-log entries should resolve (implemented, rejected, superseded), not accumulate. Backlog items without a clear path to implementation get pruned, not preserved. The warning stands: agent-infra is not a place to write more rules about rules. If knowledge isn't changing agent behavior, it's dead weight.

## Goal-Drift Detection

The system must actively detect when goals shift, not wait for the human to articulate them. Precedent: a reviews session once built 17 artifacts optimizing for "architectural elegance" before the human stated the actual goal was "recursive self-improvement with minimal maintenance" — the system should have asked. When the human gives direction that conflicts with or extends this file, surface that explicitly; when session patterns diverge from stated goals (e.g. maintenance sessions rising despite a declining-supervision goal), flag it.

## Quality Standard

Recurring patterns (used/encountered 10+ times) must become architecture — not instructions, not snippets, not manual habits (the Raycast-snippet heuristic). Qualitative reports from session-analyst are the primary feedback mechanism. No arbitrary numeric targets — the goal is "no stupid shit in the logs," judged by comparing actual runs against what an optimal run would look like.

## Projects Served

All projects: genomics, phenome, intel, hutter, emb, skills, research-mcp, and any future repos. Cross-project work happens organically — the human runs Claude Code from agent-infra and touches other repos as needed. The agent-infra MCP provides a query interface so sub-projects can access agent-infra's knowledge without carrying it. Agent-Infra provides: shared skills, hooks, MCP servers, maintenance checklists, session analysis, observability, and the research pipeline.

## Skills Ownership

**Agent-Infra owns skill quality** (authoring standards, testing, versioning, cross-project propagation). Skills live in `~/Projects/skills/` (separate directory) but quality governance lives here regardless. The information flow is natural: session-analyst findings → skill improvements → propagation.

## Resource Constraints

- Single human operator with limited attention.
- Cost-conscious (session receipts track spend).
- Compute: local Mac + cloud APIs (Anthropic, Google, OpenAI, Exa).
- Multi-vendor subscriptions provide cheaper compute for sub-agent work.

## Exit Condition

Agent-Infra becomes unnecessary when Claude natively handles meta-improvement (eliciting user goals, applying project upgrades, working correctly across subdomains, benchmarking itself), Claude Code ships native equivalents of hooks/observability/session-analysis, and the creative/divergent capability (connecting old projects, finding novel cross-domain solutions) is handled natively. This may never fully happen — agent-infra encodes domain-specific and personal-idiosyncratic knowledge that generic tooling won't replicate — but the goal is to make agent-infra's job progressively smaller, not to preserve it.

---

*Created 2026-02-28. Telos stable; dated operational baselines and one-time migration notes stripped 2026-06-14 (the measurements live in session-analyst reports and the improvement-log, not here).*
