---
title: Storage dossier — anki + mechinterp
date: 2026-07-14
status: active
---

[UNVERIFIED] Compiled from read-only Explore agent (no Write tool); figures re-verify before acting.

# anki + mechinterp_for_essay

## Totals
- **anki 5.7G** (.git 33M): crowdanki/ 4.2G (74%), .venv 1.0G (reclaim-covered), diagrams/ 385M, logs/ 36M, cache/ 25M.
- **mechinterp 1.9G** (.git 2.1M): .venv 1.8G (95%, reclaim-covered), checkpoints/ 53M, animations/ 45M, wandb/ 5.7M.

## Per-chunk verdicts

| Chunk | Size | Class | Evidence | Action | GB |
|---|---|---|---|---|---|
| anki/crowdanki/ | 4.2G | (c) gitignored, non-canonical | `.gitignore: crowdanki/`; SoT is live Anki `collection.media` 805M OUTSIDE repo; nested per-deck `.git` store media as loose objects (in-pack:0) ⇒ ~2× dup (mostly_bio: 633M media + 630M .git) | symlink → /Volumes/2TBPNY/anki-crowdanki | ~4.2G |
| anki/diagrams/{wikimedia,texample,serlo} | 378M | (b) re-downloadable | `.gitignore` labels "Bulk downloaded… re-downloadable"; `scripts/wikimedia_export_urls.py` regenerates wikimedia subset (texample/serlo: no regen script found — caveat) | symlink or delete+refetch | 378M |
| anki/cache/anki_embeddings.npz | 24M | (a) regenerable | `.gitignore: cache/`; consumed by find_anki_duplicates.py / find_anki_interference.py (regen path inferred, not a one-liner) | delete+regen or symlink | 24M |
| anki/logs/ (.bak, .bak2) | 16M | (c) redundant backups | 3 near-identical rolling backups | drop oldest / symlink logs/ | ~10M |
| mechinterp/checkpoints/ | 53M | (b) re-downloadable | `CHECKPOINT_STATUS.md`: "all downloaded"; 5 download_*.py pull from wandb cloud (run IDs match wandb/run-*) | delete+regen via download_checkpoints.py | 53M |
| mechinterp/animations/media/ | 44M | (a) regenerable | Manim render cache; `animations/grokking.py` header documents exact `uv run manim -pql … <Scene>` regen commands | delete+regen | 44M |
| both .venv | 2.8G | (c) venv | reclaim covers machine-wide venv hygiene | (reclaim) | n/a |

## Top 3
1. **Symlink anki/crowdanki/ (4.2G)** to external SSD — biggest single win on the machine after corpus; provably non-canonical (gitignored export cache, SoT is live collection). Bonus: nested per-deck `.git` loose-object doubling could be gc'd for extra reclaim.
2. **Symlink/refetch anki/diagrams (378M)** — repo's own gitignore labels re-downloadable.
3. **Delete+regenerate mechinterp checkpoints+animations (~97M)** — documented wandb-download and manim-render regen paths; zero risk.

Addressable non-venv: **~4.65G**.
