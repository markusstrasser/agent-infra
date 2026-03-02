# PROJECT CONSTITUTION
Review against these principles, not your own priors.

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

# PROJECT GOALS

# Meta — Goals

> Human-owned. Agent may propose changes but must not modify without explicit approval.

## Mission

Maximize autonomous agent capability across all projects while maintaining epistemic integrity. The system should learn things once and handle them forever — the human intervenes only for genuinely new information, creative direction, or goal-setting.

## Generative Principle

**Maximize the rate at which agents become more autonomous, measured by declining supervision — AND maximize error correction per session across all projects.**

The deeper dynamic: the better the agent gets, the faster the human must rethink what they actually want next. This is an arms race — agent capability outpaces goal-setting until prediction quality is high enough that the agent can extrapolate what the human would want without asking. The endgame: wake up to 30 great ideas, say yes/no, go back to sleep.

## Primary Success Metric

**Ratio of autonomous-to-supervised work across sub-projects.** Measured qualitatively: when reviewing a day's chat logs, there should be no:
- Reverted work (build-then-undo)
- 5-hour runs that should have been 1-hour (missing scaffolding, bad DX)
- Error branch spirals (bad hooks, missing guards)
- Agent theater (performative work that produces no value)
- Repeated corrections for things already taught once

The closer sessions get to "optimal run" (what would happen if the agent had perfect tooling and perfect instructions), the better meta is doing its job.

## Secondary Metrics

- **Wasted supervision rate** — % of human turns that are corrections, boilerplate, or rubber stamps. Currently ~21%. No numeric target, but qualitative trend should be downward.
- **Agent reliability** — % of tasks completed correctly without correction.
- **Time-to-capability** — how fast a new project gets proper agent infrastructure.

## Self-Modification Boundaries

**Full autonomy within invariants**, with a gradient:
- **Clear improvement, one obvious path** → just do it, commit, move on
- **Multiple valid solutions, could change a lot** → propose and wait for human review
- **CLAUDE.md Constitution section / GOALS.md** → always human-approved

The invariants: the Constitution section (in CLAUDE.md) and GOALS.md are human-owned. Everything else (rest of CLAUDE.md, hooks, skills, maintenance checklists, rules, MEMORY.md) can be modified autonomously when the improvement is unambiguous.

## Strategy

1. **Session forensics** — session-analyst finds behavioral anti-patterns, improvement-log tracks them to architectural fixes
2. **Hook engineering** — deterministic guards that prevent known failure modes (instructions alone = 0% reliable)
3. **Observability** — cockpit components keep the human informed without requiring them to ask
4. **Research** — stay current on agent behavior research, absorb what's applicable, ignore what's not
5. **Cross-project propagation** — skills, hooks, rules, and patterns flow from meta to all projects
6. **Self-improvement** — meta improves its own tooling using the same methods it applies to sub-projects

## Orchestrator

**Unblocked.** The orchestrator is meta-level infrastructure, independent of any specific project's validation status. Build it for tasks that are clearly automatable now:
- Entity refresh cycles
- Data maintenance
- Research sweeps
- Self-improvement passes (`/project-upgrade`, `/goals` elicitation)

The vision: any project can receive `/project-upgrade` or `/goals` and get meta's full toolkit applied autonomously, stopping only when a quality judge determines no further improvement is possible given the project's goals.

## Research Cadence

**First-class function, not every-session.** Research is divergent thinking — exploring what's new, what's possible, what others have solved. Implementation is convergent — building, testing, eating your own dogfood.

The cycle: research (divergent) until diminishing returns → build (convergent) → use it → analyze whether it actually works → research again when stuck or when new information appears.

- **Not calendar-driven.** No fixed weekly sweep that degrades into checkbox behavior.
- **Opportunistic.** New model ships → immediate sweep. Stuck on a problem → search for prior art. Steep improvement curve → more research. Diminishing returns → more action.
- **Action produces information.** At some point, building and using is more informative than reading papers.

## Projects Served

All projects: intel, selve, genomics, skills, papers-mcp, and any future repos. The uneven attention to date (mostly intel) is an artifact of where work has concentrated, not a priority decision.

