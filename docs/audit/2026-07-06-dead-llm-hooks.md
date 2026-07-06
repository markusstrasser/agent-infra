# Dead LLM-backed hooks/jobs — class diagnosis + fixes (2026-07-06)

SEARCH_ROOT: /Users/alien (hooks under ~/Projects/skills/hooks, ~/Projects/*/.claude, ~/.claude)
GLOB_SCOPE: ~/Projects
VERDICT_REQUIRES: content-match

## TL;DR

The two assigned "dead" instances are **ONE bug with two victims**, and it is **NOT**
the metered-API hypothesis. Claude Code 2.1.x **renamed the UserPromptSubmit envelope
field `.user_message` → `.prompt`** (~2026-06-16). Every hook still reading `.user_message`
reads empty → exits before doing anything → produces no output and no error. Four hooks
died silently for ~3 weeks. Fixed all four (read `.prompt`, `.user_message` fallback,
`[DEGRADED]` on a missing-both envelope) + added a lint guard so the class can't recur.

The metered-API-with-zero-credits class from the steward proposal is **real but separate** —
it kills a *different* hook (`reception-payload-llm`), also fixed here.

## Root cause per assigned instance

### 1. prior-context front-load hook — REJECTED metered-API; it is the field rename
- The hook (`userprompt-prior-context.py`) is **pure Python, no LLM call** — the metered-API
  hypothesis cannot apply. Confirmed working *today* when fed a `.user_message` envelope.
- It read `env.get("user_message")` (line 479). CC 2.1.x sends `.prompt` (official docs;
  confirmed: intel + hutter UserPromptSubmit hooks already migrated to `.prompt`). So in every
  real session since the rename the hook reads `""` → returns at the empty-prompt guard →
  no output, no trigger-log row.
- Timeline matches exactly: last real fires 2026-06-16 (evals session), then 0. The rename
  landed around that CC version bump; the hook was never updated.
- **Empirical proof it is invocation, not gate precision:** replaying 120 real recent user
  prompts through the hook with the correct field → **49% produce output**. The gate matches
  half of real traffic; the deaths were pure field-read failure.

### 2. clash-detect shadow — SAME root cause, one layer upstream
- The gemini-flash `clash-detect` launchd job is **ALIVE** (loaded, exit 0) — it just has no
  input. Its input comes from `userprompt-clash-capture.py` (a UserPromptSubmit hook), which
  read `env.get("user_message")` (line 58) → captured nothing since deploy (d355ee8, 2026-06-16,
  right at the rename). `clash-capture.jsonl` never got a row → 0 CLASH verdicts, forever.
- Fixing the capture hook's field read unblocks the whole pipeline. Verified: a `.prompt`
  directive envelope now appends a capture row.

## Metered-API hypothesis — TESTED, verdict: real class, wrong suspects
- REJECTED for both assigned instances (neither is metered-API-dependent; both are the field rename).
- CONFIRMED for a third, separate hook: `posttool-reception-payload-llm.sh` calls
  `api.anthropic.com/v1/messages` with the credit-exhausted `ANTHROPIC_API_KEY`
  (400 "credit balance too low") → silent no-op. Wired in `publishing`, where live
  `src/lib/data/*/reception.ts` targets exist, so it is a genuine dead hook. Fixed.

## Live/Dead table — every LLM-backed hook + LLM launchd job

| Item | Kind | Transport | Wired | State | Action |
|---|---|---|---|---|---|
| userprompt-prior-context.py | UserPromptSubmit (no LLM) | — | global | **WAS DEAD** (field rename) | FIXED |
| userprompt-clash-capture.py | UserPromptSubmit (no LLM) | — | agent-infra | **WAS DEAD** (field rename) → starved clash-detect | FIXED |
| userprompt-context-warn.sh | UserPromptSubmit (no LLM) | — | global | **WAS DEAD** (field rename) | FIXED |
| continuation-directive-guard.py | UserPromptSubmit (no LLM) | — | global | **WAS DEAD** (field rename) | FIXED |
| posttool-reception-payload-llm.sh | PostToolUse | metered API (dead credits) | publishing | **WAS DEAD** (Class B) | FIXED → subscription-first |
| clash-detect (launchd) | launchd job | gemini-flash | loaded | ALIVE but data-starved | unblocked via capture-hook fix |
| stop-smart-judge.sh | Stop | $0 subscription + API fallback | global | ALIVE | — |
| stop-stance-flip-shadow.sh | Stop | $0 subscription (key-stripped) | agent-infra | ALIVE | — |
| source-check-haiku.py | (LLM: metered API) | metered API | **UNWIRED** | inert (latent Class B if ever wired) | flagged, not modified |
| posttool-unsourced-claim-check.sh, peer-session-count.sh, pretool-cost-guard.sh, pretool-cursor-model-guard.py, pretool-raw-openai-guard.sh, pretool-companion-remind.sh | guards | none (pattern-match only) | mixed | ALIVE (not LLM-callers) | — |
| all other launchd jobs | launchd | none (zero-API) | loaded | ALIVE | — |

**Counts:** 5 dead hooks found (4 field-rename + 1 metered-API), **5 fixed**; 1 latent unwired
(source-check-haiku, flagged); 2 live LLM hooks + 1 live LLM launchd job unaffected.

## Fixes (all additive + reversible, no blocking-behavior change)

1. **Field rename (4 hooks):** read `env.get("prompt") or env.get("user_message")`
   (shell: `jq -r '.prompt // .user_message // ""'`); `[DEGRADED]` stderr when the envelope
   has *neither* key (catches the next contract drift loudly — rule #22).
2. **Structural guard:** `lint_hook_input_contract.py` now flags any hook reading
   `.user_message` without `.prompt`. Positive control: 4 fixed hooks pass. Negative control:
   a hook reading only `user_message` is flagged. Runs in `just harness-eval`.
3. **Regression test:** `test_userprompt_prior_context.py` pins the `.prompt` contract
   (+ `.user_message` fallback). 26/26 pass.
4. **Metered-API (reception hook):** repointed to $0 subscription (`claude -p`, key-stripped)
   first, metered API as fallback, `[DEGRADED]` when both transports fail. Mirrors the proven
   `stop-smart-judge.sh` pattern. bash + embedded-python syntax verified.

## Nothing blocked-on-parent
All fixes are dead-hook repairs (wrong field / dead transport → correct), advisory hooks stay
advisory, no blocking behavior changed, no design call. Shared-hook edits are field/transport
repairs restoring original intent — flagged here for the parent to veto if desired.
