# Trending Scout — 2026-07-09

**Date:** 2026-07-09
**Window:** 2026-06-24 → 2026-07-09 (~15 days; freshness DUE cleared)
**Sources:** vendor-versions.py, Claude Code CHANGELOG (2.1.187→2.1.205), Cursor/xAI Grok 4.5 launch posts, docs.x.ai
**Findings:** 6 adopt/evaluate, several version bumps; known-set filtered (Grok transport already wired this session)

---

## Headline

Two load-bearing deltas: **(1) Grok 4.5** lands as a Cursor-pool + xAI frontier model (named niche in our stack — not Default Routing); **(2) Claude Code 2.1.198–2.1.205** makes background agents the default and hardens SessionStart/Notification hook contracts. Vendor versions: CC **2.1.205**, Codex **0.143.0**, Agent SDK py **0.2.114** / ts **0.3.205**.

## New Findings (ranked by value − maintenance)

### 1. SpaceXAI Grok 4.5 + Cursor first-party pool (2026-07-08)
| Field | Content |
|---|---|
| Source | cursor.com/blog/grok-4-5, docs.x.ai/developers/grok-4-5 |
| What | MoE frontier model jointly trained with Cursor; 500k ctx; $2/$6 (fast $4/$18); Cursor slugs `grok-4.5-{medium,high,xhigh}` (+fast). |
| Why relevant | New critique/scout lens; CursorBench contaminated — do not promote on that bench. |
| Verdict | **Adopted (named niche)** — transport + `--axes …,grok` + scout `--scout-model grok-4.5-xhigh`. See `decisions/2026-07-09-grok-4.5-transport.md`. |

### 2. CC 2.1.198 — subagents background-by-default + Notification hook events
| Field | Content |
|---|---|
| Source | changelog 2.1.198 |
| What | Subagents run in background by default; `Notification` fires `agent_needs_input` / `agent_completed`. Explore inherits parent model (capped opus). |
| Why relevant | Our maintain/scout fan-out assumes sync-ish subagent returns; background default changes supervision surface. |
| Verdict | **Evaluate** — audit SessionStart digests + any code that waits on subagent completion; consider wiring Notification consumers. |

### 3. CC 2.1.204 — SessionStart hook streaming in headless
| Field | Content |
|---|---|
| Source | changelog 2.1.204 (2026-07-08) |
| What | Hook events now stream during SessionStart in headless — fixes remote workers idle-reaped mid-hook. |
| Why relevant | We run headless `claude -p` / launchd-adjacent paths; silent reaping was a real failure class. |
| Verdict | **Adopt-now** — no config change; treat as vendor fix. Confirm headless SessionStart hooks still exit clean. |

### 4. CC 2.1.199 — Stop/SubagentStop `additionalContext` + hyphenated matcher exact-match
| Field | Content |
|---|---|
| Source | changelog 2.1.199 |
| What | Stop hooks can return `hookSpecificOutput.additionalContext` to continue the turn; hyphenated matchers exact-match (no accidental substring). |
| Why relevant | We already use additionalContext on UserPromptSubmit; Stop path is newly first-class. Matcher change can silently un-fire hooks that relied on substring. |
| Verdict | **Evaluate** — grep settings for hyphenated matchers; probe one Stop additionalContext consumer if useful. |

### 5. CC 2.1.200 — permission mode rename default→Manual; AskUserQuestion no auto-continue
| Field | Content |
|---|---|
| Source | changelog 2.1.200 |
| What | "default" permission mode renamed to "Manual"; AskUserQuestion no longer auto-continues by default. |
| Why relevant | Docs/scripts that say `permission-mode default` need `manual`; autonomous ask-hooks already warn. |
| Verdict | **Watch** — update any stale docs that say `default` mode; our askuserquestion-autonomous-warn stays relevant. |

### 6. CC 2.1.205 — `/doctor` full checkup; transcript-tamper auto-mode rule
| Field | Content |
|---|---|
| Source | changelog 2.1.205 |
| What | `/doctor` becomes setup checkup (+ `/checkup` alias); auto mode blocks transcript tampering. |
| Why relevant | Operator DX; transcript integrity under auto mode. |
| Verdict | **Extract** — optional: point our `just doctor` docs at CC `/doctor` as complementary, not duplicate. |

## Version bumps (no new adopt unless noted)

| Tool | Was (last scout ~06-24) | Now |
|---|---|---|
| Claude Code | ~2.1.187 | **2.1.205** |
| Claude Agent SDK (py/ts) | ~0.2.108 / 0.3.187 | **0.2.114 / 0.3.205** |
| Codex CLI | (prior window) | **0.143.0** |
| Gemini CLI (npm) | — | 0.50.0 (local 0.49.0 lag) |
| Modal | — | 1.5.1 (local 1.4.2 lag) |

## Deferred / already tracked
- Cursor CLI `/review` — still not a supersession signal for risky-diff-review SHADOW.
- `sandbox.credentials` (2.1.187) — still open policy call (improvement-log).
- Fable 5 metered off-subscription — already in model-guide (2026-07-07).

## Search log
- vendor-versions.py 2026-07-09
- CHANGELOG.md sections 2.1.187 → 2.1.205
- cursor.com/blog/grok-4-5 + docs.x.ai grok-4.5
- Prior memo: `research/trending-scout-2026-06-24.md`
