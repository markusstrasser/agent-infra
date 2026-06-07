---
paths:
  - "research/**"
  - "decisions/**"
---

<!-- Gov-ID: rule:checkable-claims-carry-probes
goal: stop "breaking/blocked/unavailable" verdicts about CHECKABLE facts from being trusted second-hand and blocking real work
verifier: null
blast_radius: local
-->

# Checkable claims carry their probe

When an audit, research memo, or decision asserts a **checkable** fact — an API
surface exists/changed/was removed, a version "breaks", a file/flag/tool is
present/absent, a join field exists — include the **probe that measures it** inline
(the command + its output), not just the verdict.

A downstream consumer must **re-run the probe before acting on a "skip"/"blocked"
verdict**, and treat "breaking if used" as *scope the break* (probe the actual delta),
never *don't touch*.

**Why:** a checkable claim is the cheapest thing to verify and the most expensive to
get wrong second-hand. Distinct from semantic claims (judgment, taste) — those can't
be probed and this rule doesn't apply to them.

**Evidence (2026-06-08):** a dep-audit row said google-genai 2.x "breaks in the
Interactions API". A dep-bump agent read that, found `interactions` usage, and
**skipped** the upgrade as blocked. Direct probing of the installed 2.8 SDK showed the
break was narrow (response shape `outputs`→`steps`; call signatures compatible) — a
contained ~20-line fix, not a block. The unverified "breaks" verdict cost a real
capability upgrade until re-probed. Same session: a cross-model review's
cache-thread-safety flag was dismissed on an offline-tests-green basis; live execution
later confirmed it real. Cheap probe first; see [[live-execution-is-the-integration-verifier]].
