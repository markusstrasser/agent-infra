---
title: Knowledge Representation Paradigms for Agent Knowledge Systems
date: 2026-03-21
---

# Knowledge Representation Paradigms for Agent Knowledge Systems

*Date: 2026-03-02. Deep tier research.*
*Question: What knowledge representation paradigms enforce rigor structurally? What does each do well, where does it fail, and what class of errors does it prevent?*
*Context: Designing agent knowledge systems that work with text, data, and structured claims.*

---

## Ground Truth

No prior work in corpus on this topic. Training data covers all five paradigms at a conceptual level. All specifics (numbers, retrospectives, current states) verified via search.

---

## 1. Wolfram's Computable Knowledge

### How It Works

Wolfram Alpha represents knowledge as **computable expressions** in the Wolfram Language. Every fact is encoded not as a text string but as a symbolic expression that can be evaluated, transformed, and composed with other expressions. The Wolfram Knowledgebase contains millions of entities (cities, chemicals, genes, financial instruments) each with typed properties that return computed values, not stored text. [SOURCE: https://reference.wolfram.com/language/guide/KnowledgeRepresentationAndAccess.html]

The key architectural elements:
- **Entity/Property model**: `Entity["City", "Paris"]` has typed properties like `Population`, `Coordinates`, `Area` that return computable quantities with units
- **Symbolic expression language**: Everything is an expression (including code, data, and metadata). This means knowledge and computation share the same representation.
- **5 million lines of Mathematica code** (Theodore Gray, 2009) implementing ~10,000 algorithms that turn stored parameters into specific answers (e.g., the moon's current distance from orbital parameters, not a stored number) [SOURCE: https://blog.wolframalpha.com/2009/05/01/the-secret-behind-the-computational-engine-in-wolframalpha/]
- **Free-form linguistics layer** that maps natural language to precise Wolfram Language expressions

### What Errors It Prevents

1. **Unit inconsistency**: All quantities carry units. You cannot add meters to kilograms — the type system rejects it at evaluation time. This is the single strongest structural guarantee.
2. **Stale derived facts**: Because derived quantities are computed (not stored), they are always consistent with their parameters. The moon's distance is computed from orbital parameters, not cached.
3. **Ambiguity in entity reference**: `Entity["City", "Paris"]` is unambiguous — it distinguishes Paris, France from Paris, Texas through typed entity resolution.
4. **Type errors in composition**: Functions have typed signatures. Passing a string where a number is expected produces an error, not a plausible-but-wrong answer.

### Where It Fails

1. **Curated knowledge bottleneck**: Every domain must be manually formalized by Wolfram's team. The system cannot ingest unstructured knowledge and make it computable. This is the CYC problem at smaller scale — expert curation does not scale to the breadth of world knowledge. [INFERENCE: from architectural analysis]
2. **Qualitative and contested knowledge**: It cannot represent "the evidence suggests X but some researchers disagree." Computable expressions require definite values. Uncertainty, disagreement, and degrees of belief have no native representation.
3. **Narrative and causal reasoning**: "Why did the 2008 financial crisis happen?" is not a computable query. The paradigm handles *what* and *how much* well, but not *why*.
4. **Joel Spolsky's critique (2009)**: Wolfram Alpha fails on most real queries because it requires the user to ask a question that maps cleanly to a computable expression. Most human questions are ambiguous, context-dependent, and require common sense to interpret. "The secret of Google's success is that you don't need to know what you're looking for" — Wolfram Alpha requires you to know exactly what you want. [SOURCE: https://www.joelonsoftware.com/2009/07/09/why-wolfram-alpha-fails/]
5. **Boundaries of formalization (Ernest Davis, AMS 2024)**: Even elementary word problems that combine math with common sense cannot be reliably formalized by any AI system. The gap between natural language and formal representation remains open for any domain involving real-world context. [SOURCE: https://www.ams.org/journals/bull/2024-61-02/S0273-0979-2024-01828-X/viewer]

### The Ruliad

Wolfram's "ruliad" concept (the entangled limit of all possible computations, proposed as the fundamental structure underlying reality) received a Templeton Foundation grant for "Computational Metaphysics" in 2026. [SOURCE: https://writings.stephenwolfram.com/2026/02/what-ultimately-is-there-metaphysics-and-the-ruliad/]

A survey from the Wolfram Institute (Wiles 2025) positions it as bridging physics, CS, and philosophy. [SOURCE: https://wolframinstitute.org/output/computational-metaphysics-a-survey-of-the-ruliad-observer-theory-and-emerging-frameworks]

A philosophical analysis (Rickles, Elshatlawy & Arsiwalla, Pittsburgh PhilSci Archive) notes conceptual issues: what kind of object is the ruliad? How do observers relate to it? The paper identifies a fundamental limitation: any attempt to describe reality where the modeler-observers are included faces a self-reference problem. [SOURCE: https://philsci-archive.pitt.edu/22519/1/Ruliad.pdf]

**Assessment**: The ruliad is currently pure philosophy/physics speculation. It has zero practical implications for knowledge representation in agent systems. The concept of "computational irreducibility" (some computations cannot be short-cut, you must run them) is genuinely useful for understanding limits of prediction, but this idea predates the ruliad by decades (Wolfram's *A New Kind of Science*, 2002) and does not require the ruliad framework. [INFERENCE]

### Adoptability for Agent Systems

**Moderate for structured domains, poor for general knowledge.** The Entity/Property/Unit model is directly adoptable for representing quantitative claims (financial data, scientific measurements, demographic facts). The key insight — making knowledge executable rather than descriptive — is powerful. But the curation bottleneck and inability to represent uncertainty or disagreement make it insufficient as a general agent knowledge system. An agent could use Wolfram-style typed expressions as the *verified core* of a knowledge system while using other representations for uncertain/qualitative knowledge.

---

## 2. Ontologies & Knowledge Graphs

### 2a. Wikidata: Handling Contradictions and Provenance

Wikidata represents knowledge as **subject-property-value triples with references (provenance)**. Each statement can have:
- Multiple values for the same property (different sources may disagree)
- Qualifiers (temporal scope, geographic scope, ranking)
- References linking to external sources
- Ranks: preferred, normal, deprecated

**How it handles contradictions**: It does not resolve them. Wikidata stores all claimed values with their sources. The "preferred" rank is a community judgment about which value to display by default, not a truth determination. A 2017 ISWC study (Piscopo et al.) evaluated external references in Wikidata and found significant quality variation — provenance exists structurally but quality is uneven. [SOURCE: https://www.researchgate.net/publication/320199485]

A 2023 analysis (Yadav et al.) studied disagreement in Wikidata discussions and found that **more than half of controversial discussions do not lead to consensus**. Property deletions take far longer than creations. Despite this, Wikidata remains an "inclusive community." [SOURCE: https://export.arxiv.org/pdf/2306.11766v1.pdf]

**Key insight for agent systems**: Wikidata's model of "store everything with provenance, let consumers filter" is a pragmatic alternative to trying to determine truth. It separates knowledge acquisition from knowledge adjudication. This is structurally similar to what an agent should do — record claims with sources, defer judgment to query time.

### 2b. CYC: The 40-Year Post-Mortem

CYC (1984-present) is the most ambitious knowledge representation project ever attempted. ~30 million assertions, ~$200 million invested, ~2,000 person-years. [VERIFIED via Exa /answer, multiple sources]

**What worked** (from Lenat's final paper with Gary Marcus, arXiv:2308.04445):
- Expressiveness: CYC's representation language (CycL) is far more expressive than description logics (OWL). It can represent context, default reasoning, and second-order quantification.
- Scale of common sense coverage: No other system covers as much common-sense knowledge.
- Ken Forbus (Northwestern): "Cyc remains the most advanced in terms of expressiveness, capturing more of the range of thoughts that humans are capable of." [SOURCE: Gary Marcus obituary, https://garymarcus.substack.com/p/doug-lenat-1950-2023]

**What failed** (from Yuxi Liu's archival analysis, April 2025 — the most comprehensive retrospective):
1. **The "knowledge pump" never primed**: Lenat predicted that once enough common sense was encoded, the system would bootstrap — learn from reading text, conduct autonomous experiments. After 40 years and 30 million assertions, it never happened. The system remained dependent on manual encoding. [SOURCE: https://yuxi-liu-wired.github.io/essays/posts/cyc/]
2. **Secrecy killed academic adoption**: Cycorp's proprietary stance meant the research community could not build on, critique, or replicate the work. Contrast with Wikidata (open from day one).
3. **Brittleness at the edges**: CYC excels in narrow domains where the ontology is complete. It fails at the boundary between domains, where real-world problems live. Common sense is not a finite set of facts — it is an open-ended ability to handle novel situations.
4. **Funding pattern**: Approximately half military/intelligence-funded before 2010, entirely commercial since 2016. Cycorp survived as a business (rare for AI companies), but never achieved the generality Lenat promised.
5. **The central lesson** (Gary Marcus): "Cyc has been neither a success nor a failure, but somewhere in between: a ground-breaking, clarion experiment that never fully gelled." The problem CYC addressed — getting machines to reason about common sense — remains unsolved. LLMs have "an illusion of common sense" that fails under adversarial probing. [SOURCE: Marcus, 2023]

**Lenat/Marcus final paper (2023)**: Argues that LLMs need something like CYC's structured knowledge to move from "generative" to "trustworthy" AI. Proposes reconciliation between symbolic and neural approaches. [SOURCE: arXiv:2308.04445, 38 citations]

### 2c. OWL/RDF: What Consistency Guarantees Do Formal Ontologies Give?

OWL (Web Ontology Language) is based on description logics (DL) and provides:

**Guarantees** (from OWL 2 W3C specification):
- **Consistency checking**: Can determine if an ontology has no logical contradictions (no entity is both member and non-member of a class). This is decidable for OWL DL.
- **Subsumption checking**: Can determine if one class is necessarily a subclass of another.
- **Instance checking**: Can determine if an individual necessarily belongs to a class.
- **Entailment**: Can derive implicit facts from explicitly stated axioms.

[SOURCE: https://www.w3.org/TR/owl2-direct-semantics/Overview.html]

**The expressiveness-decidability tradeoff**: Full OWL DL reasoning is decidable but has worst-case 2-NEXPTIME complexity. Practical reasoning requires restricting to "profiles" (OWL EL, QL, RL) that are polynomial or NLogSpace. Krotzsch (2012) explains the design rationale — each profile drops features to ensure tractability: EL for large biomedical ontologies (SNOMED CT), QL for data-intensive applications, RL for rule-based reasoning. [SOURCE: https://www.researchgate.net/publication/266506924_OWL_2_Profiles_An_Introduction_to_Lightweight_Ontology_Languages]

**Practical limits**:
1. **Open World Assumption (OWA)**: OWL assumes that anything not stated might still be true. This means it cannot conclude something is false just because it is absent. This is correct for knowledge representation but counterintuitive for databases and often wrong for agent systems that need to act on available information.
2. **Unique Name Assumption is NOT default**: Two different names might refer to the same entity unless explicitly declared otherwise. This causes surprising inferences.
3. **Ontology Drift** (Shereshevsky, Feb 2026): Only 27% of organizations have knowledge graphs in production (Google Cloud survey, late 2025). Adoption is flat despite massive academic interest. The silent killer is ontology drift — the ontology stops matching reality as the domain evolves. No production system has solved this. [SOURCE: https://medium.com/graph-praxis/ontology-drift-why-your-knowledge-graph-is-slowly-going-wrong-234fa238826c]
4. **Logical consistency is not factual correctness**: A knowledge graph can be perfectly consistent (no internal contradictions) while being completely detached from reality. "The king of France is bald" is logically consistent but factually vacant. OWL guarantees coherence, not truth. [SOURCE: https://gpt.gekko.de/knowledge-graphs-llm-crisis-limitations/]
5. **Scaling reasoners**: For SNOMED CT (~350,000 concepts), state-of-the-art reasoners can classify in seconds-to-minutes. For full OWL DL, reasoning can become intractable. Dentler et al. (2012) compared EL reasoners on SNOMED CT and found significant correctness variations between reasoners. Recent work (GLaMoR, Mucke & Scherp 2025) achieves 95% accuracy 20x faster using graph language models, but trades mathematical guarantees for approximate results. [SOURCE: https://arxiv.org/pdf/2504.19023]

### What Class of Errors Ontologies Prevent

- **Taxonomic inconsistency**: X cannot simultaneously be a subclass and not-subclass of Y
- **Domain/range violations**: If "employs" links Organization to Person, an assertion linking Person to Integer is rejected
- **Cardinality violations**: If a person can have at most one birthdate, a second assertion is flagged
- **Disjointness violations**: If Cat and Dog are disjoint, nothing can be both

### What They Don't Prevent

- Factual errors within valid types (wrong birthdate, incorrect population)
- Stale knowledge (assertions that were true but are no longer)
- Missing knowledge (no assertion does not mean false under OWA)
- Contextual relevance (correct fact in wrong context)
- Anything requiring common sense or defeasible reasoning

### Adoptability for Agent Systems

**High for structural constraints, low for epistemics.** OWL-style type checking on entity properties is directly useful — it catches the class of errors where an agent asserts something structurally nonsensical (attaching a price to a person, assigning text where a number is expected). But it cannot catch the errors that matter most: wrong numbers, stale facts, unsupported claims, and missing context. The Wikidata provenance model (claims with references + ranks) is more useful for agent epistemics than the OWL consistency model.

---

## 3. Argument Frameworks

### 3a. Dung's Abstract Argumentation Frameworks

Dung's framework (1995, one of the most cited papers in AI — ~14,000 citations) models argumentation as a directed graph: nodes are arguments, edges are attacks. Multiple "semantics" determine which sets of arguments are acceptable (grounded, preferred, stable, etc.).

**Practical implementations exist**:
- **Dung-O-Matic** (ARG-tech, University of Dundee): Java implementation supporting multiple semantics. Web-service version via OVAgen. [SOURCE: https://arg.tech/index.php/?page_id=279]
- **Carneades 4** (GitHub): Go implementation of structured argumentation, 48 stars. [SOURCE: https://github.com/carneades/carneades-4]
- **arg2p-kt** (tuProlog/Bologna): Kotlin implementation of ASPIC+ framework. [SOURCE: https://github.com/tuProlog/arg2p-kt]
- **COMMA conferences** (Computational Models of Argument): Active biennial conference series, most recent 2022. [SOURCE: https://ebooks.iospress.nl/volume/computational-models-of-argument-proceedings-of-comma-2022]
- **ARG-tech secured $2.5M in funding** and spun out a commercial arm. [SOURCE: https://arg.tech]

**Bench-Capon et al. (2025)** provide a comprehensive survey of computational argumentation in AI & Law, tracing 30+ years of development from Dung's abstract framework through structured argumentation (ASPIC+, ABA) to current applications. Key finding: argumentation is central to legal AI, with active research on argument mining from natural text. [SOURCE: https://research-portal.uu.nl/ws/files/261007317/Computational_Models_of_Legal_Argument.pdf]

**Assessment**: Dung's framework is NOT purely theoretical — it has implementations, an active research community, and practical applications in legal reasoning and multi-agent negotiation. However, the abstract framework requires you to pre-identify arguments and attack relations, which is the hard part. The framework tells you what to accept *given* the attack graph; it does not help you build the attack graph from evidence. [INFERENCE]

### 3b. Toulmin's Model

Toulmin (1958) proposed that arguments have six components:
1. **Claim**: What you are asserting
2. **Grounds/Data**: Evidence supporting the claim
3. **Warrant**: The reasoning principle connecting grounds to claim
4. **Backing**: Support for the warrant itself
5. **Qualifier**: Degree of certainty ("probably", "certainly", "presumably")
6. **Rebuttal**: Conditions under which the claim does not hold

**Software implementations**:
- **Pacisco** (web-based): Collaborative argumentation system implementing Toulmin's structure with linked chains and plausibility ratings. [SOURCE: https://pacisco.org/pacisco-2/]
- **Compendium** (Open University): Evolved from IBIS into visual argumentation tool using Toulmin-influenced structures. Used extensively in NASA, design rationale capture. [TRAINING-DATA, verified name exists]
- Multiple argument mapping tools (Rationale, Argunet, MindMup) use Toulmin-inspired structures.

**Assessment for agent systems**: Toulmin's model is the most directly applicable to agent claims. The six-part structure maps cleanly to what an agent needs to produce:
- Claim = the assertion
- Grounds = retrieved evidence
- Warrant = the reasoning step (inference tag)
- Qualifier = confidence level
- Rebuttal = conditions under which the claim fails (disconfirmation)

No other framework makes the *qualifier* and *rebuttal* structurally mandatory. This is exactly what's missing from most agent outputs — they state claims without qualifying uncertainty or identifying defeat conditions.

### 3c. IBIS (Issue-Based Information System)

IBIS (Kunz & Rittel, 1970) structures deliberation as:
- **Issues**: Questions to be resolved
- **Positions**: Possible answers to issues
- **Arguments**: Pros and cons of positions

**Experience**:
- **gIBIS** (Conklin & Begeman, 1988): Graphical hypertext tool implementing IBIS. 1,316 citations. Early experiments showed the method was "still incomplete, but already a useful tool for thinking and communication." [SOURCE: https://www.semanticscholar.org/paper/gIBIS%3A-a-hypertext-tool-for-exploratory-policy-Conklin-Begeman/84676a4be7830a952f8799964321a1733443be46]
- **15-year retrospective** (Buckingham Shum et al., 2006): "Hypermedia support for argumentation-based rationale: 15 years on from gIBIS and QOC." The IBIS method was used for design rationale capture in software engineering. Key finding: useful for making design decisions explicit, but users resist the overhead of structuring their arguments while working. The "formalization tax" is real. [SOURCE: https://oro.open.ac.uk/3032/]
- **Compendium** evolved from gIBIS into a broader visual argumentation tool used by NASA, the UK Open University, and other organizations.

**Key lesson**: IBIS demonstrates that **structuring arguments during creation is cognitively expensive**. People naturally think in narratives, not argument trees. Post-hoc structuring (analyzing existing arguments) is more practical than real-time structuring (requiring people to argue in structured form).

### 3d. Wigmore Charts

Wigmore charts (1913) are visual diagrams for analyzing evidence in legal cases. They represent evidence items, their inferential relationships, and their collective support for ultimate propositions.

**Practical experience**:
- Leclerc, Verges & Vial (2022): Empirical study of whether Wigmore-style graphical methods can be used by judges. Finding: "their use by judges remains marginal, if not nonexistent." The overhead of constructing the chart outweighs the analytical benefit for experienced practitioners. Useful for training but not for practice. [SOURCE: https://hal.science/hal-03560219v1/document]
- Chalamish, Gabbay & Schild (2011): Formalized Wigmore diagrams as information-flow networks with fuzzy or probabilistic weights. [SOURCE: ResearchGate, ICAIL 2011]
- Goodwin (Informal Logic): Traces Wigmore's influence. His key contribution was representing *the strength of an argument in meeting objections* — not just logical structure but evidential weight. [SOURCE: https://informallogic.ca/index.php/informal_logic/article/view/2278/1722]

**Assessment**: Wigmore charts are powerful analytical tools that nobody uses in practice because they are too expensive to construct. The same pattern as IBIS — the "formalization tax" kills adoption. For agent systems, the key insight is that evidence should be represented with *inferential direction and weight*, not just stored. But requiring agents to construct full Wigmore charts for every claim is overkill. The useful extract is: every claim should track (a) what evidence supports it, (b) what evidence opposes it, and (c) the inferential pathway from evidence to claim.

### What Class of Errors Argument Frameworks Prevent

- **Unsupported claims**: Structurally require evidence for assertions
- **Unacknowledged counterarguments**: Dung's attack relation makes opposition explicit
- **Missing qualifiers**: Toulmin requires explicit uncertainty
- **Hidden warrants**: Toulmin separates evidence from the reasoning connecting it to the claim
- **Circular reasoning**: Dung semantics handle cycles (grounded semantics avoids all cycles)

### What They Don't Prevent

- Bad evidence (all frameworks are garbage-in/garbage-out on evidence quality)
- Wrong attack/support relationships (the hard part is identifying these, not computing over them)
- Formalization resistance (humans and agents resist the overhead of structuring arguments)

### Adoptability for Agent Systems

**High — the most directly applicable paradigm.** Toulmin's model can be implemented as a structured claim format without requiring the full apparatus of formal argumentation theory. An agent claim format like `{claim, grounds: [evidence], warrant: reasoning, qualifier: confidence, rebuttal: conditions}` would prevent the most common agent failure modes (unsourced claims, missing uncertainty, no acknowledgment of counterevidence) by making these fields structurally required. The key design question is the "formalization tax" — how to make structure cheap enough that it does not slow the agent down.

---

## 4. Probabilistic Representations

### 4a. Probabilistic Databases

**MayBMS** (Antova, Koch, Olteanu; Cornell/Oxford, 2007-2012): PostgreSQL extension for probabilistic data management. Supported compositional query language with worst-case efficiency guarantees. Featured repair-key, pick-tuples, confidence computation. [SOURCE: https://maybms.sourceforge.net/]

**Trio** (Stanford): Integrated uncertainty and lineage (provenance) management. Stored data alongside accuracy assessments and provenance tracking. [TRAINING-DATA]

**What happened**: The MayBMS project officially ran 2007-2012 at Oxford. The code remains on SourceForge but is effectively unmaintained. [VERIFIED] A comprehensive survey by Van den Broeck & Suciu (Foundations and Trends in Databases, 2015) provided the theoretical capstone. [SOURCE: https://par.nsf.gov/servlets/purl/10073513]

**The core theoretical result** (dichotomy theorem): For tuple-independent probabilistic databases, every UCQ (union of conjunctive queries) is either polynomial-time computable or #P-hard. There is no middle ground. This means query evaluation on probabilistic data is fundamentally harder than on deterministic data — most interesting queries require approximation.

**Why they did not succeed in practice**:
1. **Complexity barrier**: The theoretical results proved that exact query answering is intractable for most useful queries. Approximation is possible but loses the "database guarantee" of exact answers.
2. **Integration burden**: Requiring users to specify probability distributions over all uncertain data is impractical. Where does the probability come from?
3. **Limited demand**: Most database users want definite answers, not distributions. Uncertainty is handled at the application layer, not the storage layer.
4. **Absorbed into other fields**: The ideas live on in probabilistic programming (Stan, PyMC), knowledge graph embeddings, and neural-symbolic systems — but not as "probabilistic databases."

### 4b. Stan/PyMC as Knowledge Representation

Stan and PyMC represent knowledge as **probabilistic generative models**: a joint probability distribution over observed and latent variables, specified declaratively. The model itself is the knowledge.

**What this gives you**:
- **Uncertainty is first-class**: Every parameter has a posterior distribution, not a point estimate. You know *how much* you know.
- **Composable**: Hierarchical models represent structured knowledge (group-level effects, individual variation).
- **Updatable**: New data tightens posteriors (Bayesian updating). Knowledge naturally improves with evidence.
- **Falsifiable**: Posterior predictive checks let you test if the model fits reality. Surprising data forces model revision.

**Where it fails as general KR**:
1. **Requires mathematical modeling**: Writing a Stan model is programming, not knowledge entry. You need to specify likelihood functions, priors, and dependencies. This is orders of magnitude harder than stating facts.
2. **Numeric, not symbolic**: Probabilistic programs represent quantities, not qualitative relationships. "Companies with good management outperform" cannot be naturally expressed.
3. **Computational cost**: Markov Chain Monte Carlo (MCMC) inference scales poorly. Complex models take hours to fit.
4. **No natural language interface**: You cannot query a Stan model in English.

**BetaProbLog** (KU Leuven, AAAI 2022): A probabilistic logic programming language that models epistemic uncertainty (uncertainty about the model itself, not just aleatoric uncertainty in the data). Combines Monte Carlo with knowledge compilation. [SOURCE: https://cdn.aaai.org/ojs/21245/21245-13-25258-1-2-20220628.pdf]

### What Class of Errors Probabilistic Representations Prevent

- **False precision**: Forces you to represent uncertainty, not pretend you know more than you do
- **Base rate neglect**: Bayesian models structurally incorporate priors
- **Ignoring sample size**: Posterior uncertainty naturally reflects data quantity
- **Confirmation bias** (partially): Posterior predictive checks surface model-data mismatch

### What They Don't Prevent

- Wrong model specification (most consequential error, and the hardest to detect)
- Computational intractability for complex models
- Prior sensitivity in small-data regimes
- The "unknown unknowns" — variables you did not include in the model

### Adoptability for Agent Systems

**Low for general use, high for specific calibration tasks.** An agent should not express every claim as a probabilistic program. But for specific calibration problems (confidence scoring, prediction tracking, base rate estimation), probabilistic programming is the correct tool. The key practical pattern: agent makes claims with confidence estimates; over time, these are compared to outcomes; a probabilistic model calibrates the agent's confidence mapping. This is exactly what prediction markets and calibration measurement do.

---

## 5. Type-Theoretic Knowledge

### Dependent Types and the Curry-Howard Correspondence

The **Curry-Howard correspondence** establishes an isomorphism between proofs and programs: a proof of proposition P is a program of type P. In dependent type theory (Lean, Coq, Agda, Idris), types can depend on values, allowing propositions like "for all n, there exists a prime greater than n" to be expressed as types, and their proofs as programs.

**Can this extend beyond mathematics?**

Martin-Lof's type theory (1987) distinguishes:
- **Proposition**: A statement that can be judged true or false
- **Judgement**: An act of knowing (evidence-based)
- **Proof**: A witness to the truth of a proposition

His key insight: in intuitionistic logic, proof is primary, not truth. You do not assert "P is true"; you provide "a proof of P." Knowledge is constructive — to know X is to have a method for verifying X. [SOURCE: https://archive-pml.github.io/martin-lof/pdfs/Truth-of-a-Proposition-Evidence-of-a-Judgment-1987.pdf]

**Domanov (2024)** argues that Martin-Lof's type theory sits between phenomenology (Husserl) and analytic philosophy (Frege/Russell). The theory is "interpreted from the very beginning" — unlike classical logic which separates syntax from semantics, type theory makes them inseparable. [SOURCE: https://dspace.spbu.ru/items/3da7a08e-762f-439c-862b-5aa29e9dfcd0]

**Artemov & Protopopescu (2016)** develop intuitionistic epistemic logic where knowledge = verified proposition. The factivity of knowledge (if you know P, then P is true) becomes `KP -> not-not-P` ("known propositions cannot be false") rather than the classical `KP -> P`. This is a constructive, weaker requirement. [SOURCE: https://arxiv.org/pdf/1406.1582]

**Current state of extending beyond math**:
- **Yang et al. (CACM, Feb 2026)**: Comprehensive survey of formal mathematical reasoning. Lean 4, Coq, and Isabelle are increasingly used with LLMs for automated theorem proving. Key applications: verified code generation, hardware verification. Extension to empirical claims is listed as an *open challenge*, not an achieved result. [SOURCE: https://cacm.acm.org/research/formal-reasoning-meets-llms-toward-ai-for-mathematics-and-verification/]
- **Kogkalidis et al. (NeurIPS 2024)**: First dataset of Agda program-proofs with sub-type-level resolution. Machine learning for premise selection in proof assistants. [SOURCE: NeurIPS 2024]
- **FormalJudge (Zhou et al., Feb 2026)**: Uses Dafny specifications and Z3 SMT solving to verify agent behavior. 16.6% improvement over LLM-as-Judge baselines. A 7B model judge achieves >90% accuracy detecting deception from 72B agents. This is the closest existing work to applying formal verification to agent knowledge. [SOURCE: https://arxiv.org/html/2602.11136v1]
- **VERUS-LM (Callewaert et al., 2025)**: Framework combining LLMs with symbolic solvers. LLMs translate text to logical representations; solvers verify consistency. [SOURCE: https://arxiv.org/html/2501.14540v2]
- **ICML 2025 position paper**: "Trustworthy AI Agents Require the Integration of Large Language Models and Formal Methods." [SOURCE: https://icml.cc/virtual/2025/poster/40101]

### The "Proofs = Verified Claims" Analog

The Curry-Howard correspondence for empirical claims would require:
- A "type" for each claim (e.g., `CYC_has_30M_assertions`)
- A "proof" that inhabits the type (evidence that makes the claim true)
- A type checker that verifies the proof is valid

**This is philosophically coherent but practically impossible for most empirical claims.** The problem:
- Mathematical proofs are deterministic and verifiable by computation. Empirical evidence is probabilistic, defeasible, and context-dependent.
- The "type" of an empirical claim is inherently open-ended (what constitutes sufficient evidence for "smoking causes cancer"?).
- Formalizing the claim is as hard as formalizing common sense (the CYC problem again).

**Where it DOES work**: Claims that can be reduced to computation or database lookup.
- "CYC has >25M assertions" = verified by querying the database
- "This function terminates for all inputs" = verified by formal proof
- "The P/E ratio of AAPL is >20" = verified by computable expression

These are exactly the Wolfram-style computable claims. Dependent types add nothing beyond what computable expressions already give for these cases. For genuinely empirical claims ("this drug reduces mortality"), the gap between evidence and proof is irreducible.

### What Class of Errors Type-Theoretic Representations Prevent

- **Logical inconsistency**: Type checking catches contradictions mechanically
- **Incomplete proofs**: A proof with a gap does not typecheck
- **Type errors**: Cannot confuse different kinds of evidence (statistical with anecdotal)
- **Unjustified conclusions**: Every conclusion requires a proof term (evidence chain)

### What They Don't Prevent

- Wrong axioms (garbage axioms produce valid but meaningless proofs)
- Empirical errors (the real world is not a type system)
- Formalization errors (translating natural language to types introduces errors)
- Incompleteness (Godel's theorem: for sufficiently powerful systems, there are true statements without proofs)

### Adoptability for Agent Systems

**Very low for general knowledge, moderate for specific verification tasks.** An agent cannot formalize every claim as a dependent type. But the *idea* — that knowledge should carry its evidence chain, and the evidence chain should be mechanically verifiable — is directly applicable. The practical extract: claims should have explicit evidence chains that can be checked for logical validity (even if the evidence itself cannot be verified mechanically). FormalJudge demonstrates this is already happening for agent safety verification.

---

## Synthesis: What Each Paradigm Contributes to Agent Knowledge Systems

### Error Prevention Matrix

| Error Type | Wolfram | OWL | Toulmin | Probabilistic | Type-Theoretic |
|---|---|---|---|---|---|
| **Unit/type inconsistency** | STRONG | MODERATE | NONE | NONE | STRONG |
| **Unsupported claims** | N/A (no claims) | NONE | STRONG | NONE | STRONG |
| **Missing uncertainty** | NONE | NONE | MODERATE (qualifier) | STRONG | NONE |
| **Hidden counterevidence** | NONE | NONE | STRONG (rebuttal) | MODERATE (model comparison) | NONE |
| **Stale knowledge** | MODERATE (computed) | NONE | NONE | MODERATE (updating) | NONE |
| **Factual errors** | NONE | NONE | NONE | NONE | NONE |
| **Taxonomic inconsistency** | NONE | STRONG | NONE | NONE | MODERATE |
| **False precision** | NONE | NONE | MODERATE | STRONG | NONE |
| **Circular reasoning** | N/A | NONE | MODERATE (Dung) | N/A | STRONG |

No single paradigm prevents factual errors (wrong facts within valid types). This is the irreducible hard problem.

### Practical Recommendations for an Agent Knowledge System

**Layer 1 — Structural (cheapest to enforce, highest ROI)**:
- Wolfram-style **typed entities with units** for quantitative claims. Catches unit errors, type errors, ambiguous references.
- OWL-style **domain/range constraints** on entity properties. Catches structural nonsense (price attached to a person).
- These are *pre-flight checks* — they catch errors before claims enter the system.

**Layer 2 — Epistemic (moderate cost, high value)**:
- Toulmin-style **structured claims**: `{claim, grounds, warrant, qualifier, rebuttal}`. Makes evidence, reasoning, uncertainty, and defeat conditions structurally mandatory.
- Wikidata-style **provenance**: Every claim carries its source, recency, and quality assessment.
- This is the *knowledge format* — what a claim looks like when stored.

**Layer 3 — Dynamic (expensive, selective use)**:
- Bayesian **calibration** for confidence scores. Agent's probability estimates are compared to outcomes over time.
- Dung-style **attack graphs** for contested claims. When two claims conflict, represent the conflict explicitly and compute acceptable sets.
- This is *knowledge maintenance* — applied selectively to high-stakes or contested claims.

**Layer 4 — Verification (very expensive, narrow application)**:
- FormalJudge-style **SMT verification** for safety-critical claims.
- Type-theoretic proof chains for logically complex reasoning.
- Applied only when the cost of error justifies the cost of verification.

### What NOT to Build

1. **Do not build CYC.** Manual formalization of world knowledge does not scale. Let LLMs handle common sense; use structure for enforcing rigor on specific claims. [INFERENCE from CYC post-mortem]
2. **Do not require full Wigmore charts.** The formalization tax kills adoption. Extract the useful parts (inferential direction, evidential weight) without requiring complete formal structure.
3. **Do not try to make everything probabilistic.** Probabilistic representation is powerful but expensive. Most agent claims are better served by simple confidence qualifiers (Toulmin-style) than full posterior distributions.
4. **Do not try to prove empirical claims formally.** The gap between evidence and proof is irreducible for empirical claims. Use formal methods for logical consistency checks, not for establishing truth.

### The Key Insight Across All Paradigms

Every paradigm that succeeds in practice **makes specific epistemic metadata structurally required** rather than optionally included:
- Wolfram: units are mandatory, not optional
- OWL: types are checked, not advisory
- Toulmin: rebuttal is a structural slot, not an afterthought
- Bayesian: uncertainty is the output, not an annotation
- Dependent types: proof is required, not assumed

The pattern: **if rigor is optional, it will not happen**. The agent system analog: if provenance, confidence, and defeat conditions are optional fields, agents will skip them. Make them structurally required in the claim format, and rigor follows from architecture.

---

## Search Log

| Query | Tool | Result |
|---|---|---|
| Wolfram Alpha architecture | Exa | 5 hits, Theodore Gray blog post most useful |
| Wolfram Alpha critique limitations | Exa | 5 hits, Joel Spolsky 2009, Ernest Davis AMS 2024 |
| Wolfram ruliad critique | Exa | 5 hits, Wolfram Institute survey, Pittsburgh PhilSci |
| CYC retrospective lessons | Exa | 5 hits, Yuxi Liu 2025 (best), Gary Marcus 2023 |
| Lenat Marcus trustworthy AI | S2 | 1 hit, arXiv:2308.04445 |
| OWL consistency limits | Exa | 5 hits, OWL 2 profiles, GLaMoR, W3C spec |
| Wikidata provenance contradictions | Exa | 5 hits, Piscopo 2017, Yadav 2023 |
| KG limitations criticism | Exa | 5 hits, ontology drift, semantic web failure discussion |
| Dung argumentation practical | Exa | 5 hits, Dung-O-Matic, Carneades, COMMA |
| Argumentation software Toulmin IBIS | Exa | 5 hits, Pacisco, gIBIS, Buckingham Shum retrospective |
| Wigmore chart practical | Exa | 4 hits, Leclerc 2022 (empirical study), Goodwin |
| Probabilistic databases MayBMS | Exa | 5 hits, MayBMS site, Oxford project page, survey |
| Dependent types beyond math | Exa | 5 hits, NeurIPS 2024, Yang CACM 2026 |
| Martin-Lof type theory belief | Exa | 4 hits, original 1987 paper, Domanov 2024, Artemov 2016 |
| LLM agent formal verification | Exa | 5 hits, FormalJudge 2026, VERUS-LM, ICML position |
| Argumentation framework LLM | S2 | 5 hits, AKReF, SymAgent |
| CYC 30M/$200M claim | verify_claim | VERIFIED |
| MayBMS discontinued | verify_claim | SUPPORTED (confidence 0.8) |

## Sources Saved

- Lenat & Marcus 2023, "Getting from Generative AI to Trustworthy AI" (arXiv:2308.04445) — saved to corpus

## Disconfirmation Summary

- **Wolfram**: Searched "Wolfram Alpha fails", "formalization boundaries." Found Joel Spolsky critique (2009) and Ernest Davis (AMS 2024). Both confirm fundamental limits on computable knowledge.
- **CYC**: Searched "CYC failure", "CYC retrospective." Found Yuxi Liu's 2025 archival analysis. Confirms failure to bootstrap despite 40 years of manual encoding.
- **Ontologies**: Searched "semantic web failed", "knowledge graph limitations", "ontology drift." Found multiple critiques confirming that logical consistency does not equal factual correctness.
- **Argumentation**: Searched for practical adoption evidence. Found Leclerc 2022 (judges don't use Wigmore charts), Buckingham Shum 2006 (IBIS formalization tax). Confirms that formal argumentation is powerful but underadopted due to cognitive overhead.
- **Probabilistic DBs**: Searched for current status. Confirmed MayBMS/Trio effectively defunct. Theoretical results (dichotomy theorem) explain why — exact query evaluation is intractable for most useful queries.
- **Type theory**: Searched "formal verification empirical claims." Found Yang et al. CACM 2026 listing this as an open challenge. Confirms the gap between formal proof and empirical evidence is unresolved.

<!-- knowledge-index
generated: 2026-03-22T00:15:44Z
hash: e2f518f5996c

title: Knowledge Representation Paradigms for Agent Knowledge Systems
sources: 3
  INFERENCE: from architectural analysis
  TRAINING-DATA: , verified name exists
  INFERENCE: from CYC post-mortem
table_claims: 1

end-knowledge-index -->
