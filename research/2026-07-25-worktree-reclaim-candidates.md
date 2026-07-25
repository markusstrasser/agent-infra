---
title: Worktree reclaim candidates — per-item evidence after the 2026-07-25 sweep
date: 2026-07-25
status: active
tags: [storage, hygiene, worktrees]
extends: 2026-07-25-disk-pressure-live-fleet.md
---

# Reclaim candidates — measured 2026-07-25 21:40 CEST

State after the apply run that landed `fe8aa48` / `3cb6958` / `c5c677a`:
`/private/tmp` is **42 GB** (was 82 GB), **13 registered worktrees**, `worktree_gc audit`
reports **0 auto-safe**. Everything left therefore needs per-item evidence — which is what
this file is. It does not re-derive the leak diagnosis; that is
[the disk-pressure memo](2026-07-25-disk-pressure-live-fleet.md).

## Deciding checks used (all read-only)

| Signal | Command | What it decides |
|---|---|---|
| unique work | `git cherry main <head>` → count `^+` | 0 = every commit already on main by patch-id |
| commit survival | `git for-each-ref --contains <head>` | a named branch means removing the dir cannot orphan commits |
| in-flight edits | `status --porcelain` split tracked/untracked | staged adds ≠ build junk |
| liveness | `lsof -a -d cwd` → exact PID → `ps -p` | a holder PID, never a substring `pkill` pattern |
| kind | `.git` **file** vs **dir** | stranded worktree vs standalone clone — different reclaim rule |

The last row is a correction to my own first pass: `[ -e .git ]` matches both, so six upstream
clones initially read as "stranded worktrees". They are not worktrees at all.

## Tier 1 — delete now, nothing at risk (~2.3 GB)

| Path | Size | Why it is free |
|---|---:|---|
| `genomics-syn3sr-residuals-64655` | 1.1G | **Stranded husk.** `git status` → `fatal: not a git repository`; admin dir gone. Content vs `ship-main`: 2640 files changed, **1.48M deletions** — a half-finished `worktree remove` that aborted on the read-only source-epochs cache. The lane's commits live on `ship-main`. This is exactly the class `fe8aa48` now finishes. |
| `MosaicForecast-upstream-class-audit` | 917M | Clone of `parklab/MosaicForecast`, clean, re-clonable |
| `ensembl-vep-116` | 225M | Clone of `Ensembl/ensembl-vep`, clean, re-clonable |
| `c4investigator.P79BVX` | 33M | Clone of `Hollenbach-lab/C4Investigator`, clean |
| `aldy-4.8.3.fqALxK` | 27M | Clone of `0xTCG/aldy`, clean |
| `MosaicForecast-upstream-class-audit2` | 120K | Husk — all 143 tracked files show `D`; the tree was already deleted |
| `genomics-mirror-review.H1phcc` · `genomics-producer-review.H6AH81` · `genomics-special-mei-patch-repo.NC0vF3` | ~2.9M | Throwaway review clones, last real write 07-24 |
| `bias-2015-source` · `bonsai-demo.cwqI2B` · `genome-toolkit-bundle-verify` | 0B | Empty |

**Excluded on purpose:** `ra-test`, `ra-empty`, `ra-skip`, `ra-onlyempty`,
`ra-untracked-empty` (~700K) are the **positive-control fixtures from today's
`worktree_gc` hardening** — peer-session property, not garbage.

## Tier 2 — re-derivable, one glance first (~4.2 GB)

| Path | Size | Evidence | Caveat |
|---|---:|---|---|
| `cogitao-src-live` | 1.7G | Clone of `yassinetb/COGITAO`; only dirt is `.DS_Store` + `uv.lock` | **No `~/Projects/cogitao` exists** — this is the only local copy; deleting costs a re-clone |
| `genomics-currency-audit.sIofGg` | 1.2G | Clone of local genomics for a one-off audit; clean; last real write 07-22 22:26 (a `.pyc`) | Fully re-derivable from `~/Projects/genomics` |
| `genomics-alpha-recovery.nwzqyE` | 1.3G | Registered worktree, **cherry-uniq = 0** (nothing not already on main), tracked-dirty 0, HEAD `1094ae016` reachable from `rescue/alpha-recovery-alphagenome-multiallelic` | Only writes since 07-23 are daemon `crash-loop.log` lines |

