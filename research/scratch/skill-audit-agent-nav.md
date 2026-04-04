# Skill Audit: Agent Navigation Research

**Date:** 2026-04-04
**Scope:** 47 active skills in ~/Projects/skills/
**Evidence base:** Cao et al. (retrieval paradox), Gloaguen et al. (AGENTS.md distraction), ByteRover (flat files), Du et al. (context rot), Girolli 2026 (scaffolding)

## Summary

| Rating | Count | Skills |
|--------|-------|--------|
| RED | 4 | knowledge-compile (partially self-corrected), agent-pliability, project-upgrade, model-review |
| YELLOW | 12 | See below |
| OK | 31 | See below |

**Key finding:** The skill set is largely well-designed for agent consumption. The biggest risk is not individual skills producing bad artifacts, but the *aggregate context load* -- 47 skills averaging ~220 lines each means ~10K lines of potential context inflation. The research evidence says shorter, targeted context wins. Several skills are 2-5x longer than they need to be for the instruction content they deliver.

---

## RED — Produces artifacts or patterns that evidence says hurt agents

### 1. knowledge-compile (186 lines)

**What it does:** Synthesizes multiple research memos into unified articles with provenance.

**The good:** The skill *already knows this is a problem*. It explicitly states: "This is a human UX tool, not an agent navigation tool" and cites both Cao et al. and Gloaguen et al. It warns against building a "systematic wiki layer."

**The problem:** Despite the warnings, the skill still produces synthesized overview articles that live alongside the source memos. If agents encounter these compiled articles during grep/search, they become exactly the "pre-computed retrieval" that Cao et al. shows hurts by 40.5%. The compiled articles are longer than the source memos, adding context burden. The "When NOT to Use" section is only advisory -- nothing enforces that agents don't consume the output.

**Recommendation:**
- Add a naming convention that signals "human-only" (e.g., `_compiled-` prefix or a `human-reading/` subdirectory) so agents can skip these files during navigation
- Consider adding these to a `.claudeignore` or equivalent so agent search tools don't index them
- The self-awareness is good -- the risk is downstream consumption, not the skill's own behavior

**Research alignment:** Directly validated by Cao et al. (retrieval paradox) and Gloaguen et al. (synthesized context hurts). The skill partially self-corrects but the artifacts remain in the search path.

### 2. agent-pliability (214 lines)

**What it does:** Splits monolithic docs, renames files for discoverability, builds research/docs indexes in CLAUDE.md.

**The problem:** Phase 3c proposes adding a "Research & Docs Index" table to CLAUDE.md with a "Consult before" column. This is exactly the AGENTS.md distraction pattern from Gloaguen et al. -- LLM-generated context that tells the agent "read these files before acting." The research shows this inflates trajectory by ~4 steps and increases cost by >20%. Agents navigate better with descriptive file names alone (which the skill correctly identifies as the core mechanism) than with routing indexes that try to pre-decide what's relevant.

**The good parts:** File renaming for discoverability (Phase 2b) is directly validated by ByteRover -- descriptive file naming is the highest-ROI intervention. Monolith splitting (Phase 2a) is also sound.

**Recommendation:**
- Keep Phase 2a (splitting) and 2b (renaming) -- these are validated
- Drop or dramatically shrink Phase 2c/Phase 3 indexing. A thin `ls`-readable directory structure with good names IS the index. Adding a CLAUDE.md routing table is the AGENTS.md distraction effect
- If an index is needed at all, make it a minimal directory listing, not a "consult before" routing table

**Research alignment:** Gloaguen et al. shows broad context files reduce success by 0.5-3%. ByteRover validates descriptive naming as the right approach. The skill's core insight (file names are the cheapest index) is correct, but the execution adds an index layer that contradicts it.

### 3. project-upgrade (978 lines)

**What it does:** Feeds entire codebase to Gemini 3.1 Pro, gets findings, triages, executes fixes.

**The problem:** At 978 lines, this is by far the longest skill. When loaded into agent context, it consumes substantial tokens. Du et al. shows precision degrades 13.9-85% with context length. Most of the 978 lines are operational details (prompt templates, bash scripts, triage procedures) that could be in reference files loaded on demand rather than in the SKILL.md itself. The skill is also a case study in "prompt-based governance" (Girolli 2026) -- it encodes complex multi-phase procedures as prose instructions rather than as deterministic scripts.

**Recommendation:**
- Split into a slim SKILL.md (~100-150 lines: when to use, phases overview, key gotchas) and reference files (prompt templates, triage procedures, verification scripts)
- Move the extensive prompt templates and bash scripts into `references/` subdirectory files that are read on demand
- The skill's *function* is fine -- it's the *packaging as a 978-line context-loaded document* that's the problem

### 4. model-review (687 lines)

**What it does:** Cross-model adversarial review dispatching to Gemini and GPT.

