---
title: Karpathy/autoresearch — Implementation-Level Deltas vs Our Adaptation
date: 2026-05-26
---

# Karpathy/autoresearch — Implementation-Level Deltas vs Our Adaptation

**Question:** Beyond the architectural comparison already in [[karpathy-autoresearch-deep-dive]] (2026-03-25), what specific implementation patterns, code idioms, and prompt-engineering moves are present in karpathy/autoresearch that our `scripts/autoresearch.py` does not have? Read every file end-to-end.

**Tier:** Deep | **Date:** 2026-05-26
**Scope:** All eight files in the repo as of commit on 2026-03-26 — `README.md`, `program.md`, `prepare.py`, `train.py`, `analysis.ipynb`, `pyproject.toml`, `.python-version`, `.gitignore`.

## Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Repo is 8 files total; ~630 LoC across the three "files that matter" | `gh api repos/karpathy/autoresearch/contents/` | HIGH | [SOURCE: GitHub Contents API] | VERIFIED |
| 2 | `.gitignore` ignores `worktrees/`, `queue/`, `CLAUDE.md`, `AGENTS.md` with a comment "Agent prompt files (generated per-session by launchers)" | `.gitignore` lines 12-20 | HIGH | [SOURCE: .gitignore] | VERIFIED |
| 3 | `program.md` contains a literal "NEVER STOP" autonomy clause | program.md final section | HIGH | [SOURCE: program.md] | VERIFIED |
| 4 | `train.py` uses `gc.freeze(); gc.disable()` after step 0 to avoid ~500ms GC stalls | train.py:593-596 | HIGH | [SOURCE: train.py] | VERIFIED |
| 5 | `train.py` excludes JIT compile + warmup from time budget via `if step > 10` | train.py:578-579 | HIGH | [SOURCE: train.py] | VERIFIED |
| 6 | `train.py` fast-fails on exploded/NaN loss with `if loss > 100 or NaN: exit(1)` | train.py:570-572 | HIGH | [SOURCE: train.py] | VERIFIED |
| 7 | BPB metric is vocab-size-independent — designed so architecture+tokenizer changes are fairly comparable | prepare.py docstring of `evaluate_bpb` | HIGH | [SOURCE: prepare.py:343-365] | VERIFIED |
| 8 | Dataloader does best-fit document packing with BOS alignment, 100% utilization no padding | prepare.py `make_dataloader` docstring | HIGH | [SOURCE: prepare.py:276-282] | VERIFIED |
| 9 | Our `scripts/autoresearch.py` is 950+ LoC vs karpathy's 630 LoC of target+harness | `wc -l scripts/autoresearch.py` | HIGH | [SOURCE: local file] | VERIFIED |
| 10 | Our adaptation already includes worktree isolation, holdout eval, duplicate patch detection, LEARNINGS.md, cost tracking, multi-engine mutator | Direct code read of scripts/autoresearch.py | HIGH | [SOURCE: scripts/autoresearch.py] | VERIFIED |

---

## 1. File-by-file inventory

| File | LoC | Owner | Purpose |
|------|-----|-------|---------|
| `README.md` | 8.0 KB | Human | Design rationale, fork links, hardware tuning recipe, MIT license |
| `program.md` | 7.0 KB | Human (iterated) | "Research org code" — instructions to the agent including the LOOP FOREVER block |
| `prepare.py` | 15.0 KB | Fixed (read-only) | Data download, BPE tokenizer training, `evaluate_bpb`, BOS-aligned packing dataloader |
| `train.py` | 26.2 KB | Agent (only file the agent edits) | Full GPT model, Muon+AdamW optimizer, training loop |
| `analysis.ipynb` | 8.2 KB | Human (offline) | pandas+matplotlib over `results.tsv` |
| `pyproject.toml` | 0.5 KB | Human | uv config, torch from `pytorch-cu128` index |
| `.python-version` | 5 B | Human | `3.10` |
| `.gitignore` | 0.3 KB | Human | Includes a launcher-pattern signal |

## 2. Architectural / framing deltas (the genuinely interesting set)

### 2.1 "Agent IS the loop" mode

