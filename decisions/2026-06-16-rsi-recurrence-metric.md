---
id: 2026-06-16-rsi-recurrence-metric
concept: rsi-recurrence-measurement
repo: agent-infra
decision_date: 2026-06-16
recorded_date: 2026-06-16
provenance: contemporaneous
status: accepted
initial_leaning: "build a longitudinal recurrence tracker"
relations:
  - type: depends_on
    target: 2026-06-15-rsi-session-close-gate
---

# 2026-06-16: RSI back-half closure — descriptive recurrence metric

## Context
The RSI loop captures + surfaces well (`loop_funnel`: 1057 captured → 907 classified; **906 FM
evidence rows**) but the BACK half is unmeasured: nothing answers *"did a shipped fix actually
reduce the failure cluster it targeted?"* `blindspot_miner` is a rolling-window surfacer (no
before/after); `fm.py` has `status` + idempotent `evidence_count` but no fix anchor. Surfaced
2026-06-16 while auditing whether the loop is "successful" — the one honest answer was "front half
yes, back half unproven."

## Probe (gating fact — verified, not assumed)
`fm.py cmd_attach` writes each evidence row to `~/.claude/fm-evidence.jsonl` **with a UTC `ts`**.
→ a per-FM before/after occurrence rate is computable from EXISTING data, **zero new capture**.
This is the fact that makes the minimal shape viable; without it the decision would have been defer.

## Decision
Build the minimal descriptive metric (diverge mechanisms #1+#3 hybrid — generalize the existing
hook-ROI-window idea to FMs, reusing existing data):
1. **`fm.py resolve <id> --ref <commit>`** — stamps `status: resolved`, `fix_ref`, `fix_ts` into the
   FM block (reuse the `_bump_count` block-rewrite). **Human-invoked; never automatic.**
2. **`fm.py recurrence`** (read-only report) — for each resolved FM, occurrence rate (events/week
   from `fm-evidence.jsonl`) BEFORE vs AFTER `fix_ts`. **Flags low-N** (<~5 pre-fix events →
   "underpowered, descriptive only"); never asserts a reduction it can't support.

## Invariants (the iatrogenic guards — non-negotiable)
- **Descriptive, NEVER a target.** The recurrence number is never tied to a gate/reward — that would
  Goodhart it (mark-resolved-to-win). Report only.
- **Human stamps `resolve`; code never auto-closes** an FM.
- **Zero-LLM, read-only report; reuse existing data** (no new capture, mirrors `loop_funnel`).
- **Honest under low N** — flag, don't assert.

## Rejected
- **#2 longitudinal snapshot store** — unneeded; the evidence `ts` already gives time resolution.
- **#4 survival / time-to-recurrence** — statistically nicer but overkill at our scale.
- **#5 noop / human-judgment-only** — leaves free signal on the table; the data CAN answer it cheaply,
  so declining to measure is the wrong default HERE. (Contrast the *flow-change* decision in the same
  session, where high blast radius + no cheap signal made noop correct — the asymmetry is the point.)

## Consequences
- Turns "906 evidence rows" into "X resolved FMs with recurrence dropped, Y not, Z underpowered" —
  the instrument that answers "is the loop successful?"
- Build = ~2 functions in `fm.py` + a self-test; no new dependency, no new capture. Reversible.
- **Built** in `0e9fb1a` (2026-06-16) — `fm.py resolve` + `recurrence` + selftest (green); list regression-clean.
