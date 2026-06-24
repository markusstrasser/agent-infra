# Trending Scout — 2026-06-24

**Date:** 2026-06-24
**Window:** 2026-06-19 → 2026-06-24 (5 days)
**Sources:** Exa, Brave, GitHub releases, alphaXiv, arxiv (4 parallel scout subagents; ~398K subagent tokens / 42 tool-uses)
**Findings:** 9 new, several version bumps, known-set filtered (SlopCodeBench/Harness-1/EvoTrainer/RHO/NRT-Bench/hermes/DSPy already tracked)

---

## Headline

CC 2.1.184→2.1.187 quietly made **two permission surfaces load-bearing** (`Agent(type)` rules now enforced; `sandbox.credentials`) and **changed an interactive default** (`!` bash output auto-feeds the model). The ecosystem + paper signal both cluster on **harness self-evolution** — Xiaomi's MiMo-Code productionizes our exact RSI thesis (judge-gated `/goal`, `/dream`+`/distill`), and the paper front (Harness-Updating-Is-Not-Harness-Benefit, APEX, HarnessFix) sharpens *how to measure* the loop: decouple mutator-quality from consumer-uptake, distill success not only failure, attribute on held-out.

## New Findings (ranked by value − maintenance)

### 1. CC 2.1.186 — `Agent(type)` permission rules now ENFORCED for named subagent spawns
| Field | Content |
|---|---|
| Source | code.claude.com/docs/en/changelog (CC 2.1.186, 06-22) |
| What | Previously-unenforced `Agent(type)` deny / `Agent(x,y)` allow rules in settings now actually block subagent spawns. Silent behavior change. |
| Why relevant | We dispatch named subagents heavily (maintain loop, scouts). If any `Agent(...)` rule sits in settings, it's now load-bearing — could silently block a lane. |
| Verdict | **Adopt-now** — audit settings for `Agent(...)` rules; confirm none now blocks an intended lane. |

### 2. CC 2.1.187 — `sandbox.credentials` setting
| Field | Content |
|---|---|
| Source | changelog (CC 2.1.187 / py SDK 0.2.108 / ts SDK 0.3.187, 06-23) |
| What | Blocks sandboxed commands from reading credential files + secret env vars. |
| Why relevant | Directly hardens autonomous/sandbox-mode runs — cheap, low-maintenance security. |
| Verdict | **Adopt-now** — enable for autonomous lanes. |

### 3. MCPProxy `retrieve_tools` lazy tool-loading (pattern)
| Field | Content |
|---|---|
| Source | via 5kahoisaac/opencode-configs (MCPProxy routing mode) |
| What | One proxy endpoint searches MCP tools on-demand and lazy-loads only those matching the task keyword, instead of injecting every tool into context. |
| Why relevant | Attacks our always-loaded MCP-tool context budget — every subagent spawn pays it (measured baseline ~16.7K always-loaded tok). |
| Verdict | **Extract-pattern** — cheap probe vs static `.mcp.json`; measure context saved. |

### 4. "Harness Updating Is Not Harness Benefit" (2605.30621)
| Field | Content |
|---|---|
| Source | arxiv 2605.30621 (fresh, 0 cites) |
| What | Update-GENERATION and update-BENEFIT are decoupled abilities; uptake is the bottleneck and is non-monotonic in model strength (mid-tier gains most; a cheap model is an adequate mutator). |
| Why relevant | Our loop counts a landed hook/rule as "improvement" — this says measure **mutator-quality and consumer-uptake separately, held-out, per-consumer**. A rule that helps Opus may not help a weaker subagent. |
| Verdict | **Read-deep** — informs how the RSI loop should instrument itself (mechanism is scale-independent; tier-rates use pre-frontier open models, flag uncertain). |

