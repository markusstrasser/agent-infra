# Schema-Bounded Review Packets for `researcher` and `intel`

**Date:** 2026-03-05
**Question:** Should we replace some long prompt/context-heavy review workflows with smaller schema-bounded packets? If so, where, and how without overfitting?
**Status:** Recommendation memo

## TL;DR

Yes, but narrowly.

Do **not** rewrite all agent-readable docs into YAML or JSON.
Do **not** assume structured input is universally better for frontier models.

Instead, add schemas only at **repeated handoff points** where one step feeds another:
- search results -> evidence set
- evidence set -> reviewer
- reviewer output -> synthesizer
- memo claims -> verification queue

The goal is not "more structure." The goal is **smaller, cleaner interfaces** between substeps.

## Why This Is Worth Trying

Recent papers point in the same direction:

- **AGENTSYS**: isolate raw tool output; only pass validated structured results upward.
- **MCP-Atlas**: real failures cluster in tool use, argument binding, sequencing, and stopping, not final prose.
- **AGENTIF**: long agentic instructions are followed poorly.
- **OCTOBENCH**: models can solve the task while silently violating the scaffold.
- **AutoHarness**: better harness can beat bigger naked model.

That does **not** prove "schemas beat prose" in general. Our own memo says there is no frontier-model evidence for that broad claim. The defensible claim is narrower:

Structured packets help when they act as **machine-checkable interfaces** for repeated workflows.

## What This Is Not

Not a repo-wide migration to structured documents.
Not "put every thought into JSON."
Not a replacement for prose reasoning.
Not a new ontology project.

Keep:
- prose for context, argument, and synthesis
- structured packets for machine-checked state and handoffs

## Where To Apply It

### 1. Shared `researcher`

Current weakness:
- the skill is strong on search discipline, but too much of the workflow still jumps from search output to prose synthesis
- `verify_claim` is a spot-check tool, not a trustworthy intermediate ledger

Recommended packet:

```json
{
  "question": "What is being answered?",
  "claims": [
    {
      "claim": "Specific candidate claim",
      "status": "supported|contradicted|unclear|unverified",
      "sources": [
        {"id": "S1", "url": "...", "type": "paper|web|database"}
      ],
      "evidence": [
        "Concrete supporting or contradicting fact"
      ],
      "open_questions": [
        "What remains unresolved?"
      ]
    }
  ]
}
```

Use:
- after search / reading
- before synthesis
- before claim verification

Do not expose raw search dumps directly to the final synthesizer if a smaller evidence packet can be passed instead.

### 2. `intel` review workflows

Current weakness:
- `llm-check` recommends very large bundles and review-on-review chaining
- this contaminates independence and overloads the prompt

Recommended packet per review:

```json
{
  "question": "What should the reviewer evaluate?",
  "thesis": "Current working thesis",
  "evidence_items": [
    {
      "id": "E1",
      "source_grade": "A2|B3|...",
      "summary": "Short evidence statement",
      "supports": ["H1"],
      "cuts_against": ["H2"]
    }
  ],
  "tasks": [
    "Find strongest disconfirming evidence",
    "List unsupported claims",
    "Identify missing base rates"
  ],
  "output_schema": {
    "major_errors": [],
    "unsupported_claims": [],
    "missing_disconfirmations": [],
    "numerical_checks": [],
    "bottom_line": ""
  }
}
```

This keeps the review targeted and makes reviewer outputs comparable.

### 3. Model-review / cross-model critique

The same pattern applies:
- extract evidence first
- send the same bounded packet to each reviewer independently
- do not feed reviewer A into reviewer B by default
- synthesize only after both outputs exist

## Why This Is Not Overfitting

It stays general if we keep four constraints:

1. **Only target repeated handoffs.**
   If a structure is not reused across many sessions, it is probably yak shaving.

2. **Keep the schema small.**
   Five to eight fields is enough. If the packet needs twenty fields, the interface is probably over-designed.

3. **Measure operational gains, not benchmark vanity.**
   The packet earns its keep only if it reduces context volume, reviewer drift, timeout rate, or unsupported-claim rate.

4. **Keep prose as the final product.**
   The schema is scaffolding, not the deliverable.

## What This Would Enable

- Cleaner independent review across models
- Easier diffing of review outputs across runs
- Cheaper retries because the handoff packet is small
- Better hooks and validators, because the intermediate artifact is parseable
- Easier trace-faithfulness checks, because claims and evidence are already enumerated
- Less context pollution from large bundles and raw search output

## What To Pilot

### Pilot A: `researcher`

Add one intermediate `evidence-packet.json` artifact before final synthesis for:
- high-stakes research
- claim-heavy memos
- anything using `verify_claim`

Success criteria:
- lower unsupported-claim rate
- smaller synthesis context
- clearer unresolved-question reporting

### Pilot B: `intel/llm-check`

Replace "largest relevant bundle" with:
- one thesis packet
- one evidence packet
- one reviewer output schema

Success criteria:
- fewer timeouts
- fewer vague review outputs
- more directly actionable findings per review

## What Not To Build Yet

- repo-wide YAML frontmatter migration
- universal ontology for all research artifacts
- automatic conversion of all memos into schemas
- hard blocking on packet format before the pilot proves useful

## Bottom Line

The right move is not "structured everywhere."
The right move is:

**prose for thinking, structured packets for repeated interfaces.**

That is the smallest change that matches the recent agent-scaffolding papers without turning into a schema religion.

## Sources

- [SOURCE: arXiv:2602.07398] `AGENTSYS`
- [SOURCE: arXiv:2602.00933] `MCP-Atlas`
- [SOURCE: arXiv:2505.16944] `AGENTIF`
- [SOURCE: arXiv:2601.10343] `OCTOBENCH`
- [SOURCE: arXiv:2603.03329] `AutoHarness`
- [SOURCE: structured-vs-prose-for-agents.md]

<!-- knowledge-index
generated: 2026-03-21T23:52:37Z
hash: 17bffb091194


end-knowledge-index -->
