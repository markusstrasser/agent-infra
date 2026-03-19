---
name: skill-authoring
description: Create, design, and validate Agent Skills for Claude Code. Use when the user wants to create a new skill, improve an existing skill, or learn about skill authoring best practices. Helps with SKILL.md structure, frontmatter validation, progressive disclosure, and testing strategies.
---

# Skill Authoring

## Core Principle

**The context window is a public good.** Skills share context with conversation, system prompt, and other skills. Every line must justify its token cost. Only add context Claude doesn't already have — generic instructions the model already knows are low-value (Agent-Diff: +3.4 for known APIs vs +19 for novel).

## Before Writing: Scope Check

Before writing a skill >50 lines, confirm scope with the user. One question saves a full rewrite:
- **Tools vs domain?** "Should this cover the APIs/tools, or the domain-specific workflows?"
- **Who's the audience?** All projects (global skill) or one project (local skill)?
- **What's excluded?** Knowing what NOT to cover prevents bloat.

Don't write 280 lines then discover the user wanted a different angle.

## File Structure

```
my-skill/
├── SKILL.md          # Required: instructions + frontmatter
├── references/       # Optional: loaded on demand (L3)
├── scripts/          # Optional: executed, not loaded into context
└── assets/           # Optional: templates, resources for output
```

Keep SKILL.md under 500 lines. No README, CHANGELOG, or auxiliary docs — the skill is for the agent, not humans.

## Frontmatter Reference

```yaml
---
name: my-skill                        # lowercase, hyphens, max 64 chars
description: What + When + triggers   # max 1024 chars, CRITICAL for discovery
argument-hint: '[issue-number]'       # autocomplete hint
user-invocable: true                  # false = hide from /menu (background knowledge only)
disable-model-invocation: true        # true = manual /name only (for side-effect workflows)
allowed-tools: Read, Grep, Glob       # tool whitelist (convenience, not security boundary)
model: claude-opus-4-6                # per-skill model override
context: fork                         # run in isolated subagent
agent: Explore                        # subagent type (Explore, Plan, general-purpose, or custom)
hooks:                                # skill-scoped hooks
  PostToolUse:
    - matcher: "Write|Edit"
      hooks:
        - type: command
          command: "~/scripts/check.sh"
---
```

All fields optional. Only `description` is strongly recommended.

### Invocation Control

| Config | You invoke | Claude invokes | Use case |
|--------|-----------|----------------|----------|
| (default) | Yes | Yes | Reference + task hybrid |
| `disable-model-invocation: true` | Yes | No | Side-effect workflows (deploy, send) |
| `user-invocable: false` | No | Yes | Background knowledge |

### String Substitutions

| Variable | Description |
|----------|-------------|
| `$ARGUMENTS` | All args passed to skill |
| `$ARGUMENTS[N]` or `$N` | Nth argument (0-based) |
| `${CLAUDE_SESSION_ID}` | Current session ID |

### Shell Preprocessing

`` !`command` `` runs before Claude sees the content. Output replaces the placeholder.

```yaml
## Context
- Diff: !`gh pr diff`
- Files: !`gh pr diff --name-only`
```

### Extended Thinking

Include "ultrathink" anywhere in skill content to enable extended thinking.

## Writing Descriptions

**Formula**: `[What it does] + [Key capabilities] + "Use when" + [Trigger scenarios/keywords]`

```yaml
# Bad — too vague, no triggers:
description: Helps with documents

# Good — specific domain, trigger words, exclusions:
description: Bio/medical/scientific evidence hierarchy and anti-hallucination rules.
  Use when conducting claim-heavy medical research, genomics interpretation.
  NOT for casual health questions, software engineering, or physics.
```

**Budget:** Skill descriptions consume ~2% of context window (env var `SLASH_COMMAND_TOOL_CHAR_BUDGET`, fallback 16K chars). Too many skills = descriptions get truncated.

## Per-Step Constraint Design

Don't set one freedom level per skill — set it per step. Different steps need different constraint strength.

| Type | Purpose | When to use |
|------|---------|-------------|
| **Procedural** (HOW) | Sequential steps, divergence OK | Research, exploration, setup |
| **Criteria** (WHAT) | Quality standards, judgment axes | Evaluation, scoring, selection |
| **Template** (shape) | Fixed output structure | Reports, tables, formatted output |
| **Guardrail** (NEVER) | Boundary by prohibition | Safety, confidentiality, anti-patterns |

Annotate phases with their type for self-documentation:

