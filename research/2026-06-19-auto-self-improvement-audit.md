---
title: Automatic self-improvement audit — Jun 18–19, 2026
date: 2026-06-19
tags: [observe, rsi, autonomy, audit, act-drain, blindspot, maintain]
status: active
window: 2026-06-18 → 2026-06-19 (48h)
method: observe-style retrospective + ground-truth probes (see Verification)
---

# Automatic self-improvement audit — Jun 18–19

**Question:** What did the RSI loop do autonomously in the last 48h, and what integration/build work *could* have happened without Markus?

**Verdict (after probes):** Sensors and capture are healthy. **Synthesis, build, and disposition are human-gated.** The dominant failure mode is not wasted boilerplate (0.6% supervision waste) — it is **84 loop misses in 48h** (blindspot) that only become architecture when someone starts a session and asks.

---

## Verification (noise removed)

Probes run before writing this memo. First-pass claims corrected where falsified.

| Claim | First pass | Verified | Probe |
|-------|-----------|----------|-------|
| act-drain not scheduled | "plist missing → manual" | **FALSE** — runs daily 06:45 from `ops/launchd/com.agent-infra.act-drain.plist` (loaded in launchctl; symlink not in `~/Library/LaunchAgents/` but job is live) | `launchctl print`, `~/.claude/logs/act-drain.out` |
| Wasted supervision high | implied by blindspot volume | **0.6%** (11/1885 user msgs, 9 CORRECTION) — low lexical waste, high semantic misses | `extract_supervision.py --days 2` |
| Blindspot "166 misses" in window | cited 7d digest | **84/48h** (41 over_caution, 35 rediscovery) — use 2d for this audit | `blindspot_miner.py --days 2` (emb env) |
| Trending scout → orphan builds | vendor gap active | **0 un-harvested** trending memos in 90d | `orphan_findings.py` |
| Actionable backlog panic | implied large queue | **11 `[ ]` open** in improvement-log (F1 two-stream model holds) | grep + `loop_funnel.py` |
| `approval-tiers.json` routes builds | proposed extend it | **WRONG SURFACE** — file maps **pretool hooks** (block/predicate/warn), not act-drain disposition / auto-ship | read `config/approval-tiers.json` |
| maintain loop running | implied stalled | **Last maintain-tick: 2026-06-14** (5 days dead) | `maintenance-actions.jsonl` tail |
| steer-mine scheduled | not in launchd | **CONFIRMED manual** — ledger scans 2026-06-19 09:23–09:25Z, 495 signals, ~$5.35 | `~/.claude/steer-mining/scanned_ledger.jsonl` |
| Sessions in window | 327 | **327** (219 Jun 18, 108 Jun 19) | agentlogs `sessions` table |
| Substantive commits | ~45 | **52 total**: 13 auto-checkpoint WIP, 2 vendor-scheduled, **37 session/human** | `git log --since=2026-06-18` |

**Noise dropped from analysis:**
- **7d blindspot totals** (166) — misleading for a 2d audit; 84 is the operative number.
- **"act-drain not installed"** — job runs; only the LaunchAgents symlink is absent.
- **"vendor-scout orphans"** — ratchet green; scout memos are being harvested.
- **Supervision % alone** — structurally blind to semantic loop misses (observe skill caveat applies).

---

## Scale (48h)

| Metric | Value |
|--------|-------|
| Sessions (all vendors) | 327 |
| User messages | 1,885 |
| Wasted supervision | 0.6% (9 corrections) |
| Blindspot loop misses | **84** (41 over_caution, 35 rediscovery, 8 error) |
| Loop funnel captured | 1,262 → classified 1,084 (178 unclassified) |
| Human disposition queue | **27** (decisions-pending + steward proposals aggregated) |
| RSI close pending | 9 |
| agent-infra commits | 52 (37 substantive session work) |
| Human-triggered RSI/planning sessions | **10** (see table below) |

---

## What ran without Markus (verified autonomous)

