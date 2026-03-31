---
title: "OpenTraces + DSPy Production Patterns"
date: 2026-03-30
tags: [agent-traces, dspy, cost-optimization, schemas]
status: complete
---

## OpenTraces + DSPy Production Patterns — Research Memo

**Question:** Architecture details and reusable patterns from (1) opentraces.ai trace publishing tool, (2) DSPy at Shopify cost reduction case study
**Tier:** Standard | **Date:** 2026-03-30
**Ground truth:** Prior research on agent trace formats (ATIF, OTel GenAI) and DSPy (academic paper, Stanford NLP)

---

### Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | opentraces is a real, published CLI tool (v0.1.1) for sanitizing and publishing agent traces to HF Hub | PyPI package, GitHub repo, website | HIGH | [PyPI](https://pypi.org/project/opentraces/), [GitHub](https://github.com/JayFarei/opentraces) | VERIFIED |
| 2 | Repo created 2026-03-27, 22 stars, MIT license, by @JayFarei | GitHub API | HIGH | [SOURCE: gh api] | VERIFIED |
| 3 | Uses 19 regex patterns + Shannon entropy + context-aware scanning for secret redaction | Website claims | MEDIUM | [SOURCE: opentraces.ai] | UNVERIFIED (no code audit) |
| 4 | Schema aligns with ATIF, Agent Trace, ADP, OTel GenAI standards | README | MEDIUM | [SOURCE: GitHub README] | VERIFIED (claimed, not audited) |
| 5 | "DSPy at Shopify reduced costs from $5.5M to $73K" — specific case study | 12+ queries across Exa, Brave, web fetch | LOW | No source found | NOT FOUND |
| 6 | Shopify built "Scout" — internal tool indexing merchant feedback via MCP | Referenced in Viksit Substack article (from tweet) | MEDIUM | [SOURCE: viksit.substack.com] | VERIFIED (existence only) |
| 7 | DSPy production deployments exist at JetBlue, Databricks, Zoro UK, VMware, Sephora, Replit, Dropbox, Gradient AI | Skylar Payne blog + Portkey blog + Dropbox engineering blog | HIGH | [SOURCE: skylarbpayne.com, portkey.ai, dropbox.tech] | VERIFIED |
| 8 | Zoro UK uses DSPy with Mistral/GPT-4 tiered routing for attribute normalization | Portkey production blog | HIGH | [SOURCE: portkey.ai/blog/dspy-in-production] | VERIFIED |
| 9 | Dropbox optimized Dash relevance judge with DSPy, enabled cheap model migration (gpt-oss-120b, gemma-3-12b) | Dropbox engineering blog | HIGH | [SOURCE: dropbox.tech] | VERIFIED |
| 10 | Gradient AI beat GPT-4 performance on table extraction at 10x lower cost using DSPy | Portkey blog | HIGH | [SOURCE: portkey.ai] | VERIFIED |

---

### Part 1: opentraces.ai (@JayFarei)

**What it is:** A protocol and CLI tool for capturing AI coding agent session traces, sanitizing them (removing secrets, PII, paths), reviewing them locally, and publishing them as JSONL datasets to HuggingFace Hub. Created 2026-03-27. Very early (v0.1.1, 22 stars).

**Architecture:**

```
Agent hooks (Claude Code, Cursor, Cline, Gemini CLI)
       |
       v
  Session capture → parsers/
       |
       v
  pipeline.py → security/ (redaction) + enrichment/ (git signals, attribution)
       |
       v
  clients/ (TUI or web viewer) → human review inbox
       |
       v
  upload/ → HF Hub (JSONL shards, content-hash dedup)
```

**Monorepo structure:**
- `packages/opentraces-schema/` — Pydantic v2 models defining TraceRecord format
- `src/opentraces/parsers/` — agent-specific session log extractors
- `src/opentraces/security/` — secret scanning, anonymization, classification
- `src/opentraces/enrichment/` — git signals, code attribution, metrics
- `src/opentraces/clients/` — browser and terminal review interfaces
- `src/opentraces/upload/` — HF Hub publishing with sharding
- `web/viewer/` — React-based inbox UI

**CLI workflow:**
```bash
opentraces login --token           # HF auth
opentraces init --agent claude     # Setup repo inbox + hooks
opentraces web                     # Browser review UI
opentraces commit --all            # Finalize reviewed traces
opentraces push --repo user/name   # Publish to HF Hub
```

**Two review policies:**
1. **Review** (default) — traces land in local inbox, human approves/rejects/redacts
2. **Auto** — capture, sanitize, commit, push automatically

**Schema (TraceRecord, one JSONL line per session):**
```json
{
  "schema_version": "0.1.0",
  "trace_id": "uuid",
  "task": {"description": "...", "repository": "..."},
  "agent": {"name": "claude-code", "model": "opus-4.6"},
  "steps": [{"role": "...", "content": "...", "tool_calls": [], "reasoning_content": "..."}],
  "outcome": {"success": true, "committed": true, "patch": "..."},
  "attribution": {"files": [{"path": "...", "ranges": [...]}]},
  "metrics": {"total_steps": 15, "estimated_cost_usd": 0.42},
  "dependencies": ["numpy", "pandas"]
}
```

