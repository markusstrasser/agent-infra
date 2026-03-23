## WGS Validation Gaps Beyond Standard Benchmarking — Research Memo

**Question:** What validation and QC methods exist for personal/clinical WGS pipelines BEYOND standard GIAB benchmarking, smoke tests, and cross-tool concordance?
**Tier:** Standard | **Date:** 2026-03-23
**Ground truth:** Existing pipeline implements GIAB benchmarking (hap.py, stratified), smoke metrics (Ti/Tv, het/hom, variant counts, chrY het), Aldy vs PharmCAT PGx concordance, PRS sanity checks, noncoding benchmark (ClinVar truth set), classification calibration, cross-stage contract enforcement, regression snapshots, known-variant spot checks, end-to-end gold output test.
**Axes:** (1) CAP/CLIA practitioner — what clinical labs do that personal pipelines skip. (2) Tools/methods 2024-2026 — recent frameworks, novel approaches, underserved variant classes.

---

### Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | VerifyBamID2 provides ancestry-agnostic contamination estimation from sequence reads | Tool paper + GitHub | HIGH | [SOURCE: doi.org/10.1101/gr.246934.118, github.com/Griffan/VerifyBamID] | VERIFIED |
| 2 | Haplocheck uses mtDNA phylogeny for contamination detection, concordant with VerifyBamID2 nDNA estimates | Tool paper + GitHub | HIGH | [SOURCE: github.com/genepi/haplocheck] | VERIFIED |
| 3 | NGSTroubleFinder (2025) detects contamination AND kinship across WGS/WTS data | bioRxiv preprint | MEDIUM | [SOURCE: doi.org/10.1101/2025.01.31.635690] | PREPRINT |
| 4 | Somalier performs fast sample-swap and relatedness checks on BAMs/CRAMs/VCFs | Tool paper + GitHub | HIGH | [SOURCE: github.com/brentp/somalier] | VERIFIED |
| 5 | Genomics England uses freemix < 0.03, array concordance > 90%, chimeric reads < 5%, mapped reads > 60% as QC gates | GEL documentation | HIGH | [SOURCE: re-docs.genomicsengland.co.uk/sample_qc] | VERIFIED |
| 6 | GIAB CMRG (Challenging Medically Relevant Genes) provides SV truth set for 273 genes | Wagner et al., Nat Biotech 2022 | HIGH | [SOURCE: nature.com/articles/s41587-022-01190-7] | VERIFIED |
| 7 | Truvari v5.2 is the standard SV benchmarking tool; hap-eval from Sentieon provides haplotype-based SV comparison | Multiple benchmarking papers | HIGH | [SOURCE: biorxiv.org/content/10.1101/2022.02.21.481353v1] | VERIFIED |
| 8 | mity is a highly sensitive mtDNA variant analysis pipeline for WGS data | Publication + GitHub | HIGH | [SOURCE: fortunejournals.com, github.com/KCCG/mity] | VERIFIED |
| 9 | MitoH3 provides mtDNA haplogroup + homoplasmic/heteroplasmic variant calling | PMC publication | HIGH | [SOURCE: pmc.ncbi.nlm.nih.gov/articles/PMC11091720/] | VERIFIED |
| 10 | CYP2D6 structural variant interrogation significantly improves genotype-phenotype correlation | Gaedigk et al. 2019 | HIGH | [SOURCE: pubmed.ncbi.nlm.nih.gov/31536170/] | VERIFIED |
| 11 | CNVscope (Sentieon) uses ML-trained read-depth profiling for germline CNV calling >1kb | Sentieon documentation | HIGH | [SOURCE: omnitier.com docs, PMC12813096] | VERIFIED |
| 12 | Draft Q100 SV benchmark for HG002 contains ~30K SVs vs ~9.6K in GIAB v0.6 | Sentieon/GIAB documentation | HIGH | [SOURCE: PMC12813096] | VERIFIED |
| 13 | Ancestry-linked regulatory haplotypes influence CYP2D6 expression (2026 finding) | Nature PGx Journal 2026 | MEDIUM | [SOURCE: nature.com/articles/s41397-026-00398-1] | VERIFIED |
| 14 | Complete PGx profiling from exome sequencing is now feasible (2026 preprint) | medRxiv 2026 | MEDIUM | [SOURCE: medrxiv.org/content/10.64898/2026.01.13.26343772v2] | PREPRINT |
| 15 | CAP requires pre-analytical, analytical, and post-analytical validation phases; ISO 15189 for medical lab competence | Euformatics clinical NGS review | HIGH | [SOURCE: euformatics.com/blog-post/evolving-standards-in-clinical-ngs] | VERIFIED |

