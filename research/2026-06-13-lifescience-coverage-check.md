---
title: Life-Science-Research Codex Plugin — Content Freshness Coverage Check
date: 2026-06-13
status: complete
tags: [lifescience, codex-plugin, biomedical-mcp, coverage, delete-gate]
---

# Life-Science-Research Plugin Freshness Check

**Gate question:** Safe to delete upstream `~/.codex/plugins/cache/openai-curated/life-science-research/c6ea566d/`, or did OpenAI refresh content (cache Jun 10 2026) beyond our port (Apr 25 2026) + productionized MCP (`biomedical-mcp` v0.6.0)?

**One-line answer: SAFE TO DELETE.** Exactly one skill received a substantive upstream content update (`locus-to-gene-mapper`), and its entire value (rsID → GRCh38 coords + gene) is already implemented in `biomedical-mcp/myvariant.py` via a more robust mechanism. Everything else is a structural file rename, not content.

## Method
- `diff -rq` each upstream `<name>-skill/` vs our `sources/<name>-skill/`.
- The directory diff is dominated by a **filename change**: upstream Jun 10 renamed the instruction file `INSTRUCTIONS.md` → `SKILL.md`. Our port still uses `INSTRUCTIONS.md`. This makes ~all 50 shared skills *appear* changed.
- Real test: strip YAML header (name/description/version/license/`---`) and diff `SKILL.md` (up) vs `INSTRUCTIONS.md` (ours) body. → measures true content drift.
- Deep-diff the one skill with a differing same-named tracked file.
- Cross-check the single ALPHA against `biomedical-mcp/src/biomedical_mcp/`.

## Changed skills (true content, header-stripped)

Marquee sample (alphafold, gwas-catalog, uniprot, clinvar-variation, ensembl, opentargets, pharmgkb, gnomad-graphql, clinicaltrials, pubchem-pug):

| Skill | Body diff lines | Class |
|---|---|---|
| alphafold | 0 | rename-only (NOISE) |
| gwas-catalog | 0 | rename-only |
| uniprot | 0 | rename-only |
| clinvar-variation | 0 | rename-only |
| ensembl | 0 | rename-only |
| opentargets | 0 | rename-only |
| gnomad-graphql | 0 | rename-only |
| clinicaltrials | 0 | rename-only |
| pubchem-pug | 0 | rename-only |
| pharmgkb | 8 | NOISE (doc example gene id only) |
| **locus-to-gene-mapper** | script refactor + new test | **ALPHA** |

Across all 50 shared skills, the only differing *same-named tracked file* (per `diff -rq`) is:
`locus-to-gene-mapper-skill/scripts/map_locus_to_gene.py` (differs) + a NEW `scripts/test_map_locus_to_gene.py`. Every other skill's `scripts/`, `agents/` are byte-identical; the sole delta is the `.md` rename.

## ALPHA vs NOISE — evidence

### NOISE
- **`INSTRUCTIONS.md` → `SKILL.md` rename** (all 50 skills). Pure structural; our port content is byte-identical after header strip. No reason to chase; if anything our naming is the deliberate fork convention.
- **pharmgkb 8-line diff** — only the example PharmGKB accession in the docs changed (`PA36679` ↔ `PA134865140`). No endpoint/logic change.

### ALPHA — `locus-to-gene-mapper` (the only one)
Upstream Jun 10 (mtime confirmed: ours `Apr 24 20:57`, upstream `Jun 10 08:31` — upstream is genuinely newer, we are NOT ahead) rewrote rsID coordinate resolution:

1. **API base-URL fix:** `…/variation/v0/beta/refsnp` → `…/variation/v0/refsnp` (dropped the `/beta/` segment). A real correctness fix — ours still points at the beta path.
2. **Inlined RefSNP resolution:** added `chromosome_from_refseq`, `coordinate_from_placement`, `assembly_key_from_traits`, `resolve_refsnp_coordinates`, `fetch_refsnp_payload` (~120 LoC). Replaces ours, which shells out to `variant-coordinate-finder-skill/scripts/variant_coordinate_finder.py`.
   - **Note:** that referenced `variant-coordinate-finder-skill` exists in NEITHER tree (`ls` confirms absent upstream, in our `sources/`, and anywhere under `life-science-research/`). So OUR version's coordinate path references a missing script — it is effectively dangling. Upstream's inlining is also a *repair* of that dependency.
3. **Richer parsing:** `locus`-field fallback for gene symbols, `sequence_ontology` consequence terms, GRCh38 `degraded` status + `limitations` surfacing, primary-vs-alt/patch placement filtering.

## biomedical-mcp cross-check — the ALPHA is already covered

`biomedical-mcp` is the maintained production layer (v0.6.0); the skill `sources/` are reference scripts. The MCP already resolves the exact capability the upstream refactor improves:

- `src/biomedical_mcp/myvariant.py::_resolve_hg38` (lines 59-92): rsID → **GRCh38** coordinate via `https://rest.ensembl.org/variation/human/{rsid}` (Ensembl, cached). Different and more robust mechanism than NCBI RefSNP `/beta/`.
- `myvariant.py` default fields pull `clinvar,gnomad_exome,gnomad_genome,cadd,dbnsfp.genename,…,dbsnp` → rsID → **gene symbol + consequence** via dbNSFP/dbSNP/ClinVar (lines 16-17, 178, 207, 215-222).
- `variant_input.py::normalize_variant` already classifies/normalizes rsID input (lines 45-71).
- `ensembl.py`, `mygene.py`, `litvar.py` provide adjacent locus/variant resolution.

So the one ALPHA's value (rsID → GRCh38 coords + gene) is implemented in production by MyVariant.info + Ensembl — NOT a gap. The upstream change fixes a brittle NCBI-RefSNP path in a reference script we don't run in production.

## VERDICT

### SAFE TO DELETE

- 50/50 shared skills: content byte-identical after accounting for the `INSTRUCTIONS.md`→`SKILL.md` rename (NOISE) + one doc-example id (pharmgkb, NOISE).
- 1/50 with real logic change (`locus-to-gene-mapper`): its capability is already covered — better — in `biomedical-mcp/myvariant.py`. No NEW data source, endpoint, or output field that the MCP lacks.
- No new skills upstream (50 upstream ⊂ 55 ours; we are a strict superset by name and ahead by 5 skills).

**Optional, non-blocking nicety (NOT a delete-gate):** if we still want the *reference* `sources/locus-to-gene-mapper-skill/scripts/map_locus_to_gene.py` to be runnable standalone, port the upstream `/beta/`-URL fix + inlined `resolve_refsnp_coordinates` from `~/.codex/plugins/cache/openai-curated/life-science-research/c6ea566d/skills/locus-to-gene-mapper-skill/scripts/map_locus_to_gene.py`. This repairs our dangling `variant-coordinate-finder-skill` reference. But production (the MCP) does not depend on it, so deletion of the upstream cache loses nothing irreversible — the file is preserved in this memo's path reference and in git-tracked `sources/`.

**Delete is reversible anyway:** the upstream is a re-pullable Codex plugin cache (`openai-curated`), not unique state. The gate is satisfied.
