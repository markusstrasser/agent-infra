#!/usr/bin/env bash
# Parallel gpt-5.5-low landscape sweep via codex exec (subscription, $0).
# Web search via exa MCP (codex --search doesn't work in exec). exa-primary to
# avoid Brave 1req/s 429 + perplexity 401 at 6 parallel. 2 waves of 6.
set -uo pipefail
unset OPENAI_API_KEY   # force $0 ChatGPT-subscription path (doctor flagged mixed auth)
OUT=/Users/alien/Projects/agent-infra/research/sweep-raw-2026-06-20
cd /Users/alien/Projects/agent-infra

PRE='You are a research scout. Today is 2026-06-20. Use the exa MCP tools for web search as PRIMARY (if perplexity returns 401, continue exa-only; do NOT use brave-search). Find genuinely NEW developments, prioritizing the last 4 weeks (May-June 2026), on the TOPIC below. SKIP well-known pre-2026 staples unless a genuinely new release/result. For each finding give: name + PRIMARY url (GitHub/arxiv/official blog ONLY, never listicles/medium roundups) + date | 1-line claim | demonstrated-vs-asserted | maturity (GitHub stars + last-push date if a repo, arxiv id if a paper) | 1-line why-it-matters for a SINGLE-OPERATOR LOCAL Claude-Code/Codex/Cursor harness (we do NOT run a hosted multi-agent service). Flag pre-frontier (pre-2026 model evidence) as low-transfer. Max ~10 findings ranked by relevance. End with a 3-line TOP STEALS note. End with a COMPLETE markdown report as your final message. Do NOT create any files. TOPIC: '

run() { codex exec --full-auto -c model_reasoning_effort="low" -o "$OUT/$1.md" "$PRE$2" >"$OUT/$1.log" 2>&1; echo "done:$1 exit=$?"; }

# WAVE 1
run general-agent-frameworks 'general agent / multi-agent FRAMEWORKS: LangGraph, CrewAI, AutoGen/AG2, OpenAI Agents SDK, Pydantic-AI, Google ADK, Mastra, Agno, smolagents, Atomic Agents, LlamaIndex Workflows. New releases, breaking changes, benchmarks.' &
run coding-agents 'autonomous CODING agents and benchmark movement: Claude Code, Codex CLI, Cursor/Composer, Cline, Aider, OpenHands, Devin, Amp, Zencoder. SWE-bench / Terminal-Bench / SWE-bench-Pro leaderboard changes.' &
run mcp-tool-ecosystem 'the MCP (Model Context Protocol) ecosystem: new notable MCP servers, the MCP spec/registry, MCP security, agent TOOL ecosystems and tool-calling improvements.' &
run agent-memory-context 'agent MEMORY and CONTEXT-engineering systems: Letta/MemGPT, Mem0, Zep, Cognee, context-engineering frameworks/writeups, long-horizon agent memory.' &
run self-evolving-agents 'self-evolving / self-improving agent repos and papers BEYOND the known set [DGM, AutoAgent, DSPy, GEPA, Hermes, SkillOpt, AI-Scientist, AdaEvolve, ShinkaEvolve, Bayesian-Agent, AHE]. Genuinely NEW ones only.' &
run arxiv-agents-newest 'the NEWEST arxiv papers (last 2 weeks) on LLM agents, agentic reasoning, tool use, and agent harness optimization.' &
wait
echo "=== WAVE 1 COMPLETE ==="

# WAVE 2
run agent-eval-benchmarks 'new agent EVALUATION benchmarks and leaderboards released in 2026: agentic, tool-use, long-horizon, web/computer-use, terminal.' &
run practitioner-blogposts 'high-signal PRACTITIONER and frontier-lab BLOGPOSTS on building agents (Anthropic, OpenAI, Cognition, Cursor, serious independents) from the last 6 weeks.' &
run context-prompt-engineering 'recent CONTEXT-ENGINEERING and prompt-engineering best practices, tooling, and research for agents (2026).' &
run local-open-models-agentic 'OPEN / LOCAL models for AGENTIC use: Qwen3, DeepSeek, Kimi K2, GLM, Llama, MiniMax. New releases plus their tool-use / agent benchmark results in 2026.' &
run multi-agent-orchestration 'new MULTI-AGENT ORCHESTRATION patterns, durable-execution for agents, orchestration products beyond Temporal/LangGraph (2026).' &
run agent-observability-tooling 'agent OBSERVABILITY / EVAL / gateway dev-tools: LangSmith, Braintrust, Helicone, AgentOps, Langfuse, Phoenix/Arize, OpenLLMetry. New 2026 capabilities.' &
wait
echo "=== WAVE 2 COMPLETE ==="
echo "ALL DONE: $(ls -1 $OUT/*.md 2>/dev/null | wc -l) axis files"
