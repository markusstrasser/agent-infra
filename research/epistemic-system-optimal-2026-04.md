---
title: "Evidence-Tiered Epistemic Framework for Scientific Agents"
date: 2026-04-12
status: complete
ground_truth: claim_bench/src/, genomics/config/{claim_registry,verification_ledger,pgx_evidence_tiers,evidence_provenance_map}.json, phenome/scripts/claim_bench_adapter/, knowledge-accrual-architecture.md, knowledge-representation-paradigms.md
---

# Evidence-Tiered Epistemic Framework for Scientific Agents

**Question:** How should a scientific agent accumulate truth, evidence, and certainty
across domains — and what universal framework supports this while adapting per domain?

**Tier:** Deep | **Date:** 2026-04-12 (revised from genomics-specific v1)

---

## 1. The Problem: An Agent Accumulating Certainty

A scientific agent works across domains — genomic variants, self-reported phenotypes, drug-gene
interactions, causal relationships between interventions and outcomes. In each domain it holds
**claims**: assertions about the world that it uses when generating output.

These claims have different shapes:

| Domain | Example claim | Shape |
|--------|--------------|-------|
| Genomics | "rs8176719 is at chr9:133257521 on GRCh38" | Factual — verifiable against database |
| Phenome | "User reports chronic fatigue, severity 7/10" | Observational — authority-based |
| Causal | "Mediterranean diet reduces CRP by ~30%" | Evidential — accumulated from studies |
| Pharmacy/PGx | "CYP2D6 PM: avoid codeine" | Guideline — derived from evidence + consensus |

The agent's core epistemic problem is: **how confident should I be in each claim, and when
should that confidence change?**

This is not a freshness problem (though freshness is one signal). It's an **evidence
accumulation** problem. Confidence should naturally increase as more evidence arrives and
decrease when evidence contradicts or goes stale. Over time, the system should trend toward
higher certainty as the agent does its work — each session leaves claims in a better epistemic
state.

### What exists today (scattered across projects)

The pieces of this framework already exist, unconnected:

| Piece | Location | What it does |
|-------|----------|-------------|
| Typed claims | `genomics/config/claim_registry.json` (442 claims) | Epistemic class, evidence grade, lifecycle state |
| Per-facet verification | `genomics/config/verification_ledger.json` (973 facets) | Per-rsID status + dates from batch API checks |
| PGx evidence tiers | `genomics/config/pgx_evidence_tiers.json` | A/B/C tiers (RCT > meta-analysis > mechanistic) |
| Source provenance | `genomics/config/evidence_provenance_map.json` | Upstream sources, correlation groups, anti-double-counting |
| Authority hierarchy | `phenome/scripts/claim_bench_adapter/authority_classes.py` | SELF_REPORTED > MEDICAL_RECORD > WEARABLE ranking |
| Self-report verifier | `phenome/scripts/claim_bench_adapter/self_report_verifier.py` | Keyword-match presence checking |
| Freshness hook | `claim_bench/hooks/freshness_advisory.sh` | Warns agent when editing files with stale claims |
| Verification skill | `genomics/.claude/skills/bio-verify/` | Parallel verification against live APIs |
| Event-sourced ledger | `claim_bench/src/claim_bench/ledger.py` | JSONL append-only ledger — **0 events** |
| Verifier protocol | `claim_bench/src/claim_bench/verifier.py` | Typed verification interface — **0 implementations** (excluding phenome toy) |
| DecisionGate protocol | `claim_bench/src/claim_bench/decision.py` | Policy predicate interface — **0 real usage** |

**The working system is the top six rows.** The bottom three are infrastructure for a future
that hasn't arrived. After a full implementation session, the event ledger has zero events
because verification_ledger.json, pgx_evidence_tiers.json, and the bio-verify skill already
fill the roles.

---

## 2. How Real Systems Accumulate Scientific Knowledge

### Common pattern: current state + discrete tiers + audit trail

No real-world scientific knowledge system uses event sourcing. Every successful system uses
**current state with discrete confidence tiers, explicit upgrade/downgrade criteria, and an
audit trail through version history.** [SOURCE: ClinVar docs, Wikidata docs, SNOMED spec,
GRADE working group; see v1 memo for full citations]

