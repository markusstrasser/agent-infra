---
title: Harness surface audit — genomics, personal, arc-agi (+ global skills budget)
date: 2026-07-24
tags: [harness, cruft, skills, mcp, opus-5, audit]
status: active
---

# Harness audit — genomics · personal · arc-agi · global layer

Operator ask: what agent tooling (subagents/rules/hooks/skills/MCP/plugins) do these
three repos *need*, and what metatooling cruft should be *deleted*. Run alongside the
Opus 5 adoption (`decisions/2026-07-24-claude-opus-5-default.md`).

Method: three parallel audit agents, each required to produce mechanism-level evidence
(agentlogs `tool_calls` counts, `git log` recency, referrer greps, symlink resolution) —
not file-existence vibes. Findings below were spot-verified by the parent where they
drive a deletion.

## Headline

**The Opus-5 "strip over-verification scaffolding" cleanup is a near-no-op here.** All
three repos scanned clean: their rule text is incident-dated and evidence-specific rather
than generic caution. The one "verify" cluster found (arc-agi
`teammate-dispatch-protocol.md:110-116`) is a *parent grading a subordinate's claim*,
which is principal-agent verification and stays correct under any model — categorically
distinct from an agent re-checking its own output. **Nothing to trim. Do not manufacture
trims here.**

The real finds are elsewhere: one live-wrong skill, two dangling symlinks, a
self-contradictory MCP config, a blown global skills budget, and a class of dead
metatooling whose only remaining consumer is its own test.

## Cross-cutting: the global skills budget now binds

`~/.claude/skills/` is a symlink farm — 49 skills, all resolving into `~/Projects/skills/`.
Every description loads in **every session of every project, plus every subagent spawn**.

| Measure | Value |
|---|---|
| Total description chars | **9,902** (≈2.5K tokens/session) |
| Ceiling named in `context-budget-principles.md` §7 | 8,000 |
| Last measured (2026-06-12) | 5,393 (67% of budget) |
| Contributed by skills never invoked in 60d | 4,727 (48%) |

§7 said "no lint until it binds (measure-before-enforcing)." It binds now — 124% of ceiling,
having nearly doubled in six weeks.

**Do not read "never invoked" as "delete."** Verified by mechanism, the 23 uninvoked skills
split three ways:

- **Real interface is a CLI/recipe, not the Skill tool** — `agent-browser` (installed
  2026-07-20, 4 days old), `cursor-agent`, `debug`, `diagnose`. Invocation goes through
  Bash or `just`, so Skill-tool count is the wrong instrument. Keep.
- **Domain skills already symlinked into their owning repo** — `life-science-research`
  (genomics), `data-acquisition`/`entity-management` (intel), `scientific-drawing`
  (agent-infra). The *global* symlink is pure rent: the repo that needs it already has its
  own. **This is the clean cut — narrows visibility, zero capability loss, reversible
  (`ln -s` restores it).**
- **Genuinely unclaimed** — `ttcw-rubric-evaluator`, `goals`, `interview-prompt`,
  `leverage`, `sweep`, `research-ops`, `oura-ring`, `neurokit2`, `census-data`,
  `google-workspace`, `manim-animations`, `review-animations`, `corpus`. Needs an owner
  decision; several are for repos that exist (`anim-workbench` has no `.claude/skills/`
  dir at all, so relocating the three animation skills means creating one).

Correction to a hypothesis worth recording: there is **no content duplication or drift
risk** between global and project-local skills — every one checked resolves to the same
`~/Projects/skills/` source. Project-local dirs are additional symlink farms, not forks.
The only real local directories are genuinely repo-owned skills (genomics `annotsv`,
`gget`, …; arc-agi `idea-miner`).

## The `agent-infra` MCP: registered in 9 repos, 0 protocol calls ever

| Signal | Value |
|---|---|
| MCP protocol calls, all projects | **0** across 4,561 runs (2026-06-23..2026-07-24) |
| Bash CLI invocations of `agent_infra_mcp.py` | 2 |
| Repos registering it in `.mcp.json` | **9** (genomics, intel, personal, arc-agi, evals, anki, people, anim-workbench, immigration-research) |
| Non-test referrers in agent-infra | none — only `mcp_contract_smoke.py` (its own smoke test) and `orphan_check.py` |

