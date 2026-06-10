# Ecosystem Refactor Handoff

Date: 2026-06-10

This is the executable handoff for the current refactor. It supersedes older
thread notes and `.claude/plans/*` drafts when they conflict.

## Hard boundaries

- Do not rename `/Users/alien/Projects/agent-infra`.
- Do not rewrite live paths from `agent-infra` to `agent-meta`.
- Do not extract or revive `_synthoria-donor` in this pass.
- Do not move private data, PHI, reference photos, `.env`, API keys, databases,
  or generated bulk indexes into new public repos.
- New repos are private by default until explicitly reviewed.
- Use direct caller migration. Do not add compatibility wrappers, dual paths, or
  fallback reads unless a named live external boundary forces it.

## Baseline rollback anchors

Affected repos have local tag `pre-refactor-2026-06-10`. The tag has been pushed
where the repo has an `origin`; `ext` has no remote, so its tag is local-only.

## Current target layout

### `substrate` new repo

Owns shared source/claim/genome packages:

- `packages/corpus-core`
- `packages/corpus-testing`
- `packages/claimcore`
- `packages/genomics-read`
- `packages/clinical-profile`

Consumers must point directly to `../substrate/packages/...` via editable `uv`
sources. Remove old `../agent-infra/scripts/corpus/packages/...`,
`../genome-toolkit/packages/...`, and vendored `corpus_core` wheel references.

### `genome-toolkit`

Keeps the open local plugin shell:

- `packages/toolkit_mcp`
- root plugin/workspace metadata

It consumes substrate packages; it does not own them.

### `imagegen` new repo

Owns person-into-scene image engine code only. Keep reference photos, outputs,
private profiles, and generated assets out of git unless explicitly sanitized.

### `ext`

Receives external consumed-media acquisition code where practical. Do not move
the full media index/data corpus in this pass unless explicitly scoped and
secret-scanned.

### `intel`

Receives executable/read-only portfolio code from `phenome`, not unrelated
personal finance memos unless separately scoped.

## Execution order

1. Keep all target repos clean before each phase.
2. Create `substrate` as a private GitHub repo and move substrate packages.
3. Rewire consumers one repo at a time and run import/test smoke after each.
4. Move `imagegen` code into a private repo and update phenome callers.
5. Move portfolio executable code into `intel`; update/removing phenome CLI hooks.
6. Move external media acquisition scripts into `ext` where the ownership is clear.
7. Commit and push one semantic unit per repo.
8. Run critique close after implementation.

## Minimum validation

Run after each phase as applicable:

```bash
git status --short --branch
git diff --check
uv lock
uv run python3 -c "import corpus_core; print(corpus_core.__file__)"
uv run python3 -c "import claimcore; print(claimcore.__file__)"
uv run python3 -c "import genomics_read; print(genomics_read.__file__)"
uv run python3 -c "import clinical_profile; print(clinical_profile.__file__)"
cd /Users/alien/Projects/substrate && uv run pytest packages/corpus-core/tests packages/corpus-testing/tests
cd /Users/alien/Projects/substrate && uv run pytest packages/claimcore/tests packages/genomics-read/tests packages/clinical-profile/tests
```

Adjust test paths after package moves.

## Known stale warnings

Earlier warnings about dirty `phenome` imageengine and broad dirty `intel` state
were true before the checkpoint commits. They are stale after the 2026-06-10
cleanup and push. Still re-check status before moving files, because active
agents can create new dirt.
