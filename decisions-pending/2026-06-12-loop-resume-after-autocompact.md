# Does a `/loop` wakeup auto-resume a turn after auto-compaction? — needs one live run

**Boundary:** shared (decides whether unattended overnight `/loop` work is reliable)
**Recommendation:** Run one real test before relying on unattended `/loop` across a compaction; until then, assume a mid-task auto-compact may stall an unattended loop and keep tasks checkpoint-resumable.
**Dissent / risk:** Low cost to defer — the checkpoint mechanism already works, so a stall loses time, not state. But if the loop does NOT auto-resume, the "one window looping all day services everything" model has a hole exactly when sessions run long.

## What's established (this session)

- **PreCompact → checkpoint.md auto-save works.** `precompact-log.sh` →
  `precompact-extract.py` fires on every compaction and writes
  `<project>/.claude/checkpoint.md` with epistemic content (verified live:
  recent rows in `~/.claude/compact-log.jsonl`, fresh checkpoint.md files in
  hutter/intel/phenome). The manual "save your stuff before compaction" message
  is redundant — the hook does it.
- **Post-compact re-orientation is rule-driven** (global CLAUDE.md: read
  checkpoint.md, verify claimed commits via `git log`). `postcompact-verify.sh`
  deliberately injects no recovery context.
- **Docs ground truth:** PreCompact is side-effect-only (cannot alter the
  summary); there is NO programmatic `/compact`, no custom threshold setting,
  hooks cannot read context% (hence the new statusline-tee advisory); after an
  auto-compact the session **stops and waits for input**.

## The unverified bit

After an auto-compact stops the turn, does the next `/loop` scheduled wakeup act
as the "continue" input and resume the work? **No historical evidence exists** —
a scan of every auto-compacted session in `compact-log.jsonl` found none that
also contained a `/loop`/`ScheduleWakeup` marker. So it has never happened (or
never been logged) and cannot be confirmed from data.

## Test protocol (cheap once set up)

1. Start a session in a scratch project under `/loop` (dynamic or short interval).
2. Give it a long task that naturally fills context (e.g. read many large files
   in a loop) to trigger a real auto-compact mid-task.
3. Observe: after the auto-compact, does the loop's next fire resume work
   without a human message? Check the transcript for an assistant turn after the
   compaction `summary` entry with no intervening user message.
4. Record the result here and in improvement-log; if it resumes, the
   "one looping window" model is sound; if not, file the gap (candidate fix:
   a SessionStart(compact) hook that re-issues the loop prompt).

**Open question for you:** worth a 20-30 min sacrificial run now, or defer until
it bites? (I recommend defer — the checkpoint safety net is in place.)
**Reversible?** Yes — purely a measurement.
**Evidence:** this session's commits 5654e7e/828b95c (hooks-smoke),
2edc81b (context advisory); `compact-log.jsonl` scan.
