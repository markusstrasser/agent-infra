---
title: Storage dossier — arc-agi + arc-agi-causal-recovery
date: 2026-07-14
status: active
---

[UNVERIFIED] Compiled from read-only agent; re-verify before acting.

# arc-agi (3.8G local) + arc-agi-causal-recovery (1.1G)

## Brief corrections (evidence-based)
1. **vendor/ (1.2G) is ALREADY a symlink** → `/Volumes/2TBPNY/projects-offload/arc-agi/vendor` (gitignored). Zero local bytes, zero further to gain.
2. **arc-agi-causal-recovery is a live git WORKTREE of arc-agi** (`.git` = 77-byte pointer, shared object store), commits from TODAY 17:43 — NOT stale, NOT wholesale-archivable (would need `git worktree move`).
3. Prunable dead worktree: `/private/tmp/arc-agi-direct-table-recovery` → `git worktree prune` (metadata only).

## arc-agi verdicts

| Chunk | Size | Class | Evidence | Action | GB |
|---|---|---|---|---|---|
| data/agi3/* (duck_sft 847M) | 863M | (a) regenerable | `.gitignore:34` "AGI-3 proxy loop — derived/rederivable"; explicit `!data/agi3/holdout_ledger.jsonl` exception (paid Modal runs, NOT rederivable); `git ls-files data/agi3` = 1 file | delete/offload all except holdout_ledger.jsonl; regen via loop/RESULTS.md | ~0.84 |
| external_envs/arc-interactive/.venv | 712M | (b) rebuildable | own `uv.lock`; `git remote` = github arc-interactive; gitignored | delete nested .venv, `uv sync` on demand (<2min) | 0.71 |
| agent/kaggle/recordings | 153M | (c) untracked working data | `git ls-files`=0; raw Kaggle session recordings, no regen script | verify not sole submission record, then archive/delete | 0.15 |
| .scratch/ (arxiv caches) | 145M | (c) re-fetchable caches | arxiv_*.jsonl metadata snapshots | low-risk delete/archive | 0.14 |
| .venv root + agent/.venv | 1.35G | reclaim scope | uv.lock present, regenerable; uv cache CoW-dedups | defer to reclaim | n/a |
| .git (162M/96MiB pack) | 162M | moderate history bloat | 27,245 objects in-pack | not assessed this pass (would need gc/rewrite) | — |

## arc-agi-causal-recovery
997M .venv (reclaim scope) + git-tracked non-duplicative worktree content (experiments/learning/research/data, identical tracked-file counts to arc-agi root = shared store). **Nothing to reclaim; do not archive — mid-experiment.**

## Top 3
1. **Purge/offload arc-agi/data/agi3/* except holdout_ledger.jsonl (~0.84G)** — highest confidence, repo's own gitignore calls it rederivable and singles out the one non-rederivable file.
2. **Delete external_envs/arc-interactive/.venv (0.71G)** — rebuild via uv sync; treat external_envs/ as re-clonable.
3. **Confirm/clear agent/kaggle/recordings (0.15G) + .scratch/ (0.14G)**; leave venvs to reclaim; do NOT touch causal-recovery worktree.

Realistic reclaimable (non-venv): **~1.9G** of arc-agi; ~0 from causal-recovery.
