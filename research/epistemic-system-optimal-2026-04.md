---
title: "Optimal Epistemic System for Agent-Driven Scientific Automation"
date: 2026-04-12
status: complete
ground_truth: claim_bench/src/, genomics/config/claim_registry.json, genomics/config/verification_ledger.json, claim_bench/hooks/freshness_advisory.sh, knowledge-accrual-architecture.md, knowledge-representation-paradigms.md, epistemic-architecture-v3.md
---

# Optimal Epistemic System for Agent-Driven Scientific Automation

**Question:** If we were designing the epistemic layer from scratch today, knowing what we
know from building claim_bench and reviewing it cross-model, what would we build instead?

**Tier:** Deep | **Date:** 2026-04-12

**Ground truth assumed (not re-derived):** Knowledge accrual patterns (Wikipedia, Cochrane,
ClinGen, IC, common law) are covered in `knowledge-accrual-architecture.md`. Probabilistic
database post-mortems (MayBMS/Trio) are covered in `knowledge-representation-paradigms.md`.
Epistemic measurement infrastructure is covered in `epistemic-architecture-v3.md`. The
claim_bench codebase was read directly for this memo.

---

## 1. What Problem Are We Actually Solving

**Not:** "How do we maintain an audit trail of verification events for scientific claims?"

**Actually:** "When an agent edits a file containing hardcoded biological claims, how does it
know whether those claims are still valid?"

The failure mode is specific: gnomAD releases new allele frequency data, ClinVar reclassifies
a variant, CPIC updates a drug-gene guideline — and the agent continues to use stale values.
The agent must be warned at point of use and have a mechanism to re-verify.

### What exists and what works

| Component | Status | Real data? |
|-----------|--------|------------|
| `claim_registry.json` (442 typed claims, rich metadata) | Works | Yes — 442 claims, inline verification_status |
| `verification_ledger.json` (per-rsID per-facet status + dates) | Works | Yes — 973 facets, last sync 2026-04-03 |
| `freshness_advisory.sh` (PostToolUse hook, warns on stale claims) | Works | Yes — fires when editing bound files |
| `bio-verify` skill (parallel verification against live APIs) | Works | Yes — 529 claims audited, ~13% error rate |
| `claim_bench` JSONL event ledger | Exists | **Zero events** |
| `Verifier` protocol (typed verification interface) | Exists | **Zero implementations** |
| `DecisionGate` protocol | Exists | **Zero implementations** |
| TTL/decay system (`scan_and_decay`) | Exists | **Never run on real data** |

**The working system is: registry + ledger + hook + skill.** The claim_bench infrastructure
(event ledger, Verifier protocol, DecisionGate, TTL) was designed for a future that hasn't
arrived. After a full implementation session, the ledger has zero events because
verification_ledger.json already fills the role, and bio-verify already fills the Verifier role.

### The cross-model review found the right tensions

The 2026-04-12 Gemini review correctly identified:

1. DECAYED events are "stateful noise" — staleness is derivable from `(now - verified_at) > TTL`
2. The freshness hook reads the registry, not the ledger — dual source of truth
3. The Verifier protocol was designed for the plan's shape, not real workloads

These are symptoms of a single root cause: **event sourcing is the wrong primitive for this
problem.**

---

## 2. Evidence Recitation — How Real Systems Handle This

### 2a. ClinVar: Current State + Aggregation Hierarchy

ClinVar does NOT event-source variant assertions. It uses a three-tier aggregation model:
[SOURCE: NCBI ClinVar docs, ncbi.nlm.nih.gov/clinvar/docs/identifiers, via Perplexity]

- **SCV** (Submitted ClinVar record): individual submitter's assertion for a variant-condition pair
- **RCV** (Reference ClinVar record): aggregates all SCVs for the same variant-condition pair
- **VCV** (Variation ClinVar record): aggregates by variant across all conditions

Changes are tracked through **version increments** on SCV/RCV/VCV accessions, not through an
event log. When a submitter updates their assertion, the SCV version number increments. When
aggregate data changes, the RCV version increments.

**Conflict handling:** When submitters disagree, ClinVar flags the conflict but displays
the more pathogenic interpretation. Expert panel assertions take precedence. ~5.7% of variants
have conflicting interpretations.

**Review status:** A 4-star system that quantifies confidence:

| Stars | Review Status | Criteria |
|-------|---------------|----------|
| 4★ | Practice guideline | From an official practice guideline |
| 3★ | Expert panel reviewed | From an approved expert panel (VCEP) |
| 2★ | Multiple submitters, no conflicts | Multiple submissions with criteria, concordant |
| 1★ | Single submitter with criteria | Single submission with assertion criteria |
| 0★ | No criteria provided | Assertion without supporting evidence |

[SOURCE: ncbi.nlm.nih.gov/clinvar/docs/review_status]

**Key structural lesson:** ClinVar solved the same problem (tracking scientific claim validity
over time from multiple sources with varying authority) without event sourcing. Its model is:
current state + version tracking + aggregation hierarchy + confidence tiers + audit trail
through version history.

### 2b. Wikidata: Qualified State + Ranking

Wikidata handles temporal validity through **qualifiers on current statements**, not event logs:
[SOURCE: wikidata.org/wiki/Help:Ranking, via Perplexity]

- **P585** (point in time): when a statement was true
- **P580** (start time): when validity begins
- **P582** (end time): when validity ends
- **Preferred/Normal/Deprecated** rank with reason qualifiers

History is maintained through **complete revision snapshots**, not event replay. To find state
at a past point in time, you examine the revision history — it's version-controlled, like git.

**Key lesson:** Temporal validity through qualifiers on current state, not through event streams.
Deprecation is a rank (metadata on the statement), not an event (a separate log entry).

### 2c. SNOMED CT: Versioned Rows with Effective Dates

SNOMED tracks concept validity through **rows with effectiveTime + active flag**:
[SOURCE: SNOMED CT Release File Specification, docs.snomed.org]

New state → new row with same ID, new effectiveTime, updated fields. "Most recent effectiveTime
before or equal to query date" determines current state. This is closer to event sourcing but
implemented as versioned snapshots, not as a replay log.

### 2d. Probabilistic Databases: Theoretically Elegant, Practically Dead

MayBMS (Oxford, 2007-2012) and Trio (Stanford): both effectively defunct. The dichotomy theorem
shows that for tuple-independent probabilistic databases, every UCQ is either polynomial-time
or #P-hard — no middle ground. Most useful queries require approximation.
[SOURCE: Van den Broeck & Suciu, Foundations and Trends in Databases 2015; verified in
knowledge-representation-paradigms.md]

**Conclusion from prior research:** "First-class uncertainty is the right idea but at
presentation layer, not storage layer."

### 2e. Uncertainty Propagation in LLM Agents: Compounds Across Steps

Zhao et al. (ACL 2025) "Uncertainty Propagation on LLM Agent" — first paper to formally study
how uncertainty propagates through multi-step agent actions. Key finding: uncertainty compounds
across agent steps, making final-step-only uncertainty estimation unreliable.
[SOURCE: 10.18653/v1/2025.acl-long.302]

Duan et al. (2025) "UProp" extends this to multi-step agentic decision-making, formalizing
propagation paths. 11 citations, indicating growing research interest.
[SOURCE: arXiv:2506.17419]

**But this applies to agent REASONING chains, not to data freshness.** We're not propagating
uncertainty through a multi-step reasoning process — we're checking whether upstream database
values have changed. The relevant propagation is simpler: stale source → stale claim → stale
output. A discrete tier system handles this without the theoretical machinery of continuous
uncertainty propagation.

### 2f. Rasheed et al. 2026: Semantic Provenance Graph

"From Fluent to Verifiable: Claim-Level Auditability for Deep Research Agents" proposes a
Semantic Provenance Graph with entailment weights w ∈ [0,1] connecting claims to evidence.
[SOURCE: arXiv:2602.13855]

The SPG is designed for a different problem than ours: auditing research agent OUTPUT
(did the agent faithfully represent the evidence it found?). Our problem is about INPUT
freshness (are the values the agent is working with still current?). The SPG is relevant
if we ever need to audit the agent's reasoning, but it doesn't help with the data freshness
problem.

### 2g. GRADE / Cochrane: Evidence Certainty Tiers

GRADE (Grading of Recommendations, Assessment, Development and Evaluation) provides 4 levels
of evidence certainty: High → Moderate → Low → Very Low. Downgrade for: risk of bias,
inconsistency, indirectness, imprecision, publication bias. Upgrade for: large effect,
dose-response.
[SOURCE: knowledge-accrual-architecture.md, originally from Cochrane/GRADE working group]

