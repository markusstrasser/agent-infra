# Open / Local Agentic Models Scout — 2026-06-20

Window prioritized: May 20-June 20, 2026. Sources: Exa-primary search, then direct primary URLs. I filtered out listicles/roundups and older staples unless they materially changed the current picture.

## Findings

### 1. Kimi K2.7 Code — Moonshot open agentic coding model
Primary URL: https://www.kimi.com/resources/kimi-k2-7-code | Date: 2026-06-19  
Claim: K2.7 Code is a K2.6-derived coding-focused agentic model with ~30% fewer thinking tokens and reported gains on MCP/tool-use benchmarks. Moonshot reports MCP Atlas 76.0 and MCP Mark Verified 81.1, up from K2.6’s 69.4 and 72.8. ([kimi.com](https://www.kimi.com/resources/kimi-k2-7-code)) ([kimi.com](https://www.kimi.com/resources/kimi-k2-7-code))  
Demonstrated vs asserted: Mostly asserted/vendor-run; Moonshot explicitly says Kimi Code Bench v2 and Kimi Claw are in-house, and the comparison uses different harnesses for Kimi/Claude/Codex. ([kimi.com](https://www.kimi.com/resources/kimi-k2-7-code))  
Maturity: Kimi-K2 GitHub: 10.9k stars; last-push not visible in fetched page; active official release page dated 2026-06-19. ([github.com](https://github.com/moonshotai/Kimi-K2))  
Why it matters: This is the most directly relevant new open model for local Claude-Code/Codex/Cursor-style harnesses, but it needs your own harness eval before trusting the MCP numbers.

### 2. GLM-5.2 — Z.ai long-horizon open model
Primary URL: https://z.ai/blog/glm-5.2 | Date: 2026-06-16  
Claim: Z.ai reports GLM-5.2 as a 1M-context long-horizon model, improving over GLM-5.1 on Terminal-Bench 2.1 from 63.5 to 81.0 and SWE-bench Pro from 58.4 to 62.1; GitHub README says it targets long-horizon work and stronger coding. ([github.com](https://github.com/zai-org/GLM-5))  
Demonstrated vs asserted: Vendor-run; useful because it is explicitly benchmarked in coding-agent settings, but not independently replicated here.  
Maturity: `zai-org/GLM-5`: 4.7k stars, Exa result reported last push 2026-06-20; repo README includes GLM-5.2. ([github.com](https://github.com/zai-org/GLM-5))  
Why it matters: Strong candidate for a local/open agent backend where 1M context and terminal-task competence matter more than chatbot polish.

### 3. Qwen Code v0.17.x — zero-config computer-use in an open coding agent
Primary URL: https://qwenlm.github.io/qwen-code-docs/en/blog/weekly-update-2026-06-04/ | Date: 2026-06-04  
Claim: Qwen Code v0.17.0/v0.17.1 made Computer Use a built-in capability with 9 deferred desktop automation tools, one-time confirmation, auto binary download, macOS permission guidance, and MCP lifecycle management. ([qwenlm.github.io](https://qwenlm.github.io/qwen-code-docs/en/blog/weekly-update-2026-06-04/)) ([qwenlm.github.io](https://qwenlm.github.io/qwen-code-docs/en/blog/weekly-update-2026-06-04/))  
Demonstrated vs asserted: Demonstrated in shipped OSS harness surface; not a model benchmark, but directly executable infrastructure.  
Maturity: `QwenLM/qwen-code`: 25.4k stars, 2.5k forks, latest release v0.18.3 on 2026-06-17; GitHub API shows pushed_at 2026-06-19. ([github.com](https://github.com/QwenLM/qwen-code)) ([api.github.com](https://api.github.com/repos/QwenLM/qwen-code))  
Why it matters: For a single-operator local harness, this is more stealable than most model claims: deferred built-in tools plus compression fixes for screenshot-heavy runs.

### 4. MiniMax M3 — open-weight 1M-context multimodal/computer-use model
Primary URL: https://www.minimax.io/blog/minimax-m3 | Date: 2026-06-01  
Claim: MiniMax says M3 combines 1M context, native multimodality, desktop computer operation, and agentic/coding benchmark strength, with MCP Atlas 74.2 and SWE-bench Pro 59.0 reported in release notes. ([minimax.io](https://www.minimax.io/blog/minimax-m3))  
Demonstrated vs asserted: Vendor-run; the product surface is real, but benchmark transfer to a local harness is unproven.  
Maturity: Official blog release; GitHub/model repo not surfaced as a dedicated M3 repo in this pass.  
Why it matters: If computer-use plus long context is needed in an open-weight stack, M3 is the most obvious new MiniMax candidate.

### 5. MiniMax M2.7 — self-evolving harness claims
Primary URL: https://www.minimax.io/news/minimax-m27-en | Date: 2026-03-18, still relevant via June arXiv/agentic discussion  
Claim: MiniMax says M2.7 can build complex harnesses, use Agent Teams/Skills/dynamic tool search, and autonomously optimized an internal programming scaffold over 100+ rounds for a 30% improvement. ([minimax.io](https://www.minimax.io/news/minimax-m27-en))  
Demonstrated vs asserted: Mostly asserted/internal; the interesting part is not the score, it is the described harness self-optimization loop.  
Maturity: `MiniMax-AI/MiniMax-M2.7`: 346 stars, 23 commits, no GitHub releases visible. ([github.com](https://github.com/MiniMax-AI/MiniMax-M2.7)) ([github.com](https://github.com/MiniMax-AI/MiniMax-M2.7))  
Why it matters: The steal is architectural: failure-trajectory analysis -> scaffold edit -> eval -> keep/revert, not “use MiniMax as default.”

### 6. MiniMax M2 Series paper
Primary URL: https://arxiv.org/html/2605.26494 | Date: 2026-05  
Claim: The paper frames M2/M2.7 as agentic-deployment-first MoE models, with agent-driven data pipelines, Forge RL, and reported M2.7 scores: SWE-bench Pro 56.2, SWE-bench Multilingual 76.5, Terminal-Bench 2.0 57.0, Toolathlon 46.3.  
Demonstrated vs asserted: Paper evidence, but primarily lab-reported model family results; good for method, not final current rate.  
Maturity: arXiv:2605.26494.  
Why it matters: Useful method signal for local harness design: agentic training data is executable workspace plus artifact-aligned reward, not generic chat SFT.

### 7. DeepSeek V4 Pro CAISI evaluation
Primary URL: https://www.nist.gov/news-events/news/2026/05/caisi-evaluation-deepseek-v4-pro | Date: 2026-05-01  
Claim: CAISI/NIST evaluated DeepSeek V4 Pro and found it lagged the frontier by about 8 months across domains, using controlled token budgets and agent scaffolding. ([nist.gov](https://www.nist.gov/news-events/news/2026/05/caisi-evaluation-deepseek-v4-pro))  
Demonstrated vs asserted: Demonstrated by an official evaluator, though not an open reproduction and not focused only on local developer harnesses.  
Maturity: Official evaluation; DeepSeek V3.2-Exp repo: 1.6k stars, MIT, no GitHub releases visible. ([github.com](https://github.com/deepseek-ai/DeepSeek-V3.2))  
Why it matters: Counterweight to vendor “frontier parity” claims; DeepSeek may be cheap/open, but don’t assume parity for your hardest autonomous loops.

### 8. DeepSeek V4 API/model release and agent scores
Primary URL: https://api-docs.deepseek.com/updates | Date: 2026-04-24  
Claim: DeepSeek API added V4-Pro/V4-Flash, OpenAI and Anthropic interfaces, and retired legacy aliases on a schedule; Exa surfaced reported agent numbers including SWE Verified 80.6, MCPAtlas 73.6, Toolathlon 51.8 from the technical-report ecosystem.  
Demonstrated vs asserted: Vendor/API release is demonstrated; benchmark scores remain first-party unless separately reproduced.  
Maturity: DeepSeek repo/activity as above; release is API-visible rather than GitHub-release-driven.  
Why it matters: Anthropic-compatible routing makes it easy to drop into Claude-Code-shaped tools, but local harness scores need reproduction because CAISI’s independent result is more conservative.

### 9. Hugging Face “Is it agentic enough?” — local/open model eval harness pattern
Primary URL: https://huggingface.co/blog/is-it-agentic-enough | Date: 2026-06-18  
Claim: HF proposes benchmarking agents on your own tooling, measuring process cost rather than just final answer, with model × repo revision × task sweeps on HF Jobs. ([huggingface.co](https://huggingface.co/blog/is-it-agentic-enough))  
Demonstrated vs asserted: Demonstrated methodology/blog plus code-linked workflow; not a model release.  
Maturity: Official HF blog; no single model maturity metric.  
Why it matters: This is directly stealable for a single-operator local harness: compare models by tool-call efficiency, token burn, and revision sensitivity on your actual CLI/tasks.

### 10. Llama status — no genuinely new June agentic release found
Primary URL: https://ai.meta.com/blog/Llama-4-multimodal-intelligence/ | Date: pre-window / not June  
Claim: Llama 4 remains relevant as open-weight multimodal infrastructure, but I did not find a genuinely new May-June 2026 Meta Llama agentic release with fresh tool-use benchmark results from primary sources.  
Demonstrated vs asserted: Negative finding from primary-source search; papers like MAVEN/AgentFloor test Llama 4 variants, but that is benchmark work, not a new Llama release.  
Maturity: `meta-llama/llama-models`: 7.6k stars. ([github.com](https://github.com/meta-llama/llama-models))  
Why it matters: Do not spend integration attention here unless you need Llama licensing/locality specifically; the new action is Qwen/Kimi/GLM/MiniMax.

## Readout

The real June action is not “open models beat closed frontier.” It is “open models are now being optimized and packaged for Claude-Code-shaped long-horizon loops”: Kimi K2.7 Code, GLM-5.2, Qwen Code, and MiniMax M3/M2.7 all explicitly target tool chains, MCP, terminal agents, or computer use.

The evidence quality is uneven. Qwen Code’s harness feature is shipped and inspectable. Kimi/GLM/MiniMax benchmark numbers are mostly vendor-run and harness-confounded. DeepSeek has the strongest independent corrective signal via CAISI/NIST, and it says “good, not current frontier.”

## Top Steals

1. Steal Qwen Code’s deferred built-in tool pattern: load schemas lazily, one approval, auto-manage MCP server lifecycle.
2. Build a tiny HF-style local eval: same repo task, same harness, swap Kimi/GLM/Qwen/DeepSeek/MiniMax, measure success plus token/tool-call cost.
3. Treat vendor MCP/SWE scores as screening only; promote a model only after it survives your own Claude-Code/Codex/Cursor workload.