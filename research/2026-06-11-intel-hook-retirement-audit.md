---
title: Intel Hook Retirement Audit — coverage-verified
date: 2026-06-11
status: active
tags: [hooks, cross-project, intel, dedup, metatooling]
---

# Intel Hook Retirement Audit (coverage-verified)

**Question:** intel's `.claude/settings.json` wires **70 local hook refs vs 3
shared** — it built a parallel hook system instead of consuming
`~/Projects/skills/hooks/`. Which of its ~69 local hooks are redundant with an
already-existing shared hook and can be retired (swap local → shared), vs which
must stay?

## Headline

Of a background agent's proposed **RETIRE-21**, only **6 are coverage-verified
safe**. The agent asserted "fully covered by shared hooks already wired
globally" for the whole list **without verifying shared existence** — the same
unverified-coverage error this audit exists to catch. Re-checked against a hard
`ls ~/Projects/skills/hooks/` + a grep of the **global** `~/.claude/settings.json`
wiring, the 21 redistribute as: **6 confirmed-retire, 4 retire-unverified
(behavior differs — diff first), 2 net-new (ABSENT from shared — the opposite of
retireable), 7 intel-local with no shared equivalent, 2 domain.** The other ~48
hooks (agent's KEEP-DOMAIN 45 + KEEP-GENERAL 3) are carried forward — keeping a
hook is the safe error; only wrongful *retirement* loses protection.

| Bucket | Count |
|---|---|
| CONFIRMED-RETIRE (shared equiv verified; swap local→shared) | 6 |
| RETIRE-UNVERIFIED (nearest shared hook differs in behavior — diff before delete) | 4 |
| KEEP — promotable net-new (ABSENT from shared) | 5 |
| KEEP — intel-local infra (no shared equiv; delete = lose protection) | 7 |
| KEEP — domain (conviction/falsifier/sizing/SEC/portfolio/paper-book/backtest) | 47 |
| **Total** | **69** |

## Method

Verification is two hard facts, not name-matching:
1. **Shared existence** — `ls ~/Projects/skills/hooks/` (file present?).
2. **Global wiring** — basename grep of `~/.claude/settings.json` (does it fire
   in *every* project, intel included? If yes, intel's local copy is dead weight).

A shared hook that merely shares a NAME stem but a narrower BEHAVIOR does **not**
cover intel's concern → that's KEEP / RETIRE-UNVERIFIED, never CONFIRMED-RETIRE.

## CONFIRMED-RETIRE (6) — swap intel-local → shared

| Intel hook | Covering shared hook | Global-wired? | Note |
|---|---|---|---|
| `pretool-agent-dispatch-inventory-gate.py` | `pretool-inventory-dispatch.py` | no (shared file present, not global) | intel must add the shared ref when removing local |
| `posttool-subagent-output-required.py` | `posttool-subagent-output-check.sh` | **yes** | already fires in intel via global; local is redundant |
| `pretool-subagent-skeleton-first.py` | `pretool-subagent-gate.sh` | **yes** | global subagent gate covers skeleton/turn-budget concern |
| `pretool-subagent-output-cosign-gate.py` | `subagent-epistemic-gate.sh` (+ `subagent-source-check-stop.sh`) | **yes** | global epistemic/source cosign covers it |
| `pretool-plan-stale-check.py` | `pretool-plan-protect.sh` | **yes** | global plan-protect covers concurrent-plan staleness |
| `pretool-work-claim-heartbeat.py` | `agent-coord.py` | no (shared file present, not global) | cross-session coord exists shared; swap, don't delete-bare |

The 4 with **yes** already fire in intel through the global config — pure dead
weight. The 2 with **no** require intel to wire the shared file when deleting the
local one (else coverage drops). Behavior-overlap confidence is high for the
subagent/plan cluster; spot-confirm `skeleton-first` vs `subagent-gate` semantics
before the swap.

## RETIRE-UNVERIFIED (4) — behavior differs; diff before deleting

| Intel hook | Nearest shared hook | Why uncertain |
|---|---|---|
| `pretool-bash-uv-unbuffered.py` | `pretool-streaming-cli-guard.sh` | streaming-guard may not cover the uv-unbuffered 0-byte-output case |
| `pretool-yaml-frontmatter-gate.py` | `prewrite-frontmatter-inject.sh` | shared **injects** frontmatter; intel **gates** on unparseable YAML — different mechanism |
| `pretool-document-delete-gate.py` | `pretool-archive-guard.sh` / `pre-commit-protected-paths.sh` | shared **blocks** protected-path deletion; intel **tombstones** on delete |
| `causal-check-warn.sh` | `pretool-regression-dag-gate.sh` | both causal-DAG-flavored but may target different claim surfaces |

These are not safe deletes on the agent's say-so. Intel's owner should diff the
firing predicate against the shared hook; if equivalent, retire — if not, keep.

## KEEP — promotable net-new (5; ABSENT from shared layer)

| Intel hook | Concern | Promotable upward? |
|---|---|---|
| `pretool-hook-trigger-discipline.py` | meta-hook: catch gates firing on bare prose instead of frontmatter | **yes → agent-infra** (only projects with many hooks benefit; not "global") |
| `userprompt-correction-classifier.py` | log user corrections → regret metric | yes, **but name the consumer first** (a log no dashboard reads = generation-without-consumption) |
| `pretool-eval-rule-state-check.py` | rule-ablation eval sentinel validation | maybe — couples to an eval-harness run-dir convention |
| `stop-deep-research-completion-gate.py` | block stop when deep-research started but not integrated | maybe — overlaps shared `stop-research-gate.sh`; diff |
| `stop-generator-extraction-nudge.py` | nudge synthesis quality on reasoning sessions | maybe — intel-flavored (generator library) |

The agent put the first two in RETIRE claiming global coverage; both are **verified
ABSENT** from `~/Projects/skills/hooks/`. Retiring them would delete a capability,
not deduplicate one.

## KEEP — intel-local infra, no shared equivalent (7)

Deleting these removes protection with no shared backstop. General in spirit but
key on intel's own infra conventions; not worth promoting (single-repo value):
`pretool-console-helper-gate.py`, `pretool-bare-duckdb-connect.py`,
`pretool-hardcoded-path-gate.py`, `pretool-rule-link-validator.py`,
`pretool-tools-grep-registry-nudge.py`, `posttool-untracked-dir-warn.py`,
`posttool-tiny-dataset-file-warn.py`.

## KEEP — domain (47)

Two the agent wrongly put in RETIRE are domain controls, not generic:
`pretool-paper-book-isolation-gate.py` (intel's hidden trade journal during blind
eval) and `backtest_guard.sh` (PIT-safety on investing backtests). Plus the
agent's 45 KEEP-DOMAIN — conviction-journal YAML schema, falsifier/trigger
discipline, source-grade tiers, portfolio stance-stacking, sizing, Tier-1 data
liveness, session-start grounding. No shared equivalent exists because no other
repo implements intel's conviction/falsifier architecture. Leave them
(`vetoed-decisions.md`: don't force shared abstractions over divergent logic).

## Recommendation for intel's owner

1. **Retire the 6 confirmed** — for the 4 global-wired ones, delete the local
   ref outright; for `inventory-dispatch` + `work-claim-heartbeat`, add the
   shared ref in the same edit so coverage doesn't drop.
2. **Diff the 4 unverified** against their nearest shared hook; retire only on a
   confirmed predicate match.
3. **Leave the other 59.** The 5 net-new are candidates to promote *up* (esp.
   `hook-trigger-discipline` → agent-infra), not delete. The 7 intel-local and 47
   domain hooks stay.

Net: the "intel forked 70 hooks" story is real, but the *redundant* surface is
~6–10 hooks, not 21. The bulk is correct domain divergence. This is a
recommendation — retiring intel hooks is intel's call (another repo;
delete-of-architectural-component is human-gated).
