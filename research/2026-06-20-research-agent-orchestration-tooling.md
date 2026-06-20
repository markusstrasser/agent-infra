---
title: Research-Agent Orchestration Tooling — adopt / pattern-extract / already-frontier?
date: 2026-06-20
status: COMPLETE
question: As of mid-2026, is there GENUINELY useful (non-hype) tooling for orchestrating AI research agents worth adopting or pattern-extracting, benchmarked against our research-mcp + /research + CORAL stack?
prior_coverage:
  - research/futurehouse-technical-analysis.md (2026-03-19 — PaperQA2 7-stage pipeline, RCS, Aviary)
  - research/ai-research-tools-landscape-2026-03.md (Consensus/Elicit/FutureHouse, March)
  - research/academic-research-agent-landscape-2026-03.md (OpenScholar/STORM/scite, March)
note: Prior memos 3mo stale (pre-frontier). This pass re-verifies MATURITY on live GitHub/products (2026-06-20) + surfaces 2026 developments (Kosmos, Co-Scientist→Nature).
---

# Research-Agent Orchestration Tooling — 2026-06-20

## Verdict (bottom line)

**Already at/above frontier for our exact use case** (sourced literature memos with adversarial
verification). The OSS lit-review orchestrators (STORM, OpenScholar, GPT-Researcher, PaperQA2,
open_deep_research) either DON'T do what we do, are stale, or are architecturally at parity with
our CORAL + researcher-subagent + research-mcp stack.

**BUT two PATTERN-EXTRACTS are worth it — both are state/loop-shape mechanisms we lack, not products to adopt:**
1. **Kosmos "structured world model"** — persistent externalized research-state object that holds
   coherence over *hundreds of agent trajectories / tens of millions of tokens*, with every
   conclusion traceable to a code line or literature passage. Our CORAL caps at 3 epochs (~36
   turns) and discards inter-epoch state into a flat memo. This is the single biggest delta.
2. **Co-Scientist idea-tournament (Elo ranking of competing hypotheses)** — a generate→critique→
   **rank**→evolve loop where hypotheses compete pairwise. Our stack generates + verifies but does
   not *rank competing conclusions against each other*. Nature-validated May 2026 (not hype).

Nothing here justifies ADOPTING a dependency. Both wins are ~50-line loop-shape changes to the
researcher skill / CORAL, gated by the state-externalization lens we already hold
([[state-externalization-lens]]).

---

## Maturity table (live GitHub / product, verified 2026-06-20)

| Tool | Stars | Last push | Contribs | Status | What it is |
|---|---|---|---|---|---|
| assafelovic/gpt-researcher | 27.8k | **2026-05-28** | 100+ | ACTIVE | autonomous web/deep-research wrapper, any LLM |
| stanford-oval/storm | 28.9k | **2025-09-30** ⚠️ | 23 | **DORMANT ~9mo** | multi-perspective Q→outline→article w/ citations |
| Future-House/paper-qa (PaperQA2) | 8.7k | **2026-06-11** | 39 | ACTIVE | high-accuracy scientific RAG w/ citations |
| Future-House/aviary | 273 | 2026-06-05 | — | ACTIVE (niche) | language-agent gym for scientific tasks (RL training) |
| AkariAsai/OpenScholar | 1.5k | **2025-08-13** ⚠️ | — | **DORMANT ~10mo** | 8B retrieval-augmented science model |
| langchain-ai/open_deep_research | 11.8k | **2026-06-20** | 26 | VERY ACTIVE | supervisor+parallel-subagent deep research, MIT |

Bus-factor read: gpt-researcher (100+ contribs) and open_deep_research (LangChain-backed) are
healthy. PaperQA2 (39, FutureHouse-backed) healthy. STORM and OpenScholar are research artifacts
that shipped their paper and went quiet — treat as **pre-frontier / decayed**, do not benchmark
against current frontier.

---

## Per-tool verdict (does it do something our stack can't?)

