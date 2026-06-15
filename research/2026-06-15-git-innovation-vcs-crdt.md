---
title: Next-gen VCS identity models + CRDT-for-code — survey for code↔conversation provenance
date: 2026-06-15
status: complete
question: Do jj/Sapling/Pijul/Fossil or CRDT-for-code / AI-provenance systems offer a better
  granularity/identity model worth adopting or stealing for our git+sqlite provenance link?
context: agent-infra builds code↔conversation provenance on plain git — git blame --follow →
  commit → Session-ID trailer → agentlogs.db join. Reconstruct-on-demand, no new store.
  Deferred hard problem = rot-resistant durable code anchors that survive code movement.
recency: all currency facts verified against 2026-03..2026-06 sources; see provenance tags.
---

# Next-gen VCS + CRDT-for-code survey

## TL;DR / verdicts

| Tool | Category | License | Last release | Maturity | Bus factor | Verdict |
|---|---|---|---|---|---|---|
| **Jujutsu (jj)** | next-gen VCS | Apache-2.0 | v0.42.0 (2026-06-04) | high momentum, "experimental" self-label | low-med (Google-led, 1 founder) | **INSPIRATION** |
| **Sapling (sl)** | next-gen VCS | GPL-2.0 | 2026-05-22 | mature, Meta-internal | med (Meta, server not OSS) | **SKIP** |
| **Pijul** | patch-theory VCS | GPL-2.0 | active commits 2026 (no tagged rel.) | niche, slow | **very low (≈1 dev)** | **INSPIRATION** (idea only) |
| **Fossil** | all-in-one VCS | BSD-2 | 2.28 (2026-03-11) | very mature/stable | low (drh/SQLite team) | **SKIP** |
| **Git AI** (`git-ai-project/git-ai`) | AI line-provenance | Apache-2.0 | v1.5.8 (2026-06-14) | active, real traction | low-med (2 maintainers + 60 contrib) | **INSPIRATION → probe-ADOPT** |
| **agentdiff** (2 separate repos) | AI line-provenance | OSS (unverified license) | 2026-03 | early/prototype | very low (solo) | **SKIP** (inspiration) |
| **h5i** | git-sidecar + Yjs CRDT | OSS (unverified) | 2026-03 | prototype | very low (solo) | **SKIP** |
| **Causari / LineageLens / lineagelens** | proxy-based provenance | OSS (unverified) | 2026-03..04 | prototype | very low (solo) | **SKIP** |
| **Zed DeltaDB** | CRDT op-level VCS | "will open-source" (not yet) | not released (waitlist) | beta "in weeks" | med (funded co.) | **WATCH** |

**Headline:** Nothing here justifies abandoning the git+sqlite reconstruct-on-demand design.
The deferred hard problem (durable anchors that survive code movement) is **real and unsolved
in plain git** — and the most relevant prior art is NOT the next-gen VCSes (they don't solve
line-lineage better than `git blame`), it's **Git AI** (line-attribution that migrates across
rebase/squash/merge, stored in git notes) and **Zed DeltaDB** (delta-anchored references that
survive code movement — but unreleased). Steal the *anchor-migration* idea from Git AI; treat
DeltaDB as the design north-star to watch, not adopt.

---

## AXIS 1 — Next-gen VCS identity/granularity models

### The key correction (load-bearing — read before drawing conclusions)

The brief asks whether jj's "stable change-id" gives **better line-lineage / anchoring than
`git blame --follow`**. **It does not.** Two distinct concepts get conflated:

- **change-id** = a stable identity for a *whole commit/change* across rewrites (amend, rebase).
  It answers "is this the same logical change after I rebased it?" — NOT "where did this *line*
  go after the file was refactored." [SOURCE: jj-vcs.github.io/jj git-comparison; docs.jj-vcs.dev FAQ]
- **line lineage** in jj is still `jj file annotate`, jj's `git blame` equivalent, added only in
  v0.24 (Nov 2024). It is the same blame algorithm class — no patch-commutation, no line identity.
  [SOURCE: github.com/jj-vcs/jj README — "jj file annotate, equivalent to git blame"]

