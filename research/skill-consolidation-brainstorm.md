# Skill Consolidation: From 42 Skills to Synergistic Architecture

**Source data:** Full inventory (48 dirs, 42 active), diagnostic output analysis, model-guide routing, loop/schedule infrastructure review.

## The Problem

42 user-invocable skills is too many. The friction is:
1. **Discovery:** Which skill do I use? session-analyst vs design-review vs retro?
2. **Composition:** Running the full quality loop is 3-5 manual invocations
3. **No loop/schedule awareness:** Skills weren't designed for `/loop 15m` or `/schedule`
4. **Duplicate plumbing:** Transcript extraction, Gemini dispatch, output format repeated across 4+ skills
5. **Reference docs masquerading as skills:** llmx-guide, model-guide, claude-api, epistemics, modal, etc. are docs, not workflows

## Design Principles

1. **One skill per WORKFLOW, not per TECHNIQUE.** Session-analyst and design-review are the same workflow (analyze sessions) with different lenses.
2. **Modes, not multiplied skills.** `observe --sessions` vs `observe --architecture` vs `observe --retro`.
3. **Loop-native.** Every skill declares if it's loop-compatible and what interval makes sense.
4. **Pipeline composition.** `/morning` = harvest → rank → show. `/evening` = analyze → retro → harvest.
5. **Reference docs are references/, not skills.** Loaded on demand by the skills that need them.
6. **Preserve all nuance.** Each existing SKILL.md becomes a `references/` file in the consolidated skill. Nothing is deleted — it's reorganized.

## The Architecture: 6 Workflows + References + Standalone

### Workflow 1: `observe` — Diagnostic Production

**Absorbs:** session-analyst, design-review, retro, supervision-audit

**Why one skill:** All four (a) read session transcripts, (b) detect patterns, (c) produce improvement-log entries. They differ in WHAT they look for, not HOW they work.

**Modes:**

| Invocation | What it does | Dispatches to | Loop? |
|---|---|---|---|
| `/observe sessions [project] [N]` | Behavioral anti-patterns (20 taxonomy) | Gemini 3.1 Pro | `/loop 4h` |
| `/observe architecture [project]` | Missing abstractions, repeated workflows | Gemini 3.1 Pro | Weekly |
| `/observe retro` | End-of-session reflection | Local (no dispatch) | No (one-shot) |
| `/observe supervision` | Wasted supervision patterns | Gemini 3.1 Pro | Weekly |
| `/observe` (no args) | Smart default: retro if session ending, sessions if morning | Auto | — |

**Shared plumbing:**
- `scripts/extract_transcript.py` (already shared between session-analyst and design-review)
- `scripts/coverage-digest.sh` (dedup against existing findings)
- Output format: improvement-log.md entries (standardized across all modes)
- `references/gemini-dispatch-*.md` (mode-specific prompts, loaded on demand)
- `references/grounding-examples.md`, `references/findings-staging.md` (shared)

**What stays mode-specific:**
- The Gemini prompt (each mode has its own taxonomy/lens)
- The anti-pattern list (session-analyst's 20 items vs design-review's pattern types)
- Output enrichment (design-review produces patterns.jsonl, session-analyst produces quality scores)

### Workflow 2: `improve` — Synthesis + Implementation

**Absorbs:** harvest, suggest-skill, maintain, tick

**Why one skill:** All four consume diagnostic outputs and produce improvements. They differ in SCOPE (gather vs suggest vs implement).

**Modes:**

| Invocation | What it does | Loop? |
|---|---|---|
| `/improve harvest` | Gather+dedup findings from all sources → ranked backlog | No |
| `/improve suggest` | Detect repeated workflows → skill candidates | No |
| `/improve maintain` | Routine checks + implement top confirmed findings | `/loop 15m` |
| `/improve tick` | Single orchestrator tick | `/loop 5m` |
| `/improve` (no args) | harvest → show top 5 → implement top confirmed | — |

**Key design:** `maintain` mode is the loop workhorse. It checks:
1. Any confirmed findings in improvement-log not yet implemented?
2. Any hook ROI data suggesting promotion/demotion?
3. Any harness-changelog entries showing regression? (NEW from Meta-Harness)
4. Any quality score trends worth flagging? (NEW)

