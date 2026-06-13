---
title: Skill Bloat Audit & Trim Proposal (measure-before-cut)
date: 2026-06-13
status: complete
tags: [skills, codex, context-budget, audit, trim, intel]
---

# Skill Bloat Audit — Measure Before Cut

**Method.** Lifetime Skill-invocation counts from `~/.claude/agentlogs.db`
(`tool_calls` where `tool_name='Skill'`; skill name = `json_extract(args_json,'$.skill')`;
project = `sessions.project_slug`), history **2026-03-08 → 2026-06-13** (513 Skill calls).
A skill installed in a repo but absent from the usage table = **never fired** in 3 months.

> Caveat (logged, not waved away): **all 513 Skill rows are vendor=`claude`.** Codex does
> not emit `Skill` tool-calls to agentlogs, so we have **zero direct usage signal for Codex
> skill loads.** Codex trim is therefore justified by *redundancy/staleness on disk*
> (empty dirs, stale duplicates of live plugins), not by a usage count. Claude usage is the
> proxy for shared-skill value; Codex-only artifacts are judged structurally.

---

## 1. Usage table (lifetime, all repos)

Skills that fired at least once. `n` = lifetime invocations; `repos` = distinct project_slugs.

| skill | n | repos (n) | last fired |
|---|---|---|---|
| critique | 165 | 14 | 2026-06-13 |
| research | 69 | 9 | 2026-06-13 |
| brainstorm | 23 | 5 | 2026-06-12 |
| llmx-guide | 22 | 9 | 2026-06-12 |
| social-thread | 20 | 1 (intel) | 2026-06-05 |
| modal | 18 | 3 | 2026-06-12 |
| model-guide | 15 | 5 | 2026-06-12 |
| execute | 15 | 8 | 2026-06-13 |
| observe | 14 | 5 | 2026-06-13 |
| disqualify | 13 | 1 (intel) | 2026-06-10 |
| code-review | 12 | 4 | 2026-06-13 |
| x-api | 10 | 2 | 2026-06-04 |
| asset-decision | 9 | 2 | 2026-06-12 |
| genomics-pipeline | 8 | 1 (genomics) | 2026-06-12 |
| extract-generators | 7 | 2 | 2026-06-10 |
| entity-management | 7 | 2 | 2026-06-02 |
| loop | 6 | 2 | 2026-06-12 |
| exa:search | 6 | 1 (intel) | 2026-06-08 |
| divergence-update | 6 | 1 (intel) | 2026-06-05 |
| confirm | 6 | 1 (intel) | 2026-06-05 |
| writing-style | 5 | 3 | 2026-06-10 |
| decide | 5 | 4 | 2026-06-13 |
| adversarial-dd-batch | 5 | 1 (intel) | 2026-06-09 |
| leverage | 4 | 2 | 2026-06-11 |
| improve | 4 | 1 (agent-infra) | 2026-06-13 |
| eval | 4 | 2 | 2026-06-13 |
| bio-verify | 4 | 1 (genomics) | 2026-06-13 |
| schedule | 3 | 1 | 2026-06-10 |
| de-slop | 3 | 1 (publishing) | 2026-05-29 |
| claude-api | 3 | 3 | 2026-06-11 |
| **--- rare: <3 lifetime ---** | | | |
| source-ingest | 2 | 2 | 2026-06-08 |
| probe-fork | 2 | 1 | 2026-06-12 |
| verify-before | 1 | 1 | 2026-06-11 |
| upgrade | 1 | 1 (intel) | 2026-06-07 |
| search | 1 | 1 (intel) | 2026-06-03 |
| resolve-predictions | 1 | 1 (intel) | 2026-06-01 |
| propose-rule | 1 | 1 (intel) | 2026-05-31 |
| new-dataset | 1 | 1 (intel) | 2026-06-01 |
| interview-prompt | 1 | 1 (agent-infra) | 2026-06-07 |
| ingest-article | 1 | 1 (intel) | 2026-06-04 |
| idea-generation | 1 | 1 (intel) | 2026-06-01 |
| gpt-image-2 | 1 | 1 (phenome) | 2026-06-09 |
| forecast | 1 | 1 (intel) | 2026-05-29 |
| embedding-models | 1 | 1 (phenome) | 2026-06-09 |
| dataset | 1 | 1 (ext) | 2026-06-11 |
| analyze | 1 | 1 (hutter) | 2026-06-11 |

(omitted from cut analysis: `noop`, `webwright:run`, `frontend-design`, `new-dataset` test/plugin noise.)

---

## 2. NEVER-FIRED installed skills (3-month zero), per scope

These are installed but have **0 invocations** in the entire log.

