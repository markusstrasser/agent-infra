## SkillRouter: Retrieve-and-Rerank Skill Selection for LLM Agents at Scale

**Question:** How does SkillRouter work and is its retrieve-and-rerank approach applicable to our ~50-skill system?
**Tier:** Standard | **Date:** 2026-03-27
**Sources:** Primary paper (arXiv:2603.22455, Zheng et al. 2026, Alibaba Group) + AgentSkillOS (arXiv:2603.02176, Li et al. 2026, Shanghai AI Lab)

---

### Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | 74.0% Hit@1 on 80K skill pool with 1.2B params | Benchmark results | HIGH | [arXiv:2603.22455 Table 2] | VERIFIED |
| 2 | Removing skill body causes 29-44pp accuracy drop | Ablation study | HIGH | [arXiv:2603.22455 Section 3.1] | VERIFIED |
| 3 | Skill descriptions receive only 1.0% of cross-encoder attention | Attention analysis | HIGH | [arXiv:2603.22455 Section 3.2] | VERIFIED |
| 4 | Pointwise reranking loses 30.7pp vs listwise | Ablation study | HIGH | [arXiv:2603.22455 Section 5.4.2] | VERIFIED |
| 5 | Fine-tuned 0.6B beats zero-shot 8B (65.4 vs 64.0 Hit@1) | Benchmark comparison | HIGH | [arXiv:2603.22455 Section 5.2] | VERIFIED |
| 6 | BM25 on name+description = 0% accuracy | Ablation | HIGH | [arXiv:2603.22455 Section 3.1] | VERIFIED |
| 7 | 39,065 false negatives filtered from training data | Data pipeline stats | HIGH | [arXiv:2603.22455 Section 5.4.1] | VERIFIED |

---

### 1. Architecture Overview

SkillRouter is a two-stage pipeline: **bi-encoder retrieval + cross-encoder reranking**, totaling 1.2B parameters (0.6B each). Designed for selecting the right skill from pools of ~80,000 skills. [SOURCE: arXiv:2603.22455]

**Stage 1 — Bi-encoder Retrieval (SR-Emb-0.6B):**
- Decoder-based embedding model encodes both query and skills into shared embedding space
- All skills pre-encoded offline; online cost is encoding the query + ANN search
- Cosine similarity reduces 80K skills to top-20 candidates
- Trained with in-batch InfoNCE loss + multi-source hard negative mining (semantic, lexical, taxonomy, random negatives)

**Stage 2 — Cross-encoder Reranking (SR-Rank-0.6B):**
- Decoder-based cross-encoder jointly processes query + each candidate with full token-level cross-attention
- Processes all 20 candidates, produces final ranking
- Trained with listwise cross-entropy loss (softmax over relevance scores of all 20 candidates)
- Pointwise loss (BCE, scoring each skill independently) collapses to 43.3% Hit@1 vs 74.0% — listwise modeling of relative ordering is essential

### 2. Skill Representation

Skills have three fields:
- **Name:** identifier (e.g., `speech-to-text`)
- **Description:** one-sentence summary (e.g., "Transcribe audio files using Whisper")
- **Body:** full implementation/specification (e.g., "Converts audio/video files to text using OpenAI Whisper model. Supports chunked processing for long files, multiple output formats (txt, srt, vtt)...")

For retrieval, concatenated as: `{name} | {description} | {body}`. Truncated to 300 tokens (description) and 2,500 tokens (body).

**Critical finding — body is the signal:**

| Field | Attention Share | Information Content |
|-------|----------------|---------------------|
| Name | 7.3% | Identifier only |
| Description | 1.0% | Subsumed by body |
| Body | 91.7% | Decisive signal |

Removing the body causes **29-44 percentage point degradation** across all methods. BM25 with only name+description = literally 0% accuracy. The paper directly challenges the progressive disclosure pattern (showing agents only names+descriptions) as fundamentally insufficient for routing.

### 3. Training Pipeline

**Synthetic query generation (37,979 pairs):**
- GPT-4o-mini generates realistic task requests from skill metadata + body preview
- Key constraint: skill name must NOT appear in the query — forces learning functional requirements, not identity matching
- Queries describe concrete scenarios with specific inputs/outputs

**False negative filtering (three layers):**
Community skill repositories contain many functional duplicates. Training with these as negatives corrupts the signal.

