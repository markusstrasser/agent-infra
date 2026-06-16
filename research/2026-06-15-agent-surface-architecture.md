---
date: 2026-06-15
topic: Agent surface architecture — API design principles applied to tools/skills/hooks/rules/MCP/subagents
tier: deep
synthesis_of:
  - research/2026-06-15-agent-surface-api-design-principles.md
  - research/2026-06-15-agent-extensibility-surfaces.md
  - 4-agent parallel dispatch (inventory, gap analysis, vendor comparison)
decision_relevance: surface selection, consolidation, discoverability under context budget
---

# Agent Surface Architecture — Research Synthesis

**Question:** Given API design best practices, how should we design and govern tool surfaces, repo surfaces, agentic surfaces (subagents/rules/tools/hooks/skills/MCPs/plugins)?

**Tier:** Deep | **Date:** 2026-06-15

**Ground truth:** Prior memos cover tool attention (2026-04-25), MCP deltas (2026-05-27), agent dev-loop tooling (2026-06-08), review dispatch (decision 2026-06-14). This synthesis adds the **API-design lens** across all surface types.

---

## Executive verdict

Our architecture is **philosophically right, operationally leaky**.

- **Right:** partition over router (`/code-review` vs `/critique`), usage-gated MCP retirement, native-first surface budget, progressive disclosure via path-scoped rules, fail-open hooks, `just orient` as discoverability hub.
- **Leaky:** skills description budget overrun (Claude 10.5k chars; intel combined 14k vs 8k Codex ceiling), closeout partition unenforced in practice, premature plan-complete (no gate), incomplete parseable error envelopes, MCP spawn tax, ~80+ deferred MCP tools competing for selection attention.

The binding constraint is not model capability — it's **context budget + selection accuracy**. RAG-MCP data: same model, same tools, 13.6% → 43% selection accuracy when visible tool count drops. [SOURCE: tianpan.co/blog/2026-04-19-over-tooled-agent-problem] Our ~30k always-loaded ceiling and genomics 16-server eager spawn are the local instantiation.

---

## Surface taxonomy (when to use which)

| Surface | Load model | Enforcement | Use when |
|---------|------------|-------------|----------|
| **Rules** (`.claude/rules/`, CLAUDE.md) | Always / path-scoped | Advisory | Invariants model must always know; governance boundaries |
| **Skills** (`~/Projects/skills/`) | Lazy, auto-invoke or `/name` | Advisory | Recurring workflows; procedural knowledge |
| **Hooks** (event-triggered) | Per event | Deterministic block/pass | Cascading waste, irreversible ops, checkable predicates |
| **MCP tools** | Schema per turn | Typed schema + server | External systems; typed programmatic actions |
| **MCP resources** | On-demand fetch | Read-only | Reference data (indexes, maps) — **underused** |
| **Subagents** | Explicit dispatch | Isolated context | Fan-out, parallelism, sandbox |
| **Repo surfaces** (`just`, scripts, launchd) | Bash-invoked | Exit codes / reports | Operator + agent CLI; zero-API automation |
| **Governance** (decisions/, improvement-log) | On-demand | Hook-protected writes | Path-dependent reasoning; RSI ledger |

**Promotion heuristic** [SOURCE: Anthropic agent-design.md]: bash/rules → tool/hook when you need to **gate, render, audit, or parallelize** → skill when workflow recurs → subagent when context must isolate.

**Vendor partition** [DATA: `research/2026-06-15-agent-extensibility-surfaces.md`]: hooks=enforce, MCP=external, context-file=always-on is universal. Skills exist only on Claude+Cursor; Codex/Gemini use flat AGENTS.md/GEMINI.md instead.

---

## Inventory snapshot [DATA]

| Layer | Approx. count | Consumers | Overlap risk |
|-------|---------------|-----------|--------------|
| Shared skills | 52 (+ 14 Cursor meta) | Claude, Cursor (partial) | Tri-mount: Projects/skills → .claude + .cursor symlinks |
| Hook scripts | 127 files; 88 global handlers | Claude, Codex (shimmed) | intel project: 80 handlers |
| Rules | ~16/project + 8 global | Claude, Cursor, Codex via AGENTS.md | Constitution duplicated per project |
| MCP servers | 5 global + 16/project (genomics) | All MCP-capable | Eager spawn; bash often preferred over MCP tools |
| Subagent defs | 8 custom + vendor builtins | Claude Agent, Cursor Task | Overlaps skills for review/observe |
| `just` recipes | 29 (agent-infra) | All via Bash | Canonical entry; best discoverability |
| Research/decisions | 252 / 43 | On-demand + MCP search | Dedup failure across 4+ stores |
| Scripts | 149 (agent-infra) | Bash / launchd | Many parallel MCP tool paths |

---

## Claims table

