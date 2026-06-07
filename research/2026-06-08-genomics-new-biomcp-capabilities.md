---
title: "Genomics × biomedical-mcp v0.6.0 Gap Analysis"
date: 2026-06-08
status: complete
tags: [genomics, biomedical-mcp, pgx, civic, oncokb, ddinter, cpic, integration]
---

# Genomics × biomedical-mcp v0.6.0 Gap Analysis

## 1. How Genomics Consumes Biomedical Data Today

Genomics has three distinct consumption paths for biomedical data:

### Path A: Own HTTP client (`biomedical_client.py`)
`scripts/biomedical_client.py` is a standalone 1220-line module wrapping 9 APIs directly:
MyVariant.info (ClinVar), Open Targets GraphQL (disease associations + **OT pharmacogenomics**),
UniProt, OpenFDA (drug labels), STRING (PPI), ClinicalTrials.gov, MyGene.info, PhenoScanner,
OT Genetics L2G. Runs on Modal in `modal_biomedical_enrichment.py` (Stage: `biomedical_enrichment`).

Key capability already present: `BiomedicalClient.pharmacogenetics()` queries OT's
`pharmacogenomics` GraphQL endpoint (returns variant/genotype/phenotype/drug/evidence_level rows).
`BiomedicalClient.enrich_pgx_gene()` combines OT PGx + FDA label warnings. This is the
**primary PGx enrichment path** in the pipeline.

### Path B: biomedical-mcp Python library (direct import)
`enrich_review_packets.py` and `gene_lookup.py` import biomedical-mcp modules directly
(GnomAD, GTEx, HGNC, HPO, PanelApp, LitVar) — NOT via MCP protocol. This predates the
composite consolidation and only uses pre-v0.6.0 domain modules.

### Path C: biomedical-mcp MCP server (`biomedical` in `.mcp.json`)
Wired into `.mcp.json` as `"biomedical": {"command": "biomedical-mcp"}`. Used interactively
by agents for audit/curation work (`composite_variant_context` referenced in
`docs/audit/trait-claim-curation-2026-06-02/`). NOT called programmatically from pipeline stages.

### Path D: ClinPGx REST API (direct, two places)
`hla_drug_disease_lookup.py` calls `https://api.cpicpgx.org/v1` directly for HLA gene
annotations. `drain_cpic_verification.py` calls `https://api.clinpgx.org/data` to write
bio-verify receipts for CPIC-sourced claims in the claim registry.

### Path E: CIViC flat-file download
`chip_germline_crossref.py` loads a downloaded `ClinicalEvidenceSummaries.tsv` from
`Paths().db_dir / "civic"`. Scoped to germline/predisposing records only. `refresh_databases.py`
probes `https://civicdb.org/downloads/nightly/` for freshness. This is a static file, not a
live API call.

**Critical finding:** The `biomedical` MCP server (v0.6.0) is **wired in `.mcp.json`** but
no pipeline stage imports or calls its composite tools (`gene_dossier`, `variant_context`,
`drug_profile`) programmatically. It is used by agents during interactive sessions only.
There is no `ONCOKB_TOKEN` configured anywhere in genomics.

---

## 2. Gap Analysis: Three New v0.6.0 Sources

### 2a. CPIC/ClinPGx Pharmacogenomics (`clinpgx.py`)

**What biomedical-mcp adds:** `ClinPGx.pgx_for_gene()` and `pgx_for_drug()` return the live
CPIC `pair_view` (gene-drug pairs with CPIC levels A-D and `clinpgx_level` e.g. "1A"/"2A")
AND the `recommendation_view` (phenotype→dose-recommendation rows, implications, classification,
population, comments). This includes structured dose recommendations keyed by diplotype/phenotype —
e.g. "Poor Metabolizer → avoid codeine, use alternative."

**What genomics already has:**
- `BiomedicalClient.pharmacogenetics()` → OT pharmacogenomics (genotype/phenotype/drug/evidence_level).
  This is Open Targets' derived layer, NOT live CPIC recommendations.
- `drain_cpic_verification.py` → queries ClinPGx API for claim verification receipts.
  Reads `clinpgxlevel` but does NOT extract dose recommendations into pipeline outputs.
- `hla_drug_disease_lookup.py` → queries ClinPGx for HLA genes specifically.
- `config/pgx_evidence_levels.json` → hand-curated A/B/C level index for ~20 gene-drug pairs.
- `generate_pgx_card.py` → PharmCAT-driven PGx summary card with traffic-light drug classes.

