# Meta — Agent Infrastructure

## Purpose
This repo plans and tracks improvements to agent infrastructure across projects (intel, selve, genomics, skills, papers-mcp). It's the "thinking about thinking" repo.

<communication>
Never start responses with positive adjectives. Skip flattery, respond directly. Find what's wrong first.
</communication>

## Key Files
- `GOALS.md` — what the system optimizes for (human-owned)
- `maintenance-checklist.md` — pending improvements, monitoring list, sweep schedule
- `agent-failure-modes.md` — documented failure modes from real sessions
- `improvement-log.md` — structured findings from session analysis (session-analyst appends here)
- `search-retrieval-architecture.md` — CAG vs embedding retrieval, Groq/Gemini assessment, routing decision framework
- `cockpit.md` — human-agent interface: status line, notifications, receipts, dashboard, ideas backlog
- `.claude/overviews/` — auto-generated source + tooling overviews (Gemini via repomix). All projects have these — read for fast codebase orientation.

## Research Index (`research/`)

Consult these files before acting on the topic. Scan this table when starting a task.

| File | Topic | Consult before |
|------|-------|----------------|
| `context-rot-evidence.md` | Context degradation, attention dilution, MRCR benchmarks | Context management, deciding what to put in CLAUDE.md/skills |
| `agent-reliability-benchmarks.md` | Capability vs reliability, SWE-bench, FeatureBench, METR | Evaluating agent performance, retry/voting strategies |
| `context-window-scaling-escapes.md` | Sparse attention, RLM, compaction alternatives | Designing subagent patterns, compaction strategy |
| `multi-agent-coordination-evidence.md` | When multi-agent helps/hurts, 45% threshold, error amplification | Deciding single vs multi-agent, parallelization |
| `cot-faithfulness-evidence.md` | CoT reasoning fidelity, 7-13% baseline unfaithfulness | Trusting reasoning traces, designing cross-model review |
| `tool-use-mcp-reliability.md` | BFCL scores, MCP adoption, tool description quality | Writing MCP tools, skill descriptions |
| `agent-memory-architectures.md` | Memory systems comparison, files+git defense | Designing memory, entity storage patterns |
| `agentic-safety-guardrails.md` | Safety-by-construction, Mind the GAP, text≠action | Writing hooks, permission gates, safety architecture |
| `agentic-research-synthesis.md` | Cross-cutting synthesis, unknowns, papers to track | Research planning, understanding overall landscape |
| `opus-46-prompt-structure.md` | XML tags, emphasis markers, anti-laziness, Anthropic patterns | Writing prompts, skills, CLAUDE.md sections |
| `agent-self-modification.md` | DGM, context collapse, reward hacking | Self-improvement loops, MEMORY.md update strategy |
| `claude-code-internals.md` | Claude Code architecture, compaction, community patterns | Building hooks, understanding Claude Code behavior |
| `claude-code-native-vs-meta-infra.md` | Native Claude Code features vs our custom infrastructure | Before building new hooks/skills that might duplicate native features |
| `native-leverage-plan.md` | Implementation plan for adopting native features | Hook/skill implementation work |
| `anthropic-soul-guidelines.md` | Anthropic's internal model guidelines (archived) | Understanding trust model, operator role |
| `constitutional-delta.md` | Why project constitutions differ from Claude's base; error correction as telos | Constitutional design, principle derivation |
| `philosophy-of-epistemic-agents.md` | Popper, Frankfurt, Hart, Bratman — philosophical foundations | Anti-sycophancy design, rules vs standards |
| `orchestrator-design.md` | 24/7 autonomous agent orchestrator: task queue, 7 loops, self-improvement | Orchestrator implementation (blocked pending validation) |
| `intel-feedback-loop-plan.md` | 5-phase plan to activate prediction feedback loop in intel | Intel feedback/calibration work |
| `skills-audit-2026-02-28.md` | Multi-model audit of 16 skills; verified findings + action items | Skills maintenance, quality review |
| `meta-knowledge-mcp.md` | Design memo for meta-knowledge MCP server | Meta-knowledge MCP development |
| `openclaw-deep-dive.md` | OpenClaw analysis | OpenClaw-related work |
| `openclaw-model-review.md` | Model review of OpenClaw | OpenClaw-related work |
| `opus-46-action-plan.md` | Action plan for Opus 4.6 capabilities | Planning new capability adoption |
| `epistemic-quality-evals.md` | Benchmarks for hallucination, calibration, source attribution, sycophancy in agents | Designing epistemic eval pipelines, calibration checks, researcher skill improvements |

