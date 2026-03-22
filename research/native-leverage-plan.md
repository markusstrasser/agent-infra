---
title: "Native Leverage Plan: Claude Code Features → Project Infrastructure"
date: 2026-03-21
---

# Native Leverage Plan: Claude Code Features → Project Infrastructure

> Created: 2026-03-01. Based on claude-code-native-vs-meta-infra.md assessment.
> Scope: intel (primary), selve, genomics, shared skills/hooks.

## Guiding Principle

Replace custom infrastructure with native only when the native version is **more reliable, not just present**. Leverage new native capabilities that didn't exist before. Don't replace working things for the sake of it.

---

## Phase 1: Quick Wins (try immediately, low risk)

### 1.1 Test `/batch` as orchestrator substitute
**What:** The bundled `/batch <instruction>` skill decomposes work into 5-30 units, each in its own worktree, each opening a PR. This overlaps with the orchestrator backlog item for code changes.

**Try:** In intel, run `/batch migrate all bare python3 calls to uv run python3 across tools/` or similar refactoring task. Evaluate: does it decompose correctly? Does it respect CLAUDE.md rules? Do the PRs make sense?

**Expected outcome:** If it works, it partially obsoletes the orchestrator for code-change tasks (but NOT for data refresh, research sweeps, or entity updates which are cross-session).

**Files affected:** None (just testing).

### 1.2 Test `/simplify` post-implementation
**What:** Bundled skill that spawns 3 parallel review agents (code reuse, quality, efficiency). Free quality pass.

**Try:** After next feature implementation in intel, run `/simplify`. Compare findings to what `/model-review` would catch.

**Expected outcome:** If good, add to standard workflow. If redundant with model-review, skip.

### 1.3 Add `model` field to skills that should be pinned
**What:** Skills can now specify which model to use.

