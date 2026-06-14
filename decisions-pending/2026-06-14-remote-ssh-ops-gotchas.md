# 2026-06-14 — Remote-SSH ops gotchas → shared rule?

**Decision (30-sec yes/no):** Add a small global `~/.claude/rules/remote-ssh-ops.md`
capturing two transcript-verified, cross-project remote-VM gotchas? Or leave as
per-project lore?

## Why this is escalated (boundary)
- Reversible + STEM-verifiable fixes (not taste), BUT the proposed home is a
  **global rule** (`~/.claude/rules/`), whose dedup-owner is the Human per the
  context-budget layering convention. The loop doesn't self-author global rules.

## Evidence (drift mode, wide window, transcript-verified)
Two findings, each recurring across **2 distinct sessions**, grep-confirmed in the
real transcripts (not Gemini-hallucinated; session IDs verified to exist):

1. **SSH/SCP connection bursts trip host `fail2ban` (port-22 ban, ~600s).**
   - genomics/`b38baad8` (77× `fail2ban`, `Connection timed out`, `port 22`),
     hutter/`897a2209`. Rapid sequential SSH/SCP setup+liveness checks to Hetzner
     VMs → TCP drops while ICMP still answers → forced reboots / idle waits.
   - Fix: SSH `ControlMaster`/`ControlPersist` multiplexing (one connection reused),
     or minimum spacing between same-host SSH/SCP invocations.

2. **`pgrep -f <pat>` self-matches its own SSH-wrapper command line.**
   - genomics/`b38baad8` (`pgrep -fc sbrc_stage_data` returned inflated count incl.
     the invoking shell), hutter/`897a2209` (eval.py false count).
   - Fix: character-class bracket trick `[s]brc_stage_data` / `[e]val.py`, or explicit
     PPID exclusion, when parsing remote process tables over SSH.

## Options
- **A (recommended): tiny global rule.** Both projects (and future remote-VM work)
  inherit instead of re-learning. ~10 lines. Path-scope to nothing (gotcha, always-on)
  or leave discoverable. Low maintenance.
- **B: per-project rule** in genomics + hutter `.claude/rules/`. No global blast
  radius; duplicated (drift risk if one updates).
- **C: do nothing.** Recurrence is only 2 sessions/2 projects; may not recur if remote
  fleet work tapers.

## Loop's lean
A — the fixes are standard and correct, the cost is ~10 lines, and the same pattern
already recurred across the two heaviest remote-VM projects. But it's a global-rule
add → human call.

## If yes
Say "A" and I'll draft `~/.claude/rules/remote-ssh-ops.md`; you review the wording.
