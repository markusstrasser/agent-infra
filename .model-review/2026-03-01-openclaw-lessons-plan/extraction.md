# Extraction & Disposition — OpenClaw Lessons Plan Review

## Extraction: gemini-output.md

G1. UserPromptSubmit prompt hook is an anti-pattern — fights native architecture, brittle Haiku token-counting, latency
G2. Manual symlink removal is configuration not architecture — violates generative principle (requires ongoing supervision)
G3. Daily logs risk unbounded context bloat without temporal decay/pruning — no pruning mechanism planned
G4. Heartbeat (persistent session) is strictly inferior to cron (fresh context) for task execution
G5. Concurrency/thread safety: orchestrator + foreground user both writing to shared MEMORY.md = race conditions
G6. Orchestrator MVP lacks self-observability for its own failure rate (stuck subprocess, timeouts)
G7. Lane model missing task dependency resolution — blind priority-pull from SQLite won't handle prerequisite logic
G8. Phase 2 proposes a new hook without telemetry for false-positive measurement (violates Principle 3)
G9. Phase 1 alternative: use native subagent memory + record-to-sqlite skill instead of daily Markdown logs
G10. Phase 2 alternative: non-agentic PreCompact script dumps buffer to .jsonl, separate cron summarizes to MEMORY.md
G11. Phase 3 upgrade: dynamic wrapper/hook that masks skills per-project instead of manual symlinks
G12. Phase 4 refinement: enforce JSON output schema, error-correction loop (2 tries), then FAILED status
G13. Phase 5 upgrade: run doctor as first task in orchestrator's maintenance lane daily
G14. Priority reorder: Orchestrator first (directly drives autonomy metric)
G15. Blind spot: may underestimate context loss severity — UserPromptSubmit might be worth the latency
G16. Blind spot: fresh-context cron may destroy "train of thought" for deep qualitative analysis (intel)

## Extraction: gpt-output.md

P1. Token/char dimensional inconsistency — "2% of context (~16K chars)" conflates tokens and chars
P2. Skills gating saves ~465 chars (~80-120 tokens), only 2.9% of skills budget — materiality not established
P3. Phase 2 objective contradicts stated constraint — UserPromptSubmit is different control loop than OpenClaw's automatic flush, not a substitute
P4. "30% context preservation improvement" is ungrounded — no operational definition, not falsifiable
P5. Heartbeat vs cron already decided architecturally — question is moot, plan already committed to cron
P6. Phases 1/2/3/5 not connected to primary metric (autonomous-to-supervised ratio) — only Phase 4 targets it
P7. UserPromptSubmit can become "soft fail-closed" UX (persistent friction) — violates fail-open principle
P8. Breakeven for Phase 2: need p·H ≥ 2.77 min/session (p=incident freq, H=cost per incident) — if p low, not worth it
P9. Instrument Context-Loss Incident Rate (CLIR) before changing hooks — can't compute ROI without it
P10. Replace per-message eval with rate-limited "near-compaction sentinel" — check only every N turns or M tokens, reduce to 3-8 checks/session
P11. Add hard kill-switch + staged rollout for high-blast-radius hooks — env var disable, 1 project first
P12. Define acceptance tests for orchestrator outputs — edit-time, ship-ready rate, duplication rate, error count
P13. Make skills gating dynamic (load on-demand) rather than static per-project
P14. Testable predictions: P1 (80% capture within 2min), P2 (MEMORY.md churn ↓50%), P4 (reminder precision ≥70%), P7 (autonomy ≥96%), P10 (doctor diagnosis time ↓50%)
P15. Constitutional alignment quantified: Architecture-over-instructions 70%, Measure-before-enforcing 55%, Self-mod-reversibility 60%, Recurring-patterns 65%, Cross-model 40%, Fail-open 50%
P16. Blind spot: may undervalue small prompt savings if compaction is highly sensitive to marginal tokens

---

## Disposition Table

