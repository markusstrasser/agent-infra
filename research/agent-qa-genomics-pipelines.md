## Agent-Proof Quality Assurance for Autonomous Genomics Pipelines — Research Memo

**Question:** How should a personal genomics pipeline with autonomous agents adding code protect itself from regressions, silent errors, and quality degradation?
**Tier:** Standard | **Date:** 2026-03-23
**Ground truth:** Existing genomics pipeline (200+ stages), GIAB benchmarking, smoke tests, nf-test regression patterns already documented in `research/genomics-benchmark-design.md`. This memo addresses the META-LEVEL problem: protecting the pipeline from the agents that modify it.
**Axes:** (1) Practitioner/engineering — CI/CD for bioinformatics, MLOps regression detection. (2) Academic — pipeline validation frameworks, reproducibility, clinical lab quality systems. (3) Adjacent domain — multi-agent code quality, canary testing patterns from MLOps.

---

### Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | nf-core/variantbenchmarking provides a standardized Nextflow pipeline for comparing variant calls against truth sets (GIAB, SEQC2) for SNVs, indels, SVs, and CNVs | WorkflowHub listing, nf-core documentation | HIGH | [SOURCE: workflowhub.eu/workflows/1307] | VERIFIED |
| 2 | Clinical genomics labs use LIMS (Clarity LIMS, CloudLIMS, StarLIMS) to track sample-to-result provenance including instrument, software version, and database version | Multiple vendor documentation and ISO 17025 guides | HIGH | [SOURCE: illumina.com/clarity-lims, lims.science, wiselims.com] | VERIFIED |
| 3 | GA4GH WGS Quality Control Standards define standardized QC metrics for whole genome sequencing | GA4GH product page | HIGH | [SOURCE: ga4gh.org/product/wgs-quality-control-standards] | VERIFIED |
| 4 | MLOps canary deployment patterns (traffic splitting, shadow mode, automated rollback) are well-established for ML model updates | Multiple 2026 practitioner guides | MEDIUM | [SOURCE: oneuptime.com, medium.com/@ThinkingLoop] | VERIFIED |
| 5 | Eval-driven development operationalizes CI/CD regression detection for LLM/AI systems via automated test suites with statistical comparisons | Practitioner guide (Khera, Mar 2026) | MEDIUM | [SOURCE: shanukhera.medium.com] | VERIFIED |
| 6 | Clinical labs performing variant classification track reclassification events per ACMG/AMP guidelines and maintain audit trails of classification logic changes | ACMG Standards and Guidelines, CAP accreditation requirements | HIGH | [TRAINING-DATA, verified by search results] | VERIFIED |
| 7 | Post-implementation monitoring of AI/ML clinical tools uses control charts and ongoing performance metrics vs. reference standards | Mayo Clinic CLL MRD neural network validation study (Cancers 2025) | HIGH | [SOURCE: doi.org/10.3390/cancers17101688] | VERIFIED |
| 8 | ISO 17025 requires labs to maintain records of all conditions affecting test results, including software versions and reference databases | ISO 17025 standard, multiple LIMS vendor guides | HIGH | [SOURCE: wiselims.com/en/blog/iso-17025-lims] | VERIFIED |
| 9 | nf-test provides snapshot-based regression testing for Nextflow pipelines, comparing outputs against stored expected results | nf-test paper (GigaScience 2025) | HIGH | [SOURCE: doi.org/10.1093/gigascience/giaf130] | VERIFIED |
| 10 | GIAB benchmarking covers ~92% of GRCh38; performance inside vs outside high-confidence regions diverges massively (99.7% vs 76.5% SNV concordance) | Prior research memo, Krusche et al. 2019 | HIGH | [SOURCE: doi.org/10.1038/s41587-019-0054-x] | VERIFIED |
| 11 | Shadow mode / dual-write patterns from distributed systems engineering apply to pipeline validation: run old and new in parallel, compare, alert on divergence | Standard practice in MLOps and distributed systems | HIGH | [TRAINING-DATA] | VERIFIED |
| 12 | Multi-agent code conflicts are an unsolved problem; no production-grade framework exists for coordinating autonomous coding agents on the same codebase | No evidence of mature solutions found | MEDIUM | [INFERENCE from search results] | UNVERIFIED |

---

### 1. Agent-Introduced Regression Detection

The core problem: an agent modifies classification logic, updates a database, or refactors a tool. The change passes basic tests but silently degrades output quality in a way that only manifests downstream or on edge cases.

