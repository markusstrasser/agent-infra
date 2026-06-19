# Vercel Eve vs agent-infra — research + simulated steals

**Date:** 2026-06-17  
**Question:** Is Eve better than what we have? What can we steal, with evidence?  
**Sources:** [Vercel blog (2026-06-17)](https://vercel.com/blog/introducing-eve), [eve docs](https://vercel.com/docs/eve), [github.com/vercel/eve](https://github.com/vercel/eve), live agent-infra probes below.

---

## Executive verdict

**Eve is not a replacement** for agent-infra. It solves *deployable product agents* (Slack bots, cron reports, multi-channel surfaces) on Vercel. Agent-infra solves *coding-agent supervision* across research repos with an RSI loop and declining-supervision objective.

**Three steals are provably cheap** (existing data + existing tests; ~43s bundle). **Two are medium** (new thin scripts, no platform migration). **Three are correctly deferred** (durability, channels, full Eve port).

---

## Eve — what it actually ships

| Capability | Mechanism | Source |
|------------|-----------|--------|
| Agent shape | `agent/` tree — instructions, tools, skills, subagents, channels, schedules | [blog](https://vercel.com/blog/introducing-eve), [concepts](https://vercel.com/docs/eve/concepts) |
| Durable sessions | Vercel Workflow — checkpointed steps, resume after deploy/crash | blog § "durable session" |
| Sandbox | Isolated compute (Vercel Sandbox / Docker locally) | blog § "sandbox" |
| Approvals | `needsApproval: boolean \| ({ toolInput }) => boolean` on `defineTool` | blog § "human-in-the-loop" |
| Connections | MCP/OpenAPI + auth brokering (model never sees creds) | blog § "connections" |
| Channels | HTTP + Slack/Discord/etc. — same agent everywhere | blog § "channels" |
| Traces | OTel spans: `ai.eve.turn` → `ai.streamText` → `ai.toolCall` | blog § "tracing" |
| Evals | `defineEval` + `eve eval` in CI as deploy gate | blog § "evals" |
| Deploy | Ordinary `vercel deploy`; preview per commit | blog § "ship it" |

**Platform coupling:** full value assumes Vercel Workflow, Sandbox, Connect, AI Gateway, Observability dashboard. Open-source framework; production batteries are Vercel-shaped.

---

## What we already have (mapped to Eve)

| Eve feature | Our analog | Gap |
|-------------|------------|-----|
| `needsApproval` | 17+ pretool hooks with `decision:block` / `exit 2`; `pretool-cost-guard.sh` threshold block/warn | **Scattered** — no unified tier registry or input-scoped predicate table |
| `defineEval` / CI gate | `just smoke` (~16s+), `hooks_smoke` (262 pass), `test-health`, skill-routing locked evals, shadow windows (`clash-detect`, `risky-diff-review`) | **Fragmented** — no single `harness-eval` entry for hook-only changes |
| OTel turn traces | `agentlogs.db`: `events`, `tool_calls`, `parent_event_id`, `permission_denied` (144 rows total) | **No replay CLI** — `export_sessions_for_emb.py` strips tool spans for embedding |
| Durable workflow | Orchestrator **eradicated** 2026-06-07; interactive `/loop` primary | **By design** — logs durable, in-flight work is not |
| Filesystem agent tree | `skills/`, `skills/hooks/`, per-repo `.claude/` | **No canonical `agent/` manifest** — discoverability via `just orient` |
| Channels | Claude Code / Cursor / Codex in IDE | Different surface — not building Slack bots here |
| Preview deploy | Git + shadow JSONL (`~/.claude/clash-shadow.jsonl`, `risky-diff-shadow.jsonl`) | **Already Eve-like** for harness; promote/cut dates pre-registered |

**Runs indexed (21d):** claude 4.0k runs (approval_mode: bypass/dontAsk/default/auto…), cursor 850, codex 563. `approval_mode` is captured on `runs` but not yet used as a supervision signal.

---

## Simulations run (2026-06-17)

### 1. Eve-like span tree from agentlogs — **feasible**

Probed `~/.claude/agentlogs.db` on a recent cursor session (`d6b1de56`, 248 lines):

- 1 run, 11 sequenced events, 8 `tool_calls` (`SemanticSearch`, `Read`, `Glob`, `Grep`)
- `events.kind` includes `user_message`, `assistant_message`; `tool_calls` has `args_json`, `status`, timestamps
- Schema already has `parent_event_id` for hierarchy (migration 005 indexed it for ingest perf)

**Conclusion:** A `session_trace.py` can emit Eve-shaped NDJSON without schema migration. Missing piece is a **viewer**, not data.

### 2. Harness-eval bundle timing — **viable**

Ran back-to-back (agent-infra cwd):

| Step | Result | Time |
|------|--------|------|
| `hooks_smoke.py --timeout 8` | 262 pass, 1 async_timeout | ~25s |
| `orient.py --drift` | 14/14 jobs in CLAUDE.md | <1s |
| `test_userprompt_prior_context.py` | 15/15 | <1s |
| `pytest scripts/tests/test_orient.py` | 9/9 | ~18s |
| **Total** | all green | **~43s** |

`just smoke` already includes hooks_smoke + orient drift but is heavier (MCP contract, skill-routing eval, codex parity) and failed this run on index check — too broad for hook-only edits.

### 3. Approval-tier inventory — **partial coverage**

| Class | Count (skills/hooks) | Examples |
|-------|---------------------|----------|
| Block-ish pretools | 17 files with `decision:block` | data-guard, append-only, git-add-all |
| Exit-2 shells | 26 | bash-loop-guard, cost-guard |
| Warn/advisory | 64 | inventory-dispatch, prior-context |

`pretool-cost-guard.sh` is the closest Eve `needsApproval` analog: **predicate on input** (`estimateScanGb` equivalent = daily spend threshold) → block vs warn.

**agentlogs permission ground truth:** only `permission_denied` (144 lifetime); no `permission_requested` indexed. Cannot yet calibrate hook approvals against vendor permission UX — gap for precision-weighting edge ② in ARCHITECTURE.md.

### 4. Shadow / preview gates — **already shipping**

- `clash-detect` — LLM shadow, promote/cut ~2 weeks (`just clash-detect --summary`)
- `risky-diff-review` — one-shot 2026-06-21, scans git for risky harness diffs without review signal

These **are** Eve's "eval on deploy" pattern applied to harness changes, with human promote/cut instead of auto-block.

---

## Proposals (ranked)

### P1 — `just harness-eval` (wire existing; **do first**)

**What:** Thin recipe running harness-specific gates only:

```
hooks-smoke → orient --drift → prior-context selftest → test_orient
```

**Why:** Eve's `eve eval` blocks bad deploys; we block bad *hook* deploys. Simulation: 43s, all green today.

**Pre-reg PASS:** zero failures for 14d on daily `test-health` + manual runs after hook edits.  
**Pre-reg FAIL:** any silently-dead hook class (SyntaxError behind fail-open trap) reaches main without smoke catch — already happened 2026-06-11; this tightens the loop.

**Cost:** ~30 LOC justfile + one line in MAINTAIN.md. **Blast radius:** agent-infra only. **Maintenance:** near-zero (reuses existing scripts).

---

### P2 — Approval-tier manifest (`config/approval-tiers.json` + doctor check)

**What:** Single registry:

```json
{
  "tiers": [
    {"id": "irreversible_write", "action": "block", "hooks": ["pretool-data-guard", "pretool-append-only-guard"]},
    {"id": "spend_threshold", "action": "predicate", "hook": "pretool-cost-guard", "note": "warn $500 / block $1000"},
    {"id": "advisory_context", "action": "warn", "hooks": ["userprompt-prior-context", "pretool-inventory-dispatch"]}
  ]
}
```

Doctor surfaces: hook registered but not in manifest, manifest entry but hook missing.

**Why:** Eve's `needsApproval` is one field; our equivalent is **17 block hooks + scattered predicates**. Registry externalizes recoverable bookkeeping (state-externalization lens) without rewriting hooks.

**Pre-reg PASS:** new pretool guard added → manifest updated in same commit (doctor enforces).  
**NOT doing:** unified pretool router (high blast radius, shared infra).

**Cost:** ~80 LOC manifest + doctor check + test. **Blast radius:** agent-infra governance; hooks stay in skills/.

---

### P3 — `just session-trace <session-uuid>` (replay CLI)

**What:** `scripts/session_trace.py` — query agentlogs, emit NDJSON span tree:

```
session.turn
├── event.user_message
├── event.assistant_message
└── tool_call.Read (status, args preview)
```

Optional `--format otel` for export to Honeycomb/etc.

**Why:** Eve's Agent Runs tab answers "what did it do?" — we have the data but no one-command replay. Complements blindspot-miner (semantic) with structural forensics.

**Pre-reg PASS:** for 5 sampled sessions, trace tool-call count within ±1 of manual JSONL count.  
**Simulation:** prototype query returned 8 tools / 11 events on live cursor session — data sufficient.

**Cost:** ~120 LOC script + just recipe + 3 pytest fixtures. **Maintenance:** low (read-only query).

---

### P4 — Use `runs.approval_mode` in supervision-kpi (extend existing metric)

**What:** Segment AIR / supervision ratio by `approval_mode` (bypassPermissions vs default vs dontAsk).

**Why:** Eve parks sessions on approval; we already index approval mode but don't trend it. Cheap signal for "supervision dropped because mode changed" vs "hook worked."

**Pre-reg:** if bypassPermissions share rises 21d while AIR drops, flag in drift-sentinel (problem-hiding guard edge ③).

**Cost:** ~40 LOC in `supervision-kpi.py`. **Defer if:** approval_mode null rate too high (cursor 100% null today).

---

## Explicitly NOT proposing

| Idea | Why not |
|------|---------|
| Migrate to Eve / Vercel | Replaces Claude/Cursor interactive model; platform lock-in; wrong layer |
| Vercel Workflow durability | Orchestrator dead by decision; revive only on measured headless multi-hour demand |
| Slack channels via Eve | No product-agent use case in portfolio; `just questions` covers human gate |
| Unified `agent/` tree rewrite | skills/hooks work; cost >> benefit; orient already derives live inventory |
| Auto-promote shadow gates to block | Constitution P3 — measure first; clash/risky-diff still in shadow windows |

---

## Comparison summary

```
Eve                          agent-infra
─────────────────────────────────────────────────────
Build deployable agents      Improve coding-agent harness
One agent directory          Cross-project RSI loop
Vercel-hosted runtime        Local IDE + launchd miners
needsApproval on tools       pretool hooks (scattered)
eve eval in CI               smoke + test-health + shadows
Workflow durability          agentlogs durability (post-hoc)
Declining $/agent shipped    Declining supervision (AIR)
```

**Steal the patterns, not the platform.**

---

## Recommended next session (if approved)

1. Ship P1 (`just harness-eval`) — single commit, verify 43s green  
2. Ship P2 manifest + doctor — single commit  
3. Spike P3 `session_trace.py` with 3 tests — separate commit  

No Eve dependency. No shared-hook deploy without cross-model review (constitution P12).