### Google Co-Scientist — REAL, current, one pattern worth extracting
- **Source:** DeepMind blog; Nature paper May 2026 (AML drug-repurposing + liver-fibrosis validation,
  labcritics 2026-05-21); opened to individuals via "Gemini for Science" / Hypothesis Generation at
  I/O 2026 (blog.google, labs.google/science). Gemini Enterprise has a hosted Co-Scientist agent.
- **What it does that we don't:** coalition of specialized agents (generate / proximity-map /
  reflect / **rank** / evolve) running an **"idea tournament"** — pairwise Elo-style ranking of
  competing hypotheses (borrowed from AlphaGo/AlphaStar self-play, applied to scientific debate).
- **Delta vs us:** our pipeline gathers→verifies→synthesizes a *single* line; it does not pit
  competing conclusions against each other and rank-evolve. This is the same family as ShinkaEvolve/
  eve's Elo-from-pairwise fitness already in our evolutionary memos — convergent signal that
  **tournament-ranking over competing research conclusions is a real mechanism**, not noise.
- **Verdict:** PATTERN-EXTRACT the generate-AND-rank-competing-hypotheses loop. Don't adopt (Gemini-
  Enterprise-gated; no benefit to our $0 Claude-sub routing).

### FutureHouse / Edison Kosmos — REAL (arXiv:2511.02824, Nov 2025), the standout delta
- **Source:** edisonscientific.com/news/announcing-kosmos; arXiv:2511.02824 (2025-11-05); endpoints/
  dig.watch coverage. verify_claim: mechanism CONFIRMED (released Nov 2025, not "2026" — minor correction).
- **Numbers (vendor-stated, flag as such):** 1,500 papers + 42,000 lines of analysis code per run;
  **79.4% of conclusions validated**; ~"6 months of PhD work" per run; **$200/run ($1/credit)**.
- **The mechanism — "structured world model":** a persistent, externalized research-state object that
  "incorporates information extracted over hundreds of agent trajectories and maintains coherence
  toward a specific objective over tens of millions of tokens." Explicitly framed as the fix for
  *finite context length* limiting reasoning depth. Vendor gives no architecture detail (flag: it's
  a marketing post; arXiv:2511.02824 has the substance — not fetched this pass, follow-up if we build).
- **Traceability:** every report conclusion traces to a specific code line or literature passage =
  "fully auditable." This is the provenance discipline our [[claim-provenance-interop-standards]] /
  defeasible-cache work already wants, applied at the synthesis-output layer.
- **Delta vs us:** CORAL caps at 3 epochs (~36 turns) and flattens inter-epoch knowledge into a memo;
  there is no persistent, growing, queryable world-state across trajectories. Kosmos's world-model is
  exactly the "externalize recoverable bookkeeping out of the policy" lever from Harness-1 /
  [[state-externalization-lens]], applied to multi-trajectory *research* rather than coding.
- **Verdict:** PATTERN-EXTRACT the world-model-as-externalized-research-state (NOT adopt the $200/run
  product). Highest-value finding. If we build, read arXiv:2511.02824 first for the actual structure.

### langchain-ai/open_deep_research — ACTIVE, but architectural PARITY with us
- supervisor + parallel researcher subagents, each with isolated context window, iterative search →
  compress findings. Ranked #6 on DeepResearch Bench. MIT, pushed 2026-06-20.
- **Delta vs us:** ~none architecturally — this IS our researcher-subagent + CORAL pattern (parent/
  supervisor owns final answer, bounded subagents, isolated context, compress-then-return). They have
  async background subagents (a throughput nicety we could mirror via `run_in_background`), and a
  filesystem-context "deep agents" abstraction. No verification/adversarial layer like ours.
- **Verdict:** ALREADY-FRONTIER. Confirms our architecture is the field-standard shape. Only nicety:
  async background subagents for throughput (we already have `run_in_background`).

### GPT-Researcher — ACTIVE, BELOW our depth
- 27.8k stars, 100+ contribs, very alive. But it's a breadth-first web-research → report wrapper
  (planner + executor over web search). No citation-stance verification, no adversarial claim-check,
  no paper-fulltext synthesis. **Verdict:** BELOW our stack (we have verify_claim + cross-model
  critique + ask_papers over fulltext). Nothing to extract.

