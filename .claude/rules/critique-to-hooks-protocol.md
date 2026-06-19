---
paths:
  - "**/*.py"
  - "**/*.md"
  - ".claude/hooks/**"
---

# Critique-to-Hooks Protocol

<!-- Gov-ID: rule:critique-to-hooks-protocol
goal: turn per-session corrections into hooks in the same session, not deferred memory notes
verifier: null
blast_radius: local
-->

After fixing a correction or critique finding in-session, run this 5-step check:

1. **Fix the instance** — complete the immediate task first.
2. **Sweep the class NOW** — before hookifying, check whether the *same* failure
   has other live instances and fix them this turn. For a code/artifact defect this
   is global rule #21 ("a reported defect is a symptom — sweep the artifact for the
   CLASS"). For a **behavioral self-correction** it is the same move: if the operator
   corrected one over-ask / one rediscovery / one premature escalation, the class
   almost always recurs elsewhere in the session — fix every instance in reach, don't
   wait to be walked to the next one. (Closes blindspot B5 #1, 2026-06-19: rule #21
   was scoped to artifacts; the sweep obligation is identical for behavior.)
3. **Hookability check** — ask: "Could a pre-tool or stop hook have caught this
   CLASS of failure before it happened?" (yes/no + one sentence why)
4. **If yes → build the hook in this session.** Don't defer to "a future
   improvement." The cost is near-zero; the compound benefit starts immediately.
5. **If no → document why not** — one `[obs]` line in `improvement-log.md`
   naming the class and why it resists hookification.

## Why this exists

The pair-rule in `~/.claude/CLAUDE.md` fires when the HUMAN catches a recurring
pattern ("manually point out a recurring failure → structural fix is a hook, not
a memory note"). This protocol fires when the AGENT catches it on FIRST occurrence —
before it recurs. Evidence: 2026-05-15 intel critique session produced 4 hooks in
one pass (`pretool-recent-news-scan-gate.py`, `stance-stability.md`,
`pretool-aggregator-in-load-bearing-section.py`,
`pretool-material-risk-conviction-review.py`). The pair-rule would only have fired
if the human had to point out the pattern after it recurred.

## Scope

Applies to: any session that modifies behavior in response to a correction —
not just formal `/critique` runs. A user-flagged error, a failed test that surfaces
a class of mistake, a retro finding that names a repeatable failure — all trigger
the check.

Does NOT apply to: one-off user preferences, aesthetic choices, project-specific
constraints with no generalizable class behind them.
