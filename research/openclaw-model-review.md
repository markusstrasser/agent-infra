# OpenClaw Lessons — Model Review Synthesis

**Date:** 2026-03-01
**Models:** Gemini 3.1 Pro (pattern review), GPT-5.2 (quantitative/formal)
**Mode:** Convergent/critical
**Source plan:** `.claude/plans/f5607669-openclaw-lessons.md`
**Full review artifacts:** `.model-review/2026-03-01-openclaw-lessons-plan/`

## Key Corrections to Original Plan

### 1. UserPromptSubmit per-message hook rejected (both models)
Original plan proposed a prompt hook on every user message to check context usage and remind to save. Both models independently identified this as wrong:
- Different control loop than OpenClaw's automatic flush (reminder vs autonomous save)
- 20-50s latency per session
- "Soft fail-closed" UX (persistent friction)
- Violates fail-open principle

**Replacement:** Non-agentic PreCompact script that dumps state to checkpoint.md + rate-limited PostToolUse hook (3-8 checks/session, only when >75% context used). Conditional on CLIR data showing p > 0.2 incidents/session.

### 2. Measure before building (both models)
Both independently said: instrument Context-Loss Incident Rate before building any pre-compaction mechanism. Can't compute ROI without knowing incident frequency and cost. New Phase 0 added.

### 3. Skills gating is minimal impact (GPT)
465 chars (~80-120 tokens) saved is <1% of context. Do for cleanliness and preventing wrong-project tool invocation, not performance. Dynamic gating is better than manual symlink removal (both models).

### 4. Orchestrator needs hardening (both models)
- JSON output schema + 2-try error loop
- Self-observability (timeout/failure logging)
- Acceptance tests (edit-time, ship-ready rate)
- Race condition mitigation (separate write targets from foreground session)
- Doctor as automated first task

### 5. Cron confirmed over heartbeat (both models)
Both agree fresh-context cron is superior for task execution. Heartbeat accumulates context rot. Risk flagged: may lose "train of thought" for deep intel analysis — monitor.

## Verified: What OpenClaw Does Right (that we should adopt)

1. **Daily memory logs** — append-only buffer between session context and curated MEMORY.md
2. **Pre-compaction awareness** — their silent agentic turn is architecturally superior but we can't replicate it in Claude Code. Best we can do: non-agentic dump + rate-limited reminders.
3. **Heartbeat = orchestrator proof of concept** — validates periodic autonomous turns work at 300K+ user scale
4. **Doctor diagnostics** — single command for infrastructure health
5. **Skills gating** — load-time filtering prevents irrelevant skills from consuming prompt tokens

## Verified: What OpenClaw Does Wrong (that we should avoid)

1. **Agent-as-person philosophy** (SOUL.md self-modifiable) — our agent-as-tool model with human-owned CLAUDE.md is intentionally different and better for error correction
2. **Hooks can't block** — Claude Code hooks are strictly superior for enforcement
3. **No self-improvement pipeline** — OpenClaw has no session-analyst equivalent
4. **No cross-model review** — single-model system

## Sources
- OpenClaw GitHub: https://github.com/openclaw/openclaw (242K stars)
- Architecture deep dive: `research/openclaw-deep-dive.md` (source-verified from raw GitHub)
- Gemini review: `.model-review/2026-03-01-openclaw-lessons-plan/gemini-output.md`
- GPT review: `.model-review/2026-03-01-openclaw-lessons-plan/gpt-output.md`
- Extraction + disposition: `.model-review/2026-03-01-openclaw-lessons-plan/extraction.md`

<!-- knowledge-index
generated: 2026-03-21T23:52:36Z
hash: 17c314e17c2b

cross_refs: research/openclaw-deep-dive.md

end-knowledge-index -->
