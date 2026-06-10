---
id: 2026-06-10-dependency-glue-inversion
concept: dependency-evaluation-lens
repo: agent-infra
decision_date: 2026-06-10
recorded_date: 2026-06-10
provenance: contemporaneous
status: accepted
---

# 2026-06-10: The glue-inversion lens — "adopt the actively-developed library" often inverts

## What prompted this
emb session: operator proposed retiring emb (2,200 LOC personal search library) for
txtai (31K LOC, 80 commits/90d, 10K stars) to "harness their ongoing work." Deep dive
(clone → maintenance audit → live smoke test) reversed the intuition.

## The lens (reusable)
When evaluating "retire our small library for an actively-developed one," ask three
questions IN ORDER — each killed the txtai migration independently:

1. **Glue inversion.** Is our library already glue over actively-developed engines
   (sentence-transformers, SQLite, numpy, google-genai — all big-team)? If yes, we
   already harness ongoing work where it matters. The candidate is usually *someone
   else's glue over the same engines* — adopting it swaps N big-team dependencies for
   one wrapper. Check the candidate's bus factor: txtai = 1,872/~1,900 commits from
   one person. "Actively developed" and "bus factor 1" co-occur often.
2. **Probe the headline feature on YOUR critical path, live.** Feature matrices and
   even the candidate's own adoption stories mislead (a 15-candidate eval issue claimed
   txtai had everything; our own Explore map got reranking wrong in the other
   direction). A 15-minute smoke test on the one query shape our consumers actually
   run (`similar() AND source=...`) returned 0 results at default settings — txtai
   post-filters ANN candidates, i.e. it ships as designed behavior the exact
   K-truncation bug phenome once hacked around (`fetch_k = top_k*5`). Migration would
   have been a correctness regression on the most-used path.
3. **Check the candidate's transitive choices against our own evictions.** txtai's
   API-embedding route is litellm — evicted from this stack 2026-06 over a supply-chain
   incident (emb a9a8b7b). A dependency re-imports the decisions you already rejected.

## Outcome
txtai NOT adopted; cherry-pick list instead (fusion math, SPLADE reference, fastapi-mcp
pattern). Full dossier: `~/Projects/emb/docs/research/2026-06-10-txtai-deepdive.md`;
break-glass re-adoption conditions recorded there.

## Relation to existing principles
Sharpens global pre-build check #1 ("does this already exist?") for the inverse case
("should the existing thing be replaced?") and subagent_usage's dependency-evaluation
clause (maturity/bus-factor/self-hostability) with an ordered, probe-first procedure.

Rejected: adopting on activity metrics alone (commits/stars measure the maintainer's
work rate, not your risk); extending-by-wrapping (emb-on-txtai would fork the search
internals to fix post-filtering — wrapper fighting the engine).