Meta provides: shared skills, hooks, MCP servers, maintenance checklists, session analysis, observability, and the research pipeline. Any project should be able to install meta's toolkit and benefit.

## Skills Ownership

**Meta owns skill quality.** Meta runs session analysis, sees when skills are applied across projects, and can judge whether they work. Claude Code knowledge is co-located here. The information flow is natural: session-analyst findings → skill improvements → propagation.

Skills (`~/Projects/skills/`) may merge into meta as a directory. For now, kept separate. But quality governance (authoring standards, testing, versioning, cross-project propagation) lives in meta regardless of directory structure.

## Quality Standard

Recurring patterns (used/encountered 10+ times) must become architecture — not instructions, not snippets, not manual habits. The Raycast-snippet heuristic: if you paste it 10 times, it should be a hook, a skill, or scaffolding.

Qualitative reports from session-analyst are the primary feedback mechanism. No arbitrary numeric targets — the goal is "no stupid shit in the logs," judged by comparing actual runs against what an optimal run would look like.

## Open Questions (dispatched to model-review)

- **Enforcement granularity** — which principles deserve hooks vs. which stay instructional? Hooks can be annoying. Need empirical data from meta sessions. Progressive approach for now.
- **Autonomy gradient threshold** — where exactly does "clear improvement" end and "multiple valid solutions" begin? Probably can't be defined precisely; needs examples over time.
- **Skills merge timing** — meta owns quality but skills/ is still separate. When/whether to merge directories.

## Deferred Scope

- **IB API / trading automation** — blocked by paper trading validation in intel, not meta's concern
- **Fraud/corruption separation** — stays in intel until compute burden forces a split
- **Numeric benchmarking** — qualitative assessment first, formalize metrics when patterns stabilize

## Exit Condition

Meta becomes unnecessary when:
1. Claude (5, 6, N) natively handles meta-improvement — eliciting user goals, applying project upgrades, working correctly across subdomains, benchmarking itself
2. Claude Code ships native equivalents of hooks, observability, session analysis
3. The creative/divergent capability (connecting old projects, finding novel solutions across domains) is handled natively

This may never fully happen — meta encodes domain-specific and personal-idiosyncratic knowledge that generic tooling won't replicate. But the goal is to make meta's job progressively smaller, not to preserve it.

## Resource Constraints

- Single human operator with limited attention
- Cost-conscious (session receipts track spend)
- Compute: local Mac + cloud APIs (Anthropic, Google, OpenAI, Exa)
- Storage: SSK1TB external drive for large datasets

---

*Created: 2026-02-28. Updated: 2026-02-28 (generative principle, self-modification boundaries, research philosophy, skills ownership). Elicited via goals + constitution questionnaire.*


# PLAN UNDER REVIEW

# Subagent Optimization Plan

**Session:** (from `.claude/current-session-id`)
**Date:** 2026-03-02
**Project:** meta (agent infrastructure)

## Context

Session transcript analysis shows 1,886 subagent calls across all projects. 60% (1,128) are `general-purpose` — a catch-all type that's mostly doing work Explore or direct tools could handle. Research evidence (Google arXiv:2512.08296) confirms multi-agent helps parallelizable tasks (+81%) but hurts sequential tasks (-70%), with diminishing returns once single-agent success exceeds 45%. The current 3-line `<subagent_usage>` instruction in global CLAUDE.md isn't working — instructions alone are known unreliable (EoG).

**Goal:** Reduce wasteful subagent spawns through measurement, sharper instructions, and advisory hooks. No blocking enforcement until data confirms low false-positive rates.

## Phase 1: Measure — SubagentStart Logger (~15 min)

Constitution requires "measure before enforcing." No SubagentStart hook exists today.

### 1.1 Create `~/Projects/skills/hooks/subagent-start-log.sh`

Log every subagent spawn to `~/.claude/subagent-log.jsonl`.

**Fields from SubagentStart event:** `agent_type`, `agent_id`, `session_id`, `cwd`
**Additional from environment:** timestamp, project name (basename of cwd)

