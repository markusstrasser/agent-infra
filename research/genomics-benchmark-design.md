## Benchmark and Validation Strategies for Personal Genomics WGS Pipelines — Research Memo

**Question:** What are the most effective benchmark and validation strategies for personal genomics WGS pipelines?
**Tier:** Standard | **Date:** 2026-03-23
**Ground truth:** Existing genomics pipeline in `~/Projects/genomics/`. No prior benchmarking research in this repo.
**Axes:** (1) What errors actually matter — practitioner/incident evidence. (2) What validation catches them — academic/tooling approaches.

---

### Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | GIAB provides 7 characterized reference genomes (HG001-HG007) with high-confidence variant calls for benchmarking | GIAB consortium documentation, multiple publications | HIGH | [SOURCE: genomeinabottle.org] | VERIFIED |
| 2 | hap.py with vcfeval engine is the GA4GH-recommended benchmarking tool | GA4GH best practices paper (Krusche et al., Nat Biotech 2019) | HIGH | [SOURCE: doi.org/10.1038/s41587-019-0054-x] | VERIFIED |
| 3 | SNV concordance is 99.7% inside vs 76.5% outside high-confidence regions | GA4GH best practices paper | HIGH | [SOURCE: doi.org/10.1038/s41587-019-0054-x] | VERIFIED |
| 4 | FP/FN rates are >10x higher in tandem repeats with >10 variants vs single-variant TRs | GIAB stratifications paper (Dwarshuis et al., Nat Commun 2024) | HIGH | [SOURCE: doi.org/10.1038/s41467-024-53260-y] | VERIFIED |
| 5 | DRAGEN shows 84% error reduction on SNVs and 76% on indels vs GATK+BWA | DRAGEN paper (Nat Genet 2024) using GIAB HG001-HG007 | HIGH | [SOURCE: doi.org/10.1038/s41588-024-01944-2] | VERIFIED |
| 6 | Conventional BWA+GATK Mutect2 produces 4-fold more FP errors than DRAGEN | Evaluation of FP/FN in targeted NGS (Genome Biology 2025) | HIGH | [SOURCE: doi.org/10.1186/s13059-025-03882-2] | VERIFIED |
| 7 | Clinical variant calling discordance between labs reaches 43% in some studies | gnomAD discordance study (Genome Research 2023) | HIGH | [SOURCE: genome.cshlp.org/content/33/6/999] | VERIFIED |
| 8 | NGS false-positive rate in PRSS1 gene due to pseudogene homology causes clinical misdiagnosis | Case report (Frontiers in Pediatrics 2025) | HIGH | [SOURCE: doi.org/10.3389/fped.2025.1572366] | VERIFIED |
| 9 | PharmCAT validates against GeT-RM reference materials and is "highly concordant" | PharmCAT paper (Sangkuhl et al., Clin Pharmacol Ther 2020) | HIGH | [SOURCE: PMID 31306493] | VERIFIED |
| 10 | In a Chinese survey, 14.3% of labs (7/49) missed expected pathogenic variants | Survey of 53 labs (Frontiers in Genetics 2020) | HIGH | [SOURCE: doi.org/10.3389/fgene.2020.582637] | VERIFIED |
| 11 | nf-test provides snapshot-based regression testing for Nextflow pipelines | nf-test paper (GigaScience 2025) | HIGH | [SOURCE: doi.org/10.1093/gigascience/giaf130] | VERIFIED |
| 12 | Color Genomics uses an ensemble of 5+ variant callers (GATK, DeepVariant, Scalpel, Samtools, MNV) for clinical redundancy | Color ASHG 2018 poster | MEDIUM | [SOURCE: static.getcolor.com/pdfs/research/Color_ASHG_Poster_2018_5.pdf] | VERIFIED |

---

### 1. GIAB: The Foundation for Pipeline Validation

**What GIAB provides:**
- **7 reference genomes:** HG001 (NA12878, pilot), HG002-HG007 from the Personal Genome Project. HG002 (Ashkenazi trio son) is the most extensively characterized and the recommended primary benchmark sample.
- **High-confidence variant calls + regions:** VCF files + BED files defining where calls can be trusted. Current versions: v4.2.1 for all 7 samples on GRCh37/GRCh38, v5.0 for HG002 (assembly-based).
- **Reference materials:** Physical DNA (NIST RM 8391, 8392, 8393, 8398) available from Coriell. You can actually sequence these yourself.
- **Stratification BED files:** Divide genome into meaningful contexts (low complexity, high GC, segmental duplications, functional regions, etc.). Available for GRCh37, GRCh38, and CHM13.

