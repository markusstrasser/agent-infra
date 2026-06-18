---
title: Versioning a Living Plan Contract / Spec — Best Practices
date: 2026-06-18
status: complete
axis: versioning a living specification/contract that evolves as understanding changes
---

# Versioning a Living Plan Contract / Spec

**Scope (one axis):** how to version the agent-infra *plan contract* — the spec the
operator hands agents that EVOLVES over a project's life — so changes are stamped,
recorded, drift-detectable against the artifact it governs, and cheap (no platform).

**Sibling memos (read for the non-overlapping parts):**
- `2026-06-18-spec-formats-best-practices.md` — owns the **field set + format** of the
  contract (`exit_signal`, `scope_out`, `verifier_commands`, `regime`). This memo does
  NOT re-decide fields; it versions whatever fields that memo lands on.
- `bitemporal-append-only-correctness-2026-05-27.md` — owns append-only/supersedes
  correctness for a **DuckDB annotations table** (FK, anti-join, OCC). **The DELTA this
  memo addresses:** that is a *data store* at 10⁴–10⁶ rows with a MutationGateway; ours
  is a *single prose+structured document* edited a handful of times across a project.
  Same epistemic principle ("mark stale, never delete"), radically different mechanism —
  a Git-tracked file, not a table. I borrow the *invariants* (immutable supersedes
  pointer, append-only history, as-of reconstruction) and discard the *machinery*
  (no FK, no anti-join, no concurrency control — Git is the single writer).

---

## TL;DR — the recommended scheme (full detail in §6)

1. **Stamp** each contract with a 3-field header: `spec_version` (semver, meaning
   defined below), `status` (lifecycle enum), `governs_commit` (the artifact SHA the
   spec was last reconciled against).
2. **Record changes** with a *hybrid*: an append-only in-file `## Changelog` for the
   normal case (most edits), and a `supersedes:` pointer to a NEW file only when the
   spec is **replaced wholesale** (rare). Git is the bitemporal substrate underneath
   both — you never need to hand-roll `valid_from`/`asserted_at`.
3. **Detect drift** by making the contract's own `verifier_commands` the parity check
   (the field already exists), plus a cheap `governs_commit` staleness probe in a hook.
4. **Query provenance** via `git log` + a trailer (`Spec-Version:`), not a database.

The whole thing is three header fields, one in-file section, and one ~15-line hook.

---

## 1. How mature teams version requirements / specs (settled practice)

Two distinct, well-settled traditions — and they disagree on the unit of change.

### 1a. The ADR/RFC tradition: immutable records + status lifecycle + supersede-never-delete

This is the most directly transferable model, because an ADR — like our plan contract —
is a *decision document whose understanding evolves*. The consensus across AWS
Prescriptive Guidance, Decentraland's ADR process, and multiple practitioner writeups
[^adr-aws][^adr-277][^adr-itnext][^adr-ctaverna]:

- **Status lifecycle:** `proposed → accepted → (deprecated | superseded)`; some add
  `draft`/`review`/`rejected`. Decentraland added a distinct `Deprecated` state in
  ADR-277 precisely to separate "no longer relevant" from "replaced by a specific
  successor" [^adr-277].
- **Immutability after acceptance:** "ADRs should be treated as immutable documents
  after the team accepts or rejects them. Changes require creating a new ADR" [^adr-itnext].
- **Supersession is a typed pointer, both directions:** the old record gets
  `Superseded by ADR-XXXX`; the new one names what it replaces [^adr-aws][^adr-ctaverna].
- **Never delete — even rejected ones:** "even rejected decisions are valuable because
  they prevent future teams from reconsidering options that were already evaluated…
  An ADR is never deleted. Status changes. The record stays" [^adr-itnext]. This is
  the exact "mark stale, never delete → the history of belief change IS calibration
  data" principle in our `CLAUDE.md` epistemic_discipline §2.
- **RFC lifecycle** is the same shape on a longer arc: `proposed → accepted → done →
  archive (withdrawn/superseded)` [^rfc-sui-id].

**Note the tension our repo already lives in:** our decision-journal uses BOTH a
`supersedes` relation (new file replaces old) AND an append-only `## Revisions` section
(in-place dated note for "claim/interpretation/confidence changes — not wording")
per `.claude/rules/decision-journal.md`. That is exactly the hybrid §6 recommends,
and the rule that disambiguates them ("revise in place vs. supersede with a new file")
is the load-bearing convention to carry over to the plan contract.

### 1b. The API/OpenAPI tradition: semver + machine-diffed breaking-change gate

