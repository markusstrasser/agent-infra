# LessWrong + Gwern — Shared Corpus Reference

LessWrong high-karma posts and the full Gwern.net essay corpus are ingested into
the shared content-addressed corpus (`$CORPUS_ROOT`, default `~/Projects/corpus`),
queryable from any project via the corpus MCP and the FTS helper below.

## What's in it

| Source | Scope | Count | How |
|---|---|---|---|
| LessWrong | posts with `baseScore >= 30` | ~14,572 | GraphQL `contents{html}` → trafilatura → markdown |
| Gwern.net | essay-class pages (extensionless, non-`/doc/`,`/static/`,`/metadata/`) | ~660 | sitemap → `ingest_url` → trafilatura |

Excluded by design: LW comments (low signal), LW posts <30 karma, Gwern's `/doc/`
mirror of third-party papers (~20k PDFs/CSVs — not his writing).

Each source is a `sha_<hash>` dir with `source.html`, `parsed.trafilatura@.../page.md`,
and `metadata.json`. Metadata carries the join keys:
`source` (`lesswrong`|`gwern`), and for LW: `karma`, `vote_count`, `author`,
`author_username`, `posted_at`, `tags[]`, `lw_post_id`, `lw_url`, `word_count`.

## Query — FTS reference search (the primary surface)

```bash
PY=~/.local/share/uv/tools/corpus-core/bin/python3
SC=~/Projects/agent-infra/scripts/corpus_reference_search.py

$PY $SC --build                                   # (re)build after an ingest
$PY $SC "mesa optimization"                        # BM25 over both sources
$PY $SC "AI timelines" --source lesswrong --min-karma 100 --limit 15
$PY $SC "spaced repetition" --source gwern --full   # print top hit body
$PY $SC "scaling laws" --tag "AI"                   # filter by LW tag
```

BM25 ranked; filters: `--source`, `--min-karma`, `--tag`, `--author`, `--limit`,
`--full`. Index at `$CORPUS_ROOT/reference_fts.duckdb` (rederived, not authoritative).

**Refresh the FTS index after the LW ingest finishes** (it runs ~3h in background) —
the index only covers sources present at `--build` time.

## Ingest / refresh

```bash
PY=~/.local/share/uv/tools/corpus-core/bin/python3
cd ~/Projects/agent-infra/scripts
$PY corpus_ingest_lesswrong.py --build-index          # refresh metadata index + karma histogram
$PY corpus_ingest_lesswrong.py --ingest --floor 30    # resumable; checkpoint lesswrong_ingested.txt
$PY corpus_ingest_gwern.py                            # resumable; checkpoint gwern_ingested.txt
```

Both are idempotent (content-addressed) and resumable. Lower `--floor` to widen LW
coverage (≥20: 20.4k posts, ≥10: 30.3k). Re-run periodically for new posts/essays.

## Programmatic access

```python
from corpus_core import store as ps
import json
# iterate LW/Gwern sources
for m in ps.store_root().glob("*/metadata.json"):
    meta = json.loads(m.read_text())
    if meta.get("source") in ("lesswrong", "gwern"):
        body = next(m.parent.glob("parsed.*/page.md")).read_text()
        ...
```

Or via corpus MCP: `corpus_lookup(source_id)` for presence + parsed markdown.

## Next phase (not yet built)

- **Entity-graph join** (the second stated purpose): extract entity mentions /
  predictions / claims from LW+Gwern bodies and join into the intel thesis graph.
  The metadata (author, date, karma, tags) is the provenance layer for this; the
  extraction pass is the open work.
- **Semantic retrieval**: BM25 only today. Add embeddings if keyword recall proves
  insufficient for reference lookup.
