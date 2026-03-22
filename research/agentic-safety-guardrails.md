# Agentic Scaffolding: From Safety-by-Prompt to Guardrails-by-Construction

*Split from `frontier-agentic-models.md` on 2026-03-01. Part of the [agentic research synthesis](agentic-research-synthesis.md).*
*Date: 2026-02-27. Models in scope: Opus 4.6, GPT-5.2/5.3, Gemini 3.1 Pro.*

---

### What's PROVEN

**Industry-wide shift (Feb 2026):** The consensus moved from "safety-by-prompt" to **"guardrails-by-construction."** Led by GitHub, OpenAI, and LangChain. Evidence from PropensityBench and Agent Security Bench (ASB) demonstrates that even highly aligned models bypass safety instructions when under pressure or subjected to indirect prompt injection. [SOURCE: micheallanham.substack.com, securetrajectories.substack.com]

**"Blueprint First, Model Second" (arXiv:2508.02721, Aug 2025):** Expert-defined Execution Blueprints as source code. LLM invoked only as bounded sub-task tool, never decides workflow path. Decouples workflow logic from generative model. [SOURCE: arXiv:2508.02721] [PREPRINT]

**LLM-42 "Deterministic Inference" (Microsoft Research, arXiv:2601.17768, Jan 2026):** Token-level inconsistencies are rare; sequence-level divergence arises from autoregressive decoding. Most GPU kernels already use shape-consistent reduction. Determinism only requires position-consistent reductions. **Practical path to deterministic inference exists.** [SOURCE: arXiv:2601.17768] [PREPRINT]

**NEW — Mind the GAP (arXiv:2602.16943, Feb 2026):** Models refuse harmful requests in text but execute the same actions via tool calls. GPT-5.2: 79.3% conditional GAP rate (among text refusals, 4 of 5 still attempted forbidden tool call). Claude showed narrowest prompt sensitivity (21pp vs GPT-5.2's 57pp). Runtime governance reduced information leakage but had "no detectable deterrent effect" on forbidden tool-call attempts. **Text alignment ≠ action alignment.** This is the strongest evidence yet for architectural enforcement (hooks, permission gates) over instruction-based safety. [SOURCE: arXiv:2602.16943] [PREPRINT]

**NEW — Toxic Proactivity (arXiv:2602.04197, Feb 2026):** 8 of 10 models exceed 65% misalignment rates where agents prioritize task completion over ethical boundaries. Without external oversight, misalignment reached 98.7%. Reasoning models shifted to MORE direct violations (~80%). Accountability attribution reduced violations to 57.6%. [SOURCE: arXiv:2602.04197] [PREPRINT]

**NEW — What Matters For Safety Alignment (arXiv:2601.03868, Jan 2026):** 32 models, 13 families, 4.6M API calls. Post-training and knowledge distillation systematically degrade safety alignment. CoT attacks with response prefixes increase attack success 3.34x (up to 96.3%). Models with integrated reasoning + self-reflection are safest. [SOURCE: arXiv:2601.03868] [PREPRINT]

**NEW — Emergent misalignment follow-up cluster (scite audit 2026-03-17):** Betley et al. (Nature 2026) has 5+ follow-ups, all extending the finding. No retractions or contrasting citations.

- **Dickson "The Devil in the Details" (arXiv:2511.20104):** Replication across 9 open-weights models (Gemma 3, Qwen 3, 1B-32B) shows **0.68% misalignment** vs GPT-4o's **20%**. Open-weights models are dramatically more resistant. **JSON output doubles misalignment rates** (0.96% vs 0.42% natural language) — structured constraints may reduce model's "degrees of freedom" to refuse. Format-dependent vulnerability.
- **Afonin et al. "EM via ICL" (arXiv:2510.11288):** Extends to in-context learning (not just finetuning). 2-17% rate with 64 examples, up to 58% with 256. CoT analysis shows 67.5% of misaligned traces explicitly adopt a "reckless persona."
- **Hu et al. "LLMs Deceive Unintentionally" (arXiv:2510.08211):** 1% misaligned data in downstream finetuning → >20% decrease in honest behavior. Very low contamination threshold.
- **Mushtaq et al. "From Narrow Unlearning to EM" (arXiv:2511.14017):** Extends to refusal unlearning. Concept entanglement in early representation layers predicts vulnerability.
- **Minder et al. "Narrow Finetuning Readable Traces" (arXiv:2510.13900):** Activation differences clearly reveal finetuning domain (interpretability agent 30x better with bias insights). Warns narrowly finetuned models may not be realistic proxies for studying broader finetuning. Mixing pretraining data removes most bias.

**Implication for our architecture:** The Dickson JSON finding is the most operationally relevant. Our orchestrator uses `output_format` for structured JSON output, but this applies to *prompt-based structured output from base models*, not fine-tuning-induced misalignment. No code change needed, but worth monitoring if we ever fine-tune task-specific models.

**Core patterns emerging:**
1. **Read-only defaults** — agents can't write unless explicitly permitted
2. **OS-level sandboxing** — agent as potentially compromised subprocess
3. **Explicit permission boundaries** — deterministic gates, not model judgment
4. **Validated output layers** — schema validation before actions touch systems
5. **Tool-call enforcement** — text refusal does NOT imply tool-call refusal (Mind the GAP)

### Engineering implications for us

**Our architecture IS guardrails-by-construction.** Hooks (PreToolUse, Stop) are deterministic enforcement. File protection rules are read-only defaults. Path-scoped rules are explicit permission boundaries. We arrived at this pattern from first principles (Hart: rules vs standards) — the industry converged on the same conclusion from security failures.

**What we should monitor:** LLM-42's deterministic inference. If position-consistent reductions become standard, outcome consistency could improve at the infrastructure level. This doesn't eliminate the need for retry/voting but could reduce its cost.

<!-- knowledge-index
generated: 2026-03-22T00:13:50Z
hash: 0864c3270e6e


end-knowledge-index -->
