---
id: 2026-06-07-biomedical-mcp-tool-consolidation
concept: mcp-tool-surface-design
repo: biomedical-mcp
decision_date: 2026-06-07
recorded_date: 2026-06-07
provenance: contemporaneous
status: accepted
initial_leaning: single-grammar collapse (BioMCP-style, 1-3 tools) — assumed maximal consolidation was the goal; mid-deliberation leaned to progressive-disclosure (tag-hide + bio_expand), then flipped the MECHANISM after cross-model review (see disposition)
relations:
  - type: depends_on
    target: 2026-06-07-state-externalization-lens
---

# 2026-06-07: biomedical-mcp tool consolidation — default composites + tag-gated long tail

## Context
biomedical-mcp exposes **~85 tools across 20 domains** via FastMCP 3 `mount()` with namespace prefixes (`genetics_gene_info`, `variants_lookup`, …). Three new source-groups are queued to land (CPIC+PharmGKB PGx, DDInter drug-drug interactions, CIViC+OncoKB somatic) which would push the count toward ~95. Markus chose (2026-06-07) to **consolidate toward fewer composite tools before the count degrades planning/context**, with GenomOncology BioMCP's single-grammar design (36 tools → 1, ~16,600 → ~800 at-rest tokens) as the reference. This is D0 in `.claude/plans/cdcb8ca9-leverage-plan-2026-06-07.md` — a prerequisite gating all biomedical-mcp ports.

The at-rest cost is the problem: ~85 tool schemas load **every turn**, regardless of whether they're used.

## Alternatives considered
Five mechanisms were fleshed out in parallel (full sketches in `.claude/plans/d0-consolidation/option-{1..5}-*.md`):

1. **Single-grammar collapse** (`bio_get/search/enrich` verb×entity, 3-4 tools). ~94% token cut. **Con:** discoverability cliff (agent must know valid entity×section combos from one docstring), stringly-typed (typo → silent empty), biggest rewrite (all domains → internal dispatcher).
2. **Entity composites** (one tool per gene/variant/drug/protein/disease/…, ~15 tools, `sections=[...]` selection — generalizes the *existing* `composite_gene_dossier`/`composite_variant_context`). **Pro:** best planning fit (entities = how agents reason), fully additive/low-risk. **Con:** only ~43-65% token cut; 15 visible tools.
3. **Task/intent tools** (`review_variant`, `pgx_review`, `check_drug_interactions`, … ~13 tools — promotes existing `@prompt` templates). ~83% cut. **Con:** most opinionated; taxonomy may mismatch real queries (needs query-log audit); longest migration (3-4 wk).
4. **MCP Resources + few tools** (`bio://gene/BRCA1` URIs). **DEAD:** MCP Resources are **not agent-invocable** in Claude Code (surface only via user `@`-mention) → zero reduction in the agent-facing tool surface. Sinks the option as a primary strategy.
5. **Progressive disclosure** (tiny at-rest surface; raw tools hidden behind tags, revealed on demand via `bio_expand(domain)` / `Context.enable_components`). ~94% cut, **~4 hr migration** (mechanical tag additions), mirrors Claude Code's own ToolSearch/deferred-tool pattern.

## Counterevidence sought
The leading candidate after fleshing out was **#5 (progressive disclosure)** — but its entire viability rested on an unverified claim both agents flagged: *does FastMCP 3.4 propagate tool tags through `mount()`, and does session-scoped reveal work?* If tags were stripped at mount, #5 collapses to a 40-line key-registry workaround and loses its elegance. **Probe run before deciding** (`/tmp/fastmcp_func2.py`, FastMCP 3.4.0):
- Mounted sub-server tool `genetics_gene_info` **retains** `tags={'genetics'}` after `mount()`. ✓
- `root.disable(tags={'genetics'})` → listing drops to `['composite_dossier']` (mounted tools hidden). ✓
- `root.enable(tags={'genetics'})` → mounted tools reappear. ✓
- `Context.enable_components`/`disable_components` exist for session scope. ✓

