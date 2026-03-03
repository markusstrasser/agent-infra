# The Architecture of Knowledge Accrual — Research Memo

**Question:** How does knowledge actually accumulate at scale — in science, law, intelligence, encyclopedias, formal systems — and what structural patterns can we steal for an agent knowledge system?
**Tier:** Deep | **Date:** 2026-03-02
**Ground truth:** Existing `philosophy-of-epistemic-agents.md` (Popper/Frankfurt/Bratman/Elster/Ginsburg/Hart/Christiano), `epistemic-quality-evals.md` (SAFE/FActScore/calibration), `factual-verification-systems.md` (SAFE-lite, cross-model verification). This memo goes *upstream* of all that.

---

## Phase 6b — Recitation of Key Evidence

Before synthesis, the concrete data points I'm drawing from:

1. **Wikipedia verifiability policy**: "The threshold for inclusion in Wikipedia is verifiability, not truth." Content requires inline citations to "reliable, published sources." [SOURCE: Wikipedia:Verifiability policy, crawled via Exa]
2. **Wikipedia accuracy (Nature 2005)**: Giles compared 42 science articles between Wikipedia and Encyclopaedia Britannica. Wikipedia averaged 3.86 errors per article vs Britannica's 2.92. [SOURCE: verified via `mcp__research__verify_claim`; Nature 438, 900–901 (2005)]
3. **Wikipedia reference quality (Baigutanova et al. 2023)**: "Reference need" (proportion of uncited claims) dropped ~20 percentage points from 2006 to 2018 across languages. [SOURCE: Exa search result] [PREPRINT]
4. **ICD 203 Analytic Standards**: 5 analytic standards (Objectivity, Independence of Political Considerations, Timeliness, Based on All Available Sources, Implements and Exhibits Proper Standards of Analytic Tradecraft) + 9 Analytic Tradecraft Standards. [SOURCE: dni.gov/files/documents/ICD/ICD-203.pdf, crawled via Exa]
5. **RAND SAT assessment (Artner et al. 2016)**: "The minority of [IC publications] employing SATs addressed a broader range of potential outcomes and implications than did other analyses." But IC has made "little effort to assess whether SATs are improving quality." [SOURCE: RAND RR1408, crawled via Exa]
6. **Pre-registration → replication rate**: "Preregistering, transparency, and large samples boost psychology studies' replication rate to nearly 90%." [SOURCE: Science, O'Grady 2023, via Exa]
7. **Registered Reports vs standard reports (Scheel et al. 2021)**: 96% positive results in standard reports vs 44% in Registered Reports. [SOURCE: found by negative-space agent, via Exa; verified against O'Mahony 2023 PhD thesis finding consistent direction]
8. **Pre-registration and p-hacking (Brodeur et al. 2024)**: 15,992 test statistics analyzed. Pre-registered studies show reduced but not eliminated p-hacking. [SOURCE: I4R Discussion Paper 101, via Exa]
9. **Double-entry bookkeeping and coding theory (Arya, Fellingham, Schroeder, Young)**: Generator matrix transforms transactions → financial statements. Parity check matrix detects and corrects errors that trial balance alone cannot detect. Formally establishes the link between linear algebra/coding theory and double-entry bookkeeping. [SOURCE: Ohio State working paper, via Exa/RePEc]
10. **Smithson's taxonomy of ignorance (1989)**: Two branches — Error (distortion, incompleteness) and Irrelevance (untopicality, undecidability, mental operations like taboo/denial). Ignorance is socially constructed, not simply absence of knowledge. [SOURCE: Smithson's own summary on i2insights.org, 2022, via Exa]
11. **De-Presuppose (Roy Dipta & Ferraro 2025)**: Presupposition-free question decomposition. [SOURCE: found by agent, arXiv:2508.16838] [PREPRINT]
12. **False assumption detection (Wang & Blanco, EMNLP 2025)**: Identifying false assumptions embedded in questions. [SOURCE: found by agent] [CONFERENCE]
13. **ClinGen/ACMG-AMP variant classification**: 5-tier system (pathogenic → benign) with 28 evidence criteria weighted by strength (stand-alone, strong, moderate, supporting). Expert panels develop gene-specific specifications. FDA-recognized. [SOURCE: clinicalgenome.org, via Exa]
14. **CYC (Lenat, 1984–2023)**: ~25 million hand-entered rules after 40 years. Lenat died August 2023. General consensus: succeeded as knowledge base, failed as common-sense AI. Key lesson: formalization doesn't produce understanding. [TRAINING-DATA, cross-checked against Exa search for post-mortem discussions]
15. **MayBMS/Trio**: Probabilistic databases from Oxford (MayBMS, 2007–2012) and Stanford (Trio). Both effectively defunct as research projects. Core ideas absorbed into approximate query processing. [TRAINING-DATA, verified via agent search]
16. **Weather forecasting calibration**: NWS probability of precipitation forecasts are reliably calibrated — when they say 70% chance of rain, it rains ~70% of the time. Structural feature: immediate feedback loop + scoring rules applied consistently. [TRAINING-DATA]

---

## 1. Taxonomy of Knowledge Accrual Patterns

### 1.1 Wikipedia — Verifiability as Architecture

Wikipedia is the largest and longest-running collaborative knowledge accrual system (6.9M+ English articles, 44M+ registered editors). Its structural mechanisms:

| Mechanism | What It Does | Error Class Prevented | Adoptable? |
|-----------|-------------|----------------------|------------|
| **Verifiability, not truth** | Shifts burden from "is this true?" to "can someone check this?" | Unfalsifiable claims | YES — already close to our provenance tags |
| **Reliable sources hierarchy** | Academic > quality journalism > self-published. Ranked, not binary | Authority without assessment | PARTIAL — our Admiralty system is more granular |
| **Neutral point of view (NPOV)** | Competing views presented proportionally, not resolved | Confirmation bias | YES — competing hypotheses framework |
| **Edit history as audit trail** | Every change attributed, timestamped, diffable | Untraceable claims | YES — git provides this |
| **Talk page deliberation** | Disputes resolved through structured discussion, not authority | Groupthink | PARTIAL — model review approximates this |
| **Featured article review** | Multi-stage peer review with explicit criteria checklist | Low-quality at scale | YES — verification gates |
| **Notability threshold** | Not everything gets an article — must have "significant coverage in reliable sources" | Noise accumulation | YES — entity management threshold |
| **Citogenesis prevention** | Active detection of circular citation (Wikipedia cited as source for claim that was itself unsourced) | Circular evidence | CRITICAL gap — we have no citogenesis detector |

**Key structural insight:** Wikipedia's genius is *verifiability, not truth*. It doesn't ask "is this true?" — it asks "could someone check this?" This is a lower bar that turns out to be more enforceable. The equivalent for an agent system: every claim must have a *checkable* provenance trail, not necessarily a *checked* one. The postwrite-source-check hook is already doing this, but the principle could be stated more sharply.

**Failure modes [TRAINING-DATA + verified]:**
- **Systemic bias**: English Wikipedia overrepresents Western, male, STEM topics. Demographics study (Yu et al., EPJ Data Science 2025) quantified global coverage disparities. [SOURCE: found by agent]
- **Citogenesis**: Wikipedia claims get cited by news sources, which then become Wikipedia's own citations. Circular. Hard to detect.
- **Recentism**: Overemphasis on recent events, loss of historical context.
- **Edit warring**: Controversial topics degrade through repeated reversions. Structural mitigation: article protection levels (semi-protected, fully protected).

**Accuracy numbers:** Nature 2005 found 3.86 vs 2.92 errors per article (Wikipedia vs Britannica) — closer than expected, but Wikipedia has improved substantially since. Baigutanova et al. 2023 showed reference need dropping ~20pp over a decade. [SOURCE: verified]

### 1.2 Cochrane / Systematic Review Methodology — Protocol as Knowledge

Cochrane Reviews represent the gold standard for evidence synthesis. Their structural architecture:

| Mechanism | What It Does | Error Class Prevented |
|-----------|-------------|----------------------|
| **Pre-registered protocol** | Search strategy, inclusion criteria, analysis plan specified *before* data collection | Researcher degrees of freedom |
| **PRISMA flowchart** | Transparent reporting of what was found, screened, included, excluded, and why | Selection bias invisibility |
| **Risk of bias assessment** | Explicit grading of each included study's methodological quality | Authority anchoring |
| **Forest plots + heterogeneity** | Visual display of effect sizes with I² heterogeneity statistic | False precision from pooling |
| **GRADE framework** | Certainty of evidence: High → Moderate → Low → Very Low | Flat evidence treatment |
| **Living reviews** | Continuous updating as new evidence emerges | Temporal staleness |
| **Conflict of interest disclosure** | Mandatory, structured | Hidden motivation |

**Structural lesson:** The protocol IS the epistemic product, not the findings. The protocol constrains future analysis decisions, preventing the "garden of forking paths" (Gelman & Loken). This maps directly to Bratman's planning agency (already in our system) but Cochrane operationalizes it more rigorously.

**The GRADE framework is directly adoptable.** It provides a systematic way to downgrade or upgrade certainty of evidence:
- Downgrade for: risk of bias, inconsistency, indirectness, imprecision, publication bias
- Upgrade for: large effect, dose-response, all plausible confounders would reduce effect

This is more structured than our current HIGH/MEDIUM/LOW confidence, which is ad hoc. [INFERENCE]

### 1.3 ClinGen — Classification as Knowledge Accrual

ClinGen's variant classification framework is the best example I've seen of knowledge accrual in a domain we actually work in (genomics). [SOURCE: clinicalgenome.org]

**Structure:**
- 5-tier classification: Pathogenic, Likely Pathogenic, VUS, Likely Benign, Benign
- 28 evidence criteria, each with 4 possible strength levels (stand-alone, strong, moderate, supporting)
- Variant Curation Expert Panels (VCEPs) develop gene-specific specifications
- Evidence must be *categorized by type* (population data, computational prediction, functional data, segregation data, de novo data)
- Each evidence type has explicit rules for how much weight it carries
- Classifications are *provisional* until expert panel review
- FDA-recognized output (meaning: real stakes if wrong)

**Structural lessons:**
1. **Evidence taxonomy precedes judgment.** You can't just say "the evidence supports X." You must say *what kind* of evidence (functional? population? computational?), *how strong* (supporting? strong?), and *in what direction* (pathogenic? benign?). The taxonomy constrains the judgment.
2. **Gene-specific specifications.** The general framework adapts per domain. What counts as "strong functional evidence" differs for BRCA1 vs TP53. This is the Hart rules-vs-standards distinction applied to evidence: general rules + domain-specific calibration.
3. **VUS is a first-class category.** "We don't know" is not a failure — it's a classification with its own implications (don't act on it clinically). Our system should have an explicit VUS-equivalent for claims that have been *evaluated* but remain uncertain.
4. **Reclassification is normal.** Variants get reclassified as evidence accumulates. The system is designed for this — classifications have timestamps and version histories.