**The recommended validation workflow:**

```
1. Obtain GIAB truth VCF + high-confidence BED for your reference build
   ftp://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/giab/release/

2. Run your pipeline on GIAB reference sample (HG002 recommended)

3. Benchmark with hap.py using vcfeval engine:
   hap.py truth.vcf query.vcf \
     --engine vcfeval \
     --stratification stratifications.tsv \
     -f confident_regions.bed \
     -o output_prefix

4. Parse the *_extended.csv output for stratified metrics:
   Precision = QUERY.TP / (QUERY.TP + QUERY.FP)
   Recall    = TRUTH.TP / (TRUTH.TP + TRUTH.FN)
   F1        = 2 * Precision * Recall / (Precision + Recall)

5. Examine stratified results to identify weak spots
   (e.g., indels in tandem repeats, high-GC regions)
```

**Critical pitfalls of GIAB benchmarking:**

1. **High-confidence regions are NOT the whole genome.** GIAB v4.2.1 covers ~92% of GRCh38 for HG002. The remaining ~8% includes the hardest regions (segmental duplications, centromeres, telomeres). A pipeline can score 99.9% F1 within high-confidence regions while being terrible in excluded regions. The v5.0 benchmark for HG002 expands to include more difficult regions via assembly-based methods.

2. **Performance inside vs outside high-confidence regions diverges massively:** 99.7% SNV concordance inside vs 76.5% outside. [SOURCE: Krusche et al., Nat Biotech 2019] This means aggregate benchmarking numbers can mask huge error rates in clinically important difficult regions.

3. **Tandem repeat performance degrades sharply:** FP and FN rates are >10x higher in tandem repeats containing >10 variants compared to single-variant tandem repeats. 51-200bp AT dinucleotide tandem repeats show recall as low as 12-28% for indels. [SOURCE: Dwarshuis et al., Nat Commun 2024]

4. **Exome vs WGS mismatch:** GIAB truth sets are WGS-based. Using them for exome benchmarking produces misleadingly low recall unless you intersect with your exome capture regions BED file. [SOURCE: Biostars discussion, multiple reports]

5. **Single-sample limitation:** Benchmarking on one sample doesn't capture population-specific error modes. Using multiple GIAB samples (ideally including the Ashkenazi and Chinese trios) provides better coverage.

---

### 2. GA4GH Benchmarking Best Practices

The GA4GH Benchmarking Team (Krusche et al., Nat Biotech 2019, doi:10.1038/s41587-019-0054-x) established the canonical framework. Key recommendations:

**Comparison methods (by stringency):**
1. **Location-only match:** Any variant near the truth variant counts as TP. Appropriate when labs do Sanger confirmation.
2. **Allele match (xcmp):** Correct allele at approximately correct position. Handles different variant representations.
3. **Local haplotype match (vcfeval):** Reconstructs local haplotypes and checks if the variant calls produce the same sequence. **Recommended default.** Handles complex variant representation differences.
4. **Genotype match:** Correct allele AND correct zygosity (het vs hom). Most stringent.

**Performance metrics:**
- Report Precision (PPV), Recall (Sensitivity), and F-measure separately for SNVs and indels.
- Do NOT report a single aggregate number. Always stratify by variant type AND genomic context.
- True negatives / specificity are not meaningful for genome-wide variant calling (infinite number of potential variants).

**Stratification is non-negotiable:**
- By variant type: SNVs, insertions <50bp, deletions <50bp, complex variants
- By sequence context: low complexity, homopolymers (by length), tandem repeats (by unit size), segmental duplications, high/low GC
- By functional significance: coding, UTR, splice sites, regulatory
- By data characteristics: coverage bins (<5x, 5-10x, 10-20x, >20x), mapping quality, strand bias

**What stratification reveals that aggregate metrics hide:**
A pipeline with 99.5% overall SNV F1 might have:
- 99.9% F1 in easy regions
- 85% F1 in homopolymers >10bp
- 70% F1 in segmental duplications
- 30% F1 in AT-rich tandem repeats >50bp