| ID | Claim (short) | Disposition | Reason |
|----|--------------|-------------|--------|
| G1 | UserPromptSubmit anti-pattern | INCLUDE — revise Phase 2 | Valid concern. Per-message Haiku eval is expensive and fights native architecture. GPT agrees (P3, P7, P8). |
| G2 | Manual symlinks ≠ architecture | INCLUDE — upgrade Phase 3 | Both models agree: static symlink removal is config, not architecture. Dynamic masking is better (G11, P13). |
| G3 | Daily logs context bloat risk | DEFER | Risk is theoretical — daily logs are ~0.5-1KB/day and only today+yesterday loaded. Not "unbounded." Gemini may be overestimating. |
| G4 | Cron > heartbeat for orchestrator | INCLUDE — confirm design | Both models agree fresh-context cron is right for task execution. Keep current spec. |
| G5 | Concurrency: shared MEMORY.md race | INCLUDE — address in Phase 4 | Valid. Orchestrator and foreground user can collide. Need file locking or separate write targets. |
| G6 | Orchestrator needs self-observability | INCLUDE — add to Phase 4 | Valid gap. Timeout kills, partial failures need structured logging. |
| G7 | Lane model needs dependency resolution | DEFER | Over-engineering for N=3 task types with no dependencies. Add when needed. |
| G8 | Phase 2 needs hook telemetry | MERGE WITH P9 | Both say: measure first, then enforce. |
| G9 | Use subagent memory instead of daily logs | REJECT | Subagent memory is per-subagent, not per-session. Different use case. Daily logs capture main session context. |
| G10 | Non-agentic PreCompact script + cron summarize | INCLUDE — alternative Phase 2 | Better than per-message hook. PreCompact dumps state, separate process curates. Avoids latency. |
| G11 | Dynamic skills masking via hook | MERGE WITH P13 | Both suggest dynamic over static. |
| G12 | Orchestrator JSON schema + error loop | INCLUDE — add to Phase 4 | Good hardening. 2-try then FAILED is sound. |
| G13 | Doctor as orchestrator maintenance task | INCLUDE — upgrade Phase 5 | Removes human dependency. Aligns with autonomy goal. |
| G14 | Prioritize orchestrator first | DEFER | Orchestrator depends on Phase 1 (daily logs for memory persistence) and Phase 5 (doctor for health checks). Current order makes sense for dependencies. |
| G15 | May underestimate compaction damage | INCLUDE — flagged risk | Both models flag this. Need CLIR data (P9). |
| G16 | Cron may lose train-of-thought | INCLUDE — flagged risk | Valid for intel deep analysis. Monitor after orchestrator deployment. |
| P1 | Token/char confusion | INCLUDE — fix in plan | Dimensional error. Skills budget is chars, context is tokens. Fix the comparison. |
| P2 | Skills gating materiality low | INCLUDE — right-size expectations | 465 chars / 80-120 tokens is <1% of context. Not a compaction-driver. Do for cleanliness, not performance. |
| P3 | Phase 2 ≠ OpenClaw's flush | INCLUDE — acknowledge honestly | UserPromptSubmit is a different control loop (reminder vs automatic). Plan should not claim equivalence. |
| P4 | 30% improvement ungrounded | INCLUDE — remove claim | Agree. Remove the specific number. Replace with measurable CLIR reduction target. |
| P5 | Heartbeat already decided | INCLUDE — clean up plan | Remove the "open question" — plan already committed to cron. |
| P6 | Most phases don't target primary metric | INCLUDE — add metric connections | Fair. Connect each phase to how it reduces supervision or increases autonomy. |
| P7 | Fail-open violation risk | MERGE WITH G1 | Part of same concern about UserPromptSubmit. |
| P8 | Breakeven arithmetic | INCLUDE — add to plan | Formalize: need p·H ≥ 2.77 min/session for Phase 2 to be net positive. |
| P9 | Instrument CLIR first | INCLUDE — new prerequisite | Both models agree. Measure context-loss incidents before building Phase 2. |
| P10 | Rate-limited sentinel | INCLUDE — adopt for Phase 2 if building | If we build Phase 2 at all: rate-limit to 3-8 checks/session, not every message. |
| P11 | Kill-switch + staged rollout | INCLUDE — standard practice | Apply to any new hook with global blast radius. |
| P12 | Orchestrator acceptance tests | INCLUDE — add to Phase 4 | Define ship-ready rate, edit-time, duplication before deployment. |
| P13 | Dynamic skills gating | INCLUDE — upgrade Phase 3 | Dynamic > static. But note: Claude Code has no native skill gating mechanism, so this requires a PreToolUse hook or similar. |
| P14 | Testable predictions | INCLUDE — add to plan | Strong set. Adopt P1 (capture rate), P2 (churn), P7 (autonomy), P10 (doctor speed). |
| P15 | Constitutional scores | INCLUDE — reference for context | Useful benchmark. Measure-before-enforcing at 55% is the biggest gap. |
| P16 | May undervalue skills savings | DEFER | Only relevant if compaction is token-sensitive. Not established yet. |

## Coverage
- **Total extracted:** 32 (G: 16, P: 16)
- **Included:** 22
- **Deferred:** 4 (G3, G7, G14, P16)
- **Rejected:** 1 (G9)
- **Merged:** 5 (G8→P9, G11→P13, P7→G1, counted once each → net 3)
