> Provenance: distilled from 2026-07-14 cross-vendor agentlogs transcripts (3 Claude Code + 3 Cursor sessions) by a mining subagent; spot-verified by the integrating session (cursor-batch completion, uv-cache state, sudo-items state all confirmed on disk).

# 2026-07-14 Cleanup Sessions — Ledger

Six sessions across two tools (Claude Code, Cursor) ran concurrently/interleaved on the same
machine today, all triggered by the disk hitting **4.5 GiB free (99% used)**. They were NOT
independent: cursor session `0cf51a6d` ran the original parallel `du` survey and its numbers
were pasted verbatim as seed context into two of the Claude sessions; cursor session `ba7a49f5`
produced a "5 homes" architecture proposal that was pasted into Claude session `90f13c6f` for
review. Disk-free deltas below are each session's own self-reported before/after — they are
**not additive** (sessions ran concurrently against shared disk state; several explicitly note
"the peer session already did X").

---

## 1. Claude Code — `beb3dbeb` (agent-infra) — "Agent-history storage retention"

Starting point: agentlogs.db 9.8 GiB, `~/.codex/sessions` 9.7 GiB, `~/.codex/state_5.sqlite`
5.5 GiB, `~/.claude/projects` 3.8 GiB. User's explicit brief: "prefer retention pruning plus
SQLite VACUUM, not blind deletion." Disk free at start: 16 GiB (96% used).

**Actions taken:**
- Snapshotted full 10.5 GB `agentlogs.db` to `/Volumes/2TBPNY`, verified integrity, compressed
  (`agentlogs-2026-07-14.db.zst`, ~1.9 GiB) — done BEFORE any destructive step.
- Ran retention prune on `agentlogs.db`: 0 rows deleted (DB legitimately holds only ~21 days at
  ~500 MB/day — confirmed this was correct behavior, not a bug); purged 216K orphaned
  `record_refs`. Result: 9.8 → 9.4 GiB.
- Dumped oversized `state_5.sqlite` thread columns (title/first_user_message/preview >10KB) as
  a compressed SQL backup to 2TBPNY (`threads-oversize-2026-07-14.sql.zst`) **before** touching
  them, backed up the whole DB to `/Volumes/2TBPNY/backups/codex-state/` (killed one stuck
  backup process, PID 38028, and its partial file), then truncated the three columns to 10K
  chars each + VACUUM: **5.5 GiB → 852 MB**.
- Archived `~/.codex/sessions` files >14 days old (12,246 files) to 2TBPNY — first time ever
  archived for codex: **9.7 GiB → ~5 GiB**.
- Archived `~/.claude/projects` files >14 days old (2,327 files) to 2TBPNY: **3.8 GiB → ~2 GiB**.
- Root-caused and fixed: `rm ~/.claude/logs` (a stray symlink to the USB stick, created Jul 11,
  had been silently spawn-killing all 11 agent-infra launchd jobs for 3 days). Reloaded/
  kickstarted all 11 jobs. Wrote incident memory `launchd-logs-symlink-spawn-failure`.