### Workflow 3: `review` — Cross-Model Validation

**Absorbs:** model-review, verify-findings, plan-close

**Why one skill:** All three validate work product against external models. They differ in WHAT gets reviewed and WHEN.

**Modes:**

| Invocation | What it does | Dispatches to |
|---|---|---|
| `/review model [target]` | Adversarial cross-model review | Gemini Pro + GPT-5.4 |
| `/review verify [findings]` | Fact-check claims against code | Local |
| `/review close [plan]` | Post-implementation tests + review | Gemini Pro + GPT-5.4 |
| `/review` (no args) | Auto-detect: recent plan → close, recent findings → verify | Auto |

**Shared plumbing:**
- `scripts/model-review.py` (dispatch to llmx)
- `scripts/build_plan_close_context.py` (context assembly)
- Disposition format: CONFIRMED / HALLUCINATED / CORRECTED / DEFERRED
- `references/prompting-*.md` (model-specific tips, from model-guide)

### Workflow 4: `research` — Discovery + Synthesis

**Absorbs:** researcher, research-cycle, knowledge-compile, knowledge-diff, dispatch-research

**Modes:**

| Invocation | What it does | Loop? |
|---|---|---|
| `/research [query]` | One-shot research with MCP tools | No |
| `/research cycle` | CORAL-epoch autonomous loop (reads CYCLE.md) | `/loop 15m` |
| `/research compile [topic]` | Synthesize memos into unified article | No |
| `/research diff [text]` | Extract what's NOT in training data | No |
| `/research dispatch` | Parallel Codex audit sweep | No |

**Shared:** MCP tool orchestration, source grading, evidence hierarchy, output format.

### Workflow 5: `analyze` — Reasoning Frameworks

**Absorbs:** causal-check, causal-dag, causal-robustness, competing-hypotheses, investigate

**Modes:**

| Invocation | What it does |
|---|---|
| `/analyze causal [question]` | Causal inference check (observation geometry) |
| `/analyze dag` | Build DAG, identify adjustment sets |
| `/analyze robustness` | Post-estimation sensitivity (PySensemakr) |
| `/analyze hypotheses` | Analysis of Competing Hypotheses (ACH) |
| `/analyze investigate [target]` | Forensic deep-dive (adversarial) |

**Pipeline:** `dag` → `robustness` is a natural sequence. The skill can auto-suggest.

### Workflow 6: `upgrade` — Codebase Improvement

**Absorbs:** project-upgrade, novel-expansion, agent-pliability, evolution-forensics

**Modes:**

| Invocation | What it does | Dispatches to |
|---|---|---|
| `/upgrade audit` | Gemini+GPT parallel bug-finding | Gemini Pro + GPT-5.4 |
| `/upgrade harness` | Find architectural leverage (hooks, enforcement) | Gemini Pro + GPT-5.4 |
| `/upgrade discover` | Novel analysis discovery + implementation | Local + research |
| `/upgrade pliability` | Make files agent-discoverable | Local |
| `/upgrade forensics` | Longitudinal concept lifecycle analysis | Local |

### Reference Docs (not user-invocable, loaded on demand)

| Current skill | Becomes | Loaded by |
|---|---|---|
| llmx-guide | `references/llmx-guide/` | review, observe, research (any skill dispatching via llmx) |
| model-guide | `references/model-guide/` | review (model selection), observe (Gemini dispatch) |
| claude-api | `references/claude-api/` | Any skill writing API code |
| epistemics | `references/epistemics/` | research, analyze |
| source-grading | `references/source-grading/` | research, analyze, investigate mode |
| data-acquisition | `references/data-acquisition/` | research dispatch mode |
| modal | Stays standalone (runtime, not reference) | — |
| google-workspace | Stays standalone | — |
| browse | Stays standalone | — |
| debug-mcp-servers | `references/debug-mcp/` | On demand |

### Standalone Skills (distinct enough to keep separate)

