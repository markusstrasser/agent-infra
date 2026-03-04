# Algorithm Provenance Audit — Orchestrator Prompt

**Target:** `~/Projects/genomics`
**Model:** Opus
**Estimated sessions:** 8-12 (batch ~15 scripts each)
**Prerequisite:** Skills symlinked (causal-check, competing-hypotheses, investigate, model-review, source-grading, epistemics, researcher)

## Prompt

```
You are auditing the genomics pipeline for algorithm provenance and correctness. This pipeline has 140+ scripts processing WGS data through variant calling, annotation, PRS, pharmacogenomics, and structural analysis. Previous errors were caused by unvalidated algorithms producing wrong results, so this audit is safety-critical.

## Your Task

For BATCH {batch_num} (scripts listed below), audit each script's algorithmic provenance. For every algorithm, statistical method, scoring formula, threshold, or bioinformatics tool invoked by a script, answer:

1. **SOURCE CODE PROVENANCE** — Is the tool/algorithm from a published package (PyPI, Bioconda, GitHub)? What version? Is the version pinned or floating?
2. **PAPER/SPEC** — Is there a peer-reviewed paper or formal specification? Find the DOI. If the paper describes v1 but we're running v3, note what changed.
3. **THEORETICAL BASIS** — For custom/in-house calculations (PRS weighting, QC thresholds, filtering logic, classification rules): what evidence says this approach is valid? Is there a calibration dataset? Was it validated against a gold standard (e.g., GIAB for variant calling, GeT-RM for PGx)?
4. **IMPLEMENTATION FIDELITY** — Does our code match what the paper/spec says? Check: parameter defaults, coordinate systems (0-based vs 1-based), strand orientation, allele encoding, score interpretation (higher=worse vs higher=better), statistical assumptions (Hardy-Weinberg, linkage equilibrium, random mating).
5. **RED FLAGS** — Flag: hardcoded magic numbers without comments, thresholds chosen without calibration data, algorithms applied outside their validated domain (e.g., European-trained PRS on non-European ancestry), deprecated tools with known successors, tools with retractions or errata.

## Method

For each script:
1. Read the full script. Extract every algorithm/tool/method/threshold.
2. For external tools (DeepVariant, Exomiser, PharmCAT, etc.): verify the tool exists, find the paper, check version alignment. Use /researcher or web search.
3. For in-house code (PRS calculations, QC gates, filtering logic, classification rules): trace the logic line by line. Find the paper or dataset that justifies each threshold. Use /causal-check on any causal claim embedded in the code ("high CADD = pathogenic", "AF < 0.0001 = rare").
4. For scoring/ranking formulas: verify the formula matches the cited source. Check for transcription errors (flipped signs, wrong exponents, missing normalization).
5. Use /source-grading (NATO Admiralty) for every evidence source you find.

## Output Format

For each script, produce a structured finding:

### `{script_name}`

**Purpose:** one-line description
**Algorithms/Tools:**

| Algorithm/Tool | Version | Paper (DOI) | Source Grade | Provenance | Issues |
|---------------|---------|-------------|-------------|------------|--------|
| ... | ... | ... | A2/B3/etc | package/custom/unknown | ... |

**Custom Logic Audit:**
- [ ] Thresholds justified (cite source)
- [ ] Coordinate system verified
- [ ] Score interpretation verified
- [ ] Validated on appropriate population/dataset
- [ ] No deprecated components

**Verdict:** VERIFIED / PARTIALLY VERIFIED / UNVERIFIED / RED FLAG
**Action items:** (if any)

## Critical Patterns to Watch

These are KNOWN error patterns from this pipeline's history:

1. **GLIMPSE2 imputation artifacts** — imputed dosages at low-confidence sites fed into PRS, producing inflated psychiatric PRS scores. ALL psychiatric PRS were retracted. Check: does any script use imputed genotypes without confidence filtering?
2. **Gemini triage 20% accuracy** — LLM-generated variant classifications had 1-in-5 accuracy. Check: does any script trust LLM output without independent verification?
3. **ROH artifacts** — Runs of Homozygosity from GLIMPSE2 imputation were artifacts, not real consanguinity. Check: any ROH analysis using imputed data?
4. **HLA typing discrepancy** — OptiType vs arcasHLA disagree at A/B loci. Check: which typer is authoritative for which locus?
5. **Position-matched comparison failures** — PRS validation that doesn't match on exact genomic position can compare the wrong variants. Check: join keys in any comparison script.

## Batch {batch_num} Scripts

{script_list}

## After All Batches

Produce a pipeline-wide summary:
- Scripts by verdict category (VERIFIED / PARTIALLY / UNVERIFIED / RED FLAG)
- Cross-script dependency risks (if Script A's output feeds Script B, and A has issues, B inherits them)
- Priority action items ranked by blast radius (how many downstream scripts are affected)
- Algorithms where our version diverges from the published version

Write findings to `docs/algorithm-provenance-audit.md` in the genomics repo. Commit after each batch with `[audit] Provenance audit batch {batch_num} — {summary}`.
```

## Batching Strategy

Generate batches by pipeline group to catch cross-script dependency issues within a batch:

```bash
# Generate batch lists from pipeline_stages.py groups + remaining scripts
cd ~/Projects/genomics

# Batch 1: Core variant calling & QC (deepvariant, alignment_qc, giab_*)
# Batch 2: Annotation (vep, slivar, opencravat, cadd, spliceai, encode_ccre)
# Batch 3: SV callers (manta, delly, cnvnator, melt_mei, expansion_hunter, annotsv)
# Batch 4: PRS (prs, prs_*, glimpse2, prs_calibration, prs_qc_triad)
# Batch 5: Pharmacogenomics (pharmcat, cpsr, clinpgx, hla_*, kir_t1k, pgx_*)
# Batch 6: Prioritization (exomiser, lirical, acmg_classify, vus_*, variant_triage)
# Batch 7: DL/protein models (alphagenome, evo2, esm_cambrian, flashzoi, popeve, ncboost2, absplice2)
# Batch 8: Mito, ancestry, telomere, mosaic (mito_*, ancestry, haplogroups, mosaicforecast)
# Batch 9: Reports & downstream (generate_clinical_report, generate_review_packets, med_card, carrier_screening, chip_screening)
# Batch 10: Local analysis scripts (non-modal: calibrate_*, confidence_corrections, filter_triage, lakehouse, qc_audit, reactome_*)
```

## Pipeline Template (`pipelines/algorithm-provenance-audit.json`)

Submit via orchestrator with `--vars batch_num=1,script_list="modal_deepvariant.py modal_alignment_qc.py ..."`