**Key lesson:** Discrete tiers with explicit up/downgrade criteria. Not continuous scores.
The tiers are actionable: "Low certainty" means "further research is very likely to change
the estimate." This maps to our problem: a 1★ claim means "should be re-verified before
relying on it."

### 2h. ClinGen: Evidence Taxonomy + Domain-Specific Calibration

5-tier variant classification with 28 evidence criteria, each with 4 strength levels.
Gene-specific Expert Panels (VCEPs) develop domain-specific specifications for what counts
as "strong evidence." FDA-recognized output.
[SOURCE: knowledge-accrual-architecture.md, originally from clinicalgenome.org]

**Key lesson:** The general framework adapts per domain. What counts as "strong evidence"
for BRCA1 differs from TP53. Our system should similarly allow domain-specific verification
standards (blood group claims vs pharmacogenomics claims have different freshness requirements).

---

## 3. Seven Architectural Approaches

### Approach A: "Streamlined Status Quo" — Delete the Unused Infrastructure

Keep verification_ledger.json as source of truth. Delete the JSONL event ledger, Verifier
protocol, DecisionGate protocol, TTL/decay system. Git provides the audit trail.

| Dimension | Assessment |
|-----------|------------|
| Mechanism | verification_ledger.json + freshness hook + bio-verify skill |
| What changes | Delete ~500 lines of unused code (ledger.py, verifier.py, decision.py, ttl.py) |
| Confidence model | Binary: verified/unverified (current state) |
| Audit trail | Git history |
| Agent behavior change | None — same as today |
| Maintenance | Lower (fewer components) |

**Strength:** Honest about what's actually used. **Weakness:** Doesn't improve on the status
quo — just prunes dead code.

### Approach B: "ClinVar-Style Assertion Model" — Submitter Aggregation

Model verification as a hierarchy of assertions: individual verifiers (like ClinVar SCVs)
feed into aggregate claim status (like RCVs). Each assertion is versioned.

| Dimension | Assessment |
|-----------|------------|
| Mechanism | verifier_assertions.jsonl → claim_aggregate.json → source_summary.json |
| What changes | Replace verification_ledger with assertion-level tracking |
| Confidence model | Star rating derived from assertion count + authority level |
| Audit trail | Assertion version history |
| Agent behavior change | Moderate — hook shows star rating, agent knows how much to trust |
| Maintenance | Higher (assertion management, aggregation logic) |

**Strength:** Handles multiple verification sources gracefully. **Weakness:** We have ~2
verifiers (bio-verify + manual), not ClinVar's hundreds of submitters. The aggregation
hierarchy is over-engineered for our scale.

### Approach C: "Wikidata-Style Qualified State" — Inline Metadata with Ranks

Claims carry verification metadata as qualifiers. Three ranks: preferred (current best),
normal (default), deprecated (superseded). No separate ledger.

| Dimension | Assessment |
|-----------|------------|
| Mechanism | claim_registry.json gains verification qualifiers inline |
| What changes | Merge verification_ledger INTO claim_registry; single source of truth |
| Confidence model | Preferred/Normal/Deprecated rank per claim |
| Audit trail | Git diff |
| Agent behavior change | Moderate — deprecated claims trigger warnings |
| Maintenance | Lower (one file, not three) |

**Strength:** Single source of truth, simple model. **Weakness:** claim_registry.json is
already 10K+ lines; adding per-claim verification metadata makes it unwieldy. The
verification_ledger operates at rsID/facet granularity which is coarser (and better) than
per-claim.

### Approach D: "Source-Level Freshness" — Verify Sources, Not Claims

Instead of tracking 442 individual claims, track 8-10 upstream data sources. When a source
is verified fresh, ALL claims derived from that source are transitively fresh.

| Dimension | Assessment |
|-----------|------------|
| Mechanism | source_freshness.json (8-10 entries) + verification_ledger.json |
| What changes | Add source-level tracking; freshness hook checks source first |
| Confidence model | Source freshness propagates to claims |
| Audit trail | Git history |
| Agent behavior change | High — "ClinVar released new data" triggers targeted re-verification |
| Maintenance | Lower (monitor 10 sources, not 442 claims) |