**The gap:** Genomics does NOT feed live CPIC phenotype→dose-recommendation rows into any
report or finding. The `enrich_pgx_gene()` function uses OT PGx (indirect, GWAS-derived) + FDA
labels, but never the CPIC `recommendation_view` which carries clinical-grade actionable guidance:
"UM → use alternative," "PM → 50% dose reduction," etc. The `pgx_evidence_levels.json` is
hand-curated and covers ~20 pairs; CPIC has 100+ gene-drug pairs.

**Value:** High for PGx report card quality. The `recommendations` array in `clinpgx.pgx_for_gene()`
maps directly to what `generate_pgx_card.py` renders as traffic-light drug classes — currently
this is driven by the hand-curated config, not live CPIC data.

**Note:** `gene_dossier`'s `pharmacogenomics` section already calls `clinpgx.pgx_for_gene()` —
this is the v0.6.0 addition. But genomics doesn't call `gene_dossier` from pipeline stages.

### 2b. DDInter Drug-Drug Interactions (`ddinter.py`)

**What biomedical-mcp adds:** `DDInter` looks up drug pairs by severity (1=Minor, 2=Moderate,
3=Major) with mechanism flags (absorption, distribution, metabolism, excretion, synergistic,
antagonistic). Returns interactions via a web-scraping-style AJAX endpoint (no documented API).

**What genomics already has:**
- `pgx_polypharmacy_network.py` builds a bipartite drug↔enzyme graph weighted by fraction
  metabolized (fm), computing bottleneck scores per enzyme. Uses CPIC PK fractions + phenoconversion
  (inhibitor-induced phenotype downgrade). This is a PK-based DDI model, not a clinical evidence
  database lookup.
- `bilirubin_interaction.py` is a single-gene (UGT1A1) bilirubin interaction check.
- `biomedical_client.py` fetches FDA label `drug_interactions` sections as unstructured text.

**The gap:** Genomics has PK-level polypharmacy (enzyme bottleneck model) and FDA label text,
but NO structured severity-graded DDI lookup against a curated drug-drug interaction database.
DDInter would add severity labels (Major/Moderate/Minor) and mechanism flags to the
polypharmacy finding. However: DDInter uses undocumented AJAX endpoints (not a stable public API —
biomedical-mcp itself notes this). The DDI domain is also somewhat distinct from the germline
interpretation pipeline's core value proposition.

**Value:** Medium-low. The polypharmacy network already handles the core CYP-mediated DDI risk.
DDInter adds cross-CYP pharmacodynamic interactions that the PK model misses, but the genomics
consumer for this finding (`pgx_polypharmacy` → `finding_adapters_pgx.py`) is already fairly
rich. Clinically, DDI is usually managed by prescribers, not a genomics report.

### 2c. CIViC + OncoKB Somatic Annotation (`somatic.py`)

**What biomedical-mcp adds:** `Somatic.civic_evidence(gene, protein_change)` queries CIViC
GraphQL live for clinical evidence items (type/level/significance/disease/therapies/PMIDs).
`Somatic.oncokb_annotate(gene, protein_change)` queries OncoKB for oncogenicity, mutation
effect, treatment levels, and diagnostic/prognostic implications. OncoKB requires `ONCOKB_TOKEN`.

**What genomics already has:**
- `chip_germline_crossref.py` loads CIViC flat-file (`ClinicalEvidenceSummaries.tsv`) for
  **germline/predisposing** records only — filtered by `variant_origin="germline"` and
  `evidence_type="predisposing"`. Cross-referenced against Mutect2 CHIP candidates.
- `dataset_registry.py` lists `"civic"` in `_DATASET_LEDGER_EXCEPTIONS` (still downloading
  static TSV, not live API). No claims in `claim_registry.json` cite CIViC as source.
- No OncoKB anywhere in the codebase.
- `chip_deepsomatic` stage detects clonal hematopoiesis candidates (DeepSomatic). The
  downstream CIViC crossref uses the TSV, not the live GraphQL API.

