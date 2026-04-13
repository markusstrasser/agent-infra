---
title: "Meta Knowledge MCP — Research & Decision Record"
date: 2026-03-01
---

# Meta Knowledge MCP — Research & Decision Record

**Date:** 2026-03-01
**Status:** Proceed with minimal Option B (measurement gate)
**Cross-model review:** `.model-review/2026-03-01-agent-infra-mcp/`

## Problem

Meta accumulates knowledge about Claude Code optimizations, hook designs, prompting patterns, and architectural decisions. Other projects (intel, selve, genomics, anki) can't access this knowledge without the human cd'ing into meta.

Two distribution mechanisms exist today:
- **Push (exists):** session-analyst → improvement-log → human implements in target repo. All 6 documented cross-repo examples are push.
- **Pull (doesn't exist):** a target repo's session querying meta on demand. "What's the hook pattern for blocking writes?" requires context-switching today.

## Cross-Model Review Critiques (Gemini 3.1 Pro + GPT-5.2)

### Arguments Against MCP (mostly Gemini)

1. **Push vs pull asymmetry (G4, strongest):** All cross-repo evidence is push (meta→target), not pull (target→meta). Building a pull server based on push evidence is an architectural mismatch.

2. **On-demand knowledge fallacy (G1):** Behavioral rules (failure modes, anti-sycophancy) must be always-loaded. Agents fail silently — they can't proactively ask "what am I about to do wrong?" Moving enforcement rules behind MCP degrades from "0% reliable at EoG" to invisible.

3. **Token savings collapse (measured):** Global CLAUDE.md is only ~1,712 tokens (99 lines). Meta's reference_data section is ~1,485 tokens. Not enough removable content to justify migration on token savings alone.

4. **Portability illusion (G2, P1):** .mcp.json with absolute paths (`/Users/alien/Projects/meta/...`) is no more portable than `~/.claude/CLAUDE.md`. Portable config ≠ portable behavior.

5. **Redundant abstraction (G3, partially wrong):** Agents CAN Read/Glob/Grep meta files from any project — but they don't know the files exist. Discovery is the real problem, not access.

6. **Native alternatives exist (G5, G6):** Skills do progressive disclosure (metadata→body→resources). EMB does search. Hooks do zero-token enforcement. These are already built.

7. **Constitutional tension (G15-G17, partially valid):** P1 (architecture > instructions) applies to enforcement but NOT to advisory/reference content. Serving "here's how to design a hook" as text is legitimate. Serving "don't spin on failures" as on-demand text is not — that needs a hook.

### Arguments For MCP (mostly GPT)

1. **Single source of truth (P4, P12):** Manual propagation creates version skew. MCP backed by meta files is always current. But deployment skew replaces manual skew unless commit-pinned.

2. **Token discipline possible (P9, P11):** Single constrained tool with response budgets (≤350 tokens p90) prevents blow-up. Start with one tool, not five.

3. **Measurement-gated (P8):** Build only after baseline shows need. Kill after 4 weeks if demand is <5 calls/week.

4. **Governance-aware (P5):** MCP across 3+ projects = shared infrastructure. Must explicitly govern under autonomy boundaries.

5. **Novel: MCP as write tool (G20):** Gemini's own blind spot — MCP could serve as a safe programmatic interface for updating meta rules (with validation gates), not just reading them.

### Partition Rule (from review)

| Knowledge type | Where it belongs | Why |
|---|---|---|
| Behavioral rules (communication, pushback, git workflow) | Always-loaded (global CLAUDE.md) | Agent can't self-diagnose violations |
| Enforcement (failure mode prevention) | Hooks (zero tokens until triggered) | Architecture > instructions (P1) |
| Reference/advisory (hook designs, research findings, architecture decisions) | On-demand (MCP or Read) | Low-frequency, high-value, large volume |
| Domain-specific patterns | Skills (progressive disclosure) | Already supports tiered loading |

## Decision

**Build minimal MCP (Option B) with measurement gate.**

- One tool: `search(query, max_tokens=350)`
- Backed by meta .md files (improvement-log, agent-failure-modes, research/, MEMORY.md sections)
- Added to each project's .mcp.json
- Global CLAUDE.md: NO changes (stays ~1,712 tokens)
- No content migration — purely additive
- `instructions=` tells agent what meta knows

**Gate:** 4 weeks. If search called <5 times/week across all projects → kill it, the pull pattern has no demand. If called regularly → expand.

**Success criteria (from GPT P13-P18, calibrated):**
1. search called in ≥5 sessions/week (proves demand)
2. p90 response size ≤350 tokens (proves token discipline)
3. No increase in correction rate (proves no harm)
4. Median time-to-guidance for agent-infra tasks decreases (proves value)

## What This Does NOT Replace

- Push-based propagation (session-analyst pipeline) — already working, stays as-is
- Global CLAUDE.md — stays unchanged, no migration
- Hooks — enforcement stays architectural
- Skills — progressive disclosure stays native
- Orchestrator MVP — separate backlog item for automating push triggers

<!-- knowledge-index
generated: 2026-03-22T00:15:44Z
hash: 9e43b4bfa9aa

title: Meta Knowledge MCP — Research & Decision Record

end-knowledge-index -->
