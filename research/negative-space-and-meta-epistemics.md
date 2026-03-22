---
title: Negative Space and Meta-Epistemics for Agent Knowledge Systems
date: 2026-03-02
---

# Negative Space and Meta-Epistemics for Agent Knowledge Systems

**Date:** 2026-03-02
**Tier:** Deep
**Question:** What frameworks exist for detecting wrong questions, structural blindness, and for validating that a knowledge system actually works? Extract structural lessons for agent design.

---

## Ground Truth

Existing corpus covers: Popper/Frankfurt/Bratman philosophical foundations (`philosophy-of-epistemic-agents.md`), FActScore/SAFE/VeriScore factual verification, calibration measurement, temporal degradation, sycophancy. No prior work in this corpus on presupposition analysis, ignorance taxonomies, pertinent negatives, via negativa, replication crisis reforms, error archaeology systems, or Goodhart's law in knowledge systems.

---

# TOPIC 1: Negative Space — Detecting Wrong Questions and Structural Blindness

## 1a. Presupposition Analysis

### The Formal Framework

Presuppositions are propositions taken for granted when a sentence is uttered, as opposed to the main propositional content. The canonical example: "Have you stopped beating your wife?" presupposes that you were beating your wife. [SOURCE: SEP, plato.stanford.edu/entries/presupposition/]

Three generations of theory:

1. **Frege-Strawson semantic model.** Strawson (1950): If a presupposition is false, the sentence is neither true nor false — it suffers "presupposition failure." The statement "The present King of France is bald" doesn't have a truth value because there is no present King of France. [TRAINING-DATA, verified against SEP entry]

2. **Stalnaker's pragmatic model.** Presuppositions are requirements on the "common ground" — the set of propositions mutually accepted by conversational participants. A presupposition failure occurs when the speaker assumes something in the common ground that isn't actually there. [SOURCE: SEP, plato.stanford.edu/entries/presupposition/]

3. **Dynamic semantics.** Heim, Karttunen: presuppositions are update conditions on context sets. A statement can only be felicitously processed in a context that already entails its presuppositions. [SOURCE: SEP]

**Presupposition triggers** (a large, known class): definite descriptions ("the X"), factive verbs ("realizes that", "knows that"), change-of-state verbs ("stopped", "began"), cleft constructions ("It was X who..."), iteratives ("again", "another"). [SOURCE: SEP]

**Key insight — accommodation:** When a presupposition isn't in the common ground, listeners often silently "accommodate" it — accepting the presupposition without challenge. This is precisely the failure mode for agent research questions. The agent asks "What is the optimal dosing adjustment for CYP2D6 poor metabolizers?" which presupposes that a dosing adjustment exists and is optimal. If no CPIC guideline exists, the agent has accommodated a false presupposition.

### Computational Operationalization — Two Key Papers

**Wang & Blanco (EMNLP 2025):** "Identifying and Answering Questions with False Assumptions." Decomposes questions into atomic assumptions, validates each against retrieved evidence. Five LLMs tested; incorporating evidence + atomic assumption validation yields best results. Key finding: the problem does NOT reduce to simple fact verification — you need the decomposition step. [SOURCE: aclanthology.org/2025.emnlp-main.1228.pdf]

**Roy Dipta & Ferraro (arXiv:2508.16838):** "If We May De-Presuppose: Robustly Verifying Claims through Presupposition-Free Question Decomposition." Proposes a structured framework that decomposes claims into presupposition-free questions before verification. Achieves 2-5% improvement over baselines. Key contribution: shows that presuppositions in generated verification questions introduce unverified assumptions, and that even SOTA models remain susceptible (3-6% performance variance from prompt sensitivity alone). Code: github.com/dipta007/De-Presuppose [SOURCE: arxiv.org/html/2508.16838v1]

**Yablo (MIT):** "Non-Catastrophic Presupposition Failure" argues that presupposition failure is often non-catastrophic — the sentence still conveys useful information even when the presupposition is false. This is the harder case for agents: the question has a partially useful answer but its framing embeds a false assumption. [SOURCE: mit.edu/~yablo/ncpf.pdf]

### Structural Lesson for Agents

**ADOPTABLE.** Before pursuing a research question, decompose it into atomic presuppositions and validate each independently. This is directly implementable:
1. Extract presupposition triggers from the question (definite descriptions, factives, change-of-state verbs)
2. Generate the presupposed propositions
3. Verify each against available evidence before proceeding with the main question
4. If a presupposition fails, reformulate the question

This maps to the researcher skill's Phase 3 (hypothesis formation) but applies one step earlier — to the question itself. The Wang & Blanco approach (atomic assumption decomposition + evidence retrieval) is the most directly applicable method.

---

## 1b. Second-Order Ignorance

### Smithson's Taxonomy of Ignorance (1989)