**The problem:** Same context inflation issue as project-upgrade. 687 lines loaded into context when the skill is invoked. Contains extensive prompt templates, dispatch scripts, CLI flag documentation, and operational procedures. The "context assembly" step (Step 2) also produces synthesized context files for review models -- an indirection layer that adds tokens.

**Recommendation:**
- Split into slim SKILL.md (~150 lines) + reference files for prompt templates, CLI patterns, model-specific gotchas
- The context assembly step is necessary for cross-model dispatch but should be as lean as possible -- summarize rather than concatenate, which the skill already advises

---

## YELLOW — Minor concerns, specific notes

### 5. modal (949 lines)

**Concern:** Second-longest skill. However, it's pure API reference (migration guide, code patterns, GPU configs). Not an agent workflow instruction -- it's a lookup table.

**Mitigating factor:** Low `effort: low` tag means it's loaded only when triggered. The content is factual reference, not governance/scaffolding prose, so Girolli's "bad scaffolding" finding doesn't apply.

**Recommendation:** Consider splitting the migration guide and advanced patterns into `references/` files. The core SKILL.md should be ~200 lines covering critical API changes and the decision tree.

### 6. llmx-guide (437 lines)

**Concern:** Long for a reference skill. Contains detailed provider-specific gotchas, transport routing, and debugging procedures.

**Mitigating factor:** Factual reference, loaded on demand. Not governance prose.

**Recommendation:** Could be trimmed to ~150 lines of critical gotchas with the rest in reference files.

### 7. novel-expansion (420 lines)

**Concern:** Long skill with multi-phase pipeline. Encodes 8 failure mode gates as prose.

**Mitigating factor:** The failure modes table is earned from real incidents -- valuable reference. The skill is invoked rarely.

**Recommendation:** Move failure modes and prompt templates to reference files. Keep the phase overview and gates in SKILL.md at ~150 lines.

### 8. brainstorm (355 lines)

**Concern:** Contains full prompt templates for llmx dispatch, which inflate context when loaded.

**Recommendation:** Move prompt templates to reference files. The core skill (perturbation axes, denial cascades, pain-point gate) fits in ~150 lines.

### 9. dispatch-research (385 lines)

**Concern:** Long, with extensive Codex dispatch procedures, prompt templates, and known-issues sections.

**Recommendation:** Same pattern -- slim SKILL.md with reference files for prompt templates and operational details.

### 10. evolution-forensics (375 lines)

**Concern:** Complex multi-phase analytical skill with extensive output templates.

**Recommendation:** Move output templates and example formats to reference files.

### 11. data-acquisition (410 lines)

**Concern:** Long reference document. However, it's a decision tree + tool catalog -- genuinely useful as a lookup.

**Mitigating factor:** The decision tree at the top is exactly the "thin routing index" pattern that works. Content is factual, not governance.

**Recommendation:** Minor -- could split per-tool details into reference files, keeping the decision tree and fallback chain in the main SKILL.md.

### 12. design-review (291 lines)

**Concern:** Produces synthesized pattern files (patterns.jsonl, synthesis.md) that feed into propose-work.py. These intermediate artifacts could become distractions if agents encounter them during unrelated work.

**Recommendation:** Ensure synthesis artifacts go into a clearly-scoped directory that agents don't search during normal work. The artifacts/design-review/ path is reasonable but should be excluded from broad grep patterns.

### 13. bio-verify (259 lines)

**Concern:** Contains a large "Prior Audit Results" table (30+ rows) and "Known Issues" list (17 items) that are appended over time. This historical calibration data is useful but inflates context.

**Recommendation:** Move the audit results table and known issues to a separate reference file. The core verification workflow fits in ~120 lines.

### 14. session-analyst (283 lines)

**Concern:** Produces artifacts (improvement-log entries, session analysis) that accumulate over time. The improvement-log is append-only and grows indefinitely.

**Recommendation:** The append-only design is correct per the constitution. The concern is minor -- just monitor the size of improvement-log.md and archive older entries periodically.

### 15. competing-hypotheses (213 lines)

**Concern:** Long for a reasoning methodology skill. Contains worked examples and extensive phase descriptions.

**Recommendation:** Minor -- the ACH methodology benefits from being self-contained. Could trim ~30% by moving examples to reference files.

### 16. causal-dag (300 lines)

**Concern:** Long reasoning skill with extensive worked example and trap catalog.

**Recommendation:** Same as competing-hypotheses -- the worked example is genuinely instructive but could be a reference file.

---

## OK — No issues identified

These skills are well-designed for agent consumption. Common positive patterns:

