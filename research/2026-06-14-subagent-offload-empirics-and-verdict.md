---
title: Subagent offload for the main Opus agent — empirics + cross-model verdict (genomics/phenome)
date: 2026-06-14
tags: [subagents, context-shield, genomics, phenome, modal, state-externalization, cross-model-review]
status: active
---

# Subagent offload for the main Opus agent — empirics + verdict

**Consult before:** proposing "delegate X to a subagent to take load off the main agent";
building a status/watcher/poller subagent; assuming a subagent shields context cheaply.
This is the measurement `2026-06-14-git-janitor-subagent-verdict.md` asked for ("measure
first before building").

## Question
Going through recent phenome + genomics Opus sessions: which workloads should move to
subagents to reduce load on the main Opus agent?

## Method
agentlogs.db, claude(Opus) sessions, last 21d. Tool calls re-segmented into **main-thread
runs vs subagent runs** (main run = the run containing `Agent` dispatches; `runs ≈
subagent_count + 1` confirms subagents are indexed as separate runs). The re-segmentation
is load-bearing: a naive join lumps subagent tool calls in with the main thread and
overstates main-thread load.

## Subagent context mechanics (Claude Code docs, verified)
| # | Fact | Implication |
|---|------|-------------|
| 1 | Subagent gets a FRESH context — does NOT see parent conversation/file-reads | Shields verbose OUTPUT (the real win) |
| 2 | Non-fork subagent RE-PAYS ~6–9K tok of global+project CLAUDE.md+rules per dispatch | "Being a subagent" is not free; one-offs pay full freight |
| 3 | **Explore + Plan skip the CLAUDE.md/rules load entirely** | Cheapest shields |
| 4 | Model INHERITS parent (Opus) unless the def sets `model:` | A cheap-model def is what saves tokens, not delegation per se |
| 5 | Agent tool BLOCKS the parent unless `run_in_background` | Concurrency is opt-in |
| 6 | "Persistent memory" only exists if the agent writes a memory FILE | Not automatic (GPT-5.5 critique) |

## Load split — main thread vs subagent (the corrected picture)
| Workload | Main | Sub | Verdict |
|---|---|---|---|
| genomics modal/pipeline polling | 1490 | 296 | 83% in MAIN — real problem |
| phenome research | 83 | 972 | 92% already delegated — NOT a target |
| genomics research | 134 | 347 | 72% delegated — largely done |
| phenome browser | 30 | 232 | 89% already delegated — NOT a target |
| Read (both) | ~57% | ~43% | headroom for Explore |
| Edit/Write (both) | ~73% | ~27% | core task work — not shieldable |

Two v1 candidates (research routing, browser subagent) were **falsified** by the
re-segmentation — already delegated. git-janitor confirmed NOT a top sink (Bash failures
are modal-polling + filesystem exploration, not git/hook retries).

## The genomics modal-polling sink
- 1490 main-thread status calls + raw `modal app list`/`app logs`/`sleep N; recheck`/
  `cat <detached-run-transcript>.jsonl` (one transcript cat-polled 8+ times).
- **Status MCP tools at 100% error**: sample_state 101/101, pipeline_status 27/27,
  triage 201/201, attempt_receipt 65/65, run_frontier 30/30 (424 calls). When they fail
  the agent falls back to raw modal Bash → compounds the flood. PRIORITIES.md independently
  flags `broken-cli:corpus (missing modal dep)`.
- Caveat (probe-primitive-first): "error" may be partly a status-encoding artifact — probe
  per-tool before asserting all are broken.

## Verdict (cross-model: Gemini 3.5 Flash + GPT-5.5, CONVERGENT)
**Do NOT build a pipeline-watcher subagent.** Both models independently: an LLM agent
parsing status streams *because the status tools are broken* is "agent theater" / "relocates
failure" — a P1 (architecture-over-instructions) violation. Token math: ~100–300 main-thread
tokens per raw poll vs 6–9K subagent bootstrap → 10 polls = 60–90K tokens for what a shell
command does free.

**The dominant fix instead (state externalization, native-first):**
1. **Probe + fix the broken status MCP tools.** Likely root cause: MCP subprocess not
   inheriting venv/PATH/Modal creds (Gemini hypothesis — PROBE, don't assume).
2. **Push poll/wait/tail into a deterministic layer**: `launchd` daemon or `just
   watch-pipeline` polls Modal → writes `.genomics/state.json` (with staleness/mtime guard);
   status MCP tools READ the cache. N model-mediated polls → O(1) status reads.
3. Add ROI instrumentation (agentlogs SQL view: main vs sub calls, errors, tokens) before
   authorizing any new scoped agent (GPT gate).

## What survives as real subagent work
- **Lean on `Explore`** for the 57%-main-thread Read-hunting — native, cheapest shield, no
  new def. Pure usage shift.
- **Scoped `claim-verifier` (genomics has none) / test-fixer (phenome)** — GATED: admit only
  if the task class recurs ≥10×/21d AND uses a cheap-model def AND file-backed memory AND an
  A/B shows ≥25% Opus-equiv cost cut with no worse correction rate. Genomics claim-curation
  (~13 general-purpose dispatches/21d) passes recurrence; the rest is unproven.

## Net
The diagnosis (genomics main thread drowns in modal polling) is correct; the v1 SOLUTION
(watcher subagent) is wrong. The win is **deterministic state externalization in the genomics
repo**, not a new agent. Subagents shield *output*, not *system-prompt overhead* — so they
pay off only for large-output, cheap-model, recurring workloads. Most of what looked
delegable here is either already delegated, core task work, or better handled by fixing tools.

## Artifacts
- Critique: `.model-review/2026-06-14-subagent-offload-60b99c/` (31 findings, 1 cross-model).
- Context packet: `.model-review/subagent-offload-context.md`.
