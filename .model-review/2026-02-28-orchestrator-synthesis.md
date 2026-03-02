# Multi-Model Review Synthesis: Autonomous Agent Architecture

**Date:** 2026-02-27
**Reviewers:** Gemini 3.1 Pro (2 queries, ~250K tokens each), GPT-5.2 (1 query, ~50K tokens)
**Cost:** ~$8 total
**Source grades:** Gemini architectural claims `[C3]` until verified against code. GPT-5.2 math derivations `[A2]` (independently verifiable).

---

## Validated Findings (Both Models Agree)

### 1. `--resume` is WRONG for task chaining [CRITICAL]
**Gemini:** "This is a fundamental misunderstanding. `--resume` loads the *entire history* of the previous session."
**GPT-5.2:** "Without compaction, long sessions become quadratically more expensive: total input tokens = nF + v*n(n-1)/2."

**Fix:** Each task gets a completely fresh `claude -p` session. No `--resume`. If a task needs context from a previous task, pass it via a file (the "Document & Clear" pattern from our own best practices doc).

### 2. Wrap-up self-improvement prompt is doomed [CRITICAL]
**Gemini:** "Asking an exhausted LLM to edit core files like MEMORY.md at the end of 30-60 turns will result in hallucinations or 'No meta-updates needed' out of laziness."

**Fix:** Self-improvement is a dedicated, fresh-context task dispatched every 5 tasks. Fed the JSONL logs + git diffs from recent tasks as input. Not an afterthought appended to exhausted sessions.

### 3. 30-60 turns too high; optimal is 10-15 [IMPORTANT]
**Gemini:** "At 30 turns, Opus 4.6 will be drowning in its own tool-use JSON history."
**GPT-5.2:** Per-turn budget at $0.06/turn is feasible only if per-turn tokens are modest (~2000 in, ~400 out).

**Fix:** Default to 15 turns max. If a task needs more, force it to write progress to markdown, exit, and queue a continuation.

### 4. Build the Headless Entity Refresher FIRST [BOTH RECOMMEND]
**Gemini Query 1:** "100 lines of Python: read staleness.py output → loop → claude -p for each stale entity → --max-turns 15."
**Gemini Query 2:** "Throw away the DAG, Agent SDK, diversity monitor, sigmoid sampling. They are premature optimizations."

**Consensus MVP:** cron + SQLite queue + `claude -p --max-turns 15` per task + subprocess timeout.

---

## GPT-5.2 Math Findings [A2]

### Task Selection Algorithm
- Sigmoid max/min weight ratio = **12.19x** — sufficient spread to starve low-priority types even with diversity penalties
- The "below 10% boost" described in prose is **not implemented** in the code — the recency boost is a different mechanism
- Under uniform selection, recovering a type from 10% → 20% of recent history takes **~11.2 tasks** (no boost) or **~5.2 tasks** (max boost)
- `random.choices` with dynamic weights is mathematically sound for stochastic dispatch; Thompson/UCB solve a different problem (learning unknown rewards) and aren't automatically better unless you define and measure a reward signal

### Budget Feasibility
- $2.14/task allows ~50K-80K total tokens per task (depends on input/output ratio)
- At 4:1 input:output ratio: ~63K input + ~16K output per task
- Per-turn budget of $0.06 is viable only with ~2000 input + ~400 output tokens per turn
- **Verdict:** Budget is tight but feasible if tool outputs are aggressively truncated

### Mandatory Rotation
- Caps maximum run length at 3 (prevents pathological sequences)
- Does NOT guarantee stationary distribution matches target ranges
- A type with base priority giving sigmoid weight 12x lower than other types can remain permanently underrepresented even with rotation

### Watchdog Timeout
- 2x mean timeout kills **~11.7%** of legitimate tasks under LogNormal(σ=1)
- Better: use 95th percentile timeout estimated online per task type, or adaptive "no-heartbeat" timeout

### Session Cost Scaling
- Fresh sessions: **linear** cost growth (n tasks × fixed setup cost F)
- Resumed sessions: **quadratic** without compaction (n tasks × growing history)
- Compaction restores near-linear but introduces information loss parameter ρ

---

## Gemini Architectural Findings [C3]

### Production Patterns We Missed
1. **Dead Letter Queue (DLQ):** Failed tasks need replay capability, not just logging
2. **Idempotency:** If watchdog kills mid-entity-update, retry must not duplicate data. Git commits provide natural idempotency (commit-or-not is atomic)
3. **Lease Management:** DuckDB lock files survive process kills. Pre-flight check needed before each task
4. **Resource-Level Circuit Breakers:** If SEC EDGAR is down, 3 consecutive entity refreshes fail. Stop dispatching EDGAR-dependent tasks for 1 hour, not per-task retry
5. **Poison Pill Quarantine:** Task that fails twice goes to quarantine, not back in queue
6. **Outbox Pattern:** LLM proposes trades → outbox table → deterministic script → human approval → execution. Keep LLM away from consequential state changes

### State Management
- **SQLite over in-memory DAG:** If orchestrator crashes, queue survives. One table: `Queue(id, type, prompt, status, created_at)`
- **Cron over long-running Python:** 15-minute cron dispatches 1 task per cycle. No async complexity, no memory leaks
- Git + JSONL stays for auditability; SQLite for orchestration state

