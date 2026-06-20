---
description: Canonical provenance block schema for MEMORY files — single source of truth
paths:
  - "memory/**"
  - "scripts/memory_provenance_check.py"
---
# Memory Provenance Schema

<!-- Gov-ID: rule:memory-provenance-schema
goal: ensure every condensed lesson links back to its raw source so lessons are auditable and replayable (F2 substrate)
verifier: null
blast_radius: local
-->

Every MEMORY file under
`~/.claude/projects/-Users-alien-Projects-agent-infra/memory/*.md`
MAY carry a `provenance` block in its YAML frontmatter. Files that CLAIM a rule
or hook (body or `description` mentions "rule"/"hook" or references `rules/*.md` /
`hooks/*.py`) MUST carry `provenance.links_rule`.

## Schema block

```yaml
provenance:
  source_session_id: <session_uuid>      # matches agentlogs sessions.session_uuid AND F1 session_trace IR "session_uuid"
  trace_span_ids: [<step-id>, ...]        # F1 TraceStep.id values — optional; omit if unknown
  derived_from: [<git-sha>, ...]          # optional git commit(s) the lesson was distilled from
  lifecycle: active | superseded | invalidated   # default active; invalidate never delete (Engram/append-only rule)
  links_rule: <repo-relative path to the live rule/hook this lesson claims to back>  # required when body claims a rule/hook
```

## Field semantics

| Field | Required | Purpose |
|---|---|---|
| `source_session_id` | recommended | Ties lesson to the agentlogs session it was distilled from; enables replay via `just session-trace` |
| `trace_span_ids` | optional | Pins to specific F1 TraceStep IDs for finer-grained auditability |
| `derived_from` | optional | Git SHAs of commits the lesson originated from |
| `lifecycle` | optional (default: active) | Bi-temporal status — see lifecycle verbs below |
| `links_rule` | required when lesson claims a rule/hook | Repo-relative path; checker verifies the file exists on disk |

## Lifecycle verbs

Matches the append-only constitution and improvement-log conventions:

- `active` — lesson is current and used
- `superseded` — replaced by another memory or rule (link the replacement in the body with `[[slug]]`)
- `invalidated` — shown to be wrong; kept for calibration history, never deleted

**Never delete a memory file.** Mark as `invalidated` or `superseded` with a note. The history of belief changes is calibration data.

## Drift checker

`scripts/memory_provenance_check.py` — read-only, always exits 0.

```
uv run python3 scripts/memory_provenance_check.py          # human output
uv run python3 scripts/memory_provenance_check.py --json   # machine output
```

Warns on:
1. `MISSING_LINKS_RULE` — body/description claims rule/hook but `provenance.links_rule` absent
2. `DANGLING_LINKS_RULE` — `links_rule` set but path does not exist on disk
3. `INVALID_LIFECYCLE` — `lifecycle` present but not `active|superseded|invalidated`

## Theory (F2 substrate)

From the integration plan (`research/2026-06-20-paper-integration-plan.md`, F2):
arXiv:2601.22436 ("Not Always Faithful Self-Evolvers") shows agents **misuse condensed
experience and rely more faithfully on raw**. A condensed lesson without a raw-source
link is a weak, possibly-ignored substrate. Engram (2606.09900) adds bi-temporal
lifecycle so lessons can be invalidated without deletion.