In Karpathy's design there is no Python orchestrator at all. The human runs Claude Code (or Codex) interactively against the repo; the agent reads `program.md`, edits `train.py`, runs `uv run train.py > run.log 2>&1`, greps `val_bpb`, records to `results.tsv`, and decides itself whether to `git commit` (advance) or `git reset --hard HEAD~1` (discard). The "loop" lives in the agent's persistent reasoning, not in code.

Our `scripts/autoresearch.py` always runs the loop in Python and calls the LLM as a one-shot mutator per turn. This is more robust (deterministic loop control, structured logging, cost caps, no risk of the agent rewriting the loop itself) but loses the elegance of "point an agent at a directory."

**Implication:** an `--agent-driven` mode that writes a `program.md` into the worktree and exits, letting the operator point Claude Code at it, would close this gap and unlock the launcher pattern below.

### 2.2 `program.md` as the artifact you iterate on

Karpathy's pitch is that the human *programs the agent's instructions*, not the target code. Each `program.md` is a "research org configuration" — what roles exist, what's editable, what's read-only, when to commit, when to give up, when to never stop. The implicit roadmap is a meta-competition where different `program.md` files compete on identical hardware.

Our config is mechanical: `metric_name`, `metric_direction`, `editable_files`, `eval_command`. The `program_md` field exists as a static input but isn't framed as the primary tuning surface.

### 2.3 The launcher pattern hidden in `.gitignore`

The `.gitignore` includes:

```
worktrees/
results/
queue/

# Agent prompt files (generated per-session by launchers)
CLAUDE.md
AGENTS.md
```

This implies infrastructure that does not appear in the repo itself:
- A **launcher** that generates `CLAUDE.md` / `AGENTS.md` per session (transient, ignored). Likely tailors per-agent instructions per-worktree.
- A **`worktrees/` directory** for parallel runs.
- A **`queue/` directory** suggesting some task-queue convention — possibly for multiple parallel autoresearch agents pulling from a shared task list.
- A **`results/`** rollup directory aggregating per-worktree TSVs.

None of this is in our adaptation. Karpathy probably runs `N` agents in parallel against `N` worktrees with `N` per-session prompt files, all writing into a shared `results/` rollup. The repo doesn't ship this layer publicly, but the `.gitignore` reveals the architecture.

### 2.4 "NEVER STOP" clause inside `program.md`

The final section of `program.md` is a hard autonomy instruction:

> Once the experiment loop has begun (after the initial setup), do NOT pause to ask the human if you should continue. Do NOT ask "should I keep going?" or "is this a good stopping point?". The human might be asleep, or gone from a computer and expects you to continue working *indefinitely* until you are manually stopped. You are autonomous. If you run out of ideas, think harder — read papers referenced in the code, re-read the in-scope files for new angles, try combining previous near-misses, try more radical architectural changes. The loop runs until the human interrupts you, period.

This is a load-bearing instruction. It rules out the failure mode where an agent halts after a streak of discards and asks for permission. Our prompt has no such clause; we don't need one in orchestrator mode because the Python loop controls termination, but for an `--agent-driven` mode it would be essential.

### 2.5 Simplicity criterion baked into the prompt

```
A 0.001 val_bpb improvement that adds 20 lines of hacky code? Probably not worth it.
A 0.001 val_bpb improvement from deleting code? Definitely keep.
An improvement of ~0 but much simpler code? Keep.
```

Karpathy explicitly counter-weights metric improvement against code complexity. Our prompt is purely metric-greedy ("Propose ONE change to improve {metric}"). This is a deliberate move to avoid the obvious failure mode of autoresearch: monotonic increase in code complexity per iteration.

### 2.6 VRAM as a *soft* constraint

> **VRAM** is a soft constraint. Some increase is acceptable for meaningful val_bpb gains, but it should not blow up dramatically.

The notion that some constraints are soft (degrade gracefully) and others are hard (eval crashes) doesn't exist in our config. Adding a `soft_constraints` field that the mutator is told about — but isn't enforced by eval — is cheap and useful in any optimization setting where the secondary metric matters but isn't the objective.

### 2.7 Output-format contract

`train.py` prints a deterministic block at the end:

