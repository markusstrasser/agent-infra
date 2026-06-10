# Ecosystem Refactor Preflight

**Date:** 2026-06-10
**Related plan:** `49c9a838-ecosystem-final-layout.md`
**Purpose:** preserve reversibility, history clarity, and validation surfaces before the multi-repo ecosystem re-home.

## Verdict

Do not start the file moves until the contradictions and state risks below are resolved.

This migration is recoverable if it is treated as a sequence of semantic re-homes with explicit validation. It becomes hard to unwind if package extraction, product moves, repo renames, generated config changes, and unrelated dirty worktree state are bundled together.

## Current workspace state

Captured from `git status --short --branch` on 2026-06-10.

| Repo | State | Refactor implication |
|---|---:|---|
| `agent-infra` | `main...origin/main [ahead 106]`; dirty generated map/index/marker files plus `.claude/settings.local.json` | Commit only coherent meta changes; keep local settings out unless intentionally publishing permissions. |
| `phenome` | `main...origin/main [ahead 144]`; dirty `imageengine` files and backlog doc | Do not evict `imageengine` until this work is committed or explicitly parked. |
| `genomics` | `main...origin/main [ahead 56]`; dirty generated/audit/ops files | Substrate rewiring must avoid mixing with audit output churn. |
| `intel` | `main...origin/main [ahead 245]`; broad dirty research/log/model-review state plus `pyproject.toml`/`uv.lock` | Portfolio move must be isolated from active research/log churn. |
| `research-mcp` | `main...origin/main [ahead 42]`; dirty codebase map | Rewire editable source only in a dedicated commit. |
| `genome-toolkit` | `main`; untracked `.model-review/` | Package extraction is likely clean, but do not include model-review scratch. |
| `skills` | `main...origin/main [ahead 90]`; dirty hook and overview files | L0 references should not be bundled with substrate moves. |
| `evals` | `main...origin/main [ahead 49]`; dirty run outputs/plans | No direct move needed; leave out unless renaming L0 references. |
| `ext` | clean `main` | Safe first receiver for external-media moves. |

Missing repos/targets under `/Users/alien/Projects` at preflight time:

- `substrate`
- `imagegen`
- `agent-meta`

Existing targets:

- `ext`
- `skills`
- `evals`

## Plan contradictions to fix first

1. `parsers` is listed as promoted to L1 because `ext` is a second consumer, then later listed as phenome-only and staying vertical until a second consumer. Choose one rule before moving code.
2. `genome-toolkit` is said to keep its name, but sequencing says `genome-toolkit -> substrate`. The intended operation should be written as: extract substrate packages out of `genome-toolkit`; keep `genome-toolkit` as the open plugin shell.
3. The plan says renames last, but also includes `agent-infra -> agent-meta` as a core delta. Treat this as a final mechanical pass after package paths settle, not part of substrate extraction.
4. `synthoria` is both parked/deferred and listed as an extraction after substrate. Leave it out of this migration unless the business gate reopens.

## Hard stops

Stop before editing if any of these are true:

- Another active agent is still writing in a repo whose files are about to move.
- The source repo has uncommitted changes under the exact paths being moved.
- A target repo does not exist and the intended creation mode is not chosen: new git repo, subtree, or plain directory pending init.
- The package's import name and editable dependency path are not both known.
- There is no validation command for at least one consumer.

## Move manifest skeleton

Fill this table before implementation. Each row should become one semantic commit or a small pair of source/consumer commits.