```bash
#!/usr/bin/env bash
# subagent-start-log.sh — Log every subagent spawn for usage analysis.
# SubagentStart cannot block (no decision control). Side-effect only.
trap 'exit 0' ERR
INPUT=$(cat)
eval "$(echo "$INPUT" | python3 -c '
import sys, json
d = json.load(sys.stdin)
at = json.dumps(d.get("agent_type", "unknown"))
aid = json.dumps(d.get("agent_id", ""))
print(f"AGENT_TYPE={at}")
print(f"AGENT_ID={aid}")
' 2>/dev/null)"
SESSION_ID=""
[ -f .claude/current-session-id ] && SESSION_ID=$(cat .claude/current-session-id)
PROJECT=$(basename "$PWD")
echo "{\"ts\":\"$(date -u +%FT%TZ)\",\"event\":\"subagent_start\",\"agent_type\":$AGENT_TYPE,\"agent_id\":$AGENT_ID,\"session\":\"$SESSION_ID\",\"project\":\"$PROJECT\"}" >> ~/.claude/subagent-log.jsonl
exit 0
```

### 1.2 Wire into `~/.claude/settings.json`

Add new `SubagentStart` section (currently none exists):

```json
"SubagentStart": [
  {
    "hooks": [
      {
        "type": "command",
        "command": "/Users/alien/Projects/skills/hooks/subagent-start-log.sh"
      }
    ]
  }
]
```

### 1.3 Extend `subagent-epistemic-gate.sh` with completion logging

Add a 4-line logging block at the top of the existing SubagentStop hook (before the skip/exit logic), writing to the same JSONL with `event: "subagent_stop"` and `output_len: ${#MSG}`. This pairs start/stop by `agent_id` for duration and output size analysis.

**File:** `/Users/alien/Projects/skills/hooks/subagent-epistemic-gate.sh` (existing, extend)

---

## Phase 2: Instruction Sharpening (~10 min)

### 2.1 Rewrite `<subagent_usage>` in `~/.claude/CLAUDE.md`

Replace the current 3-line section (lines 112-115) with a concrete decision framework. Key insight from data: the problem is "when NOT to delegate" (specific, checkable), not "when to delegate" (vague).

```xml
<subagent_usage>
## Subagent Usage
Subagents are context shields — they prevent exploration from bloating your main window.

### Delegate when
- **Parallel independent axes** — 3+ searches/reads with no dependency between them
- **Context isolation** — exploration touching >5 files where you only need a summary
- **Named agents** with persistent memory (researcher, session-analyst, entity-refresher, etc.)

### Do NOT delegate (use direct tools)
- **Single-tool tasks** — one Grep, one Read, one search. Just run it.
- **Under 3 tool calls** — subagent overhead (setup + summary parsing) exceeds the work
- **Sequential chains needing intermediate results** — edit-then-verify, query-then-analyze
- **Suggestions or brainstorming** — "suggest improvements" agents produce ungrounded output
- **Confirming what's already in context** — don't delegate to verify what a Grep would answer
- **Explore covers it** — if you're exploring a codebase, use Explore, not general-purpose
</subagent_usage>
```

---

## Phase 3: Advisory Hooks (~25 min)

All hooks are advisory (exit 0 + additionalContext). No blocking until measurement confirms low false-positive rates.

### 3.1 PreToolUse:Agent gate — `pretool-subagent-gate.sh`

**File:** `/Users/alien/Projects/skills/hooks/pretool-subagent-gate.sh` (new)

Fires before every Agent tool call. Checks `tool_input.description` and `tool_input.subagent_type` for waste patterns.

**Checks:**
1. **Suggestion/brainstorm pattern** — description matches `suggest|brainstorm|ideas for|what could be` → warn
2. **Single-tool pattern** — description is short (<80 chars) and matches `^(search|find|grep|read|check|look up) ` → warn
3. **general-purpose when Explore would work** — `subagent_type == "general-purpose"` and description matches `explore|find files|codebase|search for` → suggest Explore instead

Each check outputs `additionalContext` JSON. Agent sees the warning, can proceed if it disagrees.

