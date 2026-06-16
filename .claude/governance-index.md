# Governance Index — agent-infra (GENERATED — do not edit)

Compact single-source governance for curated injection + clash-detection.
Consumers LOAD this; never re-state it. Canonical: GOALS.md · CLAUDE.md <constitution> · .claude/rules/vetoed-decisions.md. Regen: `just governance-index`.

## GOALS (the telos)
- Mission: Maximize autonomous agent capability across all projects while maintaining epistemic integrity.
- Generative Principle: Maximize the rate at which agents become more autonomous, measured by declining supervision — AND maximize error correction per session across all pr…
- Success Metric: Per-regime, not one ratio (raw "maximize autonomy/consumption" maximands incentivize flooding the human or mislabeling hard work as taste):
- Self-Modification Boundaries: Full autonomy within invariants, with a gradient:
- Goal-Drift Detection: The system must actively detect when goals shift, not wait for the human to articulate them.
- Quality Standard: Recurring patterns (used/encountered 10+ times) must become architecture — not instructions, not snippets, not manual habits (the Raycast-snippet heu…

## PRINCIPLES
- P1 Architecture over instructions
- P2 Enforce by category
- P3 Measure before enforcing
- P4 Self-modification by reversibility + blast radius
- P5 Divergence budget by uncertainty × irreversibility
- P6 Phase-state artifacts for design decisions
- P7 Research is first-class
- P8 Filter by maintenance, not effort
- P9 Skills governance
- P10 Fail open, carve out exceptions
- P11 Recurring patterns become architecture
- P12 Cross-model review for non-trivial decisions
- P13 The git log is the learning
- P14 Breaking refactors by default
- P15 Provisional by construction (the dissent license)

## VETOED (do not re-propose)
- repo-tools MCP server — retired 2026-03-20, zero usage / 4,287 runs; CLI via Bash instead.
- Speculative shared-utility extraction — a TEST, not a ban (rewritten 2026-06-09): extract a shared package ONLY when the contract is proven common across ≥2 re…
- PyMC/ArviZ for telemetry — 2026-03-19; 200MB dep for 75 data points.
- Great Expectations — 2026-03-19; config overhead exceeds benefit at our dataset sizes.
- PageRank symbol graph for code nav — 2026-03-19; repos are 20-50 files, Read+Grep is faster.
- Whole-repo packing (repomix) as default context — 2026-03-19; for chat UIs, not tool-using agents.
- Retrying the same Gemini model after 503 — switch to GPT or Flash for the rest of the session; 4 wasted-retry incidents.
- Finding-triage SQLite DB — retired 2026-03-21; inline improvement-log replaced it.
- Knowledge-substrate MCP rebuild — retired 2026-03-24 (4 reads / 60 writes in 7d); correction tracing is now just propagate / just scan-corrections (2026-…
- Compatibility shims for planned replacements — migrate callers and delete the old path; wrappers/adapters/dual-paths only for an explicitly NAMED live external bounda…
- mcp-eval / mcpevals as standing MCP CI — 2026-05-31; stale project, mandatory LLM-in-loop, PyPI name-squat; the contract gap is closed at $0 by scripts/mcp_cont…
- Standing tool-hallucination metric / Arena-style leaderboard — 2026-06-04; signal is Claude-only measurable, actionable residue ~0, Arena's causal method needs a marketplace populati…
- Corpus-mediated cross-repo contradiction layer — 2026-06-01; the live phenome↔genomics bridge already serves cross-repo flow, 0 cross-repo contradictions ever observed.
