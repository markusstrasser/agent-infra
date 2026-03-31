# Vetoed Decisions

Agents: check this list before proposing or re-implementing anything listed here.
These decisions were made deliberately and should not be re-derived.

- Do NOT build a repo-tools MCP server — retired 2026-03-20, zero usage across 4,287 runs. Use CLI scripts via Bash instead. Supporting evidence: Cao et al. 2026 retrieval paradox — adding retrieval alongside native shell tools hurts by 40.5%.
- Do NOT extract shared utility libraries across projects — assessed 2026-03-19, maintenance > value at current scale. Projects share skills/hooks/rules, not Python imports.
- Do NOT use PyMC/ArviZ for telemetry — assessed 2026-03-19, 200MB dep for 75 data points. Use scipy/numpy directly.
- Do NOT add Great Expectations for data validation — assessed 2026-03-19, config overhead exceeds benefit for our dataset sizes.
- Do NOT build a PageRank symbol graph for code navigation — assessed 2026-03-19, repos are 20-50 files, Read+Grep is faster.
- Do NOT use whole-repo packing (repomix) as default context strategy — assessed 2026-03-19, for chat UIs not tool-using agents.
- Do NOT retry same Gemini model after 503 — switch to GPT or Flash for remaining session calls. 4 confirmed incidents of wasted retries.
- Do NOT use codex-cli for trivial queries — ~37K token overhead per call from 9 MCP servers, no flag to disable. Viable for substantial tasks (audits, reviews, code analysis) where GPT-5.4 adds real value. See `/dispatch-research` for usage patterns.
- Do NOT add finding-triage SQLite DB — retired 2026-03-21, inline improvement-log approach replaced it.
- Do NOT rebuild knowledge substrate MCP — retired 2026-03-24, 4 reads / 60 writes in 7 days. Knowledge-index hook (100% coverage) solved the actual pain. Correction propagation via `scripts/propagate-correction.py` instead. Supporting evidence: Cao et al. retrieval paradox confirms that retrieval layers hurt when native navigation dominates.
