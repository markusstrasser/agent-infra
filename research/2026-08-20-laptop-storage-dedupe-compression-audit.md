# Laptop storage dedupe, compression, and cleanup audit — 2026-08-20

**Verdict:**

- The largest current opportunity is not another general cleaner. The existing
  `agentlogs-archive` owner is stalled because `/Volumes/2TBPNY` is not mounted:
  its dry run finds **6.9 GB of old raw sessions**, while the derived live search
  DB has grown to **19 GB** and has 2,559 sessions beyond its 30-day window.
- A second, non-overlapping **roughly 8–10 GiB** is available from narrow,
  rederivable surfaces after their applications are stopped: a 1.4 GiB Codex
  hook audit log, 1.36 GiB of free SQLite pages, a 1.2 GiB stale Raycast tree,
  about 1.28 GiB of old agent CLI versions, a 984 MiB Bun cache, 1.5 GiB of
  Codex runtimes, and 2.8 GiB of publishing build output. This is a planning
  band, not an additive guarantee; APFS clones and regeneration during the run
  can make the observed `df` delta smaller.
- Project-wide exact duplicates are **9.51 GiB logical** at a 1 MiB threshold,
  but most are not junk. The good targets are representation fixes: ARC audio
  content-addressing, source-epoch reachability GC, and immutable-generation
  dedupe. Blind `fdupes --delete` would cross authority boundaries.
- Compression is unusually promising for two IQ fixed-width raw files: bounded
  samples project about **3.36 GB saved** losslessly with zstd. Archival PCM audio
  also compresses 65–84% with FLAC, but active Logic projects are a user/consumer
  boundary and should not be rewritten automatically.
- The machine has **no working automatic backup** and the archival SSD is absent.
  Unique medical, photo, music, document, and expensive personal-index state are
  therefore a hard no-action class. This audit made no further deletions.

## Question and decision

The question was not merely “what is large?” It was:

> Which local bytes are unnecessary or rederivable, which can be represented
> more compactly, and which cleanup is already owned by `reclaim` or another
> lifecycle rather than needing a second mechanism?

Current snapshot: `/System/Volumes/Data` is 324 GiB used with **90 GiB
available**. Earlier in this session, a scoped `~/Library` cleanup permanently
removed 9.23 GiB. This memo covers the rest of the laptop and is read-only.

The decision is to **restore and sharpen existing owners**, not create a broad
second cleanup daemon:

1. Mount `2TBPNY` and run the existing snapshot-gated agent-history archive.
2. Rotate/compact the two unbounded Codex log stores.
3. Teach `reclaim` to report hidden-home/version-cache gaps and correct stale
   labels, while leaving project semantics to project-specific owners.
4. Only then do the three project representation changes with consumer tests.
5. Do not touch unique personal data until a backup is working.

## What already owns cleanup

`reclaim` is a useful front door, but its subcommands have distinct scopes.

| Surface | Existing owner | Live finding |
|---|---|---|
| uv, Homebrew, pip, npm, old Hugging Face models, Playwright, common app caches, Codex runtimes, Python build caches | manual `reclaim caches`; uv prune also runs nightly | uv is 12 GiB but was pruned successfully today; Codex runtimes are 1.5 GiB and regenerate |
| stale top-level project venvs | manual `reclaim venvs` | 28 venvs total 15.01 GiB, but the current command only considers `~/Projects/*/.venv` and several venvs are live |
| merged/clean worktrees | nightly `reclaim-rotate-cron` via `worktree_gc.py` | one ARC worktree remains explicitly `LAND`, so it is correctly preserved |
| `~/.claude/logs` files over 200 MiB | nightly `reclaim-rotate-cron` | only launchd stdout logs are covered; Codex hook logs are elsewhere |
| agentlogs DB retention and old raw vendor sessions | weekly `just agentlogs-archive` | owner exists but its last run failed because the external SSD was absent |
| root-owned install leftovers | manual `reclaim sudo-items` | the hard-coded “Previously Relocated Items ~11 GB” label is stale; that path is now only 64 KiB |

The nightly job actually performs three motors: safe worktree GC, uv cache prune,
and truncation of large `~/.claude/logs` files. It does **not** run the full
`reclaim caches` suite. `agentlogs-archive` is intentionally a separate owner.

The `reclaim sweep` implementation uses `$HOME/*`, so it misses hidden homes.
Those currently include about 21 GiB in `~/.claude`, 15 GiB in `~/.cache`,
14 GiB in `~/.codex`, 7.4 GiB in `~/.local`, 2.4 GiB in `~/.config`, 2.0 GiB
in `~/.bun`, and 1.6 GiB in `~/.cursor`. These are not all cleanup candidates,
but omitting them makes the report systematically incomplete.

