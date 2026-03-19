# Script Inventory (2026-03-19)

53 scripts in `scripts/`. Scanned: justfile, pipelines/*.json, CLAUDE.md, .claude/rules/*.md,
hooks, .mcp.json, launchd plists, Python cross-file imports, git log --since=30.days.

## Reference Counts

| Script | Refs | Git30 | Callers |
|--------|-----:|------:|---------|
| orchestrator.py | 41 | 24 | justfile(18), pipelines(3), CLAUDE.md(17), rules(3), launchd |
| dashboard.py | 17 | 10 | justfile(9), pipelines(3), CLAUDE.md(4), rules(1) |
| sessions.py | 14 | 4 | justfile(4), pipelines(2), CLAUDE.md(6), rules(2), hooks |
| runlog.py | 13 | 3 | justfile(3), pipelines(1), CLAUDE.md(7), rules(2) |
| config.py | 6 | 6 | pipelines(1), CLAUDE.md(2), rules(3), imported by 25+ scripts |
| calibration-canary.py | 6 | 3 | justfile(2), pipelines(2), CLAUDE.md(1), rules(1) |
| trace-faithfulness.py | 5 | 3 | justfile(2), pipelines(1), CLAUDE.md(1), rules(1) |
| autoresearch.py | 4 | 6 | CLAUDE.md(2), rules(2) |
| safe-lite-eval.py | 4 | 9 | justfile(1), pipelines(1), CLAUDE.md(1), rules(1) |
| pushback-index.py | 4 | 5 | justfile(1), pipelines(1), CLAUDE.md(1), rules(1) |
| doctor.py | 4 | 5 | justfile(2), CLAUDE.md(1), rules(1) |
| propose-work.py | 4 | 4 | CLAUDE.md(2), rules(2) |
| epistemic-lint.py | 4 | 4 | justfile(2), CLAUDE.md(1), rules(1) |
| code-review-scout.py | 4 | 4 | pipelines(2), CLAUDE.md(1), rules(1) |
| hook-roi.py | 4 | 1 | CLAUDE.md(3), rules(1), **launchd plist** |
| model-review.py | 4 | 1 | pipelines(2), rules(2) |
| compaction-nuance.py | 4 | 1 | justfile(2), pipelines(1), rules(1) |
| plan-status.py | 3 | 2 | justfile(3) |
| best-sync.py | 3 | 1 | pipelines(1), CLAUDE.md(1), rules(1) |
| fix-verify.py | 3 | 1 | pipelines(1), CLAUDE.md(2) |
| vendor-versions.py | 3 | 1 | pipelines(1), CLAUDE.md(1), rules(1) |
| agent_receipts.py | 2 | 2 | justfile(1), rules(1) |
| repo-outline.py | 2 | 2 | rules(2) |
| repo-summary.py | 2 | 2 | pipelines(1), rules(1) |
| subagent-analysis.py | 2 | 2 | pipelines(1), rules(1) |
| finding-triage.py | 2 | 3 | pipelines(1), CLAUDE.md(1) |
| extract_user_tags.py | 2 | 5 | justfile(1), rules(1) |
| repo_tools_mcp.py | 2 | 5 | CLAUDE.md(1), rules(1), .mcp.json, imports mcp_middleware |
| hook-outcome-correlator.py | 2 | 1 | CLAUDE.md(1), rules(1) |
| hook-telemetry-report.py | 2 | 1 | justfile(1), rules(1) |
| claims-reader.py | 2 | 1 | pipelines(1), rules(1) |
| code-review-schedule.py | 2 | 1 | CLAUDE.md(1), rules(1) |
| codebase-map.py | 2 | 1 | pipelines(1), rules(1) |
| fail_open.py | 2 | 1 | CLAUDE.md(2), imported by measurement scripts |
| session-shape.py | 2 | 1 | pipelines(1), CLAUDE.md(1) |
| skill-validator.py | 2 | 1 | justfile(1), pipelines(1), hooks |
| repo-imports.py | 1 | 2 | rules(1) |
| repo-changes.py | 1 | 2 | rules(1) |
| meta_infra_mcp.py | 1 | 2 | rules(1), imports mcp_middleware |
| prompt-archaeology.py | 1 | 2 | rules(1) |
| overview-trigger-analysis.py | 1 | 4 | rules(1) |
| compaction-canary.py | 1 | 1 | CLAUDE.md(1) |
| fold-detector.py | 1 | 1 | rules(1) |
| gen-skill-docs.py | 1 | 1 | justfile(1) |
| repo-deps.py | 1 | 1 | rules(1) |
| researcher-postmortem.py | 1 | 1 | pipelines(1) |
| session-features.py | 1 | 1 | CLAUDE.md(1) |
| supervision-kpi.py | 1 | 1 | CLAUDE.md(1) |
| thesis-challenge.py | 1 | 1 | CLAUDE.md(1) |
| tool-trajectory.py | 1 | 1 | CLAUDE.md(1) |
| mcp_middleware.py | 0 | 4 | **imported by** meta_mcp.py + repo_tools_mcp.py (missed by text search) |
| codex_dispatch.py | 0 | 1 | recently created, being wired |
| generate-indexes.py | 0 | 1 | run manually for index generation |
| overview-usage.py | 0 | 1 | run manually for overview analysis |

## Archive Candidates

Plan criteria: 0 callers AND 0 git activity in 30 days. **No scripts meet both criteria.**

Every 0-ref script has at least 1 commit in the last 30 days:
- `mcp_middleware.py`: actively imported by MCP servers (hidden dependency)
- `codex_dispatch.py`: just created, wiring in progress
- `generate-indexes.py`: touched recently, generates doc indexes
- `overview-usage.py`: touched recently, analyzes overview triggers

## Hook Merge Assessment

Plan proposed merging `hook-outcome-correlator.py` (219 lines) + `hook-roi.py` (179 lines)
→ `hook-telemetry-report.py` (132 lines). **Not recommended:**
- `hook-roi.py` is called by launchd plist `com.meta.hook-roi-daily.plist`
- Combined size is 530 lines, not "tiny" as plan assumed
- Each script has distinct purpose and callers
- Merge would require updating launchd plist + testing daily job

## Summary

- **Active count:** 53 (all scripts have either references or recent git activity)
- **No scripts archived** (none meet the 0-refs + 0-activity threshold)
- **No merges performed** (hook-roi.py has launchd dependency)
- **Net change:** 0 scripts removed

The plan's ≤45 target was based on assumptions about dead code that didn't hold.
The scripts directory is denser than expected — nearly everything is wired.
