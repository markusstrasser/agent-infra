## Karpathy's AutoResearch — Deep Dive

**Question:** Full analysis of karpathy/autoresearch: architecture, No Priors podcast claims (especially blockchain analogy), evolution, community forks, and comparison to our meta/scripts/autoresearch.py adaptation.
**Tier:** Deep | **Date:** 2026-03-25

### Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Repo has 56K+ stars, 7.8K forks, 8 contributors | GitHub API metadata | HIGH | [SOURCE: gh api repos/karpathy/autoresearch] | VERIFIED |
| 2 | Created March 6, 2026; last pushed March 26, 2026 | GitHub API | HIGH | [SOURCE: gh api] | VERIFIED |
| 3 | Three-file architecture: prepare.py, train.py, program.md | README | HIGH | [SOURCE: github.com/karpathy/autoresearch] | VERIFIED |
| 4 | Fixed 5-minute time budget per experiment, ~12 experiments/hour | README | HIGH | [SOURCE: github.com/karpathy/autoresearch] | VERIFIED |
| 5 | Karpathy explicitly made the blockchain analogy on No Priors podcast | Full transcript at podscripts.co, starting at 00:34:23 | HIGH | [SOURCE: podscripts.co transcript] | VERIFIED |
| 6 | Shopify CEO Tobi Lutke got 19% improvement on internal model | Multiple secondary sources (Awesome Agents, DataCamp) | MEDIUM | [SOURCE: awesomeagents.ai, datacamp.com] | NOT PRIMARY-VERIFIED |
| 7 | Chase (hwchase17) published autoresearch-agents for agent optimization | GitHub repo exists | HIGH | [SOURCE: github.com/hwchase17/autoresearch-agents] | VERIFIED |
| 8 | MIT license | README | HIGH | [SOURCE: github.com/karpathy/autoresearch] | VERIFIED |

---

### 1. The Repo — Architecture and Current State

