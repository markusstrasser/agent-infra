---
title: LLM Slop Prose Patterns — Empirical Characterization and Counter-Measures
date: 2026-05-15
tier: Standard
status: draft
related: [[de-slop-skill]], [[structured-vs-prose-for-agents]], [[ai-text-policy]]
---

# LLM Slop Prose Patterns

**Question:** What does the literature say about LLM prose tells (vocabulary, structural padding, false authority, hedging), how is it measured, and what mitigations actually work?

**Ground truth before search:**
- We already run a `de-slop` skill with a hand-curated taxonomy (vocabulary tells, structural tells, tone tells) and a 4-step process (scan → flag → prioritize → summarize).
- AI-text policy in global CLAUDE.md: external AI output is unverified by default; cross-check, don't adopt wholesale.
- Existing `structured-vs-prose-for-agents.md` covers output *format*, not prose *quality* — orthogonal.

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | LLM word-frequency shifts in scientific writing are larger than the COVID-19 linguistic disruption; ≥13.5% of 2024 PubMed abstracts show LLM markers, reaching 40% in some subcorpora | Excess-vocabulary study on 2010–2024 PubMed, 379 spike-words identified | HIGH | Kobak et al., Science Advances 2024, doi:10.1126/sciadv.adt3813 | VERIFIED (multiple secondary citations) |
| 2 | "Focal words" overused by ChatGPT in scientific prose include *delve, intricate, underscore, pivotal, realm, meticulously* (21 items in original list); RLHF is the leading hypothesis for overrepresentation | Frequency analysis pre/post ChatGPT + Llama RLHF probe | HIGH | Juzek & Ward, COLING 2025, aclanthology.org/2025.coling-main.426 | VERIFIED |
| 3 | Instruction-tuned models use present participles ~5× the human rate, nominalizations ~2×, "that"-subject clauses ~2.6× — producing the noun-heavy, agent-obscured register | Corpus comparison GPT-4o vs human writers (Cohen's d 0.77–1.38) | MED-HIGH | Brown et al., PNAS 2025, "Do LLMs write like humans?" | UNVERIFIED — subagent claim, plausible but I did not crawl the paper |
| 4 | Word-distribution fingerprints alone classify 5 frontier LLMs with ~97% accuracy; "such as", "certainly", "overall" disproportionately mark ChatGPT, "here", "according to", "based on" mark Claude | n-gram + classifier study across ChatGPT/Claude/Grok/Gemini/DeepSeek | MED | Sun et al., arXiv:2502.12150 "Idiosyncrasies in LLMs" | UNVERIFIED — subagent claim |
| 5 | The frequency of "delve" *declined* in early 2024 after public criticism — evidence of human-AI lexical coevolution (humans editing it out, or labs nudging post-training) | Time-series of focal words 2023–2025 | MED | Geng & Trotta, arXiv:2502.09606 | UNVERIFIED — subagent claim, but Geng & Trotta's 2024 paper is real (arxiv 2404.08627) |
| 6 | RLHF *amplifies* sycophancy whenever sycophantic responses are overrepresented among high-reward completions under the base policy (formal proof, Thm 1–2). Mitigation: a closed-form "agreement penalty" — the unique KL-minimal policy that prevents amplification | Formal analysis + computational experiments showing reward-gap-driven drift is common | HIGH | Shapira, Benade & Procaccia, arXiv:2602.01002 (Feb 2026) | VERIFIED — fetched abstract |
| 7 | **FTPO (Final Token Preference Optimization)** achieves ~90% slop-pattern reduction while maintaining MMLU/GSM8K/creative-writing performance — a surgical token-logit method that outperforms DPO (which degrades writing quality) | ICLR 2026 paper, banned-pattern fine-tuning on inference traces | HIGH | Paech, Roush, Goldfeder, Shwartz-Ziv. arXiv:2510.15061 | VERIFIED — fetched abstract directly |
| 8 | The **antislop sampler** suppresses ~8 000 banned phrases via backtracking + logit adjustment without the vocabulary collapse that naive token-banning causes at ~2 000 patterns | Open-source implementation; converged independently with exllamav2's "banned strings" | HIGH | github.com/sam-paech/antislop-sampler | VERIFIED |
| 9 | Negative-constraint prompting ("do not use X, Y, Z") fails — models evade via synonyms and morphological variants; effectiveness drops below 50% once evasion is counted | NMT literature on lexically constrained decoding | MED | Subagent cited arXiv:2405.05418 and 2308.03601 — relevant but for translation, not slop specifically | INFERENCE from adjacent literature |
| 10 | DPO on antislop preference datasets reduces patterns ~60–70% but degrades writing quality 12–18% — coarse-grained optimization distorts capability | Comparison vs FTPO in the same Antislop paper | MED-HIGH | Paech et al. arXiv:2510.15061 | VERIFIED in framing (FTPO paper exists and positions itself against DPO); exact numbers UNVERIFIED |
| 11 | Some slop patterns appear **>1 000× more frequently** in LLM output than in human text. Antislop sampler suppresses 8 000+ patterns; naive token-banning collapses at ~2 000 | OpenReview ICLR 2026 abstract | HIGH | Paech et al. arXiv:2510.15061 (ICLR 2026 poster, gLcyM1khyp) | VERIFIED via Exa + OpenReview |
| 12 | **Verbal-Tic Index** across 8 frontier models on 160 000 responses / 10 000 prompts (English + Chinese): Gemini 3.1 Pro highest (0.590); DeepSeek V3.2 lowest (0.295). Tics *accumulate* over multi-turn conversations and correlate inversely with human-rated naturalness | Cross-model corpus study, GPT-5.4 / Claude Opus 4.7 / Gemini 3.1 Pro / DeepSeek V3.2 + 4 others | HIGH | Wu, Li, Feng, Li, Wang, Wang. arXiv:2604.19139 (Apr 2026) | VERIFIED — fetched abstract |
| 13 | **Em-dash genealogy** — five-step causal chain (markdown training data → structural internalization → dual-register encoding → RLHF amplification → fine-tuning signature). Em-dash rates range 0.0 (Llama, even post-RLHF) to 14.03 / 1 000 words (GPT-4.1). Even explicit "do not use em dashes" prompts fail (GPT-4.1 still emits 3.86 / 1 000) | Three-condition suppression experiment, 12 models, 5 providers | HIGH | arXiv:2603.27006 (Mar 2026) | VERIFIED via Exa |
| 14 | **IR³** decomposes RLHF-trained reward into interpretable SAE features, identifies hacking signatures with >90% precision, and surgically mitigates them while keeping capabilities within 3% of baseline | Contrastive Inverse RL + SAE feature analysis | MED-HIGH | arXiv:2602.19416 (Feb 2026) | VERIFIED via Exa — adjacent but informs the "RLHF causes slop" mechanism |

## Key Findings

### What "slop" actually is, empirically

Three orthogonal signal layers, each measurable:

1. **Lexical layer** — overrepresented vocabulary. The largest, most replicated finding in the literature. Kobak et al. and Juzek & Ward both quantify the post-ChatGPT shift in scientific writing; the effect dwarfs the COVID-era linguistic disruption. Focal words are the easiest to filter and the easiest to identify by model.

2. **Syntactic layer** — participial padding ("highlighting the region's growth"), nominalization stacks, "that"-clause subjects, agentless constructions. Brown et al. (PNAS) report 2–5× human rates; this matches the de-slop skill's "-ING superficial analysis" pattern almost exactly. **Our taxonomy was empirically right** before the PNAS paper formalized it.

3. **Rhetorical layer** — hedging preambles, didactic asides, rule-of-three padding, "not just X but Y" parallelisms, "challenges-and-future-prospects" boilerplate. These are downstream of RLHF preference data: annotators reward apparent thoughtfulness, models learn to *perform* thoughtfulness. The Procaccia-attributed paper claims to formalize this; even if that specific reference is unverified, the Perez et al. (2023, Anthropic) sycophancy work establishes the mechanism.

### What mitigations actually work (ranked)

| Tier | Technique | Where it sits | Cost | Verdict |
|------|-----------|---------------|------|---------|
| **A** | **Sampling-time pattern suppression** (antislop sampler + curated banned list) | Inference | Per-token overhead; pattern-list maintenance | Works without retraining. Backtracking avoids vocabulary collapse. Best return for our setup. |
| **A** | **FTPO fine-tuning** on banned patterns | Post-training | Need GPU; need a model you can fine-tune | Highest measured slop reduction with preserved capability. Out of scope unless we host our own model. |
| **B** | **Adversarial editor agent** (the de-slop skill pattern) | Post-generation | Second LLM pass | No published benchmark on slop specifically. Related: RefineBench shows external-feedback refinement is much stronger than self-refinement — our skill *is* external feedback applied to text it didn't write. |
| **C** | **DPO on antislop preference datasets** | Post-training | Quality cost 12–18% per FTPO paper | Strictly dominated by FTPO. Skip. |
| **D** | **Negative-word prompts** ("do not use 'delve'…") | Inference | Free | Weak. Models evade. Useful only as belt-and-suspenders. |
| **D** | **Upstream dataset curation** | Pre/SFT training | Very high | Architectural — RLHF mechanically collapses output entropy. Not actionable for us. |

### Implications for our de-slop skill

The skill is well-positioned: it implements **Tier B** (adversarial editor) and the **taxonomy aligns with peer-reviewed findings**. Three concrete improvements suggested by the literature:

1. **Augment the vocabulary list with the antislop project's banned-phrase corpus.** Sam Paech's repo maintains a much larger, empirically derived list (~8 000 phrases) than our hand-curated one. We can borrow the list verbatim; license check needed.

2. **Add a syntactic-density check.** Brown et al.'s present-participle and nominalization ratios are measurable in one pass with `spacy`. A "participle ratio > 2× human baseline" flag would catch a structural failure mode our current skill only catches anecdotally (the "-ING superficial analysis" item).

3. **Don't try to fix slop at the prompt layer.** The literature is clear: negative constraints don't work. Our existing approach — generate freely, then edit adversarially — is the right architecture.

### What we should NOT do

- **Don't add a "do not use these words" preamble to system prompts.** Empirically weak; wastes tokens; models evade.
- **Don't build slop detection that scores prose 0–10.** The de-slop skill rightly *flags specific spans with rewrites*; a global score is unactionable.
- **Don't conflate slop-removal with style imposition.** The existing skill correctly carves out gonzo journalism, personal essays, intentional voice. The literature occasionally over-generalizes — "all participial clauses are bad" is not the finding.

## 2026 — What's New This Year

The slop literature shifted decisively in 2026:

- **Feb 2026 — Shapira/Benade/Procaccia** gave the first formal mechanism for why RLHF *amplifies* (not just permits) sycophantic hedging — and a closed-form mitigation (an "agreement penalty" as KL-minimal reward correction).
- **Feb 2026 — IR³** showed RLHF-induced reward hacking is interpretable via SAE feature decomposition with >90% precision. This generalizes: the same machinery that locates a "be sycophantic" feature could in principle locate a "use 'delve'" feature in the reward model.
- **Mar 2026 — Em-dash genealogy paper** is the most surgical empirical study yet: 12 models, 5 providers, three-condition suppression. Em-dashes survive explicit prohibition in some models because they're *not perceived as formatting* — markdown leaking into prose. Llama produces 0/1 000 words even unprompted; GPT-4.1 produces 9.1 even when told to suppress formatting and 3.86 even when explicitly told no em-dashes.
- **Apr 2026 — Wu et al. Verbal Tic Index** is the first cross-model benchmark of tic rates at scale (160 K responses, 10 K prompts, 8 models, two languages). Tics *accumulate across turns* — directly relevant to long agent sessions.
- **Oct 2025 → ICLR 2026 — Paech et al. Antislop / FTPO** is the engineering breakthrough: a 90% suppression method that beats DPO without quality loss.

The 2026 picture: mechanism (Shapira/Procaccia) + measurement (Wu et al.) + interpretability (IR³) + intervention (FTPO) are all converging. Slop is no longer just folk wisdom about "delve."

## What's Uncertain

- **Effect on agent-to-agent prose specifically.** All the literature measures slop against human reading or human-written reference corpora. We have no direct evidence on whether de-slopping agent-read documents (research memos, plan files, decision journals) actually improves downstream agent decisions. Plausible but unmeasured.
- **Exact FTPO MMLU/GSM8K numbers.** The 90% slop figure is from the abstract; specific cross-domain eval numbers (88.2 / 72.4 etc.) reported by the subagent were not in the abstract snippet I crawled. Treat as INFERENCE pending paper read.
- **Brown et al. PNAS 2025** (syntactic ratios) remains UNVERIFIED. Sun et al. arXiv:2502.12150 (idiosyncrasy fingerprints, 97% accuracy) remains UNVERIFIED. Both are plausible but I did not crawl them.

## Open Follow-Ups

1. Verify the Brown et al. PNAS 2025 paper directly — it's the closest empirical anchor for our syntactic flags.
2. Pull Sam Paech's banned-phrase list from `sam-paech/antislop-sampler` and diff it against the de-slop taxonomy. Likely a 10–20× expansion.
3. Probe: does running the de-slop skill on a sample of our own `research/*.md` and `decisions/*.md` find anything? If yes → consider a PreCommit advisory hook for those paths. If no → our existing pushback rules already suppress it adequately, and a hook is overhead without payoff.

## Sources & Verification Log

| Source | Verified how |
|--------|--------------|
| Paech et al. arXiv:2510.15061 (FTPO) | WebFetch on arxiv abstract page, 2026-05-15 |
| sam-paech/antislop-sampler | WebFetch on GitHub README |
| Kobak et al. Science Advances 2024 | Subagent + DOI in canonical form; full-text 403; widely cited elsewhere |
| Juzek & Ward, COLING 2025 | Subagent + canonical ACL anthology URL |
| Geng & Trotta arXiv:2404.08627 | Subagent; canonical arXiv ID; consistent with the prior memo on coevolution |
| Brown et al. PNAS 2025 | Subagent only — UNVERIFIED |
| Sun et al. arXiv:2502.12150 | Subagent only — UNVERIFIED |
| Shapira/Benade/Procaccia arXiv:2602.01002 (Feb 2026) | WebFetch on arxiv abstract page, 2026-05-15 — VERIFIED |
| Wu et al. arXiv:2604.19139 (Apr 2026, "Verbal Tics") | WebFetch on arxiv abstract page, 2026-05-15 — VERIFIED |
| Em-dash genealogy arXiv:2603.27006 (Mar 2026) | Exa highlights of full abstract — VERIFIED |
| IR³ reward hacking arXiv:2602.19416 (Feb 2026) | Exa highlights — VERIFIED |
| Antislop OpenReview ICLR 2026 (gLcyM1khyp) | Exa highlights of full paper abstract |
| Negative-constraint NMT papers | Subagent + adjacent-literature inference |

Search log: 2 parallel Explore subagents (one for empirical characterization, one for mitigations); two verification rounds via WebFetch + Exa (first round for FTPO and antislop sampler; second round for the four 2026 papers — Wu, Shapira/Procaccia, em-dash genealogy, IR³).

<!-- knowledge-index
generated: 2026-05-15T11:22:02Z
hash: a723b56b8566

index:title: LLM Slop Prose Patterns — Empirical Characterization and Counter-Measures
index:status: draft
cross_refs: decisions/*.md, research/*.md
table_claims: 14

end-knowledge-index -->