```
---
val_bpb:          0.997900
training_seconds: 300.1
total_seconds:    325.9
peak_vram_mb:     45060.2
mfu_percent:      39.80
total_tokens_M:   499.6
num_steps:        953
num_params_M:     50.3
depth:            8
```

The `---` sentinel marks the start of the report. `grep "^val_bpb:" run.log` is the entire extraction protocol. Our `run_eval` uses a regex over the full output; karpathy's structured block is easier to extend with secondary metrics. Also: log output redirected with `> run.log 2>&1` rather than `tee` "so you don't flood your context" — our orchestrator already doesn't capture eval output verbosely, but the principle is worth surfacing in any agent-driven mode.

---

## 3. Training-harness craftsmanship (only matters if we ever point autoresearch at ML training)

These are tricks in `train.py` that aren't directly transferable to non-ML targets but are worth knowing as a corpus.

### 3.1 Combined optimizer with state-of-the-art tricks
- **Muon + AdamW** in one optimizer (`MuonAdamW`). Muon for 2D matrix params, AdamW for embeddings, lm_head, scalars.
- **Polar Express orthogonalization** — five-tuple coefficients drive Newton-Schulz-style iteration for orthogonalizing gradients.
- **NorMuon variance reduction** — second-moment buffer per dimension keeps the orthogonalized step well-scaled.
- **Cautious weight decay mask** — `mask = (g * params) >= 0`; only decay where gradient and parameter agree in sign. Avoids fighting the optimizer's pull.

### 3.2 Architecture details worth knowing exist
- **Value embeddings (ResFormer)** with input-dependent sigmoid gates per head, applied on alternating layers (`has_ve(i, n_layer)`).
- **Sliding-window attention** with configurable pattern (`"SSSL"` = short-short-short-long).
- **Softcap logits** — `softcap * tanh(logits / softcap)` with `softcap=15` to bound logits.
- **ReLU² MLP** (`F.relu(x).square()`).
- **RMS norm** (`F.rms_norm`) at every residual + on q/k.

### 3.3 Throughput tricks
- **GC freeze:** `gc.collect(); gc.freeze(); gc.disable()` after step 0. Manual `gc.collect()` every 5000 steps. Avoids ~500ms GC stalls during steady-state training. **This pattern is broadly useful for any tight Python loop, not just ML.**
- **Time budget excludes compile/warmup:** `if step > 10: total_training_time += dt`. Without this, JIT compilation eats the budget. **Applicable to any timed-eval setting.**
- **Fast-fail on NaN / explosion:** `if loss > 100 or NaN: exit(1)`. **The general principle — terminate eval early on a pathological intermediate signal — is applicable to any eval where the agent can recognize "this run is doomed" before the budget expires.**
- **Pre-allocated CPU/GPU buffers with `pin_memory=True` + `non_blocking=True`** dataloader copy.
- **`torch.compile(dynamic=False, fullgraph=True)`** on optimizer steps.

### 3.4 Eval-harness invariants
- **BPB (bits per byte), not CE loss.** Vocab-size-independent, so an agent that changes the tokenizer or vocab size still gets a fair comparison. The general principle: **metric must be substrate-independent** w.r.t. the things the agent can change. Our configs don't enforce this; it's left to whoever writes the eval command.
- **Pinned validation shard** — shard 6542, held out from BPE training and dataloader. Strict train/val separation enforced in the *data layer*, not the eval loop.
- **BOS-aligned best-fit packing** — every row starts with BOS, documents packed largest-fits-first into remaining space, shortest doc cropped only when nothing fits. 100% token utilization, no padding.
- **Special tokens excluded from byte count** in BPB so they can't be gamed.

### 3.5 What we don't currently exercise

We have no ML-training experiment in `experiments/`. The current configs (`toy-scorer`, `proposal-ranker`, `claim-bench`) optimize accuracy/ranking metrics over fast deterministic evals. None of section 3 transfers unless we add an ML target.

---

## 4. Analysis / ergonomics deltas

### 4.1 `analysis.ipynb`

Five analysis sections in pandas+matplotlib:
1. Load TSV, summary head.
2. Outcome counts + keep rate.
3. List all KEPT experiments inline.
4. **Val BPB over time** scatter: discarded as faint gray dots, kept as prominent green dots with black edges, running-minimum step line.
5. Summary stats: baseline, best, total improvement, cumulative effort per improvement.
6. **Top hits by delta** — sorted by `prev_bpb - val_bpb`, biggest individual gain first.

