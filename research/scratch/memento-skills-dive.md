## Memento-Skills: Let Agents Design Agents -- Research Memo

**Question:** How does Memento-Skills implement continual skill learning for LLM agents, and what mechanisms should we consider adopting for our skill system?
**Tier:** Deep | **Date:** 2026-03-27
**Ground truth:** We have a skill system (`~/Projects/skills/`, SKILL.md format, symlinked into projects) with a `suggest-skill` slash command for detecting automation opportunities. Skills are manually authored via `skill-creator` skill. No automated evolution, no quality gating beyond manual review, no behavior-aligned retrieval (Claude Code uses metadata+description matching).

**Paper:** arXiv:2603.18743, submitted 2026-03-19
**Authors:** Huichi Zhou, Siyuan Guo, Anjie Liu, Zhongwei Yu + 13 others (Memento-Team: UCL, HKUST Guangzhou, AI Lab Yangtze River Delta)
**Code:** https://github.com/Memento-Teams/Memento-Skills (388 stars, Python, MIT-adjacent)
**Website:** https://skills.memento.run/

---

### Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | +13.7pp on GAIA test (52.3% -> 66.0%) after 3 rounds of reflective training | Benchmark, self-reported | HIGH | [arXiv:2603.18743] | VERIFIED (paper) |
| 2 | +20.8pp on HLE test (17.9% -> 38.7%), 116% relative improvement | Benchmark, self-reported | HIGH | [arXiv:2603.18743] | VERIFIED (paper) |
| 3 | Skill library grows from 5 seed skills to 41 (GAIA) / 235 (HLE) | Self-reported | MEDIUM | [arXiv:2603.18743] | VERIFIED (paper) |
| 4 | Behavior-aligned router Recall@1: 0.60 vs BM25 0.32 | Ablation | MEDIUM | [arXiv:2603.18743] | VERIFIED (paper) |
| 5 | Convergence guarantee under KL-regularized soft policy iteration (Theorem 1.3) | Formal proof | MEDIUM | [arXiv:2603.18743] | VERIFIED (paper, no convergence rate proven) |
| 6 | Skills form semantically coherent clusters matching task taxonomy | Visualization, self-reported | LOW | [arXiv:2603.18743] | CLAIMED (no independent eval) |
| 7 | Unit-test gate prevents regression on skill updates | Architecture claim | MEDIUM | [arXiv:2603.18743] | VERIFIED (code exists) |

---

### 1. Skill Format and Representation

Skills are structured markdown files in a directory-based layout. Each skill is a folder:

```
skill-name/
+-- SKILL.md          # Required. YAML frontmatter + markdown body
+-- scripts/          # Executable code for deterministic tasks
+-- references/       # Docs loaded into context as needed
+-- assets/           # Templates, icons, fonts
```

**SKILL.md structure** (from actual repo code):

```yaml
---
name: web-search
description: Web search and content fetching. Use when the user needs
  to search the web for information or fetch content from URLs.
metadata:
  dependencies:
    - httpx
    - beautifulsoup4
    - markdownify
---
```

Body is free-form markdown describing: setup, available scripts with usage examples, workflow steps, requirements. No rigid schema beyond the frontmatter.

**Progressive disclosure** (three-level loading):
1. **Metadata** (name + description) -- always in context (~100 words)
2. **SKILL.md body** -- loaded when skill triggers (<500 lines recommended)
3. **Bundled resources** -- loaded as needed (unlimited, scripts execute without loading)

**Direct comparison to our system:** Nearly identical to what we already have. Our SKILL.md format uses `name`, `description`, and free-form markdown body. Memento adds `metadata.dependencies` in frontmatter (we handle deps differently). The three-level loading model is essentially what Claude Code does: metadata for routing, body on trigger, references on demand. [SOURCE: GitHub raw content, Memento-Skills/builtin/skills/web-search/SKILL.md and skill-creator/SKILL.md]

---

### 2. Skill Creation vs. Reuse Decision

The system uses a **behavior-aligned skill router** to decide between existing skills and new creation:

**Retrieval pipeline:**
1. Sparse recall via **BM25** over skill descriptions
2. Dense embedding retrieval via **Qwen3-Embedding-0.6B** (or similar)
3. **Reciprocal rank fusion** to combine sparse+dense scores
4. Optional **cross-encoder reranker** for final scoring