1. **Name deduplication:** Remove negatives sharing exact name with ground truth (24,879 removed)
2. **Body overlap:** Trigram Jaccard similarity > 0.6 with ground truth body (13,860 removed)
3. **Embedding similarity:** Cosine > 0.92 with ground truth embedding (326 removed)

Total: 39,065 false negatives removed. Without this filtering, the model learns to penalize functionally equivalent skills, degrading performance.

**Hard negative mining (multi-source):**
- Semantic negatives (similar embeddings, different function)
- Lexical negatives (BM25 high-scorers that are wrong)
- Taxonomy negatives (same category, different skill)
- Random negatives (distribution baseline)

### 4. What Breaks at Scale

The paper identifies three failures of naive approaches:

**a) Metadata-only routing fails catastrophically.**
Current agent architectures (Claude Code included) expose only names and descriptions to the LLM for selection. The paper proves this is fundamentally insufficient — the body contains 91.7% of the selection-relevant information. This is the core insight.

**b) Pointwise scoring fails in homogeneous pools.**
When many skills are functionally similar (e.g., multiple git tools, multiple database migration tools), pointwise models assign similar scores to all candidates, effectively randomizing the ranking. Listwise loss forces the model to learn *relative* ordering among candidates. 30.7pp difference.

**c) Scale inverts the value of model size vs task-specific training.**
A zero-shot 8B model (64.0%) underperforms a fine-tuned 0.6B model (65.4%). At scale, task-specific training signal > raw model capacity. The 1.2B pipeline matches or exceeds 16B zero-shot systems.

### 5. Benchmark Structure

**Skill pool:** ~80,000 skills across 51 functional categories (database migration, code linting, API integration, git, docker, video editing, audio transcription, CI/CD, data format conversion, etc.)

**Sources:**
- **SkillBench:** Expert-curated task-skill mappings with verified ground truth (75 core queries)
- **Community skills:** Open-source repositories — high homogeneity, functional overlap, long-tail distribution

**Difficulty tiers:**
- **Easy (78,361 skills):** Base pool with all metadata intact
- **Hard (79,141 skills):** +780 LLM-generated distractors that are topically related but functionally distinct:
  - Same-domain-different-problem
  - Same-tech-different-use
  - Over-generalized (broader version lacking specific capability)

**Baselines beaten:**
- BM25: 31.4% Hit@1
- Best zero-shot embedder (Qwen3-Emb-8B): 64.0%
- OpenAI text-embedding-3-large, Gemini embedding-001: included but underperform SkillRouter
- GPT-4o-mini and GPT-5.4-mini as listwise rerankers: included
- SkillRouter 1.2B: **74.0% Hit@1, MRR@10 = 0.791**

### 6. Comparison: AgentSkillOS (Alternative Approach)

AgentSkillOS (Li et al. 2026) takes a different approach — tree-based retrieval + DAG orchestration:
- Skills organized into a **capability tree** via recursive categorization
- LLM traverses the tree to find relevant category nodes, then prunes
- Usage-frequency queue promotes active skills; dormant index for rare ones
- Task decomposition into DAG with three strategies (quality-first, efficiency-first, simplicity-first)
- Tested at 200 to 200K skills
- Claims tree-based retrieval surfaces "non-obvious yet functionally relevant skills" that embedding similarity misses

Both papers converge on: **metadata alone is insufficient; the skill body/implementation matters.**

---

### Applicability to Our System (~50 Skills)

**Current state:** ~44 SKILL.md files with frontmatter (name, description, triggers). Claude Code matches user input to skill descriptions loaded into the system prompt. At 50 skills, the entire skill index fits in context.

**Assessment: SkillRouter is overkill for 50 skills, but the findings are load-bearing.**

#### What's directly applicable NOW:

1. **Body > description for routing.** This is the paper's strongest finding and directly challenges our architecture. Currently, Claude Code sees skill names + descriptions in the system prompt. The actual skill body (the full SKILL.md content) is only loaded AFTER selection. If the LLM is making selection decisions based primarily on descriptions, we're operating in the regime the paper shows is 29-44pp worse.

   **Implication:** Our skill descriptions need to be much richer, or we need a mechanism to surface body-level information during selection. At 50 skills, we could potentially include abbreviated bodies (first 200 tokens of each) in the selection context — that's ~10K tokens, feasible.

2. **Functional overlap is the hard problem, not scale.** With 50 skills, we don't have a retrieval problem — they all fit in context. But we DO have a discrimination problem: `researcher` vs `investigate` vs `dispatch-research` vs `entity-management` all handle "find out about X" queries. The paper shows this is exactly where pointwise (independent) scoring fails. The fix at our scale: better negative definitions in descriptions ("NOT for: X, use Y instead" — which we already do in some skills).

