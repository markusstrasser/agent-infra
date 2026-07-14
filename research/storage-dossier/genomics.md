# Storage Dossier: genomics

Repo: `/Users/alien/Projects/genomics` — 5.1G total internal. `.git` = 1.1G (`objects/pack` = 846 MiB across two packs; multi-pack-index present).
`databases/` is a symlink to `/Volumes/2TBPNY/genomics-databases` — excluded from all counts (per instructions).
Remote: `origin = git@github.com:markusstrasser/genomics.git` (fetch+push). Solo committer (`strasser.ms@gmail.com` only, verified via `git log --format='%ae' | sort -u`). **7 active git worktrees** (5 detached under `/private/tmp/genomics-*`, 1 under `~/.codex/worktrees/`, 1 main) and ~20 local branches — any history rewrite must coordinate all of these, not just "solo dev = easy."

## TOTAL & breakdown

| Chunk | Size | Tracked in git? |
|---|---|---|
| `.git` | 1.1G (846M pack) | — |
| `paper_evidence/` | 763M | yes, 4777 files |
| `data/` | 550M | **no** (gitignored, 0 files) |
| `tmp/` | 289M | **no** (gitignored, 0 files) |
| `vendors/` | 227M | **no** (gitignored, 0 files) |
| `docs/` | 225M | yes, 2901 files |

---

## 1) GIT HISTORY BLOAT — key finding: it's NOT dead-blob rot, it's live PDF tracking

**Top raw blobs by size are misleading.** The single largest-by-raw-size historical file is `config/claim_events.ndjson` — 117 distinct versions, sizes up to 37,770,545 bytes, summing to **2.02 GiB of raw historical content**. Naively this looks like the #1 bloat source. It is not.

**Packed-size reality (via `git verify-pack -v` joined to blob paths, both pack files):**

| Path prefix | Packed bytes in history | % of 880MB total |
|---|---|---|
| `paper_evidence/` | 673,751,171 (673.8 MB) | **76.5%** |
| `docs/` | 162,593,122 (162.6 MB) | **18.5%** |
| `config/` (incl. claim_events.ndjson, claim_registry.json, etc.) | 12,308,847 (12.3 MB) | 1.4% |
| `scripts/` | 10,341,376 | 1.2% |
| everything else | ~21MB | 2.4% |

**Why:** `config/claim_events.ndjson` is append-only NDJSON — each of its 117 historical versions is mostly a superset of the prior one, so git's delta compression crushes it to **~4.17 MB packed total across all 117 versions** (verified: joined the 117 blob SHAs against `verify-pack` column 4). It is genuinely dead weight (untracked since commit `5b3cabf4b` on 2026-07-09, "Stop tracking claim_events.ndjson — local event log only... Exceeds GitHub 100MB") but reclaiming it only buys ~4MB, not 2GB. **Not worth a standalone rewrite.**

The real weight is **PDF binaries** — `paper_evidence/*/paper.pdf` (already-compressed binary, doesn't delta) and `docs/research/sbayes-deepdive-2026-06-13/citation_fulltext/*/paper.pdf` (26 PDFs, 170M of that folder's 175M). These are **currently tracked and currently present** in the working tree — not orphaned/deleted files sitting dead in history. So this isn't a "purge garbage" situation, it's a "you're git-tracking large regeneratable binary assets" situation.

Top packed objects (sample, `SHA blob rawsize packedsize path`):
```
915c969e  12,343,939 → 11,063,848  paper_evidence/pmid_31745548/paper.pdf
b812b2fb  10,769,556 → 10,533,826  paper_evidence/doi_10.1016_j.ajhg.2019.09.008/paper.pdf
e5e96ace   6,660,387 →  6,115,601  paper_evidence/doi_10.1038_s41588-024-01704-y/paper.pdf
1799ee7e   5,520,839 →  4,516,553  docs/research/sbayes-deepdive-2026-06-13/citation_fulltext/doi_10_1038_s41588_024_01792_w/paper.pdf
23991f6e  37,058,011 →  4,200,400  config/claim_events.ndjson  (largest single claim_events version — even this compresses 8.8x)
```

**Reclaimable estimate:** ~836 MB of the 846 MB pack (≈99%) is the `paper_evidence/` + `docs/research/*/citation_fulltext/` PDF corpus + the trivial claim_events.ndjson tail. Rewriting history to strip these paths would shrink `.git` from 1.1G to roughly **60–100 MB**.

**Evidence these PDFs are regenerable (class b):** `scripts/build_source_paper_bundle.py` materializes `paper_evidence/<source_slug>/` from `--doi`/`--pmid`/`--pdf` args against the event-backed source registry; `scripts/fetch_scihub_pdf.py` fetches PDFs directly; `scripts/citation_context_refresh.py` / `scripts/backfill_citation_context.py` populate the `docs/research/*/citation_fulltext/` bundles. Source identifiers (DOI/PMID) persist in `config/source_registry.json`, so the fetch is re-runnable, not a re-derivation from nothing.

