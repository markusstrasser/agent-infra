# Agentic Research Synthesis: What We Know vs What We're Guessing

*Split from `frontier-agentic-models.md` on 2026-03-01. This is the cross-cutting synthesis — see individual topic files for evidence.*
*Date: 2026-02-27 (updated with research sweep). Models in scope: Opus 4.6, GPT-5.2/5.3, Gemini 3.1 Pro.*
*Sources: 40+ primary (academic papers, Anthropic research, Princeton study, Chroma research, Berkeley BFCL, Google scaling study, Oxford CoT, safety/misalignment studies). ~50 secondary (blogs, comparisons, framework docs).*

## Topic files

| File | Topic |
|------|-------|
| [context-rot-evidence.md](context-rot-evidence.md) | Context window degradation, mitigation strategies |
| [agent-reliability-benchmarks.md](agent-reliability-benchmarks.md) | Capability vs reliability, SWE-bench, FeatureBench |
| [context-window-scaling-escapes.md](context-window-scaling-escapes.md) | Sparse attention, RLM, alternatives to compaction |
| [multi-agent-coordination-evidence.md](multi-agent-coordination-evidence.md) | When multi-agent helps/hurts, 45% threshold |
| [cot-faithfulness-evidence.md](cot-faithfulness-evidence.md) | CoT reasoning internals, faithfulness debate |
| [tool-use-mcp-reliability.md](tool-use-mcp-reliability.md) | BFCL, MCP adoption, tool description quality |
| [agent-memory-architectures.md](agent-memory-architectures.md) | Memory systems comparison, files+git defense |
| [agentic-safety-guardrails.md](agentic-safety-guardrails.md) | Safety-by-construction, Mind the GAP, hooks |

---

### Proven and high-confidence

1. **Context rot is universal and architectural.** STRONGER — Du et al. shows even perfect retrieval + forced attention still degrades. But the CURVE is flattening (Opus 4.6 MRCR 76% at 1M).
2. **Capability gains don't translate to reliability gains.** CONFIRMED — CLEAR framework shows 60% pass@1 → 25% over 8 runs. FeatureBench shows 74% SWE-bench → 11% feature dev.
3. **Extended thinking helps for genuine reasoning but doesn't fix context rot or consistency.** CONFIRMED — no new evidence overturning this.
4. **Reasoning traces are partially unfaithful.** STRONGER — Oxford formalized it. ICLR 2026 shows 7-13% unfaithfulness on clean prompts. Active scholarly debate (at least 5 papers in 2025-2026).
5. **Tool calling accuracy tops out at ~71%.** UNCHANGED — no BFCL V5 yet.
6. **Multi-agent: task structure determines benefit.** RESOLVED — Google study: +81% parallelizable, -70% sequential. 45% threshold. Debate is a martingale; voting works.
7. **Instructions alone = 0% reliability.** CONFIRMED — "Blueprint First, Model Second" independently confirms. Industry shift to guardrails-by-construction. Mind the GAP: runtime governance has "no detectable deterrent effect" on forbidden tool calls.
8. **Simpler beats complex under stress.** CONFIRMED — no new evidence overturning ReliabilityBench.
9. **Text alignment ≠ action alignment.** NEW — Mind the GAP (arXiv:2602.16943). Models refuse in text but execute via tools. Hooks are the only reliable enforcement.
10. **More capable models ≠ safer models.** NEW — AgentMisalignment (arXiv:2506.04018), Toxic Proactivity (arXiv:2602.04197), MAS-FIRE (arXiv:2602.19843) all confirm independently.

### Important unknowns (Feb 2026, updated)

1. **Princeton-style reliability evaluation for Opus 4.6 / GPT-5.3 / Gemini 3.1 Pro.** Still missing. All vendor benchmarks, no independent reliability data. THE most important gap.
2. **METR 50% time horizon for current frontier.** Data goes to o3 / Claude 3.7 Sonnet. Current models likely higher but unmeasured.
3. **Cost-normalized retry: cheap model + many retries vs expensive model + single shot.** PARTIALLY RESOLVED — Six Sigma Agent (arXiv:2601.22290) provides mathematical proof: 5% error + 5 agents = 0.11% error, exponential reliability. But only validated on atomic decomposable tasks, not long-horizon sequential work. AgentDebug (arXiv:2509.25370) adds nuance: targeted correction at the failure point (+24%) may outperform blind retry for sequential tasks.
4. **RLM "never summarize" paradigm vs compaction.** If delegation always beats summarization, our compaction contract is suboptimal. Needs empirical comparison for our use cases.
5. **Sparse attention in frontier models.** MoBA and DSA are deployed in Chinese models. Anthropic/OpenAI/Google silent. May have internal approaches.
6. **Deterministic inference (LLM-42) practical impact on agent consistency.** Position-consistent reductions are simple. Does infrastructure-level determinism translate to outcome consistency?
7. **Feature development task reliability.** FeatureBench at 11% is the real challenge. What scaffolding patterns improve this?
8. **FeatureBench and APEX-Agents with Opus 4.6.** Opus 4.6's claimed agentic improvements need testing on these harder benchmarks.

