# Where should hard-block metered-spend enforcement live — and which daily cap is real?

**Boundary:** shared (touches `~/Projects/skills/hooks/` and/or `~/Projects/llmx` — 3+ projects)
**Reversible?** yes (any of the three options is a revertable code change), but it changes the
spend-control surface every project inherits, so it's human-gated per invariants #4.

## Context — what's already true (so we don't re-decide the built part)

The $70 silent-spend incident (substrate `018ee7c8`, 2026-06-22) happened because a backgrounded
worker's metered escalation branch was **invisible to the foreground-Bash `pretool-cost-guard.sh`**.
Probing the actual machinery (not the improvement-log's stale premise):

- **The funnel ledger already exists.** llmx appends every call — foreground Bash, backgrounded
  worker, OR Python subprocess — to `~/.claude/llmx-usage.jsonl`, with `transport` (`api`=metered
  vs subscription=$0), `caller`, `cwd`, tokens. This is the surface-agnostic point all spend passes.
- **Observability is now shipped** (agent-infra-local, this session): `usage-check.py --metered-today`
  + `doctor.check_metered_spend()` surface today's billed spend daily (warn $10 / fail $25). A runaway
  now shows up in `doctor.py` the same day. **This proposal is ONLY about hard *blocking*.**
- `pretool-cost-guard.sh` reads a **different** ledger (`session-receipts.jsonl`) and only fires on
  interactively-typed Bash → it is the wrong ledger on the wrong surface for agentic spend.

## The decision — three options for hard block enforcement

| Option | Where the block lives | Pro | Con |
|---|---|---|---|
| **A. In-llmx pre-dispatch guard** (recommended) | llmx checks today's `transport==api` total in `llmx-usage.jsonl` before a metered dispatch; refuses over cap | **Surface-agnostic by construction** — Bash, bg worker, subprocess all blocked identically; this is the principled fix (the guard lives at the funnel, not at a proxy surface) | edits llmx (every project's dispatch path); needs a fail-open path + an override env for legit large jobs |
| **B. Periodic launchd alarm** reading the rollup | a launchd job runs `usage-check.py --metered-today --alarm 25` every N min; alarms/notifies on breach | zero edits to the hot path; cheap; local | **alarms after the fact**, doesn't *prevent* the next call — the $70 still accrues, you just learn faster |
| **C. Extend `pretool-cost-guard.sh`** to read `llmx-usage.jsonl` | the existing Bash hook adds the funnel ledger | smallest diff | still **only the foreground-Bash surface** — does nothing for the bg-worker case that caused the $70. Rejected on the merits unless paired with A/B |

**Recommendation:** **A** (the block belongs at the funnel — epistemic-discipline #8: the Bash
surface is a *proxy* for "where spend happens," and background workers are the silent fallback that
bypasses it) **+ B as the safety net** (a periodic alarm catches the case where a long-running
process started before the cap was hit). C alone does not fix the incident class.

## Sub-forks that ride along (need your call)

1. **Which daily cap is real?** invariants.md / constitution says **$25/day**. `pretool-cost-guard.sh`
   warns at **$500**, blocks at **$1000**. These disagree by 40×. The enforcement layer needs ONE number.
2. **Unpriced-model undercount.** The pricing maps (`usage-check.py:RATES`, `llmx/usage_report.py:PRICING`)
   are estimate-grade and key on model-name prefixes; live `gemini-3.5-flash` prices **$0** because only
   `gemini-3-flash` is in the table. An *alarm* that undercounts can miss real spend, and you don't want to
   *block* on a guessed price either. Fork: single-source the pricing map (invariant #9) and decide the
   policy for unpriced models (fail-open vs conservative-overcount vs refuse-with-"unpriced").

## Dissent / risk

A hard in-llmx block can wedge a legitimate large batch mid-run (the failure mode behind option B's
"alarm not block"). Mitigation: an explicit per-run override (`LLMX_SPEND_OVERRIDE=1` or a budget arg)
that the operator sets when a big job is intended — the block defaults on, the override is deliberate.

## Open question for you

Approve **A+B at the $25 cap** (with an override env for intended large jobs)? Or keep it
observability-only (already shipped) and accept that prevention stays manual?

**Evidence:** improvement-log 2026-06-25 (BACKSTOP GAP + shipped observability slice);
substrate@6dd4f84,c8af5ee (the per-pipeline in-repo fix); `~/.claude/llmx-usage.jsonl` schema;
`pretool-cost-guard.sh`; `usage-check.py --metered-today`; improvement-log:3601 (caller-attribution `[obs]`).
