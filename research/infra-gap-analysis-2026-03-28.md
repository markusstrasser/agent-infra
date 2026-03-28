# Infrastructure Gap Analysis: Detection Coverage vs Error Classes

**Date:** 2026-03-28
**Method:** Cross-repo git log analysis (meta, genomics, skills) + session-analyst retros + manual retros, 2026-03-15 to 2026-03-28
**Scope:** 44 genomics fix commits, 158 improvement-log findings, 2529 daily hook triggers

## Core Finding: Two Separate Error Universes

The system has two completely disjoint error classes with separate detection mechanisms and zero overlap:

### Universe A: Behavioral anti-patterns (meta detects)
- **What:** Token waste, wrong-tool, scope creep, build-then-undo, repeated reads, poll loops
- **Detected by:** Session-analyst (transcript analysis), hooks (real-time enforcement)
- **Volume:** 158 findings, 2529 daily hook triggers across 10 hooks
- **Enforcement:** 10 hooks deployed (spinning, dup-read, search-burst, subagent-gate, source-check, etc.)
- **Genomics fixes caught:** 0

### Universe B: Data/pipeline errors (meta does NOT detect)
- **What:** Wrong coordinates, bad math, stale data, missing outputs, wrong alleles, incorrect calibration
- **Detected by:** Cross-model review, bio-verify batch sweeps, manual execution, QA tools
- **Volume:** 44 fix commits in March 2026
- **Enforcement:** 0 hooks (until 2026-03-28 session deployed canary gate + bio-verify + snapshot + retraction + PRS sanity + forward-strand)
- **Meta detection:** Zero. Session-analyst cannot see data correctness errors in transcripts.

### Detection Source Attribution (last 5 days, 44 fixes)

| Detector | Fixes | % | Cost | Notes |
|----------|-------|---|------|-------|
| GPT-5.4 Pro review (R5) | 11 | 25% | $6.54 | Single review session. All conceptual/mathematical |
| Bio-verify batch sweep | ~51 individual errors | 39% | $0 (API calls) | Manual trigger. 11-21% error rate per batch |
| Human/execution | 8 | 18% | — | Found during pipeline runs |
| QA hooks (ruff, pyright) | 3 | 7% | $0 | Newly deployed (Mar 25) |
| Codex dispatch audit | 2 | 5% | ~$3 | GPT-5.4 for substantial audit |
| Session-analyst | 0 | 0% | — | Detects behavior, not data |

## Detection→Fix Latency Staircase

Measured on 6 successful meta detection→enforcement loops:

| Phase | Median latency | Bottleneck |
|-------|---------------|------------|
| Detection → Rule (CLAUDE.md) | 1-3 days | Steward automates this well |
| Rule → Advisory hook | 5-10 days | Requires evidence of rule failure |
| Advisory → Blocking hook | 10-18 days | Requires 3+ recurrences + hook-roi data |

**Worst case:** Dup-read pattern. Detected Mar 10, advisory Mar 26, block Mar 28 = **18 days**, 8-10 recurrences in between.

**No automation for rule→hook promotion.** The steward processes findings but doesn't auto-escalate based on hook-roi trigger data or recurrence counts.

## Proposed Finding Accumulation

27 findings are `[ ] proposed` and 10+ days old. Breakdown by age:

| Age | Count | Examples |
|-----|-------|---------|
| 25 days (Mar 3) | 6 | Hook bypass via Python, sycophancy, destructive archival |
| 21 days (Mar 7) | 4 | Misrepresent purpose, missing phase artifacts |
| 18 days (Mar 10) | 3 | os._exit side effects, ARC-AGI dead-end |
| 11 days (Mar 17) | 5 | generate_clinical_report 10x read, llmx polling |
| 4-5 days (Mar 23-24) | 4 | Various |

The constitution says "2+ recurrences → promote" but no automated check enforces this. The steward processes individual findings but doesn't batch-triage the backlog.

