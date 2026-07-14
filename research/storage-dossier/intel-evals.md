---
title: Storage dossier — intel + evals
date: 2026-07-14
status: active
---

[UNVERIFIED] Compiled from read-only agent; re-verify figures/commands before acting.

# intel (4.9G, .git 226M / 84MiB pack — actively growing) + evals (1.3G, .git 17M no bloat)

## intel breakdown
analysis/ 989M · intel/ 852M (indexed/ 429M, data/ 423M) · research/ 774M (substacks/ 686M) · datasets/ 608M (~390/410 entries ALREADY symlinked to 2TBPNY) · logs/ 40M (gitignored)

| Chunk | Size | Class | Evidence | Action | GB |
|---|---|---|---|---|---|
| intel git-history churn: `analysis/_logs/claim_graph_imports.jsonl` (8× @ ~19-21M) + `analysis/research/*_substack_source_work_queue.csv` (27× @ ~9.5M) | drives 84MiB pack | (c) tracked churning logs, still at HEAD, growing daily | `git rev-list --objects --all` top blobs; `git ls-files` confirms tracked | **gitignore both + filter-repo history rewrite** | ~0.15-0.2 |
| datasets/prices/ (local straggler) | 256M | (b) re-downloadable | `tools/download_prices.py`; watchlist_prices.csv 132M cache | symlink to 2TBPNY | 0.25 |
| datasets/{claims,sec_form4,sec_xbrl,phmsa,cms_*,fda_*} local | ~352M | (b) re-downloadable | matching `tools/download_*.py`; siblings already symlinked | symlink to 2TBPNY | 0.35 |
| research/substacks/ | 686M | (b/c) scraped auth-gated | `tools/substack_scraper.py` + daily launchd; re-scrape lossy/slow | symlink to 2TBPNY (don't delete) | 0.68 |
| indexed/theses.prev.duckdb | 54M | (a) stale backup | `tools/theses/rebuild.py` atomic-rename leaves it; DB is derivation, md+jsonl canonical | delete now | 0.054 |
| tools/bin/nordic-registry-mcp-server (17M) + .basedpyright/baseline.json (18M) in history | — | (c) accidental committed artifacts | blob scan, tracked | rm from history if regenerable | ~0.03 |
| intel/data/ (ibkr flex) | 423M | (d) primary broker data | broker retention-limited | symlink only if cold, don't delete | (0.4 if offloaded) |

## evals breakdown
data/ 468M (raw/ 445M) · longmemeval_retrieval/data/ 322M · .venv 455M (reclaim)

| Chunk | Size | Class | Evidence | Action | GB |
|---|---|---|---|---|---|
| data/raw/* (averitec, scifact, hover, feverous, gdpval…) | 445M | (b) public benchmarks, gitignored | `scripts/fetch_claim_benchmarks.py` + `manifests/download_receipts.json` (HF repo_ids); "generator not output" pattern | delete local, refetch on demand | 0.44 |
| longmemeval_retrieval/data/*.json | 322M | (b) public benchmark, NO fetch script | `PREREGISTRATION.md`: HF `xiaowu0162/longmemeval-cleaned`; gitignored but only consumers, no downloader | **write fetch_longmemeval.py (HF snapshot_download), then delete local** | 0.32 |
| gdpval/cases.jsonl, data/processed/runs/ | ~28M | (a) derived, already optimal | root .gitignore "track the generator not the output" | already handled | ~0 |

## Top 3
1. **evals ~0.77G, zero risk**: longmemeval (322M) + data/raw (445M) are public re-downloadable, already gitignored; data/raw already has the fetch-script pattern — just add `fetch_longmemeval.py` to close the one gap, then delete both local copies.
2. **intel git-history bloat**: the churning tracked `claim_graph_imports.jsonl` + `*_work_queue.csv` are the actual driver of the 84MiB pack and grow every commit — gitignore + filter-repo. Highest-leverage because it stops ongoing accretion.
3. **intel symlink stragglers**: prices/ (256M) + remaining datasets/ (~352M) + substacks/ (686M) → 2TBPNY, following the existing ~390-dir precedent. Plus instant `theses.prev.duckdb` delete (54M).