## Tier 3 — drop the directory, commits survive (~10.3 GB)

All four are clean and their HEAD is reachable from a **named branch**, so removal costs one
`git worktree add` to restore, and loses nothing.

| Path | Size | Uniq commits | Survives on | Liveness |
|---|---:|---:|---|---|
| `.claude/worktrees/agent-a2a28ee9a83ef6d95` | 3.5G | 271 | `kernel/cyp2d6-resolution` | no cwd holder; last real write **07-25 17:45** (`CYP2D6-PORT-LOG.md`) |
| `.claude/worktrees/agent-aad6f94b88c3441aa` | 2.9G | 271 | `kernel/phase-metric-port` | no cwd holder; last real write **07-25 17:36** (`PHASE-PORT-LOG.md`) |
| `jw-actuator-resume-wt-0b0f97d6` | 2.7G | 26 | `ship-main` | no holder, detached but contained |
| `genomics-ship-syn3sr.clean` | 1.2G | 21 | `ship-main` | no holder, detached but contained |

`worktree_gc apply --include-unmerged` covers exactly this class. **The two `agent-*` trees
were written to four hours ago** — recent enough to be a paused session rather than a finished
lane, so they are an operator call, not an autonomous reap. The 2026-07-24 near-miss labelled
two active worktrees RECLAIM off `lsof` alone; recency is the second signal that catches it.

## Tier 4 — keep, with the reason

| Path | Size | Why not |
|---|---:|---|
| `.claude/worktrees/red-tests-diag` | 3.3G | **20 live PIDs**, incl. `modal run` under its own `.venv`; git-`locked` |
| `kernel-integration` | 2.0G | **2 live PIDs**, last commit 23 min ago, 273 uniq commits + 2 dirty |
| `kernel-lane-namedproof` | 2.8G | 244 uniq commits, **13 tracked-dirty** |
| `kernel-mount-coverage` | 2.5G | 244 uniq commits, 2 tracked-dirty |
| `genomics-bphunter-raw-stage` | 2.4G | 176 uniq commits, 4 tracked-dirty |
| `bphunter-rescue-land` | 1.3G | cherry-uniq 0, but the 4 dirty files are **staged `A` adds** (`bphunter_raw{,_contract,_package,_validation}.py`) — new code, uncommitted |
| `genomics-minimal-drive-019f78e3-v3` | 2.5G | Content is safe (225 uniq, all on `kernel/*` branches) but **PID 3906 `cursorsandbox --run-proxy` holds its cwd** → conditional, see below |

## Totals

```
Tier 1  ~2.3 GB   free
Tier 2  ~4.2 GB   one glance
Tier 3 ~10.3 GB   dir only, branches survive  (6.4 GB of it = operator call)
        ────────
       ~16.8 GB   available now
       + 2.5 GB   conditional on PID 3906 (genomics-minimal-drive)
```

## The one conditional

`genomics-minimal-drive-019f78e3-v3` is held by a Cursor sandbox proxy, not by work — the same
shape as the `modal_crash_loop_watcher` daemons that `3cb6958` split out of HELD into DAEMON.
Its content is entirely branch-backed. If that Cursor session is confirmed gone, kill **PID
3906 by exact PID** (never a substring pattern — that has killed a healthy job here twice) and
it becomes Tier 3.

## What this does not fix

Reclaiming 16.8 GB does not close the leak. `reclaim`'s worktree section still iterates only
`$HOME/Projects/*/.claude/worktrees` (`~/.local/bin/reclaim:325`), and every large tree above
was created by an ad-hoc `git worktree add /tmp/<name>` in an agent Bash call. Until the GC
scans `/private/tmp`, this file gets rewritten next week with different names.
