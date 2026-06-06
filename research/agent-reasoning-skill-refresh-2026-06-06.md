# Agent Reasoning Skill Refresh

question: Should we revive `/analyze` for intel-style reasoning work, and what newest agent-reasoning research should shape it?
tier: Standard
date: 2026-06-06

## Ground Truth

`/analyze` is already a unified reasoning skill with five modes: causal, dag,
robustness, hypotheses, and investigate. Its causal mode requires quantified
observation, null process, residual geometry, shape-constrained hypotheses,
natural experiments, specificity ranking, recursive causal audit, probability,
top alternative, falsifier, and decision impact.

Intel has moved toward the same ontology. The thesis-graph refactor says causal
reasoning, bull/bear mechanisms, falsifier-to-data binding, and cross-entity
edges were previously prose-invisible, and the target is queryable causal plus
refutation structure. The entity checklist already requires cheapest
error-band-reducing actions, upside/downside mechanism generation, concrete
falsifiers, and structured conviction transitions.

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | The live opportunity is not "more CoT"; it is controlled reasoning effort and reusable reasoning units. | Recent 2026 arXiv papers emphasize self-regulated planning, adaptive latent reasoning, structured generate-verify-revise, context evolution, and primitive induction. | HIGH | arXiv 2605.22138, 2606.02871, 2601.07180, 2606.02304, 2606.02994 | VERIFIED |
| 2 | `/analyze` is a good fit for intel because intel's current hard problem is causal/refutation routing, not source discovery. | Intel refactor frames the thesis graph as queryable causal plus refutation structure; entity checklist requires falsifiers, mechanism families, and error-band actions. | HIGH | local intel docs | VERIFIED |
| 3 | `/analyze` should be refreshed before public release or heavy reuse. | Its core workflow is good, but it is "local only", static, and not yet wired to decide when a lightweight vs deep reasoning pass is worth the tokens. | MED | local skill plus 2026 reasoning-control papers | INFERENCE |
| 4 | The most useful new module is a "reasoning controller": choose no-op, light causal check, hypotheses pass, DAG pass, or full investigate based on observation shape and decision stakes. | SR^2AM and ALAR show benefit from deciding when/how deeply to reason; SCR shows value in explicit generate/verify/revise components and dynamic stopping. | MED | arXiv 2605.22138, 2606.02871, 2601.07180 | INFERENCE |
| 5 | Intel traces could be mined into reusable reasoning primitives. | Reasoning Primitive Induction reports gains from mining successful ReAct traces into typed pseudo-tools; UCE reports gains from typed memory/strategy/workflow/skill units scored through use. | MED | arXiv 2606.02994, 2606.02304 | INFERENCE |

## Key Findings

1. `analyze` should not be treated as an old skill to publish unchanged. It
should become the local controller for "what reasoning pass is needed here?"
Its current content is strong, but it assumes the user/agent already selected
the right mode.

2. The newest papers converge on selective reasoning:

- Structured Reasoning (SCR, submitted 2026-01-12) decouples trajectories into
  generate, verify, and revise components, using dynamic termination supervision
  and reporting up to 50% token-length reduction versus existing reasoning
  paradigms. Source: https://arxiv.org/abs/2601.07180
- SR^2AM (submitted 2026-05-21) decomposes agents into reactive execution,
  simulative planning, and self-regulation that decides when/how deeply to plan;
  the paper reports 25.8%-95.3% fewer reasoning tokens for its v1.0-30B model
  against comparable agentic LLMs. Source: https://arxiv.org/abs/2605.22138
- Adaptive Latent Agentic Reasoning (submitted 2026-06-01) argues agents waste
  text reasoning on routine turns and uses dual-mode latent vs explicit
  reasoning, reporting token reductions up to 43.6% in search and 84.6% in tool
  use while maintaining comparable or better accuracy. Source:
  https://arxiv.org/abs/2606.02871
- Unified Context Evolution (submitted 2026-06-01) externalizes experience into
  typed Memory, Strategy, Workflow, and Skill units, scoring and pruning them
  through repeated use; it reports ALFWorld 75.4% to 96.3% and WebShop 45.1 to
  61.3. Source: https://arxiv.org/abs/2606.02304
- Reasoning Primitive Induction (submitted 2026-06-02) mines successful ReAct
  traces into typed pseudo-tools and reports large gains on RuleArena NBA,
  MuSR team allocation, and NatPlan meeting planning. Source:
  https://arxiv.org/abs/2606.02994

3. Intel is the best internal testbed. Good trial targets:

- adverse move attribution: "real events vs systemic drawdown"
- thesis-flip review: "what changed, and is the stable view broken?"
- competitor substitution: "is fallback expression still the same thesis?"
- falsifier evaluation: "does this observed event actually refute the thesis?"
- causal graph pass for thesis-graph edges: "is X enabling/threatening Y, or just correlated?"

4. The refactor has already done the architectural half. The skill should not
invent a new thesis model. It should route to existing surfaces:

- entity files for canonical thesis and conviction
- `indexed/theses.duckdb` / thesis graph for structured assertions
- existing falsifier and monitoring evaluator paths for refutation
- research memos only for evidence that is not yet promoted

## Recommendation

Use `/analyze` now, but only as an internal intel reasoning layer. Do not put it
in the first public skill batch until it is updated.

Update target:

1. Add a Phase 0 "reasoning controller":
   - no-op if null/base-rate explains observation
   - light causal pass for single observed move
   - hypotheses pass for ambiguous entity/anomaly work
   - DAG pass only when estimating an effect or proposing controls
   - investigate mode only for forensic/source-chain work

2. Add intel adapters as examples, not dependencies:
   - drawdown attribution template
   - thesis-falsifier adjudication template
   - bull/bear mechanism chain audit
   - "same thesis or thesis pivot?" test

3. Add a stop rule:
   - if the conclusion does not change a decision, monitoring trigger, falsifier
     state, or research queue item, stop and label it non-actionable.

4. Mine 10-20 successful intel analyses into a small primitive library:
   - null/base-rate subtraction
   - substitute-basket comparison
   - mechanism-chain weakest-link audit
   - expression-vs-thesis split
   - falsifier-hardness classification

## What Is Uncertain

The cited June 2026 papers are preprints and not independently replicated. Their
exact benchmark gains should not be treated as settled. The reliable directional
lesson is still useful: agents need controlled reasoning depth, typed reusable
reasoning units, and stop conditions.

## Search Log

- Local: `/Users/alien/Projects/skills/analyze/SKILL.md`
- Local: `/Users/alien/Projects/intel/docs/refactors/2026-06-03-thesis-graph-full-atomization.md`
- Local: `/Users/alien/Projects/intel/docs/entity-evaluation-checklist.md`
- Web: arXiv recent agent reasoning queries, 2026-06-06
- Paper search: OpenAlex query for agent reasoning primitives/self-regulated planning/adaptive reasoning
