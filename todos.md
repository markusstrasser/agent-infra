checklists
benchmarks
evals
comparison runs

## Deferred (OpenClaw plan, 2026-03-01)

- [ ] **Context-save hook (Phase 2):** If CLIR shows >0.2 context-loss incidents/session after 20 compactions, build rate-limited PostToolUse prompt hook (trigger at >75% context, 3-8 checks/session, kill-switch env var). Prereq: 20+ CLIR data points in `~/.claude/compact-log.jsonl`.
- [ ] **Dynamic skills gating (Phase 3B):** Per-project skill masking when skill count exceeds 25. Architecture over configuration — not needed at current scale (~14 shared skills).
- [ ] **Doctor in orchestrator:** Wire `scripts/doctor.py` as first task in orchestrator maintenance lane (daily automated run). Blocked on orchestrator MVP (see `.claude/plans/3a65775d-orchestrator.md`).