Counterevidence searched for (tag-stripping on mount) was **not found** — the mechanism works as designed. Also searched whether Resources could rescue #4 (Claude Code docs + MCP spec): confirmed resources are user-attached, not agent-invoked → #4 stays dead.

## Decision
**Private-adapter consolidation: entity composites over de-registered raw tools (NOT tag-hiding/`bio_expand`).** Mechanism revised after cross-model review — see disposition below.

**Visible MCP surface (~6-7 tools, all that load at rest):**
- Entity composites generalizing the existing pattern: `gene_dossier`, `variant_context` (exist today) + add `drug_profile`, `protein_profile`, `disease_profile` — each takes `id` + `sections: list[str]` with curated non-`all` defaults, and returns a **standardized partial-failure envelope** (per-section `status`/`data`/`error`, so one dead upstream API degrades a section, never fails the whole dossier or returns silent nulls).
- `bio_search(entity, query, filters)` — cross-entity resolve/search.
- `describe_sections(entity)` — meta-tool returning the valid sections + their params + sources for an entity, served from a static section registry. Solves section discoverability + parameter pollution **without** bloating composite schemas.

**The 85 raw tools: strip the `@tool` decorators → convert to private Python adapters** under `biomedical_mcp/adapters/` (one per source, pure functions). They leave the MCP tool schema entirely — no tags, no reveal-state, **no "invisible tool-call trap"** (a hidden-but-registered tool, if called, fails at Claude Code's client-side validation before reaching the server, so the server can't self-heal; de-registered adapters avoid this because the agent never sees their names to call). Capability is preserved (composites call them), only the agent-facing transport is removed — separates transport from capability.
- *Rare raw access* (maintenance/expert): exposed only via a `full`/`debug` profile flag, not the default agent surface. Add the raw tool back to the schema only when query logs show a recurring need a composite doesn't cover.

**New sources mount with zero new visible tools:** CPIC/PharmGKB → PGx `sections` on `gene_dossier`+`drug_profile`; DDInter → interactions section on `drug_profile`; CIViC/OncoKB → somatic section on `variant_context`. Each is an adapter + a section-registry entry + tests — ≤3 surfaces touched.

**Why this over the pure options + over my own mid-deliberation tag-hiding plan:** gets #5/#1's ~94% at-rest cut (down to ~6 tools, <1k tokens) **without** #1's discoverability cliff, **without** #3's taxonomy-lock, and **without** the tag-hide mechanism's invisible-call trap + dual-surface maintenance (which both review models flagged as a Principle 8 violation). #2 alone reaches only ~43-65% because 15 tools stay visible; de-registering the long tail (not hiding it) pushes to ~94% with a *single* maintained surface. Task tools (#3) can layer on later if query logs justify the taxonomy — deferred, not rejected.

**Migration is incremental and additive:**
- **Phase A:** standardize the partial-failure envelope on the 2 existing composites (`gene_dossier`, `variant_context`). Build the section registry + `describe_sections`. Purely additive.
- **Phase B:** generalize composites to `drug_profile`/`protein_profile`/`disease_profile` (existing `_gather_sync`/ThreadPoolExecutor is the template; add per-adapter timeouts).
- **Phase C:** strip `@tool` from the raw domains → adapters; remove the domain `mount()` calls; `tools/list` should show only the ~6 composites + search + describe. Gate behind a `full` profile for raw access.
- **Phase D:** new sources (CPIC/PharmGKB, DDInter, CIViC/OncoKB) land as adapters + sections — unblocks D1/D2/D4.
- **Validation gate:** before/after at-rest token measurement + a small fixed biomedical task set (first-tool-correctness, answer-correctness, invalid-section rate) per `~/Projects/evals`. GPT's full 3-arm A/B/C eval is the heavier option if Phase C results look ambiguous.

## Cross-model review disposition (2026-06-07)
Artifacts: `.model-review/2026-06-07-d0-tool-consolidation-8f6bc0/`. Gemini 3.5 Flash + GPT-5.5.

