# Recent Agent Scaffolding, Instruction-Following, and Infra Papers

**Date:** 2026-03-05
**Question:** Which recent papers are actually worth reading on agent scaffolding, harness engineering, prompt/instruction design, and reliability infrastructure?
**Standard:** Prefer architectural signal over prompt cosmetics. Down-rank wrapper papers, benchmark theater, and post-training tricks unless they expose a durable systems lesson.

## Selection rule

The null process in this area is easy to mistake for progress:
- prompt tweaks that do not survive distribution shift
- verifier wrappers that add latency without changing the trust boundary
- multi-agent decompositions that just move errors across interfaces
- benchmark wins on synthetic tasks that do not probe real tool use

The residual signal is stronger when a paper does one of these:
- externalizes constraints into code, schemas, or policies
- isolates untrusted context from the privileged planner
- measures real tool use with realistic servers and distractors
- shows that long instructions are themselves a bottleneck

## Read Now

### 1. Defeating Prompt Injections by Design
- **Paper:** [Defeating Prompt Injections by Design](https://arxiv.org/abs/2503.18813)
- **Date:** 2025-03-24, revised 2025-06-24
- **Grade:** [C2]
- **Why it matters:** This is still the cleanest architectural paper in the space. The main move is to separate control flow from data flow and enforce capability policies in an interpreter rather than asking the model to "ignore" malicious instructions. That survives model weakness better than prompt hardening.
- **Main takeaway:** If untrusted tool output can directly enter the planner's working context, you do not have a serious prompt-injection defense.
- **Caveat:** Strong on exfiltration and action safety. Not a general solution for semantic deception or text-only misrepresentation.

### 2. AGENTSYS
- **Paper:** [AGENTSYS: Secure and Dynamic LLM Agents Through Explicit Hierarchical Memory Management](https://arxiv.org/abs/2602.07398)
- **Date:** 2026-02-07
- **Grade:** [C2]
- **Why it matters:** Best recent paper on memory isolation as a security primitive. Main agent delegates tool work to isolated workers; only schema-validated JSON returns to the parent. This shrinks both attack surface and context bloat.
- **Main takeaway:** Treat raw tool output as toxic waste. Do not let it accumulate in the same memory that drives planning.
- **Caveat:** Still uses an LLM validator, so the system is not perfectly hard-secure. But the architectural direction is strong.

### 3. AutoHarness
- **Paper:** [AutoHarness: improving LLM agents by automatically synthesizing a code harness](https://arxiv.org/abs/2603.03329)
- **Date:** 2026-03-05
- **Grade:** [D3]
- **Why it matters:** Best recent harness-engineering paper. Instead of manually writing the glue code around the model, the model synthesizes an action verifier or even a full code policy. Smaller model plus harness beats larger raw model in many game environments.
- **Main takeaway:** A weaker model inside a better harness can beat a stronger naked model.
- **Caveat:** Evidence is mostly on game environments with crisp legality constraints. Transfer to open-ended coding or research agents is plausible, not demonstrated.

### 4. SKILL-INJECT
- **Paper:** [SKILL-INJECT: Measuring Agent Vulnerability to Skill File Attacks](https://arxiv.org/abs/2602.20156)
- **Date:** 2026-02-25
- **Grade:** [C3]
- **Why it matters:** Directly relevant to any setup using third-party or shared `SKILL.md` files. It reframes skills as an instruction-supply-chain problem rather than a data-injection problem.
- **Main takeaway:** "Instruction hierarchy" defenses are weaker when the malicious payload lives inside a file the agent legitimately treats as instructions.
- **Caveat:** Benchmark paper, not a complete defense. But the threat model is real and operationally relevant.

### 5. MCP-Atlas
- **Paper:** [MCP-Atlas: A Large-Scale Benchmark for Tool-Use Competency with Real MCP Servers](https://arxiv.org/abs/2602.00933)
- **Date:** 2026-01-31
- **Grade:** [C3]
- **Why it matters:** Strong recent benchmark for real MCP use. Uses 36 real servers and 220 tools with distractors, and scores end answers via claims rather than pure trajectory matching.
- **Main takeaway:** Current frontier agents still fail mostly on tool discovery, parameterization, sequencing, and premature stopping, not on writing polished final answers.
- **Caveat:** Benchmark from Scale AI. Valuable diagnostically, but not a theory of how to fix the failures.

### 6. AGENT IF
- **Paper:** [AGENTIF: Benchmarking Instruction Following of Large Language Models in Agentic Scenarios](https://arxiv.org/abs/2505.16944)
- **Date:** 2025-05-22
- **Grade:** [C3]
- **Why it matters:** Best recent paper on long agentic instructions themselves. Instructions are long, constraint-heavy, and realistic rather than toy prompts.
- **Main takeaway:** Long system prompts and tool constraints are still followed poorly. Tool constraints and condition constraints are especially weak.
- **Caveat:** This is mainly a benchmark and error-analysis paper. It tells you where prompting breaks, not how to build a full replacement.

## Skim

### OCTOBENCH
- **Paper:** [OCTOBENCH: Benchmarking Scaffold-Aware Instruction Following in Repository-Grounded Agentic Coding](https://arxiv.org/abs/2601.10343)
- **Date:** 2026-01-16
- **Grade:** [C3]
- **Why skim:** Useful if you care about coding scaffolds specifically. Distinguishes task success from scaffold compliance and shows that models often get the task roughly right while breaking higher-priority instructions.

### LLM-in-Sandbox
- **Paper:** [LLM-in-Sandbox Elicits General Agentic Intelligence](https://arxiv.org/abs/2601.16206)
- **Date:** 2026-02-12
- **Grade:** [D3/C3]
- **Why skim:** Good for infrastructure direction. The key idea is that a sandbox is becoming default agent substrate, not just a coding tool.
- **Caveat:** Broad claims are stronger than the evidence. Treat it as directional rather than settled.

## Down-rank

### Prompt-only optimization papers
- If the core idea is a better prompt template without new enforcement, new boundaries, or realistic benchmarking, the work is low-priority.

### Detector-only prompt injection defenses
- If the defense still assumes raw untrusted content can safely flow into the privileged planner after filtering, the architecture remains fragile.

### Multi-agent wrappers without stronger invariants
- If the paper decomposes work across agents but does not improve trust boundaries, memory boundaries, or verification, it is usually moving failure around rather than removing it.

## Synthesis

Three conclusions look robust:

1. **Architecture is beating prompt cleverness.**
   The strongest recent papers are about harnesses, schemas, memory isolation, and capability policies, not better wording.

2. **Instruction load is a real bottleneck.**
   Long agentic prompts, tool specs, and condition-heavy instructions are still followed poorly. More instructions is not a reliable substitute for scaffolding.

3. **Tool use is still the weak link.**
   Real-agent failure is dominated by discovery, argument binding, sequencing, and contaminated context, not by prose generation.

## Practical reading order

If time is limited, read in this order:
1. `Defeating Prompt Injections by Design`
2. `AGENTSYS`
3. `AutoHarness`
4. `SKILL-INJECT`
5. `MCP-Atlas`
6. `AGENTIF`

## Sources

- [SOURCE: arXiv:2503.18813]
- [SOURCE: arXiv:2602.07398]
- [SOURCE: arXiv:2603.03329]
- [SOURCE: arXiv:2602.20156]
- [SOURCE: arXiv:2602.00933]
- [SOURCE: arXiv:2505.16944]
- [SOURCE: arXiv:2601.10343]
- [SOURCE: arXiv:2601.16206]

<!-- knowledge-index
generated: 2026-03-21T23:52:34Z
hash: 7002425a2b36

sources: 1
  D3: /C3

end-knowledge-index -->