```markdown
## Phase 1 — Research <- Procedural
Search broadly across 3+ sources...

## Phase 2 — Evaluate <- Criteria
Score each option on: cost, integration ease, learning curve.
Recommend the highest overall scorer.

## Phase 3 — Report <- Template
| # | Option | Cost | Integration | Learning | Score |
...

## Guardrails
- Never present unverified numbers without marking as estimates
- Never include confidential information
```

**Escalation design:** Add to constrained steps: "If these constraints don't fit the situation, propose alternatives with reasoning."

## Progressive Disclosure

Three loading stages:

1. **L1 — Metadata** (~100 tokens) — description always in context for routing
2. **L2 — SKILL.md body** (<5K tokens ideal, 500 lines max) — loaded when skill triggers
3. **L3 — Reference files** (`references/`) — loaded only when Claude reads them on demand

### L3 Extraction Decision Rubric

When a SKILL.md exceeds ~400 lines, extract low-frequency content to `references/`. Use **decision-criticality** to decide what stays in L2 vs moves to L3:

| Invocation use | Decision-critical? | Action |
|----------------|-------------------|--------|
| >50% of invocations | Yes | **Stays in L2** — needed before first tool call |
| >50% of invocations | No | Stays in L2 but candidate for compression |
| <20% of invocations | Yes | Stays in L2 as compact summary, full detail in L3 |
| <20% of invocations | No | **Move to L3** — reference file with pointer |

**The chicken-and-egg problem:** Some content (tool routing, API selection) is needed BEFORE the first tool call. If you extract it entirely to L3, the agent must read the reference file before doing anything -- adding a tool call and context load to every invocation. Keep a compact routing summary (5-15 lines) in L2 with a pointer to the full reference.

**Production examples:**
- `researcher/` -- 44-row tool table + Exa search philosophy extracted to `references/tool-routing.md` and `references/search-philosophy.md`. 15-line routing summary stays in L2. Result: 37K -> 19K (49% reduction).
- `model-guide/` -- `PROMPTING_*.md`, `BENCHMARKS.md`, `CHANGELOG.md` moved to `references/`. Quick selection matrix stays in L2.

### Reference File Pointers

Use `${CLAUDE_SKILL_DIR}` for explicit paths or bare relative paths:

```markdown
For detailed tool descriptions, read `${CLAUDE_SKILL_DIR}/references/tool-routing.md`.
For prompting specifics, read `references/PROMPTING_CLAUDE.md`.
```

Organize references by domain, not by file type:

```
references/
├── tool-routing.md
├── search-philosophy.md
└── benchmarks.md
```

For files >100 lines, include a table of contents so Claude can see scope before reading.

## Subagent Execution

`context: fork` runs the skill in an isolated subagent. The skill content becomes the subagent's task -- it won't see conversation history.

```yaml
---
name: deep-research
context: fork
agent: Explore
---
Research $ARGUMENTS thoroughly:
1. Find relevant files
2. Analyze
3. Summarize with file references
```

Only works for skills with explicit tasks. Guidelines-only skills (no actionable prompt) return nothing in forked context.

## Validation Checklist

- [ ] Valid YAML frontmatter (spaces not tabs, special chars quoted)
- [ ] `name`: lowercase, hyphens, max 64 chars
- [ ] `description`: includes WHAT, WHEN, and trigger words
- [ ] Instructions use per-step constraint design
- [ ] Dependencies explicitly documented
- [ ] Examples show realistic usage
- [ ] SKILL.md under 500 lines
- [ ] Supporting files referenced from SKILL.md with clear "when to read" guidance
- [ ] No auxiliary files (README, CHANGELOG, etc.)
- [ ] Tested: skill activates for matching queries
- [ ] Tested: skill doesn't conflict with existing skills

## Anti-Patterns

- **Generic instructions** — telling Claude what it already knows. Low value per Agent-Diff.
- **One freedom level** — applying same constraint to all steps. Use per-step typing.
- **Volume without quality** — "keep to 5 pages" specifies volume, not standards.
- **Selection without criteria** — "pick the best one" without axes to evaluate on.
- **Auxiliary file bloat** — README, CHANGELOG, docs about the skill. The agent doesn't need meta-docs.
- **All-in-SKILL.md** — dumping 1000 lines into the main file instead of using references/.
- **Background knowledge as task** — `user-invocable: false` skill with no actionable content.
- **Full extraction of decision-critical content** — moving tool routing entirely to L3 when it's needed before the first tool call. Keep a compact summary in L2.
