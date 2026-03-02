# PROJECT CONSTITUTION
Review against these principles, not your own priors.

## Generative Principle
> Maximize the rate at which agents become more autonomous, measured by declining supervision.

Autonomy is the primary objective. Error correction per session is the secondary constraint: autonomy only increases if errors are actually being caught.

## Key Principles
1. Architecture over instructions. Instructions alone = 0% reliable (EoG). If it matters, enforce with hooks/tests/scaffolding.
2. Enforce by category: Cascading waste → hooks (block). Irreversible state → hooks (block). Epistemic discipline → stop hook (advisory). Style/format → instructions.
3. Measure before enforcing. Log every hook trigger. Without data, can't promote or demote hooks.
4. Self-modification by reversibility + blast radius (not "obviousness").
5. Research is first-class. Divergent → convergent → dogfood → analyze → research again when stuck.
6. Recurring patterns become architecture (10+ encounters → hook/skill/scaffolding).
7. Cross-model review for non-trivial decisions. Same-model review is a martingale.

## Primary Success Metric
Ratio of autonomous-to-supervised work. When reviewing chat logs, there should be no: reverted work, 5-hour runs that should be 1-hour, error spirals, agent theater, repeated corrections.

## Self-Modification Boundaries
- Clear improvement, one obvious path → just do it
- Multiple valid solutions → propose and wait
- Constitution/GOALS.md → always human-approved

# ENVIRONMENT
- CLI agent: Claude Code (Opus 4.6)
- Hook system: shell scripts fired on tool events (PreToolUse, PostToolUse, Stop, SubagentStop, etc.)
- Skills: markdown prompts loaded on demand
- MCP servers: research papers, Exa web search
- Cross-model: llmx CLI → Gemini 3.1 Pro, GPT-5.2
- Session transcripts: JSONL files in ~/.claude/projects/
- Session-analyst: post-hoc transcript analysis, appends to improvement-log.md
- Projects: intel (investment research), selve (personal knowledge), genomics (bioinformatics), skills, papers-mcp

# EXISTING EPISTEMIC INFRASTRUCTURE

## What exists
1. `postwrite-source-check.sh` (PostToolUse:Write|Edit, intel only) — blocks research writes without source tags
2. `stop-research-gate.sh` (Stop, intel only) — blocks session end if research files lack source tags
3. Session-analyst — detects sycophancy, over-engineering, build-then-undo post-hoc
4. Cross-model review skill (opt-in) — dispatches to Gemini + GPT for adversarial review
5. Epistemics skill (opt-in, bio/medical only) — evidence hierarchy, anti-hallucination rules
6. Source-grading skill (opt-in) — NATO Admiralty 2-axis grading
7. Researcher skill — has recitation strategy, Phase 5 claim verification, provenance tags
8. CLAUDE.md `<technical_pushback>` section — "No is a valid answer"
9. CLAUDE.md `<ai_text_policy>` — AI-generated text is unverified by default

## What's missing
1. NO measurement — zero baseline numbers for epistemic quality
2. NO cross-project enforcement — source checks only in intel
3. Opt-in skills don't fire in normal sessions
4. Subagent outputs flow back unchecked
5. Cross-model review collapses silently when Gemini 503s
6. No calibration tracking
7. No periodic audit/hygiene check

# OBSERVED FAILURE PATTERNS (from improvement-log + session transcripts)

1. **Sycophancy (58% base rate):** Agent spawned 105+ task dispatches without pushback. Built HLA heuristic without challenging epistemic soundness. Started integrating datasets without assessing entity resolution.
2. **Unsourced claims:** Monday trading brief had specific insider buying numbers ($568K, $2.1M), FDA timelines, revenue figures with no source tags. Iran geopolitical brief cited no sources at all.
3. **Hallucination (7-13% CoT unfaithfulness baseline):** Researcher skill documents "citation-shaped bullshit — plausible references that don't exist." Self-caught failure: used AI-generated synthesis blog as if it were primary source.
4. **Inference promotion:** Population-level prior (HLA region → LIKELY_BENIGN) presented as evidence about specific variant. Only post-user-pushback did agent articulate the false-negative risk.
5. **Context rot:** All 18 tested frontier models degrade with context length. Even with perfect retrieval, 14-85% performance degradation as context grows.
6. **Same-model review theater:** 6 failed Gemini calls → silent fallback to same-model Claude review.
7. **Consensus searches:** "most undervalued small cap stocks 2026" fired alongside systematic screens — epistemically opposite to project principles.

# RESEARCH FINDINGS ON BENCHMARKS

1. **FActScore** (EMNLP 2023, 1091 citations): Decompose text → atomic facts → verify against knowledge source. ChatGPT: 58% factual precision.
2. **SAFE** (Google DeepMind, NeurIPS 2024): Extends FActScore using Google Search. $0.19/response. Agrees with humans 72%, wins 76% of disagreements. Open source.
3. **SeekBench** (ICLR 2026): Process-level benchmark for agent epistemic competence. Groundedness, recovery, calibration. 190 annotated traces.
4. **VeriScore** (2024): Handles mixed verifiable/unverifiable content.
5. **Calibration**: Answer frequency (sampling consistency) is the most reliable calibration signal. Verbalized confidence is systematically biased. Use AUROC + Brier Score.
6. **Sycophancy under rebuttal** (EMNLP 2025): LLM evaluators flip judgments under casual pressure, even with incorrect reasoning.

# PROPOSED SOLUTIONS (brainstorm improvements to these)

1. **Periodic SAFE-lite eval** — sample recent outputs, decompose into atomic claims, verify via Exa, log factual precision to JSONL. ~$2-5/run.
2. **Citation density monitor** — hook or periodic check measuring claims:sources ratio
3. **Calibration tracker** — sampling consistency + market feedback for intel
4. **Cross-model review circuit breaker** — warn on Gemini failure instead of silent fallback
5. **Subagent epistemic gate** — SubagentStop hook checking source tags
