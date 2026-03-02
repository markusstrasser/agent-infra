# Cross-Model Review: OpenClaw Lessons Implementation Plan

**Mode:** Review (convergent/critical)
**Date:** 2026-03-01
**Models:** Gemini 3.1 Pro, GPT-5.2 (reasoning-effort: high)
**Constitutional anchoring:** Yes (CLAUDE.md Constitution, GOALS.md)
**Extraction:** 32 items extracted, 22 included, 4 deferred, 1 rejected, 5 merged

---

## Verified Findings (adopt)

| IDs | Finding | Source | Verified How |
|-----|---------|--------|-------------|
| G1, P3, P7, P8 | **UserPromptSubmit per-message hook is wrong approach for pre-compaction.** It's a different control loop than OpenClaw's automatic flush (reminder vs autonomous save), adds 20-50s latency/session, risks "soft fail-closed" UX, and violates fail-open principle. | Both models | Architectural analysis: PreCompact has no decision control (confirmed in CLAUDE.md). UserPromptSubmit fires every message (confirmed in hook docs). |
| P9, G8 | **Instrument Context-Loss Incident Rate (CLIR) before building Phase 2.** Both models independently say: measure the problem before building the solution. Without knowing incident frequency (p) and cost (H), can't compute ROI. | Both models | Constitutional Principle 3: "Measure before enforcing." Currently no CLIR data exists. |
| G10 | **Better Phase 2: non-agentic PreCompact script + separate curation.** PreCompact hook dumps current context/state to a background file. Separate low-priority process curates into MEMORY.md. Keeps latency off the critical path. | Gemini | PreCompact hook confirmed: can run side-effect scripts (exit 0), can write files. Cannot inject agentic turns but CAN dump state. |
| P10 | **If building a context-save hook at all, rate-limit to 3-8 checks/session, not every message.** Compaction proximity changes slowly relative to turns. | GPT | Context % available via statusline JSON (`used_percentage`). Could check only after tool-heavy turns. |
| G2, G11, P13 | **Skills gating should be dynamic, not manual symlink removal.** Static removal is config, not architecture. Dynamic masking via project-aware mechanism is better. | Both models | Constitutional Principle 1: "Architecture over instructions." Manual symlink curation requires ongoing human supervision. |
| P2, P1 | **Skills gating token savings are minimal (~80-120 tokens, <1% of context).** Do for cleanliness and preventing wrong-project tool invocation, not for performance. The 30% claim was of the skills sub-budget, not total context. | GPT | Math verified: 16 × 97 chars ≈ 1,552 chars. 30% removal = 465 chars ≈ 80-120 tokens vs 200K token context. |
| G5 | **Orchestrator + foreground user writing shared MEMORY.md = race condition.** Need file locking or separate write targets. | Gemini | Verified: orchestrator spawns `claude -p` which can write to same memory path as interactive session. |
| G6, P12 | **Orchestrator needs self-observability and acceptance tests.** Timeout kills, partial failures need structured logging. Define ship-ready rate, edit-time, duplication rate per task type. | Both models | No observability spec in current orchestrator design (confirmed in maintenance-checklist.md). |
| G12 | **Orchestrator: enforce JSON output schema, 2-try error correction, then FAILED.** | Gemini | `claude -p --output-format json` already exists in spec. Error loop is additive hardening. |
| G13 | **Doctor should run as first task in orchestrator maintenance lane.** Removes human dependency on running diagnostics. | Gemini | Constitutional alignment: maximizes autonomy by automating a currently manual check. |
| G4, P5 | **Cron (fresh context) confirmed over heartbeat (persistent session) for orchestrator.** Both models agree. Plan already committed to this correctly. Remove the "open question" — it's decided. | Both models | Both cite context rot and agentic theater risks of persistent sessions. |
| P4 | **Remove "30% context preservation improvement" claim.** Ungrounded, not falsifiable without operational definition. Replace with measurable CLIR reduction target. | GPT | No source for this number. It was speculative. |
| P6 | **Connect each phase to primary metric (autonomous-to-supervised ratio).** Only Phase 4 directly targets it. Other phases should specify how they reduce supervision. | GPT | GOALS.md primary metric confirmed. Phases 1/2/3/5 lack explicit connection. |
| P14 | **Adopt testable predictions with specific metrics.** Key ones: MEMORY.md churn ↓50% (Phase 1), autonomy ≥96% (Phase 4), doctor diagnosis time ↓50% (Phase 5). | GPT | Makes success criteria falsifiable. |
| P11 | **Kill-switch + staged rollout for any new global hook.** Env var disable, 1 project first, then expand after 1 week. | GPT | Constitutional: reversibility + blast radius. Currently no staged rollout policy. |