**Short and targeted (good):**
- tick (32 lines) -- minimal, does one thing
- causal-robustness (60 lines) -- focused, references other skills
- source-grading (71 lines) -- taxonomy table, no artifacts
- investigate (87 lines) -- lightweight methodology
- retro (101 lines) -- produces findings but doesn't create retrieval layers
- goals (109 lines) -- questionnaire, updates one file
- verify-findings (111 lines) -- verification checklist, no synthesis layer
- de-slop (116 lines) -- inline analysis, no artifacts
- google-workspace (123 lines) -- CLI reference
- knowledge-diff (125 lines) -- extracts delta, no artifacts
- steward (135 lines) -- monitors and reacts, doesn't synthesize
- supervision-audit (139 lines) -- audit methodology, outputs fixes
- entity-management (139 lines) -- template-driven, one file per entity (flat)
- browse (140 lines) -- tool reference
- epistemics (144 lines) -- guardrails/hierarchy, not scaffolding
- maintain (164 lines) -- rotating maintenance, writes to MAINTAIN.md
- suggest-skill (171 lines) -- analysis tool, outputs candidates
- constitution (176 lines) -- questionnaire, produces one section
- negative-space-sweep (184 lines) -- divergent discovery, no artifacts
- causal-check (191 lines) -- reasoning methodology
- debug-mcp-servers (208 lines) -- troubleshooting guide
- trending-scout (230 lines) -- scan and report
- research-cycle (230 lines) -- loop driver, reads/writes CYCLE.md (single flat file)
- harvest (237 lines) -- consumes artifacts, produces ranked list (not synthesis)
- researcher (243 lines) -- produces research memos (flat files with good naming)
- claude-api (244 lines) -- API reference with reading guide
- model-guide (277 lines) -- model selection reference
- agent-pliability -- listed under RED for its indexing behavior, but renaming/splitting phases are OK

**Validated by research (doing the right thing):**
- **knowledge-compile** -- explicitly cites the retrieval paradox and warns against agent consumption (though artifacts remain in search path)
- **researcher** -- produces flat markdown memos with descriptive names, forces turn budget, avoids synthesis layers
- **entity-management** -- one flat file per entity, git-versioned, no index layer
- **agent-pliability** -- the core insight (file names = cheapest index) is directly validated by ByteRover
- **knowledge-diff** -- extracts delta only, no accumulation
- **tick** -- 32 lines, does one thing, exemplary minimalism
- **epistemics** -- guardrails not scaffolding; deterministic enforcement principle aligns with Girolli 2026

---

## Cross-Cutting Findings

### 1. Context inflation is the primary risk

The 47 skills total ~10,300 lines. While only the invoked skill is loaded, the *descriptions* of all skills appear in the system prompt (visible in the skill listing above). This is ~3,500 tokens of skill descriptions that are always present. Per Du et al., this degrades precision.

**Recommendation:** Audit the skill description strings. Many could be shorter. The description field should be a trigger condition ("when to invoke"), not a feature list.

### 2. The "prompt templates in SKILL.md" anti-pattern

Skills containing full llmx/codex prompt templates (model-review, brainstorm, dispatch-research, project-upgrade, novel-expansion) inflate the loaded context with content that's only used once during execution. These templates should be in reference files that are read on demand.

**Recommendation:** Establish a convention: SKILL.md contains workflow + decision logic. `references/` contains prompt templates, output formats, and historical data. This could save 40-60% of loaded context for the largest skills.

### 3. Synthesis artifacts in the search path

Multiple skills produce synthesized artifacts: knowledge-compile (compiled articles), design-review (synthesis.md), model-review (review output), session-analyst (improvement-log entries). When agents grep across the project, these synthesized documents appear alongside source files, creating the "pre-computed retrieval" that Cao et al. shows hurts performance.

**Recommendation:** Establish clear directory conventions so agents can distinguish source documents from synthesized artifacts. Consider `artifacts/` directories (already used by some skills) as the standard location, and train grep patterns to exclude them by default.

### 4. Several skills have earned self-correction

knowledge-compile, brainstorm (pain-point gate), and dispatch-research (template-first anti-pattern) all contain hard-won lessons that prevent known failure modes. These self-corrections are valuable and should be preserved even when skills are trimmed.

### 5. Flat files + descriptive naming is the validated pattern

The skills that best align with research are those producing flat markdown files with descriptive names: researcher (research memos), entity-management (one file per entity), knowledge-diff (delta extraction). This pattern should be reinforced as the standard.

---

## Priority Actions

1. **Split the top 5 longest skills** into slim SKILL.md + reference files: project-upgrade (978), modal (949), model-review (687), llmx-guide (437), novel-expansion (420). Estimated context savings: ~3,000 lines of loaded context.

2. **Remove or thin the CLAUDE.md index table** from agent-pliability. Keep file renaming and splitting; drop the routing index.

3. **Establish artifact isolation convention** -- synthesized outputs go to `artifacts/<skill>/` and are excluded from default agent search patterns.

4. **Add human-only naming convention** to knowledge-compile outputs so agents skip them during navigation.

5. **Trim skill description strings** in frontmatter -- trigger conditions only, not feature lists. Several descriptions exceed 200 characters when 80 would suffice.

<!-- knowledge-index
generated: 2026-04-04T17:54:45Z
hash: 3f7bfa656f1d


end-knowledge-index -->
