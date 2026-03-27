---
title: "alphaXiv Trending Papers — What We Can Leverage"
date: 2026-03-27
tags: [research-sweep, skills, autoresearch, self-improvement, skill-routing]
status: active
---

# alphaXiv Trending Papers — What We Can Leverage (2026-03-27)

**Source:** alphaXiv weekly digest (March 25, 2026) + full trending page scrape
**Papers scanned:** 20 trending papers
**Relevant to our stack:** 9 papers (agent infrastructure, self-improvement, skills)
**Skipped:** 11 papers (vision/robotics/video/generative modeling theory)
**Deep dives completed:** 6 of 6 (MetaClaw, Claudini, Memento-Skills, SkillRouter, HyperAgents, AVO)

---

## Consolidated Findings — Ranked by Leverage

### 1. Skill Bodies Are the Signal, Not Descriptions (SkillRouter)

**Paper:** SkillRouter (arXiv:2603.22455, Alibaba)

Skill descriptions receive **1% of cross-encoder attention**. The body gets **91.7%**. Removing bodies causes 29-44pp accuracy drops. BM25 on name+description alone = literally 0% accuracy.

**What this means for us:** Our progressive disclosure model (Claude Code sees only name + description for skill selection) is leaving the most informative signal on the table. At ~50 skills this hasn't been critical, but it's the first thing that will break as we grow.

**Adopt now:**
- Inject ~200 tokens of each skill body into the selection context (~10K tokens total at 50 skills — fits easily)
- Extend "NOT for: X, use Y" negative routing patterns to ALL skills with functional neighbors (currently only on `researcher`, `investigate`, a few others)
- Build synthetic skill selection eval: 50-100 queries per skill (no skill name in query), test Claude Code's selection accuracy. ~$0.50 total. Baseline before optimizing.

**Adopt at 200+ skills:** Retrieve-and-rerank pipeline (0.6B bi-encoder + 0.6B cross-encoder with listwise loss)

### 2. Failure Attribution Taxonomy (Memento-Skills)

**Paper:** Memento-Skills (arXiv:2603.18743, UCL/HKUST)

When a skill fails, classify **why**: (a) wrong skill triggered (router problem), (b) skill has bad instructions (skill weakness), (c) model couldn't execute (execution failure), (d) no skill exists (coverage gap). This changes "rewrite the skill" into "fix the right thing."

**What this means for us:** We treat skill failures as monolithic — session-analyst flags them but doesn't distinguish root cause. The taxonomy is free to adopt and makes skill maintenance targeted.

**Adopt now:**
- Add failure attribution categories to session-analyst's skill failure detection
- Add `## Known Issues` (tip memory) sections to SKILL.md files — accumulate failure notes without full rewrites
- Log `(skill_name, timestamp, session_id, outcome)` to SQLite — prerequisite for data-driven routing later

### 3. Reward Hacking Detection for Autoresearch (Claudini)

**Paper:** Claudini (arXiv:2603.24511)

Their autoresearch pipeline caught an agent gaming suffix lengths and seed-searching around iteration 95. Our `autoresearch.py` has no equivalent detection mechanism — we'd miss an agent gaming the eval function.

**What this means for us:** We already have better infrastructure than Claudini (explicit orchestrator, LEARNINGS.md, worktree isolation, multi-engine, cost controls, telemetry), but lack three things they expose:
1. **Reward hacking detection** — monitor for metrics improving via eval gaming rather than genuine improvement (e.g., metric variance suddenly dropping, trivial changes producing large gains, pattern repetition)
2. **Generalization probing** — our holdout exists but isn't distribution-shifted. Claudini used model rotation (Qwen → Llama-2 → Gemma) as forced generalization
3. **Baseline seeding** — for domains with published approaches, starting from multiple known-good baselines accelerates search vs cold start

Also confirms: LLMs are recombination engines, not inventors. "Primarily recombined ideas from existing methods — no fundamental algorithmic novelty." Matches our experience.

### 4. Generation Stamping for Rules/Skills (MetaClaw)

**Paper:** MetaClaw (arXiv:2603.17187, UNC/CMU/UCSC/Berkeley)

Every trajectory is stamped with its skill version (generation g). When skills evolve (g → g+1), all pre-evolution samples are flushed from the RL buffer. Prevents stale reward contamination.

**What this means for us:** We don't track which sessions ran under which skill/rule versions. When session-analyst or fix-verify.py evaluates whether a fix worked, it compares sessions that may have run under different rules. Generation stamping makes before/after comparisons valid.

**Adopt now:**
- Stamp session receipts with a hash of active skills + rules at session start
- `fix-verify.py` should filter by generation when evaluating fix effectiveness — only compare sessions running under the same rule set

