---
id: 2026-06-13-multiagent-shared-state-event-sourcing
concept: multiagent-state-isolation
repo: agent-infra
decision_date: 2026-06-13
recorded_date: 2026-06-13
provenance: contemporaneous
status: accepted
initial_leaning: apply five field-validated primitives surgically (atomic-rename, session-id checkpoint namespacing, SQLite WAL, append-only+flock, git retry-backoff), smallest-first
relations:
  - type: depends_on
    target: 2026-06-07-state-externalization-lens
---

# 2026-06-13: Multi-agent shared-state clobbering — event-sourcing, not atomic-rename

## Context
A 21-day `observe drift` pass (2026-06-13) surfaced concurrent agent sessions clobbering shared state as the #1 recurrence AND the #1 dropped-fix across all 5 repos (intel, agent-infra, phenome, genomics, hutter), 13+ sessions: `checkpoint.md` gutted (hutter lost 500+ lines), stop-hooks crashing mid-edit, git index.lock contention, JSON tracker collisions. A fix ("scope state by invocation ID") was proposed 2026-04-09 and never built; it then generalized to every repo.

Prior-art research (5 parallel Haiku agents — Claude Code / opencode+crush+goose / aider+codex+cline+cursor / orchestration frameworks / OS-git-SQLite primitives; see `artifacts/research/2026-06-13-multiagent-state-isolation/`) showed the field converged on: git worktrees (working-tree only), append-only JSONL, atomic-rename + flock, session/thread-ID namespacing, SQLite WAL+busy_timeout.

