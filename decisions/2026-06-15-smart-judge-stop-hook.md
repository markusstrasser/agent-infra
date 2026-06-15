---
id: 2026-06-15-smart-judge-stop-hook
concept: judgment-class-enforcement
repo: agent-infra
decision_date: 2026-06-15
recorded_date: 2026-06-15
provenance: contemporaneous
status: accepted
initial_leaning: "Add hooks for the most-violated disciplines"
relations:
  - type: supersedes_role_of
    target: stop-unsupported-completion.sh (lexical verify-before-claim detector)
  - type: respects_vetoes_of
    target: 2026-06-15-rsi-session-close-gate
  - type: grounded_in
    target: research/notes/2026-06-15-steer-mining-probe (research repo)
---

# 2026-06-15: Smart-judge Stop hook — LLM adjudication for judgment-class disciplines

## Context

Steer-mining over 206 interactive sessions (790 transcript-grounded agent_misses,
research repo, 2026-06-15) ranked the disciplines the agent violates most:
verify_before_claim 161, look-before-leap ~187, **over_caution 73** (the autonomy gap —
inverse of the #1 stated preference), guardrails 62, scope/partial 49, durable 48.

The top three are **judgment-class** — a regex cannot see them. They are ALREADY written
rules (CLAUDE.md, GOALS) violated at high frequency, so the pair-rule says the fix is
structural enforcement, not more prose. But the existing structural attempt is lexical and
stuck:

- `stop-verify-claims.sh` (global, blocking) catches ONLY mechanical claims — "I committed X"
  (git-checkable), "created file Y" (fs-checkable). Its `TEST_CLAIMS` regex is compiled and
  never used. The 161 misses are *semantic* ("the fix works", "all 13 pages sound") it cannot judge.
- `stop-unsupported-completion.sh` (agent-infra+evals, shadow) is lexical-only and self-documents
  the ceiling: it fires on a success-verb with no evidence-WORD in the final message, **ignoring
  tool history by design**. Result (measured, 320 would_fire / 1371 stops = 23%): **3 of 4 sampled
  fires are over_caution permission-asks** ("Want me to run that now?"), not unsupported claims.
  Promoting it to advisory would nag the agent to "cite evidence" *for asking a question* — the
  exact nagware GOALS forbids and the exact "15 false nags" the rsi-session-close ADR recorded.

The lexical layer cannot hit its own 60%-precision promotion bar **because** it is lexical.

## Decision

Add `stop-smart-judge.sh` — an **LLM-judge Stop hook**, the precision-adjudication successor to
the lexical shadow-detector family. One Haiku call, conditional and cheap, judges three vectors
from the final message + USER REQUEST + recent TOOL CALLS:

1. **verify_before_claim** — fresh outcome claim ("tests pass", "deployed", "wrote file X")
   with no matching action in tool history. (Tool-history-aware — this is the edge the lexical
   layer lacks: it does not fire on "Fixed." when pytest is in the recent calls.)
2. **partial_completion** — claims done while an explicit part of the request is dropped / wrong format.
3. **over_caution** — ends by asking permission for an action that is obvious, reversible, and
   already authorized by the request.

**Conditional + smart:** a deterministic claim/permission pre-filter gates the LLM; most turn-ends
cost $0 and 0 ms. **Off subscription** ($0): Haiku via `claude -p` with the API key stripped —
forced, not preferred, because the metered Anthropic API returns `credit balance is too low`
(the existing `posttool-reception-payload-llm.sh`, which calls that API, is therefore silently dead).

**Shadow-first, project-scoped, async** (cf. stop-progress-check / stop-unsupported-completion):
logs every verdict to `~/.claude/smart-judge-shadow.jsonl`, never blocks. Wired async in
agent-infra only — head-to-head with the lexical predecessor, and because each fire spawns an ~8 s
`claude -p` (non-trivial background load to bound during validation).

## Alternatives considered

1. **More prose rules / GOALS bars** — rejected: these ARE written rules being violated; pair-rule
   says enforce structurally. (Two GOALS bars were already added this session; necessary, insufficient.)
2. **Brittle blocking regex hooks** — rejected: the lexical detector proves regex mislabels
   over_caution as verify-fail; a blocking version is nagware (FM14).
3. **Metered Haiku API** (the existing smart-hook idiom) — rejected: API credit balance is zero;
   subscription is the only live transport.
4. **Hook Stop synchronously to block** — rejected for v1: 8 s latency + the rsi-close "15 false
   nags" evidence. Graduate per-vector to a SYNC soft-nudge only after shadow PPV earns it.
5. **Global rollout now** — deferred: async-shadow is harmless, but the per-fire `claude -p` load
   and the dogfood-first pattern argue for agent-infra first, global after a PPV read.

## Respecting the rsi-session-close-gate vetoes (2026-06-15)

- "Never hook Stop for RSI close" — this is NOT RSI close (no digest/steward actuation); a
  lightweight per-turn claim judge. Different purpose.
- "No LLM on SessionEnd" — this is Stop, async; not the 1.5 s SessionEnd path.
- "/goal per-turn Haiku evaluator collision" — async (post-stop) avoids the latency collision.

## Validation (this session)

- Synthetic 4/4 across all three vectors (verify / clean / over_caution / partial).
- Real-transcript replay: after one prompt refinement (calibrate verify to *fresh-action* claims +
  tell the judge the tool list is truncated), firing dropped 80%→30%; the residual context-window
  state-summary false-positives were eliminated.
- Head-to-head: on a real case the lexical detector false-fires ("shipped the fix; want me to do
  the bigger reconciliation?"), the smart-judge correctly stays SILENT (the asked-about action is
  new scope, not the authorized step) — the precision difference that separates useful from nagware.

## Closed loop / next

- **PPV check:** validate smart-judge verify_before_claim verdicts against the 478 KB
  `unsupported-completion-shadow.jsonl` (real lexical would_fire cases) — does the LLM layer reject
  the lexical FPs? And against `reflect-capture.jsonl` ground-truth user-corrections (did a flagged
  turn actually draw a correction?). This is the shadow→PPV machinery the rsi-loop plan already names.
- **Graduate** verify_before_claim first (clearest), via SYNC wiring + `SMART_JUDGE_MODE=enforce`
  soft-nudge, once PPV ≥ ~70%. over_caution stays shadow longest (most judgment, highest FP risk).
- **Re-measure** with `mine_steers.py` on post-deployment sessions: does the agent_miss rate for
  these vectors drop? (The miner is the independent outcome metric.)
- **Broaden** to more projects / global after the agent-infra PPV read + background-load check.

## Revisit if

- API credits restored → the fast `haiku-api` transport (~1-2 s) becomes viable for the sync
  enforce path; default stays subscription.
- Shadow PPV < ~50% on any vector after 2 weeks → that vector's prompt needs work or is not
  Stop-judgeable; do not promote it.
- A native per-turn evaluator (/goal) exposes a claim-verification hook → prefer it over a second LLM call.
