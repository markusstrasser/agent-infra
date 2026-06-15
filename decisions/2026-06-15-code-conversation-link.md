---
id: 2026-06-15-code-conversation-link
concept: code-conversation-provenance
repo: agent-infra
decision_date: 2026-06-15
recorded_date: 2026-06-15
provenance: contemporaneous
status: accepted
initial_leaning: build the bidirectional link as a CLI on git + agentlogs.db (vs adopting DeltaDB)
relations: []
---

# 2026-06-15: Code↔conversation link — reconstruct-on-demand on git, not a new store

## Context
Zed's "Software Is Made Between Commits" (Sobo, 2026-06-11) pitches DeltaDB: a
proprietary CRDT delta store that anchors every agent conversation to the code it
produced, bidirectionally. The underlying problem is real and one we already
fight: the *why* behind code lives in the conversation, which drifts away from the
code. We already carry the seam — `Session-ID:` commit trailers + `agentlogs.db`.

The ask: from any **code line**, recover which **session / model / effort** wrote
it; and the reverse (session → the code it produced). Session attribution is the
must-have; model/effort is nice-to-have.

**Real decision axis** (not "just recipe vs MCP" — that's surface):
**reconstruct the link on demand from git + a read-only DB join, or materialize a
new store/index for it?** Everything else follows from that.

## Hidden assumptions (made explicit, then probed)
1. ~~Session-ID trailer joins on `sessions.session_uuid`~~ — **FALSE.** Probed: the
   trailer matches `sessions.vendor_session_id` (1 hit); `session_uuid` returns 0
   for CLI sessions. Speccing against the comment-blessed "canonical" column would
   have shipped a broken join. Join key = `vendor_session_id` (OR `session_uuid`
   for cross-vendor safety).
2. ~~Effort is recoverable~~ — **FALSE.** No effort column in `agentlogs.db`, no
   effort field in session jsonl. Only `runs.reasoning_tokens` (a noisy proxy).
   Not historically recoverable.
3. Model is recoverable — **TRUE.** `runs.model_resolved` well-populated (48 null /
   ~555); `sessions.model` = main-loop model (~15% null); 7 distinct models appear,
   so attribution is informative, not constant.
4. Blame is stable enough to skip an index — **TRUE** on a 138-file repo (sub-second),
   but **renames are frequent (63 in ~50 commits)** → blame MUST use `--follow`/`-C`.
5. Trailer coverage is high — **TRUE.** 500/500 of the last 500 commits carry it
   (auto-appended by the `prepare-commit-msg` hook).
6. agentlogs covers the history — **PARTIAL.** Indexed sessions start 2026-05-26.
   Blame on older code resolves to commit+trailer but **no session row** → degrade
   honestly, never fabricate.

## Alternatives considered
1. **Reconstruct-on-demand: CLI over `git blame` + read-only join to `agentlogs.db`** —
   no new state. code→session via blame→trailer→DB; session→code via
   `git log --grep`. *Chosen.*
2. **Adopt DeltaDB** — proprietary, hosted, vendor-locks the moat (the
   error-correction ledger). Contradicts vendor-neutral multi-vendor logging +
   git-as-moat. ~80% of the value is buildable on git we already own. *Rejected.*
3. **Materialize a code↔session index table** (line-ranges → sessions in SQLite) —
   a cache needing invalidation on every commit, for a query that is already
   sub-second. Maintenance burden, zero measured need. *Rejected (native-first).*
4. **New MCP scope in `agent_infra_mcp.py`** — that server is markdown-section
   keyword search; a git/SQL join is a category mismatch. Plus the **repo-tools MCP
   veto** (zero-usage, "CLI via Bash instead"). *Rejected for now;* reconsider only
   if measured CLI usage is high enough to justify an agent-callable surface.
5. **Per-keystroke / CRDT delta capture** (Zed's mechanism) — massive data exhaust
   for sub-commit granularity we don't need. Commit-granularity + session link
   answers the actual question. *Rejected.*
6. **Backfill effort from `reasoning_tokens`** — noisy proxy would mislabel lines;
   silent-proxy-as-truth violation. *Rejected* — report `effort: n/a` instead.

## Counterevidence sought
Searched for reasons reconstruct-on-demand fails at our scale and found none that
bind: (a) blame speed — sub-second per file at 138 files; (b) join reliability —
trailer coverage 100% on the recent window and `vendor_session_id` resolves; (c) a
consumer needing sub-commit granularity — none exists (no rule or tool stores a
line-precise anchor today). The one place an index *would* earn its keep — a
rot-resistant durable anchor for references stored in docs — is a **separate,
deferred** problem (see Deferred), not the query tool being decided here.

## Decision
Build the bidirectional link as **reconstruct-on-demand**, **reusing the existing
agentlogs git infra** — the `git_commits`/`git_commit_files` tables and the
`v_session_commits` view already join commit↔session on the trailer
(`src/agentlogs/git_import.py`, `migrations/001_initial.sql:373` + `002:25`). The only
genuinely-new code is the **blame bridge** (line→commit). **Surface: extend the
`agentlogs` CLI** (`agentlogs who` / `agentlogs whence`), not a new `scripts/` file —
agentlogs owns `git_commits`. Read-only, no new store, no materialized index, no MCP.

- **code→session** (`who`): `git blame --follow -L a,b <file>` → commit hash →
  look up in `git_commits` / `v_session_commits` (fallback: parse the trailer via
  `git show -s` when the hash predates the import `--since` window) → join `sessions`
  for `model` + token cost. Join key: **`vendor_session_id OR synthetic_session_key`**
  (matches the view; `synthetic_session_key` is needed for Gemini sessions).
- **`who --history`** (lineage, not last-touch): `git log -L a,b:<file>` → every
  session that ever touched the range, oldest→newest. The *honest* answer to "who
  originated this," because plain blame credits only the **last** toucher (see
  limitations). Added in response to cross-model critique.
- **session→code** (`whence`): **already ~free** — `SELECT … FROM v_session_commits
  WHERE vendor_session_id=:sid OR synthetic_session_key=:sid` (the view + the existing
  `queries/session_commits.sql`); add `git log -L` only for line-level detail.
- **Note:** `v_session_commits` does not expose `model` — either extend the view or
  join `sessions.model` in the CLI (small).

**Attribution delivered:** session ✓ · who (session/project/time) ✓ · model ✓
(session + run level) · **effort ✗ (report `n/a`)** · token cost ✓ (bonus).

## Invariants this must preserve
- **Read-only** on `agentlogs.db` (derived store; never write).
- **No new always-loaded context** — a script + recipe, never a `rules/` file.
- **Honest degradation** — pre-2026-05-26 or null model → `session: <sid>` /
  `model: unknown`; never fabricate (P8 fail-loud).
- **Join key `vendor_session_id OR synthetic_session_key`** (matches `v_session_commits`).

## Known limitations (surfaced, not hidden)
- **Blame = last-touch, not origin ("refactor wash")** *(cross-model, both reviewers)*:
  plain `git blame` credits whoever *last* touched a line. A later session that
  reformats / moves / wraps logic re-attributes it, masking the originating session.
  This is inherent to blame and **workflow-independent**. Mitigations: (1)
  **`.git-blame-ignore-revs` + `blame.ignoreRevsFile`** (git core ≥2.23) — auto-list
  wash commits (reformat/rename) so blame skips past them; re-attributed lines carry
  a `?` → treat as `degraded` in the join *(git-native fix found in research,
  `2026-06-15-git-native-tooling-anchors.md`)*; (2) `who --history` (`git log -L`)
  shows the full lineage; (3) default `who` output is labelled "last-authored," never
  "originated."
- **Trailer re-stamp is much narrower than the context-blind reviewers claimed**
  *(cursor, code-verified — corrects Gemini+GPT)*: the `prepare-commit-msg` hook is
  **idempotent** — `prepare-commit-msg-session-id.sh:13` exits if a `Session-ID:` is
  already present. So `--amend`/`rebase` that **preserve the message preserve the
  original trailer**: no re-stamp (Gemini and GPT both asserted re-stamping; the hook
  code refutes it — I folded it on faith, cursor caught it). The ONLY re-stamp path is
  a **fresh-message commit over rewritten content** (`reset --soft` recovery-squash),
  which collapses several sessions' lines into the recovery session's id — documented
  as having happened once (`improvement-log.md`). `--history` surfaces it.
- **Subagent mis-attribution**: a line written by a subagent (e.g. a fable-low
  executor) attributes to the session's *main-loop* model. Run-level
  `model_resolved` records subagent models but they are not line-mappable. line→model
  is accurate to "the session's main model," stated as such.
- **Effort unavailable** for historical lines; only fixable forward (opt-in: stamp
  effort into a trailer/session log — deferred until a consumer wants it).
- **History floor 2026-05-26** for DB enrichment; git half works to repo genesis.

## Deferred (the genuinely hard part — where DeltaDB's CRDT actually shines)
**Rot-resistant durable anchors** for references *stored* in docs/rules (the
`file:line` rot problem). The query tool does NOT need this — it blames current
state on demand. Defer until a measured consumer exists (a rule wanting a stable
anchor). **Researched answer** (`2026-06-15-git-native-tooling-anchors.md`): the
lightest approach is a **tree-sitter normalized-AST fingerprint** —
`{path, symbol?, sig=xxhash3(node-kinds + token-text, whitespace-stripped)}`,
recomputed on demand → OK/STALE/ORPHAN/DEAD, stored in the *referencing* artifact
(no new store, ~50 LOC; steal fiberplane/drift's pattern, not the dep). Git-native
alternative: **Git AI** (`refs/notes/ai`) — **PROBED 2026-06-15 (primary source
usegitai.com): forward-only + write-path** (agents must call `git ai checkpoint` via
hooks; no retroactive attribution for existing history, no trailer/session ingestion).
**Verdict: NOT adopted as substrate** — zero coverage of our 1540 existing commits (the
ask is about *existing* code) + a per-repo write obligation; our read-only blame+trailer
bridge serves it today. Steal the `refs/notes/ai` schema ONLY if a consumer ever needs
forward sub-commit attribution. **Not** CRDT.

## Evidence
Probes (2026-06-15, this session): `agentlogs.db` schema; trailer-column
disambiguation (`vendor_session_id` 1 / `session_uuid` 0 / `synthetic_session_key`
0 on commit ~200 back); 303 agent-infra sessions indexed 05-26→06-15; model spread
(opus-4-8 150, null 46, sonnet 42, …); run-level `model_resolved` 48 null/~555;
500/500 recent commits carry the trailer; 63 renames / 50 commits.

**Cross-model critique (Gemini 3 Flash + GPT-5.5, 2026-06-15):** both independently
**held** the architecture (no reversal), citing the same deciding fact as the probe —
negligible blame+join latency vs. the sync/maintenance tax of a second store. Both
independently surfaced the last-touch attribution gap → folded above + `--history`
mode added. Both confirmed the CLI is not redundant. **BUT both were context-blind**
(handed only the ADR text) and **both hallucinated** the amend/rebase re-stamp — which
I then folded on faith (FM5 amplification).

**Codebase-aware critique (cursor-agent / composer-2.5, repo read-access, 2026-06-15):**
ran *in the repo* and verified claims against code — strictly sharper than the
context-blind round. It (1) **refuted** the amend re-stamp by reading the idempotent
hook (`prepare-commit-msg-session-id.sh:13`); (2) found the **already-built**
`git_commits` + `v_session_commits` infra my inventory missed (I grepped `blame`, not
`session_commits`/`git_import` — a search-by-implementation-not-functionality miss);
(3) added `synthetic_session_key` to the join; (4) held the architecture, deciding
fact: a proven read-only join path already exists without a new store. All four
verified by me against source before folding. **Lesson: for codebase-specific review,
dispatch a repo-aware agent — context-blind API models confidently invent repo
internals.**

Zero architecture reversals across both rounds = the `/decide` success criterion
(resolved deeper, not overturned).

## Revisit if
- A rule/tool needs a line-precise durable anchor → build the deferred anchor layer.
- A consumer needs **forward** sub-commit/line attribution → revisit Git AI (or emit `refs/notes/ai`-shaped notes from our hooks keyed to Session-ID).
- Measured CLI usage is high enough to warrant an agent-callable MCP surface.
- We decide to capture effort going forward → add a forward-only stamp + extend `who`.
