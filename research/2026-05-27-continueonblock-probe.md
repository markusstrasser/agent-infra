---
title: continueOnBlock hook conversion probe — proposal
date: 2026-05-27
status: probe complete, awaiting approval (shared-infra hook change = autonomy boundary)
trigger: research/2026-05-27-claude-code-native-overlap-probe.md flagged continueOnBlock as highest-value lift
---

# continueOnBlock — Probe & Conversion Proposal

## Confirmed semantics (official docs, v2.1.139)

> "Added hook `continueOnBlock` config option for `PostToolUse` — set to `true` to feed the hook's rejection reason back to Claude and continue the turn"

- **Scope:** `PostToolUse` event only (not PreToolUse).
- **Mechanism:** When a PostToolUse hook returns block (exit 2), the rejection text is fed back into the model's *same turn* instead of ending the turn.
- **Default:** false — the legacy behavior (turn ends, agent re-processes on next turn) is unchanged.
- **JSON shape:** `{"type": "command", "command": "...", "continueOnBlock": true}` in `settings.json` hook entries.

## Inventory of our PostToolUse hooks that currently exit 2

| Hook | Blocks on | Today | Best fit for continueOnBlock? |
|---|---|---|---|
| `postwrite-source-check.sh` | provenance tag missing | only in PROVENANCE_MODE=block (rare); default is advisory exit 0 | Low — already advisory in normal use |
| `source-check-validator.py` | same family | same | Low |
| `posttool-dup-read.sh` | re-Reading a file already in context | exit 2 + tells agent to use cached content | **Medium** — agent currently bounces off and re-reads next turn |
| `posttool-bash-failure-loop.sh` | 5+ consecutive Bash failures | currently advisory exit 0 (per AgentDebug "targeted correction +24%") | **Best candidate IF** changed to exit 2 |

## Proposal — convert ONE hook as probe

**Target:** `posttool-bash-failure-loop.sh`. Two coordinated changes:

1. **Hook script (`~/Projects/skills/hooks/posttool-bash-failure-loop.sh`):** when failure count crosses THRESHOLD (5), change behavior from "print advisory to stdout, exit 0" to "print targeted correction to stderr, exit 2."

2. **Hook config (`~/.claude/settings.json`):** add `"continueOnBlock": true` to the entry:

   ```json
   {
     "matcher": "Bash",
     "hooks": [
       {
         "type": "command",
         "command": "/Users/alien/Projects/skills/hooks/posttool-bash-failure-loop.sh",
         "continueOnBlock": true
       }
     ]
   }
   ```

**Why this hook:** the failure-loop is the textbook case for in-turn correction. The agent has just failed Bash 5 times; the corrective advice ("stop retrying X, try Y") is most valuable BEFORE the agent generates its next assistant message. With the current advisory-exit-0 pattern, the advice arrives on the next turn, by which point the agent has often already committed to "let me try once more." With continueOnBlock + exit 2, the advice lands in the same turn — the agent sees the bash failure AND the corrective advice in one piece of context.

**Why NOT source-check or dup-read first:**
- source-check: 91 fires/24h but almost all are advisory (PROVENANCE_MODE=warn). Converting would require flipping the default mode for everyone, much bigger change.
- dup-read: legitimate use case (re-Reading a file after Edit/Write), conversion would need a behavior change to handle the "stale-after-edit" case.

## Risks

- **Affects all projects** that load `~/.claude/settings.json` and `~/Projects/skills/hooks/` — this is shared infra. Per the constitution, shared hook changes affecting 3+ projects need human approval.
- **No rollback button**: if `continueOnBlock: true` introduces a loop (hook keeps blocking; agent keeps trying), recovery requires editing settings.json. Mitigation: keep THRESHOLD at 5 (one block then turn-budget exhausts) and verify the hook's correction text actually changes the agent's approach.
- **Single change rule**: per the constitution's "isolate harness changes" finding (arXiv:2603.28052), change ONE thing per commit. If we flip both the hook script AND the config in one commit and a regression appears, we can't diagnose which caused it. **Recommended sequence:** (a) commit the hook-script change as exit-0 first to confirm logic, (b) flip exit to 2 as second commit, (c) add continueOnBlock to settings.json as third commit.

## Measurement plan

Before flipping: capture baseline from the last 7 days of `~/.claude/hook-logs/posttool-bash-failure-loop.log` (or equivalent — check actual log path):
- N = sessions where the threshold tripped
- Per-session: turns from threshold-trip to first successful Bash → proxy for "how long does the agent waste before correcting"

After flipping: same measurement over equivalent window. Expected improvement: median turns-to-correct drops from ~2-3 to ~1.

If the metric doesn't move OR moves negatively (loops), revert.

## Decision needed from user

A) Approve the 3-commit sequence as described.
B) Pick a different hook to convert as the first probe (dup-read, or a meta-only hook to limit blast radius).
C) Skip — current advisory-exit-0 pattern is fine; the cost/benefit isn't worth the shared-infra change.

Default if no response: option C (skip). The 4-week sweep flagged this as high-value but the actual evidence is qualitative — no measured ROI yet. The probe converts that qualitative into measurable.

<!-- knowledge-index
generated: 2026-05-27T11:01:34Z
hash: faed28b137af

index:title: continueOnBlock hook conversion probe — proposal
index:status: probe complete, awaiting approval (shared-infra hook change = autonomy boundary)
cross_refs: research/2026-05-27-claude-code-native-overlap-probe.md

end-knowledge-index -->