## Alternatives considered
1. **Bespoke state manager** — rejected upfront (constitution: don't reinvent; the field solved this).
2. **Five primitives, surgical, smallest-first (the initial leaning)** — atomic-rename helper for trackers+checkpoint; `checkpoint.<sid>.md` namespacing; SQLite WAL audit; append-only+flock for hooks; git retry-backoff.
3. **Event-sourcing unifying model (chosen)** — many writers append immutable events; one deterministic compactor materializes canonical views; structured mutable state → SQLite WAL; session-local files stay private and are excluded from fresh-session resume.

## Counterevidence sought
Dispatched `/critique model` (Gemini 3.5 Flash + GPT-5.5) explicitly to refute option 2. Both models converged independently (semantic convergence; the extractor's "0 cross-model agreements" is a string-match artifact). The leaning did not survive:

- **Atomic rename is not concurrency control.** It linearizes the final replace only — it prevents torn/truncated files (crash-safety) but NOT lost updates. Two writers read version v, compute v+a and v+b, both rename; last writer wins, first is silently lost. If checkpoint "gutting" was a stale-shorter-checkpoint overwriting a richer one, atomic rename only makes the loss *clean*, not *prevented*.
- **Session-ID namespacing of `checkpoint.md` fragments the single source of truth.** checkpoint.md's invariant is "the one file a resuming/compacting session reads to orient." Replacing singleton `C` with set `{C_sid}` requires an unspecified total `SelectOrMerge` function (complete, fresh, conflict-handling, bounded human burden, deterministic). latest-mtime fails completeness; concatenate fails length-bound; per-session-only fails cross-session sharing. Correct ONLY for session-local scratch, not the canonical checkpoint.
- **The plan conflates three distinct problems** under one "atomic-rename" hammer: (a) crash-safety of one write, (b) lost updates from concurrent writers, (c) coordination of which session owns a shared artifact.
- **The LLM-RMW window kills naive locking** (Gemini): agent state update = read → 30-120s inference/tool-use → write. File locks built for millisecond critical sections cannot cover a multi-minute logical transaction. → optimistic concurrency (version check) or event-sourcing with short write-side sections, never a long-held lock.
- **`flock` is not portable on macOS:** stock macOS ships `lockf(1)`, not util-linux `/usr/bin/flock`; Python `fcntl.flock` works. And advisory locks need universal participation — any rogue `sed -i` / editor save / direct agent write bypasses them.

## Decision
Adopt the **event-sourcing unifying model**, not the five-primitive patch series. The primitives are correct as *implementation details* but are an incomplete correctness model on their own.

Target architecture (per shared-state class):
| State class | Writer model | Reader model | Primitive |
|---|---|---|---|
| Session-local scratch checkpoint | single session | same session resume | `sessions/<sid>/checkpoint.md`, excluded from fresh resume |
| Canonical project checkpoint | one compactor, materialized | all fresh sessions | generated atomically from event log (or OCC version frontmatter if kept hand-edited) |
| Event history (hook state, trackers) | many appenders | aggregators/dashboards | append-only JSONL or SQLite events |
| Tracker counters/status | many writers | dashboards/hooks | SQLite WAL, not shared-JSON RMW |
| Derived summary | one compactor | all sessions | atomic rename after versioned-source read |

This aligns with existing governance: append-only is already the constitution's institutional-knowledge rule; checkpoint.md is the one place violating it (edited in place). Git index contention is a *separate* class — handled by worktree isolation (already used for code-touching subagents) + auditing that hooks/scripts use `$PWD`, not hardcoded root; retry-backoff is ergonomic fallback only.

**Sequencing (smallest-first, each independently shippable + reversible):**
1. **SQLite WAL + busy_timeout audit** (rank-1: highest impact, lowest drag) — but audit *transaction shape*, not just the PRAGMA (long transactions still fail).
2. **Stop-hook state → append-only JSONL event log** (idempotent records: event_id, session_id, monotonic ts, schema version; readers quarantine partial tail line).
3. **checkpoint.md → derived-from-journal OR OCC version frontmatter** (`version`, `last_modified_by`, `parent_hash`; writer verifies on-disk version before commit, abort+reconcile on mismatch). This is the load-bearing change — design it explicitly with resume-discovery semantics and a stress test before rollout.
4. Shared JSON trackers → SQLite events.

**Open taste call (NOT yet decided — for the operator):** how much structure a single-operator setup warrants. Full event-log + materializer is production-grade; GPT flagged it may exceed a personal repo's needs, then countered that the failure is *already* architectural (5 repos, 13+ sessions). Lighter alternative: OCC version frontmatter on a still-singleton checkpoint.md (no journal/materializer) — solves lost-updates with far less machinery. Decide per-artifact: trackers clearly want SQLite; checkpoint.md may only need OCC.

## Evidence
- Drift analysis: `artifacts/observe/2026-06-13-drift-21d/`, improvement-log promotions (9daabd7).
- Prior-art synthesis + 5 graded source files: `artifacts/research/2026-06-13-multiagent-state-isolation/`.
- Cross-model critique: `.model-review/2026-06-13-multiagent-state-fix-faee77/` (disposition.md, findings.json, coverage.json). Both axes returned exit 0; 40 findings, ~12 HIGH, full directional convergence.
- Testable predictions (from critique, to run before rollout): kill-injection writes → 0 partial files; two-writer barrier RMW → lost-token rate >0 without lock/CAS, 0 with; `command -v flock` absent on stock macOS; 5×1000 concurrent SQLite inserts → <0.1% "database is locked" under WAL+timeout+retry.

## Revisit if
- Stress-test shows OCC-frontmatter-on-singleton checkpoint fully prevents observed gutting → drop the journal/materializer (avoid over-structuring a personal repo).
- A repo's checkpoint turns out to be pure scratch (not institutional memory) → per-session namespacing becomes safe there.
- Multi-machine / synced-dir (iCloud/NFS) checkout appears → re-evaluate all file-locking assumptions (advisory locks degrade over network FS).

## Supersedes
Does not supersede; refines the 2026-04-09 "scope state by invocation ID" proposal — that instinct (thread-ID partitioning) was right for session-local state but insufficient for canonical state, which needs event-sourcing/OCC.
