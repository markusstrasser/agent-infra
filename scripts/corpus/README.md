# `corpus` — canonical shared corpus store

Single store at `~/Projects/corpus/` for source bytes (PDF/HTML/etc.), parses,
citation contexts, annotations, and a DuckDB-backed graph index.

Workspace layout:

```
scripts/corpus/
├── pyproject.toml              # workspace root (tool.uv.workspace = packages/*)
├── packages/
│   └── corpus-core/            # corpus_core package (CLI + library)
│       ├── pyproject.toml
│       ├── corpus_core/
│       └── tests/
└── schemas/                    # JSON Schemas (populated in Phase 1)
```

See `~/Projects/corpus/SCHEMA.md` for the per-source directory layout.

## Install

```bash
uv tool install --editable ~/Projects/agent-infra/scripts/corpus/packages/corpus-core
```

Then `corpus --help` from any directory.

## Quick commands

```bash
corpus --corpus-root ~/Projects/corpus stats
corpus --corpus-root ~/Projects/corpus lookup --doi 10.1234/test
corpus --corpus-root ~/Projects/corpus ingest --pdf /tmp/x.pdf --doi 10.1234/test
corpus --corpus-root ~/Projects/corpus show 10.1234/test --depth full
corpus --corpus-root ~/Projects/corpus show pmid:12345678
corpus --corpus-root ~/Projects/corpus resolve-references --paper-id doi_10_1234_test
corpus --corpus-root ~/Projects/corpus extract-citances --paper-id doi_10_1234_test
corpus --corpus-root ~/Projects/corpus maintain --rebuild-indexes
corpus --corpus-root ~/Projects/corpus maintain --rebuild-graph
corpus --corpus-root ~/Projects/corpus cited-by doi_10_1234_test --stance contrasting
```