**The gap (germline side):** The live CIViC GraphQL API in biomedical-mcp offers much more
than the static TSV: it returns full evidence items including treatment implications per
molecular profile, and the variant_context composite can return the `somatic` section for
any gene+protein-change input (e.g. "BRCA1 c.5266dup" wouldn't work — needs protein-change
format like "p.Gln1756Profs*74"). The static TSV path is already working for the germline/CHIP
use case. Live API adds freshness (nightly builds vs static download) and structured treatment
levels.

**The gap (somatic oncology):** Genomics is a germline WGS pipeline. Its CHIP stage
(`chip_deepsomatic`) detects somatic clonal hematopoiesis variants in blood, but does NOT
interpret them against CIViC's somatic evidence items or OncoKB's oncogenicity assessments.
A CHIP variant (e.g. DNMT3A R882H, TET2 Q1939*, JAK2 V617F) currently gets cross-referenced
against the germline CIViC TSV only — which will be empty for somatic drivers.

**OncoKB status:** No ONCOKB_TOKEN in genomics configuration. OncoKB requires institutional
or research API access (not open). CIViC is open.

---

## 3. Claims Registry Reinvestigation Potential

**Registry state:** 993 claims, 38 cite CPIC/PharmGKB sources (`guideline:cpic_level_a_2026_03`,
`pmid:35152405`). 0 claims cite CIViC directly (CIViC is consumed via static file, not claims).

**Claim types touched by new evidence:**

### CPIC/ClinPGx → PGx interpretation_rule claims
38 claims on `pgx_evidence_levels` and `pgx_pathway_interactions` surfaces cite CPIC sources.
These are interpretation rules like "DPYD PM → reduce fluorouracil dose." The live
`recommendation_view` from ClinPGx provides structured recommendation text and classification
that could:
- (a) Confirm existing interpretation rules (confidence up) — most likely outcome
- (b) Flag updated evidence level (CPIC periodically revises A↔B) — medium likelihood
- (c) Add new gene-drug pairs not in the hand-curated config — e.g. CPIC has added PGx guidance
     for ~30 drugs since 2023

`drain_cpic_verification.py` already queries ClinPGx for these claims and writes bio-verify
receipts. The reinvestigation is already partially automated. What it does NOT do is compare
`recommendation_view` text against the stored recommendation in `pgx_evidence_levels.json`.

**Safe-autonomous:** Extend `drain_cpic_verification.py` to also extract the `drugrecommendation`
field and compare against the human-curated text in `config/pgx_evidence_levels.json`. Flag
divergences to the needs_human_queue, don't auto-update. This is data extraction, not clinical
reclassification.

### CIViC live API → CHIP variant interpretations
`chip_germline_crossref.py` currently uses a static nightly TSV. Switching to the live CIViC
GraphQL API via `biomedical_mcp.somatic.Somatic.civic_evidence()` would:
- Improve freshness (nightly TSV vs real-time GraphQL)
- Return structured `evidence_level` / `significance` / `therapies` per evidence item
- Support somatic molecular profiles (e.g. "DNMT3A R882H") that the germline filter excludes

This is safe-autonomous for the API switch itself (structural). Any resulting change in which
CIViC records are surfaced (e.g. now including somatic records for CHIP genes) is data
enrichment, not claim reclassification.

### OncoKB → CHIP oncogenicity grading
If `ONCOKB_TOKEN` were available, OncoKB's oncogenicity + treatment level could attach to each
CHIP candidate (e.g. JAK2 V617F = Oncogenic, Level 2 therapeutic for MPN). This would be a
new evidence layer, not a reclassification of existing claims — there are no OncoKB-sourced
claims currently.

**Clinical checkpoint required:** Any change that promotes a CHIP variant to a clinical
finding based on CIViC/OncoKB evidence requires human review. CHIP has complex penetrance
(VAF-dependent, clone-size dependent) and its clinical significance for healthy individuals
differs from cancer patients.

---

## 4. Integration Recommendations (Ranked)

### Priority 1 — SAFE AUTONOMOUS: Wire ClinPGx `recommendation_view` into `enrich_pgx_gene()`

**What:** Extend `BiomedicalClient.enrich_pgx_gene()` (or a new `enrich_pgx_gene_v2()`) to also
call `ClinPGx.pgx_for_gene(gene_symbol)` and attach the structured `recommendations` array to the
enrichment output. The `gene_dossier`'s `pharmacogenomics` section in biomedical-mcp already does
this cleanly — genomics can import `ClinPGx` directly (same as it does for gnomAD, GTEx etc. in
`enrich_review_packets.py`).