So jj's headline feature is orthogonal to our deferred problem. **Pijul** is the only one of the
four whose *data model* actually assigns durable identity to a line (see below).

### Jujutsu (jj) — INSPIRATION

- (a) **Line-lineage vs git blame:** no better. change-id is commit-level identity, not line-level.
  jj's real wins are workflow: working-copy-is-a-commit, no index, first-class conflicts, and an
  **operation log** (`jj op log`) — atomic undo of *any* operation including rebases. [SOURCE:
  jpk.io jj review 2026-06-08; blog.authon.dev 2026-04-15]
- (b) **Maturity/momentum:** real and accelerating. ~29.5K GitHub stars (29,468 at v0.42.0),
  monthly releases, v0.42.0 on 2026-06-04, recurring HN front-page (537 pts Apr 2026). Created by
  Martin von Zweigbergk; it is his **full-time project at Google** but **explicitly NOT a supported
  Google product** — community support only. Still self-labels "experimental… workflow gaps that
  make it unusable for your particular use." [SOURCE: github.com/jj-vcs/jj; besthub.dev 2026-06-06;
  kunalganglani.com 2026-03-23]
- **Bus factor: low-medium.** One founder, Google-employed; several Googlers assist but it has no
  corporate SLA. Survival depends on sustained personal/community investment.
- (c) **Git interop:** excellent — *this is its whole pitch.* jj uses the git on-disk format as a
  storage backend (via gitoxide); commits are real git commits; teammates keep using git on the
  same repo. **Caveat for us:** jj's *extra* metadata — including change-id and predecessors —
  is stored in `.jj/repo/store/extra/` (a StackedTable), **NOT in git**. Commits created by plain
  `git` get a bit-reversed-commit-id as change-id. [SOURCE: jj-vcs.dev architecture page]
  → So change-id is **not visible/durable through our plain-git path**; adopting it would mean
  routing writes through jj and treating git as read-only (the official recommendation), which is
  a workflow change, not a drop-in.
- **Verdict: INSPIRATION.** The *operation log* is the genuinely transferable idea — an atomic,
  undoable, append-only record of every repo mutation. We already approximate the "what changed +
  why" half via Session-ID trailers + agentlogs.db; jj's op-log is what a *native* version of that
  looks like. But jj solves a workflow problem (rebase safety), not our anchor-rot problem, and
  adopting it as a dependency means a write-path migration for zero line-lineage gain. Not adopt.

### Sapling (sl) — SKIP

- (a) Line-lineage: standard blame/annotate; no special line-identity model. Its differentiators
  are **scale** (operations scale with files-in-use, not repo size) and monorepo features like
  **directory branching** (2025-10) — irrelevant to single-machine N=1 provenance. [SOURCE:
  sapling-scm.com/docs; engineering.fb.com 2025-10-16]
- (b) Maturity: mature *inside Meta*; OSS client is real (6.8K stars, releases through 2026-05-22,
  270 contributors, last push 2026-06-15). But the scalable half — **Mononoke** (server) and
  **EdenFS** (virtual FS) — is explicitly **"not yet supported publicly."** [SOURCE:
  github.com/facebook/sapling README]
- **Bus factor: medium** (Meta-backed) but the OSS standalone story is the least-polished config.
- (c) Git interop: can clone git repos and work with GitHub, git-compatible. But there is no
  payoff here for our problem.
- **Verdict: SKIP.** Solves Meta-monorepo scale, not line anchoring. No reason to adopt or steal.

### Pijul — INSPIRATION (the idea, not the tool)

- (a) **This is the only model that genuinely beats git blame on line identity.** Pijul's theory
  of patches represents a file as a graph of byte-chunks where **each line/vertex is uniquely
  identified by (hash-of-the-change-that-introduced-it, position)**. A line **keeps its identity
  even when the change is applied in a totally different context**, and "the patch introducing
  every line can be looked up in time logarithmic in history" — i.e., blame is O(log h) and exact,
  not a heuristic backwards walk. Independent patches *commute* (apply in any order → same result
  + same version id). [SOURCE: pijul.org/manual/theory.html; pijul.org/model] **This is precisely
  the "durable anchor that survives code movement" primitive we deferred** — proven to exist.