The clinically relevant variants that fall in those hard regions are exactly the ones the pipeline fails on silently.

---

### 3. What Errors Actually Cause Clinical Harm

This section draws from documented case reports and surveys, not theoretical risk analysis.

#### Category A: False Positives Leading to Wrong Diagnosis/Treatment

**Case 1 — PRSS1 pseudogene mismapping (2025):** NGS (WES) called two heterozygous pathogenic variants in PRSS1 (p.A16V and p.N29I) in a pediatric pancreatitis patient. Sanger sequencing confirmed both were false positives. The FPs arose from sequence homology between PRSS1, PRSS2, and pseudogene PRSS3P3 — short reads cannot distinguish them. Patient was actually diagnosed with drug-induced (valproic acid) pancreatitis. Without Sanger confirmation, would have been diagnosed with hereditary pancreatitis and received inappropriate genetic counseling. [SOURCE: Frontiers in Pediatrics 2025, doi:10.3389/fped.2025.1572366]

**Case 2 — KMT2C false positive changing medulloblastoma diagnosis (2024):** HaplotypeCaller called a variant (rs10454320) in KMT2C as pathogenic, classified as "variant of uncertain significance." Sanger showed it was a false positive (a software artifact, not a technical sequencing error). Meanwhile, DeepVariant found a different real variant that HaplotypeCaller missed. The choice of variant caller literally determined the diagnosis. Concordance between the two pipelines was only 88.73%. [SOURCE: Frontiers in Oncology 2024, doi:10.3389/fonc.2024.1422811]

**Case 3 — CF complex allele missed (2025):** A girl diagnosed as F508del homozygous via targeted screening was put on Orkambi (lumacaftor/ivacaftor). Poor response. NGS panel re-sequencing revealed an additional variant in cis ([L467F;F508del] complex allele), which changes modulator response. Standard screening (testing for common variants only) missed the complex allele entirely, leading to years of suboptimal therapy. [SOURCE: Frontiers in Genetics 2025, doi:10.3389/fgene.2025.1693573]

#### Category B: Variant Interpretation Errors (Not Pipeline Per Se)

**Survey of 53 Chinese labs (2020):** Given identical raw sequencing data, 14.3% of labs missed the expected pathogenic variant entirely. Causes included: wrong variant calling, wrong annotation, incorrect filtering thresholds, wrong inheritance pattern assumptions. Even among labs that found the variants, classification discordance was substantial. After targeted training, accuracy improved significantly — the problem was largely interpretive, not algorithmic. [SOURCE: Frontiers in Genetics 2020, doi:10.3389/fgene.2020.582637]

**Case series of 33 US genetic testing errors (2021):** In 9 cases, test results were misinterpreted leading to incorrect surgeries or screening. In 5 cases, wrong tests were ordered. In 3 cases, incorrect clinical diagnoses were made. One case involved a falsified test result by a patient. The errors spanned medical-grade testing, DTC testing, and research testing. [SOURCE: The Cancer Journal 2021, doi:10.1097/PPO.0000000000000553]

**Li-Fraumeni misdiagnosis cascade (2020):** A patient went through multiple labs over years. One lab missed TP53 mutation in a custom NGS panel (likely insufficient coverage/filtering). Another lab incorrectly flagged an MSH6 VUS as Lynch syndrome. The correct Li-Fraumeni diagnosis was eventually made "by chance" at a tumor board. The cascade of errors included: FN in germline testing, incorrect VUS interpretation, failure to connect tumor TP53 finding with germline testing indication. [SOURCE: HCCP Journal 2020, doi:10.1186/s13053-020-00157-8]

#### Category C: Systematic Technical Artifacts

**gnomAD discordance (2023):** Variants that pass gold-standard quality filters in gnomAD still show systematic genotype discordance across different calling approaches (exome vs genome). The most common error mode: heterozygous in one approach, homozygous in the other. These discordant sites can produce false-positive GWAS hits from technological artifacts rather than real associations. The study provides a list of discordant sites that should be blacklisted. [SOURCE: Genome Research 2023, genome.cshlp.org/content/33/6/999]

