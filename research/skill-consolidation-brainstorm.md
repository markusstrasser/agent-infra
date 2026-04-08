# Skill Consolidation: From 42 Skills to Synergistic Architecture

**Source data:** Full inventory (48 dirs, 42 active), diagnostic output analysis, model-guide routing, loop/schedule infrastructure review, **empirical usage data (543 skill invocations across all projects).**

## The Problem

42 user-invocable skills is too many. The friction is:
1. **Discovery:** Which skill do I use? session-analyst vs design-review vs retro?
2. **Composition:** Running the full quality loop is 3-5 manual invocations
3. **No loop/schedule awareness:** Skills weren't designed for `/loop 15m` or `/schedule`
4. **Duplicate plumbing:** Transcript extraction, Gemini dispatch, output format repeated across 4+ skills
5. **Reference docs masquerading as skills:** llmx-guide, model-guide, claude-api, epistemics, modal, etc. are docs, not workflows

## Design Principles

1. **Engine + Lens separation.** Skills are composed of reusable ENGINES (transcript extraction, Gemini dispatch, cross-model dispatch, loop ticker) and swappable LENSES (behavioral anti-patterns, architectural patterns, adversarial review). Engines are shared infrastructure. Lenses are prompt files. This is already empirically true: `extract_transcript.py` is shared by 4 skills.
2. **User-facing names are workflows, internal structure is engine+lens.** Users invoke `/observe sessions` (intuitive). Internally it's `gemini-analysis engine` + `behavioral-antipatterns lens`. The workflow name is the routing layer; engines and lenses are the implementation.
3. **New perspectives = new lens files, not new skills.** Adding a new analysis type (e.g., "cost waste detection") = one prompt file in `lenses/`, not a new skill directory with SKILL.md + references/ + scripts/.
4. **Loop-native.** Every skill declares if it's loop-compatible and what interval makes sense.
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

**Engine:** `gemini-analysis` — transcript extraction → coverage digest → Gemini 3.1 Pro dispatch → finding staging. Shared across all modes except retro (which uses `local-analysis` engine).

**Lenses** (prompt files in `lenses/`):
- `behavioral-antipatterns.md` — 20-item taxonomy from session-analyst (W:1-5, ternary scoring)
- `architectural-patterns.md` — pattern extraction from design-review (TOOL_GAP, WORKFLOW_REPEAT, etc.)
- `supervision-waste.md` — correction/boilerplate/rubber-stamp classification from supervision-audit
- `retro-reflection.md` — end-of-session local analysis (no external dispatch)

**Adding a new perspective** = write one lens file. No new skill, no SKILL.md changes, no scripts. Example: "cost waste detection" lens = prompt file that asks Gemini to identify unnecessary API calls, redundant model dispatches, over-provisioned compute.

**Shared infrastructure:**
- `scripts/extract_transcript.py` (already shared by 4 skills — empirically validated)
- `scripts/coverage-digest.sh` (dedup against existing findings)
- Output: unified findings schema (all lenses produce the same JSON)
- `references/grounding-examples.md`, `references/findings-staging.md`

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

**Engine:** `cross-model-dispatch` — context assembly → parallel llmx dispatch (Gemini + GPT) → output capture → extraction → disposition table. Shared across `model` and `close` modes. `verify` mode uses `local-analysis` engine (grep/read against code, no external dispatch).

**Lenses:**
- `adversarial-review.md` — find what's wrong (convergent, standard model-review)
- `plan-close-review.md` — post-implementation correctness + coverage gaps
- `verification.md` — fact-check claims against actual code (local, no dispatch)

**Shared infrastructure:**
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

### Engine Inventory (shared infrastructure, maintained once)

| Engine | What it does | Used by | Key scripts |
|---|---|---|---|
| `gemini-analysis` | Transcript extraction → coverage digest → Gemini dispatch → finding staging | observe (sessions, architecture, supervision) | `extract_transcript.py`, `coverage-digest.sh` |
| `cross-model-dispatch` | Context assembly → parallel llmx (Gemini+GPT) → extraction → disposition | review (model, close), upgrade (audit, harness) | `model-review.py`, `build_plan_close_context.py` |
| `codex-parallel` | Parallel Codex CLI dispatch → output extraction → verification | research (dispatch) | `codex_dispatch.py` |
| `local-analysis` | No external dispatch — grep, read, git log, pattern matching | observe (retro), review (verify), improve (harvest), analyze (all) | — |
| `loop-ticker` | State file management, incremental work, timeout awareness | improve (maintain, tick), research (cycle) | — |
| `mcp-orchestrator` | MCP tool orchestration (S2, Exa, Brave, Perplexity) with source grading | research (query, cycle, compile) | — |

**Adding a new lens to any engine** = one prompt file. No code changes. The engine handles extraction, dispatch, output capture, and finding staging. The lens defines what to look for and how to interpret results.

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

## Empirical Usage Data (543 invocations, all projects, 30 days)

| Skill | Invocations | Category |
|---|---|---|
| model-review | 121 | → `review` |
| researcher | 56 | → `research` |
| model-guide | 32 | Reference (keep invocable) |
| modal | 31 | Standalone |
| llmx-guide | 31 | Reference (keep invocable) |
| brainstorm | 26 | Standalone |
| causal-check | 23 | → `analyze` |
| retro | 21 | → `observe` |
| bio-verify | 16 | Domain-specific (genomics) |
| design-review | 14 | → `observe` |
| session-analyst | 10 | → `observe` |
| data-acquisition | 10 | Standalone |
| dispatch-research | 8 | → `research` |
| research-cycle | 6 | → `research` |
| plan-close | 5 | → `review` |
| agent-pliability | 5 | → `upgrade` |
| skill-authoring | 4 | Standalone |
| maintain | 3 | → `improve` |
| project-upgrade | 3 | → `upgrade` |
| de-slop | 3 | Standalone |
| All others | ≤2 each | Low usage |

