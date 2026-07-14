---
title: Cross-repo storage-cost dossier — same functionality, less disk
date: 2026-07-14
status: active
tags: [storage, hygiene, cross-repo, offload]
---

# Storage-cost dossier — reduce footprint, keep full functionality

Scope: the big repos under `~/Projects` (9 lanes: 7 repo-profiler subagents + gpt-5.6-luna
strategy + grok-4.5 genomics review — grok returned "unavailable", covered by the Claude lane).
Machine-wide cache/venv/`__pycache__`/HF/uv hygiene is **already owned by the `reclaim` CLI**
(`~/.local/bin/reclaim`, updated today) — this dossier is the **repo-structural** layer it
doesn't touch. Per-repo detail: `research/storage-dossier/<repo>.md`.

Boot disk is **not** under pressure (175 GiB free of 460). `/Volumes/2TBPNY` external SSD is at
85% (294 GiB free). So nothing here is urgent — it's about stopping accretion and banking the
free wins.

## The one-line finding

The two problem classes are **working-tree data bloat** (fix = symlink-to-external / regenerate /
fetch-script) and **git-history blob bloat** (fix = `filter-repo` + gc). The already-symlinked
`databases/` in genomics & phenome is the template — most repos just haven't applied it
consistently, and several are sitting on **pure duplicate/write-amp waste** that costs nothing to
reclaim.

## Decision policy — default disposition per artifact class

| Class | Default | The one test that decides |
|---|---|---|
| Derived index (`.duckdb`/`.sqlite`) | symlink to external; keep tiny manifest local | clean-checkout rebuild recipe reproduces schema + row counts + checksum |
| Public reference data | symlink external (or fetch-script-only) | fetch script reproduces exact bytes without creds/fragile URL |
| Extracted-paper corpus (PDF→text) | shared content-addressed store; repo keeps manifest + symlink | given `(pdf_hash, extractor_version)` the output reproduces & verifies |
| Service/account export | external, compressed, immutable | restore one export into its consumer and it parses |
| Git-history blob bloat | history rewrite + local gc | `filter-repo --analyze` proves the blobs are unreachable/regenerable |
| Vendored dep / benchmark env | externalize; fetch-script only if pinned install proven | fresh env from lockfile/commit passes tests without network assumptions |

Rule: externalize artifact **trees**, never whole repos. Keep source + manifests + recipes local;
symlink only `data/`, `indexed/`, `reference/`, `exports/`, `vendor/`, `crowdanki/`. Never symlink
`.git`. Make a missing external mount **fail loud**, not silently rebuild or read stale.

## Cross-repo leverage plays (most GB-per-effort, generalize across repos)