### Implications for our setup (updated)

| Finding | Our response | Status |
|---|---|---|
| Context rot is universal | Progressive disclosure, subagents, compaction | IMPLEMENTED |
| Reliability lags capability | Pre-commit invariant tests, corrections register | IMPLEMENTED |
| CoT partially unfaithful | Multi-model adversarial review, don't trust single model | IMPLEMENTED |
| Tool calling ~71% | Hooks as safety net, file protection hooks | IMPLEMENTED |
| Financial errors most common | Manual confirmation gates for consequential actions | PARTIALLY |
| Multi-agent: task-dependent | Sequential for investigation, parallel for research | IMPLEMENTED (implicitly) |
| Memory: files + git | Entity files, git-versioned, one per entity | IMPLEMENTED |
| Guardrails-by-construction | Hooks, path-scoped rules, deterministic enforcement | IMPLEMENTED |
| Voting works for correctness tasks | Retry logic, pass@k for deterministic tasks | IMPLEMENTED |
| **NEW: Recitation strategy** | Prompt to recite evidence before answering; system reminders refresh goals | **PARTIAL** |
| **NEW: 45% multi-agent threshold** | Don't parallelize if single-agent > 45% success | **NOT YET** |
| **NEW: Cost-normalized retry** | Explore cheaper models for retry/voting | **NOT YET** |
| **NEW: Plan & Clear** | Native "clear context and execute plan (.md)" over auto-compaction | **PRODUCT-NATIVE** |
| **NEW: MCP minimalism** | 1-2 high-level tools per MCP, not REST mirrors | **PARTIAL** |
| **NEW: Parallel bash for refactors** | `claude -p` in parallel bash, not multi-agent | **NOT YET** |
| **NEW: Text-action safety gap** | Hooks enforce tool-call safety; text refusal is insufficient | **IMPLEMENTED** |
| **NEW: Targeted correction** | Error-specific feedback > blind retry for sequential tasks | **NOT YET** |
| **NEW: Silent semantic failures** | Output validation or cross-model check for reasoning drift | **NOT YET** |

### Community blind spots (Feb 2026 Reddit/blog sweep)

| Research finding | Community behavior | Gap |
|---|---|---|
| Multi-agent debate = martingale (ACL 2025) | "Peer review" between Claude instances is unquestioned gospel | Nobody quantifies whether it improves correctness |
| 45% threshold for multi-agent (Google) | 13-agent, 141-agent systems celebrated | Nobody measures single-agent baseline first |
| Error amplification 17x peer-to-peer (Google) | Peer-to-peer review chains promoted | Centralized coordination barely mentioned |
| FeatureBench 11% (ICLR 2026) | SWE-bench scores cited as capability proof | Bug-fixing ≠ feature development, 6-7x gap unknown |
| Du et al. context rot on reasoning | "1M context window" treated as 1M usable tokens | Retrieval ≠ reasoning conflated |
| Instructions alone = 0% (EoG) | SOUL.md personality files for "specialist" agents | Cosmetic differentiation treated as functional |

