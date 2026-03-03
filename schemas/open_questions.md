# Open Questions Template

Track research questions with their resolution status. **Null results and refutations
are first-class knowledge** — a question answered "no" or "insufficient evidence" is
as valuable as one answered "yes."

## Schema

Each question entry uses this format:

```markdown
### Q{N}: {question text}

- **Status:** {CONFIRMED | REFUTED | NO_EVIDENCE_FOUND | CONTESTED}
- **Resolution date:** {YYYY-MM-DD}
- **Evidence:** {brief summary of what was found or not found}
- **Sources:** {citation list}
- **Confidence:** {HIGH | MEDIUM | LOW}
```

## Status Enum (strict)

| Status | Meaning | Example |
|--------|---------|---------|
| `CONFIRMED` | Evidence supports the hypothesis | "Yes, API supports batch — docs section 4.2" |
| `REFUTED` | Evidence contradicts the hypothesis | "No, benchmark shows 2x slower, not faster" |
| `NO_EVIDENCE_FOUND` | Searched thoroughly, found nothing | "No published studies on X after searching S2, Exa, PubMed" |
| `CONTESTED` | Conflicting evidence from credible sources | "Model A says X, Model B says Y, no resolution" |

## Health Metric

Track confirmation rate as system health:
- **Target:** 40-60% CONFIRMED (healthy balance of positive and negative findings)
- **Red flag:** >80% CONFIRMED = likely publication bias / confirmation bias
- **Red flag:** >80% NO_EVIDENCE_FOUND = questions may be poorly scoped

## Example

### Q1: Does Brave Search API support structured data extraction?

- **Status:** REFUTED
- **Resolution date:** 2026-03-02
- **Evidence:** Brave API returns raw search results only. No extraction endpoint.
  Firecrawl and Exa have extraction; Brave does not.
- **Sources:** [docs.brave.com/api](https://docs.brave.com/api), research/brave-search-api-deep-dive.md
- **Confidence:** HIGH

### Q2: Is there a published cross-model factual verification benchmark?

- **Status:** NO_EVIDENCE_FOUND
- **Resolution date:** 2026-03-02
- **Evidence:** Searched S2 ("cross-model verification benchmark"), Exa, Google Scholar.
  Found SAFE (same-model), VeriScore (same-model), FINCH-ZK (same-model with zero-knowledge).
  No benchmark specifically measures cross-family verification effectiveness.
- **Sources:** [INFERENCE from search absence]
- **Confidence:** MEDIUM
