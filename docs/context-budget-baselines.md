# Context Budget — Measured Baselines

Relocated verbatim from `.claude/rules/context-budget-principles.md` §8 on 2026-10-13 (/doctor: dated
snapshots do not need to load every session). Append new measurements here.


2026-07-13 (global-layer re-slim after 6 months of accretion — the global non-scoped set had
crept 23.6K→~68K chars: CLAUDE.md 40.3K, wakeup-cadence 19.4K. Cut CLAUDE.md 40.3K→31.4K
(narratives → decision/memo anchors), wakeup-cadence 19.4K→9.2K, folded
context-budget-orchestration.md into subagent_usage, relocated remote-ssh-ops.md to
genomics+hutter, compressed eval-token-costs. Global non-scoped set 68K→49.4K chars.
Per-repo canary drop: agent-infra 40.3K→34.4K tok · intel 38.7K→32.9K · genomics 37.5K→31.9K ·
phenome 36.2K→30.3K. All 4 still slightly OVER the 30K ceiling — the residual is project
CLAUDE.md (human-owned constitution) + project rules, not the global layer.):

| Component (agent-infra session) | Chars | ≈Tokens |
|---|---|---|
| Global CLAUDE.md + non-scoped global rules | 49.4K | 12.4K |
| Project CLAUDE.md + non-scoped project rules | ~37K | ~9.4K |
| MEMORY.md index | 5.6K | 1.4K |
| **Total always-loaded** | **~92K** | **~34.4K** |

2026-06-13 (post context-rot slim — global CLAUDE.md 8.1K→3.9K tok, vetoed-decisions
11.8K→4.4K chars, MEMORY.md 10.3K→5.6K chars, 3 rules path-scoped, 1 deleted):

| Component (agent-infra session) | Chars | ≈Tokens |
|---|---|---|
| Global CLAUDE.md + non-scoped global rules | 23.6K | 5.9K |
| Project CLAUDE.md + non-scoped project rules | 37.4K | 9.4K |
| MEMORY.md index | 5.6K | 1.4K |
| **Total always-loaded** | **66.6K** | **~16.7K** |

Measure: sum `wc -c` over CLAUDE.md + rules without `paths:` frontmatter + MEMORY.md.
Every subagent spawn pays this too — budget new always-loaded content against it.
Historical (2026-04-05): Agent-Infra 18.7K / Selve 21K / Genomics 32.9K tokens always-loaded.
