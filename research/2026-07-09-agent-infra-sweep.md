---
title: Agent-infra frontier sweep — delta since 2026-06-24
date: 2026-07-09
tags: [rsi, harness, agent-infra, sweep]
status: complete
prior: research/2026-06-24-rsi-loop-vs-harness-evolution-sweep.md
window: 2026-06-24 → 2026-07-09
---

# Agent-infra Frontier Sweep — 2026-07-09 (15-day delta)

**Question:** What changed in agent/RSI/harness land since the Jun 24 RSI-vs-harness-evolution sweep — external (papers/vendor) and internal (what we built/consumed)?

**Prior baselines:** `research/2026-06-24-rsi-loop-vs-harness-evolution-sweep.md`, `research/trending-scout-2026-06-24.md`, `research/2026-06-15-agent-infra-sweep.md`.

---

## Verdict

**External:** one structure event — **Grok 4.5 inside the Cursor harness** (joint train + first-party pool). Treat as named niche (AA: capability frontier, calibration mid-pack), not a Default Routing flip. CC 2.1.198–205 is mostly background-agent + hook-contract hardening.

**Internal:** loop is consuming — Grok transport/critique axis, pulse empty-day false-alarm fix, usage-check PRICING sync, hook `+x` durable modes, top_priorities open-finding filter (April Status-noise). Freshness workers were 15d stale; this memo + trending-scout-2026-07-09 clear them.

No new adopt-grade external infra beyond Grok niche wiring already landed this session.

---

## External — worth knowing

| Item | Read | Action |
|------|------|--------|
| Grok 4.5 (Cursor + xAI) | Opus-class pitch; CursorBench contaminated; AA Intelligence ~54, non-hallucination ~46% | Named niche only — decision already accepted |
| CC background-agents default (2.1.198) | Subagents async by default; Notification hook events | Evaluate maintain/scout wait assumptions |
| SessionStart headless stream (2.1.204) | Idle-reap fix | Vendor fix — no build |
| HarnessFix / MiMo-Code (prior sweep) | Still the measurement thesis | Watch — no new paper delta this pass |

## Internal — built & integrated (Jun 24→Jul 9, highlight)

| Ship | Evidence | Loop-health |
|------|----------|-------------|
| Grok 4.5 transport + critique `grok` axis | `decisions/2026-07-09-grok-4.5-transport.md`, skills model-guide/critique | Generate→consume same session |
| Pulse empty-day NO_DATA (not NULL ALARM) | `scripts/pulse.py` | False-alarm class closed |
| usage-check ↔ llmx PRICING drift fix | `scripts/usage-check.py` + drift test | Metered-spend single source |
| Hook git `+x` for 2 entrypoints | skills hooks index 100755 | Doctor detect → durable mode |
| top_priorities open-finding filter | `scripts/top_priorities.py` | April Status-noise removed |
| Skill usage audit + meter split | research/2026-07-06-skill-usage-value-audit.md | Consume channel honesty |
| Fable 5 metered off-subscription | model-guide 2026-07-07 | Routing honesty |

## What not to build
- Default-route to Grok (calibration + CursorBench contamination).
- New scout backend named `grok` — use `--scout-model grok-4.5-xhigh` on cursor.
- Duplicate `/doctor` as a CC wrapper — complementary surfaces.

## Next triggers
- Dogfood `--axes standard,grok` on a real PLAN; measure premise yield.
- Unblock `XAI_API_KEY` → live xAI smoke.
- Evaluate Notification-hook consumer if background-subagent supervision rises.