**Wire into `~/.claude/settings.json`:**
```json
{
  "matcher": "Agent",
  "hooks": [
    {
      "type": "command",
      "command": "/Users/alien/Projects/skills/hooks/pretool-subagent-gate.sh"
    }
  ]
}
```

This goes under `PreToolUse` alongside the existing Bash and search matchers.

### 3.2 SubagentStop result-size warning

Extend `subagent-epistemic-gate.sh` (after the existing provenance check) with output-size warning:

```bash
# Result-size check (after existing provenance logic)
if [ ${#MSG} -gt 2000 ]; then
    KB=$(( ${#MSG} / 1024 ))
    echo "{\"additionalContext\": \"SUBAGENT SIZE: ${AGENT_TYPE} returned ${KB}KB. Large results defeat context isolation — ask subagents to return conclusions, not raw data.\"}"
fi
```

### 3.3 Spinning detector — Agent-specific threshold

**File:** `/Users/alien/.claude/hooks/spinning-detector.sh` (existing, modify)

The spinning detector currently warns at 4 consecutive same-tool calls, alerts at 8. For `Agent` specifically, warn at 3 and alert at 5 — consecutive Agent spawns are almost always delegation cascades.

Add after line 38 (after `COUNT` is written to state), before the existing threshold checks:

```bash
# Agent-specific lower threshold — delegation cascades
if [[ "$TOOL" == "Agent" ]]; then
    if (( COUNT == 3 )); then
        echo "{\"additionalContext\": \"DELEGATION CASCADE: 3 consecutive Agent calls. Consider batching into one subagent or doing the work directly.\"}"
    elif (( COUNT >= 5 )); then
        echo "{\"additionalContext\": \"DELEGATION FLOOD: $COUNT consecutive Agent calls. Stop spawning and do the work directly.\"}"
    fi
    exit 0
fi
```

---

## Phase 4: Fix Existing Agents (~15 min)

### 4.1 Researcher Stop hook — fix broken `type: prompt`

MEMORY.md documents that skill-embedded prompt hooks on PostToolUse don't inject into conversation (verified 2026-03-02). The researcher agent's Stop hook uses `type: prompt` — likely has the same injection problem.

**File:** `~/.claude/agents/researcher.md`

Convert Stop hook from `type: prompt` to `type: command` with inline source-check:

```yaml
hooks:
  Stop:
    - hooks:
        - type: command
          command: "/Users/alien/Projects/skills/hooks/subagent-source-check-stop.sh"
```

Create `/Users/alien/Projects/skills/hooks/subagent-source-check-stop.sh` (~20 lines) that:
1. Reads `last_assistant_message` from stdin JSON
2. Checks for factual claim indicators (same regex as epistemic-gate)
3. Checks for source tags
4. If claims without tags: `echo '{"decision": "block", "reason": "..."}'`

This is the same logic as `subagent-epistemic-gate.sh` but as a Stop hook it can **block** (not just warn), forcing the researcher to add citations before completing.

### 4.2 Researcher maxTurns — 30 → 20

Research on context degradation shows quality drops beyond 15-20 turns. Current 30 is generous to the point of enabling runaway. Lower to 20.

**File:** `~/.claude/agents/researcher.md` — change `maxTurns: 30` to `maxTurns: 20`

### 4.3 No changes needed for other agents

- session-analyst: Well-configured (sonnet, memory: user, agent Stop hook). No changes.
- Intel agents (4): All have appropriate memory, model pinning, tool whitelists. No changes.

---

## Phase 5: Analysis Script (~15 min)

### 5.1 Create `meta/scripts/subagent-analysis.py`

Reads `~/.claude/subagent-log.jsonl`, produces:
- **Distribution:** agent_type breakdown (general-purpose vs named vs Explore)
- **Per-project breakdown**
- **Output size distribution** (from SubagentStop logs)
- **Daily trend**
- **Waste indicators:** count of subagents matching single-tool/suggestion patterns

Usage: `uv run python3 scripts/subagent-analysis.py --days 7`
Output: Markdown table to stdout.

---

## Files Changed

