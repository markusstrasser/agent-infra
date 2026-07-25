---
title: Boot disk at 99% — the /private/tmp worktree fleet, not repo bloat
date: 2026-07-25
status: active
tags: [storage, hygiene, worktrees, urgent]
supersedes_premise: 2026-07-14-storage-cost-dossier.md
---

# Boot disk at 99% (4.8 GiB free) — measured 2026-07-25

The [2026-07-14 storage dossier](2026-07-14-storage-cost-dossier.md) opened with "boot disk is
**not** under pressure (175 GiB free of 460)". **That premise is dead.** 11 days later:

```
$ df -h /System/Volumes/Data
/dev/disk3s5   460Gi   401Gi   4.8Gi    99%
```

The dossier's repo-structural layer (`~/Projects` = 67 GB) is **not** where the 170 GB went, and
executing its whole per-repo plan would reclaim ~20 GB — a fifth of the problem. The growth is in
three places it never looked at.

## Where it actually went

| Location | Size | Nature |
|---|---:|---|
| `/private/tmp` git worktrees (46) | **75.8 GB** | 21 have **live process cwds** — in-flight fleet |
| `/private/tmp` non-worktree (7032 entries) | ~21 GB | `claude-501` scratchpads 9 GB + probe/review dirs |
| `genomics/.claude/cache/source-epochs/content` | **15.7 GB** | 508,410 files, **no GC** |
| APFS `Preboot` volume | **24.9 GB** | normal is 1–6 GB; stale OS update payloads |
| APFS `VM` volume | 15.0 GB | swap/sleepimage; reboot reclaims |
| `~/.cache/uv` + per-repo `.uv-cache` | 21.5 GB | regenerable |
| `~/.codex/sessions` | 13 GB | transcripts; agentlogs retention is 21d |

Verify: `diskutil apfs list disk3` · `du -x -d 1 -m /private/tmp | sort -rn`

## The load-bearing finding: this is live work, not garbage

Every worktree is dated 2026-07-24/25 and 21 are live by exact-cwd check
(`lsof -a -d cwd -Fn | grep ^n/private/tmp`). Several **not**-live ones carry uncommitted
changes (`kernel-lane-veccut`: 195 dirty files; `genomics-producer-b/c/a`: 19/13/8).

So the reclaim is **not** a delete sweep — it is a lifecycle gap. Per-worktree cost is
~2.3 GB average (full checkout + `.venv`); nothing reaps a lane's worktree when the lane
finishes, so a 40-lane fleet permanently costs ~90 GB.

Do **not** infer RECLAIM from a quiet worktree — the 2026-07-24 genomics incident
(`~/.claude/CLAUDE.md` agent_toolbelt) labeled two ACTIVE worktrees reclaimable off an
`lsof`-cwd inventory. Dirty-count + exact-PID + branch-ahead all have to agree.

## Root causes (each is an architecture gap, not an instruction gap)

1. **`disk-preflight.md` structurally cannot catch this.** It fires before downloads >10 GB.
   170 GB arrived as thousands of small writes. A preflight gate is not a standing monitor.
2. **`reclaim rotate` is scheduled** (`com.dotfiles.reclaim-rotate.plist`) **but has no
   worktree-GC and does not look at `/private/tmp`.** It has `venvs`, `caches`, `big`, `sweep` —
   no `worktrees`.
3. **`genomics/scripts/source_epoch.py` (599 lines) has zero retention logic** — grep for
   `retention|prune|cleanup|gc|expire|days` returns nothing. A content-addressed store with no
   GC is an unbounded leak by construction.

## Non-findings (checked, do not chase)

- **Google Drive** — 1 GB, streaming mode. Not mirroring.
- **Time Machine local snapshots** — only 3 OS-update snapshots. Not the cause.
- **uv venv duplication is cheaper than `du` says** — uv's default macOS link-mode is `clone`
  (APFS reflink), so the 23 GB of `.venv` trees share blocks. `links=1` on a probed `.so` is
  CoW-clone, not a copy. A `--link-mode=hardlink` change is NOT a win here.