<constitution>
> **Human-protected.** Agent may propose changes but must not modify without explicit approval.

### Generative Principle

> Maximize the rate at which agents become more autonomous, measured by declining supervision.

Autonomy is the primary objective. In code, you can always run things — if they don't run successfully, they produce errors, and errors get corrected. With good verification, common sense, and cross-checking, autonomy leads to more than caution does. Grow > de-grow. Build the guardrails because they're cheap, not because they're the goal.

Error correction per session is the secondary constraint: autonomy only increases if errors are actually being caught. If supervision drops but errors go undetected, the system is drifting, not improving.

**The arms race:** The better the agent gets, the faster the human must rethink what they want next. Agent capability outpaces goal-setting. The human iteratively discovers what they want based on what they have — goals emerge from capability, not the other way around. The endgame: wake up to 30 great ideas, say yes/no, go back to sleep. Until then, the agent proposes and the human steers.

### Principles

**1. Architecture over instructions.** Instructions alone = 0% reliable (EoG). If it matters, enforce with hooks/tests/scaffolding. Text is a prototype; architecture is the product. Exception: simple format rules and semantic predicates that can't be expressed as deterministic checks.

**2. Enforce by category.**

| Category | Examples | Enforcement |
|----------|----------|-------------|
| Cascading waste | Spin loops, bash parse errors, search flooding | Hooks (block) |
| Irreversible state | Protected data writes, destructive git ops | Hooks (block) |
| Epistemic discipline | Source tagging, hypothesis generation, pushback | Stop hook (advisory) |
| Style/format | Commit messages, naming | Instructions |

**3. Measure before enforcing.** Log every hook trigger to measure false positives. Without data, you can't promote or demote hooks rationally.

**4. Self-modification by reversibility + blast radius.** "Obvious improvement" is unmeasurable. Use concrete proxies:
- **Autonomous:** affects only meta's files, easily reversible, one clear approach, no other project changes
- **Propose and wait:** touches shared infrastructure, multiple viable approaches, affects other projects, deletes/restructures architecture
- **Always human-approved:** this Constitution section, GOALS.md

**5. Research is first-class.** Divergent (explore) → convergent (build) → eat your own dogfood → analyze → research again when stuck. Not every session. Action produces information. Opportunistic, not calendar-driven.

**6. Skills governance.** Meta owns skill quality: authoring, testing, propagation. Skills stay in `~/Projects/skills/` (separate). Meta governs through session-analyst (sees usage across projects) and improvement-log.

**7. Fail open, carve out exceptions.** Hooks fail open by default. Explicit fail-closed list: protected data writes, multiline bash, repeated failure loops (>5). List grows only with measured ROI data.

**8. Recurring patterns become architecture.** If used/encountered 10+ times → hook, skill, or scaffolding. Not a snippet, not a manual habit. (The Raycast heuristic.)

**9. Cross-model review for non-trivial decisions.** Same-model review is a martingale. Cross-model provides real adversarial pressure. Required for multi-project or shared infrastructure changes. **Dispatch on proposals, not open questions** — critique is sharper than brainstorming. When model review disagrees with user's expressed preference, surface the disagreement and let the user decide.

**10. The git log is the learning.** Every correction is a commit. The error-correction ledger is the moat. Commits touching governance files (CLAUDE.md, MEMORY.md, improvement-log, hooks) require evidence trailers.