| File | Action | Phase |
|------|--------|-------|
| `~/Projects/skills/hooks/subagent-start-log.sh` | NEW | 1.1 |
| `~/.claude/settings.json` | Add SubagentStart + PreToolUse:Agent sections | 1.2, 3.1 |
| `~/Projects/skills/hooks/subagent-epistemic-gate.sh` | Extend (logging + size warning) | 1.3, 3.2 |
| `~/.claude/CLAUDE.md` | Rewrite `<subagent_usage>` (lines 112-115) | 2.1 |
| `~/Projects/skills/hooks/pretool-subagent-gate.sh` | NEW | 3.1 |
| `~/.claude/hooks/spinning-detector.sh` | Add Agent threshold (after line 38) | 3.3 |
| `~/Projects/skills/hooks/subagent-source-check-stop.sh` | NEW | 4.1 |
| `~/.claude/agents/researcher.md` | Fix Stop hook type + reduce maxTurns | 4.1, 4.2 |
| `~/Projects/meta/scripts/subagent-analysis.py` | NEW | 5.1 |

## What This Plan Does NOT Do

- **No new agents.** 7 existing agents cover the use cases. The problem is overuse of general-purpose, not missing specialized agents.
- **No blocking hooks.** Everything advisory until measurement confirms <10% false-positive rate.
- **No orchestrator.** Separate tracked item, different requirements.
- **No changes to Explore/Plan.** These are built-in Claude Code agents used appropriately (628 Explore calls are legitimate codebase exploration).

## Verification

1. **Immediate:** After deploying Phase 1-3, start a new session and intentionally trigger each hook (spawn a suggestion agent, spawn a single-tool agent, spawn 3 consecutive agents). Verify additionalContext warnings appear.
2. **7-day:** Run `subagent-analysis.py --days 7` to get baseline distribution.
3. **14-day:** Run session-analyst to check if subagent waste appears as a tracked failure mode.
4. **30-day:** Compare general-purpose count to baseline 1128. Target: <700. If >900, escalate from advisory to blocking (PreToolUse exit 2).

## Expected Outcomes

- General-purpose calls: 1128 → ~500-700 (40-60% reduction from instruction + advisory hooks)
- Zero suggestion-agent spawns (PreToolUse gate catches these explicitly)
- Researcher outputs consistently carry source tags (blocking Stop hook enforces)
- Subagent result sizes trend smaller (size warning teaches tighter scoping)
- New failure mode category in improvement-log for session-analyst to track


# REFERENCED FILES


## Current subagent_usage instruction (~/.claude/CLAUDE.md lines 112-115)

```
<subagent_usage>
## Subagent Usage
Use subagents when tasks can run in parallel, require isolated context, or involve independent workstreams that don't need to share state. For simple tasks, sequential operations, single-file edits, or tasks where you need to maintain context across steps, work directly rather than delegating. Don't spawn a subagent for something a single Grep or Read call would answer.
</subagent_usage>
```

## Current subagent-epistemic-gate.sh