## Ranked findings

### P0 — unblock the owner already designed for the largest backlog

#### Agent history: archive backlog plus retention prune

- `~/.claude/agentlogs.db`: **19 GB** / 19,597 MB according to `agentlogs`.
- `~/.codex/sessions`: **8.9 GB**; 6.9 GB of the archive dry run comes from
  142 Codex JSONL files, largely the 2026-08-04 burst.
- `archive_raw_logs.py --keep-days 14` dry run:
  146 Claude files / 269.6 MB, 142 Codex files / 6.6 GB, total **288 files /
  6.9 GB**.
- `agentlogs prune --keep-days 30` dry run: 2,559 sessions, 2,632 runs,
  145,898 events, 40,732 tool calls, 6,164 file touches, and about 11.14 million
  record references are beyond retention.
- The DB's current oldest session is 2026-07-18. It has zero freelist pages, so
  no safe space is recoverable by a VACUUM alone; the retention transaction must
  run first.

The raw JSONLs are source of truth. The SQLite DB is a derived search surface,
but the retention contract requires an integrity-checked external snapshot
before pruning it. The archive job also relocates old raw files with a reversible
manifest. Therefore the only correct next action is:

```bash
# after /Volumes/2TBPNY is mounted
just -f ~/Projects/agent-infra/justfile agentlogs-archive
```

Verify the new `.db.zst`, integrity result, raw-file manifest, zero over-retention
sessions, and the before/after `df`. Do not replace this with `rm` or a local
compression pass.

### P1 — narrow rederivable surfaces missing from current lifecycle

| Surface | Evidence | Safe treatment | Potential |
|---|---|---|---:|
| Codex hook-fire log | `~/.codex/log/hook_shim_invocations.jsonl`: 1.4 GiB, 10,275,837 lines, Jun 11–Aug 20; only documented forensic reader; 48 MiB stratified sample zstd ratio 5.2% | atomic size/time rotation, retain recent plaintext and compressed history | about 1.3 GiB |
| Codex log SQLite | `logs_2.sqlite`: 1.625 GiB; 355,268 / 425,976 pages free (83.4%); live pages project to 276 MiB | compact/VACUUM only while Codex is stopped, after a verified backup or via an app-owned maintenance path | 1.355 GiB |
| Legacy Raycast extension tree | `~/.config/raycast`: 1.2 GiB, no file modified in 14 days and directory mtime 2025-09-10; active Raycast Beta uses `com.raycast-x` and `~/.config/raycast-x` has 1,185 files modified in 14 days; 0.71 GiB is byte-identical across the trees | trash the whole legacy tree after one final app/path check; do not hardlink live extension trees | 1.2 GiB logical |
| Old Claude Code binaries | current symlink targets 2.1.237; 2.1.234 and 2.1.235 remain | keep current target, remove old updater versions | 595 MiB |
| Old Cursor Agent versions | current symlink targets 2026.08.11; Jul 23, Aug 4, and a hidden 2025 version remain | keep current target, remove old versions | 463 MiB |
| Old Grok downloads | current symlinks target 1.0.5; 1.0.4 and the older generic binary remain | keep current target, remove old downloads | 251 MiB |
| Bun package cache | `~/.bun/install/cache`: 984 MiB; native command exists | `bun pm cache rm` when no install is active | 984 MiB |
| Codex workspace runtimes | `~/.cache/codex-runtimes`: 1.5 GiB | already owned by `reclaim caches`; run after Codex work finishes | 1.5 GiB |

The Codex `state_5.sqlite` file is different: it is about 960 MiB and almost all
pages belong to the `threads` table. It is active application state, not a cache
verdict. Keep it. The raw session archive does not authorize deleting it.

### P1 — rederivable project and temporary output

| Surface | Evidence | Decision |
|---|---|---|
| Publishing build | about 1.14 GiB `.svelte-kit`, 1.10 GiB `node_modules`, 0.59 GiB `build` | about 2.8 GiB rederivable; project clean command should own it |
| Chrome code-sign clones | four nominal 1.44 GB bundles in `code_sign_clone`; only the Aug-20 bundle had a live handle, leaving three nominally stale | quit Chrome, identify current bundle again, then remove only no-handle older clones; APFS clone accounting makes 4.1 GiB an upper bound |
| clang and Blender caches | about 0.75 GiB + 0.47 GiB under `/private/var/folders/.../C` | app-owned, rederivable; clean only while apps are stopped |
| genomics index temp trees | four non-empty `genomics-index-tree-*` directories total about 0.87 GiB, no open handles; producer uses `TemporaryDirectory` | stale crash residue, but fix cleanup at the producer and gate deletion on age + no live holder |
| project venvs | 28 `.venv` trees total 15.01 GiB; live processes currently use agent-infra, research-mcp, personal knowledge MCP, genomics, and ARC venvs | not a 15 GiB target; extend reporting to nested venvs, then remove only inactive, lockfile-recreatable environments |
| project `node_modules` | bounded scan found about 1.34 GiB, dominated by publishing | remove through project package managers, not a global filesystem delete |