---

### 1. Contamination and Sample-Swap Detection (MAJOR GAP)

**What clinical labs do:** Every CAP/CLIA lab runs contamination estimation and sample identity verification on every sample. This is considered basic QC, not optional.

**Tools you should implement:**

- **VerifyBamID2** — Ancestry-agnostic contamination estimation from aligned reads. Uses SVD-based population structure model, no need to know the sample's ancestry a priori. Standard threshold: FREEMIX < 0.02-0.03 (Genomics England uses < 0.03). Available as nf-core module (`verifybamid_verifybamid2`). [SOURCE: github.com/Griffan/VerifyBamID, doi.org/10.1101/gr.246934.118]

- **Haplocheck** — Phylogeny-based contamination detection using mtDNA. Exploits the fact that contamination from a different individual will introduce a second mtDNA haplogroup. High concordance with VerifyBamID2 for nDNA contamination levels. Particularly useful as a fast cross-check. [SOURCE: github.com/genepi/haplocheck]

- **Somalier** — Fast sample-swap and relatedness checks. Extracts a small set of informative sites from BAM/CRAM/VCF and computes pairwise relatedness. Catches sample swaps across a cohort or between runs. Essential when processing multiple samples. [SOURCE: github.com/brentp/somalier]

- **NGSTroubleFinder (2025)** — Newer tool that detects both contamination AND kinship across NGS data. Claims improvements over VerifyBamID2 on their test dataset. Worth monitoring but too new for production reliance. [SOURCE: doi.org/10.1101/2025.01.31.635690, PREPRINT]

**Recommendation:** Add VerifyBamID2 (FREEMIX gate) + somalier (identity check) as mandatory QC steps. Haplocheck as cross-validation. This is arguably the single largest gap — contamination and sample swaps are among the most common pre-analytical errors in clinical labs, and without these checks, downstream variant calls can be silently corrupted.

---

### 2. CAP/CLIA Clinical Validation Requirements Beyond GIAB

**What clinical labs must do that personal pipelines typically skip:**

1. **Pre-analytical QC**: DNA/RNA integrity verification (DIN/RIN scores), fragment size distribution assessment (not just median — full distribution), input mass quantification. ISO 20387:2018 covers biobanking/sample handling. [SOURCE: euformatics.com clinical NGS review]

2. **External proficiency testing (PT)**: CAP requires participation in external PT programs where blinded samples are sent to the lab and results compared across participating labs. The College of American Pathologists runs NGS-specific PT surveys (CAP NGS survey). Personal pipelines have no equivalent — but could simulate this by periodically running blinded GIAB samples through the full pipeline without checking against truth sets until after calls are made. [INFERENCE]

3. **Limit of detection (LoD) characterization**: Clinical labs must establish minimum allele frequency, minimum coverage, and minimum variant size their pipeline can reliably detect. This goes beyond aggregate benchmarking — it requires serial dilution or titration experiments. For a personal pipeline, this could be approximated by downsampling GIAB data to different coverages and measuring sensitivity decay curves. [TRAINING-DATA, verified against CAP requirements]

