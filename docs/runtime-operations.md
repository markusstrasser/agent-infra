# Runtime operations

Read the relevant section for operational diagnosis or cross-project integration. Recipe invocations and layout are pointers; derive live state with just orient / just --list. The dated model/provider snapshots below are historical evidence, not current routing defaults; use llmx info and the model-guide / llmx-guide skills before dispatch.

## Operational entrypoints

```bash
just --list                              # all recipes, grouped
just orient                              # live map — WHAT IS IT? jobs·hooks·MCP·skills, derived from ground truth (never stale)
just harness-eval                        # hook/skill pre-commit gate (~43s): hooks-smoke · drift · prior-context · orient tests
just session-trace <uuid-prefix>         # Eve-shaped span replay from agentlogs (structural forensics)
just smoke                               # minimal functional test (<1m)
uv run python3 scripts/doctor.py         # cross-project health check — HEALTHY? (full validation)
uv run python3 scripts/dashboard.py      # agent ops dashboard — WHAT HAPPENED?
uv run agentlogs recent                  # recent runs across vendors (live data: Claude+Codex+Cursor; Gemini+Kimi adapters wired but no sessions in 21d retention window)
uv run agentlogs search <query>          # FTS5 search across all vendors
uv run agentlogs stats                   # DB size, per-vendor counts, indexer health
just blindspot                           # loop-miss miner (emb); digest at .claude/blindspot-digest.md
just observe-context [project] [sessions]  # size-safe observe context (<600KB for llm-dispatch)
just prior-context-triage              # classify post-hook prior-context misses
just gather <plan.md>                   # deterministic context gather (no LLM)
just critique <plan.md>                 # gather → cross-model critique
just questions                          # human-gated pending decisions (act-drain VIEW)
just graph <id>                         # RSI-lifecycle neighborhood of a decision/commit/finding (agentlogs-native; canonical relation vocab)
just adversarial-debug-scout <repo> &   # read-only audit scouts → <repo>/docs/audit/ (background; from any repo: just -f ~/Projects/agent-infra/justfile …)
just debug-until-dry <repo> &           # scout wave loop until no new confirmed bugs; triage docs/audit/ inline
```


## Cross-project layout
| Layer | Location | Syncs how |
|-------|----------|-----------|
| Global CLAUDE.md | `~/.claude/CLAUDE.md` | Loaded in every project (universal rules) |
| Shared skills | `~/Projects/skills/` | Symlinked into global `~/.claude/skills/` by `friend-sync.sh` (each `~/.claude/skills/<name>` → `~/Projects/skills/<name>`); the global dir loads in every project. Project `.claude/skills/` holds project-specific skills only. |
| Shared hooks | `~/Projects/skills/hooks/` | Referenced by path in each project's `settings.json` |
| Project rules | `.claude/rules/` per project | Diverges intentionally (domain-specific) |
| Project hooks | `.claude/settings.json` per project | Per-project, similar patterns |
| Project agent doc | `CLAUDE.md` per project (canonical) | `AGENTS.md` symlinks to `CLAUDE.md` so Codex/Gemini/Cody read the same source. Never edit AGENTS.md directly. |
| Global hooks | `~/.claude/settings.json` | Loaded in every project |
| Research MCP | `~/Projects/research-mcp/` | Configured in `.mcp.json` per project |
| Genomics pipeline | `~/Projects/genomics/` | Extracted from selve 2026-02-28 |


## Historical transport notes

Transport facts (installed CLIs, subscription routes, effort aliases): `llmx info` or Read `~/.claude/cache/llmx-routing.json` (refresh: `llmx info --write-mirror`). Task-class model/effort choice: **model-guide skill**. Footguns during migration: **llmx-guide skill**.

**Claude routing policy (2026-06-15):** Anthropic paused API credit migration; `claude -p` and Agent SDK stay on **subscription**. Never route Claude through paid API (`anthropic-direct`, API-key billing) unless explicitly requested. Default headless: `llmx chat --subscription -m claude-opus-5` (alias: `-p anthropic --lite bare`). Smoke/probe: `llmx chat --dry-run --subscription -m claude-opus-5`. Critique preflight: `model-review.py --preflight`.

**Grok 4.7 (2026-09-23, verified live):** named niche — **not** Default Routing. Opt-in PLAN cosign: `just critique <plan> --axes standard,grok` (repo-grounded `cursor-agent --model grok-4.7-high --workspace`; no `cursor-` prefix — 4.7 dropped it, 4.6 still carries it). Scout lens: `just debug-until-dry <repo> recent --scout-backend cursor --scout-model grok-4.7-high`. Confirmed with `cursor-agent models` signed in; preflight fails closed if the exact id is absent. 4.6 slugs stay admitted. xAI API key may still 403 — Cursor pool is the live surface. Anchor: `decisions/2026-07-09-grok-4.5-transport.md` · model-guide Grok 4.7 section.

**GPT-5.6 suite (2026-07-09):** OpenAI default is **Sol / Terra / Luna** (`gpt-5.6-sol` alias `gpt-5.6`, `gpt-5.6-terra`, `gpt-5.6-luna`). Cross-lab/architecture → Sol; everyday critique → **Luna** (≈ prior 5.5 perf at ~½ price); mechanical → Luna low; Terra = mid opt-in. Effort includes `max`. Pro = API `reasoning.mode=pro`. **GPT-5.5 removed** (no upgrade). Anchor: `decisions/2026-07-09-gpt-5.6-suite.md`.

**Kimi K3 (2026-07-16):** llmx `kimi` provider default → `kimi-k3` (metered; provider flipped to api.moonshot.**ai** — the local key 401s on .cn). 1M context, $3/$15 cache-miss ($0.30 cache-hit input). Launch thinking is max-only, no effort knob — llmx sends none. Opt-in open-weight coding lane, **not** Default Routing. Vendor caveats: thinking-history sensitivity (no mid-session switch), excessive proactiveness. Anchor: skills `model-guide/references/CHANGELOG.md` 2026-07-16.

Anchor: `decisions/2026-06-15-llmx-refactor-dispatch-layer.md`.