**Rewrite risk / coordination:**
- Remote exists (GitHub) → any rewrite requires `push --force` and is a breaking history change for anyone who has cloned/fetched.
- Solo committer, but **7 live worktrees** (`git worktree list`: 5 under `/private/tmp/genomics-*`, 1 under `~/.codex/worktrees/genomics-donor-bundle-*`, all on detached HEADs — these are active agent sessions) and ~20 local branches (`feat/*`, `worktree-agent-*`, `donor-kg-tail`, etc.) all reference pre-rewrite commit SHAs. A rewrite orphans every one of them; each worktree needs teardown/recreate and each branch needs re-basing or abandoning.
- There's already a `backup/pre-lfs-claim-events-20260709` branch, evidence the operator has done exactly this kind of surgery once before (for claim_events.ndjson specifically, not yet for the PDFs).

**Exact command (NOT run — investigation only; test on a fresh `--mirror` clone first):**
```bash
git filter-repo --path paper_evidence \
  --path-glob 'docs/research/*/citation_fulltext/*.pdf' \
  --path config/claim_events.ndjson \
  --invert-paths --force
# then: re-add paper_evidence/ and docs/research/*/citation_fulltext/ to .gitignore,
# restore the PDFs from the pre-rewrite backup/clone onto disk (filter-repo also
# resets the working copy), recreate all 7 worktrees, force-push, and have every
# worktree-agent branch rebase or get abandoned.
```

---

## 2) WORKING-TREE DATA

| Chunk | Size | Class | Evidence | Action | GB saved |
|---|---|---|---|---|---|
| `data/knowledge/cost_calibration.duckdb` | **482M** | a (regenerable diagnostic log) | `scripts/knowledge/cost_oracle.py`: `CREATE TABLE IF NOT EXISTS cost_calibration`, docstring says it's a per-execution calibration log "so operators can see drift." Queried directly: **1,901 rows** in a 482MB file — `PRAGMA database_size` shows 1,928 total blocks / 1,926 used @ 256KB/block. This is DuckDB write-amplification bloat (no VACUUM/CHECKPOINT), not real data — 1901 small scalar rows (VARCHAR/INT/DOUBLE columns) should be low-single-digit MB. | `VACUUM` in place, or delete and let `CostOracle` recreate it (`CREATE TABLE IF NOT EXISTS`) — zero data-loss risk either way since it's a diagnostic log | **~477M** |
| `paper_evidence/` | 763M | b (downloadable) | `scripts/build_source_paper_bundle.py`, `scripts/fetch_scihub_pdf.py` — materialize from DOI/PMID against `config/source_registry.json` | Untrack from git (see §1) going forward; keep as local gitignored cache or relocate off internal disk (same pattern as `databases/` symlink to `/Volumes/2TBPNY`) | 763M off internal disk if relocated; ~674M off `.git` if history rewritten |
| `docs/research/sbayes-deepdive-2026-06-13/citation_fulltext/` | 170M (of docs/research's 175M) | b (downloadable) | Same fetch pipeline (`citation_context_refresh.py`, `backfill_citation_context.py`); 26 PDFs, 570 tracked files total in that folder | Same as above | ~150M off `.git` if history rewritten |
| `tmp/` | 289M | c (gitignored scratch — verified `git check-ignore -v tmp` → `.gitignore:116`) | `tmp/control-plane-postgres/` (123M, has `pgdata`) + `tmp/control_plane_postgres/` (66M, has `data` — near-duplicate name, likely a stale second copy) = local Postgres data dirs; `tmp/syn2sr_modal/` (98M) = `syn2sr.primary_small_variants.vcf.gz` + index, clearly a Modal-job download (filename literally `syn2sr_modal`) | Safe to delete entirely — 0 files tracked, ephemeral local dev/scratch state, both postgres dirs and the VCF are regenerable | 289M, **zero git impact** (already untracked) |
| `vendors/PreMode/` | 222M (of vendors' 227M) | b (downloadable) | Has `download.data.sh` at its root, no nested `.git` — a vendored model checkout with its own fetch script | Already gitignored (0 tracked files) — re-fetchable via `download.data.sh` if ever deleted; low priority since it costs nothing in `.git` | up to 222M local disk only, zero git impact |
| `data/knowledge/knowledge.duckdb` | 25M | d (primary working state) | Actively written by `compute_verification_axes.py`, `drain_rich.py`, `compute_support_state.py` etc. | Leave alone | 0 |

---

## Top 3 ranked recommendations

1. **`VACUUM` (or delete) `data/knowledge/cost_calibration.duckdb`** — 482M → ~5M for a 1,901-row diagnostic log. Zero risk, already gitignored, no git action needed, highest ROI-per-effort in the whole dossier.
2. **Delete `tmp/` contents** (289M) — postgres scratch data dirs + one Modal-downloaded VCF, already untracked, zero git impact, pure disk hygiene.
3. **Stop git-tracking `paper_evidence/` + `docs/research/*/citation_fulltext/*.pdf`** — 76.5%+18.5% ≈ 95% of the 846MB pack is PDFs that are regenerable via existing fetch scripts (`build_source_paper_bundle.py`, `fetch_scihub_pdf.py`, `citation_context_refresh.py`). This is the one that actually shrinks `.git` (1.1G → ~60-100MB) but requires a coordinated `git filter-repo` rewrite + force-push + rebuilding all 7 active worktrees — schedule deliberately, don't do it opportunistically. The `config/claim_events.ndjson` dead history (2.02 GiB raw / ~4MB packed) can ride along in the same rewrite for free but isn't worth a rewrite on its own.