Specs that are *contracts another party consumes* (OpenAPI) version with **SemVer**,
and — critically — they **mechanize the version bump** [^zuplo][^oasdiff][^pb33f]:

- `oasdiff` / `pb33f/openapi-changes` diff two spec versions (or one spec over time),
  classify each change as breaking/non-breaking, post a report on the PR, and **gate
  CI** so a breaking change forces a major bump [^oasdiff][^pb33f].
- Rule of thumb: "define strict rules about when to increment versions… publish a
  changelog for every release with migration guides for major versions" [^zuplo].

**The transferable idea is NOT the tooling** (we are not shipping an API), it's the
*shape*: **a version number is only honest if something diffs the artifact and decides
the bump for you.** A hand-typed version drifts. For our plan contract this is cheap —
a header field + a Git diff classifier in a hook (§6).

---

## 2. Keeping the spec in sync with what it specifies (the hard part — and the live frontier gap)

This is where 2025–26 spec-driven-development (SDD) for AI agents is **actively
unsolved**, which is good news: our existing `verifier_commands` field is exactly the
missing piece.

### 2a. The SDD tools all promise "living spec, single source of truth" — and none enforce it

From Martin Fowler's hands-on review of Kiro, GitHub spec-kit, and Tessl [^fowler-sdd],
plus practitioner writeups [^augment-sot][^kinde]:

- **Kiro** (Amazon, Jul 2025): three files `requirements.md` / `design.md` /
  `tasks.md` as the project's source of truth; tasks trace back to requirement numbers
  (1.1, 1.2…). But Fowler found **specs are discarded after the feature is built** — no
  long-term maintenance, no versioning mechanism [^fowler-sdd]. (Kiro's marketing claims
  drift detection; Fowler's hands-on review could not find a concrete mechanism.)
- **GitHub spec-kit:** a branch per spec → "spec-first only, not spec-anchored over
  time"; the branch model treats specs as ephemeral change-requests, contradicting the
  "living artifact" pitch [^fowler-sdd].
- **Tessl** (beta): the only one treating specs as durable — marks generated code
  `// GENERATED FROM SPEC - DO NOT EDIT`, 1:1 spec↔file mapping, regenerate via
  `tessl build`. Still no drift detection or changelog [^fowler-sdd].

The blunt summary from a practitioner survey: **"The spec drives the first generation,
then drifts: its authority over the code afterward is conventional, not enforced.
Nothing automatically enforces spec-code parity"** [^codemyspec]. Spec-first buys
parallelism at the cost of high drift risk.

### 2b. What actually closes the loop: executable specs + CI parity gate

The only mechanism the field agrees *works* is making the spec **executable** so CI can
fail when code and spec disagree [^kinde][^codemyspec]:

- Write the spec's acceptance criteria as runnable checks (BDD/Gherkin is the common
  form); "a living document that evolves with the software" because the document IS the
  test [^kinde].
- "Automated contract testing at build/CI time enforces that implementations conform to
  the spec, with CI gates failing builds when implementation diverges" [^codemyspec].

**This is the punchline for us.** Our plan contract already carries `verifier_commands`
(per the sibling spec-formats memo). That field *is* the executable-spec mechanism the
SDD frontier is groping toward. We don't need to adopt Kiro/Tessl — we need to treat
`verifier_commands` as the parity oracle and add one staleness signal (`governs_commit`,
§6) so "the spec was last reconciled at SHA X; HEAD is 40 commits past X with no spec
touch" becomes a cheap, visible drift alarm.

### 2c. Drift detection, three cheap tiers (mirrors our `probe-primitive-first` rule)

| Tier | Check | Cost | What it catches |
|---|---|---|---|
| **Staleness** | `governs_commit` ≠ HEAD AND spec file untouched for N artifact-commits | ~0 (git, hook) | spec silently abandoned while code moves |
| **Behavioral** | run `verifier_commands` — do they still pass AND still describe the artifact? | medium | spec's acceptance criteria no longer match reality |
| **Semantic** | LLM/operator reads spec vs. diff — does intent still hold? | expensive | goal moved; only a human/judge can see it |

Run the cheapest first; a higher tier failing does not imply a lower one failed (our
`probe-primitive-first.md`). Only the staleness tier should be a standing hook; the
other two are on-demand.

---

## 3. Append-only / bitemporal for belief-evolution — what to keep, what to drop