**When no skill matches:** If the router's confidence is below threshold, the system drafts a new skill. The skill-creator meta-skill handles this: it interviews the context, writes a SKILL.md draft, generates test prompts, runs evaluations, and iterates.

**Behavior-aligned training** (the key innovation): The router is NOT trained on semantic similarity. It's trained via **single-step offline RL** with a **multi-positive InfoNCE loss** optimized for *execution success*. Training data:
- Positive pairs: LLM-synthesized goals paired with skills that actually succeeded
- Hard negatives: Same domain/terminology but wrong skill (linguistically similar, behaviorally different)

The router is cast as a **KL-regularized Boltzmann policy** predicting behavioral utility, not textual relevance.

**Results:** Recall@1 jumps from 0.32 (BM25) to 0.60 (Memento-Qwen). Route hit rate: 0.29 -> 0.58. [SOURCE: arXiv:2603.18743, bemiagent.com analysis]

**What this means for us:** Our current system relies entirely on Claude Code's built-in metadata+description matching (semantic, not behavioral). We have no signal about which skills *actually succeed* when triggered. This is the single biggest gap. Adopting behavior-aligned routing would require: (a) logging skill trigger -> outcome pairs, (b) training a small embedding model on success signal. The hard-negative mining is particularly clever -- skills about "web search" vs "content fetching" may overlap semantically but diverge behaviorally.

---

### 3. Skill Evolution / Improvement Mechanism

The core loop is **Read-Write Reflective Learning**, formalized as policy iteration over external memory:

**Step 1 -- Observe:** Receive task, form augmented input.

**Step 2 -- Read (Retrieve):** Router selects most relevant skill from library. If no good match, route to skill-creator for new skill drafting.

**Step 3 -- Act (Execute):** Frozen LLM executes the multi-step workflow defined by the skill. Tools are called, code runs in a sandbox (uv-based isolation).

**Step 4 -- Feedback:** An LLM-based judge evaluates the outcome and provides diagnostic traces. This is not just pass/fail -- it produces structured attribution.

**Step 5 -- Write (Update):** Based on feedback:
- Update skill's **utility score** (running estimate of success rate)
- Record **"tip memory"** for failures (short failure notes attached to skill)
- If skill is weak: **in-place optimization** (rewrite prompt/code within the skill)
- If skill is missing entirely: **new skill discovery** via reflective rewriting
- All changes go through a **UnitTestGate** -- synthesized tests must pass before the update is accepted. On failure, **rollback** to previous version.

**Failure Attribution Framework** (the decomposition that makes targeted improvement possible):
- **Router failure:** Retrieved the wrong skill -- fix routing, not skill content
- **Skill weakness:** Correct skill was retrieved but contains inadequate instructions -- rewrite the skill
- **Execution failure:** Right skill, right instructions, but LLM couldn't follow -- model limitation, not fixable by skill editing
- **Coverage gap:** No relevant skill exists -- create a new one

This decomposition is critical: it prevents the system from churning on skill rewrites when the real problem is routing, or creating duplicate skills when the existing one just needs better instructions. [SOURCE: arXiv:2603.18743, emergentmind.com analysis, bemiagent.com analysis]

