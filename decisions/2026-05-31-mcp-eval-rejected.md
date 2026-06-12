---
id: 2026-05-31-mcp-eval-rejected
concept: mcp-server-ci
repo: meta
decision_date: 2026-05-31
recorded_date: 2026-06-13
provenance: reconstructed
status: accepted
initial_leaning: adopt mcp-eval as a dependency, per the scout note's "evaluate as dependency, LOW-MED risk" recommendation
---

# 2026-05-31: mcp-eval / mcpevals rejected as standing MCP-server CI — contract gap closed by in-process smoke instead

> Archived verbatim from `.claude/rules/vetoed-decisions.md` on 2026-06-13 when that
> always-loaded file was slimmed to verdict-lines (context-budget pass). The original
> working notes were in `.scratch/mcp-eval-evaluation-research.md` (gitignored, ephemeral);
> this file is the durable home.

## Decision (full original text)

Do NOT adopt `mcp-eval` / `mcpevals` (lastmile-ai) as standing MCP-server CI — assessed 2026-05-31 (task #8), re-grounding the scout note that recommended "evaluate as dependency." It fails due-diligence on every axis: **stale** (last commit 2025-11-19, ~6mo cold, 23★/23 open issues — the scout's "active, LOW-MED risk" was wrong), **LLM-in-loop is mandatory** (anthropic SDK core dep, default claude-3-5-sonnet, requires ANTHROPIC_API_KEY secret in CI, ~$0.05-0.50/server/run, NO deterministic/offline mode), and `pip install mcp-eval` is a **PyPI name-squat** (real pkg is `mcpevals`; the README's own install line is wrong). It also mis-fits the problem: our measured MCP pain is tool-call spin + token bloat (runtime behavior) and contract drift — neither needs a live model, and we have zero behavioral-regression incident history. The actual gap (the 11-project surface had no contract coverage) is closed at $0 by `scripts/mcp_contract_smoke.py` (in-process, no LLM/secrets/network, wired into `just smoke`; agent-infra@8bbd8d0).

## Alternatives considered

Also rejected as standing deps: `pytest-mcp-plugin` (0★, single-author) and Anthropic's `@modelcontextprotocol/conformance` (Node toolchain) — both heavier than the need for 2 small in-process servers.

## Revisit if

A specific server's agent-facing *behavior* (not contract) becomes a measured problem — then reconsider mcpevals only as an *occasional, manually-run* behavioral check, never standing CI.