This is the shape of the already-vetoed **repo-tools MCP** (retired 2026-03-20 for zero
usage across 4,287 runs; `.claude/rules/vetoed-decisions.md`). Same failure, different name.

**Flagged contradiction, unresolved:** `search-retrieval-architecture.md:156` records that
on 2026-06-14 an agent claimed this MCP was retired for zero usage and was *corrected* —
"it is live … consumed by `just orient`." That correction does not hold today: `orient.py`
contains **zero** references to `agent_infra_mcp`. Either the consumption was removed since,
or the 2026-06-14 correction was wrong. Resolve before acting — this is exactly the kind of
prior-correction that should not be silently re-overturned.

Scope note: the *script* and the *MCP registration* are separable. Dropping the registration
from 9 `.mcp.json` files costs nothing if anyone still wants the CLI.

## Per-repo

### genomics — the one live safety hole

**FIXED this session: the commit-time guard chain was not installed.** `.git/hooks/pre-commit`
was **missing** and `post-commit` did not match the tracked wrapper. Verified by the parent with
the repo's own `scripts/git_hooks.py check` (not taken on the subagent's word), then restored via
`just install-hooks`; `check` now passes.

Mechanism, confirmed from the backed-up hook diff: the installed hooks were exactly `git lfs
install`'s set (post-checkout, post-commit, post-merge, pre-push), and the drifted `post-commit`
was the LFS wrapper with the tracked file's trailing
`exec .claude/hooks/run-git-post-commit.sh` line **dropped**. `git lfs install` clobbered the
chain. Pre-restore copy saved outside the repo.

Consequence while it was off: the pre-commit lint/guard chain (ruff, F821, hardcoded-sample-ID
checks, **protected-path / data-safety enforcement**) and the post-commit ownership-bypass audit
were not running on commits to this checkout. This is the backstop MEMORY.md records as the
enforcement that *survives Codex* (`commit-time-guard-backstop.md`) — silently off, with multiple
in-repo audit docs still describing it as actively enforcing.

**Class swept — genomics was the only instance.** Checked all repos: personal, arc-agi, hutter,
anim-workbench have no pre-commit hook *and* no tracked wrapper or `install-hooks` recipe, so they
never expected one (not a defect). `evals` looked like a hit but uses `core.hooksPath ->
scripts/githooks/` and is correctly configured — the `.git/hooks/pre-commit` proxy was the wrong
instrument there.

**GAP CLOSED (built, positive-controlled, NOT committed — see below):**
`.claude/hooks/session-start-git-hooks-drift.sh` — a 5th SessionStart hook of the existing
advisory shape that runs the read-only `git_hooks.py check` and surfaces drift with the
`just install-hooks` fix. Read-only, fail-open, ~75ms. Positive-controlled **both** ways before
wiring, per the arm-time pair rule: silent with zero output on a healthy checkout, and firing
with the real drift detail when `pre-commit` is hidden. Wired as the 5th entry in
`settings.json`; all 5 verified to resolve and be executable.

**Blocked from committing, deliberately not forced.** genomics' ownership guard refused the
commit: the checkout has a *live* peer session (`138a8e25`, launch-33665, started 18:25 UTC) and
`settings.json` is claimed by a third session (`019f45fe`). Its sanctioned remedy
(`just commit-mine`) cannot attribute a foreign session — "no ownership tracker for session
61053772." Per the acknowledge-guardrails rule this was surfaced rather than routed around. The
changes were **unstaged** (so a peer's bare `git commit` cannot sweep them under its own message
— the e2ab1ceb incident class) and preserved outside the repo as
`scratchpad/genomics-git-hooks-drift.patch` + a copy of the hook. Working tree still carries both.
Needs the owning session, or the operator, to land it.

Note the restored `.git/hooks/` chain is unaffected by this — `.git/hooks/` is not
version-controlled, so the actual safety fix is live now regardless of the commit.

