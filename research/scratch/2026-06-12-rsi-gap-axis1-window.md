# RSI Gap Sweep — Axis 1: New work window 2026-05-27 → 2026-06-12

Date anchor: 2026-06-12. Axis 1 of a 4-axis gap sweep on LLM agents + recursive self-improvement (RSI).
Method: Exa (research-paper category, date ≥2026-05-27) → vendor/news targeted → disconfirmation query. All
load-bearing arXiv IDs HTTP-verified at arxiv.org/abs/<id> (200). OpenReview = ACL ARR May 2026 submissions
(under review, anonymous — treat as [PREPRINT], lower confidence on numbers).

## Provenance legend
[SOURCE] primary doc read · [PREPRINT] arXiv/OpenReview abstract only · [VENDOR] official blog/release ·
[NEWS] secondary press · [UNVERIFIED] snippet metadata only.

---

## Claims table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | **Self-Harness**: LLM agent improves its OWN harness via Weakness-Mining → Harness-Proposal → regression-gated Proposal-Validation; held-out Terminal-Bench-2.0 pass rates 40.5→61.9%, 23.8→38.1%, 42.9→57.1% across MiniMax-M2.5 / Qwen3.5 / GLM-5. | Abstract read; arXiv resolves | High (claim) / Med (numbers, no peer review) | arXiv:2606.09498 [PREPRINT][SOURCE-abstract] | NEW — closest sibling to Harness-1; delta = self-edits, regression gate |
| 2 | **PACE** (Paired Anytime-valid Commit Evaluation): reframes the *acceptor* in self-evolving loops as a sequential hypothesis test; greedy "keep if score up" = uncontrolled adaptive multiple testing → 30–42% false / 10–33% harmful commits; e-process testing-by-betting gate controls false-commit prob under optional stopping. Qwen2.5 0.5B–3B, prompt-level, GSM8K/SVAMP/ARC. | Abstract read | High | arXiv:2606.08106 [PREPRINT][SOURCE-abstract] | NEW — **most load-bearing RSI-safety result in window**; directly relevant to our PACE-like commit gates |
| 3 | **SIA: Self-Improving AI with Harness & Weight Updates** — agent updates both its harness AND model weights in a self-improvement loop. | Title + date (v2 2026-05-28); arXiv resolves | Med (abstract not read) | arXiv:2605.27276 [PREPRINT] | NEW — read before citing; weight-update axis distinguishes from Self-Harness |
| 4 | **Tail Knowledge Collapse** (TailSkills bench): recursive rewriting of skill artifacts into shorter/standardized variants preserves common-case utility while *degrading rare exception handling*; 208 oracle-verified exception tasks, 14 variant types. | Abstract read | High | OpenReview AWhmMWfEG6 [PREPRINT][SOURCE-abstract] | NEW — **critique/failure-mode**; directly bears on our skill-distillation & "store less reuse more" instincts |
| 5 | **Fluent Reflection, No Correction**: 8 frontier LLMs on open-ended rule-constrained generation; reflection gives only +0.216 pass rate and second-pass outputs frequently *repeat near-identical prior rule violations*. Argues closed-ended tasks overestimate self-correction. | Abstract read | High | OpenReview mNWz2QgJtU [PREPRINT][SOURCE-abstract] | NEW — **disconfirmation**; frontier-tested (in scope per timeliness rule) |
| 6 | **More Yap Less Meaning**: SLM self-correction sufficiency test — even when handed the ground-truth answer, SLMs gain only 4.4% and fail to identify what their reasoning missed. | Abstract read | High | arXiv:2606.08471 [PREPRINT][SOURCE-abstract] | NEW — critique, SLM-scoped (NOT frontier — limited transfer) |
| 7 | **AEL** (Agent Evolving Learning): two-timescale — fast Thompson-sampling bandit over memory-retrieval policies + slow "diagnose-before-prescribe" LLM reflection injecting new retrieval policies as bandit arms; +27% Sharpe (portfolio), +18%/+51% (ticket routing). Provably no-harm when best policy is stable. | Abstract read | Med | OpenReview dtPo105y8x [PREPRINT][SOURCE-abstract] | NEW — memory-policy-as-online-learning framing |
| 8 | **BES** (Bidirectional Evolutionary Search): self-improving search couples forward trajectory-recombination evolution with backward recursive sub-goal decomposition for dense feedback; Harvard/MIT (Kakade, Du, Lakkaraju). | Abstract read | Med | arXiv:2605.28814 [PREPRINT][SOURCE-abstract] | NEW — strong author pedigree; search-not-loop angle |
| 9 | **Meta-Agent Challenge**: benchmark asking whether current agents can autonomously *develop* agents. | Title + date; arXiv resolves | Low (abstract not read) | arXiv:2606.04455 [PREPRINT] | NEW — adjacent to AutoAgent meta-agent line (read before claiming delta) |
| 10 | **VASO**: formally-verifiable self-evolving skills for physical AI agents. | Title; arXiv resolves | Low | arXiv:2606.05395 [PREPRINT] | NEW — verification + self-evolution intersect (physical/robotics, weaker transfer to code agents) |
| 11 | **Anthropic Institute "When AI builds itself"** paper: Claude authors >80% of merged production code (from low single-digits Feb-2025); Q2-2026 engineer merges ~8× more code/day vs 2024; maps path to RSI and calls for a *verifiable global pause mechanism*. | Multiple press; Anthropic blog "When AI Builds Itself" | High (existence) / Med (internal metrics self-reported) | thenextweb.com + aimagazine.com [NEWS], anthropic blog [VENDOR] | NEW — **flagship vendor RSI-thesis artifact in window**; FOLLOW-UP/echo of our verification-bounded-RSI corpus, NOT a repeat — quantifies the coding-loop closure + safety ask |
| 12 | **Claude Managed Agents — "Dreaming"** (Research Preview, Code with Claude 2026): async between-session job consolidates memory store + ≤100 session transcripts → reorganized store (merge dups, drop stale, surface cross-session patterns); input never mutated. Harvey reported ~6× completion-rate jump. Also shipped: Outcomes (rubric self-eval loop), Multi-Agent Orchestration (≤20 parallel specialists). | claude.com blog + 3 secondary | High | claude.com/blog/building-with-claude-managed-agents [VENDOR] | NEW — **vendor productization of self-improving memory** (agents editing own memory between sessions) |
| 13 | **OpenAI "Dreaming"** (2026-06-04): ChatGPT memory-synthesis system targeting staleness/correctness/scalability over multi-year horizons; Plus/Pro US first. | openai.com/index/chatgpt-memory-dreaming | High | openai.com [VENDOR] | NEW — parallel vendor convergence on async memory consolidation (note: consumer memory, not agent-scaffold RSI) |
| 14 | **Google OpenRL**: self-hosted post-training API for fine-tuning LLMs (2026-06-11); Gemma 4 12B (2026-06-03). | opensource.googleblog.com + blog.google | Med | google blogs [VENDOR] | ADJACENT — RL infra enabling self-improvement loops, not an agent-RSI product per se |
| 15 | **Guarded Delta Patches** (Store Less, Reuse More Safely): train-free lifelong agents store *guarded delta patches* instead of full skills. | Title + abstract snippet | Low | OpenReview oA6kKQe58G [PREPRINT] | NEW — pairs with #4 (tail collapse) as a mitigation candidate |

