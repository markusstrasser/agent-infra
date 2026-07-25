# Interactive session default: Opus 5 vs the Fable pin (2026-07-25)

**Status:** ESCALATED — taste call, not a benchmark question

## The ask

`~/.claude/settings.json` still pins **Fable 5** as the interactive session model. All headless
and dispatch routing moved to **Opus 5** on 2026-07-24 (`decisions/2026-07-24-claude-opus-5-default.md`).
Keep the pin, or move interactive to Opus 5 too?

## Why it's yours

Session *feel* — verbosity, pacing, how it handles being interrupted mid-thought — is a
principal-verifier call. No benchmark decides it. You're the one in the session.

## What the numbers say (they do not settle it)

| | Opus 5 | Fable 5 |
|---|---|---|
| AA Intelligence Index (max) | **61** (#1) | 60 |
| Cost per task | **−26%** vs Fable | — |
| Subscription | **$0** | **metered $10/$50** since 2026-07-07 |
| AA-Omniscience Index | 31 | **40** |
| Verbosity at max (AA) | 100M out-tok, *"very verbose"* | — |

Opus 5 wins intelligence, cost, and subscription routing. Fable wins the
hallucination-penalized index by a clear margin (40 vs 31) — which matters more for
conversational factual work than for gated coding.

Note Fable is **metered** now, so the pin has a real running cost that Opus 5 does not.

## Recommendation

**Move interactive to Opus 5**, on cost + subscription grounds, and keep provenance/verify
discipline on for factual questions (the 50% hallucination rate is the live risk either way).

But if the Fable pin is there because the *conversation* feels better, that reason survives
every number above and I would keep it. Say which and I'll wire it.
