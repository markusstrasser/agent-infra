# Session-Corpus Value Extraction — Prior Work Archaeology

**Status: PROBE IN PROGRESS** (started 2026-06-16)

Task: find and document ALL prior work mining our own agent session transcripts/logs to produce value.
Specific recall to confirm: (a) Cursor 2.5 "full read" trials over the corpus, (b) steering-vector extraction.

Findings appended below as confirmed. Every claim grounded in a quoted file path / commit.

---

## HEADLINE (the two specific recalls — both CONFIRMED, and they are the SAME tool)

Markus's two recalls — "Cursor 2.5 full read of all of it" and "extraction for steering vectors" —
resolve to **ONE artifact**: `mine_steers.py`. There is NO activation/persona/residual-stream vector
work anywhere in ~/Projects. "Steering vector" here means a **revealed-preference vector** mined from
session transcripts (a `"vector"` JSON field = "the underlying preference/principle the steer pushed
toward"), NOT a neural activation vector. The "Cursor 2.5 full read" is `mine_steers.py` spanning
**Composer/Cursor 2.5** over full session transcripts.

### The tool: `mine_steers.py` (steer / interaction miner)
- **Path:** `~/Projects/skills/observe/scripts/mine_steers.py` (12,198 bytes, 243 lines)
- **Born:** commit `skills 9b5bbff [observe] Add steer/interaction miner — full-corpus multi-signal
  transcript mining` (Mon 2026-06-15, 15:08). Promoted from a $5 probe.
- **Docstring (quoted):** *"Steer / interaction miner — full-corpus transcript mining via Composer 2.5
  (cheap, parallel). The full-coverage, multi-signal counterpart to /observe's recent-window analysis."*
- **Input source:** `~/.claude/agentlogs.db` session universe → full Claude Code session transcript
  JSONL (`~/.claude/projects/.../*.jsonl`), tool-noise collapsed, truncated at 200K chars.
- **Model/tool that produces it:** **Composer 2.5 (= Cursor 2.5)** via `cursor-agent` (`agent`) ask-mode,
  parallel workers. Requires Cursor subscription logged in. THIS is the "Cursor 2.5 full read."
- **What it extracts — three streams in one read:**
  1. `steer` — mid-session human correction/redirect/constraint/taste → JSON with a **`"vector"`** field
     = the preference/principle pushed toward. (= the "steering vector" recall, literally the field name.)
  2. `confirmation` — explicit human approval (the positive preference signal nobody else mines).
  3. `agent_miss` — concrete agent mistake / violated discipline → which hook to build.
- **Output:** `signals.jsonl` + idempotent scanned-ledger keyed by `(vendor, session_id)` at
  `~/.claude/steer-mining/scanned_ledger.jsonl` (206 lines / 30,846 bytes as of 2026-06-16).
- **Cost:** ~$0.085/interactive session; full backfill ~$35/~40min; incremental ~free (ledger skips scanned).

### Results (from the probe writeup — `~/Projects/skills/research/notes/2026-06-15-steer-mining-probe.md`)
- Probe spent **$4.77**, ~50 sessions, 2 stages. n=17 multi-signal: 98 steers (~5.8/sess), 94 agent_miss,
  21 confirmations.
- **Headline result (quoted):** *"clustered steers reproduce ~80% of CLAUDE.md from behavior alone."*
- Induced 10 preference vectors; 7 already in CLAUDE.md (✓), 3 flagged GOALS candidates (★): #2
  durable/systemic-only, #8 bias-to-execution, #10 agent-agnostic.
- **agent_miss → violated-rule map** = highest-value NEW signal: misses cluster onto EXISTING CLAUDE.md
  rules being violated in practice → ranks which rules need HOOK enforcement (not more prose). The probe's
  "integrating insight": one full pass = an **empirical audit of the constitution**.

### Current status: WIRED (advisory loop), but mostly capture-only
- `just steer-mine` recipe — `~/Projects/agent-infra/justfile:460-461`.
- `/improve maintain` weekly row — `~/Projects/skills/improve/SKILL.md:483` ("Steering vectors (full
  corpus) | Weekly (incremental) | `just steer-mine`... Cluster recurring `vector` fields → GOALS tension
  or steward-proposal; do NOT auto-promote to hooks").
- `/observe` documents the direct call — `~/Projects/skills/observe/SKILL.md:114-117`.
- **Self-assessed gap** (cursor session `8ae4d1a7`, 2026-06-15, the exact session Markus is recalling —
  he asked *"didn't we build that session inspect and steering vector skill recently? and the /rsi skill?"*):
  the agent's own answer: *"The pieces exist, but most of the loop is capture-only... Steer mining ran once
  as a probe; it's not on the skill path."* and *"Steering vector mining | Script, not a skill |
  skills/observe/scripts/mine_steers.py — mines steers/confirmations/agent_miss → 'vector' preference lines"*.
  Pattern named there: **"SENSE built, ACT missing"** — generators/shadow-logs exist; the drain
  (`/improve maintain`, human disposition, `/rsi close`) doesn't reliably run.

### NOT FOUND: literal activation/persona steering vectors
Grepped steering|activation|contrastive|persona across all 8 repos' full git history. NO neural
steering-vector / activation-engineering / persona-vector extraction exists. The word "steering vector"
also appears in transcripts as the *Fable self-degradation safeguard* topic (Fable degrades itself via
"steering vectors" on frontier-LLM-dev requests) — that's a model-behavior discussion, NOT our work.
"contrastive" in agent-infra = the **emb-contrastive** detector method used by `blindspot_miner.py`
(embedding-space contrast, not activation steering).

> **Sibling memo (complementary, same session-series, 2026-06-16):**
> `research/2026-06-16-session-extraction-external-prior-art.md` covers the EXTERNAL literature
> (Persona Vectors arXiv 2507.21509, CAA 2312.06681, etc.). Its verdict aligns with the NOT-FOUND
> finding above: real steering/activation vectors need model internals; **transcripts-only cannot
> compute a steering vector** — only the contrastive-prompt + behavioral-rubric *protocol* transfers.
> This memo = OUR prior work; that memo = the field. Read both together.

---

## ITEM 3 — All distinct session-extraction efforts (with status)

| Effort | Path | Input | Extracts | Consumer | Status |
|---|---|---|---|---|---|
| **agentlogs** (foundation) | `src/agentlogs/` (cli/index/search/git_import/query) | `~/.claude/projects/*/*.jsonl` + git history → `~/.claude/agentlogs.db` (3.8GB, cross-vendor) | sessions/runs/tool_calls/git_commits + FTS5 | everything below; `agentlogs recent/search/stats`; launchd `agentlogs-index` (2h) | LIVE (the substrate) |
| **mine_steers.py** (the dual recall) | `skills/observe/scripts/mine_steers.py` | agentlogs.db → full transcripts via **Composer/Cursor 2.5** | steers(`vector`)/confirmations/agent_miss | `just steer-mine`; `/improve` weekly; `/observe` | WIRED, capture-only (probe→promoted 2026-06-15) |
| **steering-signals.py** (the FIRST steering miner) | `skills/goals/scripts/steering-signals.py` | agentlogs.db + hook telemetry + receipts ($0 regex) | #f feedback, corrections/redirects, topic drift, cost allocation | `/goals` Phase 0 reconnaissance (`skills/goals/SKILL.md`) | LIVE in `/goals` (deterministic; predates mine_steers, Mar 2026 commit `3b7995a`) |
| **reflect_capture.py** | `scripts/reflect_capture.py` | SessionEnd hook stdin transcript ($0) | deterministic correction signals + shadow omission-probe firings → `~/.claude/reflect-capture.jsonl` | reflect.py | LIVE (SessionEnd hook) |
| **reflect.py** | `scripts/reflect.py` | reflect-capture.jsonl + fm.py taxonomy | clusters → FM classification → enforcer proposals (quarantined) | act_drain, `just reflect-review` | LIVE (deterministic spine, $0) |
| **reflect_session_close.py** | `scripts/reflect_session_close.py` | close-queue intents + capture | Tier-1 episode digest for `/rsi close` | `/rsi close` skill; SessionStart nudge | LIVE (RSI close path) |
| **blindspot_miner.py** | `scripts/blindspot_miner.py` (runs in emb's env) | last-7d transcripts; emb-contrastive | loop-MISS flags: over_caution/rediscovery/error_correction/taste_steer | launchd `blindspot-miner` (06:50) → digest → SessionStart | LIVE launchd |
| **supervision-kpi.py** | `scripts/supervision-kpi.py` | transcripts via `supervision_taxonomy.py` ($0 regex) | per-DIRECTION supervision trend + AIR (agent-improved-rate) | pulse.py; `just supervision-kpi` | LIVE (report-only TREND) |
| **session-features.py** + **session_detectors.py** | `scripts/session-features.py`, `session_detectors.py` | transcript JSONL | structured epistemic/behavioral features per session (ACC-lite calibration exhaust) | trajectory calibration | report-only |
| **buildthenundo.py** | `scripts/buildthenundo.py` | git history | build-then-undo anti-pattern (file added then reverted same session) | `v_build_then_retire` view; improvement-log | LIVE report-only |
| **clash_detect.py** | `scripts/clash_detect.py` | clash-capture.jsonl + governance-index → gemini-3-flash | governance-clash verdicts | launchd `clash-detect` (07:00), SHADOW | LIVE SHADOW (the 1 LLM launchd job, ~$0.001/day) |
| **act_drain.py** | `scripts/act_drain.py` | reflect classify + loop_funnel + questions_view ($0) | disposition-queue digest + "Questions for you" | launchd `act-drain` (06:45) → digest → SessionStart | LIVE launchd |
| **fm.py** | `scripts/fm.py` | agent-failure-modes.md + fm-evidence.jsonl | FM taxonomy primitives (list/show/attach/mint/resolve/recurrence) | reflect.py, `/rsi close`, pulse.py | LIVE (build-time spine) |
| **pulse.py** | `scripts/pulse.py` | shells the above sensors | "are my closure instruments alive/trusted" | RSI-loop liveness surface | LIVE |
| **agentlogs SQLite views** | `src/agentlogs/migrations/001_initial.sql` | git_commits + git_commit_files | v_fix_chains / v_build_then_retire / v_churn_hotspots / v_session_durability | `agentlogs query <name>`, dashboards | LIVE analytics |

**Historical note:** `steering-signals.py` (Mar 2026) is the ORIGINAL "mine corrections from sessions"
tool — deterministic, $0, feeds `/goals`. `mine_steers.py` (Jun 2026) is its LLM-powered full-corpus
successor (Cursor 2.5, richer `vector`/confirmation/miss streams). Both live; different cost/depth tiers.

---

## ITEM 4 — Live extractors detail (input → extract → consumer → status)

(Confirmed via subagent read of each file's docstring + wiring grep. SQL line refs:
`src/agentlogs/migrations/001_initial.sql`.)

- **blindspot_miner.py** — IN: last-7d transcripts, emb-contrastive (torch in emb's env). EXTRACT: every
  human correction the loop FAILED to catch, classified into 4 directions (RAISE_AUTONOMY / GROW_COVERAGE /
  REDUCE_ERROR / AMPLIFY_TASTE). OUT→ `~/.claude/blindspot-digest.md`. CONSUMER: launchd `blindspot-miner`
  06:50 → `blindspot-surface.sh` at SessionStart. The RSI loop-closure (supervision stream grows coverage).
- **reflect.py + reflect_session_close.py + reflect_capture.py** — the RSI capture→classify→close chain.
  capture ($0, SessionEnd hook) → reflect.py clusters+classifies against FM taxonomy, auto-records evidence
  to existing FMs, quarantines new FMs/enforcers for human → reflect_session_close builds the `/rsi close`
  digest. CONSUMER: act_drain, `/rsi close`, `just reflect-review`. No enforcer activates without approval.
- **fm.py** — "fm" = **Failure Mode**. Machine-addressable taxonomy spine over `agent-failure-modes.md`
  (FM-ID HTML-comment blocks) + `~/.claude/fm-evidence.jsonl`. attach-evidence / mint (merge-before-mint
  guard, refuses <2 merges) / resolve / recurrence (pre-vs-post-fix evidence rate). Build-time, agents don't query it.
- **supervision-kpi.py** — IN: transcripts via supervision_taxonomy ($0 regex). EXTRACT: per-DIRECTION
  supervision vector (NOT scalar load) + AIR + slopes. CONSUMER: pulse.py sensor; `just supervision-kpi`. Report-only.
- **agentlogs views** (all from git_commits + git_commit_files): `v_fix_chains` (file fixed then re-fixed
  within 3d), `v_build_then_retire` (feature commit fully reverted within N days — waste), `v_churn_hotspots`
  (files with ≥5 commits, fix/revert breakdown), `v_session_durability` (per-session fragility_pct =
  commits_later_fixed / commits_produced). CONSUMER: `agentlogs query <name>`, dashboards.
- **clash_detect.py** — IN: directive-class user messages (captured by `userprompt-clash-capture.py` hook) +
  `.claude/governance-index.md` → gemini-3-flash. EXTRACT: does this directive CLASH with a stated
  goal/principle/veto? OUT→ `~/.claude/clash-shadow.jsonl`. SHADOW (surfaces nothing; 2-week precision window).
  Launchd `clash-detect` 07:00 — the ONE LLM-calling launchd job.
- **act_drain.py** — IN: `reflect classify` + loop_funnel + questions_view ($0). EXTRACT: human-disposition
  queue digest, LEADS with "Questions for you". OUT→ `~/.claude/act-drain-digest.md`. Launchd `act-drain` 06:45
  → SessionStart surface. The zero-LLM ACT half of the RSI loop.

---

## ITEM 5 — Gap list (what we do NOT extract from sessions yet)

Grounded in the cursor-8ae4d1a7 self-assessment ("SENSE built, ACT missing") + the probe writeup's
"next" section + coverage of the table above.

1. **The full mine_steers backfill never ran.** Only ~50 of ~400 billable sessions scanned (probe). The
   `agent_miss → violated-rule frequency` ranking — *which hook to build first* — is the highest-value
   unrealized output and needs the ~$35 full pass. (probe writeup "Next" + ledger 206 lines.)
2. **No DECISIONS / why-NOTs extraction.** We mine corrections (steers) and mistakes (agent_miss) but NOT
   the *decisions made and alternatives rejected* inside sessions. `decisions/` is hand-authored; nothing
   mines transcripts for "agent chose X over Y because Z" → the decision-journal is lossy vs. the transcript.
3. **No mistake→decision LINKAGE.** agent_miss is extracted flat; not tied back to the decision/turn that
   caused it. (Causal chain "this decision → this downstream miss" is unmined.)
4. **No reusable-skill / workflow distillation from sessions.** `/improve` has a "workflow→skill" mode but
   no extractor proposes skill candidates from repeated transcript patterns. (Autobrowse-style graduation is
   explicitly VETOED — `vetoed-decisions.md` — but that's browser-workflow specific; general workflow mining is open.)
5. **No reasoning-pattern / trajectory-quality extraction beyond ACC-lite.** session-features.py logs exhaust
   but nothing consumes it for "what reasoning shapes correlate with durable sessions" (the v_session_durability
   fragility signal is git-only, not reasoning-linked).
6. **Confirmations under-exploited.** mine_steers extracts confirmations (the + signal that sharpens the
   autonomy BOUNDARY) but no consumer turns them into autonomy-boundary updates — they're logged, not acted on.
7. **The drain gap (cross-cutting).** Most extractors are SENSE-complete but ACT-incomplete: digests pile up
   in quarantine/close-queue/shadow logs; `/improve maintain` + human disposition don't reliably run. This is
   the structural gap the cursor session named, not a missing extractor.

---

**Status: COMPLETE** (2026-06-16)
