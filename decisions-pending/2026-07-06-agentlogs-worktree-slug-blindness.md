# agentlogs: worktree sessions invisible to project queries + ingest lag

**Found:** 2026-07-06, arc-agi operator-input week audit
(`arc-agi/research/2026-07-06-operator-input-week-audit.md` §C1).

## Symptom [DATA]

`project_slug = 'arc-agi'` queries returned 313 of ~928 actual user-role messages for the
week. Two causes:

1. **Worktree sessions get their own slug.** Sessions launched via `claude --worktree` write
   transcripts under e.g. `-Users-alien-Projects-arc-agi--claude-worktrees-sorted-jumping-parnas`,
   which the indexer slugs as a DIFFERENT project. With worktree-per-peer now the recommended
   multi-session pattern (SessionStart peer warning), a growing share of each repo's sessions
   is invisible to `--project <repo>` queries — silently, a false-zero of the rg-gitignore class.
2. **Ingest lag on active sessions:** messages typed hours earlier (a 12:40 #g) were absent at
   22:30 despite the indexer running; recent/open sessions lag behind `agentlogs recent`
   freshness expectations.

## Why it matters

`agentlogs search --project X` is the canonical "what did we discuss" tool (global CLAUDE.md
toolbelt). Rescue-rate / operator-intervention audits (HINDSIGHT Mode 3) read operator
messages; under-reads corrupt the RSI metric. Any negative-evidence claim ("operator never
said X") from agentlogs is currently unsound.

## Proposed fix

- Indexer canonicalizes project roots: resolve `<repo>--claude-worktrees-<name>` (and git
  worktree paths generally — `git rev-parse --git-common-dir` equivalent) to the main repo
  slug; keep the worktree name as a session attribute, not a slug fork.
- Add a drift test: a synthetic worktree transcript must land under the parent slug.
- Freshness: surface per-vendor max-ingested-ts in `agentlogs stats` (it may already);
  document that open sessions lag, so auditors fall back to disk transcripts.
- Interim workaround (already in use, arc-agi): direct disk-transcript extraction —
  `arc-agi/loop/rescue_rate.py` globs `-Users-alien-Projects-arc-agi*` dirs.

## 2026-07-12 extension — same class, three more instances (cross-vendor audit)

Source: arc-agi 2-day cross-vendor session audit
(`arc-agi/loop/audit/codex_lane_read_2026-07-12.md`, `cursor_lane_read_2026-07-12.md`).

1. **llmx-cwd slug collision is the dominant instance — 89.3% of the ENTIRE store.**
   llmx dispatches codex/cursor from its cache cwds (`~/.cache/llmx/lite/*`,
   `~/.cache/llmx/cursor`), so sessions slug as `bare` / `Users-alien-cache-llmx-cursor`:
   20,942/23,464 indexed sessions are project-blind (measured 2026-07-12). Verified
   empirically: a session literally containing the searched string is missed under
   `--project arc-agi`. Fix options: llmx exports caller project via env var the adapters
   read, or adapters special-case llmx cache cwds with a content/ancestry fallback.
2. **Codex commits invisible to `agentlogs whence`** — the `Session-ID:` git trailer is a
   Claude-Code-hook-only artifact; two 8-11h codex sessions with 15 and 21+ real commits
   report ZERO commits through `whence`. Fix: codex-side trailer (llmx/codex wrapper) or a
   timestamp+path heuristic fallback in `whence`.
3. **`model` is NULL for all cursor-vendor sessions** (adapter never captures which of
   grok-4.5/composer served a transcript) — blocks per-model dispatch-economics audits.

Same "why it matters" as above, sharpened: every RSI self-audit (rescue-rate, Mode-3
grading, supervision audits) is structurally blind to the non-Claude lanes — the loops
being graded do a growing share of their work exactly there.
