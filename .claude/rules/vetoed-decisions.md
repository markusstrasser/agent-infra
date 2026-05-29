# Vetoed Decisions

<!-- Gov-ID: rule:vetoed-decisions
goal: do not re-propose or re-implement retired decisions
verifier: evals/graders/governance/no_vetoed_rebuild.py
blast_radius: local
-->

Agents: check this list before proposing or re-implementing anything listed here.
These decisions were made deliberately and should not be re-derived.

- Do NOT build a repo-tools MCP server — retired 2026-03-20, zero usage across 4,287 runs. Use CLI scripts via Bash instead. Supporting evidence: Cao et al. 2026 retrieval paradox — adding retrieval alongside native shell tools hurts by 40.5%. (Orphan file `scripts/repo_tools_mcp.py` deleted 2026-05-29 — it was in zero current `.mcp.json`; veto now enforced by the `no_vetoed_rebuild` grader.)
- Do NOT extract shared utility libraries across projects — assessed 2026-03-19, maintenance > value at current scale. Projects share skills/hooks/rules, not Python imports.
- Do NOT use PyMC/ArviZ for telemetry — assessed 2026-03-19, 200MB dep for 75 data points. Use scipy/numpy directly.
- Do NOT add Great Expectations for data validation — assessed 2026-03-19, config overhead exceeds benefit for our dataset sizes.
- Do NOT build a PageRank symbol graph for code navigation — assessed 2026-03-19, repos are 20-50 files, Read+Grep is faster.
- Do NOT use whole-repo packing (repomix) as default context strategy — assessed 2026-03-19, for chat UIs not tool-using agents.
- Do NOT retry same Gemini model after 503 — switch to GPT or Flash for remaining session calls. 4 confirmed incidents of wasted retries.
- ~~Do NOT use codex-cli for trivial queries~~ — **SUPERSEDED 2026-04-21.** Original veto cited ~37K token overhead from 9 "bundled" MCP servers with no disable flag. Codex 0.121 closed issue #17588: MCP / plugin / app disable flags via `-c mcp_servers.<name>.enabled=false` or profile blocks are now honored. Current local config has 10 user-installed MCPs + 3 plugins, all disable-able individually. Path forward: build a `cli-lite` profile with all MCPs disabled and re-measure overhead; if <5K, use codex-cli freely. Until measured, prefer substantial tasks. See `dispatch-research` skill for usage patterns.
- Do NOT add finding-triage SQLite DB — retired 2026-03-21, inline improvement-log approach replaced it. (Orphan file `scripts/finding-triage.py` deleted 2026-05-29; `findings.db` was never created. Dormant consumers `fix-verify.py` / `propose-work.py` / `pattern-maintenance.py` remain — flagged for separate decommission. Veto now enforced by the `no_vetoed_rebuild` grader.)
- Do NOT rebuild knowledge substrate MCP — retired 2026-03-24, 4 reads / 60 writes in 7 days. Knowledge-index hook (100% coverage) solved the actual pain. Correction propagation via `scripts/propagate-correction.py` instead. Supporting evidence: Cao et al. retrieval paradox confirms that retrieval layers hurt when native navigation dominates.
- Do NOT preserve or invent compatibility shims for planned replacements by default — unless a live external boundary is explicitly named, migrate callers and delete the old path. Wrappers, adapters, dual-read/write, and transitional fallbacks are design noise, not safety.
- Do NOT build an Autobrowse-style skill-graduation mechanism (auto-distill a session trace into a reusable SKILL.md) — assessed 2026-05-28 via agentlogs Phase-0 demand audit. The browser-discovery workload it targets does not exist here (`browse` Playwright daemon: 7 calls/90d). High-recurrence web sources are all ALREADY graduated into real tooling, so recurrence is re-USE, not re-paid DISCOVERY: PMC/Nature/Springer/bioRxiv → research-mcp (`fetch_paper`/OpenAlex/`search_preprints`); SEC EDGAR (~49 session-hits) → intel `tools/edgar_*.py` wrapping the `edgartools` lib; press releases → intel handlers. The existing manual practice (recurring source → write a tool wrapping a dependency) beats markdown-skill graduation. Plan + cross-model review (Gemini 3.5 Flash + GPT-5.5): `.claude/plans/ef95e560-autobrowse-graduation-mechanism.md`. Reconsider only if a genuinely browser-driven, undocumented-site workload recurs (≥3 unsolved source/task pairs across ≥2 sessions each).
