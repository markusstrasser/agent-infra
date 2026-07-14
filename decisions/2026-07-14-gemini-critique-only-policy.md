---
id: 2026-07-14-gemini-critique-only-policy
concept: llmx-transport-routing
repo: llmx
decision_date: 2026-07-14
recorded_date: 2026-07-14
provenance: contemporaneous
status: accepted
relations:
  - type: depends_on
    target: 2026-06-25-metered-spend-funnel-enforcement
  - type: depends_on
    target: 2026-05-31-gemini-cli-to-paid-api-migration
---

# 2026-07-14: Gemini is critique-only — enforced at the key + the llmx funnel

## Context

The operator's Google bill was ~€700 in June vs ~€70 in July. Forensics: June was
the first full month on the paid Gemini API (free CLI retired by Google 2026-06-18;
llmx cut over 2026-05-31) AND the heaviest Gemini month — 12,407 metered llmx calls
(~$136 token-priced, dominated by the gemini-3.5-flash critique cosigner), plus
off-ledger direct-SDK surfaces (research-mcp `ask_papers` 1M-context / `deep_research`
Interactions API, phenome/intel extractors, clash-detect launchd shadow) that bypass
both the usage ledger and the $25/day spend guard. July collapsed via the 07-06
spend block + 07-09 GPT-5.6 rerouting + June one-off batches ending.

Operator directive (2026-07-14): "ONLY run gemini when an agent runs it for
/critique ... otherwise it shouldn't run (esp not automatically)."

## Decision — two enforcement layers (architecture over instructions)

1. **The key is the funnel.** `~/.env` now stores the key ONLY as
   `GEMINI_API_KEY_CRITIQUE_ONLY` (no `GEMINI_API_KEY`/`GOOGLE_API_KEY` anywhere —
   swept shell profiles, project `.env`s, keychain: single copy). Every direct-SDK
   consumer in every repo fails loud by construction ("No API key was provided",
   verified live). This is the layer an llmx-only gate could never provide — most
   of June's spend never touched llmx.
2. **llmx policy gate at the metered funnel.** `spend_guard.enforce_gemini_policy`
   (called from `enforce_daily_cap`, i.e. both metered entry points) refuses any
   `gemini-*` dispatch unless `LLMX_GEMINI_OK=1`. New `GeminiPolicyError`
   (subclass of `SpendCapError`, exit 7, `error_type=gemini_policy`).
   `LLMX_SPEND_OVERRIDE` does NOT bypass it — budget cap and provider policy are
   separate refusals. When allowed, llmx resolves the scoped var and promotes it
   to `GEMINI_API_KEY` in-process for the genai SDK (`_promote_scoped_key`).
3. **The allowed lane:** `skills/critique/scripts/model-review.py` sets
   `LLMX_GEMINI_OK=1` in `main()` — its gemini axes (arch/gaps) inherit it via
   subprocess env. Verified: `--preflight` green post-change.
4. **clash-detect launchd job retired** — the only automatic Gemini dispatcher.
   Its dispatch was already broken (`--subscription -m gemini-3-flash-preview`
   now hard-errors in llmx) and its 2-week shadow-precision window (ADR
   2026-06-16) lapsed. Booted out; plist + launcher deleted; `clash_detect.py`
   kept for the pending `just clash-detect --summary` precision review.

## Consequences (accepted, reversible)

- research-mcp `ask_papers` / `deep_research` / extraction now fail loud on the
  missing key. Re-enable per-run by exporting `GEMINI_API_KEY` for that process,
  or permanently by loosening this policy. phenome/intel Gemini extractors same.
- Long-running processes started before the rename still hold the old env until
  restart.
- One-off manual Gemini use: `LLMX_GEMINI_OK=1 llmx chat -m gemini-* …` in a
  fresh shell (zshenv exports the scoped var).

## Verification

- refuse: `env -u GEMINI_API_KEY llmx chat -m gemini-3-flash-preview "ping"` →
  exit 7, `type=gemini_policy`, before any API call.
- allow: `LLMX_GEMINI_OK=1` + scoped var only → `pong`, exit 0.
- direct SDK without key → `ValueError: No API key was provided` (fail loud).
- `tests/test_spend_guard.py` 17 passed (5 new policy tests incl.
  spend-override-does-not-bypass).

## Revisit if

- /critique's gemini axes get retired from the default preset → drop the lane
  and the scoped key entirely.
- ask_papers-class 1M-context work returns as a standing need → name a second
  allowed lane explicitly (same env, set by that engine) rather than restoring
  the global key.