4. **Reproducibility/repeatability studies**: Same sample run N times (intra-run), across different runs (inter-run), and ideally across different operators. Clinical labs must demonstrate reproducibility with defined thresholds. For a personal pipeline: run the same sample 3+ times and measure variant call concordance. [SOURCE: euformatics.com]

5. **Reportable range documentation**: Explicit documentation of what the pipeline CAN and CANNOT call — which variant types, which genomic regions, which size ranges. Clinical labs must state this. Personal pipelines typically lack this negative documentation. [TRAINING-DATA]

6. **Library QC metrics**: Insert size distribution, GC bias, duplication rate, base quality distribution (Q30 threshold). Genomics England tracks: median fragment size > 250bp, AT dropout < 10%, chimeric reads < 5%. [SOURCE: re-docs.genomicsengland.co.uk/sample_qc]

7. **Sex verification**: Genomics England uses het/hom SNV ratio (< 3 threshold) as sex check. Clinical labs also check X chromosome coverage vs autosomal coverage ratio, and Y chromosome read presence. Your chrY het check partially covers this, but adding explicit sex concordance (declared vs observed) would be more robust. [SOURCE: re-docs.genomicsengland.co.uk/sample_qc]

---

### 3. Structural Variant / Copy Number Validation (SIGNIFICANT GAP)

**Current state of SV/CNV benchmarking:**

- **GIAB SV benchmark v0.6**: ~9,646 SVs for HG002. Limited to relatively simple SVs in high-confidence regions.
- **Draft Q100 SV benchmark**: ~30,244 SVs — 3x larger, derived from T2T Q100 assembly. Much more comprehensive. [SOURCE: PMC12813096]
- **CMRG SV benchmark**: 216 SVs across 273 medically relevant genes for HG002. Critical for clinical validation. [SOURCE: Wagner et al., Nat Biotech 2022]

**Tools for SV benchmarking:**

- **Truvari v5.2**: Standard SV benchmarking tool. Supports `bench` (benchmarking against truth set), `collapse` (merging), `refine` (local reassembly). Uses multiple similarity metrics (SVTYPE, reciprocal overlap, size similarity, sequence similarity). [SOURCE: github.com/ACEnglish/truvari]

- **hap-eval (Sentieon)**: Haplotype-based SV comparison — assembles multiple nearby variants into haplotypes for comparison rather than pairwise matching. Addresses a known limitation of Truvari's older versions. [SOURCE: PMC12813096]

**CNV-specific tools:**

- **CNVscope (Sentieon)**: ML-trained germline CNV caller for short-read WGS. Uses read-depth profiling + normalization + feature extraction + segmentation. Trained on HPRC/T2T assembly data. Calls events >1kb. [SOURCE: PMC12813096]

- For benchmarking CNV callers, a key challenge remains: **no genome-scale, high-quality CNV truth set exists yet.** The draft Q100 benchmark is the closest available, but it's not specifically optimized for CNVs. The Tempus benchmarking study evaluated germline CNV callers from WGS for clinical settings. [SOURCE: tempus.com/publications/benchmarking-of-germline-copy-number-variant-callers]

**What's missing from your pipeline:** If you do any SV/CNV calling (e.g., Manta, DELLY, TIDDIT), you should benchmark against CMRG SV truth set using Truvari. Current top performers on CMRG (ONT): dysgu (F1=0.937), cuteSV (F1=0.929), Sniffles (F1=0.909). For short-read: results are substantially worse. [SOURCE: github.com/kcleal/SV_Benchmark_CMRG]

---

### 4. Mitochondrial DNA Validation (GAP)

**Why it matters:** mtDNA variants are clinically significant (mitochondrial diseases, maternal haplogroup, heteroplasmy as disease risk marker). Standard WGS pipelines that align to GRCh38 typically include chrM, but mtDNA has unique properties that require specialized handling:

- Circular genome (alignment artifacts at the origin)
- Very high copy number (thousands per cell) — coverage is typically 1000-5000x vs 30-40x autosomal
- Heteroplasmy — mixture of mtDNA variants within a cell, with clinical significance at different variant allele fractions
- NUMTs (nuclear mitochondrial insertions) — autosomal copies of mtDNA that confound variant calling

**Tools:**

- **mity**: Highly sensitive mtDNA variant analysis pipeline for WGS. Designed to handle the high-coverage, heteroplasmy, and NUMT challenges. [SOURCE: github.com/KCCG/mity]

- **MitoH3**: Combined haplogroup assignment + homoplasmic/heteroplasmic variant calling pipeline. Designed for Alzheimer's research but broadly applicable. [SOURCE: PMC11091720]

- **Genomics England approach**: Uses separate mtDNA pipeline with NUMT filtering, heteroplasmy quantification, and haplogroup-based QC. [SOURCE: pipeline-rd-help.genomicsengland.co.uk]

- **Haplocheck** (dual-purpose): Not only contamination detection but also mtDNA haplogroup verification. [SOURCE: github.com/genepi/haplocheck]

**Heteroplasmy detection limits (2024):** Long-read nanopore can detect heteroplasmy down to ~1% VAF with sufficient coverage. Short-read WGS can reliably detect ~3-5% VAF heteroplasmy. Below these thresholds, distinguishing true heteroplasmy from sequencing error requires specialized statistical models. [SOURCE: doi.org/10.1038/s41598-024-78270-0]

**Validation approach:** Run mtDNA-specific caller on GIAB samples, compare haplogroup assignments against known haplogroups for GIAB samples (publicly available), and verify heteroplasmy calls against long-read data where available.

---

### 5. Ancestry-Aware QC and PRS Calibration

**The problem:** Most QC thresholds (Ti/Tv ratio, het/hom ratio, total variant counts) vary by ancestry. A sample from an underrepresented population may fail QC thresholds calibrated on European samples despite being perfectly valid.

**What exists:**

- **VerifyBamID2**: Already ancestry-agnostic by design (SVD-based model). [SOURCE: doi.org/10.1101/gr.246934.118]

