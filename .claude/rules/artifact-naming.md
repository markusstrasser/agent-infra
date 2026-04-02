# Artifact Naming Convention

Artifacts are files written to `artifacts/` subdirectories by skills and scripts.
Any artifact that could be produced by multiple agents or sessions **must** include
a session discriminator to prevent overwrites.

## Pattern

```
{YYYY-MM-DD}-{session_id[:8]}-{qualifier}.{ext}
```

- **date** — ISO date, always the prefix (lexicographic sort = chronological sort)
- **session_id[:8]** — first 8 chars of `.claude/current-session-id`. Fallback: `$(date +%s | tail -c8)` (epoch suffix)
- **qualifier** — what produced it: `manual`, `findings`, `suggest`, `cycle`, etc.
- **ext** — `.json` for structured data, `.md` for prose, `.jsonl` for append-mode

### Shell snippet for skills

```bash
SID=$(cat ~/.claude/current-session-id 2>/dev/null | head -c8 || date +%s | tail -c 8)
OUTFILE="${ARTIFACT_DIR}/$(date +%Y-%m-%d)-${SID}-${QUALIFIER}.json"
```

## Exceptions

- **Append-mode JSONL** (code-review-scout, patterns.jsonl) — deduplicates by hash,
  concurrent appends are safe. Date-only or static name is fine.
- **Staging/scratch files** (session-analyst `input.md`, coverage-digest.txt) —
  intermediate files that get overwritten intentionally. No session ID needed.

## Consumers

Consumers (propose-work.py, steward gather-state.sh) glob by `*.json` / `*.md` and
sort by name. The `{date}-{sid}-{qualifier}` pattern preserves sort order. No changes
needed in consumers when adopting this convention.
