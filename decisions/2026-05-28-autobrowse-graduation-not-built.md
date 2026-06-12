---
id: 2026-05-28-autobrowse-graduation-not-built
concept: skill-graduation
repo: meta
decision_date: 2026-05-28
recorded_date: 2026-06-13
provenance: reconstructed
status: accepted
initial_leaning: build an Autobrowse-style mechanism that auto-distills a session trace into a reusable SKILL.md
relations:
  - type: depends_on
    target: 2026-05-31-skillopt-not-institutionalized
    note: SkillOpt assessment confirmed skill OPTIMIZATION is a separate question and does not reopen this veto
---

# 2026-05-28: Autobrowse-style skill-graduation mechanism not built — the workload it targets does not exist here

> Archived verbatim from `.claude/rules/vetoed-decisions.md` on 2026-06-13 when that
> always-loaded file was slimmed to verdict-lines (context-budget pass). The original plan +
> cross-model review lived at `.claude/plans/ef95e560-autobrowse-graduation-mechanism.md`
> (gitignored, ephemeral); this file is the durable home.

## Decision (full original text)

Do NOT build an Autobrowse-style skill-graduation mechanism (auto-distill a session trace into a reusable SKILL.md) — assessed 2026-05-28 via agentlogs Phase-0 demand audit. The browser-discovery workload it targets does not exist here (`browse` Playwright daemon: 7 calls/90d). High-recurrence web sources are all ALREADY graduated into real tooling, so recurrence is re-USE, not re-paid DISCOVERY: PMC/Nature/Springer/bioRxiv → research-mcp (`fetch_paper`/OpenAlex/`search_preprints`); SEC EDGAR (~49 session-hits) → intel `tools/edgar_*.py` wrapping the `edgartools` lib; press releases → intel handlers. The existing manual practice (recurring source → write a tool wrapping a dependency) beats markdown-skill graduation. Plan + cross-model review (Gemini 3.5 Flash + GPT-5.5): `.claude/plans/ef95e560-autobrowse-graduation-mechanism.md`.

## Revisit if

A genuinely browser-driven, undocumented-site workload recurs: ≥3 unsolved source/task pairs across ≥2 sessions each.
