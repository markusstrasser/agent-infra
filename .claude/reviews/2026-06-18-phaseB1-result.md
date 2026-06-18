# Phase B1 — commit→decision implements-edge recovery

PHASE B1 IN PROGRESS (impl complete; gates running)

Spec: `decisions-pending/2026-06-18-phaseB-implements-trailer.md` (B1 section)
Scope: AGENTLOGS-LOCAL, UNGATED. Did NOT touch shared hooks / prepare-commit-msg / commit-check-parse.py.

## Ground truth re-probed (2026-06-18)
- `git_commits` total rows: 12924 · body-populated: 0 (before) · agent-infra rows: 1155 (DB) / 1662 (full history).
- `lifecycle_edges` before: 0 implements · 51 traversable.
- Resolving decision-slug mentions in agent-infra commit bodies: **33 distinct** over full history (31 within 30d). 124 slug-shaped strings that do NOT resolve (deleted/renamed decisions, non-decision dates like `2026-03-19-late`) — must be skipped, not emitted.

## Changes (exact)
1. `src/agentlogs/git_import.py` — `_parse_git_log`: switched to `git log -z` (NUL records) and added `%b` (body), wrapped in `\x1e` record-separators so multiline bodies can't shift header columns. Rewrote the chunk loop: `-z`+`--numstat` ALTERNATES header-chunk / numstat-chunk; the numstat chunk belongs to the PRECEDING header. Probed the real byte format before trusting (chunk 2k=header w/ US, chunk 2k+1=numstat no-US). `timeout` 30→60s. Body now populated for all imported rows; existing `ON CONFLICT DO UPDATE SET body=excluded.body` backfills.
2. `src/agentlogs/lifecycle.py` — added `_commit_implements_edges(con, nodes)`: scans agent-infra `git_commits.body` for
   - `^Implements:\s*(\S+)$` trailers → `source='commit-trailer'` (emits even if dangling: explicit author intent);
   - resolving `\b20\d\d-\d\d-\d\d-[a-z0-9][a-z0-9-]+\b` prose mentions → `source='commit-mention'` (non-resolving SKIPPED — resolution is the precision filter);
   - dedup: trailer+mention of same slug → ONE edge, prefers trailer.
   Emits `subject=<hash>, type='implements', target=<slug>, traversable=1`. Wired into `build_edges` after the frontmatter pass (same `con`, inside the atomic swap). Manifest gains `edges_commit_implements{,_resolved,_dangling}`.
3. `tests/agentlogs/test_lifecycle.py` — +3 tests (trailer→edge, prose-mention-resolves + non-resolving-skipped, trailer/mention dedup).

## Gates
1. body populated: PENDING (backfill import waiting out live launchd indexer; see below)
2. lifecycle-reindex implements count: PENDING (gated on #1)
3. `just graph <slug>`: PENDING (gated on #1)
4. tests: **PASS** — 7 collected, 7 passed (4 existing + 3 new). Verbatim below.
5. staged-paths name-status: PENDING (pre-commit)

### Gate 4 verbatim
```
tests/agentlogs/test_lifecycle.py::test_superseded_by_inverts_to_supersedes
tests/agentlogs/test_lifecycle.py::test_relates_to_never_traversable
tests/agentlogs/test_lifecycle.py::test_resolver_spans_decisions_and_research
tests/agentlogs/test_lifecycle.py::test_commit_implements_trailer_emits_edge
tests/agentlogs/test_lifecycle.py::test_commit_prose_mention_resolves_to_edge
tests/agentlogs/test_lifecycle.py::test_commit_trailer_and_mention_dedup_to_one
scripts/tests/test_lifecycle_relations.py::test_no_unknown_lifecycle_relation_strings
7 passed in 0.59s
```

## Lock contention note
The launchd `agentlogs-index` job (`--max-run-seconds 600`) holds the WAL writer lock; the CLI `git-import` exits clean after a 30s wait. Backfilling via a patient one-shot (`write_gateway(timeout_s=900)`) that WAITS the indexer out instead of racing it (does NOT touch the launchd job; does NOT use no_lock). Status appended on completion.
