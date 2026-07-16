# Turn-level prior-context hook activation (2026-07-16)

**Status:** DATA PLANE READY; LIVE HOOK HELD UNTIL 2026-07-24

## Decision

Keep the existing prompt intent gate unchanged. Add turn-level semantic retrieval only
after the 2026-07-10 `over_caution` ablation's rediscovery-control window closes. Start
in shadow: retrieve and log candidates plus exact `agentlogs show …` handles, but do not
inject them into prompts. The offline eval licenses the representation, not live prompt
precision.

## Why this representation

The private own-corpus screen compared literal FTS, raw first-24k session embeddings,
natural user/assistant turns, and generated contextual multi-view records. Natural turns
cleared the locked miss-reduction and latency gates; the richer multi-view representation
cost more to build and ranked worse. The implementation therefore preserves answer-bearing
turns and aggregates them back to sessions at retrieval time.

Evidence: `/Users/alien/Projects/evals/prior_context_retrieval/`.

## Activation sequence

1. On or after 2026-07-24, close the ablation and record whether rediscovery/day stayed
   within its preregistered control band.
2. Wire `scripts/prior-context-index search` behind the existing `INTENT` / `REDISCOVERY`
   match; do not widen those regexes in the same change.
3. Shadow at least 30 intent-matched prompts. Promote to advisory injection only if
   answer-bearing precision is at least 70%, source-handle validity is 100%, and warm p95
   retrieval adds no more than two seconds.
4. If promoted, inject snippets with source handles and keep session-level deduplication;
   never synthesize a prior claim inside the retriever.

## Boundaries

- No shared UserPromptSubmit-hook edit before 2026-07-24.
- No generated overview/resolution views without a new consumer-specific eval.
- No model/API calls in indexing or retrieval.
- The index is rederivable cache state under `~/.cache/agent-infra/prior-context`, not git.
