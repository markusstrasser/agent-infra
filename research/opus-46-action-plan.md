## Opus 4.6 Prompt Structure — Action Plan

**Source:** `research/opus-46-prompt-structure.md`
**Date:** 2026-03-01

### What we learned

1. **Position bias doesn't apply** to thinking models (tournament-mcp empirical data)
2. **MUST/NEVER are fine** for guarding hard constraints (Anthropic uses them in their own production prompts)
3. **Anti-laziness prompts are harmful** — remove "be thorough", "think carefully", "if in doubt use X"
4. **XML section tags confirmed useful** — Anthropic uses them heavily in agentic prompts (7 XML sections in their research agent)
5. **Claude Code's prompt is 150+ granular fragments** — each 50-500 tokens, one concern per fragment
6. **System prompt = trusted employer** — don't justify rules, just be clear about what you want
7. **Context-save before compaction** is a recommended pattern we're not using
8. **Skill architecture: 3-level progressive disclosure** — metadata (always loaded) → body (on trigger) → resources (on demand)

### Actions

#### 1. Anti-laziness audit and removal
**Where:** All CLAUDE.md files, all skills
**What:** Find and remove any "be thorough", "think carefully", "do not be lazy", "if in doubt, use [tool]", "default to using [tool]" language.
**Status:** Audited. Our files are clean — no anti-laziness prompts found. The MUST/NEVER usage is exclusively for hard constraints (OOM crashes, human-protected sections, ethical lines). No action needed.

#### 2. Context-save before compaction
**Where:** Global `~/.claude/CLAUDE.md` or `.claude/rules/`
**What:** Add instruction for Claude to save progress state when approaching context limits, rather than relying solely on auto-compaction. Anthropic's recommended pattern:
```
As you approach your token budget limit, save your current progress and state
to a checkpoint file before the context window refreshes. Do not stop tasks
early due to context concerns.
```
**How:** Add to `~/.claude/CLAUDE.md` under `<context_management>` section. We already have `precompact-log.sh` (hook) and the `.claude/checkpoint.md` convention — this bridges the gap by prompting Claude to actively write state, not just log the compaction event.
**Risk:** Low — additive, reversible. Worst case: creates an unnecessary checkpoint file.

#### 3. Subagent steering
**Where:** `~/.claude/CLAUDE.md` or per-project CLAUDE.md
**What:** Opus 4.6 natively orchestrates subagents and can overuse them. Add guidance similar to Anthropic's own:
```
Use subagents when tasks can run in parallel, require isolated context, or
involve independent workstreams. For simple tasks, sequential operations,
single-file edits, or tasks needing shared context across steps, work
directly rather than delegating.
```
**How:** Add to global CLAUDE.md. The meta constitution already says "Subagent delegation for fan-out (>10 discrete operations)" — this makes the threshold explicit for ALL projects.
**Risk:** Low. Already partially covered. This sharpens the heuristic.

#### 4. Remove justifications from operational rules
**Where:** Intel CLAUDE.md, genomics CLAUDE.md
**What:** The soul document confirms Claude treats system prompt as trusted employer — it follows without justification. Some of our rules include explanatory justifications that consume tokens without changing behavior. Rules that guard observed failure modes should keep their evidence ("crashed the machine", "Brooklyn r=0.86→0.038"). Rules that are just preferences can drop the explanation.
**Example:** `**USE DUCKDB, NOT PANDAS.** 2.9GB parquet + 18GB RAM = OOM.` — keep the evidence, it explains the constraint. But `Always `uvx --with <packages> python3` — PEP 668 blocks pip install.` — the "PEP 668" explanation is for humans reading the file, not for Claude. Fine to keep for documentation value, but don't add new justifications thinking Claude needs them.
**How:** No immediate action. Apply this principle going forward when writing new rules.
**Risk:** None. Behavioral change in authoring, not file editing.

#### 5. XML tags — maintain current approach
**Where:** Already applied across repos
**What:** XML section tags are confirmed useful by Anthropic's own patterns. Our current application is correct:
- Intel: 7 sections (communication, hard_constraints, duckdb_reference, gotchas, reference, core_principles, constitution)
- Meta: 5 sections
- Genomics: 1 section (constitution)
- Researcher skill: 4 sections
- Selve: skipped (too short)

No further XML changes needed. The current granularity is appropriate — we're not splitting 50-token fragments like Claude Code does because our files are read as monoliths, not conditionally assembled.

#### 6. Skill architecture alignment
**Where:** `~/Projects/skills/`
**What:** Anthropic's skill-creator defines the canonical architecture:
- Metadata (name + description): ~100 words, always loaded, triggers skill activation
- Body (<500 lines): loaded when triggered
- Bundled resources: loaded on demand via file reads

Our skills already follow this pattern. One improvement: skill descriptions could be more "pushy" per Anthropic's guidance — "include both what the skill does AND specific contexts for when to use it" and "make the skill descriptions a little bit pushy" to combat undertriggering.
**How:** Review skill descriptions during next skill maintenance sweep. Not urgent.
**Risk:** Low. Over-pushy descriptions cause overtriggering, but that's self-correcting.

### Not doing

| Idea | Why not |
|------|---------|
| Reorganize file sections for position effects | No position bias in thinking models (tournament-mcp data) |
| Soften all MUST/NEVER language | Anthropic uses it in their own production prompts; our usage is for genuine hard constraints |
| Fragment CLAUDE.md files into 50-500 token pieces | Only useful for conditional assembly; our files are monoliths loaded in full |
| Read remaining Anthropic docs pages | Diminishing returns — migration guide and effort parameter docs are for API users, not Claude Code users |
| Add "ground quotes" technique | Already implemented as researcher skill Phase 6b (recitation strategy) |

### Monitoring

After implementing actions 2-3, check in 2 weeks via session-analyst:
- Does context-save before compaction actually produce useful checkpoint files?
- Does subagent steering reduce unnecessary subagent spawning?
- Any regressions from the changes?

If no measurable improvement after 30 days, revert per meta constitution rules of adjudication.

<!-- knowledge-index
generated: 2026-03-22T00:13:52Z
hash: b834e89bda20

cross_refs: research/opus-46-prompt-structure.md

end-knowledge-index -->