**NGS provider variability (2025):** A comprehensive evaluation of targeted NGS across certified providers found: sensitivity differs up to 13.9-fold; FP error rates vary up to 615-fold. Conventional BWA+GATK Mutect2 produces 4-fold more FP errors than DRAGEN. HLA regions are particularly problematic — some providers showed complete alignment/variant-calling failures in HLA. Many FP-prone sites recur across samples but are never reported to end-users. [SOURCE: Genome Biology 2025, doi:10.1186/s13059-025-03882-2]

#### Synthesis: Error Taxonomy by Clinical Impact

| Error Type | Detection Method | Clinical Impact | Frequency |
|---|---|---|---|
| **FP in homologous/pseudogene regions** | Sanger confirmation, long reads | Wrong diagnosis, wrong genetic counseling | Common in specific loci (PRSS1, HLA, CYP2D6, SMN1) |
| **FN from pipeline choice** | Ensemble calling, multiple callers | Missed diagnosis, delayed treatment | ~11% discordance between GATK/DeepVariant |
| **Complex allele/phase miss** | Trio analysis, long reads, comprehensive sequencing | Wrong drug selection (e.g., CF modulators) | Under-recognized, emerging evidence |
| **VUS misinterpretation** | Expert review, re-classification, ClinVar updates | Unnecessary surgery (prophylactic mastectomy documented) | Substantial (17% ClinVar discordance) |
| **Reference build mismatch** | Liftover validation | Silent coordinate shift, wrong annotation | Preventable but common in ad-hoc pipelines |
| **Coverage dropout in key genes** | Per-gene QC metrics, gap analysis | Missed variants in actionable genes | Fixable with coverage monitoring |

---

### 4. Regression Testing Patterns from Mature Pipelines

#### DeepVariant
- Uses GIAB HG001-HG007 as regression benchmarks on every release.
- PrecisionFDA Truth Challenge V2 results used as public leaderboard comparison.
- Trains ML models on specific sequencing platforms (Illumina, PacBio HiFi, ONT), so regression testing must cover each model type.
- Tests stratified by variant type and genomic context. Performance tracked across releases.
- [TRAINING-DATA] Specific CI details not fully retrieved; based on Google's general ML pipeline practices with automated benchmarking.

#### GATK / DRAGEN-GATK
- Broad Institute maintains "functional equivalence" testing between DRAGEN hardware-accelerated and open-source GATK implementations.
- Best Practices workflows published as WDL, run on Terra/Cromwell with automated testing.
- GIAB samples used for performance comparison between GATK versions.
- DRAGEN paper benchmarks against HG001-HG007 with all callers (GATK, DeepVariant+BWA, DeepVariant+Giraffe, DRAGEN).

#### nf-core/sarek (Community Pipeline)
- Built on Nextflow with full CI/CD via GitHub Actions.
- Uses nf-test framework for snapshot-based regression testing.
- Test data: downsampled reference datasets in nf-core/test-datasets repository.
- On release: automated runs on AWS with full-sized datasets, results stored for cross-release comparison.
- MultiQC integration provides immediate QC dashboards.
- Each institution must perform its own clinical validation — sarek is not validated for clinical use out of the box.

#### nf-test Framework (General Pattern)
The nf-test framework (GigaScience 2025) provides the most concrete pattern for bioinformatics regression testing:

1. **Unit tests:** Individual tool/module validation with minimal inputs.
2. **Integration tests:** Subworkflow chains (e.g., alignment + variant calling).
3. **End-to-end tests:** Full pipeline runs with known-answer test data.
4. **Snapshot testing:** Captures output state (filenames, hashes) as reference snapshots. On subsequent runs, compares current output to snapshots. Prevents silent regression.
5. **Dependency-aware re-testing:** Only re-runs tests affected by code changes (via dependency graph analysis). Reduces CI time for large pipelines.
6. **CI mode:** `--ci` flag prevents automatic snapshot updates, enforcing that any output change is explicitly reviewed.

#### Color Genomics Clinical Pattern
Clinical ensemble approach: run 5+ variant callers (GATK, DeepVariant, Scalpel, Samtools, custom MNV caller), take the union, validate discordant calls. This "cast a wide net, verify differences" approach maximizes sensitivity at the cost of more Sanger confirmation work. Key insight: different callers excel in different contexts (DeepVariant better in high-GC regions, GATK+Scalpel better for larger indels).

