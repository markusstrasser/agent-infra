---
title: Tool Use Reliability
date: 2026-03-21
---

# Tool Use Reliability

*Split from `frontier-agentic-models.md` on 2026-03-01. Part of the [agentic research synthesis](agentic-research-synthesis.md).*
*Date: 2026-02-27. Models in scope: Opus 4.6, GPT-5.2/5.3, Gemini 3.1 Pro.*

---

### What's PROVEN

**BFCL V4 remains current** — no V5 released yet as of Feb 2026. Top score still Qwen-3 at 70.8%. [SOURCE: gorilla.cs.berkeley.edu/leaderboard.html]

**NEW — MCP adoption data:** 97M+ monthly SDK downloads. Anthropic, OpenAI, Google, Microsoft all adopted. MCP-Radar benchmark: 507 tasks across 6 domains, designed specifically for MCP evaluation. Empirical study of 103 major MCP servers (856 tools) found tool description quality directly impacts agent performance. [SOURCE: zuplo.com/mcp-report, arXiv:2602.14878, OpenReview MCP-Radar]

**NEW — MCP tool description quality study (arXiv:2602.14878):** First large-scale empirical study of MCP tool description quality. Poor descriptions are "smelly" — they degrade agent performance. Proposes augmented descriptions. This validates our skill design principle: tool/skill descriptions ARE instructions and need the same care as CLAUDE.md. [SOURCE: arXiv:2602.14878] [PREPRINT]

### What's SPECULATED

- Whether Opus 4.6 or GPT-5.3 improve on BFCL V4 scores — no data yet.
- MCP-Radar results for current frontier models not published yet.

<!-- knowledge-index
generated: 2026-03-22T00:15:45Z
hash: 3e3adbe209c0

title: Tool Use Reliability

end-knowledge-index -->
