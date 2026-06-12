---
id: 2026-06-09-shared-extraction-proven-common-test
concept: cross-project-infra-factoring
repo: meta
decision_date: 2026-06-09
recorded_date: 2026-06-13
provenance: reconstructed
status: accepted
initial_leaning: keep the 2026-03-19 blanket veto ("projects share skills/hooks/rules, not Python imports")
relations:
  - type: supersedes
    target: cross-project-infra-factoring
    note: the 2026-03-19 blanket "no shared utility libraries" assessment, originally recorded only as a vetoed-decisions.md entry
---

# 2026-06-09: Shared-package extraction is a test ("proven common across ≥2 repos"), not a ban

> Archived verbatim from `.claude/rules/vetoed-decisions.md` on 2026-06-13 when that
> always-loaded file was slimmed to verdict-lines (context-budget pass). This file is the
> durable home for the full reasoning; the rule file carries only the one-line test + pointer.

## Decision (full original text)

Do NOT **speculatively** extract shared utility libraries across projects — assessed 2026-03-19 (maintenance > value at current scale); re-derived on the merits 2026-06-09. The original framing ("Projects share skills/hooks/rules, **not Python imports**") is now **stale and must not be cited as a thought-terminating filter**: `corpus_core` is a shared Python package imported by intel/genomics/phenome/research-mcp, and it works. The rule is a **test, not a ban**: extract into a shared package ONLY when a contract is *proven common across ≥2 repos* — `corpus_core` is the bar (its outbox schema, `enqueue_relation` front door, and `drain` each earned their place by being implemented identically in 2+ repos *first*, then lifted). Still rejected: (a) speculative "might be reused" utilities with a single caller; (b) shared abstractions over *divergent* logic — the three mutation gateways look like twins but use different concurrency models (genomics concurrent writer-lock · intel atomic-rebuild-swap · phenome cert-emission), so one base class would be config-for-divergence; (c) CI/governance tooling buried in a runtime library — a lint banning `corpus_core.annotate` imports is dev tooling, so it stays a per-repo `lint_no_direct_corpus_writes.py` (now in all 3 repos), not a `corpus_core` module. Proven-common parts lift into `corpus_core` incrementally as each clears the bar — that *is* the live practice, not a violation of this veto.

## Revisit if

A proposed extraction passes the test: the contract is already implemented identically in ≥2 repos, the logic is genuinely convergent (not gateway-style superficial twins), and it is runtime code rather than CI/governance tooling.

## Supersedes

The 2026-03-19 blanket assessment ("maintenance > value at current scale; no shared Python imports"), which lived only as a vetoed-decisions.md entry. See also `~/.claude/projects/-Users-alien-Projects-agent-infra/memory/feedback_cross_project_consolidation.md` — priors are evaluated on the merits, not cited as dispositive filters.
