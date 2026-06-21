---
title: Leverage Hunt — RSI loop post-observe v3 (the win is actuation metadata, not another lens)
date: 2026-06-21
tags: [leverage, rsi, observe, maintain-tick, consumption-over-autonomy, gate-ergonomics]
status: active
---

# Leverage Hunt — RSI loop post-observe v3

**Mode:** `/leverage` default on a **mature, heavily-swept surface** (constitution,
06-14/06-19 RSI hunts, observe v2+v3 today). Divergence budget → **VOI probe first**:
did the already-ranked wins actuate? Fresh five-axis brainstorm would only rediscover.

**Consumer:** the agent loop (pays gate friction + idle motor) + Markus (governance
shrink / tier-3 flips).

**Complement to observe v3:** observe found **11 valid `[ ]` promotions** today
(v2×3 + v3×8). This hunt does **not** re-derive them — it asks why the RSI motor
still cannot pick any of them.

---

## VOI probe (measured 2026-06-21)

| Prior ranked win | Actuated? | Probe |
|---|---|---|
| predict-then-falsify **accept-gate** (06-19 #1) | **NO** | `predictions.jsonl` 26 rows; 0 resolutions; `auto-resolve --dry-run` → 0 refuted; `resolution_rate = 0/26` |
| maintain-tick **motor** (06-19 audit) | **IDLE** | `maintain_tick.py --list` → **0 tier-0** candidates; 1 tier-0E; **16 prose `[ ]` need classification** |
| agentlogs **payload trim** (06-14 WIN1) | **NO** | DB **4.7GB** (↑ from 3.8GB); `status_update` **190MB** write-only (94,959 rows); `tool_result` payload **767MB** |
| gate-ergonomics transform (06-17 embed-once) | **NO** | poll-hook, bare-python3, modal PATH still `[ ]` after observe v2/v3 |
| observe routing (Cursor subagents) | **YES** | skills/observe SKILL.md + `observe_bulk` profile shipped this session |
| agentlogs indexer reliability | **YES** | launchd `LastExitStatus=0`; scaled timeout + batched writes (uncommitted) |

**Meta-finding:** sensors improved (observe v3, indexer green); **actuators did not move**.
Same consumption-over-autonomy disease at the layer built to cure it.

---

## Five-axis checklist → chosen axis

| Axis | Gap size | Notes |
|------|----------|-------|
| Faster | medium | Gate-induced retries (bare-python3, modal) — measurable waste, not 10× |
| Better | **large** | Loop doesn't close: findings → `[ ]` → human `/improve` session |
| More | small | Motor + registry exist; capability gap is **metadata**, not code |
| Simpler | medium | agentlogs bloat + gov rule LOC **+608** vs shrink telos |
| Unnecessary | **large** | Human classification step for every observe promotion |

**Chosen:** **Unnecessary + Better** — remove the human routing step between observe
promotion and maintain-tick pick; instrument closure (resolution_rate, motor picks/week).

NOT *faster* as the headline — this is loop closure, not wall-clock.

---

## Measured floor

| Metric | Today | Floor (100× framing) |
|--------|-------|----------------------|
| Observe → motor latency | ∞ (manual) | Same-session registry insert → next `pulse-tick` draft |
| `maintain_tick --list` tier-0 | 0 | ≥1 pickable local hook/recipe per observe batch |
| `resolution_rate` | 0/26 | >0 within 7d of registration; refuted → retirement candidate |
| Gate-induced `agent_miss` share | ~50% (06-17 cluster) | Transform gates; block-then-retry <20% |
| agentlogs `status_update` payload | 190MB | 0MB (delete kind or never store payload) |
| improvement-log `[ ]` (actionable) | **106** | drains faster than capture (negative net open) |

---

## Ranked wins (maintenance-gated, session-level impact)

### WIN 1 — Observe promotion → `maintain-candidates.json` bridge [AUTONOMOUS, agent-infra]

**What:** When `/observe` promotes `[ ]`, emit **structured fields** the motor already
consumes (`blast_radius`, `evidence_sessions`, `checkable`, `low_downside`,
`clear_win_vs_baseline`, `build_kind`) — either inline in the log (YAML frontmatter
block) or append to `config/maintain-candidates.json` in the same session.

**Why 10× at session level:** Today observe v3 added 8 net-new items; motor sees
**16 unclassified prose items** and picks **nothing**. Every observe run multiplies
human drain work without moving the motor. One bridge turns retrospective harvest into
prospective actuation.

**Immediate tier-0 candidates from v2/v3 (agent-infra-local, checkable):**

| id | source | build_kind |
|----|--------|------------|
| `pretool-uv-run-nudge` | observe v2 bare-python3 | hook |
| `pretool-modal-path` | observe v3 modal PATH | hook |
| `critique-skip-on-refute` | observe v2 read-only refute | skill-router doc / refute.sh |

**Consumer:** `maintain_tick.py` (preferred registry source) + `pulse-tick` schedule.

**Ratchet:** observe SKILL.md promotion-sink template + test that a sample promotion
parses to ≥1 registry row.

---

### WIN 2 — Gate ergonomics batch (transform, don't block) [mixed tier]

**What:** Ship the three **highest-frequency, agent-infra-local** gate fixes from
observe v2/v3 as one motor cycle (or one interactive session):

1. PreToolUse bash nudge: `python3` → `uv run` when `pyproject.toml` present
2. PreToolUse / launchd PATH: `modal` shim
3. Poll-hook session-scoped bypass for parallel refute fan-out

**Measured pain (observe v3 citations):** `missing-module:duckdb`×46,
`pipeline_stages`×40, `command-not-found:modal`×16 / 14d — all **interactive agent**,
not cron.

**Why leverage > another observe:** These are **success-path taxes** (agents self-heal);
observe sees them; only hooks change the slope.

**Honest factor:** Per-hook wins are ~1 turn saved per incident, not 100× — but
`frequency × blocking-fraction` across 2355 sessions/7d is the session-level win.
Aligns with 06-17 finding: **50% of agent_miss is gate-induced**.

**Consumer:** every Bash tool call + parallel paper/refute sweeps.

---

### WIN 3 — Finish predict-then-falsify **closure** [partially shipped]

**Residue (06-19 hunt, still open):**

1. `maintain_tick --ablate` → `predictions.resolve(refuted|confirmed)` on scaffold removal
2. `refuted` resolution → mint retirement candidate (`--subtract` lane)

**Probe today:** auto-resolve ships but **0/26 resolve** — predictions are write-only
ledger entries routed to human questions.

**Consumer:** `questions_view` DUE count; gov-shrink retirement proposals.

**Not re-derived:** see `research/2026-06-19-leverage-rsi-autoresearch-actuation-gap.md`.

---

### WIN 4 — agentlogs `status_update` purge [AUTONOMOUS, agent-infra-only]

**Measured:** 94,959 rows, **190MB** `payload_json`, **zero downstream readers**
(same WIN1 as 06-14; DB grew instead of shrinking).

**Pilot:** migration to stop storing payload (or drop kind) + `VACUUM`; re-index
from JSONL via `record_refs`.

**Honest factor:** ~4% DB size per kind; full WIN1 (tool_result dedup) is larger but
needs migration design. status_update is the **smallest reversible delete**.

---

### SKIP (already hunted / lower VOI now)

- **Lazy-import genomics MCP** — valid, lives in genomics; cross-repo tier-2
- **New observe modes / Flash routing** — shipped this session
- **Sixth RSI theory steal** — 06-19 synthesis: integrate bolt-ons, don't rebuild
- **Whale transcript indexer backlog** — operational drain, not structural

---

## Adversarial buckets (/critique-style, inline)

| Risk | Mitigation |
|------|------------|
| Auto-registering tier-0 from prose misclassifies cross-repo work | Registry requires explicit `blast_radius`; motor defaults conservative on prose |
| Gate transforms hide real errors | Fail-open nudges only; destructive guards stay block |
| predictions auto-resolve false refute | Scope to PROXY-FREE commit-reachability (already shipped); semantic ablation stays operator-gated |
| agentlogs delete loses forensics | JSONL source of truth + `record_refs` offsets |

---

## Recommended sequence (one session each)

1. **WIN 1 bridge** — register 3 agent-infra v2/v3 items in `maintain-candidates.json`; run `maintain_tick --list` until tier-0 ≥ 1
2. **WIN 2** — ship `pretool-uv-run-nudge` + `pretool-modal-path` (motor draft or direct — reversible hooks)
3. **WIN 3 wire** — `maintain_tick --ablate` calls `predictions.resolve`
4. **WIN 4 pilot** — count-only migration script for `status_update` payload nulling

---

## Ratchet

- `just maintain-tick --list` in `pulse status` footer when tier-0 = 0 and log_open > 10
- Observe promotion template requires registry fields (architecture over instructions)
- KPI: `resolution_rate`, motor drafts/week, net `[ ]` delta (capture − drain)

---

## What I did NOT do

- Re-run observe (v3 artifacts are input, not re-derived)
- Re-rank 06-19 steals
- Auto-edit `maintain-candidates.json` (leverage proposes; ship is next session)
- Quote per-run testmon-style factors without session-level frequency math