Our `bitemporal-append-only-correctness-2026-05-27.md` proves the supersedes-chain model
correct for a DuckDB table. **For a single Git-tracked document, Git already gives you
the bitemporal substrate for free** — so import the principles, not the machinery:

| Bitemporal concept (table model) | Document-contract equivalent | Mechanism |
|---|---|---|
| `asserted_at` (transaction time) | when the edit was committed | `git log` author/commit date — free |
| `valid_from` (informational valid time) | when the change took effect for the project | the `## Changelog` date line |
| `supersedes_annotation_id` (immutable backptr) | `supersedes:` front-matter pointer to prior file | only for wholesale replacement |
| `NOT EXISTS` anti-join for "current" | `git show HEAD:plan.md` | the working file IS current |
| as-of-T reconstruction | `git show <sha>:plan.md` / `git log -L` | free, exact |
| append-only enforcement (MutationGateway) | append-only `## Changelog`; never rewrite history | convention + commit-msg trailer |
| concurrency / OCC (`UNIQUE` partial index) | **not needed** — Git merge is the single serialization point; the operator is effectively single-writer | n/a |

**The two genuinely load-bearing invariants to carry over** (the ones the bitemporal
memo proved matter):
1. **Immutable supersedes pointer** — set once at creation, never rewritten (the memo's
   §1 cycle-impossibility argument). For files this means: when you supersede, you write
   a NEW file with `supersedes: <old>`; you never repoint an existing one.
2. **Topological / chronological order of the history** (the memo's §7 replay
   invariant). For an in-file changelog this is automatic — append at the bottom (or
   top) in commit order; `git log` is the authoritative order if the in-file dates ever
   collide.

**What to drop:** FK constraints, anti-join performance tuning, the partial UNIQUE
index, materialized-current-state, replay 2-pass concerns. All of those exist because a
DB has many concurrent rows and writers. A document has one writer (the operator,
serialized by Git) and "current" is just `HEAD`. Re-implementing them would be the exact
over-build our constitution Principle 8 / Pre-Build #3 warns against — depth that adds
no correctness because Git already guarantees it.

---

## 4. Provenance: who / why / when changed the spec, and how it's queried

The mature practice (PRD "Change History" sections [^atlassian-prd], ADR records,
GitOps "Git as single source of truth" [^xops-git]) converges on: **provenance lives
in the change record, not a separate system.** Two layers, both free:

- **In-file (`## Changelog`):** one line per substantive change —
  `YYYY-MM-DD — vX.Y — <what changed, directionally> — <why / what evidence moved it>`.
  This is the human-readable belief-evolution timeline; it doubles as the calibration
  record ("we thought scope was X, learned Y, narrowed it"). Matches the PRD
  Change-History consensus: "who changed it, when, and what they changed" [^atlassian-prd].
- **In Git (the audit substrate):** author, exact timestamp, and full diff come from
  `git log`/`git blame` for free — never duplicate them into the file. Add a
  `Spec-Version: X.Y` commit trailer so provenance is *queryable*:
  `git log --grep '^Spec-Version' -- <plan-path>` reconstructs the version history with
  authors and reasons. This mirrors our existing repo conventions (the auto-appended
  `Session-ID:` trailer; the `decisions/` "commit body names the concept affected"
  rule in `.claude/rules/commit-conventions.md`) — so it adds zero new machinery, just
  one trailer name.

