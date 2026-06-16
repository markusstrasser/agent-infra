# Embed-once session extraction — validated + first recurring-mistake findings

**Date:** 2026-06-17
**Status:** architecture validated; findings actionable.
**Context:** the "derive everything from sessions" thread (2026-06-16/17). Foundation fixed
(`agentlogs` merge `e4eac54`), then the question: how to extract without re-paying per angle.

## 1. Embed-once decoupling — VALIDATED (not asserted)

The costly, irreversible step is the LLM read of a transcript. `mine_steers.py` does NARROW,
per-angle LLM extraction (Composer 2.5, **metered Cursor pool $real**) — its ledger idempotency
is keyed to the *steers/miss prompt*, so a new angle re-reads every transcript and re-pays.

**Fix, proven this session:** embed-once into an angle-agnostic local index; every future angle is
a free `emb search` (or cheap `emb read` = retrieve-then-LLM-over-only-the-hits).

Probe: 200 operator sessions (`is_subagent=0`) → `emb embed` → 719 chunks, 768-dim, **$0 local,
~2 min**. Fired 5 angle queries the steer-mining NEVER targeted; every one surfaced relevant
sessions:

| New angle (never extracted for) | top hit | sim |
|---|---|---|
| which LLM model/effort to use | the llmx-refactor dispatch ADR session | 0.733 |
| over-engineering / no caller | bounded-autonomy + "toxic proactivity FM14" | 0.675 |
| db schema / data contract | append-only assertions schema + genomics ADR | 0.611 |
| asked permission vs acting | confirmation-signal sessions | 0.661 |
| build-then-undo / wrong shape | "cure is not more architecture" / "/decide?" | 0.683 |

**Consequence:** metered per-angle re-mining is dead. The expensive LLM-digest layer the plan
proposed may be unnecessary — embed-once (raw chunks) + `emb read` per-angle likely covers it.
Build the digest layer only if a probe shows retrieve-then-read is insufficient.

### Reproduction
```bash
# export operator sessions → JSONL  (exporter: /tmp/export_sessions_probe.py, formalize into scripts/)
uv run python3 export_sessions.py            # {id,text,source,date} per session, is_subagent=0
uv run --project ~/Projects/emb emb embed sessions.jsonl -o session_index/ --chunk
uv run --project ~/Projects/emb emb search session_index/ "ANY new angle"   # free re-angle
uv run --project ~/Projects/emb emb read   session_index/ "angle" --top-k 200   # cheap LLM-on-subset
```
Model economics: a broad batch pass must use **subscription Claude/Codex ($0)** or Gemini
`--flex` (50% off, non-interactive) — NOT metered Composer (its only edge, parallelism, is moot
for an overnight batch).

## 2. First recurring-mistake findings (semantic clustering, not keyword)

595 `agent_miss` signals (2 Composer probes, ~85 operator sessions, $5.1 + partial). Keyword
ranking left 36% UNCLASSIFIED; **semantic clustering** (`emb embed` the miss texts + `emb pairs
--threshold 0.80` → 56 recurring pairs) surfaced the true clusters:

| recurring cluster | count | nature |
|---|---|---|
| subagent dispatch-gate retry (write-stub/file-output rejected 1st try) | 18 | **gate-induced** |
| provenance-tag Stop-hook block (memo written → blocked → retry) | 17 | **gate-induced** |
| shared-checkpoint / peer-session clobber | 17 | isolation not adopted |
| committed without explicit request | 12 | rule ambiguity |
| asked/stopped when already instructed | 9 | over-ask |
| bare `modal`/`python` vs `uv run` | 6 | convention |

Overall: **50% of agent_misses forced a human steer.** `didnt-verify-claim` is the keyword #1
(105) but is already heavily governed — recurrence there = coverage gaps, not missing rules.

### Meta-finding (load-bearing)
**The top two clusters — 35 misses — are OUR OWN GATES rejecting the first attempt and forcing a
retry.** They are NOT agent-discipline failures; they are **hook-ergonomics failures.** Same shape
as the 2026-06-17 poll-hook bare-dir false-fire (`skills@0e6ac79`): a large fraction of recorded
"mistakes" is gate-induced friction. **The fix is gate ergonomics — transform / auto-inject the
required strings, not block-then-retry — not more discipline.**

## 3. What should be GLOBAL (candidates — NOT yet built; gate-ergonomics first)

All global-layer (`~/Projects/skills/hooks/`), so human sign-off (hard limit #4). Per
constitution principle 3 + this morning's lesson, fix ERGONOMICS of existing gates before adding any:

1. **Subagent dispatch-gate (18):** the gate already injects the fix string in its block message,
   but still forces a re-dispatch. Make agent-def dispatch templates carry the write-stub/file-output
   strings BY DEFAULT (pass first time), or have the gate auto-append rather than block. Highest
   frequency (~1 in 5 sessions).
2. **Provenance Stop-hook (17):** same shape — auto-scaffold the tags at memo-write time, or have
   research templates include them, so the Stop hook passes first time.
3. **Peer-session clobber (17):** the SessionStart peer warning isn't being adopted → consider
   auto-worktree on detected peer, not just a warning.
4. **Commit-without-request (12):** genuine rule tension (auto-commit "after a task" vs "don't
   commit unrequested") — clarify the boundary, don't hook.

## Update — gate-ergonomics fixes SHIPPED + "find more" pass (2026-06-17)

Global candidates 1-3 implemented (all gate-ergonomics, "transform/shift-left, not block"):
- **subagent dispatch-gate** → auto-inject the write-stub/file-output discipline via
  `updatedInput` instead of block-then-retry. `skills@da1b249`.
- **provenance pre-write** → emit `additionalContext` (agent-visible) instead of exit-1 stderr
  (which never reached the model — the warn was theater). `skills@124dd56`.
- **precompact checkpoint** → session-stamp + don't clobber a PEER session's untracked
  checkpoint (the existing guard only covered git-tracked ones). `skills@c64ebfd`.
True "auto-worktree" for the peer case is NOT possible from a hook (can't fork a live session);
the real fix was making the checkpoint WRITE non-clobbering.

**"Find more" pass** (semantic clustering of the 215 UNCLASSIFIED misses, `emb pairs`):
- **continuation-misread (6)** — agent replies "No response requested" to "Continue from where
  you left off" and drops the thread. NEW, recurring, HOOKABLE (Stop/UserPrompt: a continuation
  directive must not resolve to a no-op). Top new global candidate.
- **background-job output buffering (3)** — `| tail -N` / `&` inside backgrounded Bash on long
  jobs buffers all output until completion. Bash gotcha.
- **extractor/feed scope drift (4)** — new inputs (RSS feeds, stages) scraped/added but excluded
  from downstream extraction. Domain-specific (genomics/intel).

## Revisions
- 2026-06-17: candidates 1-3 shipped; added find-more findings.