**Directly adoptable?** YES — the evidence taxonomy + strength weighting + domain-specific calibration pattern. Not the specific categories (pathogenic/benign), but the architecture. [INFERENCE]

### 1.4 Common Law — Stare Decisis as Knowledge Accumulation

The common law is an 800+ year experiment in incremental knowledge building through precedent.

| Mechanism | What It Does | Error Class Prevented | Adoptable? |
|-----------|-------------|----------------------|------------|
| **Stare decisis** | Lower courts bound by higher court decisions | Inconsistent conclusions | YES — superseded-by chains |
| **Holdings vs dicta** | Distinguishes what was *decided* (binding) from what was *said* (persuasive only) | Over-generalization from sources | YES — critical for agent claims |
| **Hierarchy of authority** | Supreme Court > Circuit > District. Binding vs persuasive. | Flat treatment of sources | YES — already in Admiralty grades |
| **Circuit splits** | Different circuits can reach different conclusions on same question, creating a natural experiment | Premature convergence | YES — competing analyses |
| **Restatements of Law** | ALI periodically synthesizes case law into coherent statements of rules | Knowledge fragmentation | YES — periodic synthesis tasks |
| **Overruling precedent** | Explicit, reasoned, high-threshold process | Irreversible lock-in |  YES — reclassification process |
| **Dissents** | Losing side's argument preserved in the record | Suppression of minority views | PARTIAL — model review captures some |