- (b) **Maturity: niche and slow.** Self-hosted on nest.pijul.com, bootstrapped (self-hosting).
  Commits through 2026 (e.g. "edition 2024 migration" 2026-04-25; "libpijul→pijul-core rename"
  2026-02). No prominent tagged releases; ecosystem tiny. [SOURCE: nest.pijul.com/pijul/pijul]
- **Bus factor: very low (~1 primary author, Pierre-Étienne Meunier).** This is the dominant risk.
- (c) **Git interop: poor / effectively rip-and-replace.** Pijul is its own format and hosting
  (the Nest); no git-backend storage model like jj. Adopting Pijul = leaving git.
- **Verdict: INSPIRATION.** Steal the *concept* — vertex identity = (introducing-change-hash,
  position) — as the design for our durable anchor, NOT the tool. A content-addressed line-birth
  identity recorded at write-time (which is exactly what Git AI and DeltaDB do in practice, see
  Axis 4) is the git-native realization of Pijul's idea. Do not take Pijul as a dependency:
  bus-factor-1 + rip-and-replace + leaves the git ecosystem our whole design rests on.

### Fossil — SKIP

- (a) Line-lineage: a solid, fast `fossil annotate|blame` (10× perf improvement in 2.25, reverse
  annotation via `-o`), but algorithmically the same class as git blame — no line-identity model.
  [SOURCE: fossil-scm.org/home/help/blame; changes.wiki]
- (b) Maturity: **very mature and stable** — 2.28 released 2026-03-11, BSD-2, single self-contained
  binary, SQLite-backed, all-in-one (issues/wiki/forum/chat). [SOURCE: fossil-scm.org]
- **Bus factor: low** (drh / the SQLite team) but the project is rock-stable and unlikely to vanish.
- (c) Git interop: can mirror to GitHub but is fundamentally its own SQLite-based repo format —
  not a git frontend. Adopting = leaving git.
- **Verdict: SKIP.** Interesting that it stores everything in SQLite (philosophically aligned with
  our agentlogs.db join), but it offers nothing on the anchor-rot problem and is not git-native.

---

## AXIS 4 — CRDT-for-code / conversation-anchored systems

The 2025-2026 explosion here is **AI-code-provenance tooling**, almost all of it git-native and
aimed at exactly our use case ("which agent/model/prompt wrote this line, durably"). Most are
weeks-to-months-old solo prototypes. One has real traction.

### Zed DeltaDB — WATCH (not adoptable yet)

- **Open or proprietary?** Zed has *stated intent* to open-source DeltaDB under the same model as
  the editor (open-source + optional paid service), but it is **NOT released and NOT open yet** —
  early-access **waitlist only** at zed.dev/deltadb, beta "in a few weeks" from the 2026-06-11
  announcement (so late-Jun/Jul 2026). No source, no pricing, no confirmed OSS date. [SOURCE:
  zed.dev/blog/introducing-deltadb 2026-06-11; zed.dev/deltadb; techtimes.com 2026-06-13]
- **Model (this is the design north-star):** CRDT-based, operation-level VCS. Records every edit
  operation between commits and gives **each delta a stable, addressable identity**. References are
  **anchored to a delta, not a line number, so they survive as code moves underneath** — "character-
  level permalinks that survive any code transformation." Each agent message + the edit it produced
  are stored side-by-side; from any line jump to the conversation, from any message jump to the code.
  Conflict-free replicated worktrees → multi-agent concurrent edits. [SOURCE: zed.dev/blog/sequoia-
  backs-zed 2025-08-20; introducing-deltadb]
