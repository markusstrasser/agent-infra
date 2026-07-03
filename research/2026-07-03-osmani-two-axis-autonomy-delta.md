# Osmani "Agentic Autonomy Levels" (2026-07-03) — delta vs our constitution

**Verdict: convergent popularization — no mechanism we lack; adopt vocabulary, park two metrics with triggers.**
Source: Addy Osmani, X post 2026-07-03 (82.7K views; Pangram: 100% human-written). Full text archived in research-mcp source store.

## His framework in one paragraph

Replaces Yegge's single-rung ladder (Gas Town / Pragmatic Engineer) with two axes — **agency**
(how far one agent goes: suggest → scoped task → goal-driven) × **orchestration** (one thread →
isolated worktrees → manager-agent factory, "management by exception"). Six levels (0 assist …
5 managed-by-exception). Pre-run contract fields (goal/scope/non-goals/tools/stop
condition/evidence/escalation/budget), a metrics list, and four anti-patterns (autonomy-as-status,
permission laundering, summary substitution, fleet cosplay).

## Delta table

| Article concept | Our counterpart | Status |
|---|---|---|
| "Autonomy level should follow the verification process, not the task name" | Constitution **verifier-conditioned scope** (decisions/2026-06-07-verifier-conditional-autonomy.md) | We're deeper: he names it as a caveat; we condition the whole objective on verifier quality per task, with the 3-regime split (automate / bounded / amplify) |
| Two-axis agency × orchestration | Implicit: subagent-usage rules + worktree isolation + file-bus recipes treat them separately | His explicit decomposition is a good *teaching frame*; no operational gap |
| Pre-run contract (goal/scope/stop/evidence/budget/escalation) | Dispatch briefs, turn-budget PreToolUse hook, Workflow `budget`, gate contract (GREEN/RED/UNKNOWN), HUMAN.md escalation | Covered. Only unwritten field: explicit **non-goals** — zero incident history of scope-overstep from its absence → pre-build check #1 says don't add |
| Summary substitution anti-pattern | Verify hooks, post-compaction git verification, subagent manifest convention, live-execution-is-the-integration-verifier | Covered architecturally (his fix is instruction-level) |
| Permission laundering | Scoped scouts (ask-mode, no commit), hooks, sandbox, guard backstops | Covered |
| Fleet cosplay | debug-until-dry / file-bus recipes encode coordination; worktree isolation | Covered |
| Autonomy-as-status | Constitution logs mid-task autonomy reclassification as an exception | Covered |
| Anthropic usage study (~70% of planning human, ~80% of execution agent) | Corroborates amplify-vs-automate memory (feedback-amplify-automate-by-verifiability) | Citation value |

## Genuinely not computed here (parked, with triggers)

`supervision-kpi.py` has: correction vector, AIR, hook-shown vs corrections-after,
approval-mode bypass share. His list adds two we lack:

1. **Longest successful unattended run with accepted work** — the cleanest single trend
   number for the generative principle ("declining supervision"). Cheap from agentlogs
   `runs` (approval_mode × duration × accepted?). *Trigger to build:* an /observe or
   operator-status-briefing cycle where the direction-vector answer is ambiguous and this
   number would have disambiguated.
2. **Token cost per accepted change** — extends the eval-token-costs rule from evals to
   supervision KPIs. *Trigger:* a model/effort routing decision that quality-per-token at
   the session level would gate.

Rework rate / defect-escape rate: need "accepted change" ground truth we don't label; not
worth an annotation pipeline for a metric with no consumer.

## Pointer

- **OpenAI "Symphony" spec** (Linear board at center, per-issue agent workspace + spec file,
  continuous progress check) — trending-scout candidate next landscape sweep; potentially
  relevant to /orchestrate design if we ever move the file-bus onto an issue tracker.

## Resurrection trigger

Re-open only if (a) one of the two parked metrics hits its trigger, or (b) a real
scope-overstep incident traces to a missing explicit non-goals field in a dispatch brief.
