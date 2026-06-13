---
title: Optimal Repository Representation for Tool-Using LLM Agents + Monolithic File Generation
date: 2026-06-13
status: complete
---

# Optimal Repo Representation for grep/glob/read/LSP Agents, and the Monolithic-File Problem

Two linked questions. **A** = what representation maximizes task success for an agent that
navigates by grep/glob/read/LSP (not a RAG chatbot). **B** = why agents emit 1000+ line
monolithic files and what controls it.

Evidence-quality convention: **[CURRENT]** = frontier models (GPT-5.x, Claude 4, Gemini 2.5+,
GLM-5, Kimi-k2.5, DeepSeek-V3.2). **[PRE-FRONTIER]** = GPT-4-class or earlier; flagged
"validity uncertain" unless scale-independent. **[MECH]** = mechanism robust to scale.

---

## TL;DR for this repo

1. **Aider's repo-map is the reference design and it is the SAME mechanism as our own
   `context-budget-principles.md` rule #1 ("file names ARE the index")** — a ranked,
   token-budgeted structural skeleton, not raw dump. The measured win for the graph layer is
   modest-but-real: **RepoGraph +32.8% relative resolve rate on SWE-bench-Lite** [CURRENT-ish,
   ICLR 2025], Aider's tree-sitter map turns "unusable on large repos" into "usable." This is a
   *retrieval/affordance* lever independent of the model — exactly the Harness-1 /
   state-externalization thesis already in our constitution.
2. **The monolith bias is now MEASURED on frontier models, not folklore.** arXiv:2604.06742
   (CLI-Tool-Bench, 2026) finds *all seven* evaluated frontier LLMs cluster at a **median of
   1–3 files per project** while human oracles spread broadly. The cause it names is
   structural, not stylistic: minimize cross-file `ImportError` risk + keep whole state inside
   one context window. **This predicts prompting will barely move it** (consistent with our
   "instructions ≈0% reliable" prior) and that the fix must be architectural — a write-time
   signal or a repo-map feedback loop. That is a *direct evidence base for a length/cohesion
   lint*, which is currently a gap.