| System | Confidence model | How confidence changes | Audit trail |
|--------|-----------------|----------------------|-------------|
| **ClinVar** | 4-star review status (0★-4★) | New submitter assertions → recalculate stars | SCV version increments |
| **GRADE** | 4 levels (High → Very Low) | Explicit upgrade/downgrade criteria | Systematic review updates |
| **ClinGen** | 5-tier classification (Pathogenic → Benign) | 28 evidence criteria, 4 strength levels each | Expert panel revision history |
| **Wikidata** | Preferred/Normal/Deprecated rank | New evidence → change rank with reason qualifier | Complete revision history |
| **SNOMED CT** | Active/inactive per effectiveTime | New row with new effectiveTime | Versioned rows |
| **Cochrane** | Living reviews + GRADE | New RCTs → update review + re-GRADE | Review version history |

### The ClinGen insight: general framework + domain-specific calibration

ClinGen has 28 evidence criteria that apply to ALL variants, but **Gene-Specific Expert Panels
(VCEPs) calibrate what counts as "strong evidence" for each gene.** [SOURCE: clinicalgenome.org]
The framework is universal; the calibration is domain-specific. What counts as "strong
functional evidence" for BRCA1 differs from TP53.

**This is the pattern we need.** A universal tier system (0-3) with domain-specific criteria
for what constitutes each tier level.

### The GRADE insight: explicit upgrade/downgrade criteria

GRADE doesn't just assign tiers — it specifies the REASONS for changing tiers:
- **Downgrade for:** risk of bias, inconsistency, indirectness, imprecision, publication bias
- **Upgrade for:** large effect size, dose-response gradient, all confounders would reduce effect

This makes tier assignment MECHANICAL, not subjective. Given the evidence profile, the tier
follows from the criteria. [SOURCE: knowledge-accrual-architecture.md]

### The Wikipedia insight: verifiability, not truth

"The threshold for inclusion is verifiability, not truth." Every claim must have a
**checkable** provenance trail, not necessarily a **checked** one. The agent system equivalent:
every claim needs a staleness condition and a verification mechanism, even if it hasn't been
verified yet. [SOURCE: knowledge-accrual-architecture.md]

### What does NOT work: event sourcing and continuous confidence propagation

- **Event sourcing:** No scientific knowledge system uses it. ClinVar/Wikidata/SNOMED use
  current state with version tracking. The event log adds overhead without proportional value
  for <5K claims. Git provides the audit trail for free.

- **Continuous confidence propagation (MayBMS/Trio):** Dichotomy theorem makes exact
  propagation #P-hard for most useful queries. Both implementations defunct. Every successful
  system uses discrete tiers instead. [SOURCE: Van den Broeck & Suciu 2015]

- **Agent reasoning uncertainty (Zhao ACL 2025, UProp):** Studies uncertainty compounding
  across agent REASONING steps — a different problem from data freshness/evidence
  accumulation. Relevant if we ever need to audit agent inference chains, not relevant for
  the claim confidence problem.

---

## 3. The Universal Framework: Three Concepts

### Concept 1: Confidence Tier

Every claim carries a single confidence tier (0-3). The tier is UNIVERSAL — all domains use
the same scale. The CRITERIA for reaching each tier are domain-specific.

| Tier | Name | Universal meaning | What changes agent behavior |
|------|------|-------------------|---------------------------|
| **0** | **Unverified** | No evidence beyond initial assertion | Warn on every use |
| **1** | **Single-source** | One verifier confirmed | Warn if stale (past TTL) |
| **2** | **Corroborated** | Multiple independent sources agree | Warn only if source reports new data |
| **3** | **Grounded** | Authoritative reference or expert consensus | Warn only on major upstream event |

Direction matters: the system should track whether confidence is growing or shrinking over
time. Git history of tier changes IS this trajectory — no separate tracking needed.

### Concept 2: Domain Adapter

Each domain defines how claims move between tiers. An adapter specifies:

```
adapter:
  name: string
  tier_criteria:
    0: {description, examples}
    1: {description, upgrade_from_0, downgrade_from_2}
    2: {description, upgrade_from_1, downgrade_from_3}
    3: {description, upgrade_from_2}
  staleness_signals: [what triggers re-evaluation]
  verification_mechanism: how claims are checked
  cadence: how often to run scheduled verification
```

This is NOT a Python protocol with zero implementations. It's a **JSON/YAML specification
per domain** that the hook and skill read.

### Concept 3: Delivery

The agent must encounter claim confidence at point of use. Three delivery mechanisms:

1. **Freshness hook** (existing) — PostToolUse advisory when editing files with stale or
   low-tier claims. Already works, needs tier awareness.
2. **Verification skill** (existing) — bio-verify for genomics, extensible per domain.
   Already works, needs scheduled mode.
