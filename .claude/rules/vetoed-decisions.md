# Vetoed Decisions

<!-- Gov-ID: rule:vetoed-decisions
goal: do not re-propose or re-implement retired decisions
verifier: evals/graders/governance/no_vetoed_rebuild.py
blast_radius: local
-->

Check this list before proposing or re-implementing anything on it. One verdict-line per veto;
full reasoning + evidence live at the pointer — read it before arguing with a veto. Priors are
evaluated on the merits when context materially changes (see the 2026-06-09 rewrite below), but
the default is the veto stands.

- **repo-tools MCP server** — retired 2026-03-20, zero usage / 4,287 runs; CLI via Bash instead. Grader-enforced (`no_vetoed_rebuild`). → `decisions/2026-03-20-retire-repo-tools-mcp.md`
- **Speculative shared-utility extraction** — a TEST, not a ban (rewritten 2026-06-09): extract a shared package ONLY when the contract is proven common across ≥2 repos first; `corpus_core` is the bar. Still rejected: single-caller "might be reused" utils; abstractions over divergent logic (the 3 mutation gateways differ by design); CI/governance lints inside runtime libs. → `decisions/2026-06-09-shared-extraction-proven-common-test.md`
- **PyMC/ArviZ for telemetry** — 2026-03-19; 200MB dep for 75 data points. scipy/numpy directly.
- **Great Expectations** — 2026-03-19; config overhead exceeds benefit at our dataset sizes.
- **PageRank symbol graph for code nav** — 2026-03-19; repos are 20-50 files, Read+Grep is faster.
- **Whole-repo packing (repomix) as default context** — 2026-03-19; for chat UIs, not tool-using agents.
- **Retrying the same Gemini model after 503** — switch to GPT or Flash for the rest of the session; 4 wasted-retry incidents.
- ~~codex-cli for trivial queries~~ — SUPERSEDED 2026-04-21 (codex#17588 disable flags landed). Prefer substantial tasks until a `cli-lite` profile is measured <5K overhead. → `dispatch-research` skill.
- **Finding-triage SQLite DB** — retired 2026-03-21; inline improvement-log replaced it. Grader-enforced. NOTE: `propose-work.py` is NOT part of this veto — it's a live cross-project signal aggregator (consumer: research-ops `gather-cycle-state.sh`). → improvement-log entries.
- **Knowledge-substrate MCP rebuild** — retired 2026-03-24 (4 reads / 60 writes in 7d); correction tracing is now `just propagate` / `just scan-corrections` (2026-05-29 update, agent-infra@d239543). → `decisions/2026-03-17-shared-knowledge-substrate.md`
- **Compatibility shims for planned replacements** — migrate callers and delete the old path; wrappers/adapters/dual-paths only for an explicitly NAMED live external boundary. (= constitution principle 14.)
- **Autobrowse-style skill graduation** (auto-distill session trace → SKILL.md) — 2026-05-28; the browser-discovery workload doesn't exist here, recurrence is re-USE already graduated into real tools. Reconsider: ≥3 unsolved browser-driven source/task pairs across ≥2 sessions. → `decisions/2026-05-28-autobrowse-graduation-not-built.md`
- **mcp-eval / mcpevals as standing MCP CI** — 2026-05-31; stale project, mandatory LLM-in-loop, PyPI name-squat; the contract gap is closed at $0 by `scripts/mcp_contract_smoke.py` in `just smoke`. Reconsider only as an occasional manual behavioral check. → `decisions/2026-05-31-mcp-eval-rejected.md`
- **Scored session-quality regression gate** (composite quality_score × harness version) — retired 2026-06-01; built twice, never ran (0/3850 sessions). Build-then-undo is covered report-only (`buildthenundo.py` + `v_build_then_retire`). Reconsider on a measured report-only miss. → improvement-log [2026-06-01] [~] RETIRED.
- **Standing tool-hallucination metric / Arena-style leaderboard** — 2026-06-04; signal is Claude-only measurable, actionable residue ~0, Arena's causal method needs a marketplace population we don't have. Keep `scripts/tool_hallucination_probe.py` as occasional manual probe only. Reconsider: an MCP tool we own hallucinated against in ≥3 sessions after an affordance fix. → `research/2026-06-04-arena-agent-eval-transfer.md`
- **Corpus-mediated cross-repo contradiction layer** — 2026-06-01; the live phenome↔genomics bridge already serves cross-repo flow, 0 cross-repo contradictions ever observed. Resurrection: a real one observed → hook at the bridge sync boundary, never an embedding stack. → `decisions/2026-06-01-cross-repo-contradiction-layer-not-built.md`