Smithson divides ignorance into two top-level branches: [SOURCE: i2insights.org/2022/06/28/ignorance-taxonomy/, Smithson's own summary]

**1. Irrelevance** (active-voice: things we choose to ignore)
- **Untopicality** — things we feel we don't need to know
- **Taboo** — things forbidden to know (classified information, privacy)
- **Undecidability** — matters that in principle cannot be determined true/false (liar's paradox)

**2. Error** (passive-voice: properties of our state of knowledge)
- **Distortion:**
  - *Confusion* — mistaking one thing for another
  - *Inaccuracy* — mis-estimating something
- **Incompleteness:**
  - *Uncertainty:* probability, ambiguity, vagueness
  - *Absence* — simply not having knowledge

**Later amendments** (Smithson, post-1989):
- **Conflictive uncertainty** — disagreements among experts. People treat this as worse than other unknowns. [SOURCE: ibid.]
- **Matthias Gross (2007)** added "nonknowledge" (reducible ignorance) vs "negative knowledge" (Knorr-Cetina 1999: knowledge about what we CANNOT know). [SOURCE: ibid.]
- **Nescience** = meta-ignorance = unknown unknowns. Once you become aware of nescience, it becomes ignorance or nonknowledge. [SOURCE: ibid., referencing Kerwin 1993]

**Firestein (2012):** "The main business of scientific research is improving our ignorance." New knowledge generates new questions — more ignorance. [SOURCE: cited in Smithson's overview]

### The Rumsfeld Formulation and Decision Science

The known-knowns/known-unknowns/unknown-unknowns matrix maps to Smithson as follows:
- Known knowns = knowledge (outside Smithson's taxonomy)
- Known unknowns = Incompleteness (uncertainty + absence)
- Unknown unknowns = Nescience / meta-ignorance
- Unknown knowns = Irrelevance (untopicality, taboo) — things we know but don't realize we know, or choose to ignore

### Techniques for Mapping Unknown Unknowns

**Reference class forecasting** (Kahneman & Tversky): Instead of asking "what will happen in THIS project?" (inside view), ask "what happened in similar projects?" (outside view). Directly addresses the planning fallacy. Implementation: identify reference class, obtain base rate statistics, adjust for specifics. [SOURCE: Wikipedia/reference_class_forecasting; McKinsey interview with Kahneman, 2011]

**Pre-mortem analysis** (Klein, 1998): Before starting, imagine the project has failed. Ask: "What went wrong?" This reversal makes unknown unknowns psychologically accessible by working backward from failure. [TRAINING-DATA, well-established]

**Red teaming:** Assign a dedicated adversary to find flaws. Structural, not optional. The key is dedicated role assignment — the red team's JOB is to find problems, which overcomes the social pressure toward agreement. [TRAINING-DATA]

### Structural Lesson for Agents

**ADOPTABLE.** Three mechanisms map directly to agent design:

1. **Ignorance audit.** Before research, explicitly categorize what you know using Smithson's taxonomy. Force the agent to populate each category. Empty categories are informative — if you have zero entries under "Confusion" (mistaking one thing for another), you probably haven't checked for category errors.

2. **Reference class check.** For any prediction or estimate, search for the reference class before generating your own estimate. "What happened when other agents/analysts tried to answer questions like this?" The correction is typically 2-3x on time/cost estimates. [SOURCE: Kahneman]

3. **Pre-mortem on research questions.** Before starting deep research, answer: "If this research fails, what's the most likely reason?" This surfaces presupposition failures, scope problems, and data availability issues before effort is invested.

---

## 1c. Pertinent Negatives and Signal Absence

### Medical Pertinent Negatives

In clinical reasoning, a "pertinent negative" is the absence of an expected finding that narrows the differential diagnosis. Example: chest pain WITHOUT radiation to the arm, WITHOUT diaphoresis, WITHOUT shortness of breath — these absences argue against myocardial infarction. The pertinent negative is documented as part of the clinical assessment precisely because its absence is diagnostic. [TRAINING-DATA, confirmed by medical literature search]

### The Dog That Didn't Bark

In intelligence analysis and legal reasoning, the absence of an expected event serves as evidence. Holmes deduced the identity of the criminal because the watchdog did NOT bark — implying the intruder was known to the dog. [SOURCE: brieflywriting.com/2012/07/25/the-dog-that-didnt-bark]

**Formalization: Hsu, Horng, Griffiths & Chater (Cognitive Science, 2016).** "When Absence of Evidence Is Evidence of Absence." Bayesian model for reasoning from absent data. Key findings: [SOURCE: cocosci.princeton.edu/papers/absentData.pdf]

- People DO reason from absence, and their reasoning follows Bayesian predictions
- The informativeness of an absence depends on the base rate: if something is usually present and is absent, that's much more informative than the absence of something rare
- Formally: P(no mines | 10 digs, surrounding density q) follows a posterior that increases with q — higher base rate makes absence more surprising and more diagnostic
- Correlation between human judgments and Bayesian model: r = 0.897 (Exp 1), r = 0.95 (Exp 2)
- People show conservatism — slightly less confident in absence than the Bayesian model predicts

### Signal Detection Theory

SDT (from radar, 1950s) provides the formal framework for absence reasoning. Every detection decision involves four outcomes: hit (correctly detect signal), miss (fail to detect signal), false alarm (detect signal when none exists), correct rejection (correctly identify no signal). The "correct rejection" IS the pertinent negative — correctly identifying that something is absent. SDT quantifies this through d' (sensitivity) and criterion placement. [TRAINING-DATA, verified against Wixted 2019 history of SDT]

The key insight from SDT: a rational detector's ability to notice absence depends on their model of what SHOULD be present. Without a strong prior model of expected signals, absence is invisible. This is why checklist-based clinical reasoning works — the checklist provides the "expected signal" model that makes absence noticeable.

### Structural Lesson for Agents

**ADOPTABLE.** Three mechanisms:

1. **Expected-findings checklist.** Before starting investigation, generate a list of what you EXPECT to find. After research, explicitly check which expected findings are absent. The absent findings are potentially the most informative. This is the clinical pertinent negative applied to research.

2. **Base-rate calibrated absence.** Per Hsu et al., an absence is informative in proportion to the base rate of the expected finding. "No SEC enforcement action" for a Fortune 500 company is uninformative (base rate of enforcement is low). "No SEC enforcement action" for a company with three restatements in five years IS informative.

3. **SDT framing for search.** Before evaluating search results, set the signal model: what would you expect to see if your hypothesis were true? What would you expect to see if it were false? This turns passive browsing into active detection with explicit criteria for hits, misses, false alarms, and correct rejections.

---

## 1d. Apophatic Epistemology / Via Negativa

### Taleb's Formulation

"The greatest — and most robust — contribution to knowledge consists in removing what we think is wrong — subtractive epistemology." (Antifragile, 2012) [SOURCE: grahammann.net/book-notes/antifragile-nassim-nicholas-taleb, multiple secondary sources]

Core claims:
- **Negative knowledge is more robust than positive knowledge.** We can be more confident that "X doesn't work" than "X works" because a single disconfirmation is often decisive while confirmation requires exhaustive testing. [TRAINING-DATA + secondary sources]
- **Via negativa in action means subtraction.** Don't eat processed food (vs. add supplements). Don't do stupid things (vs. seek brilliance). Remove bad options rather than optimizing among mediocre ones.
- **The barbell strategy** combines extremely safe + extremely risky, avoiding the middle — another form of via negativa (eliminate the mediocre middle).

### Formal Representation

"We know X is NOT the case" vs "We don't know X" — these are formally distinct:
- ¬X (we know not-X) has positive epistemic content — it eliminates possibilities
- ¬K(X) (we don't know X) is an epistemic state — it says nothing about X itself

This maps to Smithson: ¬X reduces the space of Error/Incompleteness by adding knowledge. ¬K(X) IS the Error/Incompleteness state.

In Popperian terms: falsification (¬X) is the engine of scientific progress precisely because it is asymmetric — one counterexample refutes a universal claim, but no finite number of positive examples can confirm it. [TRAINING-DATA, verified against existing philosophy-of-epistemic-agents.md]

### Structural Lesson for Agents

**ADOPTABLE.** Via negativa translates directly to three agent design principles:

1. **Disconfirmation-first research.** Already in the researcher skill (Phase 4). But the via negativa perspective strengthens it: the most valuable output of research is WHAT WAS RULED OUT, not what was found. The disconfirmation results section should be weighted equally to the findings section.

2. **Subtractive knowledge in MEMORY.md.** "X is NOT true" entries are more durable than "X is true" entries. Record failed hypotheses, dead ends, and ruled-out approaches with the same care as positive findings. They don't become stale the way positive findings do (a ruled-out approach stays ruled out).

3. **Kill criteria before investigate.** Before pursuing any complex question, specify what would make you stop. This is via negativa applied to research planning — removing waste by specifying what would make the work worthless.

---

## 1e. Question Refinement as Epistemic Progress

### Bachelard's Epistemological Obstacles

Gaston Bachelard (1938, "The Formation of the Scientific Mind") argued that the chief obstacles to scientific progress are not empirical but epistemological — existing knowledge prevents the acquisition of new knowledge. The obstacle is not ignorance but previous successful knowledge that has become calcified. [SOURCE: Multiple secondary sources: O'Donohue et al. 1998 in Behavior Analyst (PMC2731408); Souza et al. 2023 in Acta Scientiae]

Key obstacle types:
- **First experience obstacle:** Over-reliance on concrete, everyday experience as the basis for scientific understanding
- **Verbal obstacle:** Using familiar words that carry misleading connotations
- **Substantialist obstacle:** Attributing hidden substances or essences as explanations
- **Knowledge generalization obstacle:** Premature overgeneralization from limited cases

The core insight: **your previous successful framework is the obstacle.** You solved a problem using Framework A, so you try to apply Framework A to everything. The breakthrough requires breaking with Framework A, which feels like abandoning proven knowledge.

### Laudan's Problem-Solving Effectiveness

Larry Laudan (1977, "Progress and its Problems"): The measure of a research program's progress is its problem-solving effectiveness — the ratio of solved problems to generated anomalies. A degenerative research program generates more anomalies than it solves. [TRAINING-DATA]

This provides a formal criterion for question quality: a good question is one whose answer increases the net problem-solving effectiveness of the knowledge system. A bad question is one whose answer creates more confusion than it resolves.

### Boguslav et al. (2023): "Creating an Ignorance-Base"

This paper (J Biomed Inform, DOI:10.1016/j.jbi.2023.104405) proposes computationally identifying "known unknowns" in scientific literature — statements of ignorance in published papers. They annotate scientific text for explicit statements of what is NOT known. This is the closest thing to a computational "question quality" detector — it identifies gaps in knowledge by mining the literature for explicit ignorance statements. [SOURCE: pmc.ncbi.nlm.nih.gov/articles/PMC10528083/]

### Structural Lesson for Agents

**PARTIALLY ADOPTABLE.** Two mechanisms:

1. **Epistemological obstacle detection.** When an agent's research keeps returning to the same framework or methodology, flag it. "You've used the same search strategy 3 times with diminishing returns — is the framework itself the obstacle?" This maps to the researcher skill's diminishing returns gate but adds a metacognitive check.

2. **Question quality metric.** After research, assess: did the question's answer increase net problem-solving effectiveness? If answering the question created more new questions than it resolved, the original question may have been poorly formed. This is Laudan's criterion applied retroactively. No formal computational measure exists — this remains judgment-dependent.

3. **Ignorance mining.** The Boguslav approach of mining literature for explicit ignorance statements could be applied to agent outputs: scan the agent's research memos for phrases like "remains unknown," "no evidence exists," "further research needed" and aggregate them into an explicit ignorance inventory. This is computationally trivial.

---

# TOPIC 2: Meta-Epistemics — How Do You Know Your Knowledge System Works?

## 2a. The Replication Crisis as Case Study

### The Numbers

**Open Science Collaboration (2015, Science).** 270 psychologists replicated 100 studies from three psychology journals (2008 publications). Results: [SOURCE: osf.io/ezum7/; bps.org.uk]

| Metric | Original | Replication |
|--------|----------|-------------|
| Statistically significant results | 97% | 36% |
| Mean effect size | 100% of original | 50% of original (half the magnitude) |
| Original effect size within replication 95% CI | — | 47% |
| Subjectively rated as replicated | — | 39% |

This is the landmark paper. The 97% -> 36% drop is the single most important number in the replication crisis.

### Structural Reforms and Their Measured Impact

**1. Pre-registration**

**Brodeur, Cook, Hartley & Heyes (2024, Journal of Political Economy: Microeconomics).** Analyzed 15,992 test statistics from RCTs in 15 leading economics journals. Key findings: [SOURCE: static1.squarespace.com/.../BrodeurCookHartleyHeyes+2024+JPEMicro.pdf]

- **Pre-registration alone does NOT reduce p-hacking or publication bias.** It frequently lacks sufficient detail to constrain researcher decisions.
- **Pre-registration WITH a pre-analysis plan (PAP) DOES reduce both p-hacking and publication bias.** The plan must be detailed enough to constrain post-data decisions.
- The mechanism matters: vague pre-registration is performative; detailed PAPs are structural.

**2. Registered Reports**

**Scheel, Schijen & Lakens (2021, Advances in Methods and Practices in Psychological Science).** Compared 71 Registered Reports with 152 standard psychology papers. Results: [SOURCE: doi.org/10.1177/25152459211007467]

| Metric | Standard reports | Registered Reports |
|--------|-----------------|-------------------|
| Positive results (first hypothesis) | **96%** | **44%** |

This is a 52 percentage point difference. The 96% positive rate in standard reports is essentially impossible under realistic power levels — it reflects publication bias and p-hacking. The 44% rate in Registered Reports is much more consistent with what you'd expect from well-powered studies testing genuine hypotheses. [INFERENCE from the numbers]

**Chambers & Tzavella (2021, Nature Human Behaviour).** "The past, present and future of Registered Reports." Report that RRs are working as intended: reducing publication bias, increasing methodological rigor, and producing more null results (which are informative, not failures). [SOURCE: doi.org/10.1038/s41562-021-01193-7]

**Korbmacher et al. (2023, Communications Psychology).** "The replication crisis has led to positive structural, procedural, and community changes." Frame the crisis as a "credibility revolution" and document structural changes: open data mandates, pre-registration infrastructure (OSF), Registered Reports at 300+ journals, adversarial collaborations. [SOURCE: nature.com/articles/s44271-023-00003-2.pdf]

### Structural Lessons for Agents

**ADOPTABLE.** The replication crisis provides the single best case study for agent knowledge system design:

1. **Pre-registration = pre-mortem + hypothesis specification.** The researcher skill already requires Phase 3 (hypothesis formation with falsification criteria). The lesson from Brodeur et al. is that this only works if the pre-registration is DETAILED. Vague hypotheses are performative — they don't constrain the space of acceptable conclusions.

2. **The 96% -> 44% drop is the key metric.** If your knowledge system produces 96% "positive" (confirmatory) results, it's broken. A healthy system should produce ~40-60% confirmatory results depending on the domain. Monitor the confirmation rate as a system health metric.

3. **Structural reform > cultural reform.** Pre-registration without PAPs didn't work (Brodeur). Registered Reports (structural change to publication process) DID work (Scheel). This is constitutional principle #1: "Architecture over instructions."

---

## 2b. Closed-Loop Prediction Systems

### Why Weather Forecasting Is Well-Calibrated

Weather forecasting is the gold standard for calibrated prediction. Structural features that produce calibration: [TRAINING-DATA, verified against ECMWF/WMO verification resources]

1. **Rapid, unambiguous feedback.** The forecast resolves within hours to days. You said "40% chance of rain" — either it rained or it didn't. No interpretation needed.

2. **Repeated practice on similar problems.** Forecasters make thousands of forecasts per year on structurally similar questions. This enables statistical learning from feedback.

3. **Quantitative scoring.** Brier scores, reliability diagrams, ROC curves are standard. The forecaster's calibration is numerically measured, not subjectively assessed.

4. **No incentive to be wrong in a specific direction.** Unlike financial analysts (incentivized to be bullish) or doctors (incentivized toward defensive medicine), weather forecasters face symmetric loss functions.

5. **Ensemble methods.** Modern forecasting uses multiple models and probabilistic outputs, not point predictions. This forces the forecaster to think in distributions.

6. **Institutional verification culture.** ECMWF, NWS, and other organizations maintain continuous verification programs. Murphy (1993) defined forecast "goodness" along three dimensions: consistency (forecasts match beliefs), quality (beliefs match observations), value (decisions improve outcomes). [SOURCE: Ben-Bouallègue 2025, arxiv.org/pdf/2602.00622]

### Tetlock's Findings

**Good Judgment Project (IARPA ACE tournament, 2011-2015).** Key results: [SOURCE: Wikipedia/Good_Judgment_Project; verified via mcp__research__verify_claim]

- Superforecasters beat all competing research teams by 35-72%
- Superforecasters achieved Brier scores ~0.14-0.16 vs intelligence analysts ~0.30-0.37
- Top 2% of forecasters ("superforecasters") were "reportedly 30% better than intelligence officers with access to actual classified information"
- Forecasting skill is trainable: basic tutorials improved performance significantly

**What predicts forecasting accuracy (Tetlock):** [TRAINING-DATA, widely confirmed]
- **Foxes > hedgehogs.** Forecasters who synthesize many small pieces of information outperform those who have one big theory.
- **Granular updating.** The best forecasters update in small increments based on new evidence, rather than making big jumps.
- **Active open-mindedness.** Willingness to consider alternatives and revise beliefs.
- **Dragonfly eye perspective.** Synthesizing information from many angles rather than one viewpoint.

### What Distinguishes Calibrated from Uncalibrated Domains

| Feature | Calibrated (weather, poker) | Uncalibrated (geopolitics, medicine) |
|---------|-----------------------------|--------------------------------------|
| Feedback speed | Hours to days | Months to years |
| Feedback clarity | Unambiguous outcome | Ambiguous, multi-causal |
| Repetition | Thousands of similar decisions | Few similar cases |
| Scoring | Quantitative, continuous | Qualitative or absent |
| Incentives | Symmetric | Asymmetric |
| Base rates | Well-estimated | Poorly estimated or absent |

### Structural Lessons for Agents

**ADOPTABLE.** Weather forecasting's calibration comes from five structural features that can be engineered:

1. **Fast, unambiguous feedback loops.** For agent predictions, create the shortest possible path from prediction to resolution. The intel prediction tracker already does this — but the key insight is that speed matters more than volume.

2. **Quantitative scoring.** Brier scores for every prediction, tracked over time. Already in the system design (calibration measurement memo).

3. **Granular updating over big jumps.** Enforce small incremental updates to beliefs rather than wholesale revisions. This maps to the temporal degradation finding that incremental delta updates prevent context collapse.

4. **Foxes, not hedgehogs.** Architecturally, this means multi-source research (the researcher skill's multiple axes) and cross-model review (different models = different theoretical frameworks). Single-model, single-framework analysis is hedgehog analysis.

5. **Symmetric incentives.** The agent should not be rewarded for positive findings more than negative ones. This connects directly to the Registered Reports lesson — monitor the confirmation rate.

---

## 2c. Error Archaeology Systems

### ASRS (Aviation Safety Reporting System)

Established 1976. NASA administers, FAA funds. Over 558,000 reports processed by 2001; now the world's largest confidential voluntary aviation reporting system. [SOURCE: asrs.arc.nasa.gov/docs/rs/60_Case_for_Confidential_Incident_Reporting.pdf; boltflight.com ASRS article]

**Why it works — five structural features:**

1. **Confidentiality, not anonymity.** NASA receives identifying information (needed for follow-up clarification) but de-identifies before analysis. Reporters trust NASA because NASA has no enforcement role.

2. **Separation of analysis from enforcement.** NASA analyzes; FAA enforces. This was a deliberate design choice — FAA recognized that its enforcement role would poison reporting if it ran the system. The "honest broker" third party is essential.

3. **Limited immunity.** Filing an ASRS report provides limited protection from FAA enforcement actions (if report filed within 10 days, violation was inadvertent, and no criminal activity). This creates a positive incentive to report.

4. **Alert messages.** When ASRS identifies an immediate safety concern, it issues an alert message to relevant authorities. This creates visible value — reporters see their reports leading to changes.

5. **No punishment for honest error.** The system explicitly distinguishes between honest mistakes and willful violations. Only honest mistakes are protected. This prevents the system from becoming a shield for bad actors.

**Scale evidence:** 2,500+ alert messages issued since inception. Tens of thousands of users across all aviation sectors. [SOURCE: asrs.arc.nasa.gov/docs/ASRS_ProgramBriefing.pdf]

### FMEA (Failure Mode and Effects Analysis)

Originated 1940s (MIL-STD-1629). Systematic identification of failure modes, their effects, and their causes. Each failure mode gets a Risk Priority Number (RPN) = Severity x Occurrence x Detection. [SOURCE: Multiple secondary sources]

**When FMEA works:**
- Well-defined, bounded systems (automotive components, medical devices, manufacturing processes)
- When the team has domain expertise and diverse perspectives
- When action items from FMEA are actually tracked and implemented
- When FMEA is treated as a living document, updated as new failure modes are discovered

**When FMEA becomes performative:**
- When it's a compliance checkbox (done to satisfy auditors, filed and forgotten)
- When the same team generates failure modes and assesses their severity (groupthink)
- When RPN scoring becomes arbitrary (what's the difference between Severity 7 and Severity 8?)
- When the system is too complex for enumeration (software systems, organizational processes)
- "Static spreadsheet exercise" — the FMEA is done once and never updated [SOURCE: f7i.ai FMEA guide]

### Medical M&M Conferences

Century-old tradition. Evidence on effectiveness: [SOURCE: PMC7813522; PMC10023258; Lekgowe et al. 2023]

- **Murayama et al. (2002):** Survey-based study. After structured reforms to M&M conference, residents perceived significant improvement in 8 of 23 components. No outcome data.
- **Lekgowe et al. (2023):** Princess Marina Hospital, Botswana. Retrospective audit of M&M data 2016-2019. Found correlation between routine M&M conferences and reduced preventable death rate. Small sample, single institution.
- **Churchill et al. (2020, Cureus):** Integrative review. Found M&M conferences are increasingly being restructured for QI and patient safety, but "there is a need for a standardized structure."
- **Batthish et al.:** Multiple-case study found M&MCs CAN produce organizational learning (double-loop learning) when they have a "patient safety culture" with open communication.

**The evidence is weak.** No RCTs. Mostly self-report, single-institution studies. The structural features that predict effectiveness (blame-free culture, systems thinking, action tracking) are well-theorized but poorly measured.

### Structural Lessons for Agents

**ADOPTABLE.** The key structural features that separate effective from performative error-learning systems:

| Feature | Effective | Performative |
|---------|-----------|-------------|
| Analysis separated from punishment | ASRS (NASA analyzes, FAA enforces) | M&M conferences without blame-free culture |
| Incentive to report | ASRS immunity provision | Mandatory reporting without protection |
| Visible impact | ASRS alert messages | FMEA filed and forgotten |
| Living document | Dynamic FMEA, updated with new data | Static spreadsheet, done once |
| Systems focus | M&M with double-loop learning | M&M focused on individual blame |
| External diversity | Red team, independent reviewers | Same team generates and assesses |

For agent knowledge systems:

1. **Separation of error detection from error correction.** The session-analyst (error detection) should be structurally separate from the agent being analyzed (error correction). This is already the case — session-analyst runs post-hoc. ASRS validates this architecture.

2. **Correction register as living FMEA.** The improvement-log IS an FMEA — it identifies failure modes and tracks remediation. The key ASRS lesson is that filing must be incentivized and the register must visibly produce changes (closed-loop feedback).

3. **Alert messages.** When the agent detects a high-severity error pattern (not a one-off), escalate immediately rather than waiting for the next session-analyst cycle. ASRS's 2,500+ alert messages demonstrate the value of real-time escalation.

---

## 2d. Campbell's and Goodhart's Law Applied to Knowledge

### The Laws

**Goodhart (1975):** "Any observed statistical regularity will tend to collapse once pressure is placed upon it for control purposes." Modern paraphrase: "When a measure becomes a target, it ceases to be a good measure." [SOURCE: Manheim 2018/2023, MPRA/Patterns journal]

**Campbell (1979):** "The more any quantitative social indicator is used for social decision-making, the more subject it will be to corruption pressures and the more apt it will be to distort and corrupt the social processes it is intended to monitor." [SOURCE: Manheim 2018]

These are distinct but related: Goodhart describes the statistical collapse of a regularity under control pressure; Campbell describes the social corruption of an indicator under decision-making pressure.

### Concrete Examples in Knowledge/Education Systems

1. **Teaching to the test.** Schools optimize for standardized test scores; actual learning may decline while scores rise. This is Campbell's law in its purest form. [TRAINING-DATA]

2. **Citation count as quality proxy.** Papers are assessed by citation count; researchers optimize for citations (salami-slicing, citation cartels, review articles). Quality and citation count diverge. [TRAINING-DATA]

3. **AI benchmark gaming.** Models are optimized for specific benchmarks (MMLU, HumanEval); real-world performance may not track benchmark scores. The LMSYS Chatbot Arena controversy is a recent example. [SOURCE: blog.collinear.ai, Goodhart's law in AI leaderboard]

4. **h-index as academic quality proxy.** Researchers add self-citations, participate in citation rings, fragment work into minimum publishable units. The metric incentivizes quantity over quality. [TRAINING-DATA]

5. **The 96% positive result rate.** This IS Goodhart's law applied to science: the "measure" (statistical significance) became the "target" (publication criterion), and the measure collapsed (results no longer reflect reality). [INFERENCE from Scheel et al. 2021]

### Manheim's Framework for Less-Flawed Metrics (2018/2023)

David Manheim (Patterns, 2023) provides the most systematic treatment of how to dodge Goodhart and Campbell. Key strategies: [SOURCE: Manheim 2018 MPRA paper + 2023 Patterns journal version]

1. **Diversification.** Use multiple metrics that are hard to simultaneously game. If one metric is corrupted, others still provide signal.

2. **Post-hoc specification.** Don't announce the exact metric in advance. Announce the domain but choose the specific measure after data collection. This prevents targeted gaming.

3. **Randomization.** Randomly select which metric applies to which evaluation. This makes gaming computationally expensive.

4. **Secrecy.** Keep some evaluation criteria hidden. This has obvious trust downsides but prevents optimization against the metric.

5. **Composite metrics.** Combine multiple indicators into a single composite that's harder to game than any individual indicator.

### The Map-Territory Problem in Formalized Knowledge

Any formalized knowledge system (database, ontology, knowledge graph) is a map, not the territory. The map:
- Has finite resolution (discretizes continuous reality)
- Has boundaries (excludes "irrelevant" information)
- Has a projection (emphasizes some dimensions at the cost of distorting others)
- Becomes stale (territory changes, map doesn't)

The Goodhart risk: when agents optimize for coverage/completeness of their knowledge base, they may optimize for the map's internal consistency rather than its fidelity to reality. A knowledge base with 100% internal consistency and 0% external validity is perfectly organized ignorance.

### Structural Lessons for Agents

**CRITICAL.** This is the most directly applicable framework for agent knowledge system design:

1. **Diversified epistemic metrics.** Don't use a single metric for knowledge quality. Currently: pushback index, epistemic lint, SAFE-lite precision. These are already diversified (sycophancy, unsourced claims, factual accuracy — three different failure modes). Add: confirmation rate (Scheel metric), correction velocity (how fast errors are corrected after detection), and staleness rate (how quickly stored knowledge decays). No single metric should be the target.

2. **Post-hoc evaluation.** Don't announce evaluation criteria to the agent before the task. Run session-analyst on completed transcripts without pre-specifying what will be measured. This prevents the agent from optimizing for specific metric dimensions.

3. **External ground truth.** The epistemic metrics should be validated against external reality (market outcomes for intel, replication for research claims), not just internal consistency. A knowledge system that is internally consistent but externally wrong is the Goodhart failure mode.

4. **Metric rotation.** Periodically change which specific metrics are emphasized. This prevents optimization against a static evaluation function.

5. **The 40-60% confirmation rate as a health check.** If the system consistently produces >80% confirmatory findings, something is wrong (either the questions are too easy, or the system is confirming its priors). If <20%, the system is either broken or working on genuinely hard problems. Track this ratio as a system health metric.

---

## Disconfirmation Results

### What I searched for that challenged these frameworks

1. **Presupposition detection may not matter for LLMs.** Counter-argument: LLMs already handle presupposition failure reasonably well through instruction following. The Wang & Blanco paper partially addresses this — they show LLMs WITHOUT explicit presupposition checking still hallucinate answers to questions with false assumptions. The decomposition step genuinely helps.

2. **Smithson's taxonomy may be too academic for practical use.** Fair concern. The taxonomy's value is as a checklist, not as a runtime system. No one would implement all of Smithson's categories as a live system. But as a design audit tool — "have we covered each type of ignorance?" — it has practical value.

3. **Via negativa may be trivially obvious.** Counter: if it were obvious, agent systems would already emphasize negative knowledge storage. They don't. MEMORY.md entries are overwhelmingly positive ("X is true") rather than negative ("X is NOT true" or "We tried Y and it failed").

4. **Weather forecasting's calibration may not transfer.** Strong counter-argument: weather has rapid, unambiguous feedback. Investment research has slow, ambiguous feedback. The structural features CANNOT be fully replicated. But partial replication (quantitative scoring, symmetric incentives, ensemble methods) is still valuable.

5. **ASRS works because aviation has a strong safety culture.** Partial counter: the safety culture was CREATED by ASRS, not the other way around. The system came first; the culture followed. This is evidence that architectural changes precede cultural changes, supporting the constitutional principle.

6. **Goodhart's law is inescapable.** Manheim's framework shows it's manageable, not solvable. Diversification and post-hoc specification reduce gaming, but any metric system can be gamed given enough optimization pressure. The mitigation is metric rotation and external ground truth, not metric perfection.

---

## Search Log

| # | Tool | Query | Result |
|---|------|-------|--------|
| 1 | S2 | presupposition failure detection NLP computational linguistics | Noise — no relevant results |
| 2 | Exa | Smithson taxonomy of ignorance | Strong hit — i2insights.org + ResearchGate |
| 3 | S2 | pertinent negative reasoning diagnostic absence evidence | Noise — medical/radiology results |
| 4 | Exa | Strawson presupposition failure formal semantics | Strong — SEP, Yablo MIT, Glanzberg |
| 5 | Exa | pertinent negative reasoning medicine intelligence | Good — Hsu et al., legal analysis, SDT |
| 6 | Exa | Taleb via negativa subtractive knowledge | Good — Farnam Street, Wealest, Rational Walk |
| 7 | Exa | Bachelard epistemological obstacles Laudan | Moderate — secondary sources, no primary |
| 8 | Exa | replication crisis structural reforms measured improvement | Strong — Brodeur et al., Korbmacher et al. |
| 9 | Exa (crawl) | i2insights.org/2022/06/28/ignorance-taxonomy/ | Full Smithson taxonomy |
| 10 | Exa | weather forecasting calibration structural features | Moderate — technical papers, less on meta-structure |
| 11 | Exa | ASRS what makes it work | Strong — NASA documents, multiple explainers |
| 12 | Exa | Goodhart Campbell knowledge systems | Strong — Manheim framework, AI leaderboard example |
| 13 | Exa (crawl) | cocosci.princeton.edu absent data | Full paper text (Hsu et al.) |
| 14 | Exa | Tetlock superforecasting concrete results | Strong — Wikipedia, Mellers et al. |
| 15 | Exa | Open Science Collaboration 2015 numbers | Strong — OSF, BPS |
| 16 | Exa | presupposition detection NLP computational operationalize | Excellent — Wang & Blanco 2025, De-Presuppose 2025 |
| 17 | Exa | FMEA effectiveness performative | Moderate — mostly promotional, limited critique |
| 18 | Exa | pre-registration reduces p-hacking | Strong — Brodeur et al. full paper |
| 19 | Exa | registered reports null results rate | Strong — Scheel et al. 2021 |
| 20 | verify_claim | GJP Brier scores | Confirmed — 0.14-0.16 vs 0.30-0.37 |
| 21 | Exa | medical M&M conference effectiveness | Moderate — weak evidence base |
| 22 | Exa | reference class forecasting Kahneman | Good — Wikipedia, McKinsey, PMI |
| 23 | Exa | signal detection theory absence reasoning | Good — Wixted 2019, Hsu et al. again |

---

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Presuppositions are a well-defined formal construct with known triggers | SEP entry, 50+ years of literature | HIGH | plato.stanford.edu/entries/presupposition/ | VERIFIED |
| 2 | Atomic assumption decomposition improves LLM handling of false-presupposition questions | Wang & Blanco EMNLP 2025, Roy Dipta & Ferraro 2025 | HIGH | aclanthology.org, arxiv.org | VERIFIED |
| 3 | Smithson divides ignorance into Irrelevance and Error branches | Smithson's own 2022 summary of 1989 work | HIGH | i2insights.org | VERIFIED |
| 4 | Humans reason from absence consistent with Bayesian predictions, r=0.90-0.95 | Hsu et al. 2016, 2 experiments | HIGH | cocosci.princeton.edu | VERIFIED (read full paper) |
| 5 | Open Science Collaboration found 97% -> 36% significant results in replication | OSF project page, multiple secondary | HIGH | osf.io/ezum7/ | VERIFIED |
| 6 | Registered Reports show 96% vs 44% positive results | Scheel et al. 2021 | HIGH | doi.org/10.1177/25152459211007467 | VERIFIED |
| 7 | Pre-registration alone doesn't reduce p-hacking; PAPs do | Brodeur et al. 2024, 15,992 test statistics | HIGH | JPE Micro | VERIFIED |
| 8 | Superforecasters achieved Brier scores ~0.14-0.16 | verify_claim confirmed | HIGH | Multiple | VERIFIED |
| 9 | ASRS processed 500,000+ reports by 2001 | NASA ASRS Pub 60 | HIGH | asrs.arc.nasa.gov | VERIFIED |
| 10 | ASRS separation of analysis from enforcement is key design feature | NASA documents | HIGH | asrs.arc.nasa.gov | VERIFIED |
| 11 | De-Presuppose achieves 2-5% improvement | Roy Dipta & Ferraro 2025 | MEDIUM | arxiv (preprint) | VERIFIED but PREPRINT |
| 12 | M&M conferences lack strong outcome evidence | Integrative review (Churchill 2020) | MEDIUM | PMC7813522 | VERIFIED |
| 13 | Via negativa is "more robust" than positive knowledge | Taleb, theoretical argument | MEDIUM | Multiple secondary | INFERENCE (no empirical test) |
| 14 | Bachelard's epistemological obstacles apply to agent research | Extrapolation | LOW | Secondary sources | INFERENCE |
| 15 | Weather forecasting's calibration features can transfer to other domains | Tetlock partially demonstrated this | MEDIUM | GJP results | PARTIAL INFERENCE |

---

## What's Uncertain

1. **Whether presupposition decomposition actually improves agent research quality** in practice. The NLP papers show improvement on claim verification benchmarks, but no one has tested it on open-ended research questions.

2. **Whether the 40-60% confirmation rate is the right target.** This is inference from Scheel et al.'s 44% RR positive rate + the logic that a well-calibrated system should not overwhelmingly confirm its priors. The exact range is arbitrary.

3. **Whether Smithson's taxonomy adds practical value beyond what a simpler checklist would provide.** The full taxonomy may be overengineered for agent use. A three-category version (what we know, what we know we don't know, what we don't know we don't know) might suffice.

4. **Whether FMEA-style approaches work for epistemic failures.** FMEA works for physical systems with enumerable failure modes. Epistemic failures may be too diverse and context-dependent for systematic enumeration.

5. **Whether M&M conferences actually reduce errors.** The evidence is weak — mostly perceptual/self-report. No causal evidence.

---

## Sources Saved

Papers found but not saved to S2 corpus (philosophical/methodological — not typical S2 content):
- Wang & Blanco EMNLP 2025 (false assumptions in questions)
- Roy Dipta & Ferraro 2025 (De-Presuppose)
- Hsu, Horng, Griffiths & Chater 2016 (absence of evidence)
- Scheel, Schijen & Lakens 2021 (Registered Reports positive rate)
- Brodeur, Cook, Hartley & Heyes 2024 (pre-registration effectiveness)
- Manheim 2018/2023 (less-flawed metrics)
- Korbmacher et al. 2023 (replication crisis structural changes)

Web sources consulted:
- SEP: plato.stanford.edu/entries/presupposition/
- Smithson: i2insights.org/2022/06/28/ignorance-taxonomy/
- NASA ASRS: asrs.arc.nasa.gov/docs/rs/60_Case_for_Confidential_Incident_Reporting.pdf
- Good Judgment: goodjudgment.com/resources/the-superforecasters-track-record/
- ECMWF verification: Ben-Bouallègue 2025, arxiv.org/pdf/2602.00622

<!-- knowledge-index
generated: 2026-03-22T00:15:44Z
hash: 4bf7059f8424

title: Negative Space and Meta-Epistemics for Agent Knowledge Systems
sources: 10
  TRAINING-DATA: , verified against SEP entry
  TRAINING-DATA: , well-established
  TRAINING-DATA: , confirmed by medical literature search
  TRAINING-DATA: , verified against Wixted 2019 history of SDT
  TRAINING-DATA: + secondary sources
  TRAINING-DATA: , verified against existing philosophy-of-epistemic-agents.md
  INFERENCE: from the numbers
  TRAINING-DATA: , verified against ECMWF/WMO verification resources
  TRAINING-DATA: , widely confirmed
  INFERENCE: from Scheel et al. 2021
table_claims: 15

end-knowledge-index -->
