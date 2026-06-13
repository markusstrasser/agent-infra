---
title: Deterministic + graph diagnostics to forced-rank where to point LLM reasoning (code + markdown health)
date: 2026-06-13
status: complete
---

# Deterministic + graph diagnostics to forced-rank "where to point the LLM"

Question: best DETERMINISTIC/classical + GRAPH-algorithm methods to diagnose codebase + markdown-KB health and produce a FORCED RANKING of "where to point expensive LLM reasoning." Target: personal multi-repo agent-infra (20-150 src files/repo, 50-230 md memos), zero-maintenance, $0 preferred. Consumer = agent reading top-N flagged items with max reasoning.

Findings appended below as gathered.

## 1. CLASSICAL HOTSPOT PRIORITIZATION — primary evidence

**CodeScene / Tornhill canonical hotspot score** (vendor docs, CodeScene 4.0.16 + Tornhill "Your Code as a Crime Scene" 2015):
- Hotspot = **change frequency (commit count per file) × code size (LOC as proxy for complexity)**. CodeScene explicitly states "lines of code in each file as a proxy for complexity" and change frequency "as a proxy for the effort you've spent." Method = "look for an OVERLAP between the two metrics" — i.e. files that are BOTH frequently changed AND large. Exact normalization is proprietary; the visualization is a circle-packing map (size=LOC, color=churn). [vendor-source; method is well-replicated]
- **Relative Code Churn** is the alternative: churn (lines changed) weighted against total file size — a *relative* metric.
- Vendor claim: "Change alone is the single most important metric when it comes to quality issues in code." [vendor; but grounded in Nagappan/Ball + Tornhill's own studies]

**Nagappan & Ball 2005, ICSE, "Use of Relative Code Churn Measures to Predict System Defect Density"** (Microsoft Research; PEER-REVIEWED, ~highly cited):
- KEY FINDING: "absolute measures of code churn are POOR predictors of defect density; RELATIVE measures of code churn are highly predictive." This is the foundational why-churn-works result.
- Windows Server 2003 case study: relative-churn suite discriminated fault- vs not-fault-prone binaries at **89.0% accuracy**.
- TRANSFER NOTE: pre-frontier (2005) but SCALE-INDEPENDENT (it's a statistical property of change processes, not a model artifact) → transfers. The lesson for us: normalize churn by size; don't rank on raw commit count.

Process-metrics > product-metrics for defect prediction is replicated: Madeyski & Jureczko 2014 (Software Quality Journal, 180 cites) "Which process metrics can significantly improve defect prediction models?" — process metrics (incl. churn, number of revisions, number of distinct authors) significantly improve over static code metrics alone. Rahman & Devanbu (well-known) similarly: process metrics more stable/portable than code metrics for defect prediction.

IMPLICATION FOR US: the cheapest, best-evidenced single signal is **git change-frequency × size**, NOT cyclomatic complexity. Cyclomatic/cognitive complexity is a *secondary* refinement.

### Per-method verdicts — hotspot/classical tier

| Method | What it flags | Cost to run | False-positive tendency | Verdict (this setup) |
|---|---|---|---|---|
| git change-freq × LOC (CodeScene core) | files both large AND churned = maint risk | trivial (`git log --name-only` + `wc -l`); $0 | LOW — best-evidenced signal | **ADOPT — primary signal** |
| Relative churn (lines-changed / size) | recently volatile files | trivial (git numstat); $0 | LOW | **ADOPT — as recency tiebreaker** |
| Cyclomatic complexity (radon/lizard) | branchy functions | cheap, $0, language-bound (radon=Py, lizard=multi) | MED — ~redundant with LOC (Mamun 2019, see §3) | **THIN-LAYER — only as weak refinement, don't double-weight with LOC** |
| Cognitive complexity (SonarQube) | hard-to-read control flow | needs Sonar/scanner; heavier | MED | **SKIP — vendor-coupled, marginal over cyclomatic at this scale** |
| jscpd / PMD-CPD (copy-paste) | Type-1/2 clones (Rabin-Karp token match) | cheap, jscpd=node $0, 150+ langs incl. markdown | MED (boilerplate/generated false hits) | **THIN-LAYER — high signal for "DRY violation, refactor here"; run, don't gate** |

## 3. LONG-FILE / GOD-FILE DETECTION — is length even a good signal?

**Headline: raw file length is a WEAK, partly MISLEADING signal in isolation.** Evidence:
- **Non-monotonic / curvilinear size↔defect relationship** (multiple empirical studies, e.g. controlled experiments + Yamashita QRS2016): defect *density* DECREASES with size, then curves up only at the extreme tail. "The same amount of code in large and complex files was associated with FEWER defects than when in smaller, less complex files." An "optimal size" exists (short-term-memory-cache hypothesis). So ranking purely by LOC mis-ranks. [peer-reviewed but mixed/old; the robust takeaway is *non-linear*, not a clean threshold].
- **Metric redundancy: Mamun, Berger & Hansson 2019, Empirical Software Engineering** ("Effects of measurements on correlations of software code metrics") — code metrics (cyclomatic complexity, LOC, Halstead, etc.) are correlated with each other "at such a high level that such correlations [make them] redundant." CONSEQUENCE: stacking LOC + cyclomatic + Halstead in a composite is double-counting one latent "size" factor. [peer-reviewed, directly relevant].
- **Cohesion as the better "should-split" signal — but LCOM is a flawed operationalization.** The canonical god/brain-class detector (Lanza & Marinescu, *Object-Oriented Metrics in Practice*, detection strategies) is a COMPOSITE: high size/complexity (WMC) AND high coupling (access to foreign data) AND LOW cohesion (TCC/LCOM) — never size alone. But LCOM itself is "susceptible to outliers and lacks normalization" (multiple critiques) and class size "was not sufficient for fine-grained maintainability prediction." So cohesion is conceptually the right axis, but no cheap, well-normalized cohesion metric transfers cleanly to a procedural/markdown multi-repo.
- VERDICT for this setup: **use length only as a coarse PREFILTER (top-decile longest = candidate), then let churn + duplication + (for the agent) semantic cohesion decide.** Do NOT forced-rank on length. A long, stable, never-touched file is the LEAST urgent thing to point an LLM at — exactly the trap raw length sets.

## 2. GRAPH ALGORITHMS ON CODE — do they pay off at 20-150 files?

- **Centrality for "god files" (PageRank / betweenness on import graph):** identifies files everything depends on. Evidence that network centrality correlates with bug-proneness exists (key-class identification papers: Ding/Li/He 2016 weighted software networks; key-class studies). BUT at 20-150 files the import graph is small enough that `grep`-counting reverse-imports (fan-in) gives ~the same ranking as PageRank for near-zero cost. **PageRank/betweenness = THIN-LAYER at best; raw fan-in degree is the 90% version.**
- **Community detection (Louvain/Leiden) to suggest file splits / remodularization:** real research area (Ducasse et al. package remodularisation; graph-autoencoder extract-class). But it's an *action recommender* ("split this module") needing a sizable graph to be meaningful; at <150 files the modular structure is human-legible already. **SKIP — overkill at this scale; this is a >1000-file tool.**
- **Cycle detection (import cycles):** cheap, deterministic, unambiguous (a cycle IS a defect-smell), high-signal-low-FP. Tools: `pydeps`, `madge` (JS), `import-linter`. **ADOPT (thin) — a detected cycle is a clean "look here" flag with near-zero false positives.**
- **Code Property Graphs / Joern:** built for security/taint analysis across large codebases; massive setup. **SKIP — wrong tool for KB-health triage.**
- VERDICT: at this scale, the only graph signals worth computing are **fan-in degree (cheap god-file proxy)** and **import-cycle detection**. Everything fancier (PageRank, Louvain, betweenness, CPG) is a large-repo tool whose ranking you can approximate with counting at 20-150 files.

## 4. EMBEDDING-BASED DIAGNOSTICS — when does it earn its place?

- **Near-duplicate docs:** the *industrial* answer at scale (BigCode/HuggingFace dedup, trillion tokens) is **MinHash + LSH on character n-gram shingles (n=5, ~112-perm sig, banded LSH)** — Jaccard-approx, $0, no model. Embeddings (semantic dedup) are "highly accurate but computationally expensive"; the field reaches for MinHash-LSH *specifically to avoid* embedding cost. At 50-230 markdown files, MinHash-LSH is overkill-cheap and exact pairwise Jaccard is also fine (N² over 230 docs = trivial). **Embeddings NOT needed for near-dup detection.**
- **Where embeddings DO earn it (and only here):** *semantic* overlap that survives paraphrase — two memos saying the same thing in different words (MinHash misses this), and intra-file topic drift. Cost: one embedding pass (your own memory notes price Gemini Embedding 001 whole-corpus at ≈$0.01-0.05 — see `scientific-embeddings-recommendation-2026-05`). At that price it's not a cost question, it's a *value/maintenance* question.
- VERDICT: **THIN-LAYER, optional.** Lead with MinHash/Jaccard near-dup (free, lexical). Add ONE cheap embedding pass for semantic-overlap clustering ONLY if lexical dedup misses real redundancy in practice. Do not build a vector store; compute cosine in-memory and discard. Don't make embeddings part of the standing forced-ranking — they're a periodic audit, not a per-run signal.

## 5. MARKDOWN / KNOWLEDGE-BASE — what transfers, what doesn't

TRANSFERS:
- **Churn × size** transfers cleanly — a memo that's both long and frequently re-edited is exactly where belief is unsettled / the agent should look. This is the single best KB signal too.
- **Duplication detection** transfers (jscpd handles markdown; MinHash is format-agnostic) — near-dup memos = consolidation candidates. Directly matches the user's own MEMORY.md problem (the system-reminder flags it at 32.6KB / over the 24.4KB limit with over-long entries).
- **Fan-in / orphan detection** transfers via the wikilink graph: `[[name]]` backlink count = "centrality" of a memo; ZERO backlinks + never-read = orphan/dead-knowledge candidate. Cheap, high-signal.
- **Cycle / staleness:** a memo's git mtime + "stale after 90 days" (the researcher memory's own decay model) is a deterministic flag.

DOESN'T TRANSFER:
- Cyclomatic/cognitive complexity, LCOM, CPG — no control flow in prose. Meaningless.
- "Optimal size" curvilinear defect curve — no defect ground truth for prose; length is even weaker as a standalone KB signal than for code.

KB-SPECIFIC cheap signals worth adding: (a) **broken `[[wikilinks]]`** (dangling pointers — deterministic, $0); (b) **index/file divergence** (entries in MEMORY.md whose target file is missing, or files absent from the index); (c) **staleness** (mtime > decay window). All deterministic, all $0.

## RECOMMENDED FORCED-RANKING COMPOSITE

Goal: surface a top-N "point the LLM here" list from cheap, deterministic signals. Principle (from Mamun 2019): **do NOT stack correlated metrics** — pick orthogonal axes. Four near-independent signals, each normalized to a 0-1 percentile rank within the repo, then weighted:

**For CODE files:**
```
score = 0.45 * churn_rank          # git commits-touching-file over window (Nagappan/Ball: the strongest signal)
      + 0.25 * size_rank           # LOC percentile — PREFILTER weight, not dominant (curvilinear caveat)
      + 0.20 * duplication_rank    # jscpd % duplicated lines in file
      + 0.10 * fanin_rank          # reverse-import count (cheap god-file proxy)
  [+ hard flags, not weighted: in_import_cycle => force into top-N; ]
```
Rationale for weights: churn is the best-evidenced predictor (Nagappan/Ball 89%, Madeyski/Jureczko process>product) → dominant. Size is real but non-monotonic and correlated with complexity → capped, used mainly to break churn ties and catch the extreme tail. Duplication and fan-in are orthogonal smells. Cyclomatic complexity is DELIBERATELY OMITTED from the weighted sum (redundant with LOC per Mamun 2019); compute it only as a display annotation for the agent.

**For MARKDOWN/KB files:**
```
score = 0.40 * churn_rank          # git re-edit frequency (unsettled belief)
      + 0.25 * duplication_rank    # MinHash/jscpd near-dup overlap with other memos
      + 0.20 * size_rank           # length percentile (consolidation pressure)
      + 0.15 * orphan_or_stale     # 0/1: zero backlinks OR mtime>decay-window
  [+ hard flags: broken [[wikilink]] present; index/file divergence => surface regardless of score]
```

WHY THIS SHAPE (not a single metric, not ML): the consumer is an LLM with a fixed top-N budget. The job of the deterministic layer is RANKING + RECALL, not precision — surface candidates cheaply, let the expensive reasoner be the precision filter. This mirrors the agent-infra Harness-1 lens already in CLAUDE.md (externalize recoverable bookkeeping — here, the candidate pool/scoring — out of the policy). Hard flags (cycles, broken links, index divergence) bypass the weighted score because they are unambiguous defects with ~0 false positives; ranking is for the fuzzy stuff.

IMPLEMENTATION FOOTPRINT (matches zero-maintenance / $0): a single Python script over `git log --numstat` + `wc -l` + one `jscpd --reporters json` call + a wikilink/backlink pass. No new service, no vector DB, no vendor. Native-first: most of this is `git log` + a SQLite view, consistent with this repo's native-patterns rule. Cyclomatic via `radon`/`lizard` is an optional annotation, not a ranking input.

## EVIDENCE-QUALITY LEDGER
- Nagappan & Ball 2005 (relative-churn 89%): PEER-REVIEWED (ICSE), pre-frontier but scale-independent statistical result → transfers. STRONGEST anchor.
- Madeyski & Jureczko 2014 (process>product metrics): PEER-REVIEWED (Software Quality Journal, 180 cites). Solid.
- Mamun/Berger/Hansson 2019 (metric redundancy): PEER-REVIEWED (Empirical Software Eng). Directly supports "don't stack LOC+cyclomatic."
- Curvilinear size↔defect: PEER-REVIEWED but MIXED/older; robust claim is "non-linear," not a specific threshold. Use directionally.
- LCOM critiques, Lanza/Marinescu detection strategies: established textbook + papers; cohesion-is-right-axis but no clean cheap metric.
- CodeScene hotspot method: VENDOR docs (method well-replicated, formula proprietary). Tornhill "Crime Scene" 2015 = practitioner book citing the above research.
- jscpd/PMD-CPD (Rabin-Karp, Type-1/2): TOOL docs. MinHash-LSH dedup (BigCode): industrial blog (HuggingFace) — high credibility for the cost claim.
- Graph/centrality for key-classes (Ding 2016 etc.): PEER-REVIEWED but the ROI-at-small-scale verdict is MY reasoning (fan-in approximates PageRank on tiny graphs), flagged as such.

## OMISSIONS / CAVEATS
- No defect ground-truth in this environment → cannot *validate* the composite locally; weights are evidence-seeded priors, tune by spot-checking whether top-N matches where the agent actually finds issues (Constitution: ground-truth verifier conditioning — this is partial/noisy-verifier territory → bounded autonomy, human spot-check).
- S2 `search_papers` was rate-limited/empty on the churn query; primary churn evidence sourced via web + OpenAlex backend + the Nagappan/Ball primary. Provenance noted.
- SonarQube cognitive-complexity defect evidence is largely vendor-published; treated as such and skipped on those grounds, not adopted.

status: complete