**The gap this closed:** `scripts/git_hooks.py check` already
exists, is read-only, and just caught real drift — but nothing runs it automatically and nothing
signalled the drift. A `SessionStart` advisory hook would be the 5th of an existing shape
(`session-start-source-freshness.sh`, `-origin-staleness.sh`, `-worktree-base-staleness.sh`,
`-worktree-disk-bloat.sh`). `install-hooks` is documented nowhere agent-visible, so a fresh
checkout, a worktree promotion, or an incidental `git lfs install` drops the guard with no signal.

**BROKEN:** `CLAUDE.md:187` lists an `epistemics` skill as "invoke when relevant" — it exists in
none of the three places a skill can live. Probably a stale pointer to
`.claude/rules/epistemic-tiers.md` (a rule, which needs no invoking). Also `CLAUDE.md:149` claims
the always-loaded rule set is 3 files; it is 4.

**Deletion correctly NOT re-proposed — worth recording.** Six genomics skills (`annotsv`,
`clinpgx-database`, `data-transform`, `genomics-status`, `gget`, `vcfexpress`) show 0 Skill-tool
invocations across the full window. That exact cut was made and reversed **same-day, 4 minutes
apart**, on 2026-06-13 (`a9a77e301` → `db011b7c8`): "core deliberate-invoke domain capability.
Dormant != dead… the usage-only audit over-cut." Zero invocations six weeks later is not new
evidence against a decision whose whole point was that usage-only measurement is the wrong test
for deliberate-invoke tools. **The reversal is not recorded in `vetoed-decisions.md`** — which is
why it was nearly re-proposed a third time. That absence is the actionable item, not the skills.

Remaining findings from the original scope:

Always-loaded: **56,274 chars ≈ 14K tokens** (CLAUDE.md 24,814 + 4 unscoped rules).
`vetoed-decisions.md` alone is 22,686 chars — nearly the size of CLAUDE.md, and grown past
its own "Compressed 2026-06-14" marker. Content is not slop (every entry has a tripwire +
evidence pointer), but several entries are scoped to a single script or stage
(sbayesrc, DeepVariant GIAB thresholds, xtea_mei) and could be path-scoped rules instead of
paying always-loaded rent.

**Dead MCP registrations** (0 calls in genomics across 1,220 sessions / 1,563 runs, while
demonstrably live elsewhere — so this is not a data gap): `duckdb` (221 calls in intel),
`context7`, `parallel` (31 in personal), `brave-search`, `agent-infra`. Live and keep:
biomcp 109, research 97, exa 49, biomedical 46, scite 37, perplexity 4 (undocumented in
`mcp-usage.md`).

**Rule scoping — recommendation, not done.** `remote-ssh-ops.md` (1,414 chars) is the only
one of the 4 always-loaded rules that is domain-specific; its sibling
`hetzner-ephemeral-lifecycle.md` *is* scoped to `scripts/*sbayes*`, `*hetzner*`, `*sbrc*`.
Left unscoped deliberately: gotcha 2 (`pgrep -f` self-matching) generalizes beyond Hetzner,
both gotchas already cost time across two sessions each, and genomics is winding down so the
saving is ~350 tok/session against a real recurrence risk. This is a judgment call for the
owner, not a no-downside fix.

### personal — active, not dormant (hypothesis refuted)

3,376 commits, 1,167 in June, last commit today; currently an O-1A/EB-1A petition push plus
a personal-genome-catalog design effort. Its own harness contribution is lean: 7.2KB / ~1.8K tok.

**BROKEN — dangling symlinks (class-swept, exactly 2 in the whole repo):**
`.agents/skills/markitdown` and `.agents/skills/embedding-models` both point into
`~/Projects/personal-merge`, a repo that no longer exists. `.agents/` is gitignored, so this
is invisible to `git log`. `markitdown` has a live counterpart and can be repointed;
**`embedding-models` has no counterpart anywhere — that skill's content is gone, not
misplaced.** Codex sessions get zero content from both.

**DELETE:** `.claude/settings.json` permits `Bash(just guard-prepush)` — recipe removed,
zero referrers repo-wide, no `.git/hooks/pre-push`.