Other NEW-but-lower-priority (titles verified via Exa, abstracts unread — [UNVERIFIED] beyond title):
SIGA (self-evolving coding-agent adapters, arXiv:2606.09774); MetaAI Recursive Self-Design 0-to-1→1-to-N (arXiv:2606.09663);
EvoMaster (evolving agent framework for agentic science, Weinan E group); GRAM (RL-managed graph memory, OpenReview rzGvGnwVC7);
Memory Beyond Recall / dual-process memory (ywl53zPXu0); EDGE experience-distillation (JARVj9rlPP); HERO hindsight reflection (CFnfsORP7Y).

---

## Highest-signal deltas for our corpus

1. **PACE (arXiv:2606.08106)** — the single most relevant new result. It formalizes the failure mode our own
   PACE-like / e-process commit gates target: greedy accept = self-p-hacking → drift. Quantifies 30–42% false /
   10–33% harmful commits under greedy acceptance. **Read full text before next RSI-loop design decision.**
2. **Tail Knowledge Collapse (TailSkills)** + **Guarded Delta Patches** — paired problem/mitigation on recursive
   skill distillation degrading tail behavior. Directly cautions our skill-rewrite and "store-less" instincts.
3. **Vendor convergence on async memory consolidation as the productized RSI primitive**: Anthropic "Dreaming"
   (agent memory) + OpenAI "Dreaming" (consumer memory) both shipped *in this window* — the between-session
   consolidation loop is now a shipped pattern, not just research. Mirrors our own corpus belief-change ledger /
   compaction concerns.
4. **Anthropic "When AI builds itself"** is a FOLLOW-UP to our verification-bounded-RSI thesis (METR/H-JEPA
   corpus), not a repeat: it supplies a vendor-internal data point (>80% code authored by Claude) + an explicit
   "verifiable global pause" governance ask. Flag as delta, verify the >80% figure at the primary blog before citing.

## Disconfirmation / critique coverage (ran ≥1, found 3)

Critique line is healthy and frontier-relevant: **Fluent Reflection No Correction** (8 frontier LLMs, reflection
repeats prior violations) is the strongest — it passes the frontier-timeliness bar. **More Yap Less Meaning**
(SLM-only, 4.4% gain) is real but SLM-scoped → limited transfer to frontier agents. **Tail Knowledge Collapse**
critiques the recursive-distillation mechanism itself. Net: the window contains genuine adversarial pressure on
the "agents reliably self-correct/self-distill" premise, concentrated on open-ended (no clean verifier) tasks —
consistent with our verifier-conditioned-autonomy stance.

## Nothing-new / quiet areas
- **Meta (FAIR)**: no agent-RSI release surfaced in window (Gemma is Google; "MetaAI Recursive Self-Design"
  arXiv:2606.09663 is a paper title, not a Meta corporate release — do not conflate).
- **Formal RSI safety proofs**: only PACE (statistical commit gate) + VASO (physical-skill verification). No new
  theoretical bound on RSI convergence/safety beyond the commit-gate framing surfaced.
- **Follow-ups to the DO-NOT-REPEAT set** (AutoAgent / CORAL / Harness-1 / SlopCodeBench / CAID): none found
  citing them by name in-window. Self-Harness (#1) is the spiritual successor to Harness-1 but does not cite it
  in the abstract. Meta-Agent Challenge (#9) is adjacent to AutoAgent — confirm relationship on full read.

## Caveats
- OpenReview items are anonymous ACL ARR May-2026 submissions under review — numbers may change; cite as preprint.
- Vendor completion-rate figures (Harvey 6×, Anthropic >80%/8×) are self-reported, not independently audited.
- Abstracts read for #1,2,4,5,6,7,8; titles-only for #3,9,10,15 and the lower-priority list — flagged inline.
