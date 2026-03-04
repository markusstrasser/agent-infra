# Structured vs Prose for Agent-Read Documents

**Date:** 2026-03-03
**Status:** Empirical gap — no frontier-model evidence exists
**Consult before:** Schema design for agent-read docs, conviction journal format, entity doc format, YAML frontmatter decisions

## TL;DR

No published research tests whether structured formats (YAML, JSON, XML, schemas) vs natural language prose affects comprehension/accuracy on frontier models (Claude 4.5/4.6, GPT-5.x, Gemini 3.x). Zero papers. The question is empirically open.

The only frontier-relevant signal comes from **Anthropic's official Claude 4.6 documentation**, which distinguishes:
- **Prose** for progress notes, general context, reasoning
- **Structured formats** for state data (test results, task status, schema-bound information)

Practical recommendation: structure what machines parse, prose what only LLMs read. But this is architectural reasoning, not research-backed.

## The Feature Engineering Analogy

The question arose from an observation: schemas in agent-read documents feel like "feature engineering before deep learning" — manually structuring knowledge that LLMs can read as sentences. This analogy is **partially valid**:

| Aspect | Analogy holds | Analogy breaks |
|--------|--------------|----------------|
| LLM comprehension | Models can read prose as well as YAML | — |
| Programmatic consumers | — | Scripts/validators need parseable structure |
| Cross-session drift | — | Taxonomies prevent semantic drift; prose varies |
| Token efficiency | Structure adds overhead | — |
| Expressiveness | Schemas constrain what can be said | — |
| Maintenance burden | Schema evolution costs engineering time | — |

The analogy breaks because schemas serve **multiple consumers** (not just LLMs), and controlled vocabularies are **taxonomies** (preventing drift), not feature engineering (selecting representations).

## Evidence Inventory

### Frontier-Model Evidence (Claude 4.5/4.6, GPT-5.x, Gemini 3.x)

**None exists.** Exhaustive search: Semantic Scholar, Exa, Perplexity, Brave, arXiv. Zero papers testing structured vs prose input formatting on frontier models.

### Provider Documentation (closest to frontier evidence)

