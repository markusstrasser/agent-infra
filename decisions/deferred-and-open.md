---
title: Deferred & Open — decision forks not yet closed
date: 2026-06-16
status: living
---

# Deferred & Open

Forks deferred or left open by a `/decide` arc, with the trigger that reopens each. So nothing is
lost and nothing is re-proposed from scratch. Append; mark closed with the resolving commit.

## RSI loop closure (ADR `2026-06-16-rsi-unified-control-surface.md`)

| Item | State | Reopen trigger |
|---|---|---|
| `rsi weights` — precision-weight detectors | **DEFERRED** | ≥2 detectors clear the PPV gate (`reflect.PPV_CLEARED` non-empty with ≥2 families). Until then it's a weighting brain for ~1 input. |
| `rsi gate` axis-granularity rollup | **OPEN** (shipped at FM-ID granularity) | A promotion flow exists AND axis-level (reach/knowledge/capability) freezing is wanted — needs an FM-ID→axis join `fm.py` does not emit today. Probe the writer before building. |
| Label the 22 reflect omission firings | **OPEN — human (amplify lane)** | Anytime. `new-script-without-test`×9, `entity-write-without-identity-read`×6 lead. Clearing PPV≥60% graduates a detector → then `weights` reopens. |
| `v_tool_friction` closure back-edge (Jun-8 plan Phase B) | **OPEN** (planned, never shipped) | If the supervision-side closure (AIR + canary) proves insufficient and tool-friction-by-project is still wanted. Was descoped to doctor.py; grep shows neither shipped. |
| MAST detectors: reasoning-action-mismatch, information-withholding | **OPEN** (logged improvement-log 2026-06-16) | A real instance shows in sessions (not yet recurrence-gated). |
| Auto-inject write-stub in `pretool-subagent-gate.sh` (vs block) | **OPEN** | Confirm PreToolUse can mutate `Agent` input on this CC version. Keeps the #47936 guard, kills the re-author friction. |

## AutoResearch skill imports (ADR `2026-06-19-autoresearch-grounding-imports.md`)

| Item | State | Reopen trigger |
|---|---|---|
| #2 citation-verify rate-gate for `/research` | **IMPLEMENTED** (approved + shipped `skills@a529547`) | closed — `verify_citations.py` + SKILL.md Phase 3. Reopen only to promote an advisory threshold to blocking on a measured miss. |
| #1 weakness→component routing table for `/improve` | **DEFERRED** | `/improve` outputs read as non-actionable in practice (today: covered by `review_gate.py rank`/disposition). |
| #3 phase-gated 6.0→8.5 score progression | **REJECTED** | LLM-judge-as-gate proxy (`CLAUDE.md:59`, `2026-05-28-verify-against-ground-truth`, scale-rubrics claim 5). Reopen only if a *ground-truth-grounded* scalar (Scale weighted-binary criteria, S∈[0,1]) is wanted — NOT Deli's holistic persona-score. |
| #1 calibration ladder (first-round cap, max +Δ/round, ≥1 unresolved) | **REJECTED** | No host loop (`/critique` single-shot, `/code-review` scout, `/improve` per-finding). Reopen only if a scored iterative review loop is built for an independent reason. |

## Critique audit trail
- `.model-review/rsi-arch-opus.md` · `rsi-crosslab-gpt.md` · `rsi-factcheck-composer.md` (2026-06-16).
  Partial spine reversal: ship canary, defer the promotion brain. All load-bearing claims verified
  against code before folding.

## Static data simplification (ADR `2026-07-14-static-data-over-consumer-platforms.md`)

| Item | State | Close / reopen trigger |
|---|---|---|
| Phenome genomic shadow-data deletion | **OPEN — blocking** | Close only when every `genomics_findings.yaml` / `exports/genomics/**` fact maps to an exact static `results/**` record or a retained human-authored phenome observation. |
| Corpus paper-store move | **OPEN — blocking** | Close when research-mcp passes cached + new fetch, extraction, source-count, and metadata-identity checks without moving `~/Projects/corpus` bytes. |
| Cross-repo corpus attestation retirement | **OPEN — blocking** | Close after all outboxes drain, final annotations/relations/audit state are archived, and domain writes pass without corpus side effects. Reopen only on measured cross-repo annotation-driven decisions. |
| `genome-toolkit` deletion / `substrate` parking | **OPEN — dependent** | Close after negative scans show no active surface depends on either repository, `genome-toolkit` has one verified cold bundle before deletion, and `substrate` is explicitly frozen but kept intact. |
