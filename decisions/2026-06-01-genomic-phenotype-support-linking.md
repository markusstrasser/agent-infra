---
id: 2026-06-01-genomic-phenotype-support-linking
concept: cross-repo-genomic-phenotype-linking
repo: phenome
decision_date: 2026-06-01
recorded_date: 2026-06-01
provenance: contemporaneous
status: accepted
initial_leaning: IC-weighted phenotype-profile similarity (Phenomizer/Exomiser-grade, option E) as the "deepest" representation
relations:
  - type: cross_repo_of
    target: 2026-05-23-variant-phenotype-overlay-retired
  - type: depends_on
    target: 2026-05-26-cross-attestation-substrate-v2
  - type: branches_from
    target: 2026-06-01-cross-repo-contradiction-layer-not-built
---

# 2026-06-01: Genomic→phenotype support linking — ship binary HP subsumption (D), defer IC (E)

## Context
Goal: answer, with auditable evidence, *does this person's genome predispose them
to conditions their observed phenotypes are consistent with?* Concretely, link a
genomics finding (gene → MONDO disease predisposition) to the person's observed
HP phenotypes in phenome, as a frequency-aware, penetrance-honest SUPPORT
relation. This is the long-deferred phenotype-linking work; built as a breaking,
full-migration subsystem (no compat shims) on the user's mandate.

Hard boundaries it had to respect: the join is AGENT-TIME only (genomics pipeline
never imports phenotype data, C-XREPO-IMPORT); no precomputed phenotype-overlay
stage (the `variant_phenotype_overlay` stage was retired 2026-05-23); `disease_gene`
stays blocked at the KG MCP boundary; corpus is the sole relation writer via the
transactional outbox; `grade_weight`/`support_balance` are evidence weights, never
probabilities; a cross-repo *contradiction* layer is vetoed (penetrance < 1, so
predisposition + an absent phenotype is not a contradiction — the apt relation is
*support*).

## Alternatives considered
1. **OLS MONDO obo_xref walk** — probed dead: OLS4 MONDO terms carry no HP
   annotations (only OMIM/Orphanet/UMLS xrefs).
2. **Embedding similarity** (disease/phenotype label cosine) — rejected: the
   vetoed embedding-stack pattern; discards curated frequency; "vibes not evidence".
3. **UMLS CUI crosswalk** — kept only as a degraded fallback (less curated, no
   frequency).
4. **HPOA bridge + binary HP subsumption (D)** — disease→HPOA HP profile; match
   observed HP if exact / ancestor / descendant. Correct, frequency-aware, simple.
5. **HPOA + information-content phenotype similarity (E)** — Resnik/Lin profile
   similarity; the apparent "deepest" representation.
6. **Reuse genomics LIRICAL output (F)** — LIRICAL is gold-standard but consumes
   the person's HPO terms AS PIPELINE INPUT → violates the agent-time-join boundary.

## Counterevidence sought
Searched for the case that E (IC similarity) is the right shipped default. Found
the opposite, three ways: (a) corpus `claim_relations` are PER-ASSERTION edges, but
E scores a whole-PROFILE overlap → category mismatch with the sink; (b) symmetric
best-match-average collapses a single exact 1-of-20 match to ~0.5, *understating*
strong evidence; (c) information content is only meaningful against a REFERENCE
corpus computed offline — patient-local IC at N=1 is meaningless. Cross-model
critique (Gemini 3.5 Flash + GPT-5.5) converged on these. So the "deepest" option
was wrong for this sink; the correct representation is the simpler per-pair one.

Also searched whether the corpus outbox can carry cross-repo identifiers (a
critique claimed it could not): false — `claim_relation_endpoints` carries
namespaced `repo:/local:/internal:` refs with subject/object roles, already
shipping the genomics/phenome round-trip.

## Decision
Ship **option D**: asymmetric (observed→disease) binary HP subsumption against the
curated HPOA disease→phenotype profile.

