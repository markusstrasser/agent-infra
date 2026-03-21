# Agent Economics: How Near-Zero Dev Cost Changes Decision Frameworks

**Date:** 2026-03-19
**Tier:** Deep | **Axes:** 3 (mechanism, adversarial, adjacent-domain)
**Question:** How should our decision frameworks change when agent development cost ≈ 0?

## Ground Truth

Our research memos use "Effort | ROI" tables to prioritize what to build. At least 6 memos gate implementation decisions on dev-time estimates ("~2 hours", "~200 LOC", "1-3 days"). Global CLAUDE.md has "validate at 1/10 the code" framed as a cost-saving measure. The user's observation: agents are close to free SWE experts, so dev cost shouldn't be a decision factor.

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Dev creation cost has collapsed 10-100x for competent agent users | Multiple practitioner reports, DORA data, Claude Code revenue trajectory | HIGH | [SOURCE: Minton, McLeod, Osmani] | VERIFIED |
| 2 | "Effort" as invisible governor killed ideas before testing | Minton's structural argument + historical parallel (power loom) | HIGH | [SOURCE: Minton 2026-02-07] | VERIFIED |
| 3 | Jevons Paradox applies: cheaper dev = more projects, not fewer | Explicitly observed by McLeod; 44% of devs now write <10% of code manually | HIGH | [SOURCE: McLeod, Ronacher poll via Osmani] | VERIFIED |
| 4 | NEW bottleneck: comprehension debt | Only 48% consistently review AI code; review time +91%, PR size +154% | HIGH | [SOURCE: Osmani 2026-01-28, DORA 2025, Faros AI] | VERIFIED |
| 5 | NEW bottleneck: entropy spiral (coupling → context bloat → reward hacking) | Structural argument with reproducible pattern in iterative benchmarks | MEDIUM | [SOURCE: Kruglov 2026-03-04] | PLAUSIBLE-MECHANISM |
| 6 | NEW bottleneck: upstream design uncertainty persists | Code accelerates implementation but leaves design-phase ambiguity intact | HIGH | [SOURCE: Agent Wars 2026-03-15, antifound.com] | VERIFIED |
| 7 | AI amplifies existing practices — good get better, bad get worse | DORA 2025 report: high-performing teams +55-70% faster; low-performing teams accumulate debt faster | HIGH | [SOURCE: Osmani citing DORA 2025] | VERIFIED |
| 8 | The decision-relevant costs shift to: maintenance burden, complexity budget, supervision cost, integration risk, comprehension debt | Synthesis from all sources; no single source states all five | MEDIUM-HIGH | [INFERENCE from claims 1-7] | SYNTHESIS |

## Key Findings

### 1. The Invisible Governor Is Gone

Minton's framing is the sharpest: "Effort has been the invisible governor on what gets built, what gets reformed, and what gets attempted. Ideas die not because they are bad, but because the cost of testing them is too high." When that governor is removed, the entire landscape of "worth doing" is redrawn. Every "too hard" backlog item becomes viable. [SOURCE: Minton 2026-02-07]

**Implication for us:** Our "Effort" columns functioned as this governor. Items labeled "MEDIUM-HIGH effort" were implicitly killed. That filtering no longer reflects reality.

### 2. The Cost Function Flipped — Five New Bottlenecks

Creation cost → near zero. But five new costs emerge as the real decision-relevant factors:

| Old Cost (collapsing) | New Cost (rising) | Why it matters |
|----------------------|-------------------|----------------|
| Developer time | **Maintenance burden** | Agent-generated code creates coupling spiral (Kruglov); ongoing drag on future changes |
| Implementation effort | **Comprehension debt** | You understand less of your codebase over time (Osmani); rubber-stamping risk |
| Lines of code | **Supervision cost** | Human attention is scarce; every new component needs oversight (our supervision-kpi data) |
| Person-hours | **Complexity budget** | System coherence degrades with each addition; more code = more surface area for bugs |
| Sprint capacity | **Integration risk** | New things breaking existing things; agent-generated code especially prone to tight coupling |

### 3. Jevons Paradox Is Already Visible

McLeod explicitly names it: "a 5x productivity improvement wouldn't reduce demand for development — it would dramatically expand the universe of viable software projects." We see this in our own codebase (42 scripts in meta alone, growing). The risk is over-building, not under-building. [SOURCE: McLeod 2026-04]

### 4. The Right Decision Framework

**Old question:** "Is this worth the dev effort?" → Effort | ROI table
**New question:** "Does this improve the system without degrading it?" → Value | Maintenance | Complexity table

Willison's reframe (via UBOS): "Fire-and-forget prompts — let agents generate code even for low-value ideas, then review the output later." This shifts from pre-filtering (don't build) to post-filtering (build, then evaluate). [SOURCE: UBOS citing Willison]

The antifound.com critique adds a crucial nuance: "Code is a high-fidelity prototype — expensive to change. AI tools are systematically accelerating the transition from cheap design phases to expensive implementation phases while leaving upstream uncertainty completely intact." This means the design phase deserves MORE time, not less — even though implementation is cheap. [SOURCE: Agent Wars 2026-03-15]

### 5. What "Effort" Should Actually Mean Now

When we see "Effort" in a decision table, the relevant question is NOT "how long will this take to build?" but:

