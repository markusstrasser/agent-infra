# Nous Hermes Agent — scout for harness/RSI transfer (2026-06-30)

**One-line:** Nous Research's `hermes-agent` is the closest OSS analog to our
agent-infra/RSI thesis — it productizes agent-curated memory + autonomous skills
+ skill self-improvement + cross-session recall. Mostly **convergent validation**
of our design; **3 transferable mechanisms** clear the "survey missed it" bar.

Sources: docs site (hermes-agent.nousresearch.com/docs), GitHub
`NousResearch/hermes-agent` + `hermes-agent-self-evolution`, releases page.
Full scout notes: scratchpad `hermes-agent-scout-2026-06-30.md` (session
9b056ffd). Cross-ref: `research/2026-06-20-agent-workflow-orchestration-frameworks.md`
(we're frontier-for-context), `research/2026-05-27-multi-agent-coordination-4w.md`
(more-agents-flips-negative).

## Transferable (ranked)

1. **`hermes-agent-self-evolution` (separate repo) — GEPA over execution traces,
   verifier-gated. EVALUATE (high).** DSPy + GEPA (Genetic-Pareto Prompt Evolution)
   evolves SKILL.md / tool-descriptions / system-prompts / tool-code. GEPA consumes
   execution *traces* to infer *why* something failed (reflective, not pass/fail),
   proposes targeted edits, gates on constraint set: 100% test-pass, skill ≤15KB,
   cache-compat, semantic-purpose preserved, **human PR (no direct commits)**.
   No GPU, pure API, ~$2–10/run. = AlphaEvolve/ShinkaEvolve family applied to
   harness artifacts with a real verifier. Direct parallel to our dreamer/evolver +
   maintain-tick. **Open follow-up: scout this repo for build-or-adopt.**

2. **`execute_code` — sandboxed code that RPC-calls tools, collapsing N tool
   round-trips into 1 inference turn. LEARN.** Persistent Docker container holds
   state across calls. Genuine compute-allocation lever (fewer inference loops per
   pipeline); distinct from MCP tool-by-tool dispatch. Evaluate for batch/fan-out.

3. **Memory as frozen snapshot at session start + Anthropic cache breakpoints on
   the Stable tier only. CHECK OURS.** Three-tier prompt (Stable identity/tools/skills
   / Context / Volatile memory+profile+timestamp); memory writes hit disk immediately
   but only surface next session, to preserve the prefix cache. Riskless to verify
   our always-loaded tier is cache-stable and MEMORY.md isn't mutated mid-session.

## Convergent (1:1 with ours — validation, not new)
- SKILL.md format + YAML frontmatter (agentskills.io standard) + When-to-Use/Procedure/
  Pitfalls/Verification sections.
- MEMORY.md (~800 tok env/conventions) + USER.md (~500 tok prefs) split = our
  MEMORY.md + how-I-work-with-Markus.
- Autonomous-skill-creation triggers (after 5+ tool-call success / post-correction /
  post-deadend / non-trivial workflow) — same as our graduation triggers, codified
  as agent-visible rules.
- Skill write-approval staging queue (`/skills pending|diff|approve|reject`) =
  decisions-pending / HUMAN.md verifier-conditioned-autonomy surface.
- Background self-improvement review after each turn on a cheaper model
  (`auxiliary.background_review`, gated by `write_approval`) = maintain-tick/observe.

## SKEPTICAL
- Last-month direction is **scaling OUT**: Kanban multi-agent swarm with
  auto-decomposition + swarm topologies, background/async subagents with
  handle-based returns, per-task model overrides, ~23 messaging surfaces. Adopt
  the **handle-based async-subagent return** only; our 2026-05-27 + CAID evidence
  says "more agents / swarm" frequently flips negative.

## Trust caveats
- **Repo metrics not credible.** Scout reported "~206k stars / 390 contributors"
  (claimed Exa-verified) for a repo created 2025-07-22 — internally inconsistent and
  implausible (top-of-GitHub territory). Probable scrape/conflation error; mechanism
  findings do NOT depend on it.
- README markets "FTS5 + LLM summarization" and "Honcho dialectic modeling" as core;
  the docs page says summarization is explicitly avoided and Honcho is 1 of 8 optional
  plugins. Trust the docs page on mechanism.
- Release version numbers inconsistent (`v0.17` vs `v2026.6.19`); themes reliable,
  figures not. Blog-post dates not exposed; `gh api` 401 (no creds).

## Verdict
No framework to adopt wholesale (convergent with ours). Real ROI is #1 — a no-GPU,
trace-reflective, verifier-gated evolver for harness artifacts is exactly what we'd
otherwise hand-build. Worth a focused build-or-adopt scout of `hermes-agent-self-evolution`.
