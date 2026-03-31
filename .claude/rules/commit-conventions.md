# Meta Commit Conventions

Supplements the global commit message format with meta-specific rules.

## Trailers

| Trailer | When | Required? |
|---------|------|-----------|
| `Evidence:` | Governance files (CLAUDE.md, MEMORY.md, hooks, improvement-log, rules) | Hook-suggested |
| `Affects:` | Classification/curation logic, cross-project changes | Hook-suggested |
| `Rejected:` | Design choices — record what was considered and discarded | Hook-suggested |
| `Session-ID:` | Every commit — auto-appended by `prepare-commit-msg` git hook | Auto (git hook) |
| `Source:` | Cross-project provenance (`Source: intel@f9dfcc9`) | Manual |

The commit hook (`commit-check-parse.py`) suggests trailers based on staged files and message content. No trailer is blocking — all advisory. Exception: `Session-ID:` is auto-appended by a `prepare-commit-msg` git hook (symlinked from `skills/hooks/prepare-commit-msg-session-id.sh`) — reads `.claude/current-session-id`, no agent action needed.

## Concept Shift Bodies

Commits touching `research/`, `decisions/`, or index-referenced docs must have a non-empty body naming the concept affected and what changed directionally. `git log --format='%s%n%b' -- decisions/` should read as a concept evolution timeline.

## Scope Reference

Canonical scopes for meta are listed in `.git-scopes` (repo root). The commit hook warns on unknown scopes but doesn't block. When adding a genuinely new scope, add it to `.git-scopes`.
