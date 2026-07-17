---
id: 2026-07-12-agentlogs-slug-canonicalization
concept: agentlogs-project-attribution
repo: agent-infra
decision_date: 2026-07-12
recorded_date: 2026-07-12
provenance: contemporaneous
status: accepted
initial_leaning: stamp AGENTLOGS_PROJECT in child env for indexer to read
relations: []
  # Closes decisions-pending/2026-07-06-agentlogs-worktree-slug-blindness.md (deleted on accept).
---

# 2026-07-12: agentlogs slug canonicalization + llmx attribution (no env→indexer)

## Context

`decisions-pending/2026-07-06-agentlogs-worktree-slug-blindness.md` escalated worktree
slug forks and (2026-07-12 extension) llmx-cache cwd collision hiding ~89% of the store
from `--project` queries. First design stamped `AGENTLOGS_PROJECT` into the child CLI
env; Opus REJECTED — indexer reads its own `os.environ`, not the session child's.

## Alternatives considered

1. **Env stamp → indexer** — REJECTED (Opus): wrong process boundary; silent no-op.
2. **git-common-dir at index time** — works for real worktrees; does not fix llmx cache cwds.
3. **Per-caller cache dirs + marker file + JSONL sidecar** — chosen. Marker is unique per
   caller; sidecar is TTL-bounded fallback keyed by `cli_cwd` (nearest ts within 6h).
4. **Content/ancestry heuristics on transcripts** — deferred; higher maintenance, weaker verifier.

## Counterevidence sought

Looked for an in-process path where the indexer could inherit the dispatcher's env
(same PID tree). Found none: Claude/Codex/Cursor adapters run in the indexer process
against on-disk transcripts; child env is gone. Sidecar is the only durable OOB channel
without changing vendor transcript formats.

## Decision

Ship (agent-infra + llmx):

- Worktree canonicalize: `-wt\d+`, `--claude-worktrees-*`; refuse dash-encoded `-cache-llmx-`.
- Per-caller llmx cache dirs with `.llmx-caller-cwd` marker.
- Sidecar `~/.cache/llmx/dispatch-attribution.jsonl` — match `cli_cwd`, TTL 6h, skip
  truncated lines, soft rotate; **not** env→indexer.
- Drop unconditional `AGENTLOGS_PROJECT` env bonus (dead weight + inheritance hazard).

Codex `whence` trailer gap and cursor `model=NULL` remain open (out of this decision's
scope — different surfaces).

## Evidence

- Opus REJECT then FIX-THEN-LAND: `artifacts/critique/2026-07-12-llmx-opus-review.md`,
  `…-rereview.md`.
- Commits: agent-infra `a68237f` (adapters + tests); llmx `bfd3da5`.
- Tests: `tests/agentlogs/test_slug_worktree.py`.

## Revisit if

- Concurrent dispatches sharing one `cli_cwd` mis-attribute (join is nearest-ts on
  `cli_cwd`; pid is recorded but not independently held by indexer).
- Marker adoption lags and sidecar becomes the primary path under load.
- Re-index of historical `-cache-llmx-*` sessions is needed (this decision is
  forward-looking only).

## Supersedes

Closes `decisions-pending/2026-07-06-agentlogs-worktree-slug-blindness.md` (approved → executed).
