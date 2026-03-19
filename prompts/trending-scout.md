# Trending Scout

Reusable prompt template for scouting GitHub trending repos for useful patterns, tools, or dependencies.

Paste the prompt below into a Claude Code session in any project. Adjust `<scope>` to match what you're looking for.

---

## Prompt

```
<scope>
I work on agent infrastructure: orchestration, MCP servers, session analysis,
epistemic measurement, knowledge substrates, research pipelines. Python-heavy,
SQLite, FastMCP, Claude Code hooks/skills. See CLAUDE.md for full context.
</scope>

<task>
Scout GitHub trending for repos relevant to my systems. Produce a research
memo with adoption candidates ranked by value vs maintenance cost.
</task>

<phases>

## Phase 1 — Scrape trending

Fetch GitHub trending repos across these categories:
- https://github.com/trending (all languages, daily)
- https://github.com/trending/python?since=weekly
- https://github.com/trending/rust?since=weekly
- https://github.com/trending/typescript?since=weekly

Use Firecrawl, chrome automation, or WebFetch — whichever works. Extract for
each repo: name, stars/today, language, one-line description.

## Phase 2 — Filter

From the combined list, pick 5-10 repos that could plausibly improve my
systems (see <scope>). Filter criteria:
- Solves a problem I currently solve with custom code
- Offers a capability I don't have yet but could use
- Represents an architectural pattern worth stealing
- Skip: tutorials, awesome-lists, wrappers around services I already use

For each pick, write one sentence on why it's relevant.

## Phase 3 — Deep-dive

For each of the 5-10 picks:
1. Use context7 (resolve-library-id → query-docs) to read their documentation
2. Check their GitHub repo: README, architecture, API surface, open issues
3. Assess: maturity, bus factor, maintenance trajectory, license, API quality

Spend ~3-5 minutes per repo. Don't go deep on repos that turn out to be
immature or poorly maintained — note why and move on.

## Phase 4 — Brainstorm adoption

For each repo that survived Phase 3, brainstorm 3+ genuinely different ways
it could integrate with or improve our systems. Think beyond the obvious
first idea. Consider:
- Direct dependency (import it, use it)
- Pattern extraction (steal the idea, not the code)
- Replacement (swap out existing custom code)
- Composition (combine with something we already have)

## Phase 5 — Research current overlap

For each adoption candidate, check what we currently have that overlaps:
- Search this repo and sibling projects for similar functionality
- Check if we already evaluated this (grep improvement-log, research/)
- Note: "replaces X" or "complements X" or "novel capability"

## Phase 6 — Write memo

Write `research/trending-scout-YYYY-MM-DD.md` with:

### Header
- Date, categories scraped, total repos seen, picks evaluated

### Candidates (ranked by value - maintenance)
For each:
| Field | Content |
|-------|---------|
| Repo | name + link |
| What it does | one paragraph |
| Why relevant | specific to our systems |
| Integration path | which of the 4 modes from Phase 4 |
| Current overlap | what we already have |
| Maintenance cost | ongoing drag if adopted |
| Verdict | adopt / extract pattern / watch / skip |

### Patterns observed
Cross-cutting trends in what's trending. What does this week's trending
tell us about where tooling is heading?

### Null results
Categories or problem areas where nothing useful appeared. Useful for
knowing what the ecosystem still lacks.

## Phase 7 — Model review (optional)

If any candidate is rated "adopt" (direct dependency), run /model-review on
the memo before committing. Dependencies deserve adversarial review.

</phases>

<output>
Commit the memo. No implementation — this is a scouting report. Implementation
decisions come after reading the memo.
</output>
```

---

## Variations

**Narrow scope** — replace `<scope>` with a specific problem:
```
<scope>
I need a better way to do X. Currently using Y, which has problems A, B, C.
</scope>
```

**Specific language** — drop the multi-language scrape, focus on one:
```
Fetch only: https://github.com/trending/python?since=monthly
```

**Implementation mode** — add after Phase 7:
```
## Phase 8 — Implement top candidate

Pick the highest-ranked "adopt" candidate. Integrate it into the relevant
project with tests. Use a worktree agent if touching a different repo.
```