**Key insights:**
- model-review is 22% of ALL skill invocations — the review workflow is the most important
- model-guide and llmx-guide get 63 lookups combined — they're genuinely used as references, keep invocable
- The diagnostic cluster (retro + design-review + session-analyst) = 45 calls — distinct enough in frequency to be separate modes
- 18 skills have ≤2 invocations — candidates for absorption or archive
- maintain has only 3 invocations despite being loop-designed — loop adoption is low

## Unified Findings Log (Cross-Skill)

**Idea:** All diagnostic modes (`observe`, `improve`, `review`, `upgrade`) append to the same append-only log per project. Currently session-analyst → improvement-log.md, design-review → patterns.jsonl, retro → session-retro/*.json. Three different formats, three different locations.

**Proposal:** Single `findings.jsonl` per project (append-only, hook-guarded). Every diagnostic skill appends structured findings in the same schema:

```json
{
  "ts": "2026-04-07T10:30:00Z",
  "source": "observe/sessions",
  "session_uuid": "abc12345",
  "project": "meta",
  "category": "TOKEN_WASTE",
  "severity": "medium",
  "summary": "13 sequential WebFetch calls instead of API script",
  "evidence": "...",
  "proposed_fix": "hook | rule | script",
  "status": "proposed"
}
```

**Benefits:**
- `harvest` becomes a simple `jq` query over one file, not multi-source artifact scanning
- Quality scores can join findings to harness versions automatically
- Session-analyst, design-review, retro, supervision-audit all produce the same format
- Cross-project queries: `cat ~/Projects/*/findings.jsonl | jq ...`

**improvement-log.md stays** as the human-readable narrative. findings.jsonl is the machine-readable substrate. The log is derived from the JSONL, not the other way around.

## Resolved Questions (from user feedback)

1. **No backward compatibility.** Breaking refactor — delete old skills, no redirects, no wrappers.
2. **model-guide and llmx-guide stay user-invocable** — 63 combined invocations proves they're used for ad-hoc lookup. They're both reference docs AND quick-lookup skills.
3. **No named pipelines.** Any composition can be relevant at any time. Skills compose freely, not via hardcoded sequences.
4. **Skill-creator plugin:** Unaffected — it creates new skills, doesn't modify existing ones.

## Cross-Model Review Findings (2026-04-07)

Reviewed by Gemini 3.1 Pro (arch) + GPT-5.4 (formal). Both models converged on critical issues.

### Adopted

1. **Decouple findings.jsonl from consolidation.** Both models flagged bundling naming/routing + schema/telemetry as the highest-risk sub-change. Constitution says "isolate harness changes." findings.jsonl is a separate initiative.

2. **Archive the long tail FIRST.** 18 skills with ≤2 invocations = 42.9% count reduction touching ≤6.6% of traffic. Highest ROI, lowest risk. Do before workflow consolidation.

3. **Honest count: 42→~18, not 42→13.** Exceptions (model-guide, llmx-guide invocable; modal, google-workspace, browse standalone) make the real post-state ~18. Still 57% reduction — state it honestly.

4. **Mode-level telemetry as prerequisite.** Without it, we lose the 543-invocation baseline and can't measure whether consolidation helped. Add `{skill, mode, project, ts}` logging before any renames.

5. **findings.jsonl schema additions.** Add `harness_hash`, `commit_hash`, `blast_radius` when that initiative starts.

6. **Hook telemetry preservation.** Log both consolidated name AND mode to maintain historical comparability.

7. **Auto-discovery subcommands.** Each consolidated skill lists modes when called without args.

8. **Cross-project call site migration.** Explicit step: grep all CLAUDE.md, hooks, justfiles for old skill names across all projects.

### Rejected

- Named pipelines as cron jobs (user rejected pipelines entirely)
- Pre-execution rewrite hook for backward compat (user wants clean break)
- Selection-rationale as separate artifact (this brainstorm + review IS the artifact)

### Revised Implementation Order

| Phase | Scope | Traffic risk |
|---|---|---|
| **A** | Canonical post-state inventory + mode-level telemetry | 0% |
| **B** | Archive 18 long-tail skills (≤2 uses) | ≤6.6% |
| **C** | Consolidate `observe`, `research`, `analyze`, `upgrade` | ~25% |
| **D** | Consolidate `review` (highest traffic — 22%) | ~22% |
| **E** | Reassess actual count, verify narrative | 0% |
| **F** | Separate proposal: findings.jsonl unified substrate | Independent |

## Revisions

- **2026-04-07 v2:** Added empirical usage data (543 invocations). Resolved open questions per user feedback: no backward compat, keep model-guide/llmx-guide invocable, no named pipelines. Added unified findings.jsonl proposal.
- **2026-04-07 v3:** Integrated cross-model review (Gemini arch + GPT-5.4 formal). Decoupled findings.jsonl. Revised count to ~18. Added phased implementation order starting with long-tail archive. Mode telemetry as prerequisite.
- **2026-04-07 v4:** Integrated Engine+Lens architecture from brainstorm. 6 engines (gemini-analysis, cross-model-dispatch, codex-parallel, local-analysis, loop-ticker, mcp-orchestrator) shared across workflows. Lenses are prompt files — new perspectives added without code changes. Empirically validated: extract_transcript.py already shared by 4 skills.

<!-- knowledge-index
generated: 2026-04-08T06:21:31Z
hash: 2444f501e61c


end-knowledge-index -->