3. **Distractor robustness matters.** The Hard benchmark uses same-domain-different-problem distractors. Our skill set has exactly this pattern: `causal-check` vs `causal-dag` vs `causal-robustness` are all "causal" but serve different purposes. Description-level disambiguation is essential.

#### What becomes relevant at 200+ skills:

4. **Retrieve-and-rerank pipeline.** If skill count grows past ~200 (where the full index exceeds what fits in the system prompt), a two-stage pipeline becomes necessary. The architecture to steal:
   - Pre-encode all skills (including bodies) with a small embedding model
   - At query time: embed the query, ANN search for top-20, then rerank with cross-attention
   - Listwise reranking, not pointwise — critical for homogeneous skill pools

5. **False negative filtering for training data.** If we ever fine-tune a router, the three-layer filtering pipeline (name dedup, body Jaccard > 0.6, embedding cosine > 0.92) is essential for community skill repos with functional duplicates.

6. **Synthetic query generation.** GPT-4o-mini generating task requests from skills (without naming the skill) is a cheap way to create training data. Could also be used for skill testing — generate 100 queries per skill, measure if the right skill gets selected.

#### What we should NOT do:

- **Do not build a 1.2B parameter routing model for 50 skills.** The entire problem fits in Claude Code's context window. The LLM doing the routing is orders of magnitude larger and more capable than SkillRouter.

- **Do not add an embedding index for 50 skills.** Overhead > benefit at this scale. The break-even is probably around 200-500 skills.

- **Do not strip bodies from the selection process.** If anything, we should move in the opposite direction — make MORE of the body visible during selection, not less.

### Concrete Next Steps (if pursuing)

1. **Audit skill descriptions for body-level information.** The paper proves descriptions are nearly useless for routing (1% attention). Check if our descriptions contain enough functional detail for discrimination, or if they're just summaries that the body would need to resolve.

2. **Generate synthetic queries per skill.** Use GPT-4o-mini to generate 50-100 task requests per skill (without naming it). Test Claude Code's selection accuracy. This is cheap (~$0.50 total) and gives a baseline measurement.

3. **Add negative routing to descriptions.** The paper's Hard benchmark shows same-domain distractors are the failure mode. Our `researcher` skill already has "NOT for: bio/medical claim verification (use epistemics), causal inference (use causal-dag or causal-check)..." — extend this pattern to all skills with functional neighbors.

4. **Consider abbreviated body injection.** At 50 skills, we could include the first 200 tokens of each skill's body in the system prompt selection context. That's ~10K additional tokens — within budget. Would need to measure if this improves triggering accuracy.

5. **Set a 200-skill threshold for architecture change.** Below 200: optimize descriptions + negative routing. Above 200: implement retrieve-and-rerank with a small embedding model.

---

### What's Uncertain

- **Our actual skill triggering accuracy.** We have no measurement. The paper's synthetic query generation approach could be repurposed as an eval: generate queries, check if Claude Code selects the right skill. Without this baseline, we can't know if improvements are needed.

- **Whether Claude Code's LLM-based selection already captures body-level knowledge.** Claude Code has seen the full skill bodies in prior conversations. The LLM may have internalized functional distinctions that a description-only system would miss. This is different from SkillRouter's scenario where the router has NEVER seen the bodies.

- **How Claude Code actually performs selection.** The internal mechanism may already be more sophisticated than "match query to description." We don't have visibility into the skill selection process beyond what's documented.

- **The paper's generalization.** SkillRouter was tested on a specific 80K pool of largely open-source/community tools. Our skills are curated, domain-specific, and have rich descriptions with negative routing. The failure modes may not transfer.

### References

- Zheng, Y., Zhang, Z., Ma, C., Yu, Y., Zhu, J., Dong, B., & Zhu, H. (2026). SkillRouter: Retrieve-and-Rerank Skill Selection for LLM Agents at Scale. arXiv:2603.22455.
- Li, H., Mu, C., Chen, J., Ren, S., Cui, Z., Zhang, Y., Bai, L., & Hu, S. (2026). Organizing, Orchestrating, and Benchmarking Agent Skills at Ecosystem Scale. arXiv:2603.02176.

<!-- knowledge-index
generated: 2026-03-27T04:49:48Z
hash: 990590857a30

table_claims: 7

end-knowledge-index -->