**Anthropic (Claude 4.6)** — [docs.anthropic.com/claude/docs/use-xml-tags](https://docs.anthropic.com/claude/docs/use-xml-tags)
- Recommends XML tags for prompt structure: "XML tags help Claude parse complex prompts unambiguously"
- State management: "Use unstructured text for progress notes" / "Use structured formats for state data"
- No benchmarks comparing formats; this is a recommendation, not measured evidence
- Prefilled responses deprecated — "newer models can reliably match complex schemas when told to"

**OpenAI** — [platform.openai.com/docs/guides/structured-outputs](https://platform.openai.com/docs/guides/structured-outputs)
- Structured Outputs presented as enabling, not degrading
- Shows examples of CoT reasoning inside structured output schemas
- No benchmarks comparing input formats; no mention of reasoning degradation
- Absence of degradation data ≠ evidence of no degradation

**Google (Gemini 3.x)** — No first-party research on format effects found. Third-party guides recommend "structure beats volume" for long context but cite no benchmarks.

### Pre-Frontier Evidence (validity uncertain for frontier models)

| Paper | Models | Key Finding | Frontier Validity |
|-------|--------|-------------|-------------------|
| He et al. 2024 (Microsoft/MIT, 157 cites) | GPT-3.5, GPT-4 | Performance varies up to 40% by format. No universally optimal format. Larger models more robust. | **UNCERTAIN** — trend toward robustness suggests frontier cares less, but untested |
| Tam et al. 2024 "Let Me Speak Freely" (77 cites) | GPT-3.5/4 era | Structured output constraints degrade reasoning | **CONTESTED** — dottxt rebuttal showed methodological flaws; even pre-frontier finding is disputed |
| dottxt "Say What You Mean" (rebuttal) | Llama-3-8B | When prompts are equal, structured *outperforms* unstructured (77% vs 73% on Last Letter) | **PRE-FRONTIER** — Llama-3-8B is not frontier |
| Johnson et al. 2025 (NLT) | DeepSeek-V3, Llama 4 Scout | Plain English +18pp over JSON for tool selection | **PRE-FRONTIER** — no frontier-class models tested |
| ImprovingAgents 2026 | GPT-5 Nano, Llama 3.2 3B, Gemini 2.5 Flash Lite | YAML > Markdown > JSON > XML for nested data | **PRE-FRONTIER** — small models, not frontier |
| Elnashar et al. 2025 (Vanderbilt) | GPT-4o, Claude (?), Gemini (?) | JSON/YAML boost accuracy for structured data generation | **PRE-FRONTIER** — models not specified precisely |

### The "Let Me Speak Freely" Dispute

This paper (Tam et al. 2024, 77 citations) claimed structured output degrades reasoning. It became widely cited. However:

**dottxt rebuttal found critical flaws:**
1. Different prompts used for structured vs unstructured conditions (not apples-to-apples)
2. JSON prompts didn't mention JSON or provide schema
3. The "Perfect Text Parser" (Claude Haiku) was doing heavy lifting for the unstructured condition
4. When fixed with equal prompts: structured outperformed unstructured on all three tasks

**Status:** The original claim is methodologically compromised. But both the original and the rebuttal tested only pre-frontier models. The question remains open for frontier.

## Scale-Independent Findings

These hold regardless of model generation (architectural or physical, not model-dependent):

1. **Schemas serve non-LLM consumers** — Scripts, validators, dashboards need parseable structure. Tautological.
2. **Controlled vocabularies prevent cross-session drift** — An LLM writing "cautiously negative" / "bearish" / "probably avoid" across sessions makes aggregation impossible. Taxonomies are architectural constraints, not format choices.
3. **Token cost of structure is real** — XML uses ~80% more tokens than Markdown for equivalent data (ImprovingAgents). YAML uses ~10% more than Markdown.
4. **"Larger models more format-agnostic"** — Consistent trend across all pre-frontier studies. Reasonable to extrapolate to frontier, but unverified.

## Practical Recommendations

Based on architectural reasoning + Anthropic's official distinction (not research benchmarks):

| Content type | Recommended format | Rationale |
|-------------|-------------------|-----------|
| Taxonomy (conviction terms, action terms) | Controlled vocabulary | Prevents drift, enables aggregation |
| Machine-parsed fields (dates, probabilities, KL divergence) | YAML frontmatter | Scripts/validators/dashboards need exact values |
| Evidence, reasoning, context | Prose | Maximum expressiveness for LLM + human readers |
| Scenario probabilities | Structured (YAML) | Arithmetic precision, not "bull case seems less likely" |
| Progress notes, session context | Prose | Anthropic's own recommendation for Claude 4.6 |
| Test results, task status | Structured (JSON/YAML) | Anthropic's own recommendation for Claude 4.6 |

**Heuristic:** If nothing downstream parses a field except another LLM, it probably doesn't need to be YAML — it could be a sentence.

## What Would Change This Assessment

1. **Any benchmark testing format sensitivity on Claude 4.5/4.6, GPT-5.x, or Gemini 3.x** — would immediately become the primary evidence
2. **Anthropic/OpenAI/Google publishing internal benchmarks** on format effects for their latest models
3. **A well-controlled "Let Me Speak Freely" replication** on frontier models (same prompts, proper schema description, multiple frontier models)
4. **Our own empirical test** — we could design a small benchmark: same entity doc in YAML frontmatter vs prose, test extraction accuracy on Opus 4.6. ~$5 of API calls would provide more evidence than everything published.

## Search Log

14 searches across S2, Exa, Perplexity, Brave. Convergence after search 12: no frontier evidence exists. Full log in session transcript.

## Papers in Corpus

- He et al. 2024 "Does Prompt Formatting Have Any Impact on LLM Performance?" (S2: 113873a4e58e2ff15ce3523ee9fb629ff6dddfe4)
- Tam et al. 2024 "Let Me Speak Freely?" (S2: 7c394a8b4db70d7424abc300749fff0fe580bdae)
- Elnashar et al. 2025 "Prompt engineering for structured data" (S2: 4d2ff83ff3373c8480144d55684cd34a6376974f)