## What Changed This Session (2026-03-28)

Deployed 6 hooks bridging Universe A (behavioral) to Universe B (data correctness):

| Hook | Type | Catches |
|------|------|---------|
| Canary gate in Claude precommit | Blocking | Classification regressions (70 canaries, 28 branches) |
| Bio-verify on registry edits | Advisory | Variant registry errors (21.7% baseline rate) |
| Snapshot regression in precommit | Advisory | Output regressions (MosaicForecast, gene counts, etc.) |
| Retraction gate in precommit | Advisory | Stale PRS data, retracted findings |
| PRS sanity in precommit | Advisory | Numerical drift in PRS outputs |
| Forward-strand allele check | Advisory | Wrong-strand effect alleles (samtools faidx vs hg38.fa) |

**Projected impact:** Catch rate 11% → ~65% of fix-class commits.

**Remaining gap (23%):** Domain/conceptual errors (incoherent Bayes, wrong concordance calibration, excluded FDR families). Only cross-model review catches these. GPT-5.4 Pro R5 found 11 such errors for $6.54 — highest ROI detector in the system.

## Additional Findings (Gemini Flash CAG on 2.4K line cross-repo context)

### "Warn" state is the biggest enforcement gap
Hook-roi: 1249 spinning warns/day + 414 dup-read warns/day. The agent is habituated to advisory text — treats it as background noise. Gemini: "Move all warn hooks with >100 triggers/day to block or delete. The warn state is currently the biggest break in the enforcement loop."

Promoted dup-read to block this session (ad950c4). Spinning (1249/day) is the next candidate but needs false-positive analysis first — some legitimate long operations trigger it.

### Fix not applied to all execution lanes
Turn-budget rule was applied to `Agent()` dispatch prompts but NOT to direct `codex exec` calls. Codex agents exhausted turns 3 days after the "fix" (genomics 631c8a46, Mar 24). The loop failed because the fix was instruction-only and didn't reach all entry points.

Pattern: when a fix targets one tool pathway, grep for other pathways that do the same thing. `codex exec`, `llmx`, `Agent()`, and direct Bash all need the same constraints applied.

### Ruff --fix as destructive force
Genomics `6d9c8b38`: ruff `--fix` hook silently deleted newly added but unreferenced functions. A "quality hook" acting destructively. Meta's detection didn't flag this — session-analyst sees token waste but not "hook deleted your code."

The ruff hook was later changed to report-only (genomics `470c61d`). But the pattern is worth watching: auto-fix hooks can be destructive in ways that look like quality.

### The system is converging on "CI/CD for scientific claims"
Gemini's meta-observation: the system is shifting from behavioral rules ("tell the agent to be careful") to state enforcement ("the agent cannot commit if coordinates don't match hg38.fa"). The Skills repo is transitioning from an instruction library to a scientific verification pipeline.

## Recommendations

1. **Schedule periodic cross-model review** for genomics classification logic. The $6.54 R5 session found more bugs than all of meta's infrastructure combined.
2. **Add auto-escalation to steward**: when a finding hits 3+ recurrences AND hook-roi shows the advisory isn't sticking, auto-promote to blocking.
3. **Batch-triage the proposed backlog**: 27 findings need status updates. Many are covered by rules deployed since Mar 7 but never marked as such.
4. **Bio-verify on every variant registry commit** (deployed today). Monitor the 21.7% → ? error rate trend over next 2 weeks.
5. **Audit warn hooks with >100 triggers/day** — spinning (1249/day) needs false-positive analysis. If <20% false positive, promote to block.
6. **Apply fixes to all execution lanes** — when adding a constraint, grep for all tools that do the same thing (Agent, codex exec, llmx, Bash). Don't fix one pathway and leave others open.

## Revisions

None yet.

<!-- knowledge-index
generated: 2026-03-28T15:59:23Z
hash: 04ae68bd3bf3


end-knowledge-index -->