| Job | Schedule | Evidence Jun 18–19 | Output |
|-----|----------|---------------------|--------|
| `act-drain` | daily 06:45 | log lines Jun 19 06:45; digest written | disposition queue, classify run, RSI-close list |
| `blindspot-miner` | daily 06:50 | log: digest 25 top flags | `.claude/blindspot-digest.md` |
| `vendor-sweep` | daily 06:00 | log: committed `binary-extracts/2.1.183.md` | trending-scout memo, version bumps |
| `drift-sentinel` | daily | loaded, idle ok | (no new drift digest in window) |
| `agentlogs-index` | continuous | indexing through Jun 19 10:36 | 327 sessions queryable |
| `reclaim-rotate`, `codebase-map-refresh`, etc. | various | orient: 14 jobs live | background hygiene |
| Session-end auto-checkpoint | SessionEnd hook | 13 WIP commits | persistence only, not integration |
| Prior-context hook | UserPromptSubmit | shipped earlier | reduces rediscovery (residual = existing_infra) |
| Earn-its-keep registration trigger | wired Jun 18 | commits `ac208d4`, `1834656` | **verify layer** — not yet predict-then-falsify |

**Autonomous commit share:** 2/52 (vendor-sync + trending-scout follow-up). **~4%.**

---

## What required Markus (verified human triggers)

### Session triggers (first message → work chain)

| Time | Session | Trigger | Output chain |
|------|---------|---------|--------------|
| Jun 18 08:17–08:40 | cursor fan-out ×5 | "Explore RSI in anim/hutter/intel/research" | `2026-06-18-hutter-anim-rsi-comparative-report.md` |
| Jun 18 08:33 | claude:8 | "@comparative-report — what universal package?" | design question → no auto-build |
| Jun 18 11:58 | claude:c | "@planning deep-diagnosis → /decide" | planning-lifecycle ADR chain (~15 commits) |
| Jun 18 21:22 | claude:4 | Victor Chen blog URL | anim-workbench integration probe |
| Jun 18 22:52 | claude:5 | "Bring RSI machinery to ARC AGI" | hutter→arc-agi audit sessions |
| Jun 19 09:23–09:25 | (in-session) | `just steer-mine` | 495 signals → steering-vectors synthesis |
| Jun 19 09:28 | cursor:6 | `/observe ..all modes` | observe bundle (partial) |
| Jun 19 09:29+ | claude:c60f0878 | steer table pasted → **"what to integrate?"** | SoTA 4-axis sweep, behavioral eval, hermes forensics, skill-optimize demo |

**10 explicit RSI/planning sessions** drove essentially all integration thinking. No `/loop maintain` sessions in window (`maintain-tick` last ran **2026-06-14**).

### Substantive commits by theme (37 session commits)

| Theme | Commits | Autonomous? |
|-------|---------|-------------|
| Planning-lifecycle ADR + plan-core + lifecycle graph | ~18 | Human `/decide` arc |
| RSI SoTA synthesis + behavioral eval + hermes | ~8 | Human "integrate?" session |
| Gov / gitignore / implements trailers | ~6 | Mixed (some steward-driven) |
| Earn-its-keep + loop-core ratify | ~3 | Session (could be maintain-tick) |
| grep-winning research, mergiraf, citation gate | ~2 | Session |

---

## Loop funnel — where it stalls

```
CAPTURE (1262) ──► CLASSIFY (1084) ──► DISPOSITION (27 human) ──► BUILD (?)
     ✓ auto              ✓ auto            ✗ inbox                 ✗ no motor
```