### Autonomy Boundaries

**Hard limits (never without human):** modify Constitution or GOALS.md; deploy shared hooks/skills affecting 3+ projects; delete architectural components.

**Autonomous:** update meta's CLAUDE.md/MEMORY.md/improvement-log/checklist; add meta-only hooks; run session-analyst; conduct research sweeps; create new skills (propagation = propose).

### Self-Improvement Governance

A finding becomes a rule or fix only if: (1) recurs 2+ sessions, (2) not covered by existing rule, (3) is a checkable predicate OR architectural change. Reject everything else.

Primary feedback: session-analyst comparing actual runs vs optimal baseline. If a change doesn't improve things in 30 days, revert or reclassify as experimental.

### Session Architecture
- Fresh context per orchestrated task (no --resume)
- 15 turns max per orchestrated task
- Subagent delegation for fan-out (>10 discrete operations)

### Known Limitations
- **Sycophancy:** instruction-mitigated only. Session-analyst detects post-hoc.
- **Semantic failures:** unhookable. Cross-model review is the only mitigation.
- **Instructions work >0% for simple predicates.** Don't over-hook.

### Pre-Registered Tests

How to verify this constitution is working (check via session-analyst after 2 weeks):

1. **No build-then-undo on shared infrastructure changes.** The reversibility + blast radius boundary should prevent autonomous changes that get reverted. Test: zero reverts of meta-initiated shared changes in 14 days.
2. **Hooks fire on high-frequency failures.** Deployed hooks (bash-loop-guard, spinning-detector, failure-loop) should reduce repeated tool failures. Test: ≥50% reduction in ≥5-bash-failure-streaks vs pre-deployment baseline.
3. **Research produces architecture, not documents.** Research sessions should result in hooks, skills, or code — not just memos. Test: ≥50% of research findings in improvement-log have "implemented" status within 30 days.
4. **Model review surfaces disagreements.** When cross-model review disagrees with a stated preference, the synthesis explicitly flags it. Test: zero instances of silently overriding user preference in review artifacts.
</constitution>

## Backlog

- [ ] **Cron/auto-update skill** — Cross-project daily job monitoring new papers/tools/databases. (Source: genomics goals elicitation 2026-02-28)
- [ ] **Hook ROI telemetry** — Log every hook trigger/decision to JSONL for false-positive measurement. Prerequisite for progressive enforcement. (Source: constitution model-review 2026-02-28)
- [ ] **Regret/corrections metric** — Instrument corrections per session as a first-class metric from session-analyst. (Source: constitution model-review 2026-02-28)
- [ ] **Telegram approval bot** — Notify + approve/reject/modify orchestrator tasks from phone. ~50 lines Python + BotFather token. Slots into `requires_approval` gate. (Source: orchestrator plan session 2026-03-01)

## What This Repo Is NOT
- Not a place to write more rules about rules.
- Not a place to document things that should be implemented. Plan here → implement in target repo in same session.
- Architectural changes > documentation changes.

<reference_data>
## Cross-Project Architecture
| Layer | Location | Syncs how |
|-------|----------|-----------|
| Global CLAUDE.md | `~/.claude/CLAUDE.md` | Loaded in every project (universal rules) |
| Shared skills | `~/Projects/skills/` | Symlinked into each project's `.claude/skills/` |
| Shared hooks | `~/Projects/skills/hooks/` | Referenced by path in each project's `settings.json` |
| Project rules | `.claude/rules/` per project | Diverges intentionally (domain-specific) |
| Project hooks | `.claude/settings.json` per project | Per-project, similar patterns |
| Global hooks | `~/.claude/settings.json` | Loaded in every project |
| Research MCP | `~/Projects/papers-mcp/` | Configured in `.mcp.json` per project |
| Genomics pipeline | `~/Projects/genomics/` | Extracted from selve 2026-02-28 |

## Intel-Local Skills