3. **Context-rot is real and NON-uniform, and the dangerous bulk is topically-similar code,
   not random filler** (Chroma 2025) — which validates the exact wording already in
   `context-budget-principles.md` §8 ("topically-close-but-stale text hurts MORE than
   irrelevant bulk; prune for staleness first, size second"). A long file hurts an agent twice:
   once by costing tokens, once by acting as a distractor field around the ~20 lines that matter.

---

## QUESTION A — Optimal representation for a tool-using agent

### A1. Aider's repo-map — how it actually works (hard mechanics)

Source: Aider docs + DeepWiki reverse-engineering of the source + the 2023 design blog.
Implementation is `networkx` PageRank over a tree-sitter symbol graph.

- **Nodes/edges.** Tree-sitter parses each file's AST to extract *definitions* and
  *references* of functions/classes/vars/types ("Using the AST, we can identify where
  functions, classes, variables, types and other definitions occur … and where … these things
  are used or referenced"). The graph is built per-identifier: *"For each identifier that
  appears in both `defines` and `references`: for each file that references the identifier …
  add edge: `referencing_file -> defining_file` with `weight=1.0`."* Self-edges
  `weight=0.1` keep definition-only files from vanishing.
- **Ranking = personalized PageRank.** *"NetworkX's PageRank algorithm with personalization
  based on chat context."* Files already in the chat, mentioned by name, or whose path matches
  a mentioned identifier get a personalization mass of `100 / len(fnames)` — i.e. the map is
  *recomputed every turn, biased toward what the conversation is touching right now.* The 2023
  blog adds identifier-level multipliers (mentioned ident 10×, well-named/snake_or_camel ident
  10×, chat files 50×). The output is "the most important identifiers, the ones most often
  referenced by other portions of the code."
- **Token budget.** `--map-tokens` (default **1k**). It binary-searches/accumulates ranked
  defs until the budget is hit, then elides bodies with `...` (scope-aware *signatures only*,
  not full source). When no files are in the chat it expands via `map_mul_no_files`.
- **Caching.** Tree-sitter parse results cache on mtime; only changed files re-parse.

**What it buys.** The honest claim is *affordance*, not a headline accuracy number — the docs
give no benchmark. It lets the model "figure out which files it needs to look at" and "how to
use the API" without the human hand-selecting files, and it makes large repos fit a budget at
all. Think of it as a *cheap always-on `ctags`-with-ranking* prepended to the prompt.

### A2. Repo-as-graph papers — the measured numbers

- **RepoGraph** (Ouyang et al., ICLR 2025, arXiv:2410.14684; 85 cites). **[CURRENT-ish]**
  *Line-level* code graph (finer than Aider's file-node graph): tree-sitter tags → `networkx`,
  **>1,000 nodes and ~25,000 edges average per SWE-bench instance**. Plugged into existing
  scaffolds as a retrieval module:
  > "RepoGraph achieves an absolute improvement of **+2.66 and +2.34** in resolve rate for RAG
  > and Agentless respectively … **average relative improvement of 32.8%** in resolve rate on
  > SWE-bench-Lite." Best Agentless+RepoGraph = **29.67**, SoTA among open-source methods at
  > the time.
  Takeaway: a structural graph as a *navigation index* is a real, model-independent lever, but
  the absolute deltas are single-digit points, not transformative. **Granularity matters:
  RepoGraph went line/function-level, finer than Aider's file-level.**
- **Counter-evidence on graph granularity** [CURRENT]: "In Line with Context" (arXiv:2601.00376)
  finds that for *function-body generation* (not line completion), a plain **In-File baseline
  (intra-file context only) is competitive and sometimes BEATS GraphCoder/DRACO**, because
  those graph methods were built for line-level completion and *discard in-file local context*.
  Lesson: a code graph helps cross-file *navigation/localization*; it can hurt if it replaces
  local context for *generation*. Use the graph to *find* the file, not to *substitute* for
  reading it.
- **"Beyond More Context: Granularity and Order"** (arXiv:2510.06606, ASE 2025 challenge)
  [CURRENT]: chunk-level retrieval via static analysis beat file-level retrieval by **+6%** and
  no-context by **+16%** (Python); "the amount and order of context can significantly influence
  performance." Reinforces: *finer, ranked, ordered* > *whole files dumped*.
- **ReCUBE** (arXiv:2603.25770, 2026) [CURRENT]: agentic exploration helps small-context models
  (Devstral +2.06/5.01% SPR/APR) but the gain **vanishes as context capacity grows**
  (Qwen3-Coder +0.42%; GPT-5-Mini actually *better with full context, −2.21% under the agent
  loop*). Implication: the value of a smart map is *inversely proportional to how much the model
  can hold and use well* — but since context-rot (A4) means "can hold" ≠ "uses well," the map
  still pays off in practice on big repos.

> **Naming note:** the task brief listed CodePlan/RepoFusion. Those are **[PRE-FRONTIER]**
> (2023, GPT-3.5/CodeGen era) — RepoFusion is a *fine-tuned 220M model fusing repo contexts for
> completion*, CodePlan frames repo edits as planning. Neither describes a tool-using agent and
> their absolute numbers don't transfer to frontier. The live design lineage is
> Aider-repomap → RepoGraph → Prometheus/ARISE (2025–26 agent navigators).

### A3. LSP / ctags / tree-sitter as the index vs raw grep

- The whole Aider/RepoGraph line is essentially *"ctags-with-ranking, regenerated per turn."*
  Tree-sitter is the universal parser (Aider uses `py-tree-sitter-languages` wheels). No frontier
  paper found that *isolates* "LSP go-to-def tool vs grep" as a head-to-head accuracy
  experiment — **that comparison is an evidence gap.** What exists: ARISE (arXiv:2605.03117,
  2026) and Prometheus (arXiv:2507.19942) give the agent a *graph + toolset* to "follow call and
  data dependencies" for fault-localization/repair; both report the graph toolset helps long-
  horizon navigation, but neither ablates grep-only.
- Practical synthesis from the above: **a structural map is most valuable as a cheap always-
  present *table of contents that names symbols and their cross-file edges*, letting the agent
  decide what to `read` next.** It is a *router*, not a substitute for reading — which is
  exactly our `context-budget-principles.md` framing ("Indexes route; they don't summarize").

### A4. Context-rot as a function of file length (the cost side)

**Chroma "Context Rot" (2025)** [CURRENT; MECH] — 18 production models incl. Claude 4 Sonnet,
GPT-4.1, Gemini 2.5 Pro. The findings most relevant to "does a long file hurt my agent":

1. **Degradation is monotonic but NON-uniform.** "Model performance degrades as input length
   increases, often in surprising and non-uniform ways … performance grows increasingly
   unreliable as input length grows." No model held uniform accuracy across its advertised
   window; steepest drop in the 100k–500k range; **20–50% drops from 10k→100k+** on NIAH-style
   tasks.
2. **Distractors (topically-similar-but-wrong) hurt MUCH more than random filler.** "Distractors
   are topically related to the needle but do not quite answer the question." A *single*
   distractor already lowered performance vs needle-only; four compounded it; specific
   distractors dominated *hallucinated* answers. **This is the load-bearing result for code:**
   a 1,200-line file is a dense field of near-miss distractors (similar function names, old
   variants, dead branches) around the ~20 lines that matter.
3. **A long input hurts even when the answer is fully present.** LongMemEval: focused ~300-token
   prompts beat ~113k-token prompts *containing identical relevant info*; Claude Opus 4 abstained
   more on the long version citing "ambiguity."
4. **Lower needle↔question similarity degrades faster** — the agent's job (find the one function
   relevant to a vaguely-worded task) is exactly the low-similarity regime that collapses
   soonest.

Corroboration: **NoLiMa** (arXiv:2502.05167, 88 cites) [CURRENT] — beyond literal matching,
"effective" context is far shorter than advertised; **"Hidden in the Haystack"** (2505.18148)
[CURRENT] — smaller needles + more distractors are the hard regime; **RULER** (2404.06654, 991
cites) — real usable context ≪ nominal. **ACE** (arXiv:2510.04618) [CURRENT] adds the writer-side
twin: "Monolithic rewriting of context by an LLM can collapse it into shorter, less informative
summaries, leading to sharp performance drops" — i.e. monolithic *anything* (file or prompt) is
a known failure mode, and the fix is *structured itemized units*.

**Quantified answer to "how much does a long file hurt":** plan for a **20–50% reliability tax
once the relevant material is buried in >100k tokens of similar code, with measurable damage from
even a single near-miss distractor.** The damage is *concentrated in topical-similarity*, so the
mitigation is to shrink and de-noise the *neighborhood the agent reads*, not merely the global
total. This is a direct empirical license for: short, single-responsibility files + a ranked map
that points the agent at the few lines that matter.

### A5. File granularity & naming for retrieval (synthesis, evidence is indirect)

No paper directly optimizes "ideal file size for an agent." But the convergent signal across
A2–A4 is unambiguous:
- **Finer-grained, ranked, ordered units beat whole-file dumps** (+6% chunk vs file, +16% vs
  none; RepoGraph line-level; granularity "drives" completion quality).
- **Self-describing symbol names are doubly weighted** in the only production ranker we have
  (Aider's 10× "well-named identifier" multiplier) — names ARE retrieval signal, mechanically.
- **Short files are distractor-minimal** (A4): they keep the read-neighborhood high-similarity-
  to-task and low-noise.
This is the empirical backing for our existing `context-budget-principles.md` rules #1 (file
names = index) and #8 (prune topical-stale first). The gap: we assert it; the field now
*measures* it.

---

## QUESTION B — Why agents write monolithic files, and what controls it

### B1. The bias is measured on frontier models

**arXiv:2604.06742, "Evaluating LLM-Based 0-to-1 Software Generation in End-to-End CLI Tool
Scenarios" (CLI-Tool-Bench, 2026)** [CURRENT — GLM-5, Kimi-k2.5, DeepSeek-V3.2, Qwen-plus,
MiniMax-M2.5, + 2 more]. This is the strongest direct evidence found:

> "all evaluated LLMs demonstrate a strong preference for monolithic structures, with their
> medians tightly clustered between **1 and 3 files** … a shared behavioral strategy among
> LLMs: centralizing logic into a single or very few files. From an agentic perspective, this
> monolithic approach seems to be a practical adaptation **to minimize cross-file dependency
> issues (e.g., ImportError) and to keep the entire system state easily accessible within the
> model's limited context window.**"

Human oracles "exhibit a broad distribution" (normal modularization). Two more measured facts:
- **Higher token consumption does NOT yield better results** — more code ≠ better; and "code is
  significantly longer for incorrectly generated code … quality decreases with the length of the
  code" (echoed by the general-survey snippet). Length is a *negative* correlate of correctness.
- **U-shaped difficulty curve:** agents fail *most* on mid-sized repos requiring cross-file
  reasoning, and *rebound* on large repos — "likely due to standardized framework utilization
  that aligns with LLMs' pretraining distribution." Direct evidence that **the pretraining
  distribution drives structure choices.**

### B2. The mechanistic explanations (ranked by evidence strength)

1. **Context-window self-protection (phenomenon MEASURED B1; this *mechanism* is the authors' own "seems to be" interpretation, not isolated causation).** Keeping all state in one file means the
   agent never has to *re-read* across files within a turn — it dodges its own context-rot. The
   monolith is a *rational response to A4*: cross-file means more reads, more distractors, more
   `ImportError`. This is the dominant, evidence-backed cause.
2. **Single-tool-call / append-locality economy (STRONG INFERENCE).** One `Write` of a big file
   is one tool call; a modular layout is N writes + import wiring + N reads to verify. Under any
   per-call cost or step budget, the monolith is locally optimal *for the writer*. The
   **cross-session externality** the brief names — *the writer doesn't bear the reader's
   distractor tax* — is real and *unpriced*: nothing in the generation objective charges the
   author for the future agent that must grep a 1,200-line file. No paper names this externality
   explicitly = **a clean conceptual gap worth owning in our memo.**
3. **Training distribution (MEASURED-INDIRECT, B1 U-curve).** Models reproduce the structure
   distribution of their training corpus *conditioned on what they can hold*; the rebound on
   framework-heavy large repos shows pretraining patterns win when they exist. Tutorial/gist
   data (single-file scripts) is over-represented for "0-to-1 from a prompt," biasing toward
   one file.

### B3. MEASURED interventions — what actually controls it

| Intervention | Evidence | Effect | Quality |
|---|---|---|---|
| **Prompt "be modular" / "don't write monolithic output"** | Addy Osmani workflow + general guidance; no controlled frontier ablation found | Folklore-positive, **expected weak** — matches our "instructions ≈0% reliable" prior; nobody reports a measured reduction from prompting alone | thin / [PRE-FRONTIER-ish] |
| **Modular-implementation *paradigm* (decompose task into per-file/per-function tickets, agent emits one unit at a time)** | Multi-agent legacy-upgrade + survey snippets; VAPU (arXiv:2510.18509) phased per-file updates **+22.5%** requirements-met vs ZSL/OSL | Works because it **restructures the task, not the prompt** — bypasses output-token limits + raises precision by shrinking the unit | [CURRENT], moderate |
| **Multi-agent role split (planner emits structure, coders fill files)** | CoDA (2510.03194) +up to 41.5% on a different domain; CAID (our memory, arXiv:2603.21489) | Structure-planning agent forces a file layout *before* code exists → breaks the single-file default | [CURRENT], domain-transfer caveat |
| **Repo-map feedback loop at write time** | No direct study found | **UNTESTED** — plausible: feed the agent its own ranked map after each write so the "reader's cost" becomes visible to the writer. This is the natural architectural fix and an **open lever**. | gap |
| **Write-time length/cohesion lint (block/warn on >N lines or low cohesion)** | No controlled study; *implied* by length↔incorrectness correlation (B1) + "architecture shifts the slope, instructions shift the intercept" (SlopCodeBench, in our constitution) | **UNTESTED but theory-backed.** The measured length-correctness correlation means a length gate targets a real quality signal, not a style preference. | gap, recommend probe |

**Bottom line for B:** the monolith is a *structural adaptation to context limits + an unpriced
reader externality*, so — consistent with everything in our own constitution — **prompting will
not fix it; only changing the task decomposition (modular paradigm / planner agent) or adding a
write-time architectural signal (length/cohesion gate or a repo-map feedback loop) will.** The
two "gap" rows are the actionable, currently-unbuilt levers.

---

## Evidence gaps / thin spots (these are findings)

1. **No head-to-head "LSP/ctags tool vs raw grep" accuracy ablation** for a frontier agent. The
   community treats the structural map as obviously good; the *isolated* causal number is
   missing.
2. **No controlled measurement that a write-time length/cohesion lint reduces monolith
   generation** — the single most decision-relevant experiment for us, and it does not exist in
   the literature. (The length↔incorrectness correlation is the closest proxy.)
3. **The "writer doesn't pay the reader's distractor tax" externality is un-named in the
   literature** — conceptual whitespace.
4. **Aider publishes no benchmark for its own repo-map**; the quantified graph-win comes from
   RepoGraph (+32.8% rel.) and the granularity studies, not from Aider itself.
5. **scite stance check:** the monolith-bias claim (arXiv:2604.06742, 2026) has **no
   stance-tagged citations yet** (too new) — corroboration is by independent convergence
   (granularity studies, ACE context-collapse, length-correctness) rather than by a citation
   consensus. Treat the specific "median 1–3 files" number as *single-source, current, plausible*
   until a second measurement lands.

## How this maps to our existing rules (no new rule proposed here — that's a plan-mode call)

- Validates `context-budget-principles.md` #1 (names = index) and #8 (topical-stale hurts most)
  with *measured* frontier evidence rather than assertion.
- The monolith finding is a **direct evidence base for a write-time length/cohesion lint** — an
  architectural ("shifts the slope") intervention, the category our constitution prefers over
  instructions. It is currently a gap; a 10-file probe (measure monolith rate with/without a
  warn-only line gate on real agent sessions) is the cheap first step before building anything.
- RepoGraph/Aider = the Harness-1 / state-externalization thesis instantiated for *code
  navigation*: externalize the "what's where" bookkeeping into a ranked map so the policy only
  decides what to read.

## Revisions

**2026-06-13 — B2.1 mechanism label tightened after full-source re-verification.** A primary
check of the full text (arxiv.org/html/2604.06742v1) confirmed the quoted finding is real: the
paper *does* state the ImportError-avoidance + limited-context-window mechanism. But it frames it
as "seems to be" / "an agentic perspective" — the authors' *speculative interpretation*, not
isolated causation. The **phenomenon** (1–3-file median preference) is measured; the **mechanism**
is hypothesized. Softened B2.1's "MEASURED" label. (Meta-lesson: an abstract-only fetch first
mis-read the paper as making NO mechanism claim — that absence was the fetch's artifact, not the
paper's. Verify at full primary, not the abs page.)