**Where:** `scripts/modal_biomedical_enrichment.py` Step 3 (PGx enrichment). Also `generate_pgx_card.py`
to replace/supplement the hand-curated `_PGX_EVIDENCE_LEVEL_INDEX` with live CPIC data.

**Value:** Replaces the ~20-pair hand-curated `pgx_evidence_levels.json` with ~100+ live CPIC
gene-drug pairs and structured dose recommendations. Eliminates a maintenance burden and a
freshness risk (hand-curated file can drift from CPIC guidelines).

**Effort:** Low — `ClinPGx` class is already in the installed `biomedical-mcp` package. The
cache and BaseClient infrastructure is shared. One import + one method call per PGx gene.

**Autonomous:** Yes. This is data enrichment to an existing output file. No claim reclassification.
Existing `drain_cpic_verification.py` receipts validate the source.

---

### Priority 2 — SAFE AUTONOMOUS: Add ClinPGx coverage check to `drain_cpic_verification.py`

**What:** After querying the ClinPGx API, compare `drugrecommendation` text against the stored
interpretation in `config/pgx_evidence_levels.json`. Write a divergence flag to the bio-verify
receipt. Route divergences to `needs_human_queue`.

**Where:** `scripts/drain_cpic_verification.py`, after the existing receipt write.

**Value:** Turns a binary "confirmed/contradicted" receipt into a structured divergence detector.
The 38 CPIC-sourced claims can be checked for drift without triggering reclassification.

**Effort:** Low (10-20 lines).

**Autonomous:** Yes.

---

### Priority 3 — SAFE AUTONOMOUS: Upgrade CHIP CIViC lookup from static TSV to live GraphQL

**What:** Replace `load_civic_evidence()` in `chip_germline_crossref.py` (reads static
`ClinicalEvidenceSummaries.tsv`) with `biomedical_mcp.somatic.Somatic.civic_evidence(gene, protein_change)`.
The live API allows filtering by `variantOrigin` at query time (no need for pre-filter on TSV).

**Note on scope guard:** The existing TSV loader filters to `variant_origin="germline"` only.
The live API can query the same filter OR also retrieve somatic evidence for CHIP candidates.
Keeping the germline-only filter maintains current behavior; removing it adds somatic CIViC
records to the CHIP finding (see Priority 5).

**Where:** `scripts/chip_germline_crossref.py`

**Value:** Freshness (nightly TSV download eliminated), structured evidence levels, no static
file maintenance. Small net improvement.

**Effort:** Low — swap the loader function. Need to construct `protein_change` from variant
data (CHIP candidates come in as genomic coords; need HGVSp translation, or fall back to
gene-only query).

**Autonomous:** Yes (germline-only mode). Extending to somatic = Priority 5 below.

---

### Priority 4 — SAFE AUTONOMOUS: Add DDInter severity layer to polypharmacy finding (opt-in)

**What:** In `pgx_polypharmacy_network.py`, for the top bottleneck drug pairs identified by
the fm-weighted model, call `DDInter.drug_interactions(drug_name)` to annotate with severity
level (Major/Moderate/Minor) and mechanism type. Write as an optional `ddinter_severity` field
on each bottleneck pair.

**Caution:** DDInter uses undocumented AJAX endpoints — biomedical-mcp's own docs flag this.
Rate limiting and endpoint stability are unknown. Add a try/except wrapper with a fallback to
"no severity data" rather than failing the stage.

**Where:** `scripts/pgx_polypharmacy_network.py`, after bottleneck scoring.

**Value:** Medium. Adds a clinical severity label that's currently missing. But the PK model
already captures the most important DDIs (CYP enzyme competition), and prescribers manage DDI
clinically. Low urgency.

**Effort:** Low-medium (add `DDInter` import + per-pair lookup with timeout).

**Autonomous:** Yes (best-effort data enrichment, no clinical decisions).

---

### Priority 5 — HUMAN CHECKPOINT: Add somatic CIViC evidence to CHIP candidates

**What:** In `chip_germline_crossref.py` (or a new `chip_somatic_interpretation.py`), for each
CHIP variant with a known protein change, query CIViC for somatic evidence items (evidence_type=
Predictive/Prognostic, variant_origin=SOMATIC). Attach to the CHIP finding as `civic_somatic_evidence`.

