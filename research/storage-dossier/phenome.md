# Storage Dossier: phenome

Repo: `/Users/alien/Projects/phenome`
Internal footprint: **6.3G** total, **105M** `.git`. `phenome/databases/` is a symlink to `/Volumes/2TBPNY/corpus/bio` and is excluded from this accounting (already off internal drive — that pattern is the model for the recs below).
Profiled: 2026-07-14. Read-only investigation, nothing moved or deleted.

## TOTAL & breakdown

| Chunk | Size | % of 6.3G |
|---|---|---|
| `mcp/` | 2.0G | 32% |
| `indexed/` | 1.7G | 27% |
| `data/` | 564M | 9% |
| `scripts/` | 275M | 4% |
| `.git` | 105M | 2% |
| everything else (`src/`, `docs/`, self-reports, etc.) | ~1.66G | 26% |

Within the four hotspots, the heavy sub-items:

- `mcp/.venv` 1.4G + `mcp/genomics-consumer/.venv` 630M = **2.0G is entirely two Python venvs** (this *is* all of `mcp/`).
- `indexed/`: `clippings_media/` 278M, `unified/` 226M (embeddings.npy 121M + entries.jsonl 105M), `healthkit.duckdb` 191M, `science_release.duckdb` 107M, `_embedding_cache_*.npy` 118M, `*_parsed.json` (gmail/takeout/claude/threads/photos/raycast/calendar) ~254M, `overlay_markus.duckdb` 27M, `pgx.duckdb` 19M, `medical_data.duckdb` 7.0M, `todos.duckdb` 3.5M.
- `data/`: `onsides/` 326M, `pharmvar_cache/` 175M, `ctd/` 40M, `signor_human.tsv` 19M.
- `scripts/`: `scripts/data/notes-snapshot-2026-03-08/` **272M** (of scripts' 275M total — `scripts/` itself is basically negligible, it's a stray data snapshot sitting under it).

## Per-chunk verdict table

| Chunk | Size | Class | Evidence | Action | GB saved |
|---|---|---|---|---|---|
| `mcp/.venv` | 1.4G | (a) regenerable | `mcp/pyproject.toml` + `mcp/uv.lock` present; `git check-ignore -v mcp/.venv` → `.gitignore:8:.venv/` | delete, `uv sync` on demand | 1.4G |
| `mcp/genomics-consumer/.venv` | 630M | (a) regenerable + duplicate of above | `mcp/genomics-consumer/pyproject.toml` + `uv.lock` present, gitignored same as above. Package-list diff shows **140 of 146** top-level packages overlap with `mcp/.venv` (pyarrow, duckdb, onnxruntime, cryptography, pymupdf, cv2 all present in both). Confirmed *not* hardlinked — `libarrow.2400.dylib` has different inodes in each venv (124063783 vs 124064810), each holding a full independent 45.7M copy. | delete, `uv sync` on demand; longer-term collapse to one shared `uv` workspace/venv (or set `UV_LINK_MODE=hardlink` against a shared cache) to stop paying for pyarrow/duckdb/onnxruntime/torch twice | 630M now, ~600M recurring if de-duplicated |
| `indexed/unified/` (embeddings.npy + entries.jsonl) | 226M | (a) regenerable | `justfile:38` `generate-embeddings: uv run python3 scripts/connectors/generate_unified_embeddings.py`; script header: "Output: indexed/unified/ (split format)" | keep locally (hot path for search) but low priority; regenerate-on-demand is viable | 226M if evicted |
| `indexed/_embedding_cache_*.npy/.json` | 118M | (a) regenerable cache | `generate_unified_embeddings.py:865-913` — explicit incremental cache (`_embedding_cache_{slug}_vectors.npy`, legacy fallback paths) | delete freely, rebuilds incrementally next run | 118M |
| `indexed/clippings_media/` | 278M | (c) gitignored duplicate copy | `scripts/connectors/parse_clippings.py:15-38` — `SOURCE_MEDIA = ~/Documents/context/media`; `LOCAL_MEDIA = indexed/clippings_media`; sync step does `shutil.copy2(src, LOCAL_MEDIA / src.name)`. Source of truth lives elsewhere on the internal drive already. | symlink `indexed/clippings_media` → `~/Documents/context/media` instead of copying (dedupe, same pattern as `databases/`) | 278M |
| `indexed/*_parsed.json` (gmail/takeout/claude/threads/photos/raycast/calendar, ~254M) | 254M | (a)/(c) regenerable from external exports | Consumed by `scripts/connectors/extract_topics.py`, `generate_unified_embeddings.py`, `scripts/derived/derive_*`; produced by `./phenome update` (`justfile:32` "Full incremental update (snapshot, parse, regenerate embeddings)") | keep — actively used working cache; not a priority target unless raw source exports are also retained locally | n/a |
| `indexed/science_release.duckdb` | 107M | (a) regenerable | `scripts/tools/gen_db_catalogs.py:36` "Clean-room extracted science prose release (PHI-free, shippable)"; built by `kg_clean_room_build` (referenced in `scripts/tools/acquire_genomics_citations.py:5` and `scripts/hooks/pretool-regen-config-lever.sh:30`) | delete + rebuild on demand | 107M |
| `indexed/todos.duckdb` | 3.5M | (a) explicitly rebuildable view | `justfile:225-230`: "Rebuild indexed/todos.duckdb from docs/todos.md ... Markdown stays canonical; DB is the rebuildable view" | trivial, not worth touching | — |
| `indexed/healthkit.duckdb` | 191M | (b)/(d) re-derivable **only if** raw export retained | `justfile:345-348` `healthkit-ingest export="": uv run python -m phenome.healthkit.ingest {{export}}` — ingests an Apple Health `export.zip`. If that zip isn't kept elsewhere, this DB is the only copy of parsed history. | verify a source `export.zip` exists before treating as disposable; do not delete blind | conditional |
| `indexed/medical_data.duckdb` | 7.0M | (d) irreplaceable primary data | `gen_db_catalogs.py:32` "Subject-scoped PHI — labs, medications, conditions (**append-only** events)" — not a build output of any script found | leave alone (too small to matter anyway) | — |
| `indexed/pgx.duckdb`, `overlay_markus.duckdb` | 46M | (a) likely rebuildable graph builds | Fed by `scripts/connectors/fetch_pharmvar.py`, `seed_pgx_graph.py`, `scripts/agents/review_pending_edges.py`/`biograph.py` promote flow | low priority, small | — |
| `data/onsides/` | 326M | (b) re-downloadable | `scripts/connectors/load_onsides.py:13,41-42`: "Downloads the OnSIDES v3.1.0 release zip (~313MB)" from `https://github.com/tatonetti-lab/onsides/releases/download/v3.1.0/onsides-v3.1.0.zip`; `git check-ignore -v data` → `.gitignore:15:data/` | delete cache, re-download on demand | 326M |
| `data/pharmvar_cache/` | 175M | (b) re-downloadable | `scripts/connectors/fetch_pharmvar.py:43,66-67`: `CACHE = PHENOME_ROOT / "data" / "pharmvar_cache"  # raw ZIPs (gitignored data/)`, `_DOWNLOAD_URL = "https://www.pharmvar.org/get-download-file"` | delete cache, re-fetch on demand | 175M |
| `data/ctd/`, `data/signor_human.tsv` | 59M | (b) re-downloadable | `scripts/connectors/load_ctd.py` (CTD loader); SIGNOR is a public external DB | delete/re-fetch on demand | 59M |
| `scripts/data/notes-snapshot-2026-03-08/` | **272M** | (c) stray/orphaned gitignored artifact | `git check-ignore -v scripts/data` → `.gitignore:15:data/` (generic `data/` pattern also catches this misplaced dir). `scripts/connectors/snapshot_notes.py:3,16` says the *intended* destination is `~/Documents/exports/snapshots/notes-snapshot-YYYY-MM-DD/`, not `scripts/data/`. Sibling snapshot dirs at the *correct* location (`data/notes-snapshot-2026-06-07`, `data/notes-snapshot-2026-01-09`, etc.) are all 0B (rotated/cleared), while this one under `scripts/data/` is a full 1,330-file copy of `~/Documents/notes`, dated 4+ months ago (today 2026-07-14) and never cleaned up. | delete — it's a stale duplicate of a live external source (`~/Documents/notes`), sitting in the wrong place entirely by the script's own contract | 272M |

