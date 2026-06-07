---
title: Biomedical Ontologies & Datasets — 2026 Delta vs Prior Baselines
date: 2026-06-07
tags: [ontologies, genomics, phenome, pharmacogenomics, datasets, HPO, MONDO, ClinVar, OpenTargets, CPIC]
status: complete
---

# Biomedical Ontologies & Datasets — 2026 Delta

**Scope:** What changed in 2026 that is NEW vs the baselines in:
- `supplement-database-survey-2026-04.md` (baseline: Apr 2026)
- `scientific-kg-schema-standards-2026-05.md` (baseline: May 2026)
- `scientific-citation-graph-patterns-2026-05.md` (baseline: May 2026)
- phenome HP/MONDO roadmap (OlsTermClient already in use)

Sources graded: D1 = primary release page/GitHub; D2 = secondary (blog, docs); D3 = tertiary.
All release dates/versions independently verified against primary sources.

---

## Ontologies Table

| Name | 2026 Change | Release date/version | Source | Value + Difficulty |
|------|-------------|---------------------|--------|-------------------|
| **HPO** | Continuous monthly releases. v2026-02-16: 10 new terms, 29 obsoletions with redirects, 75 renames (symphalangism rationalized), 54 new subClassOf relationships, dcterms:date harmonization (10,225 terms now uniform). New internationalization effort (HPOIE) coordinating multi-language releases in lock-step via Babelon/Crowdin. | v2026-02-16 (latest confirmed) | D1: github.com/obophenotype/human-phenotype-ontology/releases | Value: HIGH — obsoletions with redirects break naive ID lookups; OlsTermClient needs redirect-aware term resolution. Difficulty: LOW — sync monthly HPOA download |
| **MONDO** | Major top-level restructuring merged Mar 27, 2026 (PR #10004): four orthogonal classification axes added to MONDO:0700096 (human disease) children — etiology, body system, severity, and inheritance — using multiple inheritance, not mutual exclusion. 156 new terms in Mar 3 release. Ongoing sub-monthly cadence. | v2026-03-03 (156 new terms); restructure merged v2026-03-27 | D1: github.com/monarch-initiative/mondo/releases, PR #10004 | Value: HIGH — top-level axis restructuring changes disease grouping logic upstream of phenome HP/MONDO links. Difficulty: MED — OlsTermClient already consumes MONDO; verify ancestor queries still work after axis restructure |
| **DOID (Human Disease Ontology)** | Mar 2026 release: 12,079 disease classes (81.1% with textual definitions). Large UMLS cross-reference update. Spanish translations (98% labels, 58.8% synonyms, 67.3% definitions). Groups expanded: CMT, dilated cardiomyopathy, hereditary sensory neuropathy, retinal vascular occlusion, 15+ others. | v2026-03-31 | D1: github.com/DiseaseOntology/HumanDiseaseOntology/releases | Value: MED — useful as cross-reference; UMLS xref update matters for phenome cross-mapping. Difficulty: LOW |
| **OAK (Ontology Access Kit)** | v0.7.0rc1–rc4 in active release cycle (Apr 2026 RC, Lawrence Berkeley Lab + EBI contributors). New: non-redundant entailed relationships, enriched mapping documentation, definition validation functionality, statistics notebook. RC status means not yet stable API. OlsTermClient in phenome is upstream of OAK, so primary impact is via EBI OLS4. | v0.7.0rc4 (2026-04-12, pre-release) | D1: github.com/INCATools/ontology-access-kit/releases | Value: MED for direct use (RC = unstable); HIGH for monitoring — OAK v0.7 stable will ship as the standard programmatic interface for HPO/MONDO traversal. Difficulty: LOW to monitor, MED to adopt early |
| **EBI OLS4** | Production LLM-powered semantic search now using `llama-embed-nemotron` (confirmed Apr 2026 issue #1238). Self-hosted embedding path documented but undocumented for non-Kubernetes deploys. Pipeworx MCP gateway wrapping OLS4 released May 2026 (pipeworx-io/mcp-ebi-ols): list_ontologies, get_term, term_ancestors, term_children. | Active (2026); Pipeworx MCP: 2026-05-14 | D1: github.com/EBISPOT/ols4; D2: Pipeworx repo | Value: MED — OlsTermClient already hits OLS4 REST; semantic search is additive for fuzzy phenotype NLP. Difficulty: LOW (OlsTermClient already wired); MED for semantic search layer |
| **Monarch dismech** | New repo: monarch-initiative/dismech (Disease Mechanisms KB). As of v0.1.24 (May 2026): 1,000+ disorders, structured pathographs linking mechanisms, endpoints/readouts, and FDA surrogate endpoints. KGX export to biolink-model edges. Comorbidity/sequelae edges now typed separately (disease-to-disease, not disease-to-phenotype). AI-assisted curation with human review (Claude Code used explicitly in PRs). | v0.1.24 (2026-05-11) | D1: github.com/monarch-initiative/dismech | Value: HIGH for mechanism-level disease interpretation (NEW — not in any prior memo). Difficulty: MED — KGX jsonl download, no REST API yet |
| **EFO** | EFO tracks GWAS Catalog and Open Targets releases; no standalone major restructuring found in 2026. Open Targets 26.03 updated EFO-linked disease/phenotype count to 47,030. | Updated with OT 26.03 (2026-03-23) | D2: platform.opentargets.org | Value: LOW delta — EFO changes ride on OT release train |
| **ChEBI** | Mirror URL updated in HPO pipeline (Jan 2026, PR #11429). No standalone major release found in 2026 search. ChEBI REST API unchanged. | Ongoing | D1 (indirect, HPO PR) | Value: LOW delta — existing DSLD/ChEMBL supplement mapping still valid |
| **Cell Ontology / Uberon / GO** | No major 2026 releases surfaced in this sweep. Monarch KG continues to integrate these. Single-cell eQTL credible sets in Open Targets 26.03 (52,738 sceQTL credible sets) are CL-linked at tissue level. | Ongoing | D3 | Value: LOW delta for current stack; revisit if single-cell layer added |

---

## Datasets Table

| Name | 2026 Change | Release date/version | Source | Value + Difficulty |
|------|-------------|---------------------|--------|-------------------|
| **ClinVar** | March 2026: Submission API updated to accept functional data from MAVEs (Multiplexed Assays of Variant Effects). New schema fields: better categorization, detailed descriptions, enhanced metadata for functional evidence. This is the first structured pathway to ingest saturation genome editing / DMS scores into ClinVar submissions at scale. Download files and website updated to show functional evidence. | 2026-03-02 (API schema update) | D1: ncbiinsights.ncbi.nlm.nih.gov/2026/03/02/update-clinvar-submission-api/ | Value: HIGH — MAVE functional scores are rapidly becoming gold standard for VUS reclassification; this changes what ClinVar returns for interpreted variants. Difficulty: LOW to consume (API backward compatible) |
| **gnomAD v4.1.1** | Bug fix release from v4.1.0: removed constraint metrics display for genes with zero expected variants in any class (synonymous, missense, LoF) — flagged as poorly calibrated. Constraint TSV still contains all genes. No gnomAD v5 announcement confirmed as of 2026-06-07 (verify_claim would be needed for any v5 claims). | v4.1.1 (confirmed May 2026 discussion) | D1: discuss.gnomad.broadinstitute.org/t/gnomad-v4-1-1-update | Value: MED — calibration fix matters for gene constraint lookups; affects pipeline handling of zero-expected genes. Difficulty: LOW — update constraint table download |
| **Open Targets Platform 26.03** | Released 2026-03-23. Key changes: (1) New clinical mining pipeline: 285,213 clinical reports from ClinicalTrials.gov/AACT + ChEMBL indications + drug warnings + TTD + EMA + PMDA — now 13 clinical stages with granular provenance. (2) ENCODE rE2G (Enhancer-to-Gene) regulatory predictions embedded in L2G: new features `e2gMean`, `e2gNeighbourhoodMean`. (3) Shapley value L2G explainability. (4) GWAS Catalog: 710 new studies, 5,000+ new credible sets. (5) ~98% date coverage on associations for novelty estimation. (6) Schema change: unified `timeseries` field in association dataset — BREAKING for existing bulk Parquet consumers. Scale: 7.43M variants, 34M evidence, 12.5M associations. | 26.03 (2026-03-23) | D1: blog.opentargets.org, platform-docs.opentargets.org/release-notes, community.opentargets.org/t/26-03-release-now-live/1987 | Value: HIGH — two actionable additions: (a) E2G in L2G improves gene prioritization for non-coding GWAS hits relevant to our stack; (b) association schema breaking change requires Parquet consumer update if consuming bulk data. Difficulty: MED — schema migration for Parquet consumers; GraphQL API backward compatible |
| **CPIC / ClinPGx migration** | CPIC data v1.55.0 (Mar 2026): BREAKING — columns renamed `pgkbcalevel` → `clinpgxlevel`; guideline URLs changed to clinpgx.org. PharmGKB rebranded to ClinPGx. Practical effect: any code using CPIC DB API or `cpic-data` TSVs that references `pgkbcalevel` or old PharmGKB links is broken. New TPMT/NUDT15 thiopurine guideline (2025–2026 update): NUDT15*2 removed, consolidated under *3 (suballele). Compound TPMT/NUDT15 intermediate metabolizers: greater dose reduction now recommended. CYP2C19*42 added (Feb 2026). | v1.55.0 (2026-03-13); TPMT/NUDT15 guideline Feb 2026; CYP2C19*42 Feb 2026 | D1: github.com/cpicpgx/cpic-data/releases, blog.clinpgx.org | Value: HIGH — BREAKING rename in CPIC DB; if biomedical-mcp or genomics pipeline uses `pgkbcalevel` column, it returns NULL silently. NUDT15*2 removed from allele definitions. Difficulty: LOW fix (rename column ref) but HIGH impact if undetected |
| **PharmCAT v3.2.0** | Released 2026-02-25: (1) F2 and F5 coagulation factor genes added to named allele matching (relevant for anticoagulant PGx). (2) NUDT15 repeat wobble (*3 suballeles) now handled. (3) Data sync with PharmVar + ClinPGx. | v3.2.0 (2026-02-25) | D1: github.com/PharmGKB/PharmCAT/releases | Value: HIGH for anticoagulant use cases — F2/F5 calling NEW. Difficulty: LOW if running PharmCAT directly; MED if consuming its output schema |
| **GWAS Catalog** | 710 new studies, 5,000+ new credible sets ingested into Open Targets 26.03. Hypothyroidism study alone contributed 780 credible sets. 52,219 unique studies total. Ongoing EBI-hosted full data available. | Via OT 26.03 (2026-03-23); standalone GWAS Catalog updated continuously | D1: Open Targets release notes | Value: HIGH — 5K new credible sets = more variant→disease links, many relevant to common complex traits. Difficulty: LOW via existing OT GraphQL |
| **Monarch dismech KGX export** | Disease mechanism pathographs exportable as biolink-model KGX jsonl edges. 1,000+ disorders. Endpoints/readouts linked. Comorbidity edges typed as `biolink:associated_with` disease-to-disease. | v0.1.24 (2026-05-11) | D1: github.com/monarch-initiative/dismech | Value: HIGH — mechanism-level causal subgraphs not available anywhere else at this fidelity. No REST API yet; bulk download only. Difficulty: MED — download KGX jsonl, parse biolink edges, integrate with existing OT/OMIM disease layer |
| **AlphaMissense / AlphaGenome** | No new AlphaMissense version release confirmed in 2026 search (v1 remains the reference). AlphaGenome (Nature Jan 2026 memo already in corpus at genomics-foundation-models-2026-04.md) — no new version. The pipeline already references AlphaGenome. | Prior baseline (already in corpus) | See genomics-foundation-models-2026-04.md | Value: No delta in this sweep |
| **ClinGen** | 3,894 genetic evidence entries in Open Targets 26.03. No standalone ClinGen schema change found in this sweep. | Via OT 26.03 | D2 | Value: LOW delta |
| **Orphanet / ORDO** | 7,245 genetic evidence entries in Open Targets 26.03. Orphanet data feeds the Monarch KG. No standalone ORDO restructuring found in this sweep. | Via OT 26.03 | D2 | Value: LOW delta |
| **NIH DSLD (Dietary Supplement Label Database)** | No 2026 update confirmed in this sweep. Prior baseline: quarterly updates, last assessed Apr 2026 in supplement survey. | Prior baseline | supplement-database-survey-2026-04.md | Value: Already assessed — no delta |
| **OpenFDA CAERS** | No 2026 structural change found. Quarterly updates continue. | Prior baseline | supplement-database-survey-2026-04.md | Value: Already assessed — not yet wired (HIGH priority from prior memo) |
| **USDA FoodData Central** | No 2026 structural change found. Ongoing updates. | Prior baseline | supplement-database-survey-2026-04.md | Value: Already assessed — not yet wired (HIGH priority from prior memo) |

---

## Key Findings Not in Tables

### 1. CPIC→ClinPGx Rename Is a Silent Breaking Change

The `pgkbcalevel` → `clinpgxlevel` column rename in cpic-data v1.55.0 is the highest-urgency finding. If the biomedical-mcp or genomics pipeline uses the CPIC DB API and references this column by name (as most codebases do), it now returns NULL. The `cpicpgx` API documentation has been updated but old client code has not. Check with `grep -r "pgkbcalevel" ~/Projects/genomics ~/Projects/biomedical-mcp`.

### 2. Open Targets Bulk Parquet Schema Changed

OT 26.03 association dataset added a unified `timeseries` embedded field. Any code that reads association Parquet files with a fixed schema (column positional reads, strict schema validation) will fail. GraphQL API is backward compatible. If the biomedical-mcp uses the bulk download path, this needs a schema migration.

### 3. MONDO Top-Level Restructuring Affects Ancestor Queries

The four-axis restructuring of MONDO:0700096 (merged Mar 27) adds new intermediate nodes in the is-a hierarchy. Any query that traverses ancestors to classify diseases into body-system or etiology categories will now find additional intermediate nodes. This is a positive change for richness but may break hard-coded path counts or ancestor-set comparisons in the phenome HP/MONDO linking logic.

### 4. Monarch dismech is New and Unassessed

The dismech KB (Disease Mechanisms KB) did not exist in any prior memo. It is a structured causal pathograph database — mechanism nodes, gene nodes, phenotype nodes, drug/endpoint nodes — with KGX export in biolink-model format. At 1,000+ disorders it is small but fast-growing (AI-assisted curation). This is the only structured disease-mechanism graph with a usable bulk export in the Monarch ecosystem. The genomics pipeline currently does not have a mechanism-level layer between variant and clinical phenotype; dismech fills this gap.

### 5. OAK v0.7 RC Status

OAK is the correct programmatic interface for HPO/MONDO OBO traversal (used by Monarch tooling). The v0.7 RC series (Apr 2026) is active but not stable. OlsTermClient in phenome already wraps EBI OLS4, which is the right choice for production. OAK v0.7 stable would be worth evaluating when it exits RC — it adds non-redundant entailed relationships and definition validation that could strengthen phenotype-linking quality.

### 6. ClinVar MAVE Functional Data Is Now Ingested Upstream

ClinVar now accepts MAVE/DMS scores via the Submission API (Mar 2026). This means ClinVar downloads will increasingly contain functional evidence for variants previously classified as VUS. The variant interpretation pipeline should track the `functional_consequence` field in ClinVar downloads — this is where MAVE scores surface. Over the next 12–24 months this will reclassify a substantial fraction of VUS toward P/LP.

### 7. PharmCAT F2/F5 Addition

F2 (Factor II / prothrombin) and F5 (Factor V Leiden) are now called by PharmCAT v3.2.0. These coagulation genes are highly relevant for personal genomics (thrombosis risk, warfarin dosing interaction). Previously PharmCAT could not call these. If the genomics pipeline runs PharmCAT, upgrading to 3.2.0 adds two clinically important PGx loci at no integration cost.

---

## Ranked 12-Bullet Priority Summary

1. **CPIC/ClinPGx `pgkbcalevel` → `clinpgxlevel` rename (BREAKING)** — Silent NULL return in any CPIC DB client referencing old column name. Check and fix immediately: `grep -r "pgkbcalevel"` across biomedical-mcp and genomics. Also: NUDT15*2 removed from allele definitions, which affects star-allele calling if using old definitions file.

2. **Open Targets 26.03 Parquet schema change** — The `timeseries` field addition breaks strict Parquet schema consumers. If any part of the stack uses OT bulk downloads (not GraphQL), apply schema migration. Also: 5,000+ new GWAS credible sets immediately available via existing GraphQL interface.

3. **ClinVar MAVE functional data ingestion** — VUS reclassification pipeline should now monitor `functional_consequence` field in ClinVar downloads. The API accepts MAVE scores as of Mar 2026; public downloads will increasingly contain them. This changes the evidence weight for variants currently marked VUS.

4. **PharmCAT v3.2.0: F2/F5 calling** — If the genomics pipeline uses PharmCAT, upgrade to v3.2.0 to get coagulation factor PGx (F2/F5) at zero integration cost. Also: NUDT15 repeat wobble handling for *3 suballeles is now correct.

5. **Monarch dismech — new mechanism-level disease graph** — 1,000+ disorder pathographs with KGX export, mechanism→gene→phenotype→endpoint chains in biolink format. Nothing like this was available before. First step: download KGX jsonl, overlay on existing MONDO/HPO disease graph. Fills the missing mechanism layer between variant and clinical phenotype.

6. **MONDO top-level axis restructure** — Four orthogonal classification axes added to MONDO:0700096 children (merged Mar 2026). Ancestor traversal in phenome HP/MONDO linking will find new intermediate nodes. Verify OlsTermClient ancestor queries still produce correct groupings; update any hard-coded ancestor-depth checks.

7. **HPO monthly releases — redirect-aware term resolution** — HPO now obsoletes ~10–30 terms per monthly release with explicit replacement redirects. The OlsTermClient should use OLS4's redirect mechanism (`obsolete=true` filter + replacement lookup), not just fail on missing term IDs. 29 obsoletions in Feb release alone.

8. **Open Targets L2G + ENCODE rE2G** — E2G regulatory predictions now embedded in L2G scoring (Enhancer-to-Gene from ENCODE). For non-coding GWAS hits, this improves gene prioritization substantially. Access via GraphQL `credibleSet.locus2GeneScore` — new `e2gMean` and `e2gNeighbourhoodMean` features. No code change needed; richer L2G output immediately available.

9. **OAK v0.7 (pre-release, monitor)** — Ontology Access Kit is the programmatic standard for HPO/MONDO traversal. RC series active Apr 2026. Non-redundant entailed relationships and definition validation are useful for phenome quality. Watch for stable release; evaluate as an OlsTermClient complement (not replacement) for batch operations.

10. **gnomAD v4.1.1 constraint calibration fix** — Genes with zero expected variants in any variant class no longer show constraint metrics on the website (but remain in TSV). Pipeline should handle these genes explicitly (mark as uncalibrated, not missing). No gnomAD v5 confirmed as of 2026-06-07.

11. **DOID March 2026 update — UMLS cross-references** — Large UMLS xref update included. If phenome uses DOID→UMLS→SNOMED cross-mapping chains, refresh the DOID OWL download.

12. **Supplement databases (prior HIGH recommendations still unacted)** — OpenFDA CAERS and USDA FoodData Central remain unwired (both flagged HIGH in Apr 2026 survey). These are not superseded by anything in this sweep. Reminder: they are the highest-value not-yet-integrated sources for the supplement evidence stack.

---

## Source Provenance

- D1 (primary): HPO GitHub releases, MONDO GitHub releases, DOID GitHub releases, OAK GitHub, ClinVar NCBI Insights blog, gnomAD Discourse, Open Targets blog + release notes + community, CPIC data GitHub, PharmCAT GitHub, Monarch dismech GitHub
- D2 (secondary): ClinPGx blog (clinpgx.org), Open Targets Platform docs
- D3: None cited

Unverified / not found in this sweep: gnomAD v5 (no announcement), AlphaMissense v2, new GTEx round, new ChEMBL major release, GWAS Catalog standalone API changes. These should be re-checked in 60 days.

<!-- knowledge-index
generated: 2026-06-07T00:00:00Z
hash: auto

title: Biomedical Ontologies & Datasets — 2026 Delta vs Prior Baselines
topics: [HPO, MONDO, DOID, ClinVar, gnomAD, Open Targets, CPIC, ClinPGx, PharmCAT, PharmVar, GWAS Catalog, Monarch, dismech, OAK, supplement databases]
consult_before: [phenome HP/MONDO linking work, biomedical-mcp data source updates, genomics variant interpretation pipeline, CPIC/PGx calling, supplement evidence stack]
end-knowledge-index -->