**Convergent (both) — adopted, drove a mechanism flip:**
- The `bio_expand`/tag-hide layer is **over-engineered for a single operator** and has a real failure mode → replaced with private-adapter de-registration (above).
- **Invisible tool-call trap** (Gemini, mechanism-level, verified-plausible): disabled tools are omitted from `tools/list`; a call to one fails at client-side validation before the server sees it → no server-side recovery hint → retry loops. This is the decisive fact for the flip.
- **Parameter pollution** (both): section-specific composite params bloat the schema / force `**kwargs` → solved by `describe_sections` meta-tool + minimal composite params.
- **Partial-failure envelope** (both): composites amplify upstream outages (32 APIs @ 99% → ~72.5% all-green); standardized per-section status required. Adopted.
- **Section registry as single source of truth** (both): define each section once → generate docs/enums/validation/tests; new source touches ≤3 surfaces. Adopted.

**Adopted (single-source):**
- GPT: keep raw tools in a `full`/`debug` profile, not the default agent surface; add a retirement rule (a raw tool must justify itself by logged usage). Adopted.
- GPT/Gemini: add a validation eval gate with task-success thresholds, not just token count. Adopted (lightweight first; 3-arm if ambiguous).

**Noted, not blocking:** GPT's "Option 2 plain (15 visible, no hiding) may be sufficient" — the private-adapter design supersedes this debate: it reaches ~6 visible without *any* hiding mechanism, so it's strictly simpler than both Option 2 and the tag-hide layer.

## Evidence
- 5 parallel design sketches: `.claude/plans/d0-consolidation/option-{1..5}-*.md`.
- FastMCP 3.4.0 functional probe (tags through mount + enable/disable + Context session scope) — passed.
- Existing seed in-repo: `composite.py` (`composite_variant_context`, `composite_gene_dossier`), `@main.prompt()` templates (`variant_review`, `pgx_review`).
- BioMCP reference benchmark: 36→1 tools, ~16,600→~800 at-rest tokens.
- Cross-model review: DONE (Gemini 3.5 Flash + GPT-5.5, 2026-06-07) — flipped the mechanism from tag-hide to private adapters; see disposition.

## Revisit if
- Query-log audit shows agents overwhelmingly hit one task shape → promote task tools (#3) onto the default surface.
- `bio_expand` two-step (expand-then-call) proves unreliable in practice (agent fails to expand before calling a hidden tool) → fall back to wider default surface or grammar (#1).
- A future Claude Code/MCP version makes Resources agent-invocable → reconsider #4 as a complement.

## Supersedes
None (first tool-surface decision for biomedical-mcp).

## Revisions
- **2026-06-07 (during execution):** No `adapters/` directory needed — reading the
  code showed the composites *already call the ~32 client classes directly*
  (`myvariant.lookup()`, `gnomad.gene_constraint()`), bypassing the domain `@tool`
  wrappers entirely. **The client classes ARE the adapter layer.** So consolidation =
  build entity composites + a section registry over the existing clients, and gate the
  domain `@tool` mounts behind a `full` profile (the agreed escape hatch) rather than
  rewriting 85 tools into adapter functions. Strictly simpler than the recorded plan;
  same end state (~6 visible tools). Phase 0 (envelope + registry + describe_sections +
  refactored gene_dossier + 9 contract tests) shipped at biomedical-mcp@609d53e.
- **2026-06-07 (execution complete):** All phases shipped in biomedical-mcp.
  Phase 1 generic entities/ registration @5e63896; Phase 2 variant/drug/protein/disease
  composites (parallel fan-out) @f1b8abc; Phase 3 profile cutover @4aca588 —
  `BIOMEDICAL_MCP_PROFILE` env var, default "composite" = **8 tools / ~1.2k at-rest
  tokens** vs "full" = 93 tools / ~10.4k (**88% reduction**), bio_search added; Phase 4
  CPIC/PharmGKB + DDInter + CIViC/OncoKB as new sections @b8d5845. 138 offline tests green.
  Only `literature`+`population` domains were fully redundant — every other domain kept
  long-tail tools, so raw domains are gated behind `full` (not deleted); clinical trials,
  pathways, supplements, nutrition, blood groups, HPO/gene search, eQTLs, ensembl sequence
  remain promotion candidates. DDInter has no official API (web-UI endpoints) → opt-in section.