Do not blanket-clean `/private/tmp/claude-501`: its 3.2 GiB ARC scratchpad has
live writers, while a 1.6 GiB inactive IQ scratchpad may contain unique experiment
output. “No current `lsof` holder” is not sufficient authority to delete a run.
Likewise, `/private/tmp/T2D_pymcmc_seed42.txt.gz` is a recent compressed result,
not a cache-shaped verdict.

### P2 — exact dedupe should change representation, not delete copies ad hoc

`fdupes` over `~/Projects` at a 1 MiB minimum found **438 duplicate sets,
1,259 redundant files, and 10,213,890,072 redundant logical bytes (9.51 GiB)**.
This is an upper bound and overlaps the project surfaces below.

| Mechanism | Logical redundancy | Better representation |
|---|---:|---|
| ARC recordings, especially canonical browser WAV copied into episode directories | 2.08 GiB in recordings; 3.09 GiB across ARC overall | immutable content-addressed audio store plus per-episode reference/manifest; hardlinks only if every writer treats audio as immutable |
| genomics source-epoch full-tree snapshots | 1.74 GiB exact redundancy inside a 3.3 GiB store | retain immutable epoch identities, then add reachability/receipt-based GC or a shared content store; do not delete epochs by age |
| personal runtime generations and venv binaries | 1.40 GiB | generation-aware dedupe only for immutable artifacts; state contract marks search/medical/media indexes as expensive and snapshotted |
| Logic projects | 1.75 GiB exact redundancy | optional archive-library dedupe after backup; never mutate live Logic packages with a generic hardlink pass |
| Documents archive | 0.30 GiB | reconcile only after backup and canonical-copy selection |

APFS may already share physical blocks for some clones, so each refactor must
measure `df` before and after. `fdupes` proves byte equality; it does not prove
ownership, mutability, or physical reclaim.

### P2 — lossless compression candidates

The probes streamed the beginning, middle, and end of each file; nothing was
rewritten.

| Candidate | Probe | Projected result | Decision |
|---|---:|---:|---|
| IQ `childK5p.dat` (2.455 GB) | zstd level 1 sample = 20.1% | about 0.49 GB, saving about 1.96 GB | strong: preserve hash/provenance and teach consumers to stream `.zst` or materialize through one owner |
| IQ `childk8p.dat` (1.592 GB) | zstd level 1 sample = 12.1% | about 0.19 GB, saving about 1.40 GB | strong under the same consumer gate |
| ARC WAV sample (50.6 MB) | FLAC = 17.9 MB | 64.6% saved | combine with the content-addressed recording store |
| Logic AIF samples | FLAC saved 63.2% and 84.0% | large archival win | archive-only option after backup; Logic may require PCM for active projects |
| Documents `combos.csv` | zstd sample = 3.05% | about 97% saved, but source is only 65.6 MB | easy but low absolute value |

Do not recompress ZIP, Parquet, safetensors, video, or `fastq.gz` files. Their
better levers are dedupe, retention, or offload.

## Preserve / no action

- `~/Documents/medical` (8.8 GiB), Photos library (8.9 GiB), Photo Booth
  (4.0 GiB), and Logic projects (8.7 GiB): unique personal data with no current
  backup.
- Personal `_system` indexes: the state contract distinguishes authoritative,
  derived-expensive-snapshotted, and rebuildable stores. Preserve expensive
  generations until their snapshots are verified.
- Raw Claude/Codex/Cursor transcripts: source of truth. Move them only through
  the manifest-backed archive.
- Corpus and scientific datasets: many are reacquirable in principle but carry
  API, provenance, normalization, or compute cost. “Downloaded” does not mean
  disposable.
- Active or unmerged worktrees: current ARC worktree is `LAND`, not `SAFE`.
- Google Drive placeholders: Spotlight reports tens of gigabytes of logical
  cloud files, but `~/Library/CloudStorage` occupies only about 858 MiB locally.
  Quitting Drive does not create the advertised logical-file savings.
- macOS diagnostics databases and update snapshots: OS-owned. There are no Data
  volume Time Machine snapshots to reclaim.
- Installed applications: Final Cut Pro, Logic, Endel, Blender, and similar
  removals are usage/taste decisions, not generic hygiene.

## Weakest-link audit