3. **Source monitoring** (new) — detect upstream changes that trigger re-evaluation.
   Domain-specific: database releases for genomics, new studies for causal, new measurements
   for phenome.

---

## 4. Four Domain Instantiations

### 4a. Genomics — Factual Claims from Databases

**Claim shape:** Empirical fact verifiable against authoritative databases.
**Example:** "rs8176719 has ref allele 'C' at chr9:133257521 (GRCh38)"

**Tier criteria:**

| Tier | Criteria | Existing data mapping |
|------|----------|---------------------|
| 0 | Asserted in config, never verified | Claims with no entry in verification_ledger |
| 1 | bio-verify confirmed against one API (e.g., myvariant) | `verification_ledger.json` facets with single `method` |
| 2 | Multiple independent APIs agree (gnomAD + ClinVar + Ensembl) | Multiple facets per rsID with concordant results |
| 3 | From stable reference (ISBT blood group tables, ACMG SF gene list) or `recency_requirement_days: 0` | Claims already marked as "inherited" verification |

**Staleness signals:** ClinVar monthly release, gnomAD major release, CPIC guideline update.

**Verification mechanism:** bio-verify skill (existing) — parallel API queries.

**Cadence:** Monthly for ClinVar/CPIC domains, quarterly for gnomAD, never for stable
references.

**What already exists:** claim_registry.json, verification_ledger.json, bio-verify skill,
freshness hook, pgx_evidence_tiers.json (for the PGx subdomain). This domain is 80% built.

### 4b. Phenome — Observational Claims from Self-Reports

**Claim shape:** Observation about a person's health state, sourced from self-reports,
wearables, or lab tests.
**Example:** "User reports chronic fatigue, severity 7/10, onset 2024-06"

**Tier criteria:**

| Tier | Criteria | Authority mapping |
|------|----------|------------------|
| 0 | Unstructured mention in conversation or notes | No authority class |
| 1 | Structured self-report (logged in phenome system) | `self_reported` |
| 2 | Corroborated by wearable data or repeated measurements | `wearable` + `self_reported` agree |
| 3 | Lab test or medical record confirms | `medical_record` or `lab_test` |

**Staleness signals:** New measurement contradicts prior (e.g., fatigue severity dropped from
7 to 2). Time since last measurement (chronic conditions need periodic re-assessment).
New lab results that bear on a self-reported claim.

**Verification mechanism:** Consistency checking — does the self-report align with wearable
data? Does the latest lab test support or contradict the claim? NOT database API queries.

**Cadence:** Triggered by new data arrival (new lab result, new wearable export), not calendar.

**What already exists:** Phenome adapter with authority_classes.py (the hierarchy IS the tier
system), self_report_verifier.py (toy keyword matcher — needs real consistency logic).

**Key difference from genomics:** Confidence comes from CORROBORATION across data modalities,
not from checking against an external database. A self-report confirmed by a wearable is more
certain than a self-report alone, regardless of when it was last checked.

### 4c. Causal — Evidence-Based Relationships

**Claim shape:** Causal or associational relationship between intervention and outcome,
accumulated from studies.
**Example:** "Mediterranean diet reduces CRP by ~30% (effect size from meta-analysis)"

**Tier criteria (GRADE-aligned):**

| Tier | GRADE equivalent | Criteria |
|------|-----------------|----------|
| 0 | Not assessed | Claimed but no evidence evaluation performed |
| 1 | Very Low / Low | Single observational study, or mechanistic reasoning only |
| 2 | Moderate | Multiple studies agree, or single well-conducted RCT |
| 3 | High | Meta-analysis of RCTs, or consistent evidence across study types |

**Upgrade criteria (from GRADE):**
- Large effect size (>2x risk ratio) → upgrade one level
- Dose-response gradient → upgrade one level
- All plausible confounders would reduce the effect → upgrade one level

**Downgrade criteria (from GRADE):**
- Risk of bias in included studies → downgrade one level
- Inconsistency across studies → downgrade one level
- Indirectness (surrogate outcomes, different population) → downgrade one level

**Staleness signals:** New meta-analysis published. Landmark RCT contradicts prior evidence.
Cochrane review updated. Major replication failure.

**Verification mechanism:** Literature search (scite for citation stance, S2 for new
meta-analyses, Exa for recent evidence). NOT database API queries.

**Cadence:** Quarterly literature scan per intervention domain.

**What already exists:** pgx_evidence_tiers.json already has A/B/C tiers for the PGx
subdomain. The `/research` skill already does literature search. No automated causal claim
tracking yet.

