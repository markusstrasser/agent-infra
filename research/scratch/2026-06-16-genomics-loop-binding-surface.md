# Loop-Binding Surface Inventory (genomics instance) — 2026-06-16

**COMPLETE** · **Provenance:** `[SOURCE: <file:line in ~/Projects/genomics>]` for every code fact below; `[INFERENCE]` for the BUILT / ABSENT verdicts. Relocated from `genomics/docs/research/` — this is ONE repo's binding surface, kept as a concrete instance behind the global ADR `decisions/2026-06-16-feature-work-loop-binding-measurement-first.md`. Note: agent-infra's blast-radius notion is **path-class** (governance / hook / schema / contract / settings, per `risky_diff_review_shadow.py`), NOT genomics' closure-hash stage count — don't port the genomics-specific metric upward.

Read-only inventory: can existing primitives (impact_analysis, planctl/conceptctl,
SessionStart peer-warning, validate-code gates) be bound to a feature-work loop?

## Q1. impact_analysis.py — blast-radius computation — BUILT-but-not-shaped-for-this

**File:** `scripts/impact_analysis.py` (487 lines). `just impact` recipe.

**What it computes.** Takes a *git diff*, NOT an arbitrary file list. Entry:
`main()` (L443) → `get_changed_files(since, commit)` (L43) runs `git diff
--name-only <since> HEAD` (or `diff-tree` for a commit) and **filters to
`scripts/*.py` + `config/*.json`** (L52-57). It does NOT accept a stage name or a
caller-supplied file list — input is always derived from git refs (`--since`,
`--commit`).

**Core fns:**
- `build_import_graph() -> dict[str, set[str]]` (L65) — AST static import graph:
  `{module_name: set(files_that_import_it)}` over `scripts/*.py`.
- `load_stage_registry()` (L104) → `STAGES` from `pipeline_stages.py`:
  `{stage: {script, depends_on, outputs, group}}`.
- `build_script_to_stages(stages) -> dict[str, list[str]]` (L130) — **this is the
  file→stage map**: `script path → [stage names using it]`.
- `get_downstream(stage, stages) -> set[str]` (L138) — transitive downstream via
  reverse DAG.
- `analyze_impact(changed_files, since) -> ImpactReport` (L235) — the core. Per
  changed file: `classify_script()` (L221) buckets into modal_stage /
  shared_library / report_generator / config / analysis_script; modal_stage →
  maps to its stages + downstream; shared_library → import-graph dependents →
  their stages + downstream.

**Blast-radius count.** Prints per-impact `affects: <stage list>` truncated to 10
("... and N more", L379-381) and a `rerun_stages` total. So a count exists, but
it's **stages-downstream-of-a-changed-file**, framed as "what Modal outputs are
now STALE", not "this file lives in N stage closures". `--json` (L461) emits
`{rerun_stages, rerun_scripts, impacts:[{name,kind,reason,downstream}]}`.

**Verdict for the loop.** The PRIMITIVE you'd want — `build_script_to_stages()` +
`get_downstream()` — exists and is directly reusable on an arbitrary file list.
But the *script entrypoint* is git-diff-oriented and advisory (`SURFACE_ROLE =
"advisory_impact_inventory"`, "never dispatches", L9-11, L34). To use at
edit/decomposition time you'd import `build_script_to_stages` +
`get_downstream` + `build_import_graph` directly and feed your own file list;
`get_changed_files`/`main` would be bypassed. No CLI flag accepts an explicit
file list today.

## Q2. planctl/conceptctl — task data model + write site — BUILT-but-not-shaped-for-this

**File:** `scripts/planctl.py` (1317 lines). Plans live as markdown docs under
`docs/ops/plans/*.md` with YAML frontmatter; `index.json` is a generated mirror.
**There is no "task" sub-entity** — the unit is a *plan* (one markdown doc). No
per-task list, no per-task field.

**Schema (the index row, built in `sync_index_from_plan_docs` L621-650):**
```
plan_key, title, status, owner_type, source_concepts[], supersedes[],
overlaps[], blocks[], plan_path, queue_state, last_updated, notes[], plan_kind
```
Frontmatter required keys (L26): `plan_key, title, status`. Render whitelist in
`render_frontmatter` (L211-221): plan_key, title, status, last_updated,
source_concepts, supersedes, overlaps, blocks — BUT it preserves arbitrary extra
keys (L238-250 "Preserve any extra custom keys alphabetically"). So **a custom
field (e.g. `blast_radius: 47` or `gate_coverage: [canary]`) CAN be attached to a
plan's frontmatter and survives round-trips** — but it is free-form, not modeled,
not validated, and not surfaced in `index.json` unless added to the entry dict.

**Write site.** Plans created by `cmd_create` (L760) → `make_plan_doc()` (L337)
writes the .md, then builds `entry = {...}` (L796-810) and appends to
`index["plans"]` (L811) + `save_index` (L812). The entry dict (L796) is where a
new top-level indexed field would attach. Frontmatter is authored in
`make_plan_doc` (L347 `fields` dict). `conceptctl` is imported (L14) and reused
for IO (`write_text`, `now_iso`, `repo_root`); concept registry is a separate
store (`docs/concepts/registry.json`).

**Verdict.** A plan, not a task, is the smallest unit; there's no per-task slot.
Attaching a blast-radius/gate-coverage number is mechanically possible (free-form
frontmatter is preserved + the `entry` dict at L796 is one edit) but nothing
models or consumes it today. Granularity mismatch: one number per plan-doc, not
per task.

## Q3. SessionStart PEER warning — ADVISORY-only (no worktree creation)