**What this means for us:** We have nothing comparable. When a skill underperforms, we notice manually (or don't). The failure attribution framework is directly adoptable as a mental model for `session-analyst`: when a skill triggers but the task fails, classify *why* before deciding whether to edit the skill, improve routing descriptions, or create a new skill. The UnitTestGate pattern (synthesized tests before committing skill changes) could be implemented via the existing eval infrastructure in skill-creator.

---

### 4. Skill Library Organization and Retrieval

**Library growth trajectory:**
- GAIA: 5 seed skills -> 41 skills after 3 learning rounds
- HLE: 5 seed skills -> 235 skills after training

**Organization:** Skills self-organize into semantic clusters. The paper reports clusters like Web/Search, Math/Chemistry, Physics, Code/Text -- "similar to a well-organized toolbox." This is an emergent property of the learning process, not imposed structure.

**Storage:** SQLite with `sqlite-vec` for vector storage + SQLAlchemy/aiosqlite for persistence. Cloud catalogue option available.

**Retrieval:** Hybrid pipeline:
1. BM25 sparse retrieval
2. Dense embedding retrieval (sqlite-vec)
3. Score-aware reciprocal rank fusion
4. Optional cross-encoder reranking

**What this means for us:** Our skill library is small (~20 skills) and symlink-organized by project. We don't need sophisticated retrieval yet. But the sqlite-vec pattern for embedding-based skill lookup is worth noting if the library grows past ~50 skills. The emergent clustering observation is interesting -- it suggests that with enough skills, natural taxonomy emerges without manual organization.

---

### 5. Quality Gating and Proliferation Prevention

**UnitTestGate:** Before accepting any skill modification:
1. LLM synthesizes test cases for the updated skill
2. Tests are run against the modified skill
3. If tests fail, the modification is rolled back
4. Only passing modifications are committed to the library

**Utility scores:** Each skill maintains a running success rate. Low-utility skills are candidates for rewriting or deprecation.

**Tip memory:** Failed attempts leave short notes ("tips") attached to the skill, providing context for future improvements without rewriting the entire skill.

**What the paper acknowledges is NOT solved:**
- Near-duplicate skills with minor variations (no deduplication protocol)
- Benchmark overfitting (skills tuned to test distribution)
- Local prompt hacks that don't generalize
- Retrieval collisions between similar skills
- Procedural bloat during library navigation

**Suggested governance (from analysis, not implemented in paper):**
- Skill deduplication protocols
- Deprecation policies with temporal decay
- Quality scores with temporal decay
- Lineage tracking for rewritten skills
- Rollback mechanisms for failed write-backs

[SOURCE: arXiv:2603.18743, bemiagent.com analysis]

**What this means for us:** The UnitTestGate is the most directly adoptable mechanism. Our `skill-creator` skill already has an eval framework (`evals/evals.json`), but it's optional and manual. Making it a *gate* -- skill changes don't persist unless evals pass -- is a concrete improvement. The utility score concept maps to tracking skill trigger -> success pairs, which we don't do. The acknowledged unsolved problems (deduplication, overfitting, prompt hacks) are important warnings: automated skill evolution without these safeguards produces crud.

---

### 6. Autonomous Agent Design -- How It Works Concretely

The "agent-designing agent" framing means: the system doesn't just use skills, it *designs new agents* (skill = agent blueprint) through experience.

**Theoretical foundation -- SRDP (Stateful Reflective Decision Process):**

The SRDP extends standard MDPs to include episodic memory:

```
D_SRDP = <S, A, P, R, gamma, M, p_LLM>
```

State is augmented: `x_t := (s_t, M_t)` where `M_t` is evolving skill memory. This recovers the Markov property by acknowledging that agent identity changes as memory evolves.

Policy formulation:
```
pi_mu(a | s, M_t) = sum_c mu(c | s, M_t) * p_LLM(a | s, c)
```
Where `mu` = skill router policy, `c` = chosen skill context, `p_LLM` = frozen model.

**Asymptotic value-gap bound:**
```
sup_s |V^pi*(s) - V^pi_M(s)| <= [2R_max/(1-gamma)^2] * eps_LLM(r_M) + delta_M
```

Three independent improvement levers:
1. **Model capability** (reduces eps_LLM): Upgrade base LLM
2. **Memory coverage** (reduces r_M): More episodes -> more skills
3. **Retrieval fidelity** (reduces delta_M): Better router/embeddings

This separation is theoretically useful: it tells you *where* to invest. If your model is already strong, improving retrieval gives more bang than adding skills.

**Convergence guarantee:** Theorem 1.3 establishes convergence under KL-regularized soft policy iteration. However: no convergence *rate* is proven, and guarantees don't address non-stationarity from write operations. [SOURCE: arXiv:2603.18743]

**In practice:** Concretely, the system starts with 5 atomic seed skills (filesystem, web-search, image-analysis, PDF, etc.), encounters tasks, routes to the best skill, executes, reflects on failure, and either improves the skill or creates a new one. Over 3 rounds on GAIA, it goes from 52.3% to 66.0%. The "agent design" happens during the Write phase: the system is literally writing new SKILL.md files that define how future agents will behave on similar tasks.

---

### Benchmark Results (Detailed)

**GAIA (General AI Assistants):**
| Configuration | Accuracy |
|---|---|
| Static baseline (5 skills, no learning) | 52.3% |
| After Round 1 | ~58% [ESTIMATED from trajectory] |
| After Round 2 | ~62% [ESTIMATED from trajectory] |
| After Round 3 (full system) | 66.0% |
| Improvement | +13.7pp absolute, +26.2% relative |

**HLE (Humanity's Last Exam):**
| Configuration | Accuracy |
|---|---|
| Static baseline | 17.9% |
| Round 0 | 30.8% |
| Round 1 | ~40% [ESTIMATED] |
| Round 2 | ~48% [ESTIMATED] |
| Round 3 | 54.5% (training) / 38.7% (test) |
| Domain peaks | Humanities 66.7%, Biology 60.7% |
| Improvement | +20.8pp absolute, +116.2% relative |

**Base model:** Gemini 3.1 Flash (not a frontier model -- cost-optimized choice)

**Note:** Results are self-reported, no independent replication. The train/test gap on HLE (54.5% train vs 38.7% test) suggests some overfitting to the training distribution, which the authors acknowledge as an open challenge.

---

### Comparison to Our System

| Dimension | Memento-Skills | Our System (skills/) | Gap | Adoptable? |
|---|---|---|---|---|
| **Skill format** | SKILL.md + scripts/ + references/ | SKILL.md + scripts/ + references/ | None | Already have |
| **Progressive loading** | 3-level (metadata, body, resources) | 3-level (Claude Code native) | None | Already have |
| **Skill creation** | Automated via reflective learning + manual via skill-creator | Manual via skill-creator skill | Large | Partially -- see below |
| **Skill retrieval** | Behavior-aligned router (BM25 + dense + fusion + reranker) | Claude Code metadata matching | Medium | Expensive to adopt |
| **Failure attribution** | 4-category decomposition (router/skill/execution/coverage) | None | Large | Directly adoptable as mental model |
| **Quality gating** | UnitTestGate (synthesized tests, rollback) | Optional manual evals | Medium | Adoptable via skill-creator evals |
| **Skill evolution** | Automated rewriting based on failure attribution | Manual editing | Large | High maintenance risk |
| **Utility tracking** | Running success rate per skill | None | Medium | Adoptable via session-analyst |
| **Tip memory** | Failure notes attached to skills | None | Small | Trivially adoptable |
| **Deduplication** | Acknowledged unsolved | N/A (small library) | N/A | Not needed yet |

---

### What to Adopt (Ranked by Value / Maintenance)

**1. Failure Attribution Mental Model (HIGH value, ZERO maintenance)**
When session-analyst detects a skill-related failure, classify it as: router failure (wrong skill triggered), skill weakness (right skill, bad instructions), execution failure (model limitation), or coverage gap (no skill exists). This changes the response from "rewrite the skill" to "fix the right thing." No code needed -- just a framework for diagnosis.

**2. Tip Memory on Skills (HIGH value, LOW maintenance)**
Add a `## Known Issues` or `## Tips` section to SKILL.md files that accumulates failure notes without rewriting the whole skill. When a skill fails in a pattern, append a tip like: "When dealing with PDFs over 50 pages, split first -- single-pass extraction misses content after page 30." This is incremental knowledge that prevents repeat failures. Session-analyst can suggest tips.

**3. Skill Trigger -> Outcome Logging (MEDIUM value, LOW maintenance)**
Log when a skill triggers and whether the task succeeded. Over time, this produces the utility scores that Memento tracks. Could be as simple as a SQLite table: `(skill_name, timestamp, session_id, outcome)`. This is prerequisite data for behavior-aligned routing if we ever want it.

**4. UnitTestGate for Skill Modifications (MEDIUM value, MEDIUM maintenance)**
Before committing a skill change, require that `evals/evals.json` passes. The skill-creator skill already has eval infrastructure -- the gap is making it mandatory rather than optional. Risk: eval authoring overhead may discourage skill improvements.

**5. Automated Skill Rewriting (LOW value for now, HIGH maintenance risk)**
The full Read-Write reflective loop is the crown jewel of Memento-Skills, but it requires: (a) an LLM judge for evaluation, (b) failure attribution, (c) automated rewriting, (d) unit test gating, (e) rollback mechanism. Each component has failure modes. At our library size (~20 skills), manual curation still outperforms automated evolution. Revisit when library exceeds ~50 skills and manual attention becomes the bottleneck.

**6. Behavior-Aligned Router Training (LOW value for now, HIGH maintenance)**
Training a custom embedding model on skill success signals requires substantial infrastructure (training data collection, model training, serving). Claude Code's native matching is good enough for ~20 skills. Revisit when retrieval precision becomes a measurable bottleneck.

---

### What NOT to Adopt

- **Automated skill creation without human review.** Memento's library grows to 235 skills on HLE -- but it's benchmark-optimized. In a production system where skills affect real workflows, unchecked proliferation creates maintenance debt. The paper itself acknowledges deduplication and overfitting as unsolved.

- **The SRDP formalism as implementation guide.** The theoretical framework is elegant but doesn't constrain implementation. The policy iteration interpretation doesn't change what you'd build -- it justifies what they built post-hoc.

- **Reciprocal rank fusion retrieval.** Overkill for <50 skills. BM25 alone or Claude Code's native matching suffices.

---

### What's Uncertain

1. **Generalization beyond benchmarks.** GAIA and HLE are fixed benchmarks with known answer distributions. Does skill evolution generalize to open-ended tasks where the answer space isn't bounded? The train/test gap on HLE (54.5% vs 38.7%) suggests partial overfitting.

2. **Long-term library health.** The paper evaluates over 3 training rounds. What happens after 30? Do skills accumulate crud? Does the router degrade with hundreds of overlapping skills? No long-term deployment data.

3. **Model dependence.** Results are with Gemini 3.1 Flash. Would a stronger model (Opus, GPT-5) reduce the value of skill evolution by solving tasks without skill assistance? The asymptotic bound suggests yes -- as eps_LLM decreases, the memory term matters less.

4. **Skill transferability.** Can skills evolved for one base model transfer to another? The paper doesn't address cross-model skill portability.

---

### Related Work Worth Tracking

- **AutoRefine** (arXiv:2601.22758): Extracts reusable expertise from trajectories as structured "refinement operators" rather than flat text. Maintenance mechanisms included.
- **MemSkill** (arXiv:2602.02474): Self-evolving memory operations (what to store, how to revise). 3 citations in 2 months -- getting traction.
- **ELL Framework** (arXiv:2508.19005): Experience-driven Lifelong Learning benchmark for self-evolving agents. 10 citations.
- **Memento (v1)** (predecessor): Same team, 2.4K stars, MIT license. "Fine-tuning LLM agents without fine-tuning LLMs." The foundation Memento-Skills builds on.

---

### Search Log

| Tool | Query | Result |
|---|---|---|
| search_papers (S2) | "Memento-Skills agents design agents reusable skills external memory" | Found paper + 9 related. Paper ID: 2859af8b7e04397e65e78bf77ad7651e02a8726a |
| web_search_exa | "Memento-Skills Let Agents Design Agents paper" | arXiv, HuggingFace, project website, blog analysis, YouTube |
| search_literature (scite) | "Memento-Skills agents design agents" | No results (too recent for scite index) |
| WebFetch | skills.memento.run | Project website -- overview, limited technical detail |
| WebFetch | bemiagent.com analysis | Detailed technical breakdown including SRDP, failure attribution, benchmark numbers |
| fetch_paper | arXiv:2603.18743 PDF | Full text: 51K chars, 12.7K tokens |
| ask_papers (RCS) | Skill format, SRDP, routing, benchmarks | RCS found no relevant chunks (PDF parsing issue), CAG mode succeeded |
| WebFetch | GitHub repo (main, builtin/skills, core) | Repo structure, 9 builtin skills, core modules |
| curl (raw GitHub) | web-search/SKILL.md | Full SKILL.md with YAML frontmatter + markdown |
| curl (raw GitHub) | skill-creator/SKILL.md | Full meta-skill for skill creation workflow |
| WebFetch | emergentmind.com analysis | Additional technical details on routing, gating |

---

### References

1. Zhou, H., Guo, S., Liu, A., et al. (2026). Memento-Skills: Let Agents Design Agents. arXiv:2603.18743. https://arxiv.org/abs/2603.18743
2. GitHub: Memento-Teams/Memento-Skills. https://github.com/Memento-Teams/Memento-Skills
3. Project website: https://skills.memento.run/
4. Qiu, L., et al. (2026). AutoRefine: From Trajectories to Reusable Expertise. arXiv:2601.22758.
5. Zhang, H., et al. (2026). MemSkill: Learning and Evolving Memory Skills. arXiv:2602.02474.

<!-- knowledge-index
generated: 2026-03-27T04:48:21Z
hash: 08ca5132718e

sources: 2
  ESTIMATED: from trajectory
  ESTIMATED: from trajectory
table_claims: 7

end-knowledge-index -->