**GAP (the one well-evidenced gap in all three repos):** `admin/`, `life/`, `synthoria/`
have zero `.claude/rules|runbooks` coverage while `admin/immigration/` is the most actively
worked directory in the repo. Today's checkpoint records the same mistake three times in one
session — NeurIPS, TMLR, Frontiers eligibility each judged from blog/FAQ/guide prose instead
of the live submission form, each needing a correction commit (`d1652ad8`, `3feee96e`,
`8aca35df`). This is **not a new failure mode**: it is an uninstantiated case of
`epistemic_discipline` #8 face (b), "prose page read as the structured source." The fix is a
path-scoped pointer instantiating the existing principle for `admin/immigration/**`, not a
new freestanding rule.

### arc-agi — well-instrumented; zero gaps

Always-loaded 97,416 chars ≈ 24.4K tokens (CLAUDE.md 16,028 + 7 rules 81,388).
Zero GAPS met the bar, and the audit says so plainly rather than padding — the repo already
carries `dispatch_lint.py`, `verdict_lint.py`, `budget_audit.py`, `plumbing_audit.py`, each
built for a failure class it has actually had.

**FIXED this session** (`arc-agi@2ee6419d`): `.claude/skills/idea-miner/SKILL.md` — the
tracked file every fresh session and worktree reads — still instructed agents to use
`loop/levers/` and `just lever`, both retired in the 2026-06-19 `ideas/` migration
(`loop/levers/` absent from the tree; `just lever` absent from the justfile). The corrected
content existed only in the **gitignored** `.agents/` copy, so the fix had never reached a
clone. Promoted to the tracked path.

**BROKEN, not fixed:** `.claude/settings.local.json` lists `agent-infra`, `context7`,
`parallel` in **both** `enabledMcpjsonServers` and `disabledMcpjsonServers`. The 8-day-older
`.doctor-20260716.bak` has no disabled block, so this is a recent unreconciled edit. Needs
one owner decision on which list wins, after which the `.bak` can go.

**DELETE (HIGH):** the `overview-*` machinery (`overview-marker`, `overview-trigger.log`,
`overview.conf`, `overview-prompts/`, `overviews/`) — all dated Mar 24 in a repo that churns
hourly; `overview.conf` names `generate-overview.sh` and `sessionend-overview-trigger.sh` as
its consumers and **neither file exists anywhere in the repo**; its `OVERVIEW_SOURCE_DIRS=src/`
points at a directory CLAUDE.md says was deleted 2026-07-19. Also an orphaned post-merge
worktree + branch (`worktree-agent-ab67736e5ca66220c`, its work merged as `b39541ce`), and
`.claude/workflows/arc-portfolio-parallel.js` — a frozen transcript of a finished sprint whose
three hardcoded tasks are respectively shipped, never-landed (`agent/action_atlas.py` doesn't
exist), and one-shot.

**Watch item, not a trim:** `verified-fable-dispatch.md`'s self-firing wave triggers are
measured against historical models (20/20, 6/6 hit rates), not against Opus 5's own higher
delegation eagerness. Re-measure the load-bearing hit rate on the next 2-3 self-fired waves;
a drop from ~90-100% is the trigger to add a volume cap.

## What actually changes for an Opus-5 orchestrator

Nothing in the *rules* — see Headline. The changes are architectural, and they come from the
system card (`research/2026-07-24-claude-opus-5-release.md`, System card section):

1. **Self-verification loops are a liveness risk at long horizon**, not a token tax — both
   arms of a 24h autonomous campaign failed to deliver, one silent for 8 hours. Long
   autonomous runs need a *progress-artifact* watchdog, not just a process-liveness check:
   `ps -p` proves the process lives while the agent verifies in circles.
2. **Vendor-confirmed: the model relays subagent claims without verifying them.** arc-agi's
   grade-at-the-primary-artifact rule is the right response and should be treated as
   load-bearing rather than as verification bloat.
3. **Fan-out is validated** (10-agent team +3.1pp, 5.6-5.9× latency; per-agent git checkouts
   = our worktree isolation) — but delegation eagerness is up, so caps matter more than
   encouragement.

## Hook wiring: verified clean everywhere it was checked

arc-agi: every hook path in `.claude/settings.json` resolved individually (2 repo-local + 6
global under `~/Projects/skills/hooks/`) — all exist, all executable, `.codex/hooks.json` mirrors
correctly. genomics: same check run programmatically over `settings.json` + `settings.local.json`.
personal: all resolve. The only broken wiring found anywhere was genomics' *git* hooks (above) and
personal's two dangling `.agents/` symlinks — none in the Claude Code hook layer.

