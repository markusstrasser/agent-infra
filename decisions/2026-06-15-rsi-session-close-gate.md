---
id: 2026-06-15-rsi-session-close-gate
concept: rsi-session-close
repo: agent-infra
decision_date: 2026-06-15
recorded_date: 2026-06-15
provenance: contemporaneous
status: accepted
initial_leaning: "Gate full RSI close on /goal achieved via SessionEnd transcript parse"
relations:
  - type: depends_on
    target: 2026-06-13-rsi-outer-loop-skill
  - type: branches_from
    target: 2026-06-04-consumption-over-autonomy
---

# 2026-06-15: Goal-gated RSI session close (two-tier, platform-split)

## Context

The recursive learning loop already captures correction signals at SessionEnd via
`reflect_capture.py` (Tier 0, zero-LLM). Full session close — digest + evidence attach +
optional steward proposal — was firing too rarely (capture >> actuation) and too often
on mid-goal interrupts (15 false Stop nags when externally blocked on genomics SR lane).

Vendor sweep + adversarial critique (Claude Opus + Codex high, 2026-06-15) confirmed:
Claude `/goal` and Codex `thread/goal/*` APIs exist; SessionEnd has no goal field;
SessionEnd default timeout is 1.5s; `background_tasks` is Stop-scoped only; transcript
marker schema for Claude goal-achieved is unverified until probed.

## Alternatives considered

1. **Hook Stop for RSI close** — reuse turn boundary. Rejected: collides with `/goal`'s
   per-turn Haiku evaluator; jw retro showed ~15 false nags when blocked-on-external.
2. **Always run full close on SessionEnd** — simple. Rejected: 888/1000 reflect-capture
   signals are retry_run noise; mid-goal sessions need capture-only.
3. **Two-tier with goal-gated Tier 1 (chosen)** — Tier 0 always; Tier 1 when goal
   achieved, explicit `/rsi close`, or strong operator signal (#f).
4. **Codex-only via app-server from SessionEnd** — no transcript parse. Rejected as sole
   path: Claude Code has no SessionEnd goal field; need transcript + optional Stop cache.

## Counterevidence sought

- Searched local `~/.claude/projects` for `goal_status` / "Goal achieved" — zero hits.
  Marker schema must come from synthetic fixtures + live probe before parser is trusted.
- Confirmed SessionEnd hooks in `~/.claude/settings.json` are already `async: true` — the
  1.5s cliff is real for sync hooks but mitigated for our wiring; Tier 1 still runs async.
- Confirmed `background_tasks` absent from SessionEnd payload — blocked-skip cannot infer
  from SessionEnd alone.

## Decision

Adopt two-tier goal-gated session close:

| Condition | Tier 0 (capture) | Tier 1 (digest + `/rsi close`) |
|-----------|------------------|--------------------------------|
| Goal achieved (verified detector) | yes | yes |
| User `/rsi close` or explicit retro | yes | yes |
| `#f` or high correction density | yes | yes |
| Goal active, not achieved | yes | **skip** |
| Goal `blocked` / external wait | yes | **skip** (capture-only) |
| Detector `unknown` (marker drift) | yes | skip + `[DEGRADED]` log |

**Vetoes (non-negotiable):**
- Never hook `Stop` for RSI close.
- No LLM on SessionEnd hook path.
- Episode boundary = first achieved timestamp, not whole session after post-goal chat.
- `/goal` Haiku evaluator is a proxy; `/rsi close` verifies one load-bearing claim independently.

**Platform split:**
- **Claude Code:** `goal_state_from_transcript()` — attachment `goal_status.met`, text
  "Goal achieved", slash `/goal clear`; fail-loud `unknown` on drift.
- **Codex:** `goal_state_from_codex()` — `thread/goal/get`; map `complete`→achieved,
  `blocked`/`budgetLimited`/`usageLimited`→blocked.

**Async drain:** SessionStart hook drains `~/.claude/close-queue/` via
`reflect_session_close.py`; nudge when `invoke_skill: true`.

## Evidence

- Vendor docs: code.claude.com/docs/en/goal, hooks SessionEnd/Stop; Codex app-server README,
  developers.openai.com/codex/use-cases/follow-goals.
- Critique artifacts: genomics `.model-review/critique-rsi-close-{claude,codex}.md`.
- Empirical: reflect-capture retry_run dominance; genomics jw blocked-on-external false nags.

## Revisit if

- Live probe disproves Claude transcript marker shapes → update fixtures + detector v2.
- Codex `status: complete` renamed → update codex mapper.
- SessionEnd gains native `goal_achieved` field → prefer vendor field over transcript parse.

## Supersedes

None. Complements plan `4d40085a-recursive-session-learning-loop` shadow→PPV machinery.