**Why-not-a-database:** our repo already vetoed standing knowledge-substrate/finding-DB
rebuilds (`vetoed-decisions.md`) on a usage basis. Git + trailers is the `native-first`
answer (`native-patterns.md`: "History/provenance annotation → git trailers, notes,
blame — don't build a custom session tracker DB").

---

## 5. What NOT to do (alternatives considered and rejected)

| Rejected | Why |
|---|---|
| **A versioning platform / SDD IDE (Kiro/Tessl) for the contract** | Heavy; Fowler shows they don't even solve versioning/drift yet [^fowler-sdd]; we'd import a dependency to get less than `git + a header + verifier_commands` gives us. Violates Pre-Build #1/#3. |
| **A bitemporal DB / table for the contract** | Correct for the annotations store; massive over-build for one document. Git is already bitemporal-for-files. (§3.) |
| **Monotonic integer version only (no semver)** | Loses the breaking/non-breaking signal that is the whole point of versioning a *contract* (does this change invalidate work agents already did under the old spec?). |
| **Supersede-with-new-file for every edit** (pure ADR immutability) | Too heavy for a doc edited many times; you'd drown in files for one-line scope tweaks. Reserve supersession for wholesale replacement; use the in-file changelog for the common case. This is precisely why our decision-journal kept BOTH mechanisms. |
| **In-place edit with no record** (pure "living doc") | The SDD failure mode — drift with no audit trail; destroys the calibration data. |
| **Hand-typed version with no diff gate** | Drifts immediately; the OpenAPI tradition exists because manual version bumps are unreliable [^oasdiff]. |

---

## 6. CONCRETE versioning scheme for the agent-infra plan contract

A plan contract is a Git-tracked file (e.g. `.claude/plans/<slug>.plan.md` or wherever
the spec-formats memo lands it). Add exactly this.

### 6a. Version stamp (front-matter, 3 fields on top of the format memo's fields)

```yaml
spec_version: 2.1          # SemVer, meaning defined below
status: accepted           # draft | accepted | superseded | abandoned
governs_commit: a1b2c3d    # artifact SHA this spec was last reconciled against
supersedes: null           # path to prior plan file, ONLY if this replaced one wholesale
```

**SemVer meaning for a plan contract** (the bump rule that makes the number honest):
- **MAJOR** — a change that **invalidates work agents did under the prior spec**
  (scope_out → scope_in, a verifier_command changed/removed, exit_signal redefined).
  Agents must re-check completed work against the new contract.
- **MINOR** — additive, non-invalidating (new scope item, new verifier added, clarified
  constraint). Prior work stays valid.
- **PATCH** — wording/typo/reordering; no semantic change. (Maps to "revise in place,
  not supersede" — the decision-journal `## Revisions` rule.)

### 6b. Recording changes — the hybrid (changelog default, supersede rare)

**Default (≈95% of edits): append to an in-file `## Changelog`.** Never rewrite prior
lines (append-only; that history IS the calibration data).

```markdown
## Changelog
- 2026-06-18 — v2.1 — MINOR — added `bench/regress.sh` to verifier_commands — caught a
  perf regression class the old set missed (evidence: run 4f2a).
- 2026-06-15 — v2.0 — MAJOR — moved "multi-tenant" from scope_out to scope_in — operator
  re-scoped after customer signal; agents must re-verify auth work against tenancy.
- 2026-06-12 — v1.0 — accepted — initial contract.
```

**Wholesale replacement (rare): write a NEW file** with `supersedes: <old-path>`, set the
old file's `status: superseded`, and add a final changelog line pointing forward. Use
this only when the plan is conceptually a different plan (the ADR immutable-supersession
case), not for incremental evolution.

**Status transitions:** `draft → accepted` (operator signs off) → `superseded` (a
successor file exists) or `abandoned` (dropped, no successor — the Decentraland
"deprecated ≠ superseded" distinction [^adr-277]). Never delete a superseded/abandoned
plan file — `git mv` it to an `archive/` dir if it clutters, but keep it in history.

### 6c. Detecting drift from the artifact it governs (cheap, no platform)

Two signals, both ~free:

1. **Staleness hook (standing, ~15 lines).** On a relevant event (e.g. PreToolUse on
   plan-governed paths, or a `just plan-drift` recipe), compare `governs_commit` to the
   count of artifact commits since:

   ```bash
   # pseudocode for the hook / recipe
   gc=$(yq '.governs_commit' "$plan")
   behind=$(git rev-list --count "$gc"..HEAD -- "$artifact_paths")
   spec_touched=$(git rev-list --count "$gc"..HEAD -- "$plan")
   # WARN if the artifact moved a lot but the spec never moved with it
   [ "$behind" -gt "$THRESH" ] && [ "$spec_touched" -eq 0 ] && echo "DRIFT: plan governs $gc, artifact +$behind commits, spec untouched"
   ```

   This is the `governs_commit` analogue of the OpenAPI "diff the spec over time"
   gate [^oasdiff] — but instead of diffing the spec, it flags *the spec failing to
   move while its artifact does*. Reconciling = re-read the plan against the diff, bump
   `governs_commit` to HEAD (a PATCH if nothing semantic changed — which is itself the
   record that "we checked and the spec still holds").

2. **Behavioral parity (on-demand).** Run the contract's own `verifier_commands`. If
   they pass AND still describe the artifact, the spec is live. This reuses the field
   the format memo already defines — the executable-spec parity gate [^kinde][^codemyspec]
   the SDD tools lack. Wire it into `just` rather than a standing hook (don't pay the
   cost every edit).

### 6d. Provenance / querying (free)

- One commit trailer: `Spec-Version: 2.1` on any commit that touches the plan.
- Query: `git log --grep '^Spec-Version' --format='%ad %an %s' -- <plan-path>` → the
  full version history with who/when/why. `git show <sha>:<plan-path>` → the spec
  as-of any point. `git log -L` if you want a single field's lineage.

### 6e. Why this is cheap and right

- **No platform, no DB, no dependency.** Three front-matter fields, one `## Changelog`
  section, one commit trailer, one ~15-line staleness probe, one `just` recipe that
  shells `verifier_commands`. Git is the bitemporal store, the audit log, and the
  as-of engine.
- **It reuses what exists:** `verifier_commands` (format memo) becomes the parity
  oracle; the decision-journal's revise-vs-supersede rule transfers verbatim; the
  `Session-ID:`-style trailer pattern extends to `Spec-Version:`; `git log`/`blame`
  is the provenance query (native-first).
- **It honors the epistemic principle:** append-only changelog + never-delete
  superseded plans = the belief-evolution / calibration record our constitution wants,
  without re-implementing the table-grade machinery the bitemporal memo correctly
  reserves for the annotations store.

---

## Sources

[^adr-aws]: AWS Prescriptive Guidance, "ADR process." https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html — Grade A (vendor reference).
[^adr-277]: Decentraland, "ADR-277: Introducing the Deprecated State for ADRs." https://adr.decentraland.org/adr/ADR-277 — Grade B (real ADR practice; the deprecated≠superseded distinction).
[^adr-itnext]: Lukas Niessen, "How to Make Architecture Decisions: RFCs, ADRs," ITNEXT. https://itnext.io/how-to-make-architecture-decisions-rfcs-adrs-and-getting-everyone-aligned-ab82e5384d2f — Grade B (practitioner; immutability + never-delete quotes).
[^adr-ctaverna]: "A practical overview on Architecture Decision Records." https://ctaverna.github.io/adr/ — Grade B.
[^rfc-sui-id]: sui-id RFC lifecycle policy (018). https://github.com/nabbisen/sui-id/blob/main/rfcs/done/018-rfc-lifecycle-policy.md — Grade B (concrete proposed→accepted→done→archive states).
[^zuplo]: Zuplo, "Semantic Versioning for APIs," 2025-04-24. https://zuplo.com/blog/2025/04/24/semantic-api-versioning — Grade B (vendor; SemVer-for-contracts rules).
[^oasdiff]: oasdiff — OpenAPI breaking-change detection + CI gate. https://www.oasdiff.com/ — Grade A (tool, mechanizes the bump).
[^pb33f]: pb33f/openapi-changes — diff a spec over time. https://github.com/pb33f/openapi-changes — Grade A (tool).
[^fowler-sdd]: Martin Fowler (Birgitta Böckeler), "Understanding Spec-Driven Development: Kiro, spec-kit, and Tessl." https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html — Grade A (hands-on, names the versioning/drift GAP in all three tools).
[^augment-sot]: Augment Code, "The Spec as Source of Truth: Why Codebases Should Be Rebuildable from Documentation." https://www.augmentcode.com/guides/spec-as-source-of-truth-rebuildable-codebase — Grade B (vendor).
[^kinde]: Kinde, "Executable Specs: Turning Plain English into Running Systems." https://www.kinde.com/learn/ai-for-software-engineering/best-practice/executable-specs-turning-plain-english-into-running-systems/ — Grade B (vendor; executable-spec-as-living-doc).
[^codemyspec]: CodeMySpec, "GitHub Spec Kit: How It Works (2026 Guide)." https://codemyspec.com/blog/github-spec-kit-guide — Grade B (practitioner; the "authority is conventional, not enforced" drift framing).
[^atlassian-prd]: Atlassian, "How to create a product requirements document (PRD)." https://www.atlassian.com/agile/product-management/requirements — Grade B (PRD Change-History: who/when/what).
[^xops-git]: XOps Tutorials, "Git as single source of truth (2026 Guide)." https://www.xopsschool.com/tutorials/git-as-single-source-of-truth/ — Grade C (tutorial; GitOps framing).

## Negative findings
- **No SDD tool (Kiro/spec-kit/Tessl) ships real spec versioning or drift detection** as
  of mid-2026 [^fowler-sdd] — this is an open frontier, not a solved problem to adopt.
  Our edge is that `verifier_commands` already gives us the executable-spec parity oracle
  those tools lack.
- **No bitemporal/DB machinery is warranted** for a single Git-tracked document; Git is
  already the bitemporal substrate (§3). Importing the annotations-table design here
  would be over-build.