**Key difference from genomics:** Evidence ACCUMULATES from studies over time rather than being
refreshed from a single authoritative database. Confidence can go UP as new studies arrive
(rare in genomics, where a verified fact stays verified). The right metaphor is Cochrane living
reviews, not ClinVar release checking.

### 4d. Pharmacy/PGx — Clinical Guidelines

**Claim shape:** Actionable recommendation derived from evidence + expert consensus.
**Example:** "CYP2D6 PM: avoid codeine, use non-codeine analgesics (CPIC Level A)"

**Tier criteria:**

| Tier | Criteria | PGx evidence tier mapping |
|------|----------|--------------------------|
| 0 | Claimed drug-gene interaction, no guideline | Not in pgx_evidence_tiers.json |
| 1 | PharmGKB clinical annotation exists | Tier C (mechanistic/PK only) |
| 2 | CPIC guideline published | Tier B (meta-analysis/observational) |
| 3 | CPIC guideline + FDA label agreement | Tier A (RCT-proven) |

**Staleness signals:** CPIC publishes new or updated guideline. FDA label change. New RCT
testing PGx-guided prescribing.

**Verification mechanism:** Check CPIC API/website, PharmGKB annotations, FDA label database.

**Cadence:** Monthly (CPIC updates). Triggered on FDA label changes.

**What already exists:** pgx_evidence_tiers.json with 20+ gene-drug pairs already tiered.
Bio-verify can check CPIC/PharmGKB via BioMCP. The evidence provenance map tracks upstream
source correlations.

**Key difference from causal:** Guidelines are AUTHORED by expert panels, not derived by the
agent. The agent's job is to track whether the guideline has changed, not to evaluate the
underlying evidence (though it should know the evidence tier for context).

---

## 5. The Evidence Accumulation Model

The four domains share a common evidence flow, just with different instantiations:

```
Observation/Data → Fact → Association → Mechanism → Guideline
     ↑                                                  ↑
  (phenome)                                      (pharmacy)
                    ↑              ↑
                (genomics)     (causal)
```

Each domain primarily operates at one level of this hierarchy, but they're connected:
- Genomic FACTS (variant frequencies, gene coordinates) feed into...
- CAUSAL claims (CYP2D6 status affects codeine metabolism) which feed into...
- GUIDELINES (avoid codeine for PMs) which feed into...
- PHENOME observations (user reports pain relief failure on codeine)

**Confidence propagation is NOT continuous** — it flows through this hierarchy as discrete tier
assignments. When a genomic fact is downgraded (gnomAD revises an allele frequency), the
downstream causal claim and guideline don't automatically change tier. They get flagged for
re-evaluation. The human/agent decides whether the upstream change affects the downstream claim.

This is the common law pattern: a lower court ruling being overturned doesn't automatically
overturn all cases that cited it — it flags them for reconsideration.
[SOURCE: knowledge-accrual-architecture.md, stare decisis analysis]

---

## 6. What to Keep, Replace, and Delete

### Keep (working, domain-general value)

| Component | Why | Domain |
|-----------|-----|--------|
| `ClaimRecord` type | Good Pydantic schema for typed claims | All |
| `EventType` enum | Sound vocabulary (VERIFIED/FALSIFIED/SUPERSEDED/RETRACTED) | All |
| `freshness_advisory.sh` hook | The delivery mechanism. Enhance with tiers | All |
| `claim_bench.toml` config | Per-project integration pattern | All |
| `claim_bench/cases/` | Gold test cases for benchmarking | All |
| `authority_classes.py` | Phenome authority hierarchy = tier criteria | Phenome |
| `pgx_evidence_tiers.json` | PGx-specific tier criteria, already populated | Pharmacy |
| `evidence_provenance_map.json` | Source correlation tracking | Genomics |

### Replace

| Component | Replace with | Why |
|-----------|-------------|-----|
| JSONL event ledger | Git-tracked JSON with inline tiers | 0 events; verification_ledger already works |
| `Verifier` protocol | Domain adapter specs (JSON/YAML) | Protocol had 0 implementations; specs are readable by hooks and skills |
| Per-claim TTL | Source-level staleness signals per domain adapter | Source freshness is the right granularity for database-derived claims |

### Delete

| Component | Why |
|-----------|-----|
| `DecisionGate` protocol | 0 real usage. The hook IS the decision gate. |
| `scan_and_decay` | DECAYED events are derivable. Gemini was right. |
| `meta_claim.py` | Meta-verification levels add complexity without value at <5K claims |
| `VerifierContext` | Designed for a protocol that doesn't exist |

