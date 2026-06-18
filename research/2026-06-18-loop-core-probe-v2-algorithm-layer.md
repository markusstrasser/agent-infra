---
title: loop-core probe v2 — algorithm-layer deletion test (shapes generic, NOT adopt-by-deletion)
date: 2026-06-18
status: complete
relates_to:
  - decisions/2026-06-16-loop-core-rsi-ledger-factoring.md
  - research/2026-06-18-hutter-anim-rsi-comparative-report.md
---

# loop-core probe v2 — algorithm-layer deletion test

Resolves the open action queued by `decisions/2026-06-16-loop-core-rsi-ledger-factoring.md`
(latest revision): *"can hutter's clade-yield/calibration/heretic views + anim's collapse onto
ONE DuckDB loop-core by deletion?"* — i.e. the **algorithm layer**, after probe v1 found the
**storage** layer diverges. Three read-only forensic agents extracted hutter/anim/intel's exact
view DDL + judged collapse-by-deletion (raw inventories: `/tmp/probe-v2/{hutter,anim,intel}.md`).

## Verdict

**Adopt-by-deletion FAILS 3/3 — but it's a PARTIAL-UPDATE, not a reversal.** The algorithm
*shapes* are ~60% generic (Markus's "the algorithms are universal" is **vindicated in SHAPE**);
they do **not** collapse onto one shared `experiments` schema that any loop migrates onto by
deleting its local views. So the extraction is a documented **skeleton cookbook** (copy-stamp
per loop into its own schema/engine), **not** a shared schema, views toolkit, or helper-lib.
The ADR's "loop-core IS real (DuckDB schema + algorithm views toolkit)" framing over-reached on
SUBSTANCE: **"toolkit" → "cookbook."**

## The matrix (6 universal patterns × 3 loops)

| Pattern | hutter (search loop) | anim (paused) | intel (partial/principal) | Shareable? |
|---|---|---|---|---|
| **leaderboard** | generic shape; min-bytes direction is a knob | ❌ no scalar score (conjunctive PASS) | ✅ generic (BSS rank) | needs scalar score — 2/3 |
| **clade-yield** | ✅ generic DAG walk on (id,parent_id,verdict,score) | columns exist, **never computed** | ❌ absent (belief-supersession ≠ offspring) | **1 real consumer (hutter)** |
| **calibration** | mostly generic; byte-direction hardcoded | ❌ prose predicted/actual, regex-inspected | ✅ **generic (Brier/BSS)** — the one strong fit | 2/3 but different units/engines |
| **funnel/probe-transfer** | ❌ verdict literals ARE the stages (PACE) | defined, not exercised | ❌ absent (ratchet purged 2026-05-19) | **hutter-only** |
| **tag-yield** | ❌ 2 timing cols + baseline-relative gain | ❌ absent | generic query, **no consumer** | nobody shares the contract |
| **heretic-audit** | generic logic, hutter-named cols | reads external artifacts (`oracle-backed`, `qd-archive.json`) — **un-portable** | built but SHADOW-only, `--enforce` refuses | concept ports, schema doesn't |

## Three blockers (hutter, decisive)

1. **The verdict vocabulary IS the algorithm.** The funnel, ratchet, and heretic key on a
   12-value domain verdict set (`BASELINE/ACCEPT/ACCEPT_HELD/REJECT/GATE_PASS/PROBE_WIN/…`) +
   a `slice IN (enwik5/6/8)` truth-tier. A flat shared `verdict` column cannot encode PACE
   gate→probe→ratchet semantics without hutter re-stating its taxonomy as columns.
2. **Score direction + multi-column gain/cost.** Everything assumes lower-is-better bytes,
   `gain=−d_s/baseline_s`, `cost=compress_s+decompress_s`. A generic scalar `score` loses both.
3. **Engine mismatch is a rewrite.** Every view is SQLite recursive-CTE string-surgery over a
   comma-joined `tags` TEXT; DuckDB needs `UNNEST(string_split())`. Adopting means *rewriting*
   244 tested production rows into untested views — risk, not savings.

anim corroborates from the other side (no scalar score at all; prose, not numbers; heretic
reads files outside any table). intel corroborates by regime (only calibration applies; the
other five are *correctly* absent — forcing them in re-introduces the auto-ratchet autonomy the
operator deliberately removed).

## What this means to build

- **DON'T BUILD:** shared `experiments` schema · loop-core views toolkit · `ledger-core` ·
  even the narrowest helper-lib. Deletion fails 3/3; the helper-lib also fails the proven-common
  bar (clade-yield: 1 real consumer; calibration: 2 but different units/engines).
- **BUILD:** the role pattern (Proposer→Runner→Verifier→Auditor→Accept→Ledger) + the 6 algorithm
  shapes become a documented **SKELETON COOKBOOK** — each new loop copy-stamps the skeleton into
  its OWN schema/engine and fills the verdict vocabulary + score units.
- **Ease-of-starting implication (GOOD):** the unified infra for "start a new domain loop" is
  layers 1+2 only — **scaffold + cross-domain skills + cookbook, zero shared runtime/schema.**
  The probe killed the one piece (layer 3) that would have added cross-repo coupling. Less
  machinery to maintain; stamp-and-diverge.

## Cost

~254k subagent output tokens (hutter 87.6k · anim 85.5k · intel 80.7k), 49 tool calls, 3 agents
parallel (~2–3.6 min each wall). Reasoning tokens not separately reported by the sub-agents;
all three ran at default effort. One forensic pass, durable verdict — cheaper than the
build-then-undo it prevents.