- **Maturity/bus factor:** Zed Industries, Boulder CO; raised >$42M incl. $32M Series B (Sequoia,
  Aug 2025). Medium bus factor (funded company, but pre-release product with admitted "painful
  false starts"). [SOURCE: techtimes.com 2026-06-13]
- **Verdict: WATCH.** This is *exactly* the conversation↔code-at-delta-granularity link we're
  building, done natively with the durable-anchor primitive we deferred. But it's unreleased,
  closed-for-now, IDE-coupled (Zed), and a heavy CRDT runtime — not a dependency we can take. Track
  the OSS release; if/when DeltaDB ships as a usable library, re-evaluate as the anchor layer. Until
  then it validates our problem statement and direction more than it offers code.

### Git AI (`git-ai-project/git-ai`) — INSPIRATION → probe-ADOPT candidate

**The single most relevant tool to our deferred problem.** This is the one to look at hard.

- **What it does:** open-source git extension; agents call `git-ai checkpoint` when they write code;
  on commit it stores **line-level** attribution (agent, model, prompt/session) in **git notes**
  under `refs/notes/ai`. `git ai blame` is a drop-in `git blame` overlaying AI authorship. Crucially
  it **moves and merges line attributions through rebase/squash/merge/reset/cherry-pick/stash** so
  attribution survives history rewrites — eventually-consistent, written 5-100ms post-operation.
  It also defines an **open standard** (Authorship Log v3.0.0, RFC-2119, `refs/notes/ai` namespace,
  addressed by commit SHA). [SOURCE: github.com/git-ai-project/git-ai README + specs/git_ai_standard_v3.0.0.md;
  usegitai.com/docs/cli/how-git-ai-works]
- **Maturity:** real and active — 2069 stars, **Apache-2.0**, **v1.5.8 released 2026-06-14**, 182
  releases, 60 contributors, last push 2026-06-14, Rust. Created 2025-07. [SOURCE:
  github.com/git-ai-project/git-ai]
- **Bus factor: low-medium.** Two named maintainers (Aidan Cunniffe — note: acunniffe, the Optic
  founder — and Sasha/svarlamov); 60 contributors incl. bot-assisted. A funded-startup smell (Git
  AI for Teams + Cloud), so commercial sustainability is plausible but it's young and 2-person-core.
- **The catch (verify before adopting):** the local CLI is free/OSS and preserves attribution
  across **local** rewrites. But **server-side** rewrites (GitHub "Squash and merge" / "Rebase and
  merge" done in the web UI, where the CLI isn't running) require **Git AI for Teams** OR their free
  open-source **CI Actions** to reconstruct attribution. [SOURCE: usegitai.com how-git-ai-works
  platform table; README] For our N=1 local-first design this matters less (we control the rewrite
  path locally), but it's the line where free ends.
- **Verdict: INSPIRATION now, probe-ADOPT candidate.** The *idea* to steal regardless: **store
  line attribution in `refs/notes/ai` and migrate it across history rewrites** — this is the
  git-native realization of Pijul's line-identity and the missing piece of our anchor-rot problem.
  Their attribution-migration logic is the hard part we deferred, already implemented + specced as
  an open standard. Two paths: (1) **steal the standard** — emit `refs/notes/ai`-shaped notes from
  our own hooks keyed to Session-ID, keeping our reconstruct-on-demand design; or (2) **probe Git AI
  as a dependency** per our dependency-first rule — a solid dependency beats reimplementation IF
  bus-factor/maturity clear the bar. **Do not adopt blind:** run the probe-the-primitive check —
  does its attribution actually survive a `git blame --follow`-class refactor (move a function
  across files) and a local rebase, on a real agent-infra commit? That's the one experiment that
  decides ADOPT vs steal-the-idea. Until that probe passes, INSPIRATION.

### The solo-prototype cluster — SKIP (mine for ideas only)

All git-native, all 2026, all very-low bus factor (single author, weeks old). None clear the
dependency bar (maintenance burden + integration risk dominate any novelty). Licenses mostly
unverified — treat as [UNVERIFIED] until checked.

- **agentdiff** — note **two unrelated repos** under the same name: `codeprakhar25/agentdiff`
  (ed25519-signed line attribution in git history, cross-agent) and `sunilmallya/agentdiff`
  (git-notes "blame for the *why*", per-line independent attribution surviving edits). The
  **ed25519-signing** idea (tamper-evident attribution, key registry in `refs/agentdiff/keys/`)
  is the one genuinely novel idea worth noting — relevant if provenance ever needs to be *evidence*,
  not just a convenience. [SOURCE: github.com/codeprakhar25/agentdiff,
  github.com/sunilmallya/agentdiff, both 2026-03] **SKIP** as dependency; signing idea = INSPIRATION.
- **h5i** (`Koukyosyumei/h5i`) — git sidecar storing provenance + test metrics + causal links in
  git notes (`refs/notes/commits`), plus **file-level Yjs (CRDT) sessions** for concurrent multi-
  agent edits, semantic/AST-level blame. The most architecturally ambitious of the solo tools
  (this is the actual "Yjs/Automerge-for-code" answer to the brief). [SOURCE: github.com/Koukyosyumei/h5i
  2026-03] **SKIP** (prototype, solo); the *AST-level blame* + git-notes-sidecar pattern = INSPIRATION.
- **Causari** (`croviatrust/causari`) — "intent-addressable code": a **proxy** (`re proxy`) +
  filesystem watcher that joins LLM traffic to file changes **by content match**, so provenance is
  observed not self-reported ("a fact, not a self-report"); `re trace`/`re why`/`re lens` give
  upstream/downstream causal cones; ships an MCP server. The **content-join-without-agent-
  cooperation** idea is clever and the **causal-cone** (trace a buggy line back to the *prompt*
  that caused it) is the most interesting query model. [SOURCE: github.com/croviatrust/causari]
  **SKIP** as dep; causal-cone + content-join = INSPIRATION.
- **LineageLens** (`karnati-praveen/lineagelens`) — self-hosted **proxy-based** capture across
  Claude Code / Codex / Gemini, correlates each edit with the next-turn tool_result to resolve
  applied/rejected/errored — honest about Cursor/Windsurf being un-proxyable (proprietary backends).
  [SOURCE: github.com/karnati-praveen/lineagelens 2026-04] **SKIP**; the applied-vs-rejected
  resolution discipline is a useful correctness note for any capture layer.

---

## What to actually do (recommendation)

1. **Keep the git+sqlite reconstruct-on-demand design.** Nothing surveyed beats it on our axes
   without a write-path migration (jj/Sapling/Pijul/Fossil) or a heavy unreleased runtime (DeltaDB).
2. **The deferred anchor-rot problem has a proven git-native shape: line attribution in
   `refs/notes/ai`-class notes, migrated across history rewrites** (Git AI) — the implemented,
   standardized version of Pijul's (introducing-change-hash, position) line identity.
3. **Run ONE probe before deciding ADOPT vs steal-the-idea (per dependency-first + probe-primitive
   rules):** on a real agent-infra repo, install Git AI, make an agent commit, then (a) move a
   function to another file and (b) local-rebase — does `git ai blame` still resolve the original
   line to the original session? If yes → ADOPT Git AI (or emit its standard from our hooks) as the
   durable-anchor layer joined to agentlogs.db via Session-ID. If no / too heavy → steal the
   `refs/notes/ai` schema and write our own minimal note-emitter from existing hooks.
4. **Watch Zed DeltaDB's OSS release** as the long-horizon north-star; do not wait on it.
5. **Park two ideas regardless of the above:** ed25519-signed attribution (agentdiff) for the day
   provenance must be tamper-evident evidence; causal-cone / content-join (Causari) for "trace a
   bug back to the prompt" — both fit a future of agentlogs.db, neither is build-now.

## Currency / skepticism notes

- Every "last release" + star count is from a 2026-03..2026-06 source (tagged inline). jj v0.42.0
  (2026-06-04), Git AI v1.5.8 (2026-06-14), Fossil 2.28 (2026-03-11), Sapling 2026-05-22, DeltaDB
  unreleased as of 2026-06-13 are all current.
- **Hype discount applied:** jj reviews are effusive ("best VCS since git") — discounted to the
  verifiable (stars, release cadence, Google-not-supported status, self-labeled experimental).
  The AI-provenance solo repos' READMEs are marketing — treated as [SOURCE] for *claimed*
  capability only; the probe in step 3 is the actual test, none of these were run.
- **Unverified:** exact OSS licenses of agentdiff/h5i/Causari/LineageLens (READMes didn't surface
  them in results) — marked [UNVERIFIED]; doesn't change the SKIP verdicts (bus factor decides those).