---

## 7. Dissent and Open Questions

### Where this framework has genuine uncertainty

1. **Cross-domain propagation.** The "flag for re-evaluation" model (§5) is simple but
   imprecise. When a genomic fact changes, WHICH downstream claims should be flagged? The
   evidence_provenance_map.json has the right shape (upstream_sources, correlation_groups)
   but only covers scoring tools, not the full claim graph. Extending it is straightforward
   but not free.

2. **Causal domain automation.** Genomics verification is mechanical (query API, compare).
   Causal verification requires literature synthesis — an LLM-mediated task, not a
   deterministic check. Automating GRADE assessments is an active research area (Zhang et al.
   2026, "Guideline-Grounded Evidence Accumulation for High-Stakes Agent Verification",
   arXiv:2603.02798). Not ready for production.

3. **Tier calibration.** The 0-3 scale is arbitrary. ClinVar uses 0-4, GRADE uses 4 levels,
   ClinGen uses 5. The specific number matters less than having discrete tiers with explicit
   criteria. 0-3 was chosen for simplicity; it can be extended if domains need finer
   granularity.

4. **Scheduled verification cost.** Monthly ClinVar sweeps of 442 claims consume API quota.
   Need a 10-claim probe to estimate per-sweep cost before committing to a cadence.

### What this framework does NOT attempt

- **Continuous confidence scores.** Theoretically elegant, practically intractable (#P-hard).
  Discrete tiers work at every scale that matters.
- **Automated GRADE assessment.** Active research (Zhang et al. 2026), not ready.
  Causal domain starts with manual tier assignment, upgraded to semi-automated as tools mature.
- **Knowledge graph.** Vetoed (Neo4j for <100K edges). The claim graph is implicit in
  provenance maps and source attribution. Explicit graph adds infrastructure without adding
  information at this scale.

---

## Sources

### Fetched this session

- ClinVar SCV/RCV model: ncbi.nlm.nih.gov/clinvar/docs/identifiers/ [Perplexity, 15 citations]
- ClinVar review status: ncbi.nlm.nih.gov/clinvar/docs/review_status/
- Wikidata temporal qualifiers: wikidata.org/wiki/Help:Ranking [Perplexity, 15 citations]
- SNOMED effectiveTime: docs.snomed.org/snomed-ct-specifications/
- Zhao et al. ACL 2025 "Uncertainty Propagation on LLM Agent": doi.org/10.18653/v1/2025.acl-long.302
- Duan et al. 2025 "UProp": arxiv.org/abs/2506.17419 (11 citations)
- Rasheed et al. 2026 "From Fluent to Verifiable": arxiv.org/abs/2602.13855
- Zhang et al. 2026 "Guideline-Grounded Evidence Accumulation": arxiv.org/abs/2603.02798
- Van den Broeck & Suciu 2015: par.nsf.gov/servlets/purl/10073513

### Ground truth (existing memos, not re-derived)

- knowledge-accrual-architecture.md (Cochrane, ClinGen, IC, common law, Wikipedia)
- knowledge-representation-paradigms.md (MayBMS/Trio, OWL/RDF, Wikidata provenance, Toulmin)
- epistemic-architecture-v3.md (ACC calibration, measurement infrastructure)
- claim_verification_package_prior_art_2026-04-11.md (inspect_ai, FIRE-Bench)

### Codebase (read directly)

- claim_bench/src/claim_bench/{types,verifier,decision,ledger,ttl}.py
- genomics/config/{claim_registry,verification_ledger,pgx_evidence_tiers,evidence_provenance_map}.json
- phenome/scripts/claim_bench_adapter/{authority_classes,self_report_verifier,phenome_decision_gate}.py
- claim_bench/hooks/freshness_advisory.sh
- genomics/.claude/skills/bio-verify/SKILL.md

## Revision History

- **2026-04-12 v1:** Genomics-specific "Source-Tiered Living Verification" recommendation
- **2026-04-12 v2:** Rewritten as domain-general "Evidence-Tiered Epistemic Framework" covering
  genomics, phenome, causal, and pharmacy domains. Added evidence accumulation model (§5),
  domain adapter concept (§3), four domain instantiations (§4). Core recommendation unchanged
  (discrete tiers over event sourcing) but framing shifted from "data freshness" to "evidence
  accumulation."

<!-- knowledge-index
generated: 2026-04-12T21:13:20Z
hash: aab36f7277d7

title: Evidence-Tiered Epistemic Framework for Scientific Agents
status: complete
table_claims: 4

end-knowledge-index -->