**Changes:**
- `~/Projects/skills/session-analyst/SKILL.md` — add `model: sonnet` (analysis task, doesn't need opus)
- `~/Projects/skills/researcher/SKILL.md` — leave as inherit (needs whatever the session is using)
- Intel's `thesis-check` — add `model: opus` (432 lines, needs deep reasoning)
- Intel's `competing-hypotheses` — add `model: sonnet` (structured scoring)

**Risk:** Low. If model field doesn't work as expected, falls back to session model.

### 1.4 Switch spinning-detector to `additionalContext`
**What:** Currently spinning-detector outputs to stderr. `additionalContext` in PostToolUse hook output injects warning directly into Claude's context — more effective than stderr which may be ignored.

**Change:** Modify `~/.claude/hooks/spinning-detector.sh` to output JSON with `additionalContext` field instead of plain stderr.

**Current output:** `echo "WARNING: ..." >&2`
**New output:** `echo '{"additionalContext": "WARNING: You have called the same tool N times consecutively. Stop and reconsider your approach."}'`

**Risk:** Low. If JSON parsing fails, hook fails open.

### 1.5 Try `/insights` command
**What:** Claude Code built-in that generates LLM analysis of session history. May overlap with session-analyst.

**Try:** Run `/insights` and compare output to what session-analyst produces. If it catches different things, they're complementary. If it catches the same things, session-analyst has more value (structured output, improvement-log integration).

**Expected outcome:** Complementary. `/insights` is broad; session-analyst is structured and actionable.

---

## Phase 2: Subagent Refactoring (moderate effort, high value)

### 2.1 Add persistent memory to intel's entity-refresher
**What:** Intel already has `entity-refresher.md` as a custom subagent. Add `memory: project` to give it cross-session memory — which entities it refreshed, which data sources were stale, which had errors.

**Change:** Add frontmatter to `/Users/alien/Projects/intel/.claude/agents/entity-refresher.md`:
```yaml
---
name: entity-refresher
description: Refresh entity files with latest public data
memory: project
model: sonnet
maxTurns: 15
tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - mcp__duckdb__execute_query
  - mcp__intelligence__resolve_entity
  - mcp__intelligence__get_dossier
---
```

**Value:** The refresher remembers which tickers had broken data sources, which coverage dates it last updated, common errors per entity. Avoids repeating failed queries.

**Memory location:** `.claude/agent-memory/entity-refresher/MEMORY.md`

### 2.2 Add persistent memory to intel's dataset-discoverer
**What:** Similar upgrade. The discoverer should remember which datasets it already assessed, which were rejected (and why), which are pending download.

**Change:** Add frontmatter to `/Users/alien/Projects/intel/.claude/agents/dataset-discoverer.md`:
```yaml
---
name: dataset-discoverer
description: Find and assess public datasets for join potential
memory: project
model: sonnet
maxTurns: 20
tools:
  - Read
  - Grep
  - Glob
  - Bash
  - WebSearch
  - WebFetch
  - mcp__exa__web_search_exa
  - mcp__research__search_papers
---
```

### 2.3 Create shared researcher subagent (parallel to skill)
**What:** The researcher skill runs `context: fork` but has no persistent memory. Create a researcher subagent at `~/.claude/agents/researcher.md` that preloads the researcher skill AND has persistent memory.

**Structure:**
```yaml
---
name: researcher
description: Deep research agent with persistent memory of sources checked, papers read, and search strategies that worked. Delegates to researcher skill.
memory: user
model: inherit
maxTurns: 30
skills:
  - researcher
  - epistemics
  - source-grading
hooks:
  Stop:
    - hooks:
        - type: prompt
          prompt: "Does the research output include source citations for every factual claim? Are there any unsourced assertions?"
---
```

**Value:** Cross-session memory of what was already researched. The `Stop` prompt hook checks source discipline before returning results — replacing the instruction-only enforcement we have now.

**Location:** `~/.claude/agents/researcher.md` (user-level, available in all projects)

### 2.4 Upgrade session-analyst to subagent with memory
**What:** Session-analyst currently finds the same patterns repeatedly across sessions. With persistent memory, it can track: which patterns it already reported, which were implemented, which recurred despite fixes.

**Location:** `~/.claude/agents/session-analyst.md` (user-level)

```yaml
---
name: session-analyst
description: Analyzes session transcripts for behavioral anti-patterns. Remembers previously reported findings to avoid duplicates and track recurrence.
memory: user
model: sonnet
maxTurns: 25
skills:
  - session-analyst
tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Write
  - Edit
hooks:
  Stop:
    - hooks:
        - type: agent
          command: "Check that all findings in the output have: session ID, evidence quote, failure mode category, severity, and proposed fix. Verify no finding duplicates an existing entry in improvement-log.md."
---
```

**Value:** The `Stop` agent hook (multi-turn, has Read/Grep/Glob) verifies output quality before results are returned. This is the "stop hook verifier" from cockpit.md backlog — now natively possible.

---

## Phase 3: Hook Upgrades (moderate effort, structural improvement)

### 3.1 Prompt hook for commit message quality
**What:** Replace instruction-only commit message governance with a prompt hook that evaluates commit messages semantically.

**Config:** In `~/.claude/settings.json`, add:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "prompt",
            "prompt": "The user is running a git commit. Check: (1) Is the message semantic and descriptive (not 'fix bug' or 'update')? (2) Does it have the [feature-name] prefix if touching multiple files? (3) Does it NOT contain 'Co-Authored-By: Claude'? (4) If touching CLAUDE.md/MEMORY.md/improvement-log/hooks, does it have Evidence: and Affects: trailers? Return ok=false with reason if any check fails.",
            "conditions": ["input.command matches 'git commit'"]
          }
        ]
      }
    ]
  }
}
```

**Value:** Semantic enforcement of commit rules that can't be checked with grep/regex. Uses Haiku (cheap, fast). Replaces instruction-only governance.

**Risk:** False positives on legitimate short commit messages. Monitor for 2 weeks.

### 3.2 Embed source-check hook in researcher skill frontmatter
**What:** Instead of relying on global PostToolUse hook for source checking, embed it directly in the researcher skill. Fires only when researcher is active.

**Change:** Add to `~/Projects/skills/researcher/SKILL.md` frontmatter:
```yaml
hooks:
  PostToolUse:
    - matcher: "Write|Edit"
      hooks:
        - type: prompt
          prompt: "The researcher just wrote or edited a file. Check: does every factual claim in the written content have a source citation in brackets (e.g., [DATA], [A2], [Exa], [S2])? Return ok=false listing any unsourced claims."
