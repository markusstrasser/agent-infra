---
title: Multi-agent shared-state coordination — prior-art landscape & verdict
date: 2026-06-13
tags: [multi-agent, worktree, isolation, state, coordination, orchestrator]
status: active
---

# Multi-agent shared-state coordination — prior-art landscape & verdict

**Consult before:** building ANY multi-agent state/locking/coordination machinery; proposing
event-sourcing/OCC/file-locking for agent state; choosing an orchestrator; "isn't this solved?"
questions about concurrent agents on one repo. Decision: `decisions/2026-06-13-multiagent-shared-state-event-sourcing.md`.

## The question
Concurrent agent sessions (Claude Code + Codex) on ONE local checkout clobber shared mutable
state (`checkpoint.md`, `current-session-id`, JSON trackers). Surfaced as the #1 recurrence by the
2026-06-13 `observe drift` pass (13+ sessions, all 5 repos). Is this solved upstream?

## Verdict: YES — isolate per agent, merge via git. Zero shared mutable state.
The entire funded field converged on the same answer, and it matches our own prior memos
(`caid-multi-agent-swe-2026-03.md`, `2026-06-12-symphony-orchestrator-reference.md`) — which a
prior-art pass should have hit FIRST (see "Process failure" below).

- **CAID** (arXiv:2603.21489, VERIFIED): git **worktree isolation beats soft isolation by 7.8pp**;
  soft isolation *hurts* vs single-agent; optimal **2-4 agents**; 3-5× cost, no wall-clock speedup.
  Coordination backbone = **git primitives, not a state layer**: worktree=isolate, commit=signal,
  merge=integrate, test=gate.
- **Symphony** (openai/symphony): central orchestrator, **no durable DB** (queue durability
  outsourced; orchestrator state disposable, reconstructed by reconciliation), **hard per-issue
  isolation** (full clones + symlink-escape defense). "No orchestrator" is workload-scoped.
- **Anthropic's own multi-agent research system**: orchestrator-worker; lead spawns workers in
  parallel, waits, synthesizes; results flow up as artifacts; **no shared-state DB**.
- **Cloud products** (Codex cloud, Cursor background agents, Devin, Jules; infra: e2b/Daytona/
  container-use): universally **isolated sandbox/clone per agent → merge via PR**. Firecracker
  microVM / container / gVisor vary; the *pattern* is identical and borrowable locally at $0 via
  git worktrees (+ optional Docker for runtime isolation).

## Tool landscape (dependency-eval, 2026-06-13)
| Class | Examples | Borrowable? |
|---|---|---|
| Worktree orchestrators | Claude Squad, Conductor, (Crystal/vibe-kanban) | Only earns keep on **parallel multi-task fan-out**; for serial/interactive peers, bare `claude --worktree` is the lever |
| Coordination memory | claude-flow (SQLite hive-mind) | Over-built for 2-4 agents; SKIP |
| Frameworks | LangGraph (checkpointers/reducers), Temporal | LangGraph patterns transfer (thread-id, reducers, SQLite checkpoint); Temporal = server overkill |
| Native | Claude Code `--worktree` (`baseRef:head`), Agent `isolation:"worktree"` | Already adopted; the answer |

## What this means for us (the decision)
- **Primary fix = isolation** (already used for code subagents; the gap was peer INTERACTIVE
  sessions + checkpoint/tracker files). Shipped: global CLAUDE.md `--worktree` convention +
  `sessionstart-peer-session-warn.sh`.
- **Event-sourcing / OCC / atomic-rename / flock = NOT NEEDED.** The only irreducibly-shared store
  is `agentlogs.db`, already WAL + `busy_timeout=30000` (`src/agentlogs/db.py`). launchd state is
  single-writer. Five turns of proposed locking machinery collapsed to one convention + one hook.

## Caveats
- **Vendor-slop:** the landscape pass leaned on blogs; product specifics (tool "EOL" dates,
  funding, "Nx velocity", successor naming) are UNVERIFIED and not relied upon. Only the convergent
  *principle* is trusted — it agrees across 4 independent agents + CAID (real paper) + Symphony memo.
- Multi-machine / iCloud/NFS checkout would break advisory file-locking assumptions (n/a today).

## Process failure (recorded so the next agent avoids it)
This landscape was partly **re-derived** (~245K Haiku tokens) despite `caid-*` and `symphony-*`
already existing in `research/`. The `pretool-inventory-dispatch.py` gate didn't catch it: (1) it
mined only `git log --since=21.days` (the March CAID memo invisible), (2) the topic word "worktree"
tripped its isolation-skip. **Fixed 2026-06-13** (skills@1bc125d): the gate now scans the
research-index + `research/`/`decisions/` filenames and checks the structured isolation field.
Lesson: grep `research/` + the index BEFORE fanning out research subagents.

## Pointers
- Raw research: `artifacts/research/2026-06-13-multiagent-state-isolation/` (CLIs+primitives),
  `artifacts/research/2026-06-13-orchestrator-tools/` (orchestrators+cloud).
- Decision + cross-model critique: `decisions/2026-06-13-multiagent-shared-state-event-sourcing.md`.