| Move | Source | Target | Consumers to rewire | Validation |
|---|---|---|---|---|
| `corpus-core` | `agent-infra/scripts/corpus/packages/corpus-core` | `substrate/packages/corpus-core` | `agent-infra`, `phenome`, `genomics`, `intel`, `research-mcp`, `genome-toolkit` if transitive | `uv run pytest` target tests; `rg` for old editable paths and ambient corpus defaults. |
| `claimcore` | `genome-toolkit/packages/claimcore` | `substrate/packages/claimcore` | `genome-toolkit`, `phenome`, `genomics` if imported | package tests plus `rg "claimcore|packages/claimcore"`. |
| `genomics-read` | `genome-toolkit/packages/genomics-read` | `substrate/packages/genomics-read` | `genome-toolkit`, `genomics`, `phenome` if imported | package tests plus import smoke. |
| `clinical-profile` | `genome-toolkit/packages/clinical-profile` | `substrate/packages/clinical-profile` | `genome-toolkit`, `phenome` if imported | package tests plus import smoke. |
| `imageengine` | `phenome/src/phenome/imageengine`, related modal/UI/MCP/tests | `imagegen` | `phenome` MCP callers, any scripts | commit or park current dirty imageengine work first; run `tests/test_imageengine.py`. |
| `portfolio` | `phenome/portfolio` | `intel` | `intel` private workbook/workflows | check canonical finance routing and avoid mixing with active intel logs. |
| external scrapers | `phenome/scripts` pinterest/instagram/media acquisition | `ext` | `ext` archive ingestion | ext smoke; `rg` for old script paths. |
| donor service | `phenome/donor`, `phenome/mcp/donor`, donor tests | `_synthoria-donor` | none while parked | only after explicit business-gate decision. |
| repo rename | `agent-infra` | `agent-meta` | global/project `.mcp.json`, launchd, docs, scripts, memories | final grep sweep; MCP startup smoke; launchd plist check. |

## Recommended execution order

1. Commit/park source-path dirty work, especially `phenome` imageengine changes.
2. Create `substrate` as a real repo or explicitly document that it is a plain workspace directory before first move.
3. Do low-risk vertical evictions where target repos are clean: external scrapers to `ext` first, then portfolio only if intel state is isolated, then imagegen after imageengine dirt is resolved.
4. Extract substrate packages one package family at a time. Rewire one consumer per commit when practical.
5. Run a narrow validation after each consumer rewire; run the full matrix only after all rows in a phase pass.
6. Rename `agent-infra` to `agent-meta` last, as a mechanical reference update.

## Commit and push policy

- Stay on `main`.
- No branch.
- No stash as a substitute for understanding.
- Commit only semantic units with the format `[scope] Verb thing — why`.
- Keep generated files, local permission files, run outputs, and model-review scratch out unless they are the subject of the commit.
- Push only after each repo has a clean or intentionally dirty status where unrelated dirt is documented and unstaged.

## Validation matrix

Minimum checks before and after each phase:

```bash
git status --short --branch
git diff --check
rg -n "agent-infra|agent-meta|scripts/corpus/packages|packages/corpus-core|packages/claimcore|packages/genomics-read|packages/clinical-profile|phenome/imageengine|portfolio|pinterest|instagram" .
```

Corpus/substrate-specific checks:

```bash
rg -n "store_root|CORPUS_ROOT:-|CORPUS_STORE|~/Projects/corpus" /Users/alien/Projects/agent-infra /Users/alien/Projects/genomics /Users/alien/Projects/phenome /Users/alien/Projects/intel /Users/alien/Projects/research-mcp
uv run pytest scripts/corpus/packages/corpus-core/tests
```

Consumer smoke pattern:

```bash
uv run python3 -c "import corpus_core; print(corpus_core.__file__)"
uv run python3 -c "import claimcore; print(claimcore.__file__)"
uv run python3 -c "import genomics_read; print(genomics_read.__file__)"
uv run python3 -c "import clinical_profile; print(clinical_profile.__file__)"
```

Run the import smokes from the consumer repo after its `pyproject.toml`/`uv.lock` is rewired, not just from the package source repo.

## Recovery notes

- Because `.claude/plans/` is ignored, force-add this artifact only if the migration needs it in git history. Otherwise treat it as a local operator ledger.
- If a move fails halfway, prefer a forward fix or a semantic revert commit over `git reset --hard`.
- For active repos with large ahead counts, pushing before this migration may reduce collaboration risk, but only after each repo's uncommitted state is classified.