**intel** (14 of 27 never fired — the worst offender):
`3-statement-model`, `audit-xls`, `commands`, `comps-analysis`, `dcf-model`,
`earnings-preview`, `governance`, `llm-check`, `model-update`, `modeling`,
`talent-dossier`, `thesis-check`, `trace-influence`, `xlsx-author`

**genomics** (7 of 9): `annotsv`, `clinpgx-database`, `data-transform`,
`genomics-status`, `gget`, `life-science-research`, `vcfexpress`

**phenome** (3 of 8): `life-science-research`, `markitdown`, `scientific-drawing`

**agent-infra** (2 of 3): `scientific-drawing`, `skill-authoring`

**global `~/.claude/skills`** (3 of 21): `person-into-scene`, `sweep`, `trending-scout`

**`~/.codex/skills`** (loose dirs): `codex-primary-runtime`, `playwright-interactive`, `sweep`

---

## 3. intel — the overflow driver (scrutinized hardest)

**Budget math.** Codex-discoverable shared skill descriptions sum to **4,451 chars**
(under the 8,000-char / ~2% ceiling). intel's 27 project skills add **10,002 chars on top** —
intel *alone* more than doubles the budget and blows past 8K. In an intel session Codex loads
global + intel ≈ **14.5K chars**, ~1.8× the budget. **intel is the cause of the overflow.**

**14 intel skills have NEVER fired in 3 months** (listed in §2). The financial-modeling
cluster is the dead weight: `3-statement-model`, `dcf-model`, `comps-analysis`,
`model-update`, `modeling`, `audit-xls`, `xlsx-author`, `earnings-preview` — 8 skills, all
zero. The `_FINANCE_SKILLS_PROVENANCE.md` marker suggests these were imported as a bundle and
never wired into a workflow. `talent-dossier`, `thesis-check`, `trace-influence`, `commands`,
`governance`, `llm-check` round out the never-fired set.

Of intel's skills that *do* fire, the heavy hitters are `critique`(60), `social-thread`(20),
`research`(20), `disqualify`(13), `brainstorm`(12) — but `critique`/`research`/`brainstorm`
are **global** skills (no need for an intel copy). Only `social-thread`, `disqualify`,
`asset-decision`, `divergence-update`, `confirm`, `adversarial-dd-batch`, `entity-management`,
`extract-generators`, `exa:search`, `x-api` are intel-local AND load-bearing.

---

## 4. PER-REPO CUT LIST

Each cut names the usage number justifying it (0 = never fired in 3 months).

### intel — CUT 14 (all never-fired), saves 4,403 chars (44% of intel's 10,002, measured)
| skill | lifetime n | note |
|---|---|---|
| 3-statement-model | 0 | finance bundle, dead |
| dcf-model | 0 | finance bundle, dead |
| comps-analysis | 0 | finance bundle, dead |
| model-update | 0 | finance bundle, dead |
| modeling | 0 | finance bundle, dead |
| audit-xls | 0 | finance bundle, dead |
| xlsx-author | 0 | finance bundle, dead |
| earnings-preview | 0 | finance bundle, dead |
| talent-dossier | 0 | dead |
| thesis-check | 0 | dead |
| trace-influence | 0 | dead |
| commands | 0 | dead |
| governance | 0 | dead |
| llm-check | 0 | dead |

Rare-but-fired intel skills (1 invocation each) — **demote/merge, don't hard-cut yet**:
`upgrade`(1, global dup → just delete the intel copy), `search`(1), `resolve-predictions`(1),
`propose-rule`(1), `new-dataset`(1), `ingest-article`(1), `idea-generation`(1), `forecast`(1).
These 8 are weak but each fired once in-domain; fold related ones (`new-dataset`/`dataset`,
`idea-generation`/`forecast`) or watch one more cycle. After the 14 hard cuts intel goes
27→13 skills.

### genomics — CUT 6 (verify the one keep first)
`annotsv`(0), `clinpgx-database`(0), `data-transform`(0), `genomics-status`(0), `gget`(0),
`vcfexpress`(0). **KEEP `life-science-research`** despite 0 — see rare-but-keep. genomics 9→3.

### phenome — CUT 2
`markitdown`(0 — native `markitdown` CLI / Modal Marker covers PDF→md), and the **intel/phenome
`life-science-research`** copies are redundant with the genomics one. `scientific-drawing`(0) →
see rare-but-keep. phenome 8→6 (or 7 if life-science-research kept project-local).

### agent-infra — CUT 1
`skill-authoring`(0) — but see rare-but-keep (governance tool). `scientific-drawing`(0) →
keep per rare-but-keep. Net: **0 hard cuts**; agent-infra's 3 are all load-bearing-or-tooling.