1. **Standardize `/Volumes/2TBPNY/projects-offload/<repo>/<class>/` + repo-local symlink.** Already
   in use (genomics/phenome `databases/`, arc-agi `vendor/`, intel's ~390 dataset dirs). Extending
   it to the stragglers (anki `crowdanki/`, intel `substacks/`+`datasets/`, personal `indexed/`)
   banks **~10 GB** with near-zero semantic risk.
2. **One shared content-addressed paper store.** corpus holds **2,581 PDFs / 4.26 GB**; genomics
   tracks ~150 more *in git*; intel scrapes substacks. Store PDFs by SHA-256, extracted output by
   `(pdf_hash, extractor_version)`, each repo keeps a DOI→hash manifest. Dedups the overlap and —
   critically — gets the genomics PDFs **out of git history**.
3. **A pre-commit / gitignore guard against the next 10 GB.** intel is *actively* growing its pack
   by committing churning logs every day; genomics tracks regenerable PDFs. A shared gitignore
   template + a large-generated-file pre-commit reject stops recurrence across all repos.
4. **Regeneration knowledge lives in manifests, not prose.** Every deletable artifact needs
   source-URL/accession + version + checksum + build command tracked in git, so "delete and
   refetch" is safe. corpus/evals already do this ("track the generator, not the output"); make it
   the standard.

## Per-repo ranked reclaim (internal drive, functionality preserved)

| Repo | Reclaimable | Headline move(s) | Risk |
|---|---:|---|---|
| **corpus** | ~7.5G of 9.0G | delete+refetch PDFs (4.26G) & reparse `parsed.*/` (1.26G, ~$0.01/PDF); delete reference raw dupes (2.0G — zip already on 2TBPNY) | low; **fix stalled ledger-commit job first** |
| **phenome** | ~3.1G of 6.3G | delete misplaced `scripts/…/notes-snapshot` (272M); dedupe+regen two mcp/ uv venvs (2.0G, 140/146 pkgs dup); symlink clippings_media + purge data/ caches (838M) | low |
| **anki(+mechinterp)** | ~4.65G | symlink `crowdanki/` (4.2G — gitignored export cache, SoT is live Anki collection); symlink/refetch diagrams (378M); regen mechinterp checkpoints+anim (97M) | low |
| **arc-agi(+causal)** | ~1.9G | purge `data/agi3/*` except holdout_ledger.jsonl (0.84G, gitignore-documented rederivable); drop `arc-interactive/.venv` (0.71G); clear kaggle recordings + .scratch (0.29G) | low; causal-recovery is a **live worktree — leave it** |
| **intel(+evals)** | ~2.3G | evals: refetch public benchmarks (0.77G, add `fetch_longmemeval.py`); intel: symlink prices+datasets+substacks stragglers (1.3G); delete `theses.prev.duckdb` (54M); gitignore+rewrite churning logs | low |
| **genomics** | ~766M now + ~1G git | **VACUUM `cost_calibration.duckdb` (477M→5M, write-amp not data)**; delete `tmp/` (289M scratch); history-rewrite the tracked PDFs (.git 1.1G→~80M) | VACUUM/tmp trivial; rewrite = coordinated |
| **personal(+publishing)** | ~3.4G | relocate `exports/` + `indexed/` to 2TBPNY (~3.2G); delete stale twitter backup (167M); publishing history-rewrite dead museum-JPEGs (~230M) | low |

## Git-history rewrite playbook (genomics + publishing only)

Standard safe path: mirror-backup → in a disposable clone `git filter-repo --analyze` → strip
**by blob-id / path** (not by size — size-stripping also nukes live large files) → run tests +
verify tree/tags → force-push → collaborators reclone → expire reflogs + gc.

- **publishing** — cleanest case: **227 MiB of genuinely dead blobs** (full-res museum JPEGs
  orphaned when commits `85d2edd`/`2dc55c8` downscaled them in place; `node_modules` was never
  committed). Use `filter-repo --strip-blobs-with-ids <computed-dead-id-list>`. GitHub remote, solo
  author → low coordination. Reclaims ~220–260 MiB of the 481 MiB `.git`.
- **genomics** — **not** a dead-blob case (the scary-looking `claim_events.ndjson`, 2 GiB raw
  across 117 versions, delta-compresses to ~4 MB). The 846 MiB pack is **95% live-tracked
  regenerable PDFs** (`paper_evidence/` 674 MB + `citation_fulltext/` 163 MB). Rewrite strips those
  paths → `.git` 1.1G→~60–100 MB, but needs coordination of **7 live worktrees + ~20 branches +
  force-push**. Schedule deliberately; pair with gitignoring the PDF trees so it can't recur.

## Do NOT delete-and-regenerate (the false-economy traps)

- **corpus ledger text** (`annotations.jsonl`/`metadata.json`, ~1.2G) — the belief-change audit
  trail; SCHEMA.md requires local POSIX. Irreplaceable.
- **arc-agi `holdout_ledger.jsonl`** — paid Modal runs, append-only, not rederivable (the repo's
  own gitignore singles it out).
- **intel `data/` (ibkr flex) + personal `snapshots/` (916M)** — broker/account state that is
  retention-limited or gone once the source rotates.
- **substacks / chatgpt+claude exports** — auth-gated; re-scrape/re-export is lossy and slow.
  Externalize+compress, don't delete.
- **personal `indexed/`** — rebuildable but costs ~$27 of Gemini embeddings; **relocate, don't
  regenerate.**

## Two operational caveats surfaced (fix before acting)

1. **corpus ledger-commit launchd job is STALLED** — last commit 2026-06-26 (18 days), 89% of
   source dirs untracked. `metadata.json.pdf_sha256` is the *only* record of what to refetch, so do
   **not** bulk-delete corpus PDFs until `com.agent-infra.corpus-ledger-commit` is healthy again.
2. **genomics history rewrite** must tear down/recreate all 7 active worktrees; a prior
   `backup/pre-lfs-claim-events-20260709` branch shows this surgery has been done once before.