---

### 5. PharmCAT Validation Approach

**Architecture:**
PharmCAT operates in two phases:
1. **Named Allele Matcher:** Takes a VCF file, extracts variants at CPIC-defined allele positions, infers star allele haplotypes.
2. **Reporter:** Maps diplotypes to phenotypes and retrieves CPIC/DPWG/FDA prescribing recommendations.

**Validation strategy:**
- **Primary validation:** Compared PharmCAT star allele calls against CDC GeT-RM (Genetic Testing Reference Materials) characterization for 137 samples across 28 pharmacogenes. Result: "highly concordant." [SOURCE: Sangkuhl et al., Clin Pharmacol Ther 2020, PMID 31306493]
- **1000 Genomes validation:** Ran PharmCAT on 1000 Genomes Project VCFs, cross-checked against independently characterized allele frequencies.
- **CYP2D6 special handling:** CYP2D6 is too complex for VCF-based calling alone (structural variants, duplications, deletions). PharmCAT accepts external CYP2D6 calls (from tools like Stargazer, Cyrius, or StellarPGx that use BAM-level analysis).

**Known limitations and pitfalls:**
- `--missing-to-ref` flag: Assumes genotypes at missing PGx sites are reference (0/0). PharmCAT documentation explicitly calls this "DANGEROUS." If your VCF doesn't include all allele-defining positions (common with array data), missing positions are ambiguous — they could be uncalled variants, not true reference.
- **Imputation accuracy:** When using array-based genotyping + imputation for PGx, imputation quality varies by population and by variant. The Korean study (14,490 samples, medRxiv 2026) validated imputed PGx calls against WGS and found discordances particularly for rare variants and structural variants.
- **G6PD and sex chromosomes:** Often excluded from automated pipelines because imputation panels lack sex chromosome data.
- **Complex star alleles:** Some star alleles require phasing information that short-read VCFs cannot provide. PharmCAT flags these but may default to a less specific call.

**Validation approach for a personal pipeline:**
1. Run PharmCAT on GIAB samples that have GeT-RM characterization (HG001/NA12878 is a GeT-RM sample).
2. Compare your pipeline's star allele calls against published GeT-RM consensus.
3. For CYP2D6: use a dedicated structural variant caller (Cyrius for WGS), pass results to PharmCAT.
4. Spot-check actionable diplotypes against PharmGKB annotations.
5. Track PharmCAT version updates — allele definitions change with CPIC guideline updates.

---

### 6. Recommended Validation Architecture for a Personal WGS Pipeline

Based on the evidence above, here is a layered validation strategy ordered by cost and value:

#### Layer 0: Smoke Test (minutes, every pipeline run)
- Output VCF is valid (bcftools stats parses without error)
- Expected number of variants is within normal range (~4-5M for WGS)
- Ti/Tv ratio for SNVs is ~2.0-2.1 for WGS (deviation signals systematic error)
- Het/Hom ratio is within expected range for the sample's ancestry
- Minimal coverage thresholds met across target regions

#### Layer 1: GIAB Benchmarking (hours, on pipeline changes)
- Run pipeline on HG002 (minimum), ideally HG001 + HG002
- Benchmark with `hap.py --engine vcfeval` against latest GIAB truth set
- Stratify with GIAB stratification BED files
- Track metrics across pipeline versions: overall F1, and F1 in problem regions (homopolymers, tandem repeats, segmental duplications, high-GC)
- **Set performance floors:** e.g., SNV recall >99.5%, indel recall >98%, SNV precision >99.9%

#### Layer 2: Regression Snapshots (minutes, every code change)
- Snapshot testing (nf-test pattern): capture output hashes/metrics from a small reference dataset
- Any change in output triggers review
- Keep a "golden VCF" from a downsampled reference run; diff against it

#### Layer 3: Known-Variant Spot Checks (minutes, periodic)
- Maintain a curated list of variants that your pipeline MUST call correctly (clinically actionable variants from your own genome or GIAB samples)
- Include edge cases: variants in homopolymers, near indels, in pseudogene-adjacent regions, in HLA
- Automated check: are these variants present with expected genotype in the output?

#### Layer 4: PGx Validation (hours, on pipeline or PharmCAT version changes)
- Run PharmCAT on GIAB/GeT-RM samples
- Compare star allele calls against GeT-RM consensus
- CYP2D6 structural variant validation via dedicated caller