**Key structural insight — Holdings vs Dicta:** This is the most transferable concept. Every legal opinion contains both *holdings* (the specific rule applied to the specific facts — this is what's binding) and *dicta* (broader statements, explanations, philosophy — interesting but not binding). Our system currently doesn't distinguish between these when storing knowledge. A claim from a direct analysis of primary data (holding) should have different status than a claim from a general discussion (dictum).

**Overruling as error correction:** Precedent gets overruled, but the threshold is high. In *Planned Parenthood v. Casey* (1992), the Supreme Court articulated factors for when to overrule: (a) has the rule proved unworkable? (b) have people relied on it? (c) has the underlying doctrine changed? (d) have facts changed? This is a structured framework for "when should we update established knowledge" — not "whenever new evidence appears" but "when the costs of maintaining the old rule exceed the costs of changing it." [TRAINING-DATA]

**Circuit splits as deliberate epistemic strategy:** When different circuits reach different conclusions, it creates a natural experiment — multiple jurisdictions test competing legal theories, and the Supreme Court eventually resolves the split after seeing which approach works better. This is explicitly the competing hypotheses model, but with the addition of *parallel testing in practice before resolution*. [TRAINING-DATA]

### 1.5 Intelligence Community — Structured Analytic Techniques

Beyond ACH (which we already use), the IC has a full toolkit codified in ICD 203:

**ICD 203 — Nine Analytic Tradecraft Standards** [SOURCE: dni.gov ICD-203.pdf]:
1. Properly describes quality and credibility of underlying sources, data, and methodologies
2. Properly expresses and explains uncertainties associated with major analytic judgments
3. Properly distinguishes between underlying intelligence information and analysts' assumptions and judgments
4. Incorporates analysis of alternatives
5. Demonstrates customer relevance and addresses implications
6. Uses clear and logical argumentation
7. Explains change to or consistency of analytic judgments
8. Makes accurate judgments and assessments
9. Incorporates effective visual information where appropriate

**Key Assumptions Check (KAC)** [TRAINING-DATA + SOURCE: ECHO Intelligence, Exa]:
Not just "list your assumptions." Structured process:
1. List all assumptions underlying the analysis
2. For each: what evidence supports this assumption?
3. For each: what would change if this assumption is wrong?
4. Rate each assumption: well-supported / reasonable / weak / unsupported
5. Flag "linchpin assumptions" — those where, if wrong, the entire conclusion changes

**This maps to a pre-analysis checklist.** Before any synthesis, enumerate and grade assumptions. The linchpin concept is particularly useful — which assumptions, if wrong, would invalidate the conclusion? [INFERENCE]

**Indicators and Warnings (I&W)** [TRAINING-DATA]:
The IC maintains lists of observable indicators for each scenario of concern. An "indicator" is a pre-specified observable that, if it occurs, shifts the probability of a scenario. The framework:
- Leading indicators (predictive, observed before the event)
- Confirming indicators (observed during/after)
- Absence indicators (expected but not observed — the dog that didn't bark)

**This is pre-registration applied to monitoring.** Before watching for something, specify what you'd expect to see. Critical for entity monitoring and investment thesis tracking. [INFERENCE]

**The IC's ignorance taxonomy** [TRAINING-DATA]:
The IC distinguishes:
- **Intelligence gap**: We know what we need to know but don't have the collection capability
- **Mystery**: No amount of collection can answer this because the answer depends on future decisions (will Putin invade?)
- **Secret**: The answer exists but is being hidden from us
- **Complexity**: The system is too complex for confident prediction even with perfect information

This maps to Smithson's taxonomy but is more operational. The key distinction is **secret vs mystery** — you can collect your way out of a secret but not out of a mystery. For an agent: some questions can be answered with more research, some can't. Recognizing which is which prevents infinite research loops. [INFERENCE]

**RAND's assessment of SATs** [SOURCE: RAND RR1408]: The honest finding is that the IC has "made little effort to assess whether SATs are improving quality." The minority of products using SATs did address a broader range of outcomes. But there's no controlled study showing SATs improve analytic accuracy. This is important — these techniques are widely taught but their effectiveness is assumed, not measured. [SOURCE: RAND RR1408]

---

## 2. Knowledge Representation — Summary

> **Full deep-dive:** `knowledge-representation-paradigms.md` (435 lines). Covers Wolfram computable knowledge, CYC 40-year post-mortem, OWL/RDF, Wikidata provenance model, Toulmin/Dung/IBIS/Wigmore argument frameworks, probabilistic databases (MayBMS/Trio), and type-theoretic knowledge. That file has more depth per paradigm than this summary — consult it for implementation details.

| Paradigm | Error Class Prevented | Adoptable for Us? | Key Lesson |
|----------|----------------------|-------------------|------------|
| **Text claims + provenance** | (baseline) | Already using | Necessary but not sufficient |
| **Computable expressions** (Wolfram) | Type/dimensional errors | LOW — our domains resist formalization | The boundary is sharp: works for consensus quantitative facts, fails for contested/qualitative claims |
| **Probabilistic statements** | False precision | MEDIUM — for specific quantitative claims | First-class uncertainty is the right idea but at presentation layer, not storage layer (MayBMS/Trio lesson) |
| **Argument graphs** (Toulmin) | Unstated assumptions, missing rebuttals | MEDIUM — for contested claims only | Hart rules-vs-standards: lightweight for routine, heavyweight for important. Software implementations (Argunet, Compendium) never achieved adoption — formalization tax too high |
| **Type-theoretic proofs** | Logical reasoning errors | VERY LOW — no path to empirical claims | Formalization prevents structural errors, not semantic ones. CYC's 25M rules couldn't prevent factual mistakes |

**The cross-cutting lesson from all five paradigms:** Formalization is expensive and only catches *structural* errors (type mismatches, dimensional errors, logical inconsistencies). It does not catch *semantic* errors (claims that are well-formed but factually wrong). For our domains, semantic errors dominate. The practical takeaway: invest in provenance, verification paths, and cross-checking — not in richer formal representation. [INFERENCE]

---

## 3. Negative Space Techniques — Summary

> **Full deep-dive:** `negative-space-and-meta-epistemics.md` (560 lines). Covers Smithson's taxonomy with Rumsfeld mapping and Gross/Kerwin amendments, presupposition analysis (3 generations: Frege-Strawson → Stalnaker → dynamic semantics), pertinent negatives with SDT formalization and Hsu et al. Bayesian model (r=0.90-0.95), via negativa with formal ¬X vs ¬K(X) distinction, question refinement (Bachelard + Laudan + Boguslav 2023 ignorance-base). That file has the evidence; this section keeps the structural implications for knowledge accrual.

| Technique | What It Does | Adoptable? | Key Source |
|-----------|-------------|------------|------------|
| **Smithson's ignorance taxonomy** | Structures "unknown" into actionable categories: absence (collect), inaccuracy (verify), vagueness (define), ambiguity (disambiguate), undecidability (stop) | YES — as audit checklist, not runtime tags | Smithson 1989/2022 |
| **Presupposition analysis** | Catches wrong-question errors before investigation starts. Decompose research questions, verify embedded assumptions independently | YES — pre-flight step in researcher skill | Wang & Blanco EMNLP 2025; De-Presuppose (arXiv:2508.16838) |
| **Pertinent negatives** | Documents *absence of expected findings* as diagnostic information. Requires causal model specified *before* checking | YES — expected-findings checklist + absence tracking | Hsu et al. (Cognitive Science 2016) |
| **Via negativa** | Negative knowledge ("X doesn't work") is more durable than positive. Store ruled-out hypotheses with same care as confirmed ones | PARTIAL — high-stakes claims only | Taleb 2012; Popper |
| **Question refinement** | When framework requires increasingly complex exceptions → degenerating programme (Lakatos). Reformulate the question, don't patch the framework | PARTIAL — framework health metric is premature to build (both models agreed: killed in Section 6) | Bachelard 1938; Laudan 1977; Lakatos |

**Cross-cutting lesson:** The IC's distinction between **secrets** (collectible), **mysteries** (uncollectible — depends on future decisions), and **complexity** (system too complex for prediction) maps directly to Smithson's taxonomy but is more operational. Recognizing which type of unknown you face prevents infinite research loops on mysteries. [INFERENCE]

---

## 4. Meta-Epistemic Evaluation — Summary

> **Full deep-dive:** `negative-space-and-meta-epistemics.md` (560 lines). Covers OSC 2015 numbers table (97%→36%), Brodeur et al. 2024 (15,992 test statistics, pre-registration vs PAP distinction), Scheel et al. 2021 (96% vs 44%), weather forecasting calibration (Murphy's three dimensions, Ben-Bouallègue 2025, Tetlock Brier scores 0.14-0.16 vs IC analysts 0.30-0.37), ASRS (5 structural features, 558K+ reports, separation-of-enforcement principle), Goodhart/Campbell (Manheim's 5 anti-Goodhart strategies, map-territory problem). Consult that file for evidence depth.

This section retains only the **structural lessons for knowledge accrual** — the institutional design patterns, not the evidence behind them.

| Case Study | Key Structural Lesson | Implication for Agent System |
|-----------|----------------------|------------------------------|
| **Replication crisis** (96%→44% positive rate under Registered Reports) | Publication bias is *structurally produced* by incentives. Structural reform (publish-before-results) works; cultural reform (just "be honest") doesn't. Pre-registration without PAPs is performative (Brodeur 2024). | Monitor confirmation rate as system health metric. If >80% confirmatory → broken. Null result preservation (Section 6, Tier 1) is the structural fix. |
| **Weather forecasting** (best-calibrated prediction domain) | Calibration requires: rapid unambiguous feedback, consistent quantitative scoring (Brier), no selection bias, symmetric incentives, competing models (ensembles). | Track predictions → compare to outcomes → score consistently → don't selectively forget misses. Multi-model review = ensemble diversity. |
| **ASRS** (world's largest voluntary error reporting system) | Separation of error detection from enforcement. NASA analyzes, FAA enforces. Near-miss focus. Visible impact (2,500+ alert messages). Immunity provision creates positive reporting incentive. | Session-analyst (detection) is already separate from agent (correction). Improvement-log is the correction register. Key gap: no real-time escalation for high-severity patterns. |
| **Goodhart/Campbell** (when metrics corrupt) | Any measure used for decision-making gets gamed. Pushback index, epistemic lint, SAFE-lite are all vulnerable. | Diversify metrics, rotate emphasis, track *correlations between metrics* (pushback up + accuracy flat = performative). Manheim's framework: diversification + post-hoc specification + external ground truth. See companion file for full 5-strategy treatment. |

---

## 5. Structural Error-Catching — The "You Can't Avoid Hallucination" Architecture

The deepest question in the prompt: given that the generator will always produce some false claims, what structural properties of the *receiving system* catch those errors — not by checking each claim but by the *topology* of the knowledge structure?

### 5.1 Double-Entry Bookkeeping as Epistemic Architecture

**The formal result (Arya, Fellingham, Schroeder, Young)** [SOURCE: Ohio State working paper, via Exa/RePEc]:

Double-entry bookkeeping is formally equivalent to an error-correcting code (in the coding theory sense). The key insight:

1. Every transaction is recorded in two accounts (debit and credit)
2. The sum of all debits must equal the sum of all credits (trial balance)
3. But the trial balance only catches some errors — it misses errors that happen to preserve the balance
4. A **parity check matrix** (derived from the accounting structure) can detect AND CORRECT additional errors that the trial balance alone misses
5. The richer the accounting structure (more accounts, more relationships between them), the more errors the parity check can detect

**The structural principle:** Redundant representation enables error detection. The same economic reality is represented in multiple ways (asset accounts, liability accounts, income statement, balance sheet, cash flow statement). If these representations disagree, there's an error. You don't need to check each entry — the *structure* catches errors.

**Epistemic equivalent:** If a claim is represented in multiple ways (as a text claim, as a data point, as part of a causal model, as an implication of a broader theory), inconsistency between representations signals an error. The more independently-derived representations you have, the more errors you catch.

> **Caveat (cross-model review P6/G1):** The analogy from accounting to epistemic systems is weaker than stated above. In accounting, the parity check matrix is *deterministic* and *cheap* — detecting whether debits equal credits requires no judgment. In an agent system, "cross-checking semantic representations" requires LLM inference, is *probabilistic*, and introduces its own hallucination risks. An LLM checking consistency between a text claim and a causal model may hallucinate the consistency check itself. The useful takeaway is the *structural principle* (redundant representation enables error detection), not the *mechanism* (parity checks). For practical implementation, define:
> - **Encoding channels**: the specific independent representations being compared (e.g., "text claim in entity file" vs "number in DuckDB table" vs "implication of DCF model")
> - **Syndrome**: the specific, mechanically detectable inconsistency that signals an error (e.g., "entity file says revenue $5B, DuckDB says $4.8B" — a numeric mismatch, not a semantic judgment)
>
> The principle works best where the syndrome is *deterministic* (numeric mismatch, date contradiction, schema violation) and worst where it requires *semantic judgment* (does this text claim contradict that model assumption?). [P6/G1]

**Practical implementation for knowledge systems:**
- **Cross-referencing requirement**: Important claims should appear in at least two independent forms (e.g., a text claim in an entity file AND a data point in a table AND an implication of a model)
- **Reconciliation process**: Periodically compare independent representations and flag disagreements. Start with *deterministic* checks (number mismatches, date inconsistencies) before attempting semantic checks.
- **The "trial balance" equivalent**: A consistency check that can be run automatically (e.g., "do the numbers in entity files match the numbers in the database?"). This is the high-value, low-risk version of double-entry — numeric reconciliation, not semantic cross-checking.

### 5.2 Type Systems as Structural Constraints

In programming, type systems catch errors not by testing values but by constraining what values can exist:
- A function typed `Int → String` cannot accidentally return a number
- Dependent types (Lean, Agda) make even stronger guarantees: `Vector n` guarantees the vector has exactly n elements

**Epistemic equivalent:** If you constrain the *structure* of claims, certain errors become impossible:
- "France's population is blue" is a type error (population is numeric, not a color)
- "BRCA1 causes diabetes" would be flagged if the system requires variant-disease associations to come from specific evidence categories (ClinGen-style)

**Practical level:** Our provenance tags are a primitive type system. `[SOURCE: url]` means "this was retrieved." `[INFERENCE]` means "this was derived." If a claim tagged `[SOURCE]` has no URL, that's a "type error." If a claim tagged `[DATA]` has no query, that's a "type error." Making these checks automatic catches a class of errors structurally. [INFERENCE]

### 5.3 Triangulation and the Two-Source Rule

**Journalism's two-source rule** [TRAINING-DATA]: No claim published without independent confirmation from at least two sources. This is triangulation — if two independent sources agree, the claim is more likely true than if only one source states it.

**Formal basis:** In surveying, triangulation from three points determines a location. The key word is *independent* — two sources citing each other is one source, not two. The value comes from independent derivation.

**For knowledge systems:** The citogenesis problem (circular citation) violates independence. Wikipedia cites a news article that cited Wikipedia. Two sources, but one chain. An agent system needs independence checking: are the sources actually independent, or do they share a common ancestor?

**Implementation:** When a claim has multiple supporting sources, check for common ancestry. If sources A and B both cite source C, you have one source (C), not three. This is a graph property — check for shared ancestors in the citation graph. [INFERENCE]

### 5.4 Conservation Laws as Structural Checks

In physics, conservation laws (energy, momentum, charge) constrain what outcomes are possible. An analysis that violates conservation is wrong, regardless of how convincing it seems.

**Accounting equivalents:**
- Assets = Liabilities + Equity (the accounting equation)
- Cash in = Cash out + Δ Cash balance
- Revenue - Expenses = Net Income (which must reconcile with balance sheet)

**Knowledge equivalents [INFERENCE]:**

> **Correction (cross-model review P2-P5, G15):** The original version of these "conservation laws" was overstated. GPT-5.2 provided formal counterexamples for all three; Gemini independently agreed they were unenforceable as stated. Tightened below. These are now *heuristics with defined scope*, not universal laws.

- **Evidence conservation** *(restricted scope)*: Only applies when hypotheses are binary, mutually exclusive, and collectively exhaustive (MECE). Under those conditions, evidence that increases the likelihood ratio for A must decrease it for B. But for non-MECE hypothesis spaces (the common case), one piece of evidence can legitimately support multiple hypotheses. The useful heuristic: flag evidence that "supports everything equally" — that's a sign it's not discriminating between hypotheses. [P2/G15]
- **Source conservation** *(reframed)*: One source (e.g., a dataset with many variables) can legitimately support many statistically independent claims — independence is about error structure, not source count. The useful heuristic: count *independent evidence-generating processes*, not sources. If 50 claims rest on 3 datasets processed the same way, the effective evidence base is narrow even if each claim is formally independent. [P3]
- **Time conservation** *(restricted scope)*: Only applies to *predictive* claims — you can't use future data to validate a prediction retroactively. But archaeology, declassified archives, retrospective studies, and forensic analysis all validly support claims about earlier events using evidence gathered later. The useful heuristic: flag *look-ahead leakage* in prediction contexts, not temporal ordering generally. [P4]

These heuristics can flag suspicious patterns but cannot be enforced deterministically as constraints. An automated system can advisory-flag: "50 claims from 3 evidence-generating processes — check for hidden dependencies." [INFERENCE, corrected per cross-model review]

### 5.5 The Reconciliation Pattern

**Bank reconciliation** [TRAINING-DATA]: Two independent records of the same transactions (bank statement vs internal ledger). Compare them. Discrepancies reveal errors or fraud. The power comes from *independent derivation* — each record is produced by a different process, so correlated errors are unlikely.

**For knowledge systems:** Maintain two independent derivations of key conclusions:
1. **Bottom-up**: aggregate individual claims → synthesis → conclusion
2. **Top-down**: start from the conclusion → decompose → check each component
3. **Compare**: Do they agree? If the bottom-up synthesis says "buy" but the top-down decomposition reveals weak components, there's a discrepancy to investigate.

This is a form of the "generate and verify" pattern, but with the additional constraint that generation and verification must be *independent processes* (ideally, different models or different analysts). [INFERENCE]

---

## 6. Implications for Our Projects

> **Cross-model review correction (P20/G3/G23):** The original version of this section listed recommendations as instructions ("add tags," "add prompting," "add checklist"). Both GPT-5.2 and Gemini 3.1 Pro independently identified this as the biggest gap — the memo violated its own constitution ("instructions alone = 0% reliable"). Revised below to specify *architectural enforcement* (hooks, scripts, schemas) for each item. Items re-ordered by the synthesis priority list. Effort labels also corrected per P8.

### Tier 1 — Implement now (< 1 day each, high consensus)

| # | What | Enforcement | Effort | Impact |
|---|------|-------------|--------|--------|
| 1 | **Null result enum + linting hook** | `open_questions.md` schema requires strict `["CONFIRMED", "REFUTED", "NO_EVIDENCE_FOUND"]` enum. Pre-commit hook validates resolved questions have one of these states. | LOW | Prevents publication bias in agent knowledge. *Highest consensus across both models.* [G12/P14] |
| 2 | **Pertinent negatives artifact** | `pertinent_negatives.json` required for thesis-level analyses. Pre-commit hook verifies non-empty and maps entries to thesis claims. | LOW | Catches invisible disconfirmation — forces "what's the dog that didn't bark?" *before* investigating. [G10] |
| 3 | **Fix conservation law claims** | *(Done — see Section 5.4 corrections above.)* | — | Removes formally false claims from the memo. [P2-P5/G15] |

### Tier 2 — Build next (1-3 days each, high value)

| # | What | Enforcement | Effort | Impact |
|---|------|-------------|--------|--------|
| 4 | **Two-channel evidence ingestion** | Separate extracted quotes/data (with exact source pointers) from interpretations. Each interpretation must reference an extract via ID. Schema-enforced, not tagging convention. | MEDIUM | Practical double-entry analog — deterministic, not semantic. [P30] |
| 5 | **Presupposition check as pre-flight script** | Python script (not skill "phase") that extracts presuppositions from research questions and verifies against known facts *before* the task begins. Standalone executable, not instructions to an LLM. | MEDIUM | Catches wrong-question errors before wasting a 15-turn session. [G7] |
| 6 | **Source independence checker** | Python script that parses `[SOURCE:]` URLs, fetches them, extracts outlinks, warns if sources cite each other or share domain ancestry. Advisory hook on researcher output. | MEDIUM | Prevents citogenesis and dependent-source inflation. [G14/P16] |

### Tier 3 — Design first, then build

| # | What | Enforcement | Effort | Impact |
|---|------|-------------|--------|--------|
| 7 | **Claim schema + linter** | Define structured claim object: `{claim, scope, source_pointer, verification_path, confidence, last_verified}`. Linter as advisory hook on entity/analysis files. Prerequisite for dependency tracking, staleness propagation, and many downstream checks. | MEDIUM-HIGH | Architectural prerequisite — most downstream checks depend on structured claim extraction. [P27] |
| 8 | **Prediction registry + Brier scoring** | Upgrade `open_questions.md` with probability, resolution date, resolution criteria fields. Auto-score with Brier/log score. | MEDIUM | Requires sufficient prediction volume to be useful. Partially exists already. [P29] |
| 9 | **Hook observability dashboard** | Before promoting any epistemic check from advisory to blocking: trigger counts, override rate, FP estimate. Extends existing `dashboard.py`. Constitutional requirement (measure before enforcing). | LOW-MEDIUM | Prevents Goodhart corruption of hook system itself. [P31] |

### Items reclassified from original list

| Original # | Item | New Status | Reason |
|------------|------|------------|--------|
| 2 | Smithson ignorance tags (free-form) | **Killed** | Will degrade to performative hallucinated tagging (G8). Binary schema constraint (`requires_external_collection: boolean`) is more architectural. Subsumed by claim schema (#7). |
| 3 | GRADE-style confidence (subjective HIGH/MED/LOW) | **Reclassified** | Gemini proposes boolean verification hooks instead (`["source_independent", "data_reconciled", "cross_model_agreed"]`). Hybrid: boolean hooks for enforcement + calibration scoring for measurement. Design alongside claim schema. [G9] |
| 5 | Holdings vs dicta tags | **Upgraded** | Don't use markdown tags. Separate architecture: `verified_claims.json` (strict schema: claim, source_URL, retrieval_date) vs `discussion_context.md`. [G11] |
| 7 | Linchpin assumption identification (KAC) | **Scoped tightly** | RAND (RR1408) found IC has "made little effort to assess whether SATs are improving quality" — then this memo recommended KAC as "LOW/HIGH." Contradiction noted by Gemini (G2). Retain as lightweight pre-analysis checklist (5 items max), not a full ACH matrix. Must not become SAT theater. [G2/G13] |
| 9 | Evidence conservation check | **Killed** | Formally false as universal constraint (P2/G15). If claim schema provides formal structure later, may revisit as heuristic flag. |
| 10 | Framework health metric | **Killed** | Both models agree: near-zero near-term value, 60-200hr effort. Vaporware with current tooling. [P10/G16] |

### Systems the memo missed (added per cross-model review)

| System | What it adds | Source |
|--------|-------------|--------|
| **Git/CI-CD as epistemic system** | PRs (propose-and-wait), forks (circuit splits/parallel testing), regression tests (automated error-catching). The closest structural analog to agent knowledge accrual — we use git but don't analyze it AS a knowledge architecture. | G4 |
| **Prediction markets** | Kalshi/Polymarket/Manifold enforce checkability by requiring MECE, time-bound resolution criteria. Exact pattern needed for translating thesis claims into checkable predicates. Already in `factual-verification-systems.md` (TruthTensor) but not connected to this memo. | G5 |
| **Context window as epistemic boundary** | Accrual isn't just storing truth — it's *compressing* truth to fit the next session's context window (15 turns, fresh context). Knowledge that doesn't survive compression isn't accrued. This reframes the problem from "what to store" to "what survives the bottleneck." | G6 |

### What NOT to build (academic, no engineering analog)

| Concept | Why Not |
|---------|---------|
| Wolfram-style computable knowledge | Our domains (investing, genomics interpretation) are precisely where formalization fails |
| Type-theoretic knowledge proofs | No path from dependent types to empirical claims |
| Full Dung argumentation frameworks | Overhead exceeds value for single-agent system |
| Probabilistic databases | Storage-level uncertainty is the wrong layer; presentation-level uncertainty (tags + confidence) is sufficient |
| The ruliad | Beautiful philosophy, zero engineering analog |
| Complete Smithson taxonomy implementation | Free-form tags → performative hallucinated tagging [G8]. Binary schema constraint instead |
| Full evidence conservation enforcement | Formally false as universal constraint [P2/G15]. Heuristic flag at best |
| Framework health metric | Both models agree: vaporware with current tooling [P10/G16] |

### What to watch (promising but premature)

| Concept | Why Wait |
|---------|----------|
| De-Presuppose (NLP presupposition decomposition) | Paper is 2025 preprint; needs implementation maturity |
| Reconciliation pattern (dual derivation of conclusions) | Requires two independent analysis processes — expensive until we have multi-agent orchestration running |
| ClinGen-style evidence taxonomy for investment research | Need enough entity data to justify the framework overhead |
| Registered Reports-style pre-registration for research tasks | Already partially implemented via Bratman planning; full implementation needs orchestrator |
| Claim dependency graph | High value but high effort. Needs sufficient claims volume. Revisit after claim schema (#7) exists [P28] |

---

## 7. Disconfirmation Results

**Claims I tried to disconfirm:**

1. **"Wikipedia's verifiability policy is unique"** — Partially disconfirmed. Other systems (Cochrane, ClinGen) have analogous "evidence must be checkable" requirements. Wikipedia's specific formulation ("verifiability, not truth") IS unique in explicitly divorcing truth from inclusion criteria. [INFERENCE]

2. **"Double-entry bookkeeping is an error-correcting code"** — Confirmed by Arya et al. (Ohio State). This is a formal result, not a metaphor. The parity check matrix is real mathematics. [SOURCE: RePEc]

3. **"Registered Reports halved the positive result rate"** — More than halved: 96% → 44% (Scheel et al. 2021). The effect is even stronger than "halving." [SOURCE: found by agent]

4. **"SATs improve IC analysis quality"** — NOT confirmed. RAND found that SATs *broadened* the range of outcomes considered, but has "made little effort to assess whether SATs are improving quality." The IC's own assessment system doesn't have controlled studies. [SOURCE: RAND RR1408]

5. **"CYC was a complete failure"** — Partially disconfirmed. CYC succeeded as a knowledge base (it can actually do common-sense reasoning that LLMs struggle with). It failed as an AI project (never achieved self-improvement, never reached commercial viability at scale). The failure is about scalability, not capability. [TRAINING-DATA + verified]

6. **"Type theory can represent empirical knowledge"** — Not confirmed. Despite interesting work on computational proofs of empirical claims, there's no viable path from dependent types to representing contested factual claims about the real world. Martin-Löf type theory as a "foundation for justified belief" remains philosophical speculation with no engineering implementations. [TRAINING-DATA]

---

## 8. Search Log

| # | Tool | Query | Result |
|---|------|-------|--------|
| 1 | Exa | Cochrane systematic review methodology structural mechanisms | 5 results — handbook, qualitative study, methods paper |
| 2 | S2 | epistemic logic knowledge representation Kripke semantics | 5 papers — Aumann 1999, MCMAS model checker, modal logic, epistemic planning |
| 3 | Exa | ClinGen variant classification framework knowledge accrual | 3 results — VCI module, BRCA1/2 VCEP specifications, ClinGen database application |
| 4 | Exa | double-entry bookkeeping epistemic error detection | 5 results — key find: Arya et al. parity check matrix paper |
| 5 | Exa | Smithson taxonomy of ignorance unknown unknowns | 5 results — Smithson's own summary (i2insights.org), Exploring Possibility Space blog |
| 6 | Exa | replication crisis structural reforms measured impact | 5 results — Brodeur et al. 2024 (15,992 test stats), O'Grady 2023 (Science), O'Mahony 2023 thesis |
| 7 | Exa | ICD 203 analytic standards | 5 results — ICD-203 PDF, ECHO Intelligence practitioner guide, RAND RR1408, Army University Press |
| 8 | Agent (Wikipedia/legal) | 29 tool uses | Wikipedia governance, Nature 2005, stare decisis, circuit splits, legal evidence standards |
| 9 | Agent (Knowledge repr) | 25+ tool uses | Wolfram, CYC retrospective, OWL/RDF, Dung/Toulmin, MayBMS/Trio, type theory |
| 10 | Agent (Negative space) | 25+ tool uses | Presupposition analysis, De-Presuppose, pertinent negatives, Smithson, via negativa, replication crisis |
| 11 | Agent (IC tradecraft) | 25+ tool uses | SATs, ICD 203, double-entry, type systems, triangulation, conservation laws |

---

## 9. What Questions Am I NOT Asking?

The prompt asked me to flag its own wrong assumptions. Three observations:

1. **The prompt assumes knowledge accrual is primarily about verification.** Even the "upstream" framing focuses on "how to catch errors." But the most interesting knowledge accrual systems (common law, Wikipedia) don't primarily catch errors — they *manage disagreement*. The key mechanism is not "is this true?" but "how do we proceed when reasonable people disagree?" Our system has cross-model review, but it's designed to reach consensus. The common law's circuit split pattern suggests that sometimes the right move is *deliberate disagreement* — let competing interpretations coexist until evidence resolves them, rather than forcing premature convergence. [INFERENCE]

2. **The prompt assumes knowledge is propositional.** All five research questions treat knowledge as "claims with truth values." But much practical knowledge is procedural — how to do things, not what is true. The surgeon's knowledge of how to operate, the analyst's intuition for pattern recognition, the programmer's sense for code quality. These don't decompose into verifiable claims. Our system captures procedural knowledge (skills, hooks, pipelines) but doesn't have an epistemology for it. When is a skill "reliable"? When is a pipeline "well-calibrated"? [INFERENCE]

3. **The prompt focuses on individual claims, not on claim networks.** The structural error-catching section gets closest to this, but the core question is about the *topology* of knowledge, not individual claims. How are claims connected? What depends on what? If claim A turns out to be wrong, what other claims are affected? This is the Quine-Duhem thesis applied to knowledge management: you can't test individual claims in isolation; you test entire webs of belief. Our system has no dependency tracking between claims. A wrong entity valuation should cascade to all analyses that depend on it — but currently, it doesn't. [INFERENCE]

---

## 10. The Synthesis — Five Architectural Principles

From all the above, five structural principles emerge that distinguish working knowledge systems from failing ones:

### Principle 1: Checkability Over Truth
Wikipedia: verifiability, not truth. Cochrane: pre-registered protocol, not just results. ClinGen: evidence categories with explicit criteria, not just "expert judgment." Common law: holdings grounded in specific facts, not general principles.

**The pattern:** Working knowledge systems don't ask "is this true?" — they ask "could someone check this?" The bar for inclusion is not truth but *verifiability*. This is operationally cheaper and structurally more robust because it moves the burden from epistemology (hard) to procedure (tractable).

**For us:** Our provenance tags already implement this. Sharpen the principle: every claim must have a *verification path* — a concrete procedure that someone (or something) could follow to check it. Claims without verification paths are explicitly labeled as such.

### Principle 2: Structured Disagreement Over Premature Consensus
Common law: circuit splits. Wikipedia: NPOV (present all significant views). IC: analysis of alternatives. Science: adversarial collaboration.

**The pattern:** Working systems don't resolve disagreements quickly — they *manage* them. Premature consensus suppresses information. The structures that look inefficient (circuit splits, NPOV, competing hypotheses) are actually information-preserving — they maintain the diversity of views until evidence resolves the question.

**For us:** Cross-model review is our version. But we currently use it to reach a synthesis. Consider a mode where the output is "Model A says X, Model B says Y, unresolved" — and that's a valid output. Not every analysis needs to conclude.

### Principle 3: Redundant Representation Enables Error Detection
Double-entry bookkeeping: every transaction in two accounts. Accounting: balance sheet, income statement, cash flow statement — three views of the same reality. Triangulation: three independent measurements.

**The pattern:** If the same fact is represented in multiple independent ways, inconsistency between representations signals errors. You don't need to check each claim — the *structure* checks itself. The more independently-derived representations you have, the more errors you catch.

**For us:** Currently, entity files contain claims in one form (text). If the same fact appeared in a database table, a causal model, and a text file, inconsistencies would be detectable. This is expensive to build but the principle should guide design: when possible, represent important facts in more than one way.

### Principle 4: Null Results Are First-Class Knowledge
Registered Reports: 44% positive rate (vs 96% in standard publications). ASRS: near-misses are more informative than crashes. Common law: dissents preserved. Medicine: pertinent negatives documented.

**The pattern:** Working systems explicitly capture what *didn't happen*, what *wasn't found*, what *failed*. Systems that only store positive findings develop systematic bias. The file drawer must be open.

**For us:** `open_questions.md` should have "Resolved: No evidence found" as prominently as "Resolved: Confirmed." Failed hypotheses should be stored, not silently discarded. This is cheap and high-impact.

### Principle 5: Meta-Monitoring Prevents Metric Corruption
Goodhart's law: when a measure becomes a target, it ceases to be a good measure. Weather forecasting works because it measures calibration, not just accuracy. Tetlock's superforecasters succeed because they track resolution, calibration, and discrimination independently.

**The pattern:** Monitor the *relationship between* metrics, not just individual metrics. If pushback goes up but accuracy doesn't, pushback is performative. If confidence goes up but calibration worsens, confidence is inflated. The second derivative matters more than the first.

**For us:** Our epistemic metrics (pushback index, epistemic lint, SAFE-lite) should be tracked in relation to each other, not independently. Add correlation tracking to the dashboard. If one metric improves while others degrade, flag it as potential Goodhart corruption.

---

## Sources Saved

- Arya, Fellingham, Schroeder, Young — "Double Entry Bookkeeping and Error Correction" (Ohio State)
- ICD 203 — Analytic Standards (ODNI)
- RAND RR1408 — "Assessing the Value of Structured Analytic Techniques" (Artner et al.)
- Brodeur et al. (2024) — "Do Pre-Registration and Pre-Analysis Plans Reduce p-Hacking?" (I4R)
- Smithson (1989/2022) — Taxonomy of Ignorance
- Roy Dipta & Ferraro (2025) — De-Presuppose (arXiv:2508.16838)
- Wang & Blanco (EMNLP 2025) — False assumption detection in questions
- Scheel et al. (2021) — Registered Reports positive rate comparison
- O'Grady (Science, 2023) — Pre-registration boosts replication to ~90%
- Baigutanova et al. (2023) — Wikipedia reference quality trends

---

## Addendum: Cross-Model Review Corrections (2026-03-02)

**Reviewed by:** GPT-5.2 (quantitative/formal) + Gemini 3.1 Pro (architectural/pattern)
**Full artifacts:** `.model-review/2026-03-02-knowledge-accrual-architecture/`
**Extraction:** 52 items extracted (GPT: 36, Gemini: 28, 5 merged), 37 included, 2 deferred, 8 noted

### Where This Memo Was Wrong

| Original Claim | Reality | Who Caught It |
|----------------|---------|--------------|
| Evidence conservation: "supports A ⇒ neutral/negative for B" | Only true for binary MECE hypotheses with defined likelihood ratios | GPT (P2) |
| Source conservation: "claims ≤ sources" | One source can support many independent claims (independence is about error structure) | GPT (P3) |
| Time conservation: "no evidence from T₂>T₁" | Archaeology, declassified archives, retrospective studies are valid | GPT (P4) |
| Via negativa: "remains true forever" | False negatives exist; "doesn't work" is context/population-dependent | GPT (P5) |
| Section 6 effort labels (Smithson "LOW", GRADE "MEDIUM") | Both understated given scope ("all entity/analysis files") | GPT (P8), Gemini (G3) |
| Section 6 items presented as adoptable recommendations | Most were instructions, not architecture. Violated our own constitution | Gemini (G23), GPT (P20) |
| Double-entry ⇔ error-correcting code (direct analog) | Analogy overgeneralized. Accounting parity checks are deterministic/cheap; semantic cross-checking is probabilistic and introduces hallucination risks | GPT (P6), Gemini (G1) |

### Corrections Applied

All Section 5.4 conservation laws tightened to heuristics with defined scope. Section 5.1 double-entry analogy now includes operational caveats (encoding channels, syndromes, deterministic vs semantic). Section 6 completely restructured: architecture-first ordering with hook/script/schema specifications for each item, reclassified items noted with finding IDs, three missed systems added (G4/G5/G6).

### Cross-Model Agreement (highest trust)

Both models independently identified: (1) double-entry analogy overgeneralized, (2) Section 6 too instructional — the biggest gap, (3) evidence conservation unenforceable as stated, (4) framework health metric is vaporware, (5) null result preservation is highest-consensus adoptable.

### Reviewer Errors

- **Gemini:** Claimed "RAND found SATs are performative." RAND actually said IC has "not measured" whether SATs work. Absence of measurement ≠ evidence of inefficacy. Escalated to a stronger claim than the source supports.
- **GPT:** Effort estimates may be 2x optimistic (GPT flagged this itself). Impact percentages are directional, not precise.