1. **Maintenance load** — Does this add ongoing drag? (none / low / medium / high)
2. **Complexity cost** — Does this make the system harder to reason about?
3. **Prerequisite gap** — Does this depend on something that doesn't exist yet?
4. **Integration surface** — Does this touch many existing components?
5. **Supervision demand** — Does this need human oversight to operate correctly?

Items that are "high value, zero maintenance, standalone" should be built immediately regardless of LOC count. Items that are "medium value, high maintenance, deeply integrated" should still be deferred — but for the right reason.

## Disconfirmation Results

**Searched for:** "AI coding agents NOT actually cheaper" "hidden costs offset productivity gains" "development cost still matters"

**Found:**
- Osmani's DORA data shows *team* throughput paradox: +98% individual output but +91% review time, no decrease in overall workload. This is real but doesn't contradict the "dev cost ≈ 0" thesis — it confirms that the bottleneck shifted to review/supervision, not that dev cost remained high.
- Kruglov's entropy spiral shows agent-generated code can become MORE expensive to maintain than human-written code. This is the strongest counterargument — but it argues for better maintenance-burden filtering, not for keeping effort-based filtering.
- Agent Wars piece argues implementation speed is counterproductive when design uncertainty is high. Valid — but this argues for better design processes, not for limiting implementation.

**No contradictory evidence found for the core thesis** that creation cost has collapsed. All counterarguments identify NEW costs that should replace effort-based filtering, not preserve it.

## Causal Model

```
Agent capability improvement (exogenous)
    → Creation cost collapses (observed, ~10-100x)
        → Effort-based filtering becomes uninformative (our observation)
        → Jevons Paradox: more gets built (observed: 42 scripts)
            → Maintenance burden increases (entropy spiral)
            → Comprehension debt increases (rubber-stamping risk)
            → Supervision cost becomes dominant (our data)
            → Complexity budget depletes faster
            → Integration risk grows with surface area

Confounders considered:
- "Effort" might proxy for complexity, not dev time → PARTIALLY TRUE
  Some items (claim dependency graph) are gated by prerequisites, not time.
  These should be relabeled to state the actual prerequisite.
- Agent-generated code might be lower quality → REAL but addressable
  Argues for quality gates, not effort gates.
```

## Concrete Debiasing Plan

### 1. Replace "Effort" columns in research memos

| Old Column | New Column | What it measures |
|-----------|-----------|-----------------|
| `Effort` | `Maintenance` | Ongoing drag: none / low / medium / high |
| `Effort to deploy` | `Prerequisites` | What must exist first? (if nothing, say "none") |
| `ROI` (effort-weighted) | `Value` | Impact independent of creation cost |
| "Not worth building" | "Not worth maintaining" | Gate on ongoing cost, not creation cost |

### 2. Update Global CLAUDE.md Pre-Build Check #4

**Before:** "Can we validate at 1/10 the code? Build the 50-line version first."
**After:** "Can we validate with 1/10 the complexity? Build the simplest version first. Expand only after evidence it works. Minimize maintenance surface, not dev time."

### 3. Reframe "Not worth building" sections in research memos

Items should be classified as:
- **Build now** — high value, low maintenance, no prerequisites
- **Build after X** — high value but depends on prerequisite X existing first
- **Don't maintain** — low value relative to ongoing complexity/supervision cost
- **Track** — interesting concept, no current use case

### 4. Update propose-work.py ranking (already clean, but add)

When generating proposals from improvement-log findings, rank by: value × (1 / maintenance_burden) rather than value × (1 / effort).

### 5. Willison's "fire-and-forget" principle for borderline ideas

For items that are borderline: let the agent try building it. If it works and is low-maintenance, keep it. If it creates complexity, revert. Pre-filtering on effort is the wrong gate when creation cost ≈ 0.

## What's Uncertain

1. **How much does agent code quality actually improve with better scaffolding?** Kruglov's entropy spiral assumes unconstrained generation. Our hooks + tests + review may already mitigate this. No empirical data from our own setup.
2. **Where is the equilibrium?** Jevons Paradox says we'll build more. But at what point does maintenance burden cap the system? We don't have a measurement for "total system complexity" to know when we're approaching it.
3. **Does comprehension debt matter for solo + agent setups?** Osmani's data is from teams. For a single human + agents, the comprehension debt dynamic might be different (you only need to understand the system at the level of supervision, not implementation).

## Sources

| Source | Author | Date | URL |
|--------|--------|------|-----|
| The Invisible Governor | Simon Minton | 2026-02-07 | canaryiq briefing |
| When Software Costs Hit Zero | Michael Ulin | 2026-02-22 | whimseylabs substack |
| Code is Cheap (UBOS summary of Willison) | UBOS/Carlos | 2026 | ubos.tech |
| The 80% Problem in Agentic Coding | Addy Osmani | 2026-01-28 | addyo substack |
| The Cost of Agentic Coding | Sam McLeod | 2025-04 | smcleod.net |
| Ascending Spiral of Entropy | Gennadii Kruglov | 2026-03-04 | kruglov.ai |
| Codegen Is Not Productivity | Agent Wars / antifound | 2026-03-15 | agent-wars.com |
| DORA 2025 report | Google | 2025 | [via Osmani] |
| Armin Ronacher developer poll | via Osmani | 2026-01 | [5000 developer survey] |

<!-- knowledge-index
generated: 2026-03-21T23:52:34Z
hash: 45b69b95e86b

sources: 1
  INFERENCE: from claims 1-7
table_claims: 8

end-knowledge-index -->