| # | Claim | Evidence | Confidence | Status |
|---|-------|----------|------------|--------|
| 1 | Tool selection degrades on a cliff, not a slope — consolidation before addition is the #1 lever | RAG-MCP 13.6%→43%; Perplexity ~100 tok/skill index entry | HIGH | VERIFIED |
| 2 | Vendors converge on hooks+MCP+context-file; skills are Claude/Cursor-only | Platform docs comparison | HIGH | VERIFIED |
| 3 | Our review partition is correct; stacking is the bug, not missing router | ADR 2026-06-14; critique SKILL.md line 3 | HIGH | [DATA] |
| 4 | Terminal/bash beats MCP for our repo scale (~5× cost, 0 repo-tools MCP uses) | arXiv:2604.00073; agent-dev-loop memo | MED | VERIFIED |
| 5 | Parseable failure envelopes are highest-ROI zero-dep fix | agent-dev-loop Tier 1 #1; hooks partial, MCP/scripts not | HIGH | [DATA] |
| 6 | MCP Resources suit research-index/codebase-maps better than always-loaded rules | Vendor MCP primitive partition; context-budget canary | MED | INFERENCE |
| 7 | Description trigger+negative criteria measurably lift tool routing | Anthropic tool-use-concepts.md | MED | FRONTIER (not replicated locally) |
| 8 | JSON Schema validates shape, not referent existence | tianpan.co Jun 2026 | MED | VERIFIED |
| 9 | Self-generated skills provide no benefit on average | Perplexity skills article | LOW | FRONTIER |
| 10 | Codex `modify` hook outcome has no Claude equivalent — input rewrite without block | OpenAI Codex hooks docs | HIGH | VERIFIED |

---

## Scorecard (local surfaces vs API lenses) [INFERENCE]

| Surface | Partition | Discover | Compose | Envelopes | Stability | Surprise | Budget |
|---------|:---------:|:--------:|:-------:|:---------:|:---------:|:--------:|:------:|
| Hooks | OK | POOR | OK | OK | OK | OK | OK |
| Skills | GOOD | OK | OK | OK | OK | OK | GOOD |
| Rules | OK | POOR | OK | — | OK | OK | OK |
| MCP | GOOD | POOR | OK | POOR | OK | OK | GOOD |
| Subagents | OK | OK | POOR | OK | OK | POOR | OK |
| Scripts | POOR | POOR | OK | OK | OK | POOR | OK |
| **just** | GOOD | GOOD | GOOD | OK | GOOD | GOOD | GOOD |

`just orient` is the best single discoverability surface; rules/hooks/MCP scatter without it.

---

## Top 5 proliferation pain points [DATA]

1. **Review stacking** — closeout runs diff + design + composer on same artifact (ADR phase 2 open)
2. **MCP deferred-tool bloat** — 16 servers/project, 5.25s import; scite moved bio-only; lazy-import still open
3. **MCP exists, agents use Bash** — 0 genomics MCP pipeline calls vs 260× `modal app list`
4. **Four-surface dedup** — governance miners miss CLAUDE.md + rules → duplicate candidates
5. **Half-loops** — predictions.jsonl (4 seeds), skill-usage-watch killed, session_quality retired

---

## Recommendations (maintenance-ranked)

| Rank | Action | Why | Maintenance |
|:----:|--------|-----|-------------|
| 1 | **Failure envelope on MCP + scripts** — `[<tool>] BLOCKED` + `fix: agentlogs index` | One-turn self-correction; hooks already partial | Low |
| 2 | **Finish closeout partition** (ADR items 1–5) | Stops highest-waste stacking | Low–med |
| 3 | **Four-surface dedup in all governance miners** | Prevents duplicate rules/skills | Low |
| 4 | **Advisory hook retirement via gov.py** (read-discipline 6680/60d) | Cuts composability noise | Med |
| 5 | **Lazy-import + MCP prune** (genomics/phenome) | SessionStart latency | Med–high |
| 6 | **Pilot MCP Resources** for research-index + codebase maps | Offloads always-loaded budget | Med |
| 7 | **Codex skills sync** — align `~/.agents/skills` with full Claude set; `just skills-budget` | Mount/budget gap, not missing primitive | Med |

---

## What we're doing right

1. **Rejected `/review` router** — partition enforced, SkillRouter overlap avoided (ADR 2026-06-14)
2. **Retired repo-tools MCP** — 0 uses / 4,287 runs; vetoed rebuild
3. **Native-first gate** — `.claude/rules/native-patterns.md` decision flow
4. **`just orient`** — live map of repos/loops/hooks/MCP/skills
5. **Observe-before-promote** — gov.py shadow windows, hook ROI tracking

---

## Falsifiable hypotheses (pre-registered)

| ID | Hypothesis | Test |
|----|------------|------|
| H1 | Trigger+negative descriptions lift routing precision | Rewrite 10 terse skills; compare `/observe` before/after |
| H2 | Context budget binds before model capability | calibration-canary: full vs constrained MCP profile |
| H3 | Hook-enforced invariants beat rule-only for same category | agentlogs violation rate by category |
| H4 | Sessions with >30 visible tools show higher failure uplift | agentlogs cross-ref tool count × session flags |
| H5 | Self-contained skills route better than cross-referencing skills | Audit skill cross-refs vs routing failures |

---

## Related memos

- **Principles (14 ranked):** `research/2026-06-15-agent-surface-api-design-principles.md`
- **Vendor comparison:** `research/2026-06-15-agent-extensibility-surfaces.md`
- **Dev-loop meta-finding:** `research/agent-dev-loop-tooling-2026-06.md`
- **Review partition ADR:** `decisions/2026-06-14-review-dispatch-consolidation.md`

---

## What's uncertain

- Exact tool-count accuracy thresholds (30-tool cliff) — practitioner estimates, not controlled studies
- Whether MCP Resources actually reduce always-loaded pressure in our harness (untested locally)
- Cross-model skill routing divergence (Perplexity: Sonnet vs GPT differ materially)
- Optimal description length vs token economy for our 52-skill catalog