## Stale reference: `phenome` no longer exists

`~/Projects/phenome` is absent from disk with zero sessions in the retention window, yet
agent-infra's `CLAUDE.md` `<reference_data>` cross-project table and several MEMORY.md entries
still list it as a live project. Not resolved here: unclear whether it was deleted, renamed, or
folded into `substrate`/`genomics`, and CLAUDE.md is human-owned. Flagging rather than guessing —
and deliberately not deleting the `phenome-phenotype-ontology-roadmap` memory, since its content
may still be valid knowledge under a new home.

## EXECUTED 2026-07-24 (operator approved both)

### Skills relocation — budget back under ceiling

**9,902 → 7,390 chars** (ceiling 8,000). 13 domain skills moved out of the always-loaded
global farm into their owning repo, 36 remain global. Zero capability lost — each was
symlinked into its owner *before* the global link was dropped, and the script refused to drop
any global link whose local home didn't resolve. All 13 verified resolvable afterward.
Reversible per row: `ln -s ~/Projects/skills/<name> ~/.claude/skills/<name>`.

| Owner | Skills |
|---|---|
| genomics | life-science-research |
| intel | data-acquisition, dataset-register, entity-management |
| personal | oura-ring, neurokit2 |
| anim-workbench | manim-animations, review-animations |
| agent-infra | scientific-drawing, research-ops |
| immigration-research | census-data |
| corpus / publishing | corpus, ttcw-rubric-evaluator |

Deliberately **kept global**: `agent-browser` (4 days old), `cursor-agent`, `debug`,
`diagnose`, `verify-before`, `leverage`, `sweep`, `interview-prompt`, `goals`,
`google-workspace` — either their real interface is a CLI/recipe (so Skill-tool count is the
wrong instrument) or they're cross-cutting commands invokable from any repo.

Checked first: `setup-friend.sh` is one-time onboarding with a hardcoded 9-skill list, not a
running sync, so removals won't be silently restored. (Its list is itself stale — it wires to
the retired `meta` project.)

### agent-infra MCP registration dropped from all 9 repos

Script kept and untouched; only the never-invoked protocol registration removed. All 9
`.mcp.json` files re-validated as parseable afterward.

A formatting guard (re-dump of the *unmodified* file must be byte-identical to disk) blocked
`arc-agi` and `personal` — both would have taken a whole-file reformat, `personal` because it
uses compact inline arrays. Those two were done as surgical text edits instead.

**Committed:** arc-agi `15118a55`, personal `b042e737`, anim-workbench `23a7ac0`.
**No commit needed:** immigration-research, genomics, anki — `.mcp.json` is untracked/gitignored
there, so the change is purely local config.
**NOT committed, deliberately:** `evals`, `intel`, `people` — each already carried *pre-existing
uncommitted* edits from another session (evals + intel: a `corpus` server removal; people: an
added `EXA_API_KEY` env var). Committing `.mcp.json` there would have swept a peer's work under
this message — the e2ab1ceb incident class. The agent-infra removal is applied in their working
trees; the owning session should commit it alongside its own change.

## Not done / left open

- Every deletion touching 3+ projects (the 9-repo MCP registration, the global skills
  symlink narrowing) is held for operator sign-off per hard limit #4.
- 95 steward proposals and 28 stale control-plane questions were counted but not triaged.
- The `vetoed-decisions.md` omission of the 2026-06-13 genomics-skills reversal is unfixed
  (genomics' file, and the entry needs the owner's framing).

## Method note — a mistake worth recording

The parent twice read a stale file mtime as a dead subagent and acted on it: once dispatching a
redundant nudge, once redispatching a second agent onto scope the "stalled" agent had already
completed (stood down before it started). Both agents were alive and mid-write. This is the
`wakeup-cadence.md` rule — *a staleness signal LOCATES, exact-PID DECIDES* — applied to the wrong
instrument: for harness subagents there is no PID to check, so the correct probe is a status
`SendMessage`, which costs one turn and is unambiguous. Do that first, never infer death from
output mtime.
