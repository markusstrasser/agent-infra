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

**Core patterns emerging:**
1. **Read-only defaults** — agents can't write unless explicitly permitted
2. **OS-level sandboxing** — agent as potentially compromised subprocess
3. **Explicit permission boundaries** — deterministic gates, not model judgment
4. **Validated output layers** — schema validation before actions touch systems
5. **Tool-call enforcement** — text refusal does NOT imply tool-call refusal (Mind the GAP)

### Engineering implications for us

**Our architecture IS guardrails-by-construction.** Hooks (PreToolUse, Stop) are deterministic enforcement. File protection rules are read-only defaults. Path-scoped rules are explicit permission boundaries. We arrived at this pattern from first principles (Hart: rules vs standards) — the industry converged on the same conclusion from security failures.

**What we should monitor:** LLM-42's deterministic inference. If position-consistent reductions become standard, outcome consistency could improve at the infrastructure level. This doesn't eliminate the need for retry/voting but could reduce its cost.