| Skill | Why standalone |
|---|---|
| brainstorm | Divergent ideation — orthogonal to all workflows |
| negative-space-sweep | Absence detection — unique methodology |
| de-slop | Text editing — different domain entirely |
| entity-management | Data management — not a workflow |
| constitution | Project setup — rare, high-stakes |
| skill-authoring | Meta-skill — creates other skills |
| trending-scout | Ecosystem monitoring — external-facing |

## Result: 42 → 6 workflows + 7 standalone + references

| Before | After | Reduction |
|---|---|---|
| 42 user-invocable skills | 13 (6 workflows + 7 standalone) | -69% |
| 0 skills declaring loop compatibility | 4 modes with explicit loop intervals | — |
| 0 pipeline compositions | 3 named pipelines (morning, evening, weekly) | — |
| 6 reference-only skills cluttering the list | 0 (moved to references/) | -6 |

## Named Pipelines (sugar, not separate skills)

These are just sequences that could be aliases or documented patterns:

| Pipeline | Sequence | When |
|---|---|---|
| `/morning` | `improve harvest` → show ranked items → propose top 3 | Daily, or `/schedule 05:00` |
| `/evening` | `observe retro` → `observe sessions --today` | End of work day |
| `/weekly` | `observe architecture` → `observe supervision` → `improve harvest` → `upgrade harness --deferred` | Weekly |

## Loop/Schedule Declarations

New frontmatter field: `loop-compatible: { interval: "15m", state: "CYCLE.md" }`

```yaml
---
name: improve
loop-compatible:
  modes: [maintain, tick]
  interval: "15m"  # default for /loop
  state: ".claude/maintain-state.json"
---
```

## Migration Strategy

1. **Phase 0:** Create the 6 new workflow skills with SKILL.md that routes to modes.
2. **Phase 1:** Move existing references/ and scripts/ into the new structure.
3. **Phase 2:** Each old SKILL.md becomes `references/{old-name}.md` in the new skill.
4. **Phase 3:** Update cross-skill references (model-review → review --model, etc.)
5. **Phase 4:** Archive old skill directories to `_archive/`.
6. **Phase 5:** Update CLAUDE.md registered skills lists, hook matchers, etc.

**Critical constraint:** Old skill names must keep working during transition. The SKILL.md for `session-analyst` can become a thin redirect: "This skill has been consolidated into `/observe --sessions`. Running that now."

## What We Gain

1. **Discoverable:** 13 skills, not 42. Each name maps to a workflow, not a technique.
2. **Composable:** Named pipelines for common sequences. `/morning` is one command.
3. **Loop-native:** `maintain` and `research cycle` declare their intervals. `/loop 15m /improve maintain` is the documented way to run them.
4. **No lost nuance:** Every existing SKILL.md, prompt, grounding example, and anti-pattern taxonomy lives in `references/`. The consolidated skill ROUTES to them.
5. **Shared plumbing:** Transcript extraction, Gemini dispatch, output format, disposition tables — written once, used by all modes.
6. **Harness-aware:** The new `improve maintain` mode integrates harness-changelog and quality scores from today's Meta-Harness work.

## What We Lose

1. **Direct invocation simplicity:** `/session-analyst meta 5` → `/observe sessions meta 5` (slightly longer).
2. **Independent evolution:** Changing the session-analyst prompt now means editing `observe/references/session-analyst-prompt.md` inside a larger skill.
3. **Skill-level metrics:** Hook telemetry logs skill invocations. Consolidated skills need mode-level tracking.

## Open Questions

1. **Redirect period:** How long do old skill names keep working as thin redirects?
2. **Reference skills:** Should llmx-guide and model-guide stay user-invocable (they're useful for ad-hoc lookup) even though they're conceptually references?
3. **Pipeline syntax:** Is `/morning` a skill, a just recipe, or a `/loop` pattern?
4. **Skill-creator plugin:** The official plugin creates skills — does consolidation break its assumptions?

## Revisions

(None yet — initial brainstorm)

<!-- knowledge-index
generated: 2026-04-08T05:43:35Z
hash: a017a5b9c95c


end-knowledge-index -->