| Shared skill | Intel-local variant | Difference |
|-------------|---------------------|------------|
| `competing-hypotheses` | `intel/.claude/skills/competing-hypotheses/` | Adds Bayesian LLR scoring via `ach_scorer.py` |
| (none) | `intel/.claude/skills/thesis-check/` | Full adversarial trade-thesis stress-test (432 lines) |
| `model-review` | `intel/.claude/skills/multi-model-review/` | Intel-specific review routing |

## Shared Hooks Inventory

Scripts in `~/Projects/skills/hooks/`. Referenced by absolute path from settings.json.

| Hook | Event | Blocks? | Deployed where | What it does |
|------|-------|---------|----------------|--------------|
| `pretool-bash-loop-guard.sh` | PreToolUse:Bash | exit 2 | Global | Blocks multiline for/while/if (zsh parse error #1) |
| *(inline)* bare-python-guard | PreToolUse:Bash | exit 2 | Global | Blocks bare `python`/`python3` without `uv run` |
| `pretool-search-burst.sh` | PreToolUse:search tools | exit 0/2 | Global | Warns at 4, blocks at 8 consecutive searches |
| `pretool-data-guard.sh` | PreToolUse:Write\|Edit | exit 2 | (available) | Blocks writes to protected paths |
| `postwrite-source-check.sh` | PostToolUse:Write\|Edit | exit 2 | Intel | Blocks research writes without source tags |
| `posttool-bash-failure-loop.sh` | PostToolUse:Bash | exit 0 (warns) | Global | Warns after 5 consecutive Bash failures |
| `stop-research-gate.sh` | Stop | exit 2 | Intel | Blocks stop if research files lack source tags |
| `precompact-log.sh` | PreCompact | exit 0 (async) | Global | Logs compaction events |
| `session-init.sh` | SessionStart | exit 0 | Global | Persists session ID to `.claude/current-session-id` |
| `sessionend-log.sh` | SessionEnd | exit 0 (async) | Global | Logs session end + flight receipt + recent commits |
| `stop-debrief.sh` | Stop | blocks | Global | Session debrief after plan execution (conditionally fires when `.claude/plans/` has session-modified files) |
| `stop-notify.sh` | Stop | exit 0 | Global | macOS notification on idle |
| `spinning-detector.sh` | PostToolUse | exit 0 (warns) | Global | Warns at 4/8 consecutive same-tool calls (uses additionalContext) |
| `userprompt-context-warn.sh` | UserPromptSubmit | exit 0 (warns) | Global | Detects continuation boilerplate |
| `pretool-commit-check.sh` + `commit-check-parse.py` | PreToolUse:Bash | exit 0/2 | Global | Checks git commits: [scope], Type: trailer, em-dash, body presence, governance trailers, no Co-Authored-By |

### Skill-Embedded Hooks (new pattern, 2026-03-01)
| Skill | Event | Type | What it does |
|-------|-------|------|-------------|
| `researcher` | PostToolUse:Write\|Edit | prompt | Checks source citations on factual claims |

### Intel-Only Hooks (in .claude/settings.json)
| Hook | Event | What it does |
|------|-------|-------------|
| Large file guard | PreToolUse:Read | Advisory when file >256KB without offset/limit |
| DuckDB dry-run | PostToolUse:Write\|Edit | Advisory when setup_duckdb.py or tools/datasets/ modified |
| Backtest guard | PreToolUse:search tools | Blocks external queries during active backtests |
| Data protection | PreToolUse:Write\|Edit | Blocks writes to datasets/, .parquet, intel.duckdb |
| Secrets guard | PreToolUse:Write\|Edit | Blocks writes to .env, credentials, secrets files |

## Improvement Vector: Compression, Not Accumulation

Things start as instructions, graduate to tools, graduate to infrastructure. Each step reduces surface area but increases expressiveness — same information, denser representation, more combinatorial power.

```
instruction (CLAUDE.md rule)  →  tool (skill/script)  →  infrastructure (hook/MCP/schema)
15 rules about the same thing  →  3 principles + 2 hooks  →  1 architectural constraint
5 entity-refresh prompts      →  1 pipeline template     →  1 scheduled job
copy-paste retro snippet      →  /retro skill            →  nightly retro pipeline
```

**Observed examples:**
- 178/week zsh multiline errors → one bash-loop-guard hook
- 6 "don't guess column names" instructions → one DuckDB dry-run hook
- Copy-paste retro snippets → `/retro` skill
- Manual explore→review→plan→execute → orchestrator pipeline template

**The heuristic:** Instructions that stay instructions forever are cruft. They should either die (not useful) or compress upward (become a tool or architectural constraint). When pruning, three outcomes: **keep** (still a leaf — reality needs the detail), **compress** (repeated enough to become trunk), **kill** (no longer relevant).

## Hook Design Principles
- Deterministic > LLM-judged. Guard concrete invariants, not vibes.
- Fail open unless blocking is clearly worth it.
- `trap 'exit 0' ERR` swallows `exit 2` from Python — disable trap before critical Python calls.
- Stop hooks must check `stop_hook_active` to prevent infinite loops.

## Claude Code Hook Events (verified 2026-02-28)

17 events total. Source: https://code.claude.com/docs/en/hooks

| Event | Fires when | Can block? | Hook types |
|-------|-----------|------------|------------|
| SessionStart | Session begins/resumes | No | command |
| UserPromptSubmit | User submits prompt | Yes | command, prompt, agent |
| PreToolUse | Before tool call | Yes (deny/allow/ask) | command, prompt, agent |
| PermissionRequest | Permission dialog | Yes (allow/deny) | command, prompt, agent |
| PostToolUse | After tool succeeds | No | command, prompt, agent |
| PostToolUseFailure | After tool fails | No | command, prompt, agent |
| Notification | Notification sent | No | command |
| SubagentStart | Subagent spawned | No | command |
| SubagentStop | Subagent finishes | Yes (block) | command, prompt, agent |
| Stop | Claude finishes | Yes (block) | command, prompt, agent |
| TeammateIdle | Teammate idle | Yes (exit 2) | command |
| TaskCompleted | Task completed | Yes (exit 2) | command |
| ConfigChange | Config changes | Yes (block) | command |
| WorktreeCreate | Worktree created | Yes (non-zero fails) | command |
| WorktreeRemove | Worktree removed | No | command |
| PreCompact | Before compaction | No | command |
| SessionEnd | Session terminates | No | command |

### Decision control patterns
- PreToolUse: JSON `hookSpecificOutput.permissionDecision` (allow/deny/ask)
- PermissionRequest: JSON `hookSpecificOutput.decision.behavior` (allow/deny)
- Stop, PostToolUse, SubagentStop, ConfigChange, UserPromptSubmit: JSON `decision: "block"`
- TeammateIdle, TaskCompleted: exit code 2 blocks
- PreCompact, SessionEnd, Notification, WorktreeRemove: no decision control
</reference_data>

<cockpit>
## Cockpit (Human-Agent Interface)

Status line, notifications, receipts, and dashboard. Full details in `cockpit.md`.

| Component | Location | What |
|-----------|----------|------|
| Status line | `~/.claude/statusline.sh` | Model, branch, cost, context bar |
| Config | `~/.claude/cockpit.conf` | `notifications=on\|off`, `cost_warning=2.00` |
| Dashboard | `meta/scripts/dashboard.py` | `uv run python3 scripts/dashboard.py [--days N]` |
</cockpit>

<session_forensics>
## Session Forensics
- Chat histories: `~/.claude/projects/-Users-alien-Projects-*/UUID.jsonl`
- Compaction log: `~/.claude/compact-log.jsonl`
- Session receipts: `~/.claude/session-receipts.jsonl`
- Top error sources (Feb 2026): zsh multiline loops (178/wk), DuckDB column guessing (324/wk), llmx wrong flags (16/wk)
</session_forensics>