The proposed reclaim chain is:

> large bytes → genuinely duplicate/compressible → authority identified → all
> consumers tolerate the representation → backup/restore exists → physical
> blocks are actually released.

The weakest links are **authority/consumer validation** and **backup**, not the
ability to find matching bytes. Exact hashes and compression ratios only locate
candidates. They do not decide which copy is canonical or whether an application
writes in place.

The leading explanation is lifecycle drift: the largest owners already exist,
but the archive disk was absent, hidden homes are omitted from the general
report, and several append-only logs/version caches have no rotation. The null
hypothesis is that most large storage is legitimate current work; that null is
true for unique media, live state, active scratchpads, installed toolchains, and
many datasets.

The top alternative to cleanup is adding reliable backed storage and leaving
hot data intact. It becomes the preferred option for unique media and expensive
derived state because the current backup precondition fails.

### Falsifiers

- If the mounted archive run does not relocate roughly the 6.9 GB dry-run set,
  the archive manifest/candidate logic is stale and must be diagnosed before any
  manual deletion.
- If offline VACUUM of `logs_2.sqlite` does not recover near its 1.36 GiB
  freelist, another live connection/WAL or APFS allocation is the mechanism.
- If the old Raycast tree changes while only Raycast Beta is running, the path
  classification is wrong; keep it.
- If a `.zst` IQ consumer probe cannot reproduce byte-identical raw input, keep
  the raw file and reject the migration.
- If `df` gains materially less than logical duplicate estimates, APFS block
  sharing explains the gap; do not escalate by deleting more authority.

## Recommended queue

1. **Existing owner:** mount `2TBPNY`; run and verify `agentlogs-archive`.
2. **Backup:** restore a working automatic backup before touching personal data.
3. **One-time, app-stopped cleanup:** reclaim caches, stale CLI versions, Bun
   cache, legacy Raycast tree, and proven stale Chrome/temp trees.
4. **Small lifecycle fixes:** rotate/compress the Codex hook log; compact the
   Codex log DB offline; include hidden-home totals in `reclaim sweep`; replace
   `sudo-items`' hard-coded size labels with live `du`; report nested venvs but do
   not broaden autonomous deletion.
5. **Project changes with tests:** IQ zstd consumer path, ARC recording CAS, and
   genomics source-epoch reachability GC.

No new all-purpose cleanup automation is justified. The bounded owners above
cover the real mechanisms and keep raw evidence, expensive state, and personal
data out of generic deletion paths.

## Execution update — 2026-08-20 12:02 CEST

The operator authorized the no-SSD slice after this memo was written. The slice
completed with **90 GiB → 99 GiB free** on `/System/Volumes/Data`: about 12.3 GiB
of logical targets produced a measured **9 GiB physical reclaim**. The smaller
physical delta is consistent with the memo's APFS clone warning.

Completed and verified:

- Rotated the 1.42 GiB Codex hook-fire log and compressed it losslessly to a
  **57 MiB** zstd archive. `zstd -t` passed, and the new live JSONL was recreated
  automatically and continued receiving valid records.
- Removed two obsolete Claude Code binaries, three obsolete Cursor Agent
  versions, two obsolete Grok downloads, and the stale stable-Raycast extension
  tree. Current Claude 2.1.237, Cursor Agent 2026.08.11, Grok 1.0.5, and Raycast
  Beta remained live.
- Cleared the 984 MiB Bun install cache using the native command. Operational
  footgun: `bun pm cache rm` failed outside a package root and succeeded from the
  publishing repository, so a future `reclaim` owner must provide a valid cwd.
- Removed ignored publishing output (`.svelte-kit`, `node_modules`, and `build`),
  reducing that repository from about 3.5 GiB to **843 MiB** without changing
  Git status; `bun.lock` remains the reconstruction contract.
- Removed two Chrome code-sign clones with zero live handles, four orphaned
  genomics index temp trees with zero live handles, and inactive clang/Blender
  caches. A deletion-time recheck found Chrome mapped both `erU5kP` and
  `isGZQE`; both were preserved even though an earlier scan saw only one.
- Trash was empty before each recoverable move, contained only the enumerated
  targets afterward, and was then emptied. No personal data was touched.

Still gated:

- `agentlogs-archive`, its 30-day DB prune, and 6.9 GB raw-session relocation:
  `2TBPNY` remains unmounted.
- `logs_2.sqlite` offline VACUUM and Codex runtime removal: Codex is active.
- npm cache removal: several live MCP servers are executing from `_npx`.
- The two mapped Chrome clones: Chrome is active.
- IQ compression, ARC recording CAS, source-epoch GC, and all personal-data
  transformations: these require consumer/backup gates rather than a cleanup
  command.