## Top 3 ranked recommendations

1. **Delete `scripts/data/notes-snapshot-2026-03-08/` (272M).** This is not even supposed to live in the repo per `snapshot_notes.py`'s own destination logic (`~/Documents/exports/snapshots/...`); it's a stale, gitignored, orphaned duplicate of `~/Documents/notes` from four months ago, sitting next to a family of correctly-rotated 0-byte snapshot dirs. Zero functionality lost — highest-confidence, lowest-risk win, and it single-handedly explains why "`scripts/`" looked like a 275M code directory.

2. **Delete-and-regenerate the two `mcp/` venvs (2.0G) and stop duplicating them.** Both are gitignored, both have `pyproject.toml`+`uv.lock`, and `mcp/genomics-consumer/.venv` duplicates 140/146 packages already in `mcp/.venv` (verified via non-hardlinked, separate-inode copies of `libarrow.2400.dylib`, `_duckdb.cpython-313-darwin.so`, `onnxruntime`, etc.). Regenerate via `uv sync` when the MCP server actually needs to run; longer-term, collapse the two into one shared `uv` workspace/venv to permanently stop paying ~600M in duplicated binary deps (torch/pyarrow/duckdb/onnxruntime/cv2/pymupdf).

3. **Symlink `indexed/clippings_media/` (278M) to its real source `~/Documents/context/media`, and clear `data/` re-downloadable caches (onsides 326M + pharmvar_cache 175M + ctd/signor 59M = 560M).** `parse_clippings.py` explicitly `shutil.copy2`s from `~/Documents/context/media` instead of linking, so this repo carries a needless full duplicate — same fix pattern the repo already uses for `databases/`. Separately, `data/` is 100% gitignored external-source cache (OnSIDES GitHub release, PharmVar zips, CTD/SIGNOR downloads) with working downloader scripts for each — safe to purge and re-fetch on demand rather than carry ~560M of re-downloadable cache permanently.

Combined, items 1–3 identify **~3.1G of reducible internal footprint out of 6.3G** without any loss of functionality (regenerate-on-demand or dedupe-via-symlink for everything flagged). `indexed/medical_data.duckdb` (PHI, append-only, no build script found) and `indexed/healthkit.duckdb` (re-derivable only if the source Apple Health export.zip is separately retained) were explicitly excluded from action — treat as class (d)/conditional and leave alone.