- **Ancestry inference from WGS**: Tools like `peddy` (from somalier's author) infer ancestry from genotype data and can be used to set ancestry-appropriate QC thresholds. [TRAINING-DATA]

- **Population-stratified variant count ranges**: Genomics England uses 3.2M-4.7M total SNVs as acceptable range, but this is broad because their cohort is diverse. Ideally, you'd set ancestry-specific ranges. [SOURCE: re-docs.genomicsengland.co.uk/sample_qc]

- **PRS calibration**: Your pipeline already does matched vs unmatched z-scores and phenotype concordance. The additional step from recent literature: ancestry-specific PRS normalization using reference panel percentiles (e.g., gnomAD or 1000 Genomes subpopulation distributions). The key 2025-2026 development is the Human Pangenome Reference Consortium (HPRC) providing diverse reference assemblies that improve variant calling accuracy in non-European samples. [TRAINING-DATA, partially verified]

**Recommendation:** Add ancestry inference step (peddy or similar) early in QC, then use inferred ancestry to set population-appropriate thresholds for downstream metrics. This is especially important for het/hom ratio and total variant counts, which vary significantly by population.

---

### 6. Pharmacogenomics Validation Beyond Star Allele Concordance

**What you have:** Aldy vs PharmCAT concordance.

**What you're missing:**

- **CYP2D6 structural variant detection**: CYP2D6 is the most pharmacogenomically important gene with extensive structural variation (gene deletions, duplications, hybrid alleles CYP2D6/CYP2D7). Star allele concordance misses these. Interrogating CYP2D6 SVs significantly improves genotype-phenotype correlation. [SOURCE: pubmed.ncbi.nlm.nih.gov/31536170/]

- **Ancestry-linked regulatory haplotypes**: A 2026 paper shows functional ancestry-linked regulatory haplotypes influence CYP2D6 expression — meaning same star allele can have different metabolizer phenotype in different populations. [SOURCE: nature.com/articles/s41397-026-00398-1]

- **PharmVar structural variation tutorial**: CYP2D6 SV testing requires specialized approaches — read-depth analysis, breakpoint detection, and haplotype phasing. PharmVar provides a tutorial specifically for this. [SOURCE: PMC10840842]

- **Computational variant predictors for PGx**: A 2026 paper evaluates computational tools that predict functional impact of PGx variants, beyond simple star allele lookup — useful for novel or rare variants not in PharmGKB. [SOURCE: nature.com/articles/s41397-026-00399-0]

- **GeT-RM validation**: CDC's Genetic Testing Reference Materials program provides characterized reference materials for PGx genes. PharmCAT validation against GeT-RM is standard — you should verify your pipeline produces concordant calls on GeT-RM samples. [TRAINING-DATA, verified in prior research]

**Recommendation:** Add CYP2D6 copy number and SV detection (Cyrius, or Aldy's SV mode). Validate against GeT-RM reference materials. Track ancestry alongside PGx calls for genes where ancestry affects expression.

---

### 7. Novel Approaches: ML-Based QC and Foundation Model Scoring

**What exists in 2025-2026:**

- **CNVscope (Sentieon)**: ML-trained CNV caller using models trained on HPRC/T2T assemblies. [SOURCE: PMC12813096]

- **Neretva (2026 preprint)**: Unsupervised neural variational inference for variant scoring — uses a neural network to learn variant quality distributions without labeled truth sets. Potential for QC without GIAB dependency. [SOURCE: biorxiv.org/content/10.64898/2026.02.03.703582v1]

- **DeepVariant** (already established but evolving): Google's ML-based variant caller continues to improve. v1.8.0 is current. The model itself serves as a form of validation — if DeepVariant and GATK disagree on a call, that disagreement is informative. [TRAINING-DATA]

- **DRAGEN ML pipelines**: Illumina's DRAGEN uses ML for variant filtering (CNN-based). 84% SNV error reduction, 76% indel error reduction vs GATK+BWA. [SOURCE: doi.org/10.1038/s41588-024-01944-2, from prior research memo]

- **Foundation models for genomics (emerging)**: Evo, Nucleotide Transformer, and similar genomic foundation models can score variant pathogenicity but are NOT yet validated for QC pipeline integration. These are research-phase, not production-ready. [TRAINING-DATA]

**Recommendation:** Using DeepVariant as an independent caller alongside your primary caller and flagging discordant calls is the most practical ML-based QC available today. Foundation model scoring is worth monitoring but not implementing yet.

---

### 8. Comprehensive Genomics England QC Framework (Reference Implementation)

Genomics England's AggV2 sample QC represents the most publicly documented large-scale clinical WGS QC framework. Their gates:

| Metric | Threshold | Your Pipeline |
|--------|-----------|---------------|
| Contamination (freemix) | < 0.03 | **MISSING** |
| Array concordance (identity) | > 90% | **MISSING** (no array data) |
| Het/Hom SNV ratio | < 3 | Have (smoke) |
| Total SNVs | 3.2M - 4.7M | Have (smoke) |
| Coverage at 15X | > 95% genome | **MISSING as explicit gate** |
| Mean coverage | Tracked (median 39X) | Likely have but verify |
| Median fragment size | > 250bp | **MISSING** |
| Chimeric reads | < 5% | **MISSING** |
| Mapped reads | > 60% | **MISSING** |
| AT dropout | < 10% | **MISSING** |

[SOURCE: re-docs.genomicsengland.co.uk/sample_qc]

---

### Priority Recommendations (Ranked by Impact)

| Priority | Gap | Effort | Impact | Tool/Method |
|----------|-----|--------|--------|-------------|
| **P0** | Contamination detection | Low | Critical | VerifyBamID2 + haplocheck |
| **P0** | Sample identity verification | Low | Critical | Somalier (if multi-sample) |
| **P1** | Pre-analytical QC gates | Low | High | Fragment size, chimeric reads, mapped reads, AT dropout |
| **P1** | Sex concordance check | Low | High | X/autosomal coverage ratio + declared sex |
| **P1** | Ancestry inference for threshold calibration | Medium | High | peddy / ancestry PCA from VCF |
| **P2** | mtDNA-specific validation | Medium | Medium | mity or MitoH3 + haplogroup verification |
| **P2** | SV/CNV benchmarking | Medium | Medium | Truvari + CMRG truth set (if SV calling exists) |
| **P2** | CYP2D6 structural variant validation | Medium | High (for PGx) | Cyrius or Aldy SV mode + GeT-RM |
| **P3** | Coverage at 15X gate | Low | Medium | samtools depth or mosdepth |
| **P3** | LoD characterization via downsampling | Medium | Medium | Subsample GIAB BAM at 10X/15X/20X/30X |
| **P3** | Reproducibility testing | High | Medium | Run same sample 3x, measure concordance |
| **P3** | ML-based discordant call QC | Medium | Low-Medium | DeepVariant as independent caller |

---

### What's Uncertain

1. **Array concordance without array data**: Genomics England uses microarray genotyping for identity verification. Without array data, somalier-based relatedness or fingerprinting against prior runs is the closest substitute. Whether fingerprinting against dbSNP-derived sites is sufficient for a single-sample personal pipeline is unclear.

2. **Ancestry-specific QC thresholds**: Published thresholds from large biobanks (UK Biobank, All of Us, Genomics England) exist but are calibrated for population-scale QC, not individual sample QC. How to adapt these for N=1 personal genomics is not well-documented.

3. **mtDNA validation ground truth**: GIAB provides limited mtDNA benchmarking. The quality of mtDNA truth sets is lower than autosomal truth sets. Long-read sequencing of the same sample provides the best mtDNA validation, but this requires additional sequencing.

4. **Foundation model variant scoring**: The field is moving fast (Evo, Nucleotide Transformer, GPN-MSA) but no tool has been validated for clinical-grade QC gating as of March 2026. Worth monitoring quarterly.

---

### Search Log

| # | Tool | Query | Result |
|---|------|-------|--------|
| 1 | Read | Prior research memo (genomics-benchmark-design.md) | Grounded existing knowledge |
| 2 | Exa (advanced) | Clinical WGS QC + CAP/CLIA + contamination + ancestry | 11 results: GA4GH standards, GEL QC, Tempus CNV, Euformatics clinical NGS |
| 3 | Exa (advanced) | mtDNA validation + SV/CNV benchmarking + ML variant scoring | 10 results: mity, MitoH3, haplocheck, heteroplasmy detection |
| 4 | Exa (advanced) | PGx beyond star alleles + WGS QC tools 2025-2026 | 8 results: CYP2D6 SVs, PharmVar tutorial, ancestry-linked regulatory haplotypes |
| 5 | WebFetch | Genomics England sample QC docs | Full QC metric table with thresholds |
| 6 | WebFetch | Euformatics clinical NGS standards | CAP/CLIA/ISO requirements overview |
| 7 | Brave | Somalier + VerifyBamID2 + contamination tools | NGSTroubleFinder (2025), haplocheck, nf-core modules |
| 8 | Exa | GIAB SV benchmark + Truvari + T2T + CMRG | Q100 benchmark (30K SVs), Truvari v5.2, hap-eval, SV caller comparison |

<!-- knowledge-index
generated: 2026-03-23T19:00:36Z
hash: 346538d10f9a

sources: 3
  TRAINING-DATA: , verified against CAP requirements
  TRAINING-DATA: , partially verified
  TRAINING-DATA: , verified in prior research
table_claims: 15

end-knowledge-index -->
