---
title: Git-native provenance/diff tooling + durable rot-resistant code anchors — adoption survey
date: 2026-06-15
status: complete
tags: [git, provenance, blame, anchors, scip, tree-sitter, diff, attribution]
question: (Axis 2) Which git-native metadata/diff/line-lineage tools sharpen blame→Session-ID attribution? (Axis 3) What is the LIGHTEST adoptable way to anchor a stored code reference so it survives edits/moves, on top of git, without a heavy index server?
context: agent-infra builds code↔conversation provenance on plain git — git blame --follow → commit → Session-ID trailer → agentlogs.db join (git_commits / v_session_commits exist). Reconstruct-on-demand, no new store. Deferred problem = rot-resistant durable anchors.
---

# Git-native tooling + durable code anchors — adoption survey

## TL;DR / verdict table

| Tool / primitive | Axis | Maturity | Bus factor | License | Last release | Verdict |
|---|---|---|---|---|---|---|
| `.git-blame-ignore-revs` + `--ignore-rev` | 2 | git core, stable | git project | GPL-2 | shipped (git ≥2.23) | **ADOPT — directly mitigates refactor-wash** |
| `git log -L` (line/range lineage) | 2 | git core, stable | git project | GPL-2 | shipped | **ADOPT — backs `--history` mode** |
| `git blame --reverse` | 2 | git core, stable | git project | GPL-2 | shipped | **ADOPT — "when did this line vanish/last-touched-forward"** |
| `git blame -C -C -C` / `-M` (copy/move detect) | 2 | git core, stable | git project | GPL-2 | shipped | **ADOPT (selective) — recovers cross-file attribution** |
| `git interpret-trailers` | 2 | git core, stable | git project | GPL-2 | shipped | **ADOPT — parse Session-ID robustly, stop regexing** |
| `--line-prefix` (diff) | 2 | git core, stable | git project | GPL-2 | shipped | INSPIRATION — niche, for annotated output only |
| git notes (refs/notes/*) | 2 | git core, stable | git project | GPL-2 | shipped | **INSPIRATION — know the pattern; don't adopt as store** |
| difftastic | 2 | mature, very active | 1 (Wilfred) healthy | MIT | v0.69.0 (2026-04-30) | INSPIRATION — human diff UX, not attribution |
| git-absorb | 2 | mature, active | multi-contrib | BSD-3 | v0.9.0 (2026-02-14) | SKIP (for provenance) — useful dev ergonomics, orthogonal |
| git-appraise | 2 | **dead** | abandoned | Apache-2 | v0.7 (2021) | SKIP — but its notes schema is the reference design |
| git-bug | 2 | active master, slow tags | 1 (MichaelMure) | GPL-3 | v0.10.1 tag (2025-05) | SKIP — too heavy for a metadata sidecar |
| fiberplane/drift | 3 | young, active | ~1, tiny (99★) | MIT | v0.10.0 (2026-05-08) | **INSPIRATION — steal the pattern, don't depend** |
| SCIP (scip-code/scip) | 3 | mature, community-gov | committee (was Sourcegraph) | Apache-2 | v0.7.1 (2026-04-14) | SKIP — needs an indexer per language + index server class |
| LSIF | 3 | **deprecated** | dead | — | superseded by SCIP | SKIP — fully removed from SCIP/Sourcegraph 2026 |
| tree-sitter normalized-AST fingerprint | 3 | mature lib | tree-sitter org | MIT | rolling | **ADOPT (the mechanism) — this is the lightest durable anchor** |
| comment-anchors / magic-anchors | 3 | maintenance-only | varies | MIT | — | SKIP — editor bookmarks, not rot-resistant |
| LSP symbol resolution | 3 | mature | per-language | varies | rolling | SKIP — needs a live server per language; too heavy |

---

## Axis 2 — git-native provenance / diff / line-lineage tooling

Our pipeline today: `git blame --follow` → commit SHA → `Session-ID:` trailer → join `git_commits`/`v_session_commits` → agentlogs.db for session/model. The wins below sharpen the *line→commit* hop (the weakest link, because refactors wash attribution) and harden the *commit→Session-ID* parse.

### 2a. `--ignore-rev` / `.git-blame-ignore-revs` — THE refactor-wash fix [SOURCE: git-scm docs, stable since git 2.23]

This is the single most relevant primitive for our stated limitation. `git blame --ignore-rev <sha>` and the repo-level `.git-blame-ignore-revs` file (one SHA per line) tell blame to **skip** specified commits when assigning lines — blame attributes the line to the *commit before* the ignored one and marks it with a `?` in porcelain. Purpose-built for "bulk reformat / rename / lint-sweep commits that touched every line but changed no logic."

- **Why it matters for us:** our blame→session join mis-attributes a line to a formatting/refactor commit whose Session-ID is a janitor session, not the session that wrote the logic. Maintaining a `.git-blame-ignore-revs` of known wash commits makes blame point back at the *substantive* session.
- **Config to make it automatic:** `git config blame.ignoreRevsFile .git-blame-ignore-revs`. Then plain `git blame` and our pipeline honor it with no flag plumbing.
- **Adoptable lever:** generate `.git-blame-ignore-revs` automatically. Candidates: commits matching `[fmt]`/`reformat`/`lint`/`style`/`ruff`/`prettier` in the subject, OR commits whose diff is ≥N lines but whose tree-sitter-normalized AST is unchanged (the drift fingerprint from Axis 3 doubles as a wash-detector). This is a `just` recipe + a cron, no new store.
- **Caveat (probe before trusting):** `--ignore-rev` only *re-attributes within history* — if the wash commit genuinely introduced the current text, blame still falls through to a plausible-but-not-guaranteed prior commit (the `?` marker flags low confidence). It does not reconstruct semantic authorship; it removes known-noise commits from the candidate set. Treat re-attributed lines as `[degraded confidence]` in the join, not ground truth.
- **VERDICT: ADOPT.** Highest-ROI Axis-2 item. Maintain an auto-generated ignore-revs file + set `blame.ignoreRevsFile`. Mark `?`-flagged lines as degraded in the session join.

### 2b. `git log -L` — line/range lineage backing `--history` mode [SOURCE: git-scm docs, stable]

`git log -L <start>,<end>:<file>` and `git log -L :<funcname>:<file>` walk the full history of a line range or function, following it through diffs (and the funcname form re-finds the function across moves via the same regex git uses for hunk headers). Output is the sequence of commits that touched that range, oldest→newest.

- **Why it matters:** this is the native engine for a `--history` line-lineage mode — instead of a single blame SHA you get the *ordered set* of commits (→ Session-IDs) that shaped a line. That converts "who last touched line 42" into "the 5 sessions that built line 42," which is what conversation-provenance actually wants.
- **Join shape:** pipe `git log -L` `--format=%H` → `git_commits` → `v_session_commits` → ordered session list. No new tables.
- **Caveat:** `-L` is slower than blame (walks history per range) and the `:funcname:` form depends on git's funcname regex, which is weak for some languages (Python OK via `*.py diff=python` in `.gitattributes`; set `diff=` drivers for our languages). Range form is robust; funcname form needs `.gitattributes` config first (cheap probe).
- **VERDICT: ADOPT** as the backing for `--history` mode. Configure `.gitattributes` diff drivers for our languages so the funcname form works.

### 2c. `git blame --reverse` — forward attribution [SOURCE: git-scm docs, stable]

`git blame --reverse START..END` answers the inverse question: "in which commit did this line *last* exist / when did it get deleted or changed." Useful for "this rule cites a line that's now gone — what's the last session that still had it" and for detecting anchor death (Axis 3 overlap).

- **VERDICT: ADOPT (selective)** — pairs with anchor staleness: when a stored `file:line` reference no longer resolves, `--reverse` finds the commit/session where it last lived, giving a "this anchor died in session X" diagnostic instead of a silent miss.

### 2d. `git blame -M -C` (move/copy detection) [SOURCE: git-scm docs, stable]

`-M` detects within-file moved lines; `-C` (repeatable up to `-C -C -C`) detects lines copied/moved *from other files in the same commit and across history*. This recovers attribution when code was relocated — a refactor moves a function to a new file and naïve blame attributes the whole block to the move commit; `-C -C -C` traces it to the original author/commit/session.

- **Why it matters:** complements `--ignore-rev`. Where ignore-rev removes noise commits, `-C` *recovers* the true source commit across file moves — directly attacking the "refactor wash" class from the other side.
- **Caveat:** `-C -C -C` is expensive (super-linear on large histories) — use it on-demand for a specific degraded line, not as the default blame in the hot path. Probe cost on our repos before wiring into any batch job.
- **VERDICT: ADOPT (selective / on-demand)** for re-attributing degraded lines, not as the default blame.

### 2e. `git interpret-trailers` — robust Session-ID parsing [SOURCE: git-scm docs, stable]

We currently (per CLAUDE.md) auto-append `Session-ID:` via a `prepare-commit-msg` hook and presumably parse it back with regex. `git interpret-trailers --parse` (and `git log --format='%(trailers:key=Session-ID,valueonly)'`) parses trailers per the documented trailer grammar — handles multi-line trailers, folding, and multiple trailers without ad-hoc regex.

- **Why it matters:** `%(trailers:key=...)` in `--format` lets the blame→commit→session join read Session-ID (and Evidence/Source/Affects) *directly in the git query*, no post-processing. Removes a regex failure surface (the GF-2 audit already recorded a hook false-positive from text-matching inside commit-message strings — trailer parsing is the structured fix).
- **VERDICT: ADOPT.** Replace any regex Session-ID extraction with `git log --format='%(trailers:key=Session-ID,valueonly)'`. Single-source the trailer key so producer hook and consumer query agree (constitution invariant principle 9).

### 2f. `--line-prefix` [SOURCE: git-scm docs]
Diff cosmetic flag (prefixes every output line). Only useful if we render annotated provenance diffs for humans. INSPIRATION, not load-bearing.

### 2g. git notes (refs/notes/*) — know it, don't adopt as store [SOURCE: git-scm docs + git-appraise design]

git notes attach mutable metadata to any object (commit/blob/tree) under `refs/notes/<ns>`, stored out-of-line so they don't change the commit SHA. The canonical production use is **git-appraise** (below), which stores entire code reviews as one-JSON-object-per-line notes merged with the `cat_sort_uniq` strategy.

- **Relevant gotchas (these are why it's INSPIRATION not ADOPT):**
  - Notes are **NOT fetched/pushed by default** — need explicit `refspec` config (`refs/notes/*:refs/notes/*`) or they silently don't propagate. Single-operator + local repos blunts this, but it's the classic notes footgun.
  - Notes **merge conflicts** are real on concurrent edits; `cat_sort_uniq`/`union` strategies exist but you must configure `notes.mergeStrategy`.
  - Rewriting history (rebase) can orphan notes unless `notes.rewriteRef` is set.
- **Why not adopt:** our design is reconstruct-on-demand from commit↔session join + agentlogs.db. Notes would be a *second mutable store* attached to objects — exactly the "no new store" we're avoiding. The session metadata already lives in trailers (immutable, in the commit) + agentlogs.db. Notes solve "annotate an object you can't rewrite," which we don't have.
- **VERDICT: INSPIRATION.** The git-appraise notes schema (JSON-per-line + cat_sort_uniq) is the reference design *if* we ever need mutable per-commit annotations that survive rebase. We don't, today.

### 2h. difftastic — structural diff [SOURCE: github.com/Wilfred/difftastic, crates.io]
v0.69.0 (2026-04-30), MIT, 25K★, ~182K downloads, single maintainer (Wilfred Hughes) but consistently shipping (~bi-monthly releases through 2026). Tree-sitter structural diff: shows *what* changed semantically, ignores reformatting.
- **For attribution:** does NOT improve blame→session (it's a display diff, not a line-mapper; it has no stable line-identity output we can join on). Its value is the *idea* — AST-normalized comparison — which we harvest in Axis 3, not the binary.
- **VERDICT: INSPIRATION** (the AST-normalization idea) / SKIP as a provenance dependency.

### 2i. git-absorb [SOURCE: github.com/tummychow/git-absorb, crates.io]
v0.9.0 (2026-02-14), BSD-3, 6K★, multi-contributor, healthy. Auto-generates `fixup!` commits targeting the right ancestor. Pure dev ergonomics (cleaner atomic commits → cleaner blame downstream, weakly).
- **VERDICT: SKIP for provenance.** Orthogonal to attribution. Could be a separate dev-quality-of-life adoption, but not this thread.

### 2j. git-appraise [SOURCE: github.com/google/git-appraise]
v0.7 (2021), Apache-2, last push 2023-08, ~3 Homebrew installs/30d. **Effectively dead.** Google-origin, abandoned.
- **VERDICT: SKIP the tool. ADOPT-AS-REFERENCE the design** (notes-as-metadata, JSON-per-line, cat_sort_uniq merge) — it's the most battle-tested example of the git-notes-metadata pattern, which informs the 2g verdict.

### 2k. git-bug [SOURCE: github.com/git-bug/git-bug, pkg.go.dev]
Last tagged v0.10.1 (2025-05-19) but master is active into 2026 (pseudo-versions through 2026-05-31), GPL-3, 10K★, dominated by one maintainer (MichaelMure). Stores issues as native git objects (custom DAG, not notes).
- **VERDICT: SKIP.** It's a full distributed issue tracker — far heavier than a metadata sidecar, and GPL-3 is a license consideration if anything links it. The *entity-in-git-objects* model is interesting but over-scoped for "attach session metadata," which trailers already do.

---

## Axis 3 — durable rot-resistant code anchors (the DEFERRED problem)

Goal: a stored reference (a rule citing `file:func`, a session note about a line) that survives edits, reformatting, renames, and file moves — **on top of git, no index server.** The field in mid-2026 has converged on a clear answer for the *light* end.

### The spectrum, lightest → heaviest

1. **Raw `file:line`** — rots on the next edit above the line. (What we'd do naïvely.)
2. **`file:line` pinned to a commit SHA** — stable but *frozen*: it points at history, not at the live code. Good for "what was here then," useless for "where is this now."
3. **Comment/magic anchors** (`// ANCHOR[id=x]`, codetags) — a literal marker string in the source. Survives line shifts because you grep for the marker, not the line number. BUT: requires editing the source to plant the marker, the marker itself can be deleted/moved by a refactor with no detection, and the mature implementations (StarlaneStudios comment-anchors, 238★, explicitly "no major changes planned") are **editor navigation bookmarks, not durable references**. SKIP — wrong tool: they help a human navigate, they don't make a *stored external reference* rot-resistant.
4. **Symbol-path anchoring** (`file#SymbolName`, qualified) — anchor to a declaration name, resolved by parsing. Survives line shifts and reformatting; survives renames *only if* you track an alias edge (Roslyn/Mimir model: rename = alias edge, not identity rewrite). Lightweight: needs a parser, not an index server. This is the SimplyLiz/CodeMCP "Doc Symbol Linking" + Mimir/KodeKlarity model.
5. **Tree-sitter normalized-AST fingerprint** (the drift model) — anchor = `path#Symbol` + a content hash of the symbol's *normalized* AST (node kinds + token text, no whitespace/position). Recompute on demand; if the hash differs, the anchored code *changed* (staleness signal); if `path#Symbol` no longer resolves, the anchor *died* (orphan signal). **No index server, no VCS history needed, works on uncommitted files.** ← lightest thing that actually answers "is this reference still valid."
6. **Content-addressed logic graph** (Aura VCS, "every function = content hash, the address is the identity") — heaviest: a shadow branch maintaining a full AST graph, identity anchors separate from body hashes, hash-algorithm versioning. This is a whole VCS layer. SKIP — this is the sibling `git-innovation-vcs-crdt` memo's territory; for our deferred problem it's massive over-build.
7. **SCIP / LSIF code-graph index** — a precise, cross-repo symbol index emitted by a per-language indexer and served from a store. SKIP (see below).

### The recommendation: tier 4+5, steal drift's pattern, don't depend on drift

**fiberplane/drift** [SOURCE: github.com/fiberplane/drift] is the closest existing implementation of exactly our deferred problem:
- Markdown (or any) file declares an anchor to `path` or `path#Symbol`.
- `drift link` stamps a `sig:` = **XxHash3 of the normalized tree-sitter AST** (node kinds + token text, no whitespace/position) into a `drift.lock` (TOML) at repo root.
- `drift check` recomputes and reports `ok` / `STALE (changed after doc)` / `STALE (file not found)`, with git blame for *who* changed it.
- Symbol-level anchors (`#AuthConfig`) narrow staleness to one declaration's subtree.
- Supported: TS, Python, Rust, Go, Zig, Java; unsupported languages fall back to raw content hash.
- **Crucially: CLI only, no server, no daemon, no index DB — just a lockfile + recompute.** Staleness detection needs zero VCS history.

But: **v0.10.0 (2026-05-08), MIT, written in Zig, 99 stars, bus factor ~1, very young.** Per our dependency-evaluation rule (solid dependency beats reimplementation; gate on maintenance burden + integration risk) — drift is **too immature and too thin a community to take as a hard dependency** in a load-bearing provenance path. A 99-star single-maintainer Zig CLI that could go dormant is integration risk we don't need.

**VERDICT: INSPIRATION — reimplement the pattern in ~50 lines on tree-sitter, which we already have access to.** The pattern is trivial and the mechanism (normalized-AST hash) is the genuinely portable part:

```
anchor = { path, symbol?, sig }
sig    = xxhash3( normalize_ast( parse(path)[symbol] ) )   # node-kinds + token-text only
resolve(anchor):
    if path missing                       -> DEAD  (use blame --reverse to find death commit/session)
    elif symbol not found in path         -> ORPHAN (renamed/removed; try alias/suffix match -> degraded)
    elif xxhash3(normalize_ast(...)) != sig -> STALE (code changed; still resolves, content drifted)
    else                                  -> OK
```

- Store anchors in the thing that owns the reference (a rule's frontmatter, a sqlite row) — **no new central store**, consistent with our design.
- `tree-sitter` parsers are MIT/Apache, mature, and the same family difftastic/drift use — vendored per language, no server.
- Tier-4 fallback (symbol-path + suffix match for renames) handles the rename case drift punts on, with a `degraded` confidence flag — mirrors the CodeMCP `exact`/`suffix`/`ambiguous`/`missing` confidence ladder.
- This **reuses the Axis-2 wash-detector**: a commit whose normalized-AST sig is unchanged but whose line diff is large IS a reformat/refactor wash → auto-add to `.git-blame-ignore-revs`. One mechanism, two payoffs.

### Why SKIP SCIP / LSIF / LSP for our case [SOURCE: sourcegraph.com/blog/the-future-of-scip, scip-code/scip]

- **SCIP** is alive and *more* credible than a year ago: as of 2026-03 Sourcegraph transitioned it to community governance under `scip-code/scip` (Core Steering Committee + SEP RFC process), Apache-2, v0.7.1 (2026-04-14), used by rust-analyzer, Mozilla Searchfox, Glean. It is the *right* answer if you want precise cross-repo go-to-def/find-refs at scale.
- **But it's the wrong weight class for us.** SCIP requires (a) a per-language indexer (scip-typescript, scip-python, rust-analyzer emit, etc.) run as a build step, and (b) something to *consume* the index — historically a Sourcegraph instance or the scip CLI. That's an index-pipeline + (effectively) a server. For "anchor a rule's citation so it doesn't rot," it's 100× the machinery of a normalized-AST hash. Our constitution's maintenance-not-effort gate (principle 8) kills it: standing indexer + index store = real ongoing drag.
- **LSIF is fully deprecated** — SCIP removed all LSIF references in v0.7.0 (2026), Sourcegraph's LSIF→SCIP migration is destructive/irreversible, support removed. Do not build on LSIF.
- **LSP symbol resolution** gives precise rename-aware resolution but needs a *live language server per language* in the path — heaviest runtime footprint of all. SKIP for a batch staleness check.

---

## Concrete adoption plan (no new store, CLI over git + sqlite + tree-sitter)

1. **[HIGH] `.git-blame-ignore-revs` + `blame.ignoreRevsFile`** — auto-generate from (a) subject-pattern wash commits and (b) AST-sig-unchanged-but-large-diff commits. Mark `?`-flagged blame lines as `degraded` in the session join. *Directly fixes the refactor-wash limitation.*
2. **[HIGH] Switch Session-ID extraction to `git log --format='%(trailers:key=Session-ID,valueonly)'`** — kills the regex parse surface; single-source the trailer key with the producer hook.
3. **[MED] `--history` mode via `git log -L`** — return the ordered set of sessions that shaped a line/function, not just the last. Configure `.gitattributes` diff drivers for our languages so `:funcname:` works.
4. **[MED] Durable anchors = drift's pattern, reimplemented** — `{path, symbol?, sig=xxhash3(normalized tree-sitter AST)}` stored in the referencing artifact; `resolve()` returns OK/STALE/ORPHAN/DEAD; ORPHAN tries suffix match → `degraded`. ~50 LOC + vendored tree-sitter parsers. No server.
5. **[LOW] On-demand `blame -C -C -C` and `blame --reverse`** for re-attributing/diagnosing degraded or dead anchors. Cost-probe before any batch use (super-linear).

## Pre-registered probes (per checkable-claims-carry-probes rule)
- Before wiring `:funcname:` `git log -L`: `git log -L :somefunc:somefile.py --format=%H | head` on a real repo file — confirm it follows the function (needs `.gitattributes diff=python`).
- Before trusting `--ignore-rev` re-attribution: pick a known reformat commit, `git blame --ignore-rev <sha> <file>` and confirm `?`-marked lines fall back to the substantive commit, not garbage.
- Before adopting any tree-sitter parser set: confirm parsers exist + are maintained for our actual languages (Python primary; check the others in use).

## Open questions / deferred
- Rename-following for anchors (tier-4 alias edges) is the one thing drift's pure-fingerprint model doesn't do — our suffix-match fallback is heuristic (`degraded`), not the Roslyn/Mimir alias-edge model. If anchor rename-survival becomes load-bearing, the alias-edge approach (record `new→old` on detected rename) is the next step up, still no server.
- Sibling thread: next-gen VCS identity (jj/Sapling/Pijul/Aura content-addressing) is `research/2026-06-15-git-innovation-vcs-crdt.md` — that's where the *heavy* content-addressed-logic option (Aura) belongs; this memo deliberately stays git-native + light.