- **Ontology knowledge layer** (`phenome/ontology/`): a static, version-pinned
  DuckDB artifact built from HPO `v2026-02-16` + HPOA + Mondo `v2026-05-05` — HP
  is-a closure (reflexive), HPOA with NORMALIZED frequency (ratio/percent/HP-term
  → [0,1]; empty→`unknown`, never a fabricated 0), Mondo→OMIM/ORPHA xref
  canonicalized (`Orphanet:`→`ORPHA:`). The live OLS API cannot serve bulk
  closure; this is the offline layer.
- **Engine** (`phenome/linking/`, pure, agent-time): observed phenotype set =
  subject_specific assertions with OBSERVATIONAL predicates only
  (`presents_as`/`observed_in`/`measured_as`) — mechanistic verbs binding an HP
  term are not observations of it. MONDO→OMIM/ORPHA resolution is **fail-closed
  with full accounting** (unique/ambiguous/unresolved/no_hpoa — every finding in
  exactly one bucket, 0 silent drops). `grade_weight` = subsumption match
  confidence only (exact 1.0, observed_subclass 0.9, observed_superclass 0.6);
  HPOA frequency and the genomic risk source are SEPARATE evidence fields, never
  multiplied in (frequency is phenotype-given-disease, not penetrance; the weight
  is not a probability).
- **Emission**: `support` `claim_relations` via the EXISTING phenome
  `pending_corpus_attestations` outbox + the shared cross-process drain — corpus
  stays sole writer (lint-clean). A DISTINCT attestor (`genomic-phenotype-linker`),
  detector `genomic-phenotype-linker:v1`, invoked EXPLICITLY by the orchestrator,
  never wired into the phenome closure batch (so it cannot drift into a hidden
  precomputed overlay).
- **Agent surface**: a gene-SCOPED, read-only `genomic_phenotype_support` tool on
  the genomics-consumer MCP — the blessed home for agent-time phenotype synthesis.
  NOT `disease_gene`, NOT a pipeline stage. A provenance manifest (genomic source
  digest + phenome snapshot digest + full per-link evidence) is the auditable
  record the closed corpus relation schema cannot hold.

**Deferred behind gates:** E (IC profile similarity) until a reference-corpus IC
artifact exists AND it proves ≥15% incremental true links at ≤5% FP on fixtures;
temporal `onset` filtering. LIRICAL: recompute D agent-side (no Modal dependency);
run LIRICAL once offline only as a *comparator* to validate D's ranking.

## Evidence
- Real build: 19,944 HP terms, 217k closure rows, 282,723 HPOA annotations,
  19,069 Mondo xrefs.
- Real run: 38 subject-specific observed phenotypes; VHL → OMIM:193300 + ORPHA:892
  (18-term profile); scoped 3-gene query (VHL/TSC1/BRCA1) → 23 links, clean
  accounting (1 unresolved: a BRCA1 MONDO id with no OMIM/ORPHA xref).
- Full enqueue→drain→project→support_balance round-trip green against a temp
  CORPUS_ROOT; idempotent re-emit; `lint_no_direct_corpus_writes` exit 0.
- Cross-model critique drove the E→D simplification (plan fc1a3dd3 v2).

## Known limitation
Binary subsumption produces near-vacuous matches against very general observed
terms (e.g. "Abnormality of the nervous system"): a whole-catalog run emitted
~11.6k mostly-weak edges. Mitigation shipped: (a) the agent surface is gene-SCOPED
(whole-catalog rejected); (b) `observed_superclass` matches are weighted lowest and
fully visible in evidence. The principled fix is the deferred IC layer (E), which
down-weights low-information terms.

## Revisit if
A reference-corpus IC artifact is built and E clears its incremental-value gate; a
real cross-repo contradiction is ever observed (would reopen the contradiction-layer
veto, not this support layer); HPOA/HPO/Mondo version bumps materially change
profiles (rebuild the artifact, re-run the LIRICAL comparator).

## Supersedes
Nothing — additive. The retired `variant_phenotype_overlay` stage
(2026-05-23) was already removed from both the genomics producer and the phenome
consumer mirror in the 2026-05-31 reconciliation; this subsystem is its blessed
agent-time replacement, so no remnant deletion was required.