```bash
#!/usr/bin/env bash
# subagent-epistemic-gate.sh — Check subagent outputs for provenance on factual claims.
# SubagentStop command hook. Advisory only (exit 0 + additionalContext).
#
# Skips code-focused subagents (Explore, Plan) where provenance tags don't apply.
# Checks last_assistant_message for factual claims (numbers, dates, proper nouns)
# without nearby provenance tags.

trap 'exit 0' ERR

INPUT=$(cat)

# Extract agent_type and last_assistant_message
eval "$(echo "$INPUT" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    agent_type = d.get("agent_type", "")
    msg = d.get("last_assistant_message", "")
    # Shell-safe: escape single quotes
    agent_type = agent_type.replace("'\''", "'\''\\'\'''\''")
    msg = msg.replace("'\''", "'\''\\'\'''\''")
    print(f"AGENT_TYPE='\''{ agent_type }'\''")
    print(f"MSG='\''{ msg[:2000] }'\''")  # Cap at 2000 chars
except Exception:
    print("AGENT_TYPE='\'''\''")
    print("MSG='\'''\''")
' 2>/dev/null)"

# Skip code-focused subagents where provenance tags are irrelevant
case "$AGENT_TYPE" in
    Explore|Plan|statusline-setup|claude-code-guide|session-analyst)
        exit 0
        ;;
esac

# Skip short outputs (likely not research-heavy)
if [ ${#MSG} -lt 200 ]; then
    exit 0
fi

# Check for factual claim indicators: dollar amounts, percentages, dates, specific numbers
HAS_CLAIMS=false
if echo "$MSG" | grep -qE '\$[0-9]|[0-9]+%|[0-9]{4}-[0-9]{2}|billion|million|trillion|according to|study|paper|found that|reported|measured'; then
    HAS_CLAIMS=true
fi

[ "$HAS_CLAIMS" = "false" ] && exit 0

# Check for provenance tags
HAS_TAGS=false
if echo "$MSG" | grep -qE '\[SOURCE:|\[DATABASE:|\[DATA\]|\[INFERENCE\]|\[SPEC\]|\[CALC\]|\[QUOTE\]|\[TRAINING-DATA\]|\[PREPRINT\]|\[FRONTIER\]|\[UNVERIFIED\]|\[[A-F][1-6]\]'; then
    HAS_TAGS=true
fi

if [ "$HAS_TAGS" = "false" ]; then
    echo "{\"additionalContext\": \"SUBAGENT PROVENANCE: The $AGENT_TYPE subagent returned factual claims without provenance tags. Before incorporating these claims into your output, verify them or add appropriate tags ([SOURCE:], [SPEC], [TRAINING-DATA], etc.). Unsourced subagent claims compound error across steps.\"}"
fi

exit 0
```

## Current spinning-detector.sh

```bash
#!/usr/bin/env bash
# spinning-detector.sh — Detect agent stuck in tool-call loops.
# PostToolUse hook. Warns (stdout) if same tool called 4+ times consecutively.
# Uses $PPID (Claude Code parent PID) for session-scoped state.

trap 'exit 0' ERR

INPUT=$(cat)

TOOL=$(echo "$INPUT" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get("tool_name", ""))
except Exception:
    print("")
' 2>/dev/null)

[[ -z "$TOOL" ]] && exit 0

STATE="/tmp/claude-spinning-$PPID"

if [[ -f "$STATE" ]]; then
  LAST_TOOL=$(sed -n '1p' "$STATE")
  COUNT=$(sed -n '2p' "$STATE")
  COUNT=${COUNT:-0}
else
  LAST_TOOL=""
  COUNT=0
fi

if [[ "$TOOL" == "$LAST_TOOL" ]]; then
  COUNT=$((COUNT + 1))
else
  COUNT=1
fi

printf '%s\n%s\n' "$TOOL" "$COUNT" > "$STATE"

if (( COUNT == 4 )); then
  echo "{\"additionalContext\": \"SPINNING WARNING: You have called $TOOL $COUNT times consecutively. You may be stuck in a loop. Stop and reconsider your approach — try a different tool or strategy.\"}"
elif (( COUNT >= 8 )); then
  echo "{\"additionalContext\": \"SPINNING ALERT: You have called $TOOL $COUNT times consecutively. You are almost certainly stuck. STOP repeating the same tool call. Explain what you're trying to achieve and try a completely different approach.\"}"
fi

exit 0
```

## Current researcher.md agent definition

```yaml
---
name: researcher
description: Deep research agent with persistent memory of sources checked, papers read, and search strategies that worked. Use for any research task requiring multiple sources and epistemic rigor.
memory: user
maxTurns: 30
skills:
  - researcher
  - epistemics
  - source-grading
hooks:
  Stop:
    - hooks:
        - type: prompt
          prompt: "Check the research output. Does every factual claim have a source citation in brackets (e.g., [DATA], [A2], [Exa], [S2], [PubMed])? Are there any unsourced assertions presented as fact? Is there at least one attempt at disconfirmation? Return ok=false listing any gaps."
---

You are a research agent with persistent cross-session memory.

## Memory Usage

Check your MEMORY.md before starting any research:
- Which sources were already checked for this topic
- Which search strategies produced useful results
- Which APIs or databases had errors or rate limits
- Which papers were already read and summarized

After completing research, update your memory with:
- New sources discovered and their quality
- Search strategies that worked (save the query terms)
- Sources that were empty or irrelevant (save to avoid re-checking)
- Any API/tool issues encountered

## Delegation

Your research instructions come from the preloaded `researcher` skill. Follow its phases, tool routing, and output contract. The `epistemics` and `source-grading` skills provide domain-specific evaluation frameworks when relevant.
```