## Deferred (with reason)

| ID | Finding | Why Deferred |
|----|---------|-------------|
| G3 | Daily logs context bloat | Theoretical risk. Daily logs = ~0.5-1KB/day, only today+yesterday loaded. Not unbounded. Monitor after deployment. |
| G7 | Lane model needs dependency resolution | Over-engineering for N=3 task types. Add when task dependencies actually exist. |
| G14 | Prioritize orchestrator first | Current dependency chain (daily logs → Phase 2 → orchestrator) is correct. But orchestrator should move up if CLIR measurement shows low context-loss incidents. |
| P16 | Compaction sensitivity to marginal tokens | Only relevant if proven empirically. Not established yet. |

## Rejected (with reason)

| ID | Finding | Why Rejected |
|----|---------|-------------|
| G9 | Use subagent memory instead of daily logs | Subagent memory is per-subagent MEMORY.md. Daily logs capture main session context — different use case. Subagent memory doesn't help with main session context loss. |

## Where I Was Wrong

| My Original Claim | Reality | Who Caught It |
|-------------------|---------|--------------|
| "UserPromptSubmit prompt hook (preferred)" for pre-compaction | Per-message hook is wrong approach — wrong control loop, excessive latency, fail-closed risk | Both models |
| "~30% context preservation improvement" | Ungrounded number, not falsifiable | GPT |
| "Skills gating saves ~30% of token budget" | Saves ~30% of 1,552 chars = 465 chars, which is <1% of context window. Misleading framing. | GPT |
| "Should the orchestrator use heartbeat or cron?" posed as open question | Already decided (cron). Remove from open questions. | Both models |

## Gemini Errors (distrust)

| Claim | Why Wrong |
|-------|-----------|
| "Daily logs directly conflict with Claude Code's native memory limits (200-line limit)" | 200-line limit applies to MEMORY.md auto-managed by Claude Code. Daily logs are separate files in a subdirectory. No conflict. |
| "Use native subagent memory + record-to-sqlite instead of daily logs" | Subagent memory is per-subagent, not main session. Different problem space. |
| Temperature override ignored: Gemini 3.1 Pro locked to temp=1.0 | Not an error but a known constraint — noted for future dispatches. |

## GPT Errors (distrust)

| Claim | Why Wrong |
|-------|-----------|
| "Sessions/day: 1-3; user messages/session: 20-50 (given)" | These weren't "given" — GPT fabricated them as assumptions. Actual sessions: 6-10/day based on session receipts. Messages per session: varies widely (5-100+). |
| "Cross-model review for non-trivial decisions — Score: 40%" | Score seems low given we're literally doing cross-model review right now. The constitutional principle is being followed; the gap is in formal decision gates, which is reasonable but not a 40% score. |

---

## Revised Plan

### Phase 0 (NEW): Instrument CLIR (1 session, ~30 min)
**What:** Define and log Context-Loss Incidents before building any pre-compaction mechanism.
**Taxonomy:** (a) repeated instructions, (b) lost task state post-compaction, (c) missing memory write, (d) wrong-project contamination.
**How:** Add a simple counter to `precompact-log.sh` that tags the last 3 tool calls + whether memory was written in the prior 5 turns. Review after 20 compaction events.
**Why:** Constitutional Principle 3. Can't build Phase 2 without knowing if the problem is real.