Our `print_progress` covers (2)-(5) in ASCII. The "top hits by delta" view is genuinely useful and missing from ours; the scatter plot is purely cosmetic.

### 4.2 README "hardware tuning recipe"

The README contains a 7-point recipe for porting to smaller hardware:
1. Use lower-entropy dataset (tinystories).
2. Decrease `vocab_size` (8192 → 4096 → 2048 → 1024 → 256 byte-level).
3. Lower `MAX_SEQ_LEN` (to e.g. 256). Compensate by raising `DEVICE_BATCH_SIZE`.
4. Decrease `EVAL_TOKENS` so val eval is cheaper.
5. Lower `DEPTH` (8 → 4).
6. Use `WINDOW_PATTERN = "L"` (avoid banded attention on small models).
7. Lower `TOTAL_BATCH_SIZE` to powers of 2 (down to ~16K).

The pattern is worth keeping even outside ML: **every autoresearch experiment config should document its "shrink for fast iteration" knobs** — the orthogonal axes you can dial down to iterate in seconds rather than minutes.

### 4.3 README "notable forks"

Karpathy maintains a curated fork list in README. Five forks linked: macOS (miolini), MLX (trevin-creator), Windows RTX (jsegov), AMD (andyluo7), and implicitly more via the deep-dive memo. Tracking downstream adaptation is itself a signal — "what kinds of hardware/domains do people want this for" is information we'd lose if we never surfaced our own adaptations publicly.

---

## 5. What we have that karpathy doesn't (for completeness)

For symmetry with the rest of this memo — already covered in the prior deep-dive but worth listing:

- Worktree isolation + auto-cleanup (we have `.autoresearch-worktrees/`; karpathy has the launcher-pattern `worktrees/` but it's not in-repo)
- Multi-engine mutator: Claude Code, Codex CLI, llmx (non-agentic)
- Holdout eval with retroactive discard on >1.5x divergence
- SHA-hash duplicate-patch detection (skip without eval if patch already tried)
- Auto-generated `LEARNINGS.md` summarizing discards every 10 experiments
- Seed implementations (evaluate known baselines before mutation begins)
- Cost tracking per experiment, budget cap, billing-error fatal stop
- Reproducibility receipt amended into each kept commit (config hash, prev best, cost, elapsed)
- Timing probe on first experiment with auto-adjusted mutator timeout
- Stall detection (`consecutive_discards >= 3`)
- ASCII progress chart
- Three CLI subcommands: `run`, `results`, `progress`
- Domain-agnostic via JSON config

---

## 6. Ranked port recommendations

| # | Item | Value | Cost | Recommendation |
|---|------|-------|------|----------------|
| 1 | **`--agent-driven` mode** writing `program.md` + `LOOP FOREVER` clause to the worktree, then exiting so the operator points Claude Code at it | HIGH — unlocks the elegance of "point an agent at a dir" and matches karpathy's framing | ~50 LoC | DO |
| 2 | **Simplicity criterion + NEVER-STOP clause** in mutator prompt | HIGH — counter-weights complexity creep | ~5 LoC | DO |
| 3 | **Fast-fail predicate** in eval config — eval command can short-circuit on pathological intermediate signal so budget isn't wasted | MEDIUM — speeds iteration when most variants are bad | ~20 LoC | DO |
| 4 | **"Top hits by delta" view** in `print_progress` and a per-experiment `analysis.ipynb` template | MEDIUM — better offline review for kept-experiment ranking | ~30 LoC | DO |
| 5 | **Structured `---`-delimited eval output block** convention in experiment templates | LOW-MEDIUM — easier to add secondary metrics (mfu, peak_vram-equivalents) | ~5 LoC + template doc | DO if writing new experiments |
| 6 | **`soft_constraints` config field** the mutator is told about but eval doesn't enforce | LOW-MEDIUM — useful for multi-objective settings | ~10 LoC | DEFER until needed |
| 7 | **GC-freeze pattern in any tight Python loop** we run repeatedly | LOW — only matters if we have eval inner loops that aren't already C-extension-bound | ~3 LoC where applicable | OPPORTUNISTIC |
| 8 | **Launcher / `queue/` pattern** for parallel autoresearch | SPECULATIVE — only matters if we run multi-agent autoresearch against shared targets | ~200 LoC | DEFER until we have a use case |
| 9 | **ML training experiment** as a target (port `train.py` + `prepare.py` into `experiments/ml-train/`) | LOW for our current goals — we don't optimize ML models | ~700 LoC port | SKIP unless someone wants this |

Items 1-4 are cheap and worth doing in one pass.

---

## What's Uncertain

1. **Whether `--agent-driven` mode is worth the maintenance burden** alongside our orchestrator-driven mode. Two ways to invoke autoresearch doubles surface area. Possible mitigation: orchestrator-driven mode generates the same `program.md` and just chooses to call the LLM itself rather than handing off. Untested.
2. **Whether NEVER-STOP prompt clauses actually work against current frontier models.** Claude Sonnet 4.6 / Opus 4.7 may already be sufficiently non-sycophantic that the clause is redundant. Worth probing with a short run before assuming the clause is load-bearing.
3. **Whether the simplicity criterion measurably reduces complexity creep over a 100-experiment run.** No data. Would need an ablation between "metric only" and "metric + simplicity" prompts on the same target.
4. **The actual launcher pattern.** We can only infer it from `.gitignore`. Karpathy hasn't published the launcher code.

---

## Disconfirmation Search

Looked for: prior reviews of karpathy/autoresearch implementation details we might have missed.

- The prior deep-dive memo [[karpathy-autoresearch-deep-dive]] (2026-03-25) is the most thorough we have; it covers podcast claims, fork ecosystem, distributed-vision blockchain analogy, and 12-row structural feature comparison. It does **not** cover: GC freeze, time-budget-excludes-compile, fast-fail-on-explosion, BPB substrate-independence rationale, BOS packing, the `.gitignore` launcher signal, the structured `---` output convention, the simplicity criterion in `program.md`, the NEVER-STOP clause, or the VRAM-as-soft-constraint framing. This memo adds those.
- The earlier [[autoresearch-analysis]] (2026-03-08) is a top-level pattern summary, not an implementation-level read.
- No published critique I found goes deeper than "it's LLM-driven hyperparameter search" or "fancy Optuna." The implementation craft is undersold in public discussion.

## Search Log

| # | Tool | Query | Hits |
|---|------|-------|------|
| 1 | gh api | `repos/karpathy/autoresearch/contents/` | 8 files inventoried |
| 2 | gh api | per-file content fetches for all 8 files | All 8 contents retrieved to `/tmp/autoresearch-karpathy/` |
| 3 | Read (line-by-line) | prepare.py:1-390 | Full read, focus on `evaluate_bpb`, `make_dataloader`, BPE training |
| 4 | Read (line-by-line) | train.py:1-631 | Full read, focus on optimizer, GC, fast-fail, time-budget gating |
| 5 | python3 -c json.load | analysis.ipynb cells | All 11 cells inspected |
| 6 | Read | program.md | Full read, NEVER-STOP and simplicity clauses identified |
| 7 | Read | README.md | Full read, hardware tuning recipe + forks |
| 8 | cat | `.gitignore`, `pyproject.toml`, `.python-version` | Launcher signal identified |
| 9 | Read | scripts/autoresearch.py:1-980 | Full read for delta accounting |
| 10 | grep | `autoresearch` in `~/Projects/agent-infra/{skills,decisions,research}` | Existing memos found |
| 11 | Read | research/karpathy-autoresearch-deep-dive.md (full) | Cross-checked to avoid duplicating prior coverage |

## Revisions

- 2026-05-26: Initial memo. Supplements [[karpathy-autoresearch-deep-dive]] (2026-03-25) with implementation-level details from a full file-by-file re-read.

<!-- knowledge-index
generated: 2026-05-26T10:02:22Z
hash: 5ee22b8c461f

index:title: Karpathy/autoresearch — Implementation-Level Deltas vs Our Adaptation
cross_refs: research/karpathy-autoresearch-deep-dive.md
table_claims: 10

end-knowledge-index -->