**Also interesting but not transferable:** Their dual-timescale insight (fast skill fixes vs slow policy optimization) maps conceptually to our skill updates vs CLAUDE.md governance changes, but the mechanism (cloud LoRA fine-tuning + GRPO) requires model weight access we don't have.

### 5. HyperAgents — Meta-Level Self-Improvement (pending)

**Paper:** HyperAgents (arXiv:2603.19461, UBC/Meta)

*Deep dive in progress — will update when agent completes.*

Preliminary: Framework for AI systems to autonomously modify their own self-improvement mechanisms. Maps directly to our session-analyst → improvement-log → rules/hooks loop. Key question: do they have guardrails/structures for meta-level modification that we're missing?

### 6. AVO — Agentic Variation Operators (pending)

**Paper:** AVO (arXiv:2603.24517)

*Deep dive in progress — will update when agent completes.*

Preliminary: LLMs as autonomous evolutionary search operators, discovering attention kernels outperforming cuDNN and FlashAttention. Directly comparable to our `autoresearch.py` mutation/fitness approach. Key question: variation operator design differences.

---

## Other Relevant Papers (Not Deep-Dived)

| Paper | Why relevant | Quick take |
|-------|-------------|------------|
| **UI-Voyager** (2603.24533) | GUI agent learning from failures, 81% success (> human 80%) | Failure-driven learning loop similar to session-analyst. Their "failed experience" database is the pattern to watch. |
| **Y-Combinator for LLMs** (2603.20105) | Long-context rot via λ-calculus | Relevant to compaction — may have techniques for preserving information across context boundaries. Worth reading if compaction issues resurface. |
| **Self-Distillation Degrades Reasoning** (2603.24472) | "Epistemic verbalization" suppression | Self-distillation shortens reasoning but suppresses uncertainty expressions critical for generalization. Relevant to understanding model behavior differences across versions. |

## Skipped Papers (Not Relevant)

UNITE (2603.22283), CanViT (2603.22570), TAG (2603.24584), WAMs vs VLAs (2603.22078), WildWorld (2603.23497), Latent-WAM (2603.24581), GameplayQA (2603.24329), Relax Forcing (2603.21366), daVinci-MagiHuman (2603.21986), GLD (2603.22275), ThinkJEPA (2603.22281), EUPE (2603.22387), UniGRPO (2603.23500), Schrödinger Bridges (2603.18992), Attention Residuals (Kimi), Omni-WorldBench (2603.22212)

All vision/robotics/video/generative modeling. No agent infrastructure application.

---

## Implementation Priority

| # | Action | Source | Effort | Maintenance |
|---|--------|--------|--------|-------------|
| 1 | Failure attribution taxonomy in session-analyst | Memento-Skills | Low | None (classification only) |
| 2 | `## Known Issues` sections in SKILL.md files | Memento-Skills | Low | Low (append-only) |
| 3 | Negative routing on all skills with functional neighbors | SkillRouter | Low | Low |
| 4 | Generation stamping in session receipts | MetaClaw | Medium | Low |
| 5 | Skill trigger-outcome logging to SQLite | Memento-Skills | Medium | Low |
| 6 | Synthetic skill selection eval (~$0.50) | SkillRouter | Medium | None (one-shot baseline) |
| 7 | Reward hacking detection in autoresearch | Claudini | Medium | Low |
| 8 | Body injection in skill selection context | SkillRouter | Medium | Low |
| 9 | Distribution-shifted holdout in autoresearch | Claudini | Medium | Medium |
| 10 | Baseline seeding for autoresearch domains | Claudini | Low | None (per-experiment) |

---

## Detailed Memos

- `research/scratch/metaclaw-dive.md` — Full MetaClaw analysis
- `research/scratch/claudini-dive.md` — Full Claudini analysis
- `research/scratch/memento-skills-dive.md` — Full Memento-Skills analysis
- `research/scratch/skillrouter-dive.md` — Full SkillRouter analysis
- `research/scratch/hyperagents-dive.md` — (pending)
- `research/scratch/avo-dive.md` — (pending)

<!-- knowledge-index
generated: 2026-03-27T13:24:28Z
hash: 96f7864bb360

title: alphaXiv Trending Papers — What We Can Leverage
status: active
tags: research-sweep, skills, autoresearch, self-improvement, skill-routing
cross_refs: research/scratch/avo-dive.md, research/scratch/claudini-dive.md, research/scratch/hyperagents-dive.md, research/scratch/memento-skills-dive.md, research/scratch/metaclaw-dive.md, research/scratch/skillrouter-dive.md

end-knowledge-index -->