**Pattern 1: Golden Dataset Regression (the canary)**

Run a frozen reference dataset (GIAB HG002, or a curated subset of your own genome's known variants) through the pipeline before and after every code change. Compare outputs deterministically.

What to compare:
- **Variant call concordance:** Use hap.py/vcfeval against the GIAB truth set. Any change in F1, precision, or recall beyond a defined tolerance (e.g., 0.001) blocks the commit.
- **Classification concordance:** For a fixed set of ~50-100 known variants (pathogenic, benign, VUS), compare classification outputs before and after. ANY reclassification triggers review.
- **Numerical stability:** For PRS scores, ancestry proportions, heterozygosity rates — compare floating-point outputs within tolerance bands.
- **Output schema stability:** Assert that output files have the expected columns, types, and row counts.

Implementation:
```
# Pre-commit hook or post-commit CI job
1. Run pipeline on frozen GIAB HG002 subset (chr22, ~5min)
2. Compare VCF output against stored baseline VCF
3. Compare classification output against stored baseline classifications
4. Compare summary statistics against stored baseline stats
5. If delta > threshold on ANY metric: block or flag
```

nf-test (GigaScience 2025) provides exactly this for Nextflow pipelines — snapshot-based regression testing where outputs are compared against stored expected results. The nf-core/variantbenchmarking pipeline (workflowhub.eu/workflows/1307) wraps hap.py, Truvari, and other comparison tools into a standardized workflow. [SOURCE: doi.org/10.1093/gigascience/giaf130, SOURCE: workflowhub.eu/workflows/1307]

**Pattern 2: Statistical Process Control (SPC)**

Borrowed from clinical laboratory medicine and manufacturing QC. Track key metrics over time and flag when they leave control limits.

Metrics to track per pipeline run:
- Total variants called (SNVs, indels, SVs separately)
- Ti/Tv ratio (should be ~2.0-2.1 for WGS)
- Het/Hom ratio (population-dependent but stable for one person)
- Variants per chromosome (stable for one person)
- Number of variants classified pathogenic, benign, VUS
- PRS score distributions

Implementation: SQLite table logging every pipeline run's summary stats. Control chart logic (mean +/- 2 SD over last N runs). Alert when a metric exceeds limits. This is how clinical labs monitor instrument performance — Levey-Jennings charts with Westgard rules. [TRAINING-DATA]

The Mayo Clinic CLL MRD study (Cancers 2025) demonstrates this pattern for a clinical AI tool: post-implementation monitoring uses ongoing comparison of AI-assisted results against manual reference to detect drift. They track concordance, sensitivity, and specificity on rolling windows. [SOURCE: doi.org/10.3390/cancers17101688]

**Pattern 3: Diff-Based Output Auditing**

For every pipeline run, store the full output artifacts (VCF, classification reports, etc.) with git-lfs or content-addressable storage. Maintain a `diff` between consecutive runs. Any run where the agent modified code should have its diff reviewed against the prior run's output.

The key insight from MLOps canary deployment: you don't need to know what "correct" looks like to detect change. If an agent's code change causes the output to change, that change itself is informative and should be visible. [INFERENCE]

---

### 2. Classification Drift Monitoring

Clinical genetics labs face the variant reclassification problem: variants are classified under ACMG/AMP criteria, but evidence changes over time (new population data, new functional studies, updated ClinVar submissions). Labs must periodically reclassify.

In an agent-modified pipeline, drift has TWO sources:
1. **Evidence drift:** Upstream databases (ClinVar, gnomAD, OMIM) update, changing the inputs to classification logic. This is expected.
2. **Logic drift:** An agent modifies classification thresholds, adds new rules, or changes weighting. This is the dangerous kind — it may not be captured by standard tests.

**Monitoring patterns from clinical labs:**

1. **Reclassification event logging:** Every time a variant's classification changes, log: variant ID, old classification, new classification, reason (database update vs logic change vs new evidence), timestamp, and which agent/commit caused it. This is a regulatory requirement under CAP/CLIA for clinical labs. [TRAINING-DATA, confirmed by ACMG Standards]

2. **Classification distribution monitoring:** Track the proportion of variants in each ACMG class (P, LP, VUS, LB, B) over time. A sudden shift in the P/VUS ratio suggests either a database update or a logic change. For one person's genome, the distribution should be very stable.

3. **Sentinel variant panel:** Maintain a curated set of ~50 variants with known, manually verified classifications. After every pipeline change, re-run classification on this panel. Any discordance is a signal.

4. **ClinVar concordance tracking:** For variants that exist in ClinVar, track concordance between your pipeline's classification and ClinVar's. A drop in concordance suggests logic drift. Caveat: ClinVar itself has known issues (43% discordance between lab submissions for some variant classes). [SOURCE: genome.cshlp.org/content/33/6/999]

**The MLOps analogy:**

| ML Monitoring Concept | Genomics Analogy |
|----------------------|------------------|
| Data drift (input distribution change) | Database version change (ClinVar update, gnomAD release) |
| Concept drift (relationship between input and output changes) | Classification logic change by agent |
| Prediction drift (output distribution change) | Reclassification rate change |
| Ground truth comparison | ClinVar/GIAB concordance check |
| Feature importance tracking | Which ACMG criteria are driving classifications |

---

### 3. Gate Architecture for Agent-Modified Pipelines

A 4-layer gate architecture, ordered from cheapest to most expensive.

**Layer 0: Pre-Commit Static Gates (< 5 seconds)**
- Syntax validation of all modified files
- Schema validation for config files, database schemas, VCF headers
- Import/dependency checks (no new unresolved imports)
- Type checking if applicable
- File size checks (no accidental data commits)

**Layer 1: Pre-Commit Fast Functional Gates (< 60 seconds)**
- Smoke test: run pipeline on a tiny subset (100 variants)
- Output schema assertion: correct columns, types, row counts
- Classification logic unit tests: fixed input variants produce expected classifications
- Database query tests: known queries return expected results

**Layer 2: Post-Commit Integration Gates (< 10 minutes)**
- Canary dataset run: full pipeline on GIAB HG002 chr22
- Concordance check against stored baseline
- Statistical comparison of summary metrics
- Regression test via nf-test snapshots

**Layer 3: Periodic Deep Validation (daily or weekly)**
- Full GIAB benchmarking (all 7 samples, stratified by region type)
- Classification drift analysis (sentinel panel + distribution monitoring)
- Cross-database consistency checks
- Provenance audit (all tool versions, database versions match expectations)

**Agent-specific considerations:**

The key difference from normal CI/CD: **agents can modify the tests themselves.** An agent that adds a new classification rule might also "helpfully" update the test expectations to match, masking a regression.

Mitigations:
1. **Test fixtures are read-only to agents.** Golden dataset files, expected output baselines, and sentinel variant panels must be in a protected directory that agents cannot modify without human approval. This is the genomics equivalent of the "data streams have owners" principle.
2. **Baseline updates require explicit human approval.** When an agent's change legitimately changes outputs (e.g., adding a new annotation source), the baseline update is a separate, human-approved step.
3. **Test-modification alerts.** If an agent modifies test files in the same commit as pipeline code, flag for review. The pattern: `git diff --name-only | grep -E '(test_|_test\.|fixtures/|expected/)'` in a pre-commit hook.

---

### 4. Canary Testing for Pipelines

**What mature pipelines do:**

- **nf-core:** Uses nf-test for snapshot-based regression testing. Each module has test data (tiny datasets) and expected outputs. CI runs these on every PR. The nf-core/variantbenchmarking pipeline specifically wraps hap.py, Truvari, and WITTYER for variant comparison. [SOURCE: workflowhub.eu/workflows/1307]

- **GATK:** Provides test datasets and expected outputs for each tool. The GATK resource bundle includes mini-reference genomes and test BAMs for rapid testing.

- **DRAGEN:** Illumina maintains internal regression suites across GIAB samples. Public performance data published in Nature Genetics (2024) shows performance across all 7 GIAB samples with stratification. [SOURCE: doi.org/10.1038/s41588-024-01944-2]

**Canary architecture for a personal pipeline:**

```
canary/
  fixtures/
    giab_hg002_chr22.bam         # Frozen input
    giab_hg002_truth.vcf.gz      # GIAB truth set
    sentinel_variants.tsv        # 50 known-classification variants
    expected_metrics.json         # Baseline metrics (SPC center line)
  baselines/
    output_v{N}.vcf.gz           # Stored baseline output
    classifications_v{N}.tsv     # Stored baseline classifications
    stats_v{N}.json              # Stored baseline statistics
  scripts/
    run_canary.sh                # Run pipeline on canary data
    compare_outputs.py           # Compare against baseline
    update_baseline.sh           # Human-only baseline update
```

The canary runs in shadow mode: it doesn't affect the real pipeline, just validates that the same inputs produce acceptably similar outputs after code changes.

**Cost model for a personal pipeline:**

- chr22 subset of GIAB HG002: ~2-3% of genome, runs in ~5 minutes on Modal
- Full GIAB HG002: ~45-60 minutes on Modal
- Sentinel variant classification: seconds (no alignment needed, just re-classify)
- Total daily canary cost on Modal: approximately $0.50-2.00 depending on depth

---

### 5. Provenance and Audit Trail

Clinical genomics labs maintain provenance through LIMS (Laboratory Information Management Systems). Key systems: Illumina Clarity LIMS, CloudLIMS, StarLIMS, custom solutions. [SOURCE: illumina.com, cloudlims.com, starlims.com]

**What they track:**

Per ISO 17025 and CAP accreditation requirements:
- **Software versions:** Every tool in the pipeline, pinned and recorded per run
- **Database versions:** ClinVar version, gnomAD version, OMIM date, dbSNP build
- **Reference genome:** Build, source, checksum
- **Classification logic version:** Which rules, which thresholds, which criteria were applied
- **Instrument parameters:** (not applicable for reanalysis, but important for wet lab)
- **Analyst identity:** Who (or what) reviewed/approved results
- **Change history:** What changed between runs, with justification

**For an agent-modified pipeline, the additional requirements:**

1. **Agent identity per change:** Which agent (Claude, Codex, Gemini) made each code change. Git already captures this via author, but a structured `Agent:` trailer in commit messages is more queryable.

2. **Motivation capture:** WHY the agent made the change. Not just the commit message, but the session context — what prompted the change, what evidence was cited. Session transcripts are the raw material; a structured `Motivation:` field in a provenance DB extracts the key fact.

3. **Dependency manifest per run:** A lockfile-like artifact recording every tool version and database version used in a specific pipeline execution. This exists in Nextflow as `pipeline_info/` with `software_versions.yml`. For non-Nextflow stages, capture manually.

```yaml
# run_manifest.yaml — generated per pipeline execution
run_id: "2026-03-23-001"
git_commit: "abc123"
agent_commits_since_last_run:
  - commit: "def456"
    agent: "claude-opus-4.6"
    scope: "classification"
    description: "Updated ClinVar pathogenicity threshold"
tools:
  bwa-mem2: "2.2.1"
  gatk: "4.6.1.0"
  deepvariant: "1.7.0"
  pharmcat: "2.15.3"
databases:
  clinvar: "2026-03-15"
  gnomad: "4.1"
  omim: "2026-03-01"
  dbsnp: "156"
reference:
  build: "GRCh38"
  checksum: "sha256:..."
```

4. **Result hash chain:** Each pipeline run produces a hash of its outputs. The sequence of hashes creates an append-only audit trail. If any output changes without a corresponding code or database change, something went wrong.

---

### 6. Cross-Agent Consistency

When Claude, Codex, and Gemini all modify the same pipeline, the coordination problem has three aspects:

**Problem 1: Semantic conflicts**

Two agents might both be valid individually but conflict when combined. Example: Agent A adds a new annotation source that changes how many variants pass a filter. Agent B tightens the filter threshold to reduce false positives. Together, they might eliminate true positives that Agent B's threshold would have kept under the old annotation.

**No mature framework exists for this.** [INFERENCE] Multi-agent coding is a 2025-2026 research area with no production-grade solutions for semantic conflict detection. The closest analogy is database schema migration coordination, where tools like Alembic/Flyway detect conflicting migrations.

**Practical mitigations:**

1. **Single-writer per scope.** Assign pipeline scopes (alignment, variant calling, classification, annotation, PRS, pharmacogenomics) and route agent tasks to one scope at a time. No two agents modify the same scope concurrently. This is optimistic concurrency control — scope-level locks.

2. **Post-merge integration test.** After any agent commit, run the Layer 2 integration gate. This catches conflicts that are invisible at the unit level.

3. **Agent-aware code review.** When Agent A modifies code, the next agent session in the same scope should start by reading the recent git log for that scope. The meta project already does this ("inventory before dispatch"). Enforce it for genomics.

4. **Monotonic improvement constraint.** Define a primary metric (e.g., F1 on GIAB HG002). No agent commit may decrease this metric. If it does, the commit is reverted automatically. This is the "ratchet" pattern — quality can only go up.

**Problem 2: Style/convention drift**

Three agents writing in three styles makes the codebase harder to maintain. This is the least important problem — linting and formatting tools handle it. Pre-commit hooks with ruff/black are sufficient.

**Problem 3: Knowledge fragmentation**

Agent A discovers that a particular gene region has high error rates. Agent B, in a later session, doesn't know this and writes code that relies on accuracy in that region.

Mitigation: The pipeline needs a **known-issues registry** — a structured document that agents must read before modifying a scope. The meta project's `agent-failure-modes.md` is an analogy. For genomics, this would be `pipeline-known-issues.md` listing problematic regions, known tool limitations, and scope-specific gotchas.

---

### 7. Recommended Architecture (Synthesis)

Combining all patterns into a concrete architecture for the genomics pipeline:

```
LAYER 0: Pre-commit (< 5s)
  ├── Syntax/type check
  ├── Schema validation
  ├── Protected file check (agents can't modify golden fixtures)
  └── Test-modification alert (flag if tests changed with code)

LAYER 1: Pre-commit functional (< 60s)
  ├── Smoke test (100 variant subset)
  ├── Classification unit tests (sentinel panel)
  └── Output schema assertions

LAYER 2: Post-commit integration (< 10min)
  ├── Canary run (GIAB HG002 chr22)
  ├── Concordance vs stored baseline
  ├── SPC metric check (vs historical control limits)
  └── Monotonic improvement check on primary metric

LAYER 3: Periodic deep validation (daily/weekly)
  ├── Full GIAB benchmarking (7 samples, stratified)
  ├── Classification drift analysis
  ├── Provenance manifest generation
  └── Cross-database consistency audit

PROVENANCE LAYER (every run):
  ├── Run manifest (tools, databases, git state)
  ├── Output hash chain
  ├── Agent commit attribution
  └── Reclassification event log

COORDINATION LAYER (continuous):
  ├── Scope-based write locks
  ├── Known-issues registry
  └── Agent inventory before dispatch
```

**The single most important thing:** Layer 2 — the post-commit canary on GIAB chr22 — provides the highest value-to-cost ratio. It catches most regressions at modest compute cost (~$0.50/run on Modal). Everything else is defense-in-depth.

**The second most important thing:** Read-only golden fixtures that agents cannot modify. Without this, an agent can silently "fix" a test it broke by updating the expected output.

---

### What's Uncertain

1. **No evidence of production multi-agent genomics pipelines.** The cross-agent consistency patterns are extrapolated from software engineering and MLOps, not observed in genomics specifically. [INFERENCE]

2. **Optimal canary dataset size is unknown.** chr22 is a practical choice (small, quick to run) but it may not exercise all pipeline stages equally. A more principled canary would include variants from each problematic region type (tandem repeats, segmental duplications, high-GC). This requires empirical testing.

3. **SPC thresholds for a single-person pipeline are untested.** Classical Westgard rules assume independent measurements. For one genome analyzed repeatedly, the variance comes from code changes, not measurement noise. The control limits may need to be tighter.

4. **Agent test modification is a real risk but the frequency is unknown.** Need to monitor how often agents in the genomics project actually modify test expectations alongside code changes.

5. **Classification drift monitoring for personal (non-clinical) use has no established standard.** Clinical labs follow CAP/CLIA. A personal pipeline can be more pragmatic, but "how much drift is acceptable" is a personal risk tolerance question.

---

### Search Log

| Axis | Tool | Query | Useful? |
|------|------|-------|---------|
| Practitioner/engineering | Exa advanced | CI/CD pipeline validation bioinformatics automated testing regression detection genomics | YES — found nf-core/variantbenchmarking, GA4GH QC standards |
| Academic/clinical | Exa advanced | variant classification drift monitoring clinical genomics laboratory quality assurance | PARTIAL — found Mayo CLL monitoring study, mostly non-genomics ML results |
| MLOps/adjacent | Exa advanced | MLOps data pipeline validation canary testing autonomous agents code changes regression detection | YES — found eval-driven development, canary deployment patterns |
| Provenance/audit | Exa advanced | clinical genomics laboratory provenance audit trail tool version database version CAP accreditation LIMS tracking | YES — found LIMS vendors, ISO 17025 patterns |
| Prior work | Local | genomics-benchmark-design.md | YES — GIAB, hap.py, nf-test, validation patterns already documented |

<!-- knowledge-index
generated: 2026-03-23T19:11:53Z
hash: a474f3e0eb9c

cross_refs: research/genomics-benchmark-design.md
sources: 3
  TRAINING-DATA: , verified by search results
  INFERENCE: from search results
  TRAINING-DATA: , confirmed by ACMG Standards
table_claims: 12

end-knowledge-index -->