### 5. Codex rust-v0.142.0 — subagent terminal-error propagation (+ token budgets, delegation modes)
| Field | Content |
|---|---|
| Source | github.com/openai/codex/releases/tag/rust-v0.142.0 (06-22) |
| What | Parent agents now RECEIVE terminal subagent errors (#28375) instead of seeing them as empty successful completions; + rollout token-budget aborts; + multi-agent delegation modes; + indexed web-search. |
| Why relevant | The error-propagation fix is exactly the failure class behind our subagent-zero-output gate (claude-code#47936). |
| Verdict | **Evaluate** — re-check whether our zero-output gate needs adjustment on Codex 0.142. |

### 6. MiMo-Code (Xiaomi, 10.6k★, MIT) — judge-gated `/goal` + `/dream`/`/distill`
| Field | Content |
|---|---|
| Source | github.com/XiaomiMiMo/MiMo-Code (v0.1.3, 06-24, TS, OpenCode fork) |
| What | `/goal` = independent-judge model gates stopping (prevents "optimistic stops"); `/dream` distills traces→memory; `/distill` discovers repeated workflows; SQLite FTS5 cross-session memory. |
| Why relevant | Convergent external validation of our verifier-conditioned-autonomy + over_caution/"ready means execute" concern, and our /observe→skill-graduation loop — as readable code, from a major lab. |
| Verdict | **Extract-pattern** — read the judge-gate impl before any `/goal`-style work; don't adopt (we're single-operator, no OpenCode fork). |

### 7. CC 2.1.186 — `respondToBashCommands` default change (interactive)
| Field | Content |
|---|---|
| Source | changelog (CC 2.1.186, 06-22) |
| What | `!`-prefixed bash output now AUTO-feeds the model (was context-only); `"respondToBashCommands": false` restores prior. |
| Why relevant | Global rule tells the operator to use `! <command>` for interactive logins — output now auto-responds. Default-behavior shift worth awareness. |
| Verdict | **Watch** — note in session guidance; not a fix. |

### 8. APEX — L2 success-trace distillation (2606.15363)
| Field | Content |
|---|---|
| Source | arxiv 2606.15363 (06-13) |
| What | 3-layer co-evolution; L2 = distill behavioral principles from SUCCESS traces (inverse of our failure-driven correction ledger). Headline metric is a self-defined proxy (Goodhart-flag). |
| Verdict | **Extract-method** — the success-distillation half complements our failure-only ledger (the "save from success AND failure" gap). |

### 9. HarnessFix — held-out trace attribution (2606.06324)
| Field | Content |
|---|---|
| Source | arxiv 2606.06324 (06-04) |
| What | Trace→IR with step-level provenance attributes failures to a specific step×harness-layer; flaw-record consolidation; reports **held-out** improvement. |
| Verdict | **Extract-method** — the held-out-attribution discipline is our anti-Goodhart guard mechanized; informs debug-until-dry/session-trace. |

## Version Bumps

| Tool | Previous | Current | Notable |
|---|---|---|---|
| Claude Code | 2.1.183 | 2.1.187 | Agent(type) enforce, sandbox.credentials, respondToBashCommands, MCP idle-timeout abort, StructuredOutput loop fix |
| Claude Agent SDK (ts) | — | 0.3.187 | background canUseTool + agent_id, rewind_conversation, ReadMcpResourceDirTool |
| Codex | 0.141 | rust-v0.142.0 | subagent error propagation, token budgets, delegation modes |
| Google GenAI SDK | 2.8.x | 2.10.0 | interactions rewrite, WebSocket API-key-in-URL security fix, Computer Use fields |
| Antigravity `agy` | — | 1.0.11 | ADC auth (`USE_ADC`), permission-engine regex fixes |
| Gemini CLI | 0.46 (local) | 0.47.0 | (being transitioned INTO Antigravity `agy` per discussion #27274) |

## Already Known (filtered)

SlopCodeBench, Harness-1, EvoTrainer, RHO, NRT-Bench, predict-then-falsify gate papers, NousResearch hermes self-evolution, DSPy, DeusData codebase-memory-mcp (vetoed), Polaris/Gödel-agent (out-of-window, March). CC permission `Tool(param:value)` (2.1.178) + native git-blocking (2.1.183) — last memo.

## Search Log

4 parallel researcher subagents (Anthropic deep-check; OpenAI+Google; ecosystem+MCP; papers). All verified versions against release pages, not memory. No hook-system changes landed this window (our hook infra stable). Unverified: claude-code #32105 tool-output-compression + Agent Teams stabilization — appear unresolved as of 2.1.187 (issue pages not reliably fetchable). Gemini CLI deltas now land on Antigravity `agy`, not gemini-cli — adjust baseline tracking.