- Code/config changes committed: light-path prune (skip FTS-rebuild/VACUUM transaction entirely
  when the delete-plan is 0 rows — old path took >1h for a no-op, new path takes seconds; test
  in `tests/agentlogs/test_prune.py`), VACUUM now gated on freelist fraction, `LowPriorityIO:
  false` added to the `agentlogs-archive` plist (job had been running ~10x slower under
  launchd's default background I/O QoS), timestamped phase markers added to the archive log.
- Retired reclaim's competing nightly agentlogs prune (commit `9705f5f`) — it always deleted 0
  rows and had died mid-VACUUM the previous night on a full disk; `reclaim-rotate` is now a
  warn-only stub, its cron keeps only `uv cache prune`. Fixed a stale `reclaim rotate` hint
  (`709672d`).
- doctor.py updated to fail-loud on the two silent-death modes that caused this incident:
  spawn-failed launchd jobs and a stale snapshot series (`d6a8aa1`).
- Filed (not fixed here) a backlog item for ingest-side DB bloat: codex `message` events storing
  2.6 GB of duplicated whole-context text, `payload_json` 1.8 GB — explicitly deferred "until
  steady state hurts" (commit `cbe6e59`). **This got picked up the same day** in session
  `90f13c6f` below.
- Secondary ask ("what else can we optimize on this laptop?"): ran `reclaim`'s existing
  read-only survey; cleared CloudKit cache (5.3 GB) + 6,992 Python build-cache dirs + diagnostic
  logs (97 → 102 GiB free). Found a week-old orphaned daemon spare-process pair on an old binary
  (PID 4951/4958, ~250 MB) — confirmed not part of the live daemon pool, user approved ("ok
  do"), killed it.
- **Left for the user, not auto-executed:** `/Users/Shared/Previously Relocated Items 18`
  (11 GB, root-owned — gave exact command `sudo rm -rf '/Users/Shared/Previously Relocated
  Items 18'` or `reclaim sudo-items --yes`); two old agent-session PIDs (73719 at 2d19h, 96725
  at 17h) flagged to kill only if the user doesn't recognize them as intentional runs.

**Final state reported:** disk free **16 GiB (96%) → 99 GiB (76%)**.

**Decisions:** single retention owner going forward is the snapshot-gated weekly
`agentlogs-archive` job (Sun 03:30) for all four stores; snapshot rotation deliberately left
un-implemented (1.9 GB/week vs 296 GB free on the stick = ~3 years headroom, not worth building);
root-owned or ambiguous-owner items always surfaced to the user rather than auto-deleted.

---

## 2. Claude Code — `92e34fe1` (arc-agi) — ".claude worktrees 16.8 GiB"

Brief: "Fix this... don't regress (there's one codex working currently)." Biggest single reclaim
of the day.

**Actions taken:**
- Verified via `lsof` that the concurrently-running codex process's cwd was the **main**
  checkout (zero open files under `.claude/worktrees/`) before touching anything.
- Content-verified (not just patch-id) which of 14 worktrees' commits were already on `main`;
  for those genuinely ahead, created preserving branches (`worktree-agent-a52c…`,
  `worktree-agent-a9dc…`, `worktree-agent-a7a14…`) before removal. One held a genuinely unlanded
  `certificates` block — filed backlog row `pv01-certificate-block-merge` so it has a
  consumption path.
- Moved real content out before deleting: model-screen's 51M `screen_out/` recordings →
  `agent/recordings/model_screen/`, gave its detached HEAD a branch name.
- A hook blocked `rm` of a junk `data/data` symlink (pattern-matched a protected `data/` glob);
  let `git worktree remove` unlink it instead, verified main's real `data/` (957M) stayed intact.
- `git worktree remove --force` on all 14 + `git worktree prune` + removed empty
  `.claude/worktrees/.DS_Store` and the now-empty dir.
- **Result: 16.8 GiB freed**, disk went from ~0 to 16 GiB free. All `worktree-*` branches kept
  (refs only, zero disk cost).
- Extended the same pass to **publishing**: dropped a 311 MiB `.svelte-kit` build-output dir
  from a dirty worktree, but explicitly left the worktree itself (locked, dead-PID lock but 13
  real unmerged commits + 4 dirty files) for the user to merge, not delete.
- Deleted `arc-agi/.scratch/arc_alpha_sweep/repos` (3.6 GiB, 29 cloned public repos) — wrote
  `REPOS_MANIFEST.tsv` (name→remote→exact HEAD sha) FIRST, only deleted clones with both
  recorded, preserving reproducibility for two research memos.
- Deleted 5 dormant project venvs (substrate, arc-agi-2, anki, genomics-e2e-sim,
  genomics-control-plane-lab) ≈ 3.5 GiB — verified not hardlinked to the uv cache first, and
  verified `emb`/`llmx` CLIs (which live independently in `~/.local/share/uv/tools/`) still work.
- Deleted `ncbitaxon` extracted `.dmp` files (483 MiB; kept `taxdump.tar.gz`, which re-extracts
  them), `pi-install/node_modules`, ruff/pytest caches, substrate's clean worktree.
- **Moved (not deleted)** to `/Volumes/2TBPNY/backups/reclaim-2026-07-14/` (3.7 GiB total):
  `phenome/dist/claims_public.duckdb.jun13-prose-backup` (1.9 GiB, confirmed-retired KG),
  `phenome/results/dl_scores` (1.1 GiB, confirmed stale vs. live Jun-20 pipeline output),
  `agent-infra/artifacts/observe` (739 MiB, gitignored but rederivable from agentlogs).
- Killed a `uv cache prune` rather than pass `--force` when a codex session was using the cache
  — same call independently made in sessions `90f13c6f` and cursor `0cf51a6d`.
- Deleted two small stale files after confirming zero consumers: `phenome/indexed/
  todos.prev.duckdb` (3.5M — live `todos.duckdb` rebuilt same day) and
  `instagram_parsed.json.bak-20260623T093401` (524K) — ~4 MiB total.
- **Explicitly ruled out** `phenome/indexed/` (1.8 GiB) entirely — it's the ADR-0022 "principal"
  data layer (search index + DuckDBs + parsed source dumps phenome's live tools read), not a
  cache.
- **Explicitly left, with reasons:** `genomics/.claude/cache/source-epochs` (3.5 GiB —
  content-addressed store possibly bound to a genomics pipeline that had committed 10 min
  earlier), `~/.cache/uv` (8.4 GiB, blocked by active codex uv usage), `genomics-hookperf/
  paper_evidence` (762 MiB byte-duplicate of `genomics/paper_evidence` — **explicitly refused to
  symlink-dedupe it**: hookperf exists to measure hook/filesystem performance, so replacing a
  real tree with a symlink would contaminate the metric being measured), `genomics/
  T2D_pymcmc_seed42.txt` (523 MiB stray gitignored MCMC output in an actively-committing repo —
  not unilaterally deleted), `genomics/.git` (2.0 GiB gc candidate, skipped while repo is live).
- **Identified as real data, not junk:** `corpus` (8.9 GiB), `anki`/`anki-toolkit` (4.3 GiB,
  131 overlapping-but-not-identical files — no safe dedup without knowing canonical), `intel/
  research`+`analysis`.

**Final state reported:** disk free **16 GiB → 77 GiB**.

---

## 3. Claude Code — `90f13c6f` (agent-infra) — "Background size survey" → evolved into execution

Started by receiving the same survey numbers cursor session `0cf51a6d` had already produced
(worktrees 16.8G, phenome 5.5G, arc-agi/.scratch 3.9G, agentlogs.db 9.8G, codex/sessions 9.7G,
etc.), then reviewed a pasted "5 homes" architecture critique (source: cursor session
`ba7a49f5`, reviewed under standard "might be slop, be critical" framing — the review itself was
interrupted by the user before Claude's verdict text landed, so no captured verdict here), then
moved into actual execution.

**Actions taken:**
- genome-toolkit cleanup: deleted a superseded 2.8 GiB backup outright (`rm -f
  claims_public.jun24-backup.duckdb`), moved the live `claims_public.duckdb` + `sources` dir to
  external storage (291 GB free there), verified DB integrity post-move (48 tables open through
  the symlink). **genome-toolkit: 5.7 GiB → 134 MiB.**
- Found and fixed a major latent bug: `~/.claude/agentlogs.db-wal` had ballooned to ~4 GiB (a
  VACUUM-in-WAL-mode artifact) and never shrank because the indexer's long-lived connection
  blocked checkpointing. `PRAGMA wal_checkpoint(TRUNCATE)` → WAL down to 88 MiB, reclaiming ~5
  GiB (`~/.claude` 18G → 13G). Shipped a permanent fix: both `prune.py` and `compact.py` now end
  with `wal_checkpoint(TRUNCATE)` (committed).
- Root-caused the "15 GB of text" mystery: the codex adapter was storing the **entire pasted
  file content** as `text` on every `message` event — 53,771 rows averaging 50KB = 2.6 GiB of
  triplicated data (already on disk once, in raw JSONL once, now in the index a third time).
  Plus `payload_json` 1.8 GiB (write-only metadata) and a 1.46 GiB duplicate FTS index.
- Shipped an ingest-side fix: new shared `textcap.py` module (one cap definition used by both
  ingest and backfill — "identical output" is a pinned test) caps oversized `message`-kind text
  at head-4KB + tail-3KB. **Explicitly exempted `assistant_message` rows** after computing the
  tradeoff live on real numbers: capping them would save only 266 MiB (8% of the total win) but
  would destroy real model-output content agentlogs exists to search; capped only `user_message`
  (2,627 MiB) and `developer_message` (474 MiB).
- Wrote 78 tests, including one pinning the assistant-message exemption at both ingest and
  backfill paths.
- Dry-run: 80,401 rows, 3,370 MB → 555 MB (saves 2.8 GB). Applied live after waiting out lock
  contention **twice** rather than killing/forcing past the legitimate scheduled indexer job
  (chained wait+apply into one shell so no other job could grab the lock in the gap).
- `~/.cache/uv`: found a peer session (the arc-agi one, `92e34fe1`) had already pruned it from
  9.7G to 2.3M before this session got to it — corrected its own stale "20G of caches" estimate
  accordingly.
- Self-corrected an earlier "~6G of dormant venvs" estimate down to ~550 MB after actually
  checking commit dates (only `intel-harness` was truly cold).

**Decisions:** never force a busy uv cache or an active sqlite write-lock — wait for the
legitimate owner; a shared invariant (the text-cap threshold) gets ONE definition loaded by both
ingest and backfill, never restated.

---

## 4. Cursor — `0eb44903` (agent-infra project) — "Finder can't complete… Wolfram Player (Error -36)"

Opened on a recurring macOS Finder I/O error complaint; the diagnosis of the -36 error itself
wasn't captured in the extracted window, but the session clearly pivoted into a **Documents
folder reorganization** (likely as a side effect of investigating what Finder couldn't
read/write):

**Actions taken:**
- Found and fixed symlinks broken by an earlier Documents reorg: 8 hoelzl curated-photo
  symlinks + `~/semantic_index.jsonl`, repointed to their new paths; updated phenome docs that
  referenced the old paths (`hoelzl-haus/{README,floor-plan,curated/INDEX}.md`, `.claude/rules/
  data-sources.md`).
- Dissolved a redundant `personal/` subfolder inside `~/Documents` (user: "it's MY documents
  folder... so kinda stupid name") into domain folders: hoelzl → `official/property/hoelzl/`,
  Markus books/OCEAN/TOPIQ → `notes/self/`, SF event data → `notes/sf-2026/`, `alex.csv` →
  `archive/dating/`, questionnaire prompts → `medical/phenotype/`. Post-reorg top level:
  `archive/ context/ exports/ image-gen/ medical/ notes/ official/ reference/`.
- Identified `~/Projects/scripting` as obsolete (already gone locally, GitHub repo archived as a
  redirect stub) — live replacements already in `~/dotfiles/scripts` and `~/dotfiles/raycast`.
- Identified `~/Projects/cleanup_scripts_backup` (76K, no git, Aug 2025) as dead, superseded by
  `~/dotfiles/scripts/cleanup` — **recommended** delete/archive, did not auto-delete.
- Answered a CLI-architecture question with a firm recommendation: keep 3 separate layers by
  audience/blast-radius (personal machine scripts → `dotfiles`; cross-repo agent ops →
  `agent-infra` + `just`; domain-specific → that repo's own CLI) rather than one mega-CLI;
  explicitly placed `reclaim`/disk hygiene in `dotfiles`, not `agent-infra`.

---

## 5. Cursor — `0cf51a6d` (agent-infra project) — "Find things to save diskspace… just recs… parallelize"

**This is the upstream source of the survey numbers used as seed context in Claude sessions
`92e34fe1` and `90f13c6f` above** — ran first (12:47), recommendation-only per explicit user
instruction ("don't delete yet").

**Actions taken:**
- Parallel `du`-based survey (caches, dev artifacts, worktrees, project outputs, personal data,
  apps) at 4.5 GiB free / 99% used. Output included the safe-cleanup tier (uv cache 8.4G, Codex
  updater/runtime caches 2.8G+1.5G, Chrome 1.5G, Homebrew 1.2G, Telegram 0.85G, Playwright 0.52G,
  Trash 0.62G, Cursor cache 0.30G, misc 0.22G ≈ 18-20 GiB) separately from the high-value/
  higher-risk tier (worktrees 16.8G, genomics worktrees ~7G, phenome 5.5G, arc-agi/.scratch
  3.9G, rebuildable venvs, agent-infra 1.7G) and the agent-history stores (agentlogs.db 9.8G,
  codex/sessions 9.7G, state_5.sqlite 5.5G, claude/projects 3.8G) — explicitly flagged the last
  group as "likely partly duplicated... prefer retention pruning plus VACUUM, not blind
  deletion," the same framing the user then gave Claude session `beb3dbeb`.
- User: "do the safe cleanup for now" → executed **only** the safe tier: emptied Trash, cleared
  app/dev caches. First `uv cache clean` pass was a no-op (sandboxed shell redirected it to a
  temp cache); re-ran against the explicit real path. **Result: 4.5 → 12 GiB free (~7.5 GiB
  recovered).**
- Detected active UV/MCP/test processes holding the real 8.4 GiB uv cache and declined to force
  through them — left it for later.

---

## 6. Cursor — `ba7a49f5` (agent-infra project) — "Any better ideas of how my entire mac SSD and setup should be organized?"

**This session produced the "5 homes" proposal later pasted into Claude session `90f13c6f`.**

**Actions/recommendations:**
- Proposed a "5 homes, no more" model: `~/dotfiles` (machine config + personal scripts),
  `~/.local/bin` (PATH shims only, never source of truth), `~/Projects` (git repos only, not
  blobs), `~/.config` (XDG app config incl. `volumes.env`), `/Volumes/2TBPNY` (heavy/cold/
  regenerable). Verdict: existing structure is already right; the problem is "too many homes for
  the same job" plus hot-SSD-holding-cold-weight (Data volume was 87% used / 53 GB free at the
  time).
- Ran a `~/` root-dir cruft scan and recommended: delete `~/raycast` (empty shell — real scripts
  already in dotfiles), fold `~/scripts`'s one file (`keychain-keys.sh`) into dotfiles then
  delete `~/scripts`, drop `~/bin` (only held `plink2`+`vcf_subset`), delete `~/Support/Claude/`
  (empty config stub).
- Flagged fat cruft at `$HOME` root: `genomics-pii-scrub-backup.bundle` (824M),
  `tools/` (1.5G, whisper weights — belongs on the volume), `go/` (2.0G, mostly zoekt),
  `google-cloud-sdk/` (729M manual install), `syn2sr-deliverable-20260603/` (11M); plus dotfile
  cruft: `.claude_backup_Jan_2026` (408M), several `.claude.json.backup*`/`.bak*` (~3M),
  `.gemini`+`.gemini-bare` (~850M — two separate Gemini homes), `.embed-cli.db` (29M), ~15
  `.zcompdump.*` copies.
- Checked `.claude-science` (3.9G) before flagging it — confirmed it's a **real, separate**
  Claude Science app install (binaries + `.app` shims), explicitly kept, not cruft.
- User approved: "delete the cruft if certain, Fat cruft too." Session log excerpt ends
  mid-execution, re-requesting an approval card — **VERIFIED COMPLETE 16:58 by the integrating
  session**: all 11 named targets (~/go, ~/tools, ~/google-cloud-sdk, ~/raycast, ~/scripts,
  ~/bin, ~/Support, ~/.claude_backup_Jan_2026, ~/.gemini-bare, genomics-pii bundle,
  syn2sr-deliverable) are gone from disk (~6.3 GiB).

---

## LEARNABLE CLASSES

**Recurring — worth promoting into `reclaim` or a scheduled job:**

1. **Worktree pruning** (arc-agi 16.8 GiB — the single biggest reclaim of the day; publishing
   311 MiB `.svelte-kit`). Multiple repos independently accumulated dead `.claude/worktrees/`.
   A scheduled sweep (list → classify clean/dirty/already-on-main via content check, not
   patch-id → prune) across all of `~/Projects` would catch this before it reaches double-digit
   GiB. The safety pattern used today (verify via `lsof`/cwd that no live peer is inside the
   worktree; content-diff before assuming "already on main"; branch-before-remove for anything
   genuinely ahead) is exactly the logic such a job would need to encode.
2. **uv cache prune, but lock-aware.** Three independent sessions today (`90f13c6f`,
   `92e34fe1`, cursor `0cf51a6d`) each separately hit "cache in use by a peer, don't force" and
   made the same correct call. Worth codifying once as a `reclaim` policy (default non-forcing,
   retry-later) rather than re-deriving it per session.
3. **Superseded backup files sitting next to their live counterpart**
   (`claims_public.jun24-backup.duckdb` 2.8G, `phenome/dist/…jun13-prose-backup` 1.9G,
   `todos.prev.duckdb`, `instagram_parsed.json.bak-*`). A recurring pattern across repos — worth
   a `reclaim` check for `*backup*`/`*.bak-\d{8}*` files older than N days with a live sibling
   present.
4. **Dormant project venvs**, but only after checking last-commit date, not size alone — one
   session's first-pass estimate (6 GiB) was 10x too high until it actually checked commit
   recency (true figure ~550 MiB).
5. **`$HOME` root-dir cruft audit** (empty `~/raycast`, `~/scripts`, `~/bin`,
   `~/Support/Claude/`, stray installs like `google-cloud-sdk`, whisper weights outside the
   volume policy). Slow-accumulating but repeatable — worth a periodic `reclaim homedir-audit`
   rather than only surfacing when the disk is already critical.

**Already solved as standing infrastructure today — a later session must NOT re-propose these:**

- **"Build an agentlogs/codex retention job"** — now exists and was substantially hardened
  today: single weekly snapshot-gated `agentlogs-archive` launchd job owns all four stores;
  light-path no-op prune (seconds, not >1h); WAL truncation on every prune/compact; ingest-side
  text-capping (`textcap.py`) for the codex whole-context-duplication bug, with assistant-output
  explicitly exempted. Check `~/Projects/agent-infra/src/agentlogs/{prune,compact,textcap}.py`
  and the `com.agent-infra.agentlogs-archive` plist before proposing anything here again.
- **Symlink-deduping `genomics-hookperf/paper_evidence` against `genomics/paper_evidence`**
  (762 MiB, byte-identical) — explicitly reasoned through and rejected today: hookperf exists to
  measure filesystem/hook performance, so replacing its real tree with a symlink would
  contaminate the metric. A later session flagging this as a "duplicate" would be repeating a
  mistake already caught.

**Genuine one-offs (fixed permanently or resolved; not a class to build tooling around):**

- The `~/.claude/logs` → USB symlink that silently killed 11 launchd jobs for 3 days (a specific
  Jul-11 mistake, reverted; doctor.py now fail-louds on the general failure mode, which is the
  right level of fix — not a symlink-specific sweep).
- codex `state_5.sqlite`'s triplicated-column bug (same huge string stored 3x per thread row) —
  fixed at the source today; only recurs if codex reintroduces it upstream.
- The week-old orphaned daemon spare-process pair (PID 4951/4958) — daemons self-clean their
  spare pool; not a sweep target.
- `/Users/Shared/Previously Relocated Items 18` (11 GiB) — a one-time macOS migration/
  permission-repair artifact, sudo-gated, left for the user.
- The `~/Documents` `personal/` folder dissolution and hoelzl symlink fixes — genuine one-off
  personal reorganization.

**Cross-tool pattern worth noting explicitly:** Cursor sessions did the fast, low-risk recon and
safe-tier execution (parallel `du` survey, Trash + cache clearing, architecture brainstorming);
Claude Code sessions did the slower, higher-risk execution requiring verification (worktree
peer-safety checks, SQL-level DB surgery, manifest-before-delete, ingest-code fixes). The survey
numbers and the architecture proposal both flowed Cursor → Claude via user copy-paste, not any
automated handoff — if a shared "what's using disk right now" view is ever built, this is the
seam it would replace.