| Stage | Automatic? | Blocker |
|-------|-----------|---------|
| Capture (reflect, agentlogs, hooks) | Yes | — |
| Detect misses (blindspot) | Yes | — |
| Mine preferences (steer-mine) | **No** | no launchd; $5/run; session-triggered only |
| Classify (act-drain, reflect) | Yes | 178 unclassified still |
| Synthesize cross-axis | **No** | no job connects blindspot + steer + scout → ranked plan |
| Prioritize | Partial | act-drain ranks; human reads 27-item digest |
| Build tier-0 items | **No** | maintain-tick dead 5 days; 3 shippable items sit `[ ]` |
| Verify promote | Partial | earn-its-keep wired; **predict-then-falsify not wired** (#1 SoTA steal) |

### Three open tier-0 builds (identified, not shipped)

From `improvement-log.md` + `2026-06-19-steering-vectors.md` — agent-infra-local, checkable, 2+ sessions:

1. **continuation-misread hook** — 4+ sessions, UserPromptSubmit/Stop predicate
2. **HUMAN.md template-aware grep** — false `[open]` count in hutter agi3-status
3. **Codex global hooks fleet shim** — 63 unshimmed hooks (cross-repo → steward, not tier-0)

Items 1–2 should have shipped via maintain-tick without human. Item 3 correctly waits on steward gate.

---

## Case studies (simulated auto-path vs actual)

### 1. RSI SoTA synthesis (`17ae0ef`, Jun 19)

**Actual:** Human pasted steer table → "what to integrate?" → 4 research dispatches → ranked steal table.

**Could auto:** Weekly job: inputs = blindspot top-3 + steer vectors + vendor-scout `[ ]` + improvement-log recurrence → `llm-dispatch` synthesis memo. **Tier-0 builds auto-queue; tier-2 → decisions-pending only.**

**Simulation:** `orphan_findings.py` shows scout memos ARE harvested — the gap is **cross-axis synthesis**, not memo orphaning.

### 2. Behavioral eval feasibility (`3995598`, Jun 19)

**Actual:** Triggered inside integration session → 29 cases, harness-induced over-ask proven.

**Could auto:** blindspot `over_caution` > threshold for 7d AND no registered behavioral testground → spawn feasibility probe (scripts exist: `extract_behavioral_eval_cases.py`, `overcaution_smoke.py`).

**Simulation (2d blindspot):** 41 over_caution flags — threshold would have fired. Probe is autonomous; **first testground build stays operator-go** (caution floor is taste/principal).

### 3. Hermes forensics (`7182390`, Jun 19)

**Actual:** vendor-sweep flagged Jun 19 06:00 → human integration session deep-read same day.

**Could auto:** scout item tagged `extract-pattern` → headless deep-read within 48h → improvement-log verdict. Latency: ≤1 day without human URL drop.

**Simulation:** scout ran autonomously; deep-read did not.

### 4. Planning-lifecycle ADR chain (~18 commits, Jun 18)

**Actual:** Human `@deep-diagnosis → /decide`.

**Could auto (partial):** research memo convergence detector → **draft ADR only**; human for telos fields (`success_metric`, irreversible schema). Bounded autonomy, not full auto.

### 5. continuation-misread (open since Jun 17)

**Actual:** steer-mine + blindspot + steering-vectors all agree. Still `[ ]`.

**Could auto:** maintain-tick picks top `[ ]` where `blast_radius=agent-infra`, `evidence_sessions≥2`, implements + runs harness-eval.

**Simulation:** maintain-tick last ran **2026-06-14** — item would still be open even with perfect routing. **Root cause confirmed: no motor.**

---

## The three blockers (verified, ranked)

### 1. maintain-tick is dead (since Jun 14)

Orchestrator eradicated 2026-06-07; `/improve maintain` is interactive `/loop 30m` only. No launchd job. **5-day gap** during highest RSI activity week.

**Fix:** `com.agent-infra.maintain-tick` — 30–60m, rate-gated (`pgrep` cap), sweep → pick-one tier-0 → ship → log to `maintenance-actions.jsonl`. Closes ~60% of the gap alone.

### 2. No synthesis job (sensors → ranked integration plan)

blindspot + steer + scout + funnel run independently. Nothing produces "what to integrate this week" without a human prompt.

**Fix:** weekly `integration-synthesis` dispatch (deep_review, <600KB context via `observe_prepare_context.py`). Output: `research/YYYY-MM-DD-auto-integration-rank.md`.

### 3. Disposition inbox, not router

27 items in act-drain digest; **4 steward proposals from April** still present. Human must triage everything.

**Fix:** new `config/build-autonomy-tiers.json` (separate from pretool `approval-tiers.json`):

| Tier | Rule | Action |
|------|------|--------|
| 0 | agent-infra-local, reversible, checkable, ≥2 sessions | auto-ship via maintain-tick |
| 1 | same + single-variable harness change | auto-ship + notify in digest |
| 2 | shared / 3+ projects | decisions-pending |
| 3 | GOALS, constitution, taste | principal only |

---

## Auto-wiring checklist (verified feasible)

| # | Wire | Closes | Sim result |
|---|------|--------|------------|
| 1 | launchd `maintain-tick` | tier-0 builds, continuation hook | maintain dead 5d — would have shipped #1–2 |
| 2 | launchd `steer-mine` weekly | preference mining without $5 session | manual only today |
| 3 | weekly `integration-synthesis` | "what to integrate?" without prompt | 10 human sessions → ~3 auto memos |
| 4 | predict-then-falsify on act-drain promote | accretion / policy-maze (#1 SoTA) | not wired; proposed only |
| 5 | blindspot threshold → behavioral probe | over_caution instrument | 41 flags/2d — would trigger |
| 6 | scout `extract-pattern` → 48h deep-read | hermes-class latency | scout ok; read manual |
| 7 | `build-autonomy-tiers.json` + router in act_drain.py | 27-item inbox → auto-route | pretool tiers ≠ build tiers (corrected) |
| 8 | install LaunchAgents symlink for act-drain | ops hygiene | job runs anyway via direct plist path |

**Do not build (verified noise):**
- Extending `approval-tiers.json` for builds — wrong file.
- Orphan trending memo ratchet — already green.
- Bare-model over-ask eval — refuted (`2026-06-19-behavioral-eval-feasibility`); need harness replay.

---

## What correctly stays human

Per verifier-conditioned autonomy (constitution):

- **Tier 2–3:** cross-repo hooks, schema/ADR telos, first behavioral testground go
- **Caution floor** on behavioral eval — never penalize uncorrected asks
- **ARC-AGI prize repo propagation** — new domain, human direction Jun 18 justified

Everything else in the Jun 18–19 window was **partial-verifier**: gather → draft → check → reversible ship.

---

## Recommended sequence

1. **maintain-tick launchd** — unblocks tier-0 queue immediately (continuation hook, HUMAN.md grep).
2. **predict-then-falsify gate** — preventive accretion fix (#1 SoTA steal; autonomous).
3. **steer-mine weekly + integration-synthesis** — removes "what to integrate?" prompt.
4. **build-autonomy-tiers.json** — route act-drain disposition automatically.
5. **behavioral testground** — one operator go, then automate probe + rising bar.

---

## Success metrics (pre-register)

Track after wiring #1–#3 for 14 days:

| Metric | Baseline (Jun 18–19) | Target |
|--------|---------------------|--------|
| Human "integrate / act now / why didn't you" sessions | 10 RSI sessions / 48h | −50% |
| tier-0 `[ ]` age | continuation open 3+ days | 0 items >24h |
| maintain-tick runs | 0 in 5 days | ≥2/day |
| Autonomous commit share | ~4% | ≥25% of agent-infra harness commits |
| Blindspot over_caution / 48h | 41 | trending down after behavioral probe |

---

## Artifacts

- Probes: `loop_funnel.py`, `orphan_findings.py`, `extract_supervision.py --days 2`, `blindspot_miner.py --days 2`, launchctl, git log
- Source memos: [[2026-06-19-steering-vectors]], [[2026-06-19-rsi-sota-synthesis-what-to-integrate]], [[2026-06-19-behavioral-eval-feasibility]]
- Digests: `~/.claude/act-drain-digest.md`, `.claude/blindspot-digest.md`

---

## Addendum — sessions & patterns not in first pass (2026-06-19)

Second probe pass: project/vendor splits, subagent inflation, genomics bug-hunt arc, cross-repo threads.

### Session count correction (major noise)

Raw agentlogs: **327 sessions / 48h**. Most are **harness automation**, not operator work.

| Bucket | n | What |
|--------|---|------|
| Cursor zero-duration subagents | 134 | `/debug` verifiers, RSI fan-out, audits (parent dispatches) |
| Stop-hook Haiku sub-sessions | 69 | `agent-infra` only, ~0.3m each, "review an AI coding agent…" |
| steer-mining worker pool | 32 | identical mine prompt in `Users-alien-claude-steer-mining-ws` |
| Codex `bare` <1m bootstrap | ~50 | AGENTS.md preamble, hook/codex shim invocations |
| **Operator estimate** | **~60** | remainder |

**Implication:** "327 sessions" overstates human supervision load ~5×. RSI audit should weight **substantive claude sessions >5m (non-hook): 17 total** — 10 agent-infra, 2 evals, 1 each agent/substrate/phenome/anim/intel.

### Pattern A — Genomics parallel adversarial bug hunt (dominant non-RSI self-improvement)

**Not covered in first pass.** Largest cursor footprint (44 subagents).

| Fact | Value |
|------|-------|
| Method | 11 passes × 4–6 parallel `/debug` cursor subagents per wave |
| Output | `genomics/docs/audit/2026-06-19-*` — 201 `PASS*` IDs, fix backlog, closeout |
| Fixes applied in hunt | **Zero** (explicit user constraint: documentation only) |
| Fixes landed separately | ~15 overnight commits (BUG/NEW/RL/HLA-B) |
| Gates | `just canary` + `just ir-canary` green; CI contract sync FAIL (NEW-M) |

Prompt clusters (verified): adversarial `/debug` verifier (×6), Modal grounding reads (×5), per-commit review (×many one-offs).

**Automation gap:** This is a **working verification loop** for partial-verifier domains — but entirely **session-orchestrated**. No launchd, no standing "audit delta since last green" job. Could auto-trigger when: (a) ≥N commits land on clinical path, (b) canary green but contract lint red, (c) `fix-backlog.md` has P0 items >24h.

**Human still needed for:** P0 fix approval queue ("implement only with explicit approval" in backlog).

### Pattern B — Stop-hook verification fleet (autonomous, uncounted win)

69 Haiku sub-sessions / 48h in agent-infra — **Stop prompt hook** verifying claimed work. Total ~19 min compute.

This IS automatic self-improvement running today. Not in RSI funnel metrics. **Recommendation:** index `first_message LIKE 'review an AI coding agent'` separately in `loop_funnel.py` so verification load isn't confused with operator sessions.

### Pattern C — steer-mine worker fan-out

32 cursor sessions, single prompt: "mining a Claude Code session transcript for HUMAN-AGENT INTERACTION…"

Spawned by `mine_steers.py --workers 3` during manual `just steer-mine` (09:23Z Jun 19). **Parallel extraction works** — scheduling + auto-synthesis downstream does not.

### Pattern D — ARC-AGI graft prep (Jun 18–19)

| Time | Work |
|------|------|
| Jun 18 22:52 | Human: "bring RSI machinery to ARC AGI" (claude:5, 95m) |
| Jun 18 23:03 | cursor inventory audit (arc-agi state) |
| Jun 19 10:29–10:35 | **Burst: 6 parallel cursor audits** (loop/, agent/, src/, experiments/, tests/) |

Same fan-out pattern as genomics bug hunt, different domain. **No auto-bridge** from hutter comparative report → arc-agi scaffold — human seeded both times.

### Pattern E — Long operator sessions (unaudited in v1)

| Duration | Project | Trigger | Notes |
|----------|---------|---------|-------|
| 618m | `agent` | `/goal @GOAL.md` | GOALS stewardship — principal register, not harness RSI |
| 471m | substrate | `/update-config` | Config migration; no RSI integration |
| 224m | evals | Life-sci-bench URL | Benchmark ingest + critique |
| 179m | agent-infra | planning `/decide` chain | covered in v1 |
| 173m | agent-infra | lifecycle-graph plan | gov spine — covered partially |
| 170m | phenome | medical/octa images | domain deliverable, not infra |
| 141m | repoviz | codex bootstrap | tooling |
| 128m | agent-infra | "Look thru all convos phenome/genomics/hutter" | **cross-repo config audit** — should be standing job |

**New auto candidate:** cross-convo consistency scanner (session `claude:b` Jun 18) — grep agentlogs for conflicting hook/settings decisions across phenome/genomics/hutter. Partial-verifier, bounded autonomy.

### Pattern F — Substrate bughunt thread

| Session | Work |
|---------|------|
| cursor empty-window 110m | "Continue bug hunt for substrate… Keep bughunting" |
| substrate claude 471m | `/update-config` |
| substrate cursor ×11 | zero-duration subagents |

Parallel to genomics hunt but smaller. **Same gap:** no standing bughunt scheduler per repo.

### Pattern G — anim-workbench outer-loop reviews

Short sessions with forced `## Verdict` first line — **OUTER LOOP REVIEW** template (Jun 18 13:43, 22:22). Victor Chen blog session (85m) same day. Self-improvement via external pattern import — human URL drop required.

### Pattern H — Tool failures (2d, `/observe failures` tier-1)

| Cluster | Last seen | Note |
|---------|-----------|------|
| `missing-module:modal_utils` | Jun 18 | genomics bare-python / wrong cwd |
| `missing-module:graph_explorer` | Jun 19 | substrate |
| `missing-module:corpus_core` | Jun 17 | cross-repo |
| `missing-module:yaml`, `edgar`, etc. | Jun 17–18 | invocation discipline |

Failures mode **not run** in first audit pass. These are **auto-fixable** via existing pretool guards + maintain-tick — but maintain dead 5d. Not new architecture.

### Pattern I — Supervision sub-patterns (2d, lexical)

Top buckets: `direction` (1879), `system` (742), `slash-command` (177), `context-continuation` (159), `hook-feedback` (70).

**159 context-continuation** messages — aligns with continuation-misread hook candidate (still unshipped). Lexical classifier undercounts semantic over-ask (blindspot 41 vs supervision CORRECTION 9).

### Pattern J — steer signal taxonomy (495 signals, Jun 19 mine)

| Type | n |
|------|---|
| redirect | 85 |
| constraint | 45 |
| correction | 29 |
| disconfirmation | 23 |
| scope | 21 |
| taste | 6 |

Top synthesized vectors (unique, not clustered in JSONL): verify-then-act dual, human-escalation via HUMAN.md, skeptical external synthesis, loop-vs-interactive feasibility, operator opt-in for loop policy.

**Gap:** vectors sit in JSONL — no automatic cluster→`[ ]` promotion except human reading steering-vectors memo.

### Revised automation priorities (after addendum)

| Priority | Target | Why new |
|----------|--------|---------|
| **A0** | Session counting split in agentlogs/dashboard | 267/327 automated — metrics lie without it |
| **A1** | Standing audit-delta job (genomics pattern generalized) | biggest verified self-improvement Jun 18–19, 100% manual orchestration |
| **A2** | Cross-repo config consistency scan | 128m session proves need; one-shot |
| **A3** | Index stop-hook fleet in loop_funnel | 69 runs/day invisible |
| **A4** | maintain-tick (unchanged from v1) | would catch tool-failure clusters + tier-0 hooks |

### What this changes about the v1 verdict

v1 focused on **RSI loop** (blindspot→act-drain→integrate). Second pass shows **more self-improvement happened outside that loop**:

- Genomics 11-pass audit (verification without RSI)
- 69 stop-hook verifications (harness self-check)
- steer-mine workers (preference capture, manual trigger)

**The system already has multiple self-improvement modes — they don't share a motor.** Unifying them under maintain-tick + honest session accounting is higher leverage than adding another sensor.