**Repository:** [github.com/karpathy/autoresearch](https://github.com/karpathy/autoresearch)
**Stats (as of 2026-03-25):** 56,291 stars | 7,841 forks | MIT license | Python 83.4%, Jupyter 16.6% | 8 contributors | Created 2026-03-06 | Still actively pushed (2026-03-26)

**Core Architecture — Three files with strict ownership:**

| File | Owner | Purpose |
|------|-------|---------|
| `prepare.py` | Fixed (human-written, never modified) | Data prep (downloads FineWeb-Edu, trains BPE tokenizer), evaluation utilities, dataloader |
| `train.py` | Agent (only file the agent edits) | Full GPT model definition, optimizer (Muon + AdamW), training loop. Everything is fair game. |
| `program.md` | Human (iterated by the researcher) | Instructions for the agent — research direction, constraints, what to explore. Karpathy calls this "research org code." |

**The Loop:**
1. Agent reads `program.md` + current `train.py`
2. Proposes a modification to `train.py`
3. Commits the change
4. Runs training for exactly 5 minutes (wall clock, excluding startup/compilation)
5. Measures `val_bpb` (validation bits per byte) — lower is better, vocab-size-independent
6. If improved: keep the commit. If not: `git reset` to discard.
7. Repeat.

**Key Design Decisions:**
- **Single file to modify.** Bounded agent scope, reviewable diffs.
- **Fixed time budget.** Makes experiments directly comparable regardless of what the agent changes (model size, batch size, architecture). Also means autoresearch finds the most optimal model *for your specific platform* in that time budget. Downside: runs are not comparable across different hardware.
- **Self-contained.** No external dependencies beyond PyTorch + a few small packages. No distributed training, no complex configs.
- **Agent-agnostic.** "Simply spin up your Claude/Codex or whatever you want in this repo." The agent just needs to read files, edit files, and use git.

**What the repo is NOT:**
- Not an orchestration framework (no loop runner in the repo itself)
- Not a hyperparameter search tool (the agent can modify *anything* in train.py, not just a predefined parameter space)
- Not distributed (single GPU, single thread, synchronous)

The repo is deliberately minimal — ~630 lines of Python in the files that matter. Karpathy's README leans into this: "The core idea is that you're not touching any of the Python files like you normally would as a researcher. Instead, you are programming the `program.md` Markdown files that provide context to the AI agents and set up your autonomous research org."

[SOURCE: github.com/karpathy/autoresearch README via gh api]

---

### 2. The No Priors Podcast — What Karpathy Actually Said

**Episode:** "Andrej Karpathy on Code Agents, AutoResearch, and the Loopy Era of AI"
**Published:** March 20, 2026 | **Host:** Sarah Guo | **Duration:** ~66 minutes
[SOURCE: podscripts.co/podcasts/no-priors-artificial-intelligence-technology-startups/andrej-karpathy-on-code-agents-autoresearch-and-the-loopy-era-of-ai]

#### The Blockchain Analogy (starting at ~00:33:48)

This is the critical passage. Karpathy is discussing how autoresearch could scale to a distributed, untrusted pool of workers (like SETI@home), and he makes the blockchain analogy *himself* — this is not host projection or pattern-matching:

> "I was more interested in is how you can have an untrusted pool of workers out there on the internet. [...] So you're basically dealing with a similar kind of — it's almost actually like looks a little bit like — my designs that incorporate an untrusted pool of workers actually look a little bit more like a blockchain a little bit, because instead of blocks, you have commits, and these commits can build on each other, and they contain like changes to the code as you're improving it. And the proof of work is basically doing tons of experimentation to find the commits that work, and that's hard. And then the reward is just being on the leaderboard right now. There's no monetary reward whatsoever."

He then explicitly names the computational asymmetry:

> "But I don't want to push the analogy too far, but it fundamentally has this issue where a huge amount of search goes into it, but it's very cheap to verify that a candidate solution is indeed good because you can just train a single — you know, someone had to try 10,000 ideas but you just have to check that the thing that they produced actually works, because the 99,000 of them didn't work."

And the trust architecture:

> "Basically long story short is like you have to come up with a system where an untrusted pool of workers can collaborate with a trusted pool of workers that do the verification. And the whole thing is kind of like asynchronous and works and is like safe from a security perspective because if anyone sends you arbitrary code and you're going to run it that's very sketchy and dodgy."

He concludes with the vision:

> "A swarm of agents on the internet could collaborate to improve LLMs and could potentially even like run circles around Frontier Labs. Like, who knows, you know? [...] Frontier Labs have a huge amount of trusted compute. But the Earth is much bigger and has a huge amount of untrusted compute. But if you put systems in place that deal with this, then maybe it is possible."

#### Assessment of the Fletcher/TIG Pattern-Matching

The question posed was whether Fletcher (TIG founder) is "pattern-matching too aggressively" when he says Karpathy's architecture resembles blockchain — specifically: "commits that build on each other, computational asymmetry (hard to find, cheap to verify), an untrusted pool of workers collaborating through a blockchain-like structure."

**Verdict: Fletcher is accurately describing what Karpathy said.** Karpathy himself used the word "blockchain," himself identified the three structural parallels (commits-as-blocks, proof-of-work-as-experimentation, cheap verification), and himself described the untrusted/trusted worker dichotomy. He even added his own caveat ("I don't want to push the analogy too far").

The one nuance: Karpathy is describing a *future vision* for distributed autoresearch, not the current repo. The released repo is single-GPU, single-agent, fully trusted. The blockchain-like architecture is his design for what comes next — the "SETI@home for ML research" version. Fletcher may be eliding this distinction between the current implementation and the aspirational architecture.

#### Other Notable Concepts from the Podcast

- **"Research org code"**: Karpathy frames `program.md` as describing a research organization — roles, processes, constraints — and envisions a meta-competition where different program.md configurations compete on identical hardware.
- **"Remove yourself as the bottleneck"**: The system's core goal. "Here's an objective, here's a metric, here's your boundaries of what you can and cannot do, and go."
- **Agent skill, not capability**: "When AI agents fail, it's usually a skill issue, not a capability issue." The bottleneck is how you set up the agent, not what the model can do.
- **Macro actions**: "The real shift is working in macro actions. One does research, one writes code, one plans, all running 20-minute tasks simultaneously."

---

### 3. Evolution of the Idea

**Timeline:**
- **Feb 2026:** Karpathy coins the term "vibe coding" (related concept — natural language directing agents rather than writing code directly). [SOURCE: multiple secondary sources]
- **March 6, 2026:** Repo created on GitHub.
- **March 7, 2026:** First tweet announcing the project. Karpathy runs experiments overnight, wakes up to ~50 experiments completed, model improved. [SOURCE: x.com/karpathy/status/2029701092347630069, referenced in README]
- **March 8-9, 2026:** Second tweet with more results: "~650 experiments on depth 12 model transfer well to depth 24 so nanochat is about to get a new leaderboard entry for 'time to GPT-2' too." [SOURCE: Reddit r/singularity thread quoting Karpathy]
- **March 10-15, 2026:** Viral adoption. 21,000+ stars within days. Community forks for macOS, Windows, AMD. [SOURCE: DataCamp, AwesomeAgents]
- **March 17, 2026:** Fortune article coins "The Karpathy Loop" as a term. [SOURCE: fortune.com/2026/03/17/]
- **March 20, 2026:** No Priors podcast appearance. Karpathy describes the distributed/SETI@home vision, blockchain analogy, and "research org code" concept.
- **As of March 25, 2026:** 56K+ stars. Repo still being pushed to (last push: March 26). No major architectural changes to the core three-file structure.

**Post-podcast evolution:** Karpathy has hinted at but not released the distributed version. The current repo remains single-GPU, single-agent, synchronous. The "SETI@home for autoresearch" remains aspirational.

**Key post from Karpathy** (referenced in AwesomeAgents): "autoresearch has to be asynchronously massively collaborative for agents (think: SETI@home style). The goal is not to emulate a single PhD student, it's to emulate a research community of them." [SOURCE: awesomeagents.ai, quoting Karpathy X post]

---

### 4. Community Forks and Extensions

#### Platform Ports (Karpathy-acknowledged in README)

| Fork | Platform | Stars | Notes |
|------|----------|-------|-------|
| miolini/autoresearch-macos | macOS/MPS | 1,614 | Most popular fork |
| trevin-creator/autoresearch-mlx | macOS/MLX | — | Apple Silicon native |
| jsegov/autoresearch-win-rtx | Windows/RTX | 389 | Windows port |
| andyluo7/autoresearch | AMD | 22 | AMD GPU support |

#### Conceptual Extensions

| Project | Author | What's Different |
|---------|--------|-----------------|
| **hwchase17/autoresearch-agents** | Harrison Chase (LangChain) | Applies the loop to **agent optimization**, not ML training. `agent.py` replaces `train.py`. Eval via LangSmith instead of val_bpb. Same keep/discard ratchet. [SOURCE: github.com/hwchase17/autoresearch-agents] |
| **mutable-state-inc/autoresearch-at-home** | mutable-state-inc | 448 stars. Unclear differentiation from main repo. |
| **ncdrone/autoresearch-ANE** | ncdrone | Targets Apple Neural Engine with native Obj-C + private APIs. No GPU required. 46 stars. |
| **kousun12/darwin-derby** | kousun12 | "AI agents running research on anything automatically." Generalized beyond ML. 45 stars. |
| **Reza Rezvani's Claude Code skill** | Medium author | Turned the loop into a Claude Code skill that applies to API speed, headline CTR, prompt quality. Not a fork — a reimplementation as a skill. [SOURCE: alirezarezvani.medium.com] |

**ML Engineer newsletter** (#379) reported someone wiring autoresearch to a 16-GPU Kubernetes cluster: "910 experiments over 8 hours, achieving a 2.87% improvement in validation versus baseline and reaching the same quality roughly 9x faster than a single-GPU sequential setup." [SOURCE: machinelearning.substack.com]

**Shopify CEO Tobi Lutke** adapted it for an internal 0.8B parameter model: 37 experiments over 8 hours, 19% improvement. [SOURCE: AwesomeAgents, DataCamp — not primary-verified against Lutke's original post]

#### Community Criticism (from Reddit)

Informed skeptics note:
- "It's hyperparameter search in a loop. We've had Bayesian optimization and neural architecture search doing this for years. The fact that an LLM is doing the search instead of a Gaussian process doesn't make it 'early singularity.'" [SOURCE: Reddit r/singularity, user No-Understanding2406]
- "The actually interesting question is whether LLMs can propose qualitatively novel architectures vs just tweaking knobs." [SOURCE: same thread]
- "The key limitation: each run starts from zero. The agent has no memory of what it tried before." [SOURCE: Reddit user Ni2021]

These are fair critiques. The counterpoint (from the sameernanda.com analysis) is that AutoResearch is not NAS or Optuna because the search space is unbounded — the agent can modify arbitrary code, not just a predefined parameter grid. Whether this produces *qualitatively* novel architectures in practice is unproven.

---

### 5. How Does Our Adaptation Compare?

**Our script:** `meta/scripts/autoresearch.py` (~950 lines)
**Docstring:** "Adapted from karpathy/autoresearch. Runs an autonomous loop: LLM edits code -> deterministic eval -> keep/discard -> repeat."

#### Structural Comparison

| Feature | Karpathy's autoresearch | Our meta/autoresearch.py |
|---------|------------------------|--------------------------|
| **Loop runner** | None in repo — the *agent itself* is the loop. You point Claude Code at the repo and it runs the loop interactively. | **Explicit Python loop runner.** Our script IS the loop — it orchestrates mutator calls, eval, keep/discard decisions programmatically. |
| **Architecture** | 3 files: prepare.py, train.py, program.md | JSON config + editable files + eval command. Fully config-driven. |
| **Domain** | ML training (val_bpb) | **Domain-agnostic.** Config specifies metric name, direction, eval command. Experiments include `toy-scorer` (accuracy) and `proposal-ranker` (ranking quality). |
| **Agent coupling** | Agent-agnostic but agent IS the loop | **Multi-engine support:** Claude Code, Codex CLI, llmx (non-agentic). Engine selection via config. |
| **Git strategy** | Agent uses git manually (commit/reset) | **Automated git worktree isolation.** Creates disposable worktrees per run (`autoresearch/{tag}` branches). |
| **Telemetry** | `results.tsv` (agent-maintained) | **Append-only ExperimentLog** with JSONL + TSV + archived patches per experiment. Patch hashes, cost tracking, timing. |
| **Memory** | None (agent has no cross-experiment memory beyond what's in the git log) | **LEARNINGS.md auto-generation** every N experiments — summarizes discarded experiments to prevent repetition. Also feeds last N kept diffs into prompts. |
| **Stall detection** | None | Tracks consecutive discards. After threshold (default 3), the prompt naturally pushes "try something radically different." |
| **Holdout eval** | None | **Periodic holdout evaluation** on a separate eval command every K keeps, to check generalization. |
| **Cost tracking** | None | Tracks cost per experiment, total cost, budget cap ($2 default). Stops on billing errors. |
| **Timing probe** | None | First experiment is a timing probe — measures mutator latency and auto-adjusts timeout. |
| **Progress viz** | progress.png (presumably from a notebook) | **ASCII progress chart** with running best, top improvements, keep/discard/crash counts. |
| **CLI** | None (agent-driven) | Full CLI: `run`, `results`, `progress` subcommands with filtering. |

#### Faithfulness Assessment

**Core loop: Faithful.** The fundamental mechanism — LLM proposes code edit, deterministic eval runs, keep if improved / git reset if not, repeat — is identical. This is the "Karpathy Loop" pattern preserved exactly.

**Key divergences:**

1. **Our script is the orchestrator; Karpathy's repo has no orchestrator.** This is the biggest architectural difference. In Karpathy's design, the agent IS the loop — you point Claude Code at the repo and it reads program.md and runs the cycle. In our version, the Python script drives the loop and the LLM is a "mutator" — called once per iteration to propose an edit, then the script handles eval, keep/discard, logging. This is a deliberate design choice that enables multi-engine support (Claude, Codex, llmx) and deterministic loop behavior.

2. **Domain generalization.** Karpathy's repo is purpose-built for ML training. Our version abstracts the domain away via config: any eval command that outputs a metric can be optimized. The `toy-scorer` and `proposal-ranker` experiments demonstrate this — neither involves ML training.

3. **Memory/learning accumulation.** Karpathy's version has no cross-experiment memory. Our version auto-generates LEARNINGS.md summarizing failed approaches, feeds recent results and kept diffs into the mutator prompt, and tracks experiment history in structured JSONL. This directly addresses the Reddit critique ("each run starts from zero").

4. **Worktree isolation.** Karpathy's approach: agent works on a git feature branch in the same repo. Our approach: disposable git worktrees, so experiments don't interfere with the main working directory. More robust for cases where the target repo is actively used.

5. **Holdout evaluation.** Our version periodically runs a separate holdout eval to check generalization — a standard ML practice that Karpathy's minimal design omits.

**What we don't have that Karpathy's design offers:**
- The elegance of "the agent IS the loop." Our orchestrator approach is more robust but loses the simplicity of just pointing an agent at a repo.
- The `program.md` as "research org code" framing. Our config is mechanical (metric name, direction, files); Karpathy's program.md carries research *strategy* in natural language.

**Verdict:** Our adaptation is a **production hardening** of the Karpathy Loop pattern, not a faithful reproduction. It preserves the core mechanism (mutate → eval → ratchet) while adding the infrastructure a real system needs: multi-engine support, cost controls, experiment telemetry, memory, holdout validation, worktree isolation, and CLI tooling. The tradeoff is complexity (950 lines vs. Karpathy's 630-line train.py + agent-as-orchestrator) in exchange for robustness and domain generality.

---

### What's Uncertain

1. **Whether the distributed/SETI@home vision will materialize.** Karpathy described it on the podcast but has not released code. The trust/verification architecture he sketched is conceptual.
2. **Whether LLM-as-mutator produces qualitatively novel architectures or just tweaks knobs.** The Reddit skeptics raise a valid point. Documented improvements (missing QKnorm scaler, better learning rates) are competent but not paradigm-shifting.
3. **Shopify's 19% improvement claim** is widely cited but I could not find Lutke's original post to verify the exact claim. [UNVERIFIED — secondary sources only]
4. **Whether our LEARNINGS.md approach actually prevents repetition better than the agent's native context window.** Untested hypothesis.

### Disconfirmation Search

Searched for: "autoresearch failed," "autoresearch limitations," "autoresearch criticism"

- Reddit skeptics argue it's "fancy Optuna with worse sample efficiency" [SOURCE: r/singularity]
- DifferencePublic7057 on Reddit: "Still needs hand holding. Sometimes Deepseek can one shot something complex, but it's usually less than 70%. One error or slightly incorrect output can break the chain."
- The New Stack article notes the boundary: "The domains where autonomous loops struggle (legal reasoning, strategic planning, creative work, medical diagnosis) aren't struggling because AI can't generate good candidates. They're struggling because checking whether a candidate is good still requires expensive human judgment."
- No reports of catastrophic failures or fundamentally broken results. The ratchet design (only keep improvements) makes the failure mode "no progress" rather than "regression."

### Search Log

| # | Tool | Query | Hits |
|---|------|-------|------|
| 1 | gh api | repos/karpathy/autoresearch metadata | 1 (repo exists, 56K stars) |
| 2 | Exa web_search | "Karpathy autoresearch project..." | 10 (Fortune, Reddit, DataCamp, NewStack, Medium, GitHub, sameernanda, mindstudio, abhs.in, Medium #2) |
| 3 | Brave web_search | "Karpathy No Priors podcast autoresearch blockchain" | 10 (podscripts.co, Reddit, blockchain.news, glenrhodes.com, Apple Podcasts, Reddit, ML Engineer, X posts) |
| 4 | WebFetch | podscripts.co full transcript | Partial — got architecture overview but not blockchain passage |
| 5 | WebFetch | podscripts.co (targeted blockchain passage) | Indeterminate — summarizer couldn't locate it |
| 6 | Exa web_search | "Karpathy autoresearch blockchain analogy commits untrusted workers" | 5 (sameernanda, NewStack, YouTube, podscripts.co, podscan.fm) — **Found exact transcript with blockchain quote** |
| 7 | gh api | forks sorted by stars | 10 forks returned |
| 8 | Exa web_search | "autoresearch-agents Chase agent optimization fork" | 8 (GitHub main, hwchase17/autoresearch-agents, substack, Medium x2, YouTube, GitHub mirror, AwesomeAgents) |
| 9 | Read | meta/scripts/autoresearch.py (4 reads, full file) | Complete source review |
| 10 | Glob + Read | meta/experiments/ configs | toy-scorer and proposal-ranker configs |

<!-- knowledge-index
generated: 2026-03-26T04:45:42Z
hash: 86600b043bf8

table_claims: 8

end-knowledge-index -->