```

**Value:** Source discipline enforced at the skill level, not globally. Reduces global hook complexity. The prompt hook can do semantic evaluation (is this actually a factual claim?) vs the current bash script which does text matching.

### 3.3 Intel: Large file read guard
**What:** From session analysis — agents waste tool calls trying to Read files >256KB without offset/limit.

**Config:** Add to intel's `.claude/settings.json`:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read",
        "hooks": [
          {
            "type": "command",
            "command": "INPUT=$(cat); FILE=$(echo \"$INPUT\" | python3 -c \"import sys,json; print(json.load(sys.stdin)['tool_input'].get('file_path',''))\"); if [ -f \"$FILE\" ]; then SIZE=$(stat -f%z \"$FILE\" 2>/dev/null || echo 0); if [ \"$SIZE\" -gt 262144 ]; then echo '{\"additionalContext\": \"WARNING: This file is '\"$(echo $SIZE | python3 -c 'import sys; s=int(sys.stdin.read()); print(f\"{s/1024:.0f}KB\" if s<1048576 else f\"{s/1048576:.1f}MB\")')\"' — use offset and limit parameters to read in chunks.\"}'; fi; fi"
          }
        ]
      }
    ]
  }
}
```

**Value:** Prevents wasted tool calls on large CSV/parquet files. Advisory only (doesn't block).

### 3.4 Intel: DuckDB dry-run hook on setup_duckdb.py changes
**What:** Auto-validate DuckDB views when code touching dataset definitions is committed.

**Config:** Add PostToolUse hook in intel that detects writes to `setup_duckdb.py` or `tools/datasets/`:
```json
{
  "matcher": "Write|Edit",
  "hooks": [
    {
      "type": "command",
      "command": "INPUT=$(cat); FILE=$(echo \"$INPUT\" | python3 -c \"import sys,json; print(json.load(sys.stdin)['tool_input'].get('file_path',''))\"); if echo \"$FILE\" | grep -qE '(setup_duckdb|tools/datasets/)'; then echo '{\"additionalContext\": \"You modified dataset code. Run: uv run python3 setup_duckdb.py --dry-run to validate all views before committing.\"}'; fi"
    }
  ]
}
```

**Value:** Catches view failures before they propagate. Advisory (reminds, doesn't block).

---

## Phase 4: Cross-Project Propagation

### 4.1 Selve: Add research quality Stop hook
**What:** Selve lacks the research quality gate that intel and genomics have. Deploy `stop-research-gate.sh`.

**Change:** Add to `selve/.claude/settings.json` (or settings.local.json):
```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/Users/alien/Projects/skills/hooks/stop-research-gate.sh"
          }
        ]
      }
    ]
  }
}
```

**Paths to check:** `docs/research/`, `docs/entities/` (adjust to selve's structure).

### 4.2 Genomics: Add persistent memory to pipeline agents
**What:** Genomics has 9 domain skills but no custom subagents with memory. The pipeline benefits from remembering which analyses succeeded/failed across sessions.

**Create:** `~/Projects/genomics/.claude/agents/pipeline-runner.md` with `memory: project`.

### 4.3 Propagate `model` field to all shared skills
**What:** Audit all 16 shared skills and add `model` field where appropriate.

**Candidates:**
| Skill | Pin to | Rationale |
|-------|--------|-----------|
| session-analyst | sonnet | Analysis, not creative. Cheaper. |
| model-guide | haiku | Reference lookup only |
| source-grading | haiku | Structured rubric application |
| debug-mcp-servers | haiku | Diagnostic, simple |
| epistemics | inherit | Needs whatever capability the session has |
| researcher | inherit | Task-dependent |
| model-review | inherit | Cross-model dispatch, model field irrelevant |

---

## Phase 5: Monitor / Evaluate Later

### 5.1 Agent teams (EXPERIMENTAL)
**When to revisit:** When it leaves experimental. Currently too many limitations (no resume, task lag, one team per session). Not a replacement for our orchestrator.

### 5.2 OTel export
**When to revisit:** When we want Grafana dashboards or need to debug cross-session performance patterns. Current JSONL pipeline is adequate.

### 5.3 Plugins
**When to revisit:** When distributing meta's toolkit to other users. Currently single-user setup — plugins add namespace overhead with no benefit.

### 5.4 `/batch` for entity refresh
**If Phase 1.1 succeeds:** Test `/batch refresh all entities in analysis/entities/ using the entity-refresher agent`. If it works, it becomes the code-change arm of the orchestrator. Data-refresh and research-sweep arms still need custom orchestration.

---

## What We Do NOT Replace

These stay custom. No native equivalent exists or the native version is inferior:

| Component | Why it stays |
|-----------|-------------|
| Orchestrator concept (cron + SQLite) | Native agent teams are session-scoped. We need cross-session, cross-project, scheduled. |
| Session-analyst pipeline | `/insights` is broad; session-analyst is structured, appends to improvement-log, triggers architectural fixes. |
| improvement-log → fix pipeline | No native equivalent. This is the error-correction ledger. |
| Cockpit receipts + dashboard | OTel needs infrastructure we don't have. JSONL + dashboard.py works. |
| Spinning detector | No native equivalent for same-tool repetition detection. |
| Idle notification (macOS) | No native macOS notification integration. |
| Cross-project hook/skill propagation | Native skills don't have a governance layer. |
| Hook ROI telemetry | Backlog item. No native hook analytics. |
| Intel backtest guard | Domain-specific temporal gating. No generic equivalent. |
| Data protection hooks (parquet, duckdb) | Domain-specific. Must stay custom. |

---

## Implementation Order

```
Week 1: Phase 1 (quick wins)
  1.1 Test /batch           → 30 min
  1.2 Test /simplify        → 15 min
  1.3 Add model fields      → 20 min, 5 files
  1.4 Fix spinning-detector → 15 min, 1 file
  1.5 Test /insights        → 10 min

Week 2: Phase 2 (subagent upgrades)
  2.1 entity-refresher memory    → 20 min, 1 file
  2.2 dataset-discoverer memory  → 15 min, 1 file
  2.3 researcher subagent        → 30 min, 1 new file
  2.4 session-analyst subagent   → 30 min, 1 new file

Week 3: Phase 3 (hook upgrades)
  3.1 Commit message prompt hook → 30 min, 1 file
  3.2 Researcher source hook     → 20 min, 1 file
  3.3 Large file read guard      → 20 min, 1 file
  3.4 DuckDB dry-run advisory    → 15 min, 1 file

Week 4: Phase 4 (propagation)
  4.1 Selve research gate        → 15 min, 1 file
  4.2 Genomics pipeline agent    → 30 min, 1 new file
  4.3 Model field propagation    → 20 min, 6 files
```

---

## Success Criteria

After 30 days, session-analyst should find:
1. **Zero wasted tool calls on large file reads** (Phase 3.3)
2. **Subagent researchers don't re-search already-known sources** (Phase 2.3 memory)
3. **Entity refresher skips known-broken data sources** (Phase 2.1 memory)
4. **Source discipline violations caught by prompt hooks, not post-hoc** (Phase 3.2)
5. **Commit message quality issues flagged before commit, not after** (Phase 3.1)
6. **Session-analyst findings don't duplicate previous reports** (Phase 2.4 memory)

Measure via: session-analyst runs comparing pre/post deployment, manual review of first 10 sessions per phase.

---

*Companion doc: `claude-code-native-vs-meta-infra.md` (same directory)*

<!-- knowledge-index
generated: 2026-03-22T00:15:44Z
hash: d0d666de2416

title: Native Leverage Plan: Claude Code Features → Project Infrastructure

end-knowledge-index -->