**Strength:** Reduces verification surface by ~50x. Matches how the data actually flows:
databases release data → claims are derived. **Weakness:** Some claims span multiple sources
(a variant's allele frequency comes from gnomAD, its pathogenicity from ClinVar). Need
per-claim source attribution.

### Approach E: "Confidence Tiers" — ClinGen/GRADE-Inspired Discrete Levels

Every claim carries a discrete confidence tier. Tiers have explicit upgrade/downgrade criteria
and are directly actionable by the agent.

| Dimension | Assessment |
|-----------|------------|
| Mechanism | claim_registry.json + confidence_tier field + tier definitions |
| What changes | Replace binary verified/unverified with 4-tier system |
| Confidence model | 0★ unverified / 1★ agent-checked / 2★ multi-source / 3★ reference-grounded |
| Audit trail | Git history |
| Agent behavior change | High — tier determines agent caution level |
| Maintenance | Low (tier assignment is mechanical) |

**Strength:** Directly actionable. A 0★ claim next to edited code triggers a warning; a 3★
claim from ISBT blood group tables needs no re-check. **Weakness:** Tier assignment for 442
claims needs initial seeding.

### Approach F: "Provenance DAG" — Rasheed-Inspired Lightweight Graph

A DAG connecting agent outputs → claims → sources → databases. Each edge carries a freshness
property. The agent traverses stale paths to find what needs re-verification.

| Dimension | Assessment |
|-----------|------------|
| Mechanism | claim_bindings.json (outputs→claims) + source attribution (claims→sources) |
| What changes | Add source attribution to claims; build traversal logic |
| Confidence model | Path freshness: min(edge freshness along output→source path) |
| Audit trail | Graph + git |
| Agent behavior change | Moderate — stale path detection on demand |
| Maintenance | Higher (graph maintenance, traversal logic) |

**Strength:** Compositional — freshness propagates through the dependency graph. Elegant for
the "which of my outputs are affected by this ClinVar update?" question. **Weakness:** We
already have the graph implicitly (claim_bindings.json maps files→claims, claims have
source_ids). Building an explicit graph adds infrastructure without adding information.

### Approach G: "Living Review Cycles" — Cochrane-Inspired Scheduled Verification

Scheduled batch verification per domain on a cadence. Not event-by-event but periodic sweeps.
Bio-verify runs on a schedule, updates verification_ledger.

| Dimension | Assessment |
|-----------|------------|
| Mechanism | Scheduled bio-verify per domain (weekly/monthly) + freshness hook |
| What changes | Add launchd plists for scheduled domain sweeps |
| Confidence model | Time-since-last-sweep + source monitoring |
| Audit trail | Git history + sweep logs |
| Agent behavior change | High — claims are proactively kept fresh, not just reactively warned |
| Maintenance | Low (scheduled tasks, existing bio-verify skill) |

**Strength:** Solves the "zero events in the ledger" problem by actually running verification
regularly. Proactive rather than reactive. **Weakness:** Cost — bio-verify calls live APIs,
and scheduled sweeps of 442 claims consume API quota. Needs rate-limiting and cost caps.

---

## 4. Selection Rationale — Composite Architecture

No single approach solves the whole problem. The right answer combines **D + E + G** with
the streamlining of **A**:

### "Source-Tiered Living Verification" — The Recommended Design

**Three layers, each solving a different problem:**

| Layer | Problem | Solution | Component |
|-------|---------|----------|-----------|
| **Source monitoring** | "Has ClinVar/gnomAD released new data?" | Source freshness tracker | `source_freshness.json` |
| **Claim confidence** | "How much should the agent trust this claim?" | 4-tier confidence model | `confidence_tier` field in claim_registry |
| **Active maintenance** | "Are claims actually being re-verified?" | Scheduled domain sweeps | launchd + bio-verify |

**Plus the existing working components:**

| Component | Role | Changes |
|-----------|------|---------|
| `claim_registry.json` | Typed claims with metadata | Add `confidence_tier` field |
| `verification_ledger.json` | Per-rsID per-facet status + dates | Add `_meta.sources` for source freshness |
| `freshness_advisory.sh` | PostToolUse hook | Show confidence tier in warning |
| `bio-verify` skill | On-demand verification | Add scheduled domain sweeps |

### Why this composite, not a single approach

- **D (source-level)** solves the scaling problem: monitor 10 sources instead of 442 claims
- **E (confidence tiers)** solves the actionability problem: the agent knows HOW much to trust,
  not just whether to trust
- **G (living review)** solves the "zero events" problem: verification actually happens
  regularly
- **A (streamline)** solves the maintenance problem: delete unused infrastructure

### What the confidence tiers look like

| Tier | Name | Criteria | Agent Behavior |
|------|------|----------|----------------|
| 0★ | Unverified | Never checked against live source | Warn on every edit of bound files |
| 1★ | Agent-checked | bio-verify ran, single source confirmed | Warn if >TTL days since last check |
| 2★ | Multi-source | Multiple independent APIs agree | Warn if >2×TTL days since last check |
| 3★ | Reference-grounded | From stable reference databases (ISBT blood group tables, ACMG SF gene list) or expert panel | Warn only if source releases new version |

Tier assignment is mechanical:
- Claims with `recency_requirement_days: 0` in the registry start at 3★ (stable references)
- Claims verified by bio-verify with one source → 1★
- Claims where multiple API sources agree → 2★
- Claims never verified → 0★

### Source freshness model

```json
{
  "_meta": {
    "sources": {
      "clinvar": {
        "release_checked": "2026-04-01",
        "current_release": "2026-04-01",
        "check_url": "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/",
        "check_cadence_days": 30
      },
      "gnomad_r4": {
        "release_checked": "2025-11-15",
        "current_release": "2025-11-15",
        "check_cadence_days": 90
      },
      "cpic": {
        "release_checked": "2026-03-20",
        "current_release": "2026-03-20",
        "check_cadence_days": 30
      }
    }
  }
}
```

When `current_release > release_checked` → trigger targeted re-verification for affected
domain. Source monitoring runs weekly via launchd (checks release pages, not individual claims).

### Scheduled verification cadence

| Domain | Cadence | Rationale |
|--------|---------|-----------|
| Pharmacogenomics (CPIC) | Monthly | CPIC publishes guideline updates ~quarterly |
| Variant pathogenicity (ClinVar) | Monthly | ClinVar releases monthly |
| Allele frequencies (gnomAD) | Quarterly | gnomAD releases are major events, not frequent |
| Blood group antigens (ISBT) | Never (3★) | ISBT tables change rarely; check on major ISBT release only |
| Gene coordinates (Ensembl) | Per GRCh release | Coordinates change only with reference genome updates |

---

## 5. What to Keep, Replace, and Delete from claim_bench

### Keep

| Component | Why |
|-----------|-----|
| `ClaimRecord` type in `types.py` | Good Pydantic schema. Useful for typed claim manipulation. |
| `freshness_advisory.sh` hook | The one thing that actually changes agent behavior. Enhance with tier display. |
| `claim_bench/cases/` (8 gold test cases) | Useful for future benchmarking via inspect_ai integration. |
| `EventType` enum | The classification (VERIFIED/FALSIFIED/SUPERSEDED/RETRACTED) is sound vocabulary. |
| Cross-model review findings | Architectural insight. Move to this memo or decisions/. |
| `claim_bench.toml` project-level config | Clean pattern for per-project claim_bench integration. |

### Replace

| Component | Replace With | Why |
|-----------|-------------|-----|
| JSONL event ledger (`ledger.py`) | `verification_ledger.json` (already works) | Ledger has 0 events. verification_ledger has 973 facets. Git is the audit trail. |
| `Verifier` protocol (`verifier.py`) | `bio-verify` skill (already works) | The skill already does parallel verification against live APIs. The protocol is a premature abstraction with 0 implementations. |
| Per-claim TTL (`ttl.py`) | Source-level freshness + confidence tiers | Source freshness is the right granularity. `scan_and_decay` generates DECAYED events that are derivable (Gemini's correct observation). |

### Delete

| Component | Why |
|-----------|-----|
| `DecisionGate` protocol (`decision.py`) | 0 implementations. "Promote/block/needs_review" is a surface the freshness hook already handles (it advises, the agent decides). |
| `scan_and_decay` in `ttl.py` | DECAYED events are derivable from `(now - verified_at) > TTL`. Writing them to a ledger is stateful noise. |
| `meta_claim.py` | Meta-verification levels (L0/L1/L2) add complexity without value at <500 claims. |
| `VerifierContext` | Designed for a verification protocol that doesn't exist. Bio-verify handles its own context. |

### The honest accounting

claim_bench is ~800 lines of production code with comprehensive tests. ~300 lines are
genuinely useful (types, hook, config pattern). ~500 lines solve a problem that
verification_ledger.json + bio-verify already solve. The implementation was well-executed —
the types are clean, the tests pass, the dedup logic is correct. The issue isn't code quality;
it's that the system was designed top-down from an event-sourcing plan rather than bottom-up
from the working verification flow.

---

## 6. Implementation Sketch

### Files (not code)

```
genomics/
├── config/
│   ├── claim_registry.json      # Add: confidence_tier per claim
│   ├── claim_bindings.json      # Unchanged
│   ├── verification_ledger.json # Add: _meta.sources for source freshness
│   └── claim_bench.toml         # Unchanged
│
├── scripts/
│   └── source_freshness.py      # NEW: check upstream source release dates
│
└── .claude/
    └── skills/
        └── bio-verify/
            └── SKILL.md          # Add: scheduled domain sweep mode
```

```
agent-infra/
├── claim_bench/
│   ├── src/claim_bench/
│   │   ├── types.py              # Keep ClaimRecord + EventType
│   │   ├── scorer.py             # Keep (inspect_ai integration)
│   │   ├── cards.py              # Keep (benchmark cards)
│   │   ├── task.py               # Keep (benchmark task)
│   │   ├── ledger.py             # DELETE
│   ���   ├── verifier.py           # DELETE
│   │   ├── decision.py           # DELETE
│   │   ├── ttl.py                # DELETE
│   │   └── meta_claim.py         # DELETE
│   ├── hooks/
│   │   └── freshness_advisory.sh # MODIFY: show confidence tier
│   └── cases/                    # Keep (gold test cases)
│
└── com.agent-infra.source-monitor.plist  # NEW: weekly source freshness check
```

### Migration path

1. Add `confidence_tier` field to claim_registry.json (seed from existing data: 
   `recency_requirement_days: 0` → 3★, `verification_status: "verified"` → 1★, else → 0★)
2. Add `_meta.sources` to verification_ledger.json (populate from current knowledge of
   source release dates)
3. Write `source_freshness.py` — checks upstream release pages, updates `_meta.sources`
4. Enhance `freshness_advisory.sh` to display confidence tier in warnings
5. Add scheduled mode to bio-verify skill (domain sweep, respecting API rate limits)
6. Create launchd plist for weekly source monitoring
7. Delete unused claim_bench modules (ledger.py, verifier.py, decision.py, ttl.py, meta_claim.py)
8. Update tests to reflect new structure

No big-bang migration needed. Steps 1-3 are additive. Steps 4-6 enhance existing components.
Step 7 is cleanup after the new system is validated.

---

## 7. What This Memo Does NOT Answer

1. **Exact API endpoints for source release monitoring.** ClinVar FTP is straightforward;
   gnomAD blog/GitHub releases need discovery. This is a 1-hour probe, not research.

2. **Cost model for scheduled bio-verify sweeps.** 442 claims × API calls per claim × sweep
   frequency = ? Need a 10-claim probe to estimate per-call cost, then extrapolate.

3. **inspect_ai integration specifics.** The prior art memo (`claim_verification_package_prior_art_2026-04-11.md`) covers this — inspect_ai's Task/Solver/Scorer types are the benchmark foundation. This memo is about the epistemic layer, not the eval layer.

4. **Whether the confidence tier system needs per-domain calibration.** ClinGen uses
   gene-specific Expert Panels for domain calibration. At 442 claims across ~6 domains, this
   is premature. Revisit if claim count reaches >2000 or domains exceed 10.

---

## 8. Dissent and Open Questions

### Where I disagree with the plan

The plan proposed searching for "confidence propagation" as a continuous function 
`output.confidence = f(input_claims.verification_state)`. After researching probabilistic
databases, uncertainty propagation literature, and real-world scientific knowledge systems:

**Continuous confidence propagation is the wrong primitive for this problem.**

- The dichotomy theorem shows exact propagation is #P-hard for most useful queries
- No surviving implementation exists (MayBMS/Trio both defunct)
- Zhao et al./UProp study uncertainty in agent REASONING chains, not data freshness
- Every successful real-world system (ClinVar, GRADE, ClinGen) uses discrete tiers
- The information loss from discretizing is minimal: the agent doesn't need 0.73 confidence;
  it needs "verified last month by two sources" or "never checked"

The discrete-tier model (ClinVar stars, GRADE levels) is both theoretically sound and
practically proven at scales orders of magnitude larger than ours.

### Where I agree with the plan

The plan correctly identified that:
- Event sourcing creates overhead without proportional value at this scale
- The freshness hook is the right delivery mechanism
- Hierarchical verification (source → claim) is more efficient than per-claim
- The system should be maintainable by the agent itself
- DECAYED events are derivable (Gemini was right)

### Open question: Is the event log worth keeping for benchmark purposes?

The inspect_ai integration wants gold-case evaluation data. If we ever run bio-verify in
"eval mode" (compare agent verification against known ground truth), we'd want to log
verification events for analysis. The JSONL format is fine for this — but it's an EVAL
artifact, not an epistemic primitive. Keep it in the benchmark package, not in the core
epistemic system.

---

## Search Log

| # | Tool | Query | Signal |
|---|------|-------|--------|
| 1 | Read (7 files) | claim_bench source: types.py, verifier.py, decision.py, ledger.py, ttl.py | HIGH — understood full architecture |
| 2 | Read | genomics/config/claim_registry.json, verification_ledger.json | HIGH — grounded in real data |
| 3 | Read | freshness_advisory.sh, bio-verify/SKILL.md | HIGH — understood working system |
| 4 | Read | knowledge-accrual-architecture.md | HIGH — prior research covers Cochrane, ClinGen, IC, common law |
| 5 | Read | knowledge-representation-paradigms.md | HIGH — prior research covers MayBMS/Trio, Wikidata provenance |
| 6 | Read | epistemic-architecture-v3.md | HIGH — prior measurement infrastructure |
| 7 | Perplexity Reason | ClinVar SCV/RCV data model | HIGH — 15 citations, exact model details |
| 8 | Perplexity Reason | Wikidata temporal qualifiers + SNOMED effective dates | HIGH — 15 citations, both models |
| 9 | S2 search | Rasheed "From Fluent to Verifiable" | FOUND — arXiv:2602.13855 |
| 10 | S2 search | uncertainty propagation LLM agent | FOUND — UProp (11 cites), SAUP (8 cites) |
| 11 | scite search | "confidence propagation" OR "uncertainty propagation" agent LLM | FOUND — Zhao et al. ACL 2025 |
| 12 | Read | claim_verification_package_prior_art_2026-04-11.md | HIGH — inspect_ai integration context |

Budget used: ~$2 (2 Perplexity Reason calls, 2 S2 searches, 1 scite search, local reads).
Stopped well under $5 budget because existing research memos covered 70%+ of the questions.

**Disconfirmation searched for:**
- "event sourcing knowledge management success" — no hits in scientific/medical domain
- ClinVar/Wikidata/SNOMED all confirmed to NOT use event sourcing
- Continuous confidence propagation — confirmed intractable (dichotomy theorem) and no
  surviving implementations

---

## Sources

### Direct (fetched or read this session)

- ClinVar identifiers: https://www.ncbi.nlm.nih.gov/clinvar/docs/identifiers/
- ClinVar review status: https://www.ncbi.nlm.nih.gov/clinvar/docs/review_status/
- ClinVar review guidelines: https://www.ncbi.nlm.nih.gov/clinvar/docs/review_guidelines/
- Wikidata ranking: https://www.wikidata.org/wiki/Help:Ranking
- Wikidata qualifier P585: https://www.wikidata.org/wiki/Property:P585
- SNOMED CT specification: https://docs.snomed.org/snomed-ct-specifications/
- Zhao et al. ACL 2025 "Uncertainty Propagation on LLM Agent": https://doi.org/10.18653/v1/2025.acl-long.302
- Duan et al. 2025 "UProp": https://arxiv.org/abs/2506.17419
- Rasheed et al. 2026 "From Fluent to Verifiable": https://arxiv.org/abs/2602.13855
- Van den Broeck & Suciu 2015, "Probabilistic Databases": https://par.nsf.gov/servlets/purl/10073513

### Ground truth (existing memos)

- knowledge-accrual-architecture.md (Cochrane, ClinGen, IC, common law, Wikipedia)
- knowledge-representation-paradigms.md (MayBMS, Trio, OWL/RDF, Wikidata provenance, Toulmin)
- epistemic-architecture-v3.md (ACC calibration, measurement infrastructure)
- claim_verification_package_prior_art_2026-04-11.md (inspect_ai, FIRE-Bench)

<!-- knowledge-index
generated: 2026-04-12T20:16:30Z
hash: 4a7fcc7bfa56

title: Optimal Epistemic System for Agent-Driven Scientific Automation
status: complete
table_claims: 9

end-knowledge-index -->
