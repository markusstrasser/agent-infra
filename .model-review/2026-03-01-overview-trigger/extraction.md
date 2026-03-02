# Extraction: Overview Trigger Reviews

## Extraction: gemini-output.md

G1. LOC is a broken proxy for architectural significance — 1-line schema change needs update, 500-line formatting pass doesn't
G2. repomix (2-5s) isn't expensive since SessionEnd is async — premature optimization to avoid it
G3. Treating all 3 overviews as monolithic block is wrong — changes to workflows shouldn't trigger source arch update
G4. Proposal violates "measure before enforcing" — magic numbers (50 lines, 7 days) deployed without data
G5. Semantic diffing via cheap LLM router — pipe git diff to Flash ($0.001) for Y/N before expensive Pro generation
G6. Path-based scoping — git diff --name-only to route triggers to specific overview types
G7. AST/structural diffing (difftastic, ctags) detects function/signature changes, ignores comments/formatting
G8. Shadow deployment — log trigger decisions without generating, tune heuristic against real data for 3 days
G9. repomix hash (Option 3) is "most sensitive" not "most precise" — typo in docstring changes hash
G10. Drop time decay entirely — if project untouched, architecture unchanged, burning tokens for nothing
G11. Flash sycophancy risk — may answer Y too often, degrading router into guaranteed trigger
G12. Background process lifecycle concern — nohup may not survive if Claude Code kills process group on SessionEnd

## Extraction: gpt-output.md

P1. LOC is not a monotone proxy for ΔArchitecture — renames, config changes, feature flags are low-LOC high-impact
P2. False positives: reformatting, vendored code, generated code, comment sweeps are high-LOC low-impact
P3. repomix hash precision claim assumes deterministic serialization + semantic normalization
P4. Commit count measures developer batching, not codebase drift
P5. All options implicitly assume 1 trigger = all 3 overviews — major unstated cost driver
P6. Option 5 (dirty flag) degenerates to always-regenerate or misses everything — not coherent
P7. Quantitative cost-benefit: Option 6 (hybrid) wins at $0.197/wk, Option 4 at $0.226/wk
P8. Measurement logging + 2-week threshold sweep before deploying — plot FPR/FNR vs threshold
P9. Composite structural-change trigger: files_added + files_deleted + renames >= 1 OR dependency file touched OR LOC > T
P10. Per-overview-type triggering cuts cost 2-3x (avg calls/regen drops from 3 to ~1-2)
P11. Cheap preview gate: skip regen for test/docs/formatting-only diffs
P12. Time decay should run from cron/scheduler, not SessionEnd — guarantees 7-day cap for quiet projects (genomics)
P13. Sensitivity analysis: if staleness penalty > $0.30/event, higher-trigger mechanisms overtake hybrid
P14. Testable predictions with logged metrics: repo, timestamp, head_sha, diff_lines, diff_files, diff_renames, trigger_fired, overview_md_diff_bytes
P15. Constitutional gap: "measure before enforcing" at only 40% coverage without experiment plan

## Disposition Table

| ID | Claim (short) | Disposition | Reason |
|----|--------------|-------------|--------|
| G1, P1, P2 | LOC is bad proxy for arch significance | INCLUDE | Both models, obviously correct |
| G2 | repomix check isn't expensive (async) | INCLUDE | Verified — SessionEnd is async |
| G3, P5, P10 | Per-overview-type triggering needed | INCLUDE — Tier 1 | Both models, strongest agreement |
| G4, P8, P15 | Measure before deploying thresholds | INCLUDE — Tier 1 | Constitutional alignment, both models |
| G5 | LLM router (Flash as semantic judge) | DEFER | Flash sycophancy risk (G11), adds LLM dependency to trigger. Evaluate after logging phase |
| G6 | Path-based scoping (--name-only routing) | INCLUDE — Tier 1 | Deterministic, zero-cost, enables per-overview triggering |
| G7 | AST/structural diffing (difftastic) | DEFER | Interesting but adds tool dependency. Evaluate if LOC+structural signals insufficient |
| G8 | Shadow mode first (log, don't generate) | INCLUDE — Tier 1 | Best path to constitutional compliance |
| G9 | repomix hash = sensitive not precise | INCLUDE | Correct — eliminates Option 3 |
| G10 | Drop time decay entirely | REJECT | GPT's point (P12) is stronger: bursty projects like genomics need it. But execution via cron, not SessionEnd |
| G11 | Flash sycophancy risk in router | INCLUDE | Valid concern, supports deferring G5 |
| G12 | nohup process lifecycle concern | INCLUDE | Needs testing — real risk |
| P3 | repomix hash needs deterministic serialization | INCLUDE | Reinforces G9 — Option 3 eliminated |
| P4 | Commit count = developer batching | INCLUDE | Eliminates Option 1 |
| P6 | Dirty flag degenerates | INCLUDE | Eliminates Option 5 |
| P7 | Quantitative ranking: hybrid > LOC > any-change | INCLUDE — caveat | Synthetic inputs, but framework is sound |
| P9 | Composite trigger: structural signals + LOC | INCLUDE — Tier 1 | Fixes the core LOC gap (renames, file adds) |
| P11 | Preview gate: skip test/docs/formatting | INCLUDE — Tier 2 | Low-cost, high-impact FP reduction |
| P12 | Time decay via cron, not SessionEnd | INCLUDE | Solves genomics bursty-quiet pattern |
| P13 | Sensitivity analysis on staleness penalty | INCLUDE | Useful for threshold tuning |
| P14 | Testable predictions with logged metrics | INCLUDE — Tier 1 | The actual implementation spec for measurement |

Coverage: 22 items extracted (12 Gemini, 10 GPT after dedup). 17 INCLUDE, 2 DEFER, 1 REJECT, 2 MERGE.
