---
title: Worktree reclaim candidates — per-item evidence after the 2026-07-25 sweep
date: 2026-07-25
status: active
tags: [storage, hygiene, worktrees]
extends: 2026-07-25-disk-pressure-live-fleet.md
---

# Reclaim candidates — measured 2026-07-25 21:40 CEST

State after the apply run that landed `6d294e6` / `d8b4181` / `b4f89cc`:
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
| `genomics-syn3sr-residuals-64655` | 1.1G | **Stranded husk.** `git status` → `fatal: not a git repository`; admin dir gone. Content vs `ship-main`: 2640 files changed, **1.48M deletions** — a half-finished `worktree remove` that aborted on the read-only source-epochs cache. The lane's commits live on `ship-main`. This is exactly the class `6d294e6` now finishes. |
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
shape as the `modal_crash_loop_watcher` daemons that `d8b4181` split out of HELD into DAEMON.
Its content is entirely branch-backed. If that Cursor session is confirmed gone, kill **PID
3906 by exact PID** (never a substring pattern — that has killed a healthy job here twice) and
it becomes Tier 3.

## The leak, and what shipped for it (2026-07-25 22:0x)

Reclaiming 16.8 GB does not close the leak. Every large tree above came from an ad-hoc
`git worktree add /tmp/<name>` in an agent Bash call, and nothing on this machine collects
those.

### Vendor coverage — narrower than the search summaries claim

From the primary docs, not a blog:

| Creator | Vendor cleanup |
|---|---|
| interactive `--worktree` / `EnterWorktree` | exit-time: clean+unnamed auto-removed, else prompt |
| **`-p --worktree` (headless)** | **none** — "Claude doesn't clean up their worktrees" |
| subagent `isolation: worktree`, background session | periodic sweep at `cleanupPeriodDays`; skips trees holding work |
| **manual `git worktree add`** | **none** |

The docs are explicit that the sweep "never removes worktrees you create with `--worktree`",
and `ExitWorktree` that it "will NOT touch worktrees you created manually". We dispatch
headless constantly and hand-rolled the rest, so we sat in the two uncovered rows.

Two vendor facts I had wrong earlier, both corrected by measurement:

- **Codex has no worktree feature at all** — no flag in `codex --help`, and `~/.codex/worktrees`
  holds four *symlinks to `~/Projects` repos*, not worktrees. No lifecycle to route to.
- **Cursor does have one** — `cursor-agent -w` → `~/.cursor/worktrees/<repo>/<name>`, nested one
  level deeper than every other layout.

### Shipped

| Change | Where | Effect |
|---|---|---|
| `pretool-worktree-location-guard.py` | skills `50d979d` | Blocks `git worktree add` outside a managed dir. Wired into `pretool-bash-dispatch.py` (Claude) **and** `~/.codex/hooks.json` via the shim (Codex runs gates individually, not through the dispatcher). 16/16 selftest; verified firing on both paths. |
| Stranded-tree discovery | agent-infra `8002268` | `worktree_gc` scans `/private/tmp` + `~/.cursor/worktrees` (depth 2) instead of only asking repos what they own. 10 tests. |
| Nightly GC | dotfiles `0d97cb1` | `com.dotfiles.reclaim-rotate` (04:10) now runs `worktree_gc apply --all-projects`. |
| Cursor rule | `~/.cursor/rules/worktree-location.mdc` | Cursor doesn't run our hooks; a rule is the only lever. |

### Rejected: lowering `cleanupPeriodDays`

The obvious knob is a trap. It is a **single shared cutoff** — the docs: *"Claude Code deletes
session files and other application data older than this period at startup. The same age cutoff
applies to automatic removal of orphaned worktrees."* There is no worktree-only setting. Cutting
it to 7 to reap worktrees sooner would delete 23 days of session transcripts, which
`agentlogs`, `session-forensics` and every retro depend on. Left at the 30-day default; our own
GC reaps on whatever schedule we want with none of that coupling.

### The scheduled job was dead

Worth recording separately: `com.dotfiles.reclaim-rotate` — the only scheduled disk-reclaim job
on this box — had exit code 2 on **11/11 runs**. `uv cache prune` waits 300 s for a cache lock
agents always hold, times out, and aborts the job. The script's own header had recorded that
finding on 2026-06-10 and it kept running for six weeks. The prune now uses a 15 s timeout and
is allowed to skip; the log prints a free-space delta so a future no-op is visible rather than
silent.

## Revisions

- **2026-09-23** — pointer only: dotfiles history was rewritten to drop a committed API-key literal, so `0d97cb1` (Nightly GC row) is now `6ff14c5`. Full old→new map in improvement-log 2026-09-23 "DOTFILES-KEY-REWRITE".