### global `~/.claude/skills` — CUT 0, watch 3
`person-into-scene`(0), `sweep`(0), `trending-scout`(0) never fired — but all three are
**capability skills you'd invoke deliberately** (image-gen, consistency-scan, landscape-scan),
not workflow bloat. Global skills load everywhere but the *shared* set is only 4.4K chars
(under budget). **No cut; re-measure in 30 days.**

### `~/.codex/skills` loose dirs — CUT 2 (structural, not usage)
- `codex-primary-runtime/` — **empty 0-byte dir (Apr 23), NOT a skill.** The real runtime is
  `~/.cache/codex-runtimes/codex-primary-runtime/`. `rm -rf ~/.codex/skills/codex-primary-runtime`.
- `playwright-interactive/` — stale OpenAI-curated skill dir (Mar 5); superseded by the live
  `browser@openai-bundled` plugin (installed, enabled). `rm -rf ~/.codex/skills/playwright-interactive`.

---

## 5. RARE-BUT-KEEP (low/zero usage, load-bearing — do NOT cut)

| skill | n | why it stays |
|---|---|---|
| `life-science-research` (genomics) | 0 | domain capability skill — invoked on-demand for lit lookup; not workflow-frequent but load-bearing when it fires. Keep ONE canonical copy (genomics), cut the intel/phenome dups. |
| `scientific-drawing` (agent-infra/phenome) | 0 | figure-generation capability; deliberate-invoke, rare by nature. Keep one. |
| `skill-authoring` (agent-infra) | 0 | **governance tooling** — meta owns skill quality; this is the authoring path. Keep (it's a tool, not a workflow trigger). |
| `de-slop` (codex symlink) | 3 | text-quality pass; fired recently. Symlink to `~/Projects/skills/de-slop`, in the managed set. Keep. |
| `verify-before` / `probe-fork` | 1–2 | discipline/safety skills — rare-but-load-bearing class (probe-before-build). Keep. |
| `schedule` / `loop` | 3–6 | orchestration primitives. Keep. |
| global `person-into-scene`/`sweep`/`trending-scout` | 0 | deliberate-invoke capabilities, shared budget under ceiling. Keep, watch. |

**Rule applied:** never-fired ≠ cut when the skill is a *deliberately-invoked capability* or a
*safety/governance tool*. Cut = never-fired **workflow** skills (the finance bundle is the
archetype: imported, never wired to a caller).

---

## 6. Codex APP vs CLI — removal procedure (empirically verified on this machine)

**Architecture (verified, not doc-guessed).** Codex loads skills from three on-disk layers:
1. `~/.codex/skills/` (user) — here, mostly **symlinks** into `~/Projects/skills/` (our managed
   Claude skills), plus a few **real dirs** (loose installs) and `~/.codex/skills/.system/`.
2. `~/.codex/skills/.system/` — **OpenAI-bundled defaults**: `imagegen`, `openai-docs`,
   `plugin-creator`, `skill-creator`, `skill-installer`. (Do not touch — app-managed.)
3. `.codex/skills/` (project) — none here; per-repo skills reach Codex via
   `.agents/skills` → `.claude/skills` symlinks (see §7).

**The disable surface is `[plugins."<name>@<source>"]` in `~/.codex/config.toml`, NOT
`[[skills.config]]`.** (The general docs describe `[[skills.config]] enabled=false`; this
install uses the **plugins** marketplace model — config.toml here has 15 `[plugins.…] enabled=true`
blocks, zero `[[skills.config]]` blocks. Use the live mechanism, not the doc default.)

**Three removal paths by skill TYPE:**

| Skill type on disk | App-level removal (correct) | CLI shortcut |
|---|---|---|
| **Marketplace plugin** (`@openai-curated`, `@openai-bundled`, `@openai-primary-runtime`, `@claude-plugins-official`) | `codex plugin remove <name>@<source>` — drops it from `~/.codex/config.toml` AND the local cache. Sets `enabled=false` effect. This IS the app removal (config is shared app↔CLI). | same command |
| **Loose dir** in `~/.codex/skills/<name>` (real dir, not symlink, not a plugin) | `rm -rf ~/.codex/skills/<name>` — these are not plugin-managed (e.g. `codex-primary-runtime`, `playwright-interactive`). | same |
| **Symlinked skill** (`~/.codex/skills/<name>` → `~/Projects/skills/<name>`) | remove the **source** under `~/Projects/skills/` (friend-sync governed). Deleting the symlink alone gets re-created by `friend-sync.sh`. | n/a |

**App vs CLI distinction (resolved):** Codex CLI and the Codex desktop app share
`~/.codex/config.toml` and `~/.codex/skills/`. There is **no separate app-only skill store** on
this install — `codex plugin remove` (or editing config.toml + `rm` the dir) removes a skill
from BOTH the app and the CLI. The official docs do **not** document a distinct app-UI removal
path; the marketplace-plugin model means config.toml is the single source of truth. To inspect:
`codex plugin list`. To disable without deleting: set `enabled = false` under the plugin block.

**Doc citations:**
- Agent Skills — Codex: https://developers.openai.com/codex/skills
- Configuration Reference — Codex: https://developers.openai.com/codex/config-reference
- Skills context-budget (hardcoded 2%, ~8,000-char baseline, not configurable):
  https://github.com/openai/codex/issues/19679
- `playwright-interactive` is an OpenAI-curated skill:
  https://github.com/openai/skills/blob/main/skills/.curated/playwright-interactive/SKILL.md

> Doc gap flagged: OpenAI's published docs describe `[[skills.config]]` but this install
> (Codex CLI 0.135, plugin-marketplace era) uses `[plugins.…]`. Trust the live config + `codex
> plugin list`, not the doc snippet — they diverged across versions.

---

## 7. codex_parity_sync — what re-syncs, so a trim STICKS

`scripts/codex_parity_sync.py` mirrors per-repo Claude assets into Codex's discovery layer.
For **skills** it does exactly one thing (step 3, `sync_repo`):
```
<repo>/.agents/skills  →  symlink to  <repo>/.claude/skills
```
It creates/verifies a single **directory symlink** `.agents/skills → .claude/skills` so Codex
auto-discovers a repo's skills. **It does NOT copy individual skills and does NOT write to the
global `~/.codex/skills/`.** Therefore:

- **To trim a project skill durably:** delete it from `<repo>/.claude/skills/<name>`. The
  `.agents/skills` symlink points at that dir, so the deletion propagates immediately and
  parity-sync has nothing to re-create (it only ensures the top-level symlink exists).
- **The global `~/.codex/skills/` symlinks** (analyze, critique, …) are created by
  **`friend-sync.sh`**, not parity-sync — each `~/.codex/skills/<name>` → `~/Projects/skills/<name>`.
  To trim a *shared* skill from Codex you must remove the source in `~/Projects/skills/`;
  deleting just the symlink, friend-sync recreates it.
- **The two loose dirs** (`codex-primary-runtime`, `playwright-interactive`) are owned by
  NEITHER sync script (real dirs, not symlinks) — `rm -rf` is permanent, nothing re-creates them.

**Conclusion:** intel/genomics/phenome cuts = delete from `<repo>/.claude/skills/`; nothing
re-syncs them back. Codex loose-dir cuts = `rm -rf`, permanent.

---

## Recommended first action (highest ROI, reversible)

Cut intel's 14 never-fired skills from `intel/.claude/skills/` (4,403 chars measured, 44% of
intel's 10,002). This single change drops an intel Codex session from ~14.5K → ~10.1K
skill-description chars — the biggest single dent in the overflow, landing it near the 8K
ceiling. All cuts are git-reversible. Pair with the two Codex `rm -rf` loose-dir deletions
(pure cruft, zero risk).

## Revisions

**2026-06-13 (same day) — intel + genomics hard-cuts EXECUTED then REVERTED. The §2-§4
cut lists over-reached; do not re-apply them.** Running the cuts surfaced live `CLAUDE.md`
pointers to the "dead" skills: `intel/CLAUDE.md:100` wires the finance bundle to the
conviction template; `:94`/`:36` document thesis-check/trace-influence/commands as workflow;
`genomics/CLAUDE.md:225` lists annotsv/clinpgx-database/gget/vcfexpress as invoke-when-relevant
bio tools. The §3 premise ("imported as a bundle, never wired into a workflow") was **false**.
These are **documented deliberate-invoke capabilities** — the exact class §5 chose to KEEP
(life-science-research). 0 invocations in 3 months = dormant, not dead. Reverted intel
(ba36c3d2 → b82a2f6c) and genomics (185cf4099 → 78fdca70). **KEPT** (genuinely correct):
phenome `markitdown` (native-superseded utility, not a capability → 2dc3d0f4) and the two
codex loose dirs (`codex-primary-runtime` empty dir + `playwright-interactive` superseded by
`browser@openai-bundled`).

**Methodology fix (the durable lesson): a usage-only skill audit MUST cross-check
doc-references before cutting.** A skill named in a routing doc (`CLAUDE.md`, a rule) is
*wired by definition* — usage count cannot override that. The real Codex-overload lever is
**description-length trimming** (keep the capability, shorten the `description:` field Codex
budgets against), not deletion of documented skills. intel's overflow is 27 skills × verbose
descriptions, not 27 skills existing.
