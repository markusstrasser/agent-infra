# Generalize the global "inventory before research" rule to cover first-party in-session search (not just subagent dispatch)

**Boundary:** shared (global `~/.claude/CLAUDE.md` `<subagent_usage>` — 3+ projects)

**Recommendation:** Yes, but **rule-only and minimal** — extend the existing
"Inventory before dispatch" line to also name *first-party* research-intent search
("before a research-intent Grep/Read/web search, check existing docs/memos/git-log
first"). **Do NOT build a new hook** for this surface. The dispatch case is already
hooked (`pretool-inventory-dispatch.py`, PreToolUse:Agent) because dispatch is a
discrete, detectable event. First-party Grep/Read fire constantly and "is *this*
search research-intent (docs-first matters) vs routine code navigation" is a
**semantic** distinction — a PreToolUse hook on Grep/Read would flood every session
(constitution: "Instructions work >0% for simple predicates. Don't over-hook";
"Semantic failures: unhookable").

**Dissent / risk:**
- recurrence-2 is **thin** for a global-rule edit, and the two occurrences are
  *different surfaces*: 1st (genomics 2163) was subagent **dispatch** — already
  covered; 2nd (phenome 351a2b7f) is **first-party search**. One could argue
  "only one occurrence of the *uncovered* surface → wait for recurrence-2 of
  *that* surface before touching a shared rule."
- The dispatch case explicitly learned **"rule alone was insufficient, needed a
  hook"** (2163 status line). A rule for first-party search may likewise underperform
  — but a hook isn't tractable here, so the rule is the best *available* lever, not a
  proven-sufficient one. Accept it as a cheap nudge, not a guarantee.
- Alternative: make it a **phenome-local** instruction instead of a global rule
  (contain blast radius until the pattern proves cross-project).

**Open question for you:** global rule generalization now, or phenome-local
instruction + wait for a 2nd first-party-surface occurrence before going global?

**Reversible?** Yes — a one-line rule edit, git-reverted in seconds. Cost if wrong:
minor token overhead from an occasionally-irrelevant reminder line (the same
low-cost failure mode every auto-loaded rule carries).

**Evidence:** `improvement-log.md:2161` (1st, dispatch, `[x]` hooked) ·
`improvement-log.md:3737` (2nd, first-party, this session) ·
`~/Projects/skills/hooks/pretool-inventory-dispatch.py` (the dispatch-only hook +
its own deferred-v2 note) · supervision audit `70590d8` / tick `b3ad971`.
Cross-lab `/critique model` not run (one-line reversible rule edit — low consequence);
available on request before sign-off if you want it pressure-tested.