**Standards alignment (claimed):** ATIF (trajectory structure), Agent Trace (code attribution), ADP (training pipeline interop), OTel GenAI (observability).

**Sanitization pipeline:**
- 19 regex patterns for known secret formats (API keys, tokens, credentials)
- Shannon entropy analysis (catches high-entropy strings that aren't matched by regex)
- Context-aware scanning (filesystem paths, emails, DB connection strings)
- Redaction tokens: `[REDACTED_API_KEY]`, `[REDACTED_EMAIL]`, etc.

**Downstream ML use cases (from schema design):**
- **SFT:** Fine-tuning on real agent workflows with outcome-validated quality
- **RL/RLHF:** Committed patches as reward proxy, per-step token costs for penalized reward
- **Analytics:** Cache hit rates, token breakdowns, model distribution
- **Domain sourcing:** Filter by language tags, dependencies, VCS context

**What's reusable for personal agent infrastructure:**

1. **Schema as a contract.** The TraceRecord format is a solid starting point for structured agent session logging. The key insight: one JSONL line per session, with steps/outcome/attribution/metrics as first-class fields. Our session receipts already have similar structure but lack attribution (which files were touched, with line ranges) and outcome signals (did the patch commit, was it correct).

2. **Sanitization-before-export pattern.** Even for private use, the regex + entropy + context-aware scanning pipeline is valuable. We already redact in some contexts but not systematically. The 19-pattern regex library is worth stealing.

3. **Review inbox with two policies.** The auto/review policy split maps directly to our trust tiers: autonomous work gets auto-captured, uncertain work goes through review. We already have session-analyst as a post-hoc reviewer — opentraces makes the review synchronous and per-session.

4. **Agent hooks as capture mechanism.** They install as `.claude/skills/opentraces/` — using the skills directory as a distribution mechanism is clever. Our skills infrastructure already supports this.

5. **Content-hash dedup across pushes.** Prevents duplicate trace uploads. Relevant if we ever export traces for training or sharing.

**What's NOT reusable:**
- HuggingFace Hub integration (we don't publish datasets)
- The React web viewer (our TUI/dashboard approach is simpler and sufficient)
- Multi-agent parser support (we're Claude Code only)
- The social/crowdsourcing aspect (this is designed for community data donation)

---

### Part 2: "DSPy at Shopify" — Case Study Investigation

**Finding: The specific "$5.5M to $73K" DSPy case study at Shopify does NOT appear in any public source.**

After 12+ searches across Exa, Brave, direct URL fetching, and targeted quote searches, no blog post, presentation, slides, or talk matching this description was found. What exists:

- **Shopify Scout** is a real internal tool that "indexed hundreds of millions of merchant feedback items" and exposes them via MCP (referenced in a tweet, cited by Viksit Gaur on Substack). No public technical details about its architecture or cost structure.
- **Viksit Gaur's Substack** is a tutorial showing how to *build something like* Shopify Scout using DSPy, not a Shopify case study.
- **No Shopify engineer has publicly presented** a DSPy cost reduction story with these numbers.

**Assessment:** The "$5.5M to $73K" figure is likely either (a) from a different company conflated with Shopify, (b) from a private/internal presentation not yet public, or (c) a fabricated/exaggerated claim circulating on social media. [UNVERIFIED — cannot confirm or deny existence of non-public presentations.]

**What DOES exist — real DSPy production patterns:**

#### Verified DSPy Production Deployments

| Company | Use Case | Pattern | Cost Impact | Source |
|---------|----------|---------|-------------|--------|
| **Zoro UK** | Product attribute normalization across millions of items from 300+ suppliers | Two-tier: Mistral for triage, GPT-4 for complex sorting | Not quantified | [SOURCE: portkey.ai/blog] |
| **Gradient AI** | Table data extraction from messy documents | DSPy-optimized pipeline | "Beat GPT-4 at 10x lower cost per table, 10x lower manual effort" | [SOURCE: portkey.ai/blog] |
| **Dropbox** | Dash relevance judge for search results | DSPy optimization enabling model migration | Enabled switch to gpt-oss-120b and gemma-3-12b without rewrite | [SOURCE: dropbox.tech] |
| **JetBlue, Databricks, VMware, Sephora, Replit** | Listed as users | Not detailed | Not quantified | [SOURCE: skylarbpayne.com] |

#### The Real DSPy Cost Reduction Pattern

The pattern that the "$5.5M to $73K" claim likely describes (even if the specific numbers are unverified) is well-documented across multiple companies:

1. **Start with a large model** (GPT-4/5.x class) doing everything in a single prompt
2. **Decompose into sub-tasks** using DSPy signatures (typed I/O declarations)
3. **Optimize each sub-task independently** — DSPy's compilers (MIPRO, BootstrapFewShot) find optimal prompts/examples for each
4. **Migrate each sub-task to the cheapest model that maintains quality** — often GPT-3.5/4o-mini/Mistral/Gemma class
5. **Result:** 10-100x cost reduction on inference while maintaining or improving quality

**The math that generates "$5.5M to $73K" style numbers:**
- Large model at $15/M output tokens, processing 1M requests/day
- After decomposition: 80% of sub-tasks route to a $0.15/M token model
- Remaining 20% stay on the large model but with shorter, optimized prompts
- Combined: 75-98x cost reduction is arithmetically plausible

**DSPy architecture for this pattern:**
```python
class IntentClassifier(dspy.Signature):
    """Classify user intent into one of N categories."""
    query: str = dspy.InputField()
    intent: Literal["search", "retrieve", "analyze"] = dspy.OutputField()

class SubTaskRouter(dspy.Module):
    def __init__(self):
        self.classifier = dspy.Predict(IntentClassifier)  # cheap model
        self.search_handler = dspy.ChainOfThought(SearchSig)  # medium model
        self.analyze_handler = dspy.ChainOfThought(AnalyzeSig)  # expensive model
    
    def forward(self, query):
        intent = self.classifier(query=query).intent
        if intent == "search":
            return self.search_handler(query=query)  # routed to cheap
        elif intent == "analyze":
            return self.analyze_handler(query=query)  # stays expensive
```

**What's reusable for personal agent infrastructure:**

1. **Decomposition + tiered routing is the pattern, not DSPy itself.** DSPy is a framework for discovering optimal prompts and routing. For a personal project with low volume, the framework overhead isn't justified — but the *pattern* of decomposing a monolithic prompt into typed sub-tasks with per-task model selection is directly applicable.

2. **Typed signatures as contracts.** DSPy's `Signature` class (typed input/output) is the same insight as our skill format: declare what goes in and what comes out, let the runtime handle the rest. We already have this in skills; DSPy proves it works at scale.

3. **Compilation as evaluation.** DSPy compilers need examples and metrics. The process of building examples + metrics for each sub-task is itself a form of eval infrastructure. Our `safe-lite-eval.py` and `calibration-canary.py` serve a similar purpose.

4. **Model migration without rewrite.** Dropbox's key finding: DSPy let them swap models (GPT-4o to gemma-3-12b) without changing application code. This is the same benefit our `llmx` transport routing provides — model-agnostic dispatch.

5. **The Skylar Payne insight:** "Engineers inevitably rebuild DSPy's abstractions poorly rather than adopting them deliberately." The abstractions are: typed I/O, composable modules, evaluation-driven optimization, model-agnostic dispatch. We have all four in different forms across our infrastructure. The gap: we don't have automated prompt/few-shot optimization (DSPy's MIPRO compiler). This matters only when volume justifies it.

---

### What's Uncertain

1. **opentraces schema stability.** v0.1.0, 3 days old, 22 stars. The schema will change. Don't build against it yet — watch for v0.2+.

2. **opentraces sanitization quality.** "19 regex patterns + Shannon entropy" is claimed but unaudited. Secret scanning is a hard problem (GitHub's own scanner has 100+ patterns). For real security, this needs adversarial testing.

3. **The "$5.5M to $73K" Shopify DSPy case study.** Cannot confirm this exists as a public artifact. May be conflated with the general DSPy cost reduction pattern applied at an unnamed company, or from a private presentation. The arithmetic is plausible but the specific attribution to Shopify is unverified.

4. **DSPy at scale for agent infrastructure.** Most verified production uses are for specific ML tasks (classification, extraction, search relevance) — not for general agent orchestration. The agent orchestration use case is described in tutorials but lacks verified production case studies.

---

### Search Log

| Query | Tool | Result |
|-------|------|--------|
| "opentraces.ai jayfarei CLI" | Exa | Found PyPI, HF dataset, GitHub |
| "opentraces.ai jayfarei" | Brave | Found opentraces.ai site |
| "DSPy Shopify $5.5M $73K" | Exa | No match — got general DSPy articles |
| "DSPy Shopify $5.5M $73K" | Brave | No match |
| opentraces.ai site fetch | WebFetch | Full site content extracted |
| GitHub API repo metadata | gh api | Repo stats confirmed |
| "DSPy cost optimization $5.5M" | Exa (advanced) | No match, results overflow |
| opentraces README (raw GitHub) | WebFetch | Architecture + schema extracted |
| Viksit Substack (Shopify Scout DSPy) | WebFetch | Tutorial only, not case study |
| skylarbpayne.com DSPy patterns | WebFetch | Lists DSPy users, no Shopify cost numbers |
| "DSPy $5.5 million $73K" exact | Brave | Zero results |
| Portkey DSPy production blog | WebFetch | Zoro UK + Gradient AI cases, no Shopify |
| DSPy intent decomposition cost savings | Brave | General pattern articles, no specific $5.5M case |
| LLM cost reduction millions DSPy | Exa | General articles only |
| HF opentraces-test dataset | WebFetch | Timeout |

<!-- knowledge-index
generated: 2026-03-31T03:08:12Z
hash: 4e0de83e2055

title: OpenTraces + DSPy Production Patterns
status: complete
tags: agent-traces, dspy, cost-optimization, schemas
table_claims: 10

end-knowledge-index -->