## Current settings.json (global hooks)

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/alien/Projects/skills/hooks/pretool-bash-loop-guard.sh"
          },
          {
            "type": "command",
            "command": "cmd=$(echo \"$CLAUDE_TOOL_INPUT\" | grep -oE '\"command\":\\s*\"[^\"]*\"' | head -1); if echo \"$cmd\" | grep -qE '\"(python |python3 )' && ! echo \"$cmd\" | grep -q 'uv run'; then echo 'BLOCK: use \"uv run python\" not bare python'; exit 2; fi"
          },
          {
            "type": "command",
            "command": "/Users/alien/Projects/skills/hooks/pretool-commit-check.sh"
          }
        ]
      },
      {
        "matcher": "mcp__exa|mcp__research|mcp__paper-search|WebSearch|WebFetch",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/alien/Projects/skills/hooks/pretool-search-burst.sh"
          },
          {
            "type": "command",
            "command": "/Users/alien/Projects/skills/hooks/pretool-consensus-search.sh"
          }
        ]
      },
      {
        "hooks": [
          {
            "type": "command",
            "command": "/Users/alien/.claude/hooks/tool-tracker.sh"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "INPUT=$(cat); FPATH=$(echo \"$INPUT\" | grep -oE '\"file_path\"\\s*:\\s*\"[^\"]*MEMORY\\.md\"' | head -1); if [ -n \"$FPATH\" ]; then FILE=$(echo \"$FPATH\" | sed 's/.*\"file_path\"\\s*:\\s*\"//;s/\"//'); if [ -f \"$FILE\" ]; then LINES=$(wc -l < \"$FILE\"); if [ \"$LINES\" -gt 180 ]; then echo \"WARNING: MEMORY.md is $LINES lines (limit 200, truncated at load). Move detailed content to topic files and keep MEMORY.md as a concise index.\" >&2; fi; fi; fi"
          },
          {
            "type": "command",
            "command": "/Users/alien/Projects/skills/hooks/postwrite-source-check.sh"
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/alien/Projects/skills/hooks/posttool-bash-failure-loop.sh",
            "statusMessage": "Checking for failure loops..."
          },
          {
            "type": "command",
            "command": "/Users/alien/Projects/skills/hooks/posttool-review-check.sh"
          }
        ]
      },
      {
        "hooks": [
          {
            "type": "command",
            "command": "/Users/alien/.claude/hooks/spinning-detector.sh"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/Users/alien/Projects/skills/hooks/stop-uncommitted-warn.sh"
          },
          {
            "type": "command",
            "command": "/Users/alien/.claude/hooks/stop-debrief.sh"
          },
          {
            "type": "command",
            "command": "/Users/alien/.claude/hooks/stop-notify.sh"
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/Users/alien/Projects/skills/hooks/precompact-log.sh",
            "async": true
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/Users/alien/Projects/skills/hooks/userprompt-context-warn.sh"
          },
          {
            "type": "command",
            "command": "/Users/alien/.claude/hooks/tab-color.sh working"
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/Users/alien/.claude/hooks/session-init.sh"
          }
        ]
      }
    ],
    "SubagentStop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/Users/alien/Projects/skills/hooks/subagent-epistemic-gate.sh"
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/Users/alien/Projects/skills/hooks/sessionend-log.sh",
            "async": true
          },
          {
            "type": "command",
            "command": "/Users/alien/Projects/skills/hooks/sessionend-overview-trigger.sh",
            "async": true
          }
        ]
      }
    ]
  },
  "statusLine": {
    "type": "command",
    "command": "~/.claude/statusline.sh"
  },
  "enabledPlugins": {
    "frontend-design@claude-plugins-official": true,
    "playground@claude-plugins-official": true,
    "claude-md-management@claude-plugins-official": true
  },
  "skipDangerousModePermissionPrompt": true
}
```

## Research evidence: multi-agent coordination

# Multi-Agent Coordination — Now With Controlled Experiments

*Split from `frontier-agentic-models.md` on 2026-03-01. Part of the [agentic research synthesis](agentic-research-synthesis.md).*
*Date: 2026-02-27. Models in scope: Opus 4.6, GPT-5.2/5.3, Gemini 3.1 Pro.*

---

### What's PROVEN

**NEW — Google "Towards a Science of Scaling Agent Systems" (arXiv:2512.08296, Dec 2025):** The first controlled experiment we were waiting for. 180 agent configurations, 5 architectures, 3 LLM families, 4 benchmarks. [SOURCE: arXiv:2512.08296, research.google/blog]

Key findings:
1. **Multi-agent dramatically improves parallelizable tasks (+81%)** but **degrades sequential tasks (-70%).** Coordination benefits are task-contingent.
2. **Error amplification:** Independent agents amplify errors up to **17x**. Centralized coordination limits to **4.4x**. This is why orchestrator-worker beats peer-to-peer.
3. **45% threshold:** Once a single agent hits ~45% success rate, adding agents brings diminishing or negative returns.
4. **Predictive model:** Identifies optimal architecture for 87% of unseen tasks using coordination metrics (efficiency, overhead, error amplification, redundancy). Cross-validated R²=0.513. [SOURCE: arXiv:2512.08296]

**NEW — "Single-agent or Multi-agent? Why Not Both?" (arXiv:2505.18286, May 2025):** MAS benefits over SAS **diminish as LLM capabilities improve**. Frontier LLMs (o3, Gemini 2.5 Pro) have advanced enough in long-context reasoning, memory retention, and tool usage that many MAS motivations are now mitigated. Proposes LLM-based routing: complexity assessment → route to single or multi based on threshold. [SOURCE: arXiv:2505.18286]

**NEW — "Debate or Vote" (arXiv:2508.17536):** Debate is a martingale — no expected correctness improvement. Majority voting alone captures most multi-agent gains. See [agent-reliability-benchmarks.md](agent-reliability-benchmarks.md) for details.

**NEW — MAST Taxonomy "Why Do Multi-Agent LLM Systems Fail?" (arXiv:2503.13657, March 2025, v3 Oct 2025):** 14 failure modes in 3 categories across 1,600+ annotated traces, 7 frameworks. Categories: System Design Issues, Inter-Agent Misalignment, Task Verification. Key finding: agents converge on shared evidence without eliciting unobserved knowledge from each other. Step repetition and conversation history loss are prevalent. Provides granular taxonomy complementing our high-level failure modes. [SOURCE: arXiv:2503.13657] [PUBLISHED]

### What was SPECULATED → NOW RESOLVED

- ~~Whether multi-agent fundamentally outperforms single-agent for complex tasks.~~ → **IT DEPENDS ON TASK STRUCTURE.** Parallelizable → yes (+81%). Sequential → no (-70%). The question was wrong — it's not single vs multi, it's matching architecture to task decomposition structure.
- ~~Whether coordination overhead is worth it.~~ → **Only for parallelizable tasks, and only until the single agent passes 45% success rate.** After that, diminishing or negative returns.

### Engineering implications for us

Our current architecture is validated: **orchestrator (Opus) + worker subagents (Sonnet) with centralized coordination.** The Google study shows centralized coordination limits error amplification to 4.4x vs 17x for independent agents.

**NEW decision:** Route by task structure. Research tasks (multiple independent search axes) → multi-agent parallelization. Sequential analysis tasks (entity investigation, hypothesis testing) → single agent. We're already doing this implicitly with the researcher skill's parallel dispatch — make it explicit.

**NEW risk:** The 45% threshold means for our best tasks (entity refresh, signal scanning), adding agents may already be past diminishing returns. Only parallelize when the single-agent success rate is below 45%.