### Human-in-the-Loop
- **Synchronous alerts for high-impact findings:** Telegram/Pushover for urgent signals (massive insider dump, material 8-K)
- **Graduated autonomy:** High confidence + low impact → auto-commit. High confidence + high impact → alert. Low confidence → daily review queue
- **Daily review too slow for alpha:** 12-hour lag destroys time-sensitive edge

### Cost Optimization
- **Model tiering:** Entity refresh → Haiku/Sonnet. Investigation/decisions → Opus
- **Dynamic budget:** Underspent at 10 PM → boost exploration. Overspent at 10 AM → lock to critical only
- **Context pruning:** Strip large DuckDB results from session history before any resume

### Task Selection
- **UCB1 over sigmoid:** Mathematically sound exploration/exploitation. Formula: `exploitation + C * sqrt(ln(total_runs) / type_runs) + urgency_boost`
- **GPT-5.2 disagrees:** Says UCB solves a different problem (unknown rewards) and isn't automatically better. Sigmoid is fine for heuristic dispatch.
- **My assessment:** Gemini is probably right for the long run (we WANT to learn which task types produce the most value), but GPT-5.2 is right that it requires defining and measuring a reward signal first. Start with sigmoid, add UCB when we have reward data.

### The One-Weekend MVP
1. SQLite state (`orchestrator.db`)
2. Cron every 15 minutes → query for PENDING → dispatch 1 task
3. `claude -p "..." --max-turns 15 --output-format json`
4. `subprocess.run(timeout=1800)` as watchdog
5. Telegram bot for instant human review

### Missed Architectures (Need Verification)
- **LangGraph:** "Your Python orchestrator is manually reinventing LangGraph's StateGraph." [PLAUSIBLE — but may be overkill for one person]
- **Magentic-One (Microsoft):** Dynamic routing to specialized agents. [RELEVANT but experimental]
- **SWE-agent ACI:** LLMs need truncated, paginated tool output, not raw dumps. [VALID — our DuckDB queries can overwhelm context]

### Cross-Project Design
- **Separate queues, strict working directory isolation.** Do not mix intel and selve/self contexts
- **Cross-pollination only via shared METHODOLOGY agent** that reads logs from both projects
- Full teardown between project switches: kill MCP servers, cd to new project, load new CLAUDE.md

### Daily Log Additions
Missing from our design:
1. **Epistemic state changes:** "What did we change our minds about today?"
2. **Portfolio impact:** "Did findings alter conviction on active positions?"
3. **Data/infrastructure health:** View failures, schema issues
4. **Context efficiency:** How many tasks hit auto-compaction? (Tunes max-turns)
5. **Compaction count per task type** — critical for calibrating session length

---

## Disagreements Between Models

| Topic | Gemini 3.1 | GPT-5.2 | Assessment |
|-------|-----------|---------|------------|
| Task selection | UCB1 is better | Sigmoid is fine for heuristic dispatch; UCB needs reward signal | GPT-5.2 is more precise — start with sigmoid, upgrade when we have reward data |
| Orchestrator as LLM | Use Haiku for triage + evaluation | (not asked) | PLAUSIBLE — cheap Haiku call to classify failures is good ROI |
| LangGraph | "You're reinventing it" | (not asked) | OVERCALL — LangGraph adds dependency for marginal gain at our scale |
| Session length | 10-15 turns max | Budget math works at 35 turns if tokens/turn are modest | Gemini's practical experience + our own failure modes data → 15 is the right cap |

---

## Revised Implementation Plan

### Phase 0: MVP (One Weekend)
```
staleness.py → SQLite queue → cron every 15 min →
claude -p --max-turns 15 → subprocess timeout 30 min →
Telegram alert for human review → git commit on success
```

Files to create:
1. `meta/orchestrator.py` — 100-200 lines. SQLite queue + dispatch loop
2. `meta/orchestrator.db` — auto-created. One table
3. Telegram bot token in `~/.config/orchestrator.env`

### Phase 1: Hardening (Week 2)
- Circuit breakers per resource (SEC, DuckDB, Gemini)
- DLQ for failed tasks
- DuckDB lock pre-flight check
- JSONL event stream
- Daily markdown summary with epistemic changes + portfolio impact

### Phase 2: Intelligence (Week 3-4)
- Dedicated METHODOLOGY task every 5 tasks
- UCB1 task selection (once we have reward data from Phase 0-1)
- Model tiering (Haiku for entity refresh, Opus for investigation)
- Dynamic budget allocation
- Graduated autonomy (auto-commit / alert / daily review)

### Phase 3: Multi-Project (Month 2)
- selve project integration (separate queue, shared methodology)
- Cross-project learning
- Dashboard for trend tracking

---

## Action Items
1. **Build MVP this weekend** — staleness → SQLite → cron → claude -p → Telegram
2. **Fix the architecture doc:** Remove --resume chaining, reduce max-turns to 15, add DLQ/circuit breakers/idempotency
3. **Add Haiku triage layer** — cheap LLM call to classify task failures before retry
4. **Implement outbox pattern** for paper ledger trades
5. **Add compaction counter** to task logs (calibrate session length empirically)