**Why human checkpoint:** CHIP variants in healthy individuals have different clinical significance
than the same variant in a cancer patient. CIViC evidence levels (A-E) apply to the cancer
context. Surfacing a "Level A" therapeutic implication (e.g. JAK2 V617F → ruxolitinib for MPN)
on a CHIP finding without clinical interpretation would be misleading. Requires clinical
geneticist review before surfacing to report.

**Value:** High if the CHIP stage is clinically reported (adds structured oncology context to
CHIP candidates like DNMT3A R882H, TET2, JAK2 V617F). Medium if CHIP is research-only.

**Effort:** Medium (need HGVSp from CHIP variants, CIViC query, finding model extension,
clinical note template).

---

### Priority 6 — BLOCKED ON TOKEN: OncoKB oncogenicity for CHIP candidates

**What:** If `ONCOKB_TOKEN` is obtained, `Somatic.oncokb_annotate(gene, protein_change)` returns
oncogenicity ("Oncogenic"/"Likely Oncogenic"/"VUS") + treatment levels for each CHIP candidate.
This is the most clinically actionable addition for the CHIP pipeline.

**Blocked by:** No `ONCOKB_TOKEN` in genomics. OncoKB's research API requires academic/institutional
registration at oncokb.org/apiAccess. Obtain before implementing.

**Note:** Even with the token, this is a human-checkpoint integration per Priority 5 reasoning.

**Autonomous:** No — requires token acquisition + clinical review policy for surfacing.

---

### Non-recommendation: Replacing `biomedical_client.py` pharmacogenetics with `gene_dossier`

**Do NOT:** Replace the entire `BiomedicalClient.enrich_pgx_gene()` path with calls to the
`gene_dossier` MCP composite. The pipeline runs on Modal (no MCP server available on GPU
instances). `biomedical_client.py` is Modal-compatible; MCP protocol is not. The right pattern
(as done in `enrich_review_packets.py`) is direct Python import of biomedical-mcp modules, not
MCP protocol calls.

---

## 5. Summary Table

| Integration | Autonomous? | Effort | Value | Blocks On |
|---|---|---|---|---|
| 1. ClinPGx dose recs into `enrich_pgx_gene` | Yes | Low | High | Nothing |
| 2. ClinPGx divergence check in `drain_cpic` | Yes | Low | Medium | Nothing |
| 3. Upgrade CHIP CIViC to live GraphQL | Yes | Low | Medium | HGVSp from CHIP coords |
| 4. DDInter severity layer on polypharmacy | Yes | Low-med | Low-med | AJAX stability risk |
| 5. Somatic CIViC on CHIP candidates | No — human checkpoint | Medium | High | Clinical review policy |
| 6. OncoKB for CHIP | No — blocked | Medium | High | ONCOKB_TOKEN |

---

## 6. Key Findings Summary

1. **No new-capability gap on `variant_context`:** Genomics already has ClinVar + gnomAD +
   GWAS Catalog via its own `BiomedicalClient`. The v0.6.0 `somatic` section of `variant_context`
   is the only genuinely new layer — and it's opt-in for a reason (somatic is not a germline
   pipeline default).

2. **CPIC dose recommendations are the highest-value gap.** Genomics has CPIC level assignment
   and claim verification, but NOT structured dose recommendations in pipeline outputs. These
   are the clinically actionable "what to prescribe" rows and live in the ClinPGx
   `recommendation_view` table — not in Open Targets' PGx endpoint (which genomics already queries).

3. **CIViC is already integrated but via a stale path.** The static TSV is adequate for
   germline/predisposing use, but switching to the live API is a low-effort improvement.
   The somatic CIViC layer is a new capability for CHIP interpretation.

4. **OncoKB is entirely absent and requires a token.** This is the biggest potential capability
   gap for oncology-focused CHIP interpretation, but it is blocked by access, not code.

5. **`gene_dossier`'s `pharmacogenomics` section IS what genomics needs** — but genomics
   should import `ClinPGx` directly (Python) not call `gene_dossier` via MCP (doesn't work
   on Modal). The thin integration path is already proven by how `enrich_review_packets.py`
   imports biomedical-mcp modules.

6. **DDInter is lowest priority.** The polypharmacy network already covers CYP-mediated DDIs
   with a rigorous PK model. DDInter adds pharmacodynamic severity labels but the unstable
   AJAX endpoint is a reliability risk.