#### Layer 5: Cross-Caller Concordance (hours, periodic)
- Run same sample through 2+ callers (e.g., DeepVariant + GATK HaplotypeCaller)
- Examine discordant calls: these are the highest-risk positions
- Sanger-equivalent validation (IGV manual review) for discordant calls in actionable genes

#### Anti-Patterns to Avoid
1. **Reporting only aggregate F1.** Always stratify. A 99.5% F1 can hide catastrophic failure in specific regions.
2. **Benchmarking only within high-confidence regions.** Understand what percentage of your clinically relevant genes falls outside GIAB high-confidence regions.
3. **Using `--missing-to-ref` in PharmCAT without understanding implications.** This silently assumes uncalled positions are reference.
4. **Skipping per-gene coverage QC.** A single gene with a coverage dropout can be the one that matters.
5. **Treating GIAB benchmarking as one-time validation.** Pipeline dependencies (reference genome, tool versions, model files) change. Re-benchmark on updates.
6. **Ignoring population-specific error modes.** GIAB samples are from specific populations. Error rates may differ for underrepresented ancestries.

---

### What's Uncertain

1. **GIAB v5.0 scope:** The assembly-based v5.0 benchmark for HG002 covers more difficult regions, but details on its coverage of specific clinically relevant loci (e.g., specific pharmacogenes, HLA) were not fully characterized in this review.

2. **Long-read benchmarking standards:** As ONT and PacBio HiFi become more common for personal WGS, benchmarking standards for long-read-specific error modes (systematic basecalling errors, methylation artifacts) are still evolving.

3. **SV benchmarking maturity:** Structural variant benchmarking with GIAB is less mature than small variant benchmarking. GIAB has SV truth sets but tools like Truvari for SV comparison are newer and less standardized.

4. **Ancestry-specific performance gaps:** Most benchmarking is done on the Ashkenazi Jewish (HG002-004) and Chinese (HG005-007) GIAB samples. Performance on African, South Asian, and other populations may differ, particularly for complex/polymorphic regions with different allele frequencies.

5. **PharmCAT accuracy for rare star alleles:** Validation was against GeT-RM consensus, which covers common alleles well. Rare or novel star alleles are less well characterized.

---

### Key Sources

- Krusche P et al. "Best practices for benchmarking germline small-variant calls in human genomes." *Nat Biotechnol* 37:555-560 (2019). doi:10.1038/s41587-019-0054-x
- Dwarshuis N et al. "The GIAB genomic stratifications resource for human reference genomes." *Nat Commun* 15:8525 (2024). doi:10.1038/s41467-024-53260-y
- Sangkuhl K et al. "Pharmacogenomics Clinical Annotation Tool (PharmCAT)." *Clin Pharmacol Ther* 107:203-210 (2020). PMID:31306493
- Olson ND et al. "PrecisionFDA Truth Challenge V2." *Cell Genomics* 2:100129 (2022).
- Skitchenko R et al. "Variant calling pipeline selection effect on molecular diagnostics outcome." *Front Oncol* 14:1422811 (2024).
- Liu Y et al. "NGS misguided clinical interpretation of PRSS1 variant." *Front Pediatr* 13:1572366 (2025).
- Karnstedt M et al. "Pitfalls in CF screening — targeted variant analysis." *Front Genet* 16:1693573 (2025).
- Atkinson EG et al. "Discordant calls across genotype discovery approaches." *Genome Research* 33:999 (2023).
- Lee S et al. "Evaluation of false positive and false negative errors in targeted NGS." *Genome Biology* (2025). doi:10.1186/s13059-025-03882-2
- nf-test paper. "Improving reliability, quality and maintainability of bioinformatics pipelines with nf-test." *GigaScience* (2025). doi:10.1093/gigascience/giaf130
- GIAB FTP: ftp://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/giab/release/
- GA4GH benchmarking tools: https://github.com/ga4gh/benchmarking-tools
- GIAB stratifications pipeline: https://github.com/usnistgov/giab-stratifications

<!-- knowledge-index
generated: 2026-03-23T17:35:33Z
hash: 1bff32a5ea27

table_claims: 12

end-knowledge-index -->
