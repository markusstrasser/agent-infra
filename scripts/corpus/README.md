# `papers` — canonical shared papers store

Single store at `~/Projects/papers/` for PDFs, marker parses, citation contexts,
and a DuckDB-backed citation graph.

See `~/Projects/papers/SCHEMA.md` for the layout and `~/Projects/agent-infra/.claude/plans/2026-05-11-shared-papers-store.md` for the full plan.

## Install

```bash
uv tool install --editable ~/Projects/agent-infra/scripts/papers
```

Then `papers --help` from any directory; `uvx papers ...` for one-off invocation.

## Quick commands

```bash
papers stats
papers ingest --pdf /tmp/x.pdf --doi 10.1234/test
papers show doi_10_1234_test --depth full
papers resolve-references --paper-id doi_10_1234_test
papers extract-citances --paper-id doi_10_1234_test
papers maintain --rebuild-indexes
papers maintain --rebuild-graph
papers cited-by doi_10_1234_test --stance contrasting
```
