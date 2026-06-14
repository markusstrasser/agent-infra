---
title: Leverage Hunt — whole RSI/agent-infra system (10-100x wins the reactive loop can't see)
date: 2026-06-14
tags: [leverage, rsi, agentlogs, governance, self-improvement]
status: active
---

# Leverage Hunt — whole agent-infra / cross-project RSI system

**Mode:** `/leverage` default (frame → five-axis checklist → measure floor → frontier-grounded
→ pilot-corrects-plan → ratchet). Surface is MATURE/heavily-instrumented → lightweight axis
checklist, not full perturbation apparatus (per skill's divergence-budget calibration).

**Consumer of the output (step 1):** the agent itself (every subagent spawn pays the always-loaded
cost; every launchd job + interactive session queries agentlogs.db) AND Markus (the governance
shrink / retirement decisions are his call). Mixed — automate the storage/code wins, surface the
governance-shrink wins.

**Prior art read before claiming novelty** (inventory-before-dispatch):
`2026-06-12-agents-rsi-gap-sweep.md` (RSI theory — accept-gate is load-bearing, PACE self-p-hacking;
already swept) and `2026-06-08-orphaned-generator-sweep.md` (dead-script surface ~14%, `just
orphan-check` ratchet already proposed). **Both ground are covered — this hunt deliberately steers
AWAY from rediscovering them** and onto three unswept surfaces.

---

## Measurement corrected the plan THREE times (the point of the pilot step)

The recon subagents asserted claims that direct measurement on the live DB falsified:

| Claim (recon agent) | Measured truth | Probe |
|---|---|---|
| "payload_json is trimmed metadata, 270MB" | **payload_json = 1,614MB** — 1.7× the text column (927MB); the SINGLE biggest store | `SELECT SUM(LENGTH(payload_json))/1048576.0 FROM events` |
| "no verbatim payload duplication; well-designed" | tool_result payloads (740MB) hold the FULL raw vendor result (entire `results[]` array, URLs, durations) — duplicates the source JSONL | `SELECT substr(payload_json,1,600) FROM events WHERE kind='tool_result'` |
| improvement-log "2 [~] retired / 191 [x] = 1%" | **17 [~] / 225 [x] / 127 [obs]** — ~7%, not 1% (recon under-counted), but the 13× add-vs-retire asymmetry is real | `grep -oE '\[(x|obs|~)\]' improvement-log.md \| sort \| uniq -c` |

Lesson re-confirmed: subagent quantitative claims are unreliable (one agent also reported "1.19M LOC
/ 161 scripts" vs actual 31K LOC / 108 scripts). Measure the principal, never trust the proxy.

---

## The three unswept leverage surfaces (ranked by factor × autonomy)

### WIN 1 — agentlogs.db storage: 3.8GB, ~50% reclaimable, no consumer loss [AUTONOMOUS, agent-infra-only]

**Axis:** simpler (storage/maintenance) + faster (every query scans a fatter B-tree).
**Floor (100x framing):** a session metadata store that keeps text-for-FTS + structured columns,
NOT verbatim vendor payloads the source JSONL already holds. The JSONL files (3.1GB) are the source
of truth; `record_refs` already stores byte-offset pointers back to them — so the verbatim payload
in SQLite is pure duplication of a recoverable source.

**Measured current state (the floor gap):**
- `events` table = 3.0GB of the 3.8GB DB. `payload_json` 1.61GB + `text` 0.93GB.
- **`status_update` events: 86,038 rows, 360MB payload, 7MB text — WRITE-ONLY.** Only ever written
  by `adapters/claude.py` + `adapters/codex.py`; **never read by any query, view, or CLI command**
  (`grep -rln status_update src/agentlogs/` → adapters only). Content is spinner text /
  "queue-operation" / "/remote-control is active" banners. Zero analytical value. **Clean ~360MB delete.**
- `trim_payload()` (index.py:188) only drops a fixed `_REDUNDANT_PAYLOAD_KEYS` set — it does NOT
  drop the bulky `results[]` / content arrays. That's why tool_result payloads are 740MB.
- **VACUUM never runs to completion.** `freelist_count = 24 pages (~100KB)` on a 3.8GB file ⇒ prune
  deletes rows but space is never reclaimed. The `reclaim rotate` daily job IS wired (04:10) but
  contends on the indexer single-writer lock (same failure as `uv cache prune` "freed 0 with 9 live
  procs", confirmed 2026-06-10). Dry-run this session hit `another indexer/prune is running`.

**Ratchet (the durable fix, three parts):**
1. **Stop storing `status_update` events at all** (adapter-level skip) — or store text only, drop
   payload. ~360MB/cycle never accumulates again. Pure win, no reader.
2. **Extend `trim_payload` to drop large content arrays** from tool_result/tool_call payloads
   (keep durationSeconds/query/metadata; drop the verbatim `results[]`/`content[]` recoverable from
   JSONL via record_refs). Estimated 400-700MB.
3. **Make VACUUM actually fire** — run `PRAGMA incremental_vacuum` or a full VACUUM in the
   reclaim-rotate window when the indexer lock is free (or switch to `auto_vacuum=INCREMENTAL` so
   freed pages return without a full rewrite). Without this, (1)+(2) free rows but not disk.

**Honest factor:** not 10x on the file, but **~1.5-2× smaller DB (3.8GB → ~2GB)** + faster FTS/scan
on every query the 2h launchd jobs + interactive sessions run, + bounded growth. Autonomous,
reversible (rebuildable from JSONL), one clear approach. Pilot blocked only by the live lock — the
code changes are safe to make now; the data backfill runs in the reclaim window.

### WIN 2 — close the loop on the NEW RSI machinery: report-without-actuator is repeated 4× [PROPOSE — touches the loop]

**Axis:** unnecessary (the human step that shouldn't exist) + better (loop actually closes).
This is the project's #1 named disease — *consumption-over-autonomy* — recurring at the META layer,
inside the very machinery built to fight it. Four detectors PRODUCE a verdict and DEAD-END:

| Producer | Emits | Actuator | Gap |
|---|---|---|---|
| `hook-roi.py` | "DEMOTE / CULL this advisory (high fires, 0 blocks)" | none — human-gated | noisy hook lives until manual review; agent learns to ignore advisories (cried-wolf) |
| `buildthenundo.py` | 8 build-then-undo instances (P11 threshold=10) | report-only in gov.py | no gate; lived months as a measured contradiction |
| `predictions.py` (shipped 2026-06-14) | DUE/unresolved predictions | drift-sentinel surfaces; **no REGISTRATION trigger** | write-only risk: 4 seed predictions, nothing appends new ones on ship |
| improvement-log | 225 [x] vs 17 [~] | manual retirement only | 13× add-vs-retire; shrink-as-capability-rises is dormant |

**The single structural fix (not four):** the frontier already named the missing piece —
`2026-06-12-rsi-gap-sweep` deferred **AHE's "falsifiable contract"** (every self-improvement edit
ships a self-declared prediction verified next round) and **PACE's e-process accept-gate** (greedy
keep-if-score-up = self-p-hacking; the ACCEPT-GATE is the load-bearing component). The prediction
ledger is half of AHE already shipped — it just lacks the *registration trigger*. Wiring
"every [ ]→[x] in improvement-log auto-appends a skeleton prediction + a retirement check-date"
closes the registration gap AND the retirement gap in one mechanism: a scaffold that passes its
verifier on the check-date auto-surfaces as a retirement candidate. **This is the load-bearing RSI
win** — it makes the loop self-closing instead of human-polled.

**Honest factor:** can't size in factors (it's a closure, not a speedup). Value = the declining-
supervision objective itself becomes measurable (registration rate + retirement rate as KPIs).
Propose-and-wait: touches the loop's actuator layer, multiple viable designs (auto-gate vs
surface-candidate), Markus's call on how hard to auto-act.

### WIN 3 — the 14-job launchd mesh + 108-script surface: consolidation, not deletion [PROPOSE]

**Axis:** simpler (maintenance/complexity). 14 launchd jobs, 108 .py scripts (31K LOC), 240 research
memos, 37 decisions. The orphaned-generator sweep (2026-06-08) already proposed `just orphan-check`
as the ratchet for dead scripts — **check whether it shipped and is firing**; if yes, this is
covered. The genuinely new observation: ~6 daily launchd jobs each write a gitignored digest
surfaced at SessionStart (blindspot, drift, gov, priorities, skill-usage, vendor). That's 6
independent SessionStart surface hooks — a **digest-fragmentation** smell. Consolidation candidate:
one `morning-digest` job that merges the report-only halves, one SessionStart surface. Low factor,
pure maintenance — gate on whether the fragmentation actually costs (measure SessionStart latency +
digest read-rate first). Flagged, NOT recommended without that measurement.

---

## What I deliberately did NOT do (anti-rediscovery)
- Did not re-sweep dead scripts (orphaned-generator-sweep 2026-06-08 owns this + proposed the ratchet).
- Did not re-derive RSI theory (rsi-gap-sweep 2026-06-12 owns it: accept-gate load-bearing, PACE,
  weight-level dead at frontier).
- Did not web-search the storage design — the principal check is the DB measurement (done); the
  field already converged on "SQLite/WAL is right at this scale" (multiagent-state memo 2026-06-13).

## Pre-registered factors (verify after WIN 1 ships)
- DB size: 3.8GB → target <2.2GB after status_update drop + payload trim + VACUUM.
- status_update rows in events: 86K → 0 going forward (adapter skip).
- freelist after VACUUM fires: should briefly spike then file shrinks (today: stuck at 24 pages).