### PaperQA2 (Future-House/paper-qa) — ACTIVE, RCS already partially in our stack
- The one durable mechanism is **RCS** (rerank+contextual-summarization: LLM maps over top-k chunks,
  emits relevance score 0-10 + query-specific summary; ablation drop p<0.001) and **calibrated
  refusal** (explicit "I cannot answer," 21.9% refusal, 85.2% precision-on-answered). research-mcp's
  `prepare_evidence` (RCS scoring) already implements the rerank-summarize step. Calibrated-refusal as
  an explicit abstention option in synthesis is a small possible add, not a dependency.
- **Verdict:** AT PARITY on the transferable mechanism; calibrated-refusal is a minor optional polish.

### STORM (Stanford OVAL) — DORMANT, pre-frontier
- Last push 2025-09-30 (~9mo). Mechanism (multi-perspective question simulation → outline → article)
  is a 2024 NAACL idea (arXiv:2402.14207). **Flag: pre-frontier, relevance decayed.** Don't benchmark.

### OpenScholar (Ai2) — DORMANT, pre-frontier
- Last push 2025-08-13 (~10mo). The Nature result (OpenScholar-8B beats GPT-4o +6.1% on
  ScholarQABench; GPT-4o hallucinates citations 78-90%) is a model+benchmark contribution, not an
  orchestration framework to adopt. **Flag: decayed.**

### Products not worth a dependency (UX/access, not orchestration we lack)
- **Elicit** — best-in-class evidence-table UX + factored cognition; closed product. extract_table in
  research-mcp already does Elicit-style structured extraction. No orchestration delta.
- **Consensus / Undermind / Perplexity research / Manus** — consumer products; no inspectable
  orchestration we could pattern-extract that we don't already have. Perplexity-research = our
  deep_research; SaC already vetoed ([[sac-eval-verdict]]).

---

## Where we actually stand (honest frontier check)

Our stack = research-mcp (S2/Exa/OpenAlex/EuropePMC search, fetch+extract, ask_papers 1M-context
synthesis, prepare_evidence=RCS, verify_claim, deep_research, citation traversal) + /research skill +
researcher subagent w/ persistent memory + CORAL epochs + cross-model adversarial verification.

- **Search/retrieval/synthesis:** at or above the OSS field (multi-source, fulltext, RCS present).
- **Verification:** ABOVE field — none of the OSS orchestrators have our adversarial claim-check +
  cross-model critique. open_deep_research, GPT-Researcher have zero verification layer.
- **Loop shape (multi-trajectory state + ranking):** BELOW Kosmos (no persistent world-model) and
  Co-Scientist (no hypothesis tournament). These are the two genuine gaps.

## Recommended actions (both pattern-extract, neither adopt)
1. **World-model-as-externalized-research-state** for CORAL: replace the flat inter-epoch memo with a
   persistent, growing, queryable state object (claims + provenance pointers + open-gaps), so coherence
   survives across epochs/trajectories. Read arXiv:2511.02824 before building. Consumer: the researcher
   subagent loop. Gated by [[state-externalization-lens]] (this IS that lever for research).
2. **Tournament-rank competing conclusions** when a research question has >1 viable answer: generate N
   conclusions, pairwise-critique+rank (Elo), evolve the winner. Convergent with ShinkaEvolve/eve Elo
   fitness already in our evolutionary memos. Consumer: /research synthesis step on contested questions.

## Caveats / provenance flags
- Kosmos numbers (1,500 papers, 79.4%, $200/run) are VENDOR-stated marketing-page figures — directional,
  not independently verified. arXiv:2511.02824 is the substance (not read this pass).
- Co-Scientist Nature validation (May 2026) is real and peer-reviewed; the "idea tournament" is the
  durable mechanism, not the specific wet-lab results.
- STORM / OpenScholar flagged pre-frontier (>9mo dormant) — prior March memos benchmarked against them;
  that comparison has decayed.