**Two relevant SessionStart hooks found in `.claude/hooks/`, both pure-advisory
(`additionalContext` JSON, fail-open):**
- `session-start-worktree-disk-bloat.sh` — warns when `.claude/worktrees/` has
  > 3 dirs or low free space; prints `git worktree remove` cleanup commands as
  TEXT (L62-76). Does NOT create anything.

**The "PEER SESSION" emitter is `/Users/alien/Projects/skills/hooks/sessionstart-peer-session-warn.sh`** (wired at `~/.claude/settings.json:509`,
SessionStart). CONFIRMED purely advisory:
- Detects peers via `pgrep -x claude` + `lsof -d cwd` counting claude PIDs whose
  cwd == this checkout (L29-36). If `count >= 2`, prints a warning.
- The "fix" is **TEXT ONLY** — it `echo`s `claude --worktree ${base}-wt${sfx}`
  (L50) as a copy-paste suggestion. It does NOT run `git worktree add`, does NOT
  spawn anything, `set -uo pipefail` + "Advisory only, ALWAYS exit 0" (L10),
  `exit 0` (L56). Logs the fire via `hook-trigger-log.sh` (L54).

**No mechanism anywhere auto-creates or auto-offers (interactively) a worktree.**
`claude --worktree` is a CLI flag the *operator* invokes; the hook only suggests
it as a string. The genomics-repo `session-start-worktree-disk-bloat.sh` likewise
only prints `git worktree remove` cleanup text. Worktree creation for subagents
is a separate path (the Agent tool's `isolation: "worktree"` param + the
`pretool-worktree-edit-scope.sh` enforcement), not a session-level auto-offer.

**Verdict: ABSENT** (as an auto-create/auto-offer mechanism) — purely advisory
text re-fired every session a peer is detected.

## Q4. Gate→coverage map — BUILT-but-not-shaped-for-this (one gate only: payload-validity)

`validate-code` (Justfile:988) chains ~60 leaf gates. Surveyed the named ones:

- **canary / ir-canary / retraction-gate** — these are *regression* gates (run a
  fixed classification/IR/retraction-propagation fixture, e.g. `retraction-gate` →
  `test_retraction_propagation.py`). They assert behavior on baked-in fixtures;
  **none expose a queryable "which files/stages do I cover" set**. Coverage is
  implicit in the fixture, not declared.
- **lint-architecture / bio-verify** — import/boundary lints + bio-constant
  manifest; no file→gate coverage map surfaced for a decomposition check.

**The one real gate→stage coverage map: payload-validity.**
`scripts/payload_contract.py` defines `_SEED_PAYLOAD_DECLARATIONS: dict[str,
PayloadDeclaration]` (L168) — **keyed by STAGE NAME** → `PayloadDeclaration`
(denominator_field, eligible_field, expected_floor, summary_artifact). This IS a
queryable map "does stage X have a payload-validity declaration / is it covered".
`scripts/lint_payload_declarations.py` validates **every declared stage name
exists in `pipeline_stages.STAGES`** (L71-76, imports `STAGES`, returns `set(STAGES)`)
— so the coverage set is machine-checkable and stage-keyed today. An UNDECLARED
stage is explicitly "uncheckable, non-blocking" (payload_contract.py L43-44,
L96) — i.e. *the gate already computes its own coverage gap* (declared vs all
STAGES).

**But:** this map is keyed by **stage**, not by **file/task**, and it covers only
the payload-validity axis. To answer "is THIS decomposition task inside a gate's
coverage" you'd (a) map task→files→stages via Q1's `build_script_to_stages`, then
(b) intersect with `set(_SEED_PAYLOAD_DECLARATIONS)`. No single manifest unifies
all ~60 gates → their coverage sets; for canary/ir-canary/retraction the coverage
is implicit/uncomputable from a manifest.

**Verdict: BUILT-but-not-shaped-for-this.** A stage-keyed coverage map exists for
exactly ONE gate (payload-validity, `payload_contract._SEED_PAYLOAD_DECLARATIONS`
+ `lint_payload_declarations` validating against `STAGES`). The other gates carry
no declared coverage set. There is NO gate→file map and NO unified gate-coverage
manifest.

---

## Decision-relevant summary (per question)

**Q1 — impact_analysis.py: BUILT-but-not-shaped-for-this.** The reusable
primitives (`build_script_to_stages` file→stage map, `get_downstream` transitive
DAG, `build_import_graph`) all exist and work on arbitrary inputs, but the
*entrypoint* derives its file list from a git diff (`--since`/`--commit`) and is
advisory. Bind by importing the three functions directly with your own file list;
don't shell out to `main`.

**Q2 — planctl: BUILT-but-not-shaped-for-this.** Unit is a *plan* (markdown +
frontmatter), not a *task* — no per-task field exists. A blast-radius/coverage
number can attach as free-form frontmatter (preserved by `render_frontmatter`
L238-250) + one field in the `entry` dict at `cmd_create` L796, but nothing
models/validates/consumes it. Granularity is one-per-plan-doc.

**Q3 — peer-session worktree: ABSENT (advisory only).** Emitter is
`~/Projects/skills/hooks/sessionstart-peer-session-warn.sh` (settings.json:509).
It only `echo`s `claude --worktree <name>` as text and exits 0; no auto-create,
no interactive auto-offer. Worktree isolation is operator-CLI / subagent-param
only.

**Q4 — gate→coverage map: BUILT-but-not-shaped-for-this (1 of ~60 gates).** Only
payload-validity has a stage-keyed coverage map
(`payload_contract._SEED_PAYLOAD_DECLARATIONS`, validated against
`pipeline_stages.STAGES` by `lint_payload_declarations.py`) — and it already
computes its own declared-vs-all coverage gap. No gate→FILE map, no unified
manifest across gates; canary/ir-canary/retraction coverage is implicit in
fixtures and not queryable.

## Q4. Gate→coverage map — queryable gate coverage?
_pending_