### Phase 1: Daily Memory Logs (unchanged, 30 min)
Keep as-is. Gemini's bloat concern is overblown (daily logs are tiny, only 2 days loaded).
**Add:** Connect to primary metric — daily logs reduce supervision by preventing "what were we doing?" re-orientation after compaction.

### Phase 2: Pre-Compaction Context Save (REVISED)
**Drop:** UserPromptSubmit per-message hook (both models agree: wrong approach).
**New approach:**
- **Step A:** Enhance `precompact-log.sh` to dump current task state + recent tool calls + uncommitted file paths to `.claude/checkpoint.md`. This is non-agentic, fast, side-effect only.
- **Step B:** Strengthen CLAUDE.md instruction + daily log convention. Yes, instructions are 0% reliable on their own, but combined with daily logs and checkpoint.md dumping, the *system* covers more cases.
- **Step C (conditional on CLIR data):** If CLIR shows p > 0.2 incidents/session, build a rate-limited PostToolUse prompt hook (3-8 checks/session, not every message) that uses `context_window.used_percentage` from statusline to inject "save context now" only when >75% used.
- **Kill-switch:** Env var `DISABLE_CONTEXT_SAVE_HOOK=1` to disable instantly.
- **Staged rollout:** meta only for 2 weeks, then expand.

### Phase 3: Skills Gating (UPGRADED)
**Drop:** Manual symlink audit (config, not architecture).
**New:** Per-project skill filtering. Options:
- **A (pragmatic):** Audit symlinks now (10 min, captures 80% of value), then build dynamic gating later.
- **B (architectural):** PreToolUse hook or `.claude/rules/` per-project that masks irrelevant skills.
- Do A now, B when we have 25+ skills or see wrong-project tool invocations.

### Phase 4: Orchestrator MVP (HARDENED)
Keep cron-based fresh context (confirmed by both models). Add:
- [ ] JSON output schema enforcement with 2-try error loop
- [ ] Self-observability: structured JSONL logging for timeouts, failures, partial completions
- [ ] Acceptance tests: edit-time, ship-ready rate, duplication rate per task type
- [ ] Race condition mitigation: orchestrator writes to separate memory namespace, not shared MEMORY.md
- [ ] Doctor as first maintenance task (automated health check before autonomous work)
- [ ] Kill-switch for orchestrator (env var to disable without code changes)

### Phase 5: Doctor Script (UPGRADED)
Run as first task in orchestrator maintenance lane. Also available manually.
Keep implementation as planned — read-only diagnostics.

### Revised Priority
1. **Phase 0 (CLIR instrumentation)** — prerequisite for Phase 2, required by constitution
2. **Phase 1 (daily logs)** — lowest effort, enables context persistence
3. **Phase 3A (symlink audit)** — 10 min, captures most value
4. **Phase 5 (doctor)** — supports Phase 4
5. **Phase 4 (orchestrator)** — most ambitious, highest autonomy impact
6. **Phase 2 (context save)** — conditional on CLIR data
7. **Phase 3B (dynamic gating)** — when scale warrants

### Flagged Risks (monitor)
- G16: Cron may lose train-of-thought for intel deep analysis. Watch for quality regressions.
- G15: May be underestimating compaction damage. CLIR data will resolve this.
- G5: Race conditions on shared memory. Orchestrator must write to separate files.

---

## Constitutional Alignment Summary (from GPT, adjusted)

| Principle | Coverage | Key Gap |
|-----------|----------|---------|
| Architecture over instructions | 75% | Phase 2 Step B is still instruction-reliant. Step A (PreCompact dump) is architectural. |
| Measure before enforcing | 70% (up from 55%) | Phase 0 (CLIR) directly addresses this. |
| Self-modification by reversibility | 75% | Kill-switches and staged rollout added. |
| Recurring patterns → architecture | 65% | Need occurrence counts for context-loss before promoting. |
| Fail open | 70% | Per-message hook eliminated. Rate-limited fallback is less aggressive. |
