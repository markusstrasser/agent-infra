# CONTEXT: Cross-Model Review — Optimal Trigger for Codebase Overview Regeneration

# PROJECT CONSTITUTION (abridged for focus)
- Generative principle: Maximize rate agents become more autonomous, measured by declining supervision.
- Architecture over instructions: if it matters, enforce with hooks/tests/scaffolding.
- Measure before enforcing: log triggers, measure false positives.
- Fail open, carve out exceptions. Hooks fail open by default.
- Recurring patterns (10+) become architecture.

# PROJECT GOALS (abridged)
- Primary metric: ratio of autonomous-to-supervised work across sub-projects.
- Quality standard: recurring patterns (10+ uses) must become architecture.
- Orchestrator: unblocked. Build for clearly automatable tasks.
- Skills ownership: meta owns skill quality and cross-project propagation.

# SYSTEM DESCRIPTION

## What
AI-generated architectural overviews of codebases. Pipeline: repomix (code extraction) → prompt template → Gemini → markdown summary. Currently 3 overview types per project (source architecture, project structure, dev tooling).

## Why
Provides agents and humans with up-to-date architectural understanding without manual documentation maintenance. Overviews are gitignored (not committed), regenerated when codebase changes.

## Current trigger: git pre-push hook
- Works for evo (solo dev, 1-5 pushes/day)
- Doesn't generalize: some projects rarely push, some never push
- All projects use main-only workflow (no branches)

## Cost structure
- Check cost: git operations = instant (~0ms)
- repomix extraction: ~2-5 seconds
- Gemini Flash generation: ~10-20s, ~$0.001-0.01/call
- Gemini Pro generation: ~30-60s, ~$0.01-0.05/call
- 3 overviews per project × ~5 projects = 15 generations per trigger

## Change patterns across projects
- intel: frequent code changes, new datasets, analysis scripts. Heavy commit volume.
- selve: moderate changes, personal knowledge base.
- genomics: burst activity (pipeline development), then quiet.
- evo: steady feature development, architectural stability.
- meta: config/hook/rule changes, mostly small files.

# THE DECISION

## 6 Candidates (ranked by proposer)

1. **Commit count threshold** — `git rev-list --count`. Simple but semantic-blind.
2. **git diff against target dirs** — scoped but fires on trivial changes.
3. **Content hash of repomix output** — most precise but adds repomix invocation cost.
4. **Lines-changed threshold** — `git diff --shortstat`, threshold of 50 lines. Proposer's lean.
5. **Post-commit dirty flag + SessionEnd** — always dirty, complexity without precision.
6. **Hybrid: lines threshold + time decay** — `(lines > 30) OR (days > 7 AND lines > 0)`.

## Proposer's lean: Option 4 + time decay from Option 6
50-line threshold in target directories, with 7-day time decay safety net.

## Open questions
1. Fundamentally better trigger mechanism?
2. Lines-changed vs file-count vs function-count vs AST diff?
3. Should trigger know WHAT changed (structural vs tests)?
4. Preview step before expensive generation?
5. Per-overview-type triggers vs single trigger for all?

# CONSTRAINTS
- Trigger check runs in SessionEnd hook (async, non-blocking, cannot block session exit)
- Must work across projects with different change patterns
- Must be implementable as a bash hook (~50 lines)
- False negative cost: agent works with stale overview (suboptimal but not catastrophic)
- False positive cost: wasted Gemini API cost + generation time (annoying but not catastrophic)
- Goal: minimize both, with slight preference for fewer false negatives (staleness is worse than waste)