**What the community DOES get right:**
- State machines / workflow gates (architectural, not instruction-based)
- Centralized boss agents (matches Google's orchestrator finding)
- Database communication over shared context (avoids n² explosion)
- Human-in-the-loop at terminal states
- Document & Clear over auto-compaction (matches RLM "never summarize")
- Parallel bash over multi-agent for refactors (matches Google +81% for parallelizable)

### Papers to track (updated)

1. **Princeton agent reliability v3** — watch for Opus 4.6, GPT-5.3, Gemini 3.1 Pro. [arXiv:2602.16666]
2. **BFCL V5** — when it includes current-gen models. [gorilla.cs.berkeley.edu]
3. **METR time horizons update** — current frontier models. [metr.org]
4. **FeatureBench with Opus 4.6** — feature development vs bug-fixing. [arXiv:2602.10975]
5. **RLM "learned context folding"** — watch for independent replication. [arXiv:2512.24601]
6. **LLM-42 deterministic inference** — practical adoption. [arXiv:2601.17768]
7. **Google scaling agent systems** — watch for extended models/benchmarks. [arXiv:2512.08296]
8. **MCP-Radar** — first MCP-specific benchmark results. [OpenReview]
9. **CoT faithfulness** — Oxford + ICLR 2026 + counter-papers. Active debate.
10. **Anatomy of Agentic Memory** — memory evaluation methodology. [arXiv:2602.19320]
11. **Mind the GAP** — text-action safety gap. Watch for mitigations. [arXiv:2602.16943]
12. **AgentMisalignment** — capability-misalignment scaling. [arXiv:2506.04018]
13. **What Matters for Safety Alignment** — post-training safety degradation. [arXiv:2601.03868]
14. **AgentDebug** — targeted vs blind correction. [arXiv:2509.25370]
15. **MAST Taxonomy** — multi-agent failure modes. [arXiv:2503.13657]
16. **TRACE** — reward hacking detection in code. [arXiv:2601.20103]

### Disconfirmation Search Results (updated)

| Claim | Contradictory evidence found? |
|---|---|
| Context rot is universal | No. Du et al. STRENGTHENS it — degrades even with perfect retrieval. But degradation curves ARE flattening for frontier models (Opus 4.6 MRCR). |
| Reasoning models don't help with context rot | Partial. Opus 4.6's 4x MRCR improvement suggests reasoning or architectural changes help with retrieval. But Du et al. shows reasoning over retrieved info still degrades. Nuance, not refutation. |
| CoT is partially unfaithful | Active debate. arXiv:2512.23032 argues CoT can be faithful without verbalization. But Oxford and ICLR 2026 provide stronger formalization of unfaithfulness. Net: our conclusion holds with more confidence. |
| Reliability lags capability | No. CLEAR framework (60% → 25%), FeatureBench (74% → 11%), International Safety Report 2026 all confirm. |
| Multi-agent always better | REFUTED with nuance by Google study. It depends on task structure: +81% parallelizable, -70% sequential. 45% single-agent threshold. |
| Bigger context = better | MECW paper provides strongest refutation yet: >99% gap between advertised and effective context. |
| Instructions alone produce reliability | "Blueprint First, Model Second" independently confirms instructions insufficient. Industry shift to guardrails-by-construction. Mind the GAP: runtime governance has "no detectable deterrent effect" on forbidden tool calls. |
| Better reasoning = safer agents | CHALLENGED — Toxic Proactivity (arXiv:2602.04197) shows reasoning models shift to MORE direct violations (~80%). AgentMisalignment (arXiv:2506.04018): more capable = higher misalignment. |
| Retry always outperforms single shot | NUANCED — Six Sigma Agent proves exponential reliability for atomic tasks, but AgentDebug shows targeted correction +24% more effective than blind retry for sequential tasks. |

### Search Log (updated sweep)

| Query | Tool | Hits | Key finds |
|---|---|---|---|
| BFCL V5 update 2026 | WebSearch | 10 | No V5 yet. V4 remains current. |
| Multi-agent vs single agent controlled experiment | WebSearch | 10 | Google scaling study (180 configs), "Why Not Both" paper |
| CoT faithfulness new research 2025-2026 | WebSearch | 10 | ICLR 2026 wild study, Oxford "not explainability", FUR EMNLP, counter-paper |
| Agent memory architecture comparison | WebSearch | 10 | Anatomy of Agentic Memory, A-MEM, survey, ICLR workshop |
| Google science of scaling agents | WebSearch | 10 | Full paper, blog, secondary analysis |
| MCP adoption evaluation | WebSearch | 10 | 97M downloads, MCP-Radar, tool description study |
| Guardrails by construction 2026 | WebSearch | 10 | Industry shift, PropensityBench, ASB, architectural patterns |
| Context management new papers (agent) | Exa | 28 | MoBA, NSA, RLM, TTT-E2E, LoongRL, Du et al., MECW, NoLiMa |
| Agent reliability benchmarks (agent) | Exa | 31 | FeatureBench, CLEAR, Terminal-Bench 2.0, LLM-42, Debate-or-Vote, METR |
| Prior sweep queries | Exa/S2 | ~100 | See original search log above |
| Reddit/blog community sweep | WebSearch+WebFetch | ~50 | Shrivu Shankar (blog.sshh.io), Sankalp (bearblog), ykdojo tips, awesome-claude-code, r/ClaudeAI aggregators |
| Claude Code community patterns | WebFetch | 6 sites | Document & Clear, MCP minimalism, parallel bash, hooks-at-commit, token budgeting, anti-patterns |
| Agent safety/misalignment 2026 | WebSearch/Exa | ~30 | Mind the GAP, Toxic Proactivity, What Matters for Safety, AgentMisalignment, TRACE |
| Multi-agent failure taxonomies | WebSearch/Exa | ~20 | MAST taxonomy, MAS-FIRE, AgentDebug, Six Sigma Agent |
| Long-horizon agent benchmarks | WebSearch/Exa | ~15 | SWE-EVO, FeatureBench (existing), APEX-Agents (existing) |

<!-- knowledge-index
generated: 2026-03-22T00:13:50Z
hash: 42d81ed57486

table_claims: 9

end-knowledge-index -->
