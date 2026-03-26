---
title: TIG Monorepo Architecture — Deep Dive
date: 2026-03-25
---

## TIG Monorepo Architecture — Deep Dive

**Question:** What is the actual system architecture of tig-foundation/tig-monorepo?
**Tier:** Deep | **Date:** 2026-03-25
**Sources:** GitHub API (gh api) reading of actual source code; 13 source files read directly.

---

### 1. Protocol Mechanics

**Source:** `tig-protocol/src/contracts/` — `rewards.rs`, `benchmarks.rs`, `opow.rs`, `algorithms.rs`, `context.rs`

#### Rounds and Blocks

The protocol operates on a **round-based block system**. Each round contains `config.rounds.blocks_per_round` blocks. Key state transitions (merges, advance votes, cutoff phase-ins) happen at round boundaries — specifically at the last block of each round: `(block_details.height + 1) % config.rounds.blocks_per_round == 0`.

Blocks are the atomic unit. Every block triggers a full state update cycle:
1. OPoW update (cutoffs, qualifiers, influence)
2. Algorithm update (adoption, merge points, merges, advance votes)
3. Rewards update (emission distribution)

#### Reward Calculation (`rewards.rs`)

Emissions follow a **schedule-based model** with a gamma scaling factor:

```
gamma = a * (1 - b * exp(-c * num_active_challenges))
block_reward = schedule[round].block_reward
scaled_reward = block_reward * gamma
```

Gamma scales with the number of active challenges — more challenges = higher effective rewards. This creates an incentive to expand the challenge set.

The reward pool is split across **six emission types**:
- **Code** — for algorithm code contributors (proportional to adoption)
- **Advance** — for algorithmic "advances" (IP/method contributions, proportional to adoption)
- **Benchmarker** — for compute providers (proportional to influence)
- **Delegator** — for token stakers who delegate to benchmarkers
- **ChallengeOwner** — fixed pool for challenge creators
- **Bootstrap** — unused code/advance rewards (adoption below threshold)
- **Vault** — everything else (protocol treasury)

**Adoption measurement** is the core economic mechanism. Per-challenge, each algorithm's adoption is calculated as:

```
For each algorithm in a challenge:
  weight = sum over (benchmarkers using it):
    benchmarker.influence * (qualifiers_from_this_algo / benchmarker_total_qualifiers)
  adoption = normalize(weights)  // sums to 1.0 per challenge
```

Adoption must exceed `config.codes.adoption_threshold` (or be merged) to earn rewards. This means an algorithm only gets paid if benchmarkers actually choose to run it at scale.

#### The OPoW System (`opow.rs`)

"Optimisation Proof of Work" — the core consensus mechanism. This is **not** hash-based PoW. Instead:

1. **Benchmarkers submit solutions** to optimization challenges
2. **Cutoff system**: Each benchmarker's cutoff = `min_bundles_across_challenges * cutoff_multiplier`. This forces balanced participation across ALL active challenges — you can't farm a single easy challenge.
3. **Qualifier selection**: Bundles (groups of nonces) are sorted by quality, then assigned across tracks using a round-robin-with-cutoff algorithm. Better solutions = more qualifiers.
4. **Influence calculation**: A multi-factor weighted average:
   - Per-challenge qualifier share (weighted by phase-in for new challenges)
   - Self-deposit share (weighted by deposit amount)
   - Delegated deposit share
   - **Imbalance penalty**: `influence *= approx_inv_exp(imbalance_multiplier * imbalance)` where imbalance is the variance-to-mean ratio of factors. This penalizes benchmarkers who are strong in one factor but weak in others.
   - **Legacy multiplier**: Newer algorithms get a slight advantage (anti-incumbency)

5. **Deposit-to-qualifier cap**: `max_deposit_to_qualifier_ratio` prevents whale staking from dominating without actual compute contribution.

#### Advance/Code Lifecycle (`algorithms.rs`)

Two-track system:
- **Code** = compiled algorithm implementation (Rust .so files). Submitted with source code. Gets compiled, binary deployed.
- **Advance** = algorithmic method/IP. Submitted with evidence. Goes through a voting process.

Lifecycle:
1. Submit code/advance (requires fee payment from player balance)
2. Code gets compiled → binary submitted
3. Benchmarkers choose algorithms to run
4. Adoption accumulates based on benchmarker influence × qualifier ratio
5. **Merge**: At round end, the algorithm with the most merge_points (above threshold) gets "merged" — its adoption threshold drops to 0, guaranteeing continued rewards as long as anyone uses it.

Advance voting: Weighted by locked deposits with a time horizon. Passes if `yes / (yes + no) >= min_percent_yes_votes`.

#### Benchmark Submission Flow (`benchmarks.rs`)

A three-phase commit:

1. **Precommit** — Declare intent: choose challenge, algorithm, track, fuel budget, num_bundles. Pay fee. A random track is selected from the challenge's active tracks (seeded). A random hash is generated.
2. **Benchmark** — Submit results: merkle root over all nonce outputs + solution quality vector. Protocol randomly samples nonces for spot-checking (samples stratified: some above-average, some below-average quality).
3. **Proof** — Submit merkle proofs for sampled nonces. If merkle proof doesn't verify, an "allegation" (fraud flag) is recorded.

Quality types: **Continuous** (median of bundle) or **Binary** (mean of bundle). Bundles below `min_active_quality` are discarded.

---

### 2. Challenge Implementation

**Source:** `tig-challenges/src/knapsack/mod.rs`, `tig-challenges/src/neuralnet_optimizer/mod.rs`

#### Challenge IDs and Types

7 challenges: c001-c007. CPU challenges: c001 (satisfiability), c002 (vehicle_routing), c003 (knapsack), c007 (hypergraph). GPU challenges: c004, c005, c006 (includes neuralnet_optimizer).

#### Knapsack Challenge (c003) — CPU

**Not a standard knapsack.** This is a **team formation / quadratic knapsack** with interaction values:

- **Instance generation**: Simulates a project-participant assignment scenario.
  - 30,000 projects divided into lognormal-sized subsets
  - n_items participants, each assigned projects from a random subset + spillover
  - **Interaction values** = Jaccard similarity × 1000 between participant project sets
  - Individual values are all 0 — ALL value comes from pairwise interactions
  - Weights uniform [1, 10]
  - Budget = track.budget% of total weight

- **Verification**: Check no duplicates, weight within budget, compute `sum(values[i]) + sum(interaction_values[i][j])` for all selected pairs. O(n^2) in selected items — cheap relative to solving.

- **Quality evaluation**: `quality = (total_value - sota_baseline) / sota_baseline`, clamped to [-10, 10], multiplied by QUALITY_PRECISION. Currently the SOTA baseline equals the greedy baseline (tabu search), so any improvement over tabu search scores positively.

- **Asymmetry**: Generating an instance is O(n^2) for Jaccard computation. Verifying a solution is O(k^2) where k is number of selected items. But SOLVING optimally is NP-hard (quadratic knapsack). The interaction structure (Jaccard similarities from project overlaps) creates complex dependencies that defeat greedy approaches.

#### Neural Network Optimizer Challenge (c004-c006) — GPU

**A genuine ML optimization challenge**: Given a randomly generated regression dataset (Random Fourier Features → noisy targets), train a neural network using your custom optimizer. The challenge provides the training harness; you write the optimizer.

- **Instance generation** (runs on GPU):
  - Generates RFF (Random Fourier Features) parameters from seed
  - Creates dataset: 1000 train, 200 validation, 250 test samples
  - 1D input → 2D output, via RFF with noise_std=0.2
  - Track parameter: n_hidden (number of hidden layers)
  - Fixed architecture: 256 hidden units, batch_size=128, max_epochs=1000, patience=50

- **The optimizer interface** (what competitors implement):
  - `optimizer_init_state(seed, param_sizes, stream, module, prop)` — initialize CUDA state
  - `optimizer_query_at_params(state, params, epoch, losses)` — optional parameter perturbation before forward pass
  - `optimizer_step(state, params, gradients, epoch, losses)` — compute parameter updates from gradients

- **Quality evaluation**: `quality = (epsilon_star_squared - avg_test_loss) / epsilon_star_squared` where epsilon_star = baseline noise. Positive means you beat the noise floor.

- **Asymmetry**: Training loop runs thousands of forward/backward passes. Verification: run inference on test set (single forward pass) + compute loss. Orders of magnitude cheaper.

---

### 3. Algorithm Submission Quality

**Source:** `tig-algorithms/src/knapsack/fast_and_furious/mod.rs`, `tig-algorithms/src/vehicle_routing/hgs_v1/mod.rs`, `tig-algorithms/src/neuralnet_optimizer/neural_alchemist/`

#### fast_and_furious (Knapsack) — Genuine Algorithmic Sophistication

~600 lines of Rust. This is **not trivial**. It implements:

1. **Initial solution construction**: Weight-sorted greedy → iterated density-sorted refinement with convergence detection
2. **Windowed structure**: Items partitioned into locked/core/rejected zones based on density ranking. Only core items participate in expensive operations.
3. **DP refinement**: A proper integer programming step — solves a bounded knapsack DP over the core window items to find optimal selection. Uses cached DP/choose arrays.
4. **Variable Neighborhood Descent (VND)**: Four move operators:
   - Best-add (fill slack capacity)
   - Same-weight swap (equal weight items, O(1) weight change)
   - Reduce-weight swap (reduce total weight, limited diff)
   - Increase-weight swap (use slack, best value/weight ratio)
5. **Multi-strategy perturbation**: 6 different destroy heuristics (by contribution, weight, synergy, density, density×weight², usage-penalized). Adaptive strength increases with stall count.
6. **Greedy reconstruction**: 6 matching reconstruction strategies
7. **Hyperparameters**: Exposed via JSON (n_perturbation_rounds, perturbation_strength_base)

The algorithm uses `unsafe` pointer arithmetic for the inner loops (contribution updates), BTreeMap for weight-bucketed item lookup, and snapshot/restore for perturbation rollback. The author clearly understands metaheuristics (ILS/VND/perturbation), operations research (DP for subset selection), and Rust performance optimization.

#### hgs_v1 (Vehicle Routing) — Multi-File Academic Implementation

The mod.rs is just a thin wrapper, but the algorithm is split across 9 submodules:
- `constructive.rs`, `genetic.rs`, `individual.rs`, `loader_tig.rs`, `local_search.rs`, `params.rs`, `population.rs`, `problem.rs`, `sequence.rs`, `solver.rs`

This is a Hybrid Genetic Search (HGS) implementation — a well-known VRPTW metaheuristic from Vidal et al. (2012, 2022). The multi-file structure and naming conventions suggest either an adaptation of an academic codebase or someone deeply familiar with the HGS framework. **This is graduate-level operations research.**

#### neural_alchemist (Neural Net Optimizer) — Custom GPU Optimizer

The Rust side implements a **"DualPhaseConsensusState"** optimizer with:
- Per-layer learning rates (seeded random initialization in ranges by layer size)
- Spectral boost scheduling (cosine with warmup)
- Fisher information tracking
- Error feedback (EF) compression with lookahead
- Layer-type-specific tuning (BN boost, output damping)
- Noise injection (variance parameter)

The CUDA kernels are sophisticated:
- `dual_consensus_fisher_kernel`: A custom Adam variant that blends adaptive (Adam), normalized, and sign-based updates with Nesterov momentum, Fisher-adaptive epsilon, Barzai-Borwein-style step prediction, lookahead averaging, and gated update clipping
- `sign_ef_consensus_kernel`: A sign-SGD variant with Fisher diagonal preconditioning, error feedback accumulation, and lookahead slow-weight averaging

This is **research-grade optimizer engineering**. The author combines elements from: Adam (Kingma & Ba), signSGD (Bernstein et al.), Lookahead (Zhang et al.), Fisher information matrix approximation, and error feedback compression (Stich et al.). Not a textbook implementation — a genuine hybrid design.

#### Quality Assessment Summary

| Algorithm | Domain | Sophistication | Level |
|-----------|--------|---------------|-------|
| fast_and_furious | Knapsack | ILS + VND + DP + multi-strategy perturbation | Senior engineer / OR practitioner |
| hgs_v1 | VRPTW | Full Hybrid Genetic Search framework | Graduate-level OR researcher |
| neural_alchemist | NN Optimizer | Custom dual-phase GPU optimizer + 2 CUDA kernels | ML research engineer |

These are **not trivial**. The submissions show genuine algorithmic innovation, not just boilerplate.

---

### 4. The Runtime (`tig-runtime/`)

**Source:** `tig-runtime/src/main.rs`

The runtime is a **CLI tool** that executes a single algorithm on a single challenge instance. Architecture:

1. **Dynamic library loading**: Uses `libloading` to load compiled algorithm `.so` files at runtime
2. **Fuel metering**: Injects a `__fuel_remaining` pointer into the loaded library. The algorithm binary is compiled with instrumentation that decrements fuel on each operation. When fuel hits 0, the process exits with code 87.
3. **Runtime signature**: Injects `__runtime_signature` pointer — initialized from the seed, modified by the algorithm during execution. Used to prove the algorithm actually ran (not just returned a precomputed answer).
4. **Challenge dispatch**: Feature-gated per challenge (compile with `--features c001` etc.)
5. **CPU vs GPU**: CPU challenges load `.so` only. GPU challenges additionally load a `.ptx` file, initialize CUDA context, and run an `initialize_kernel` + `finalize_kernel` for fuel accounting.

**GPU fuel scaling**: `let gpu_fuel_scale = 20` — GPU fuel counts are scaled 20x to loosely align with CPU fuel budgets.

**GPU fuel injection**: The PTX is loaded as text, and `0xdeadbeefdeadbeef` is string-replaced with the actual max fuel hex value. This is a compile-time constant injection into the GPU kernel.

**Sandboxing**: The slave runs algorithms inside **Docker containers** (one per challenge type: `docker exec batch["challenge"] tig-runtime ...`). This provides process isolation but not formal sandboxing. The fuel mechanism provides compute limiting. Runtime signature provides execution authenticity.

**Verification**: A separate `tig-verifier` binary re-runs the challenge instance generation and solution evaluation (but NOT the solving). The slave calls it after each nonce computation.

---

### 5. The Benchmarker

**Source:** `tig-benchmarker/master/main.py`, `tig-benchmarker/slave/main.py`

#### Architecture: Master/Slave (Python)

**Master** (`master/main.py`): Orchestration loop running every 5 seconds:
- `DataFetcher` — pulls latest block data from the protocol
- `JobManager` — manages benchmark job creation and assignment
- `PrecommitManager` — handles precommit submissions
- `SubmissionsManager` — handles benchmark/proof submissions
- `SlaveManager` — manages slave node connections (started as a thread)
- `ClientManager` — manages client connections (started as a thread)

On each new block: all managers notified for state refresh.

**Slave** (`slave/main.py`): Worker node that:
1. Downloads algorithm binaries (`.so` files, `.ptx` for GPU) from a URL, caches locally by challenge/arch
2. Runs `tig-runtime` inside Docker containers per nonce
3. Runs `tig-verifier` to validate each solution
4. Computes Merkle trees over outputs
5. Sends results back to master (root, proofs, or errors)

State machine per batch: `PENDING → PROCESSING → READY → FINISHED`

Key details:
- Detects CPU architecture (amd64/arm64) for correct binary selection
- Each batch has: settings, challenge, algorithm, rand_hash, fuel_budget, hyperparameters, nonces
- Merkle hashes computed from `OutputData` (nonce, runtime_signature, fuel_consumed, solution)
- Results compressed with zlib for storage
- TTL-based purging of completed batch folders

#### Docker Container Model

Each challenge type runs in its own Docker container. The slave executes:
```
docker exec <challenge_name> tig-runtime <settings> <rand_hash> <nonce> <binary_path> --fuel <budget>
docker exec <challenge_name> tig-verifier <settings> <rand_hash> <nonce> <output_file>
```

This means:
- Pre-built Docker images with the tig-runtime/tig-verifier for each challenge
- Algorithms loaded as dynamic libraries INTO those containers
- GPU challenges additionally pass `--ptx` for CUDA kernels

---

### 6. Commit History Patterns

**Source:** GitHub API commit stats

- **Total commits touching `tig-algorithms/`**: 255 (from Link header pagination)
- **Current knapsack algorithms**: ~20+ named algorithms (classic_quadkp, dynamic, fast_and_fun, fast_and_furious, knap_one, knap_supreme, knapheudp, knapmaxxing, knapsack_redone, knapsplat_hyper_s, knapsplatt, native_knapsack, near_knap, near_knap_improve_v1, new_relative_ultra, quadkp_improved, quadkp_maximize, relative_opt_fast, relative_opt_mid, etc.)

The naming patterns show evolutionary development:
- `near_knap` → `near_knap_improve_v1` (iteration)
- `relative_opt_fast` → `relative_opt_mid` → `relative_opt_optima` → `new_relative_ultra` (progression)
- `quadkp_improved` → `quadkp_maximize` (refinement)
- `knapsplatt` → `knapsplat_hyper_s` (variant)
- `sat_separate` → `sat_separate_opt` → `sat_separate_opt_p` → `sat_separate_prob` (satisfiability evolution)
- `sigma_freud` → `sigma_freud_v3` → `sigma_freud_v4` → `sigma_freud_v5` (hypergraph iterations)

**Pre-compiled binaries**: Many algorithms have `.so` files in `lib/` alongside source. Both amd64 and arm64 binaries for CPU challenges.

**Tar.gz archives**: Every algorithm has a `.tar.gz` in `lib/` — these are the deployment artifacts downloaded by slaves.

---

### 7. CUDA Neural Net Setup

**Source:** `tig-challenges/src/neuralnet_optimizer/mod.rs`, `template.cu`, `neural_alchemist/kernels.cu`

#### Training Harness Structure

The challenge provides a **complete training loop** (`training_loop()` function in `mod.rs`):

1. **Model**: MLP with configurable hidden layers (256 units), ReLU activation, batch normalization. Has `num_frozen_layers` (2) that don't get gradient updates.
2. **Forward pass**: cuBLAS (matrix multiply) + cuDNN (batch norm) + custom kernels
3. **Backward pass**: Full backpropagation through the unfrozen layers
4. **Optimizer interface**: Three function pointers that competitors implement:
   - `init_state` — allocate GPU memory for optimizer state
   - `query_at_params` — optionally modify parameters before forward pass (enables sharpness-aware training, perturbation-based methods)
   - `step` — given gradients + params, return parameter updates

The training loop handles:
- Per-epoch shuffling of training data (CPU-side shuffle, GPU batch upload)
- Mini-batch iteration (128 samples)
- Validation loss tracking
- Early stopping (patience=50, min_delta=1e-7)
- Best model saving via `save_solution` callback

#### CUDA Kernel Architecture

The `template.cu` specifies constraints:
- Must be compatible with nvidia/cuda:12.6.3-cudnn-devel-ubuntu24.04
- Multi-block kernels must write to non-overlapping memory (determinism requirement)
- Random numbers via CURAND seeded from challenge seed

The `kernels.cu` in challenge source (not shown in full, but referenced) provides dataset generation kernels:
- `generate_rff_params` — Random Fourier Feature parameter generation
- `generate_dataset` — Sample generation with noise injection
- `initialize_kernel` / `finalize_kernel` — fuel tracking bookkeeping

Fuel for GPU is tracked differently: a fuel counter lives in GPU global memory, checked by `finalize_kernel`. The runtime replaces a sentinel value (`0xdeadbeefdeadbeef`) in the PTX with the actual fuel limit at load time.

---

### 8. Architectural Assessment

#### What TIG Actually Is

TIG is a **proof-of-useful-work protocol** where the "work" is solving NP-hard optimization problems. The economic design has several notable properties:

1. **Algorithm adoption as market signal**: Benchmarkers choose which algorithm to run. Adoption is emergent — the protocol doesn't pick winners, market behavior does. This creates a competitive marketplace for optimization algorithms.

2. **Balanced participation enforcement**: The cutoff system forces benchmarkers to submit across ALL challenges. You can't specialize in one easy problem.

3. **Asymmetric verification**: All challenges are designed so verification is orders of magnitude cheaper than solving. Knapsack: O(k^2) verify vs NP-hard solve. Neural net: single forward pass vs thousands of training epochs.

4. **Three-party value chain**: Challenge owners design problems, algorithm contributors write solvers, benchmarkers provide compute. Each gets rewarded proportionally.

5. **Advance system for IP**: The voting-based advance mechanism attempts to reward algorithmic methods (not just implementations). This is novel — most protocols only reward execution.

#### Strengths

- The protocol code is well-structured Rust with clear separation of concerns
- Challenges are genuinely hard (quadratic knapsack, VRPTW, neural net training optimization)
- Algorithm submissions show real sophistication — these are OR/ML practitioners, not script kiddies
- The fuel metering + runtime signature system is clever for preventing precomputation
- Docker containerization provides reasonable isolation
- The CUDA support (c004-c006) is non-trivial infrastructure

#### Weaknesses / Risks

- **Python benchmarker**: The master/slave is Python with subprocess calls to Docker. Production-grade but not high-performance.
- **Centralized compilation**: Algorithms are compiled by the protocol (GitHub Actions workflow `build_algorithm.yml`), creating a trusted compilation step.
- **Docker is not a security sandbox**: Algorithms run as dynamic libraries inside Docker containers. A malicious `.so` could potentially exploit container escape.
- **SOTA baseline = greedy baseline**: The knapsack quality metric uses tabu search as baseline, with SOTA noted as "Not implemented yet". This means quality scores may shift significantly when SOTA is calibrated.
- **Fuel scaling is approximate**: `gpu_fuel_scale = 20` is described as "loosely aligned" — this creates an economic asymmetry between CPU and GPU challenges.
- **Small community signal**: 73 stars, 51 forks as of March 2026. The algorithm quality is high but the ecosystem is small.

---

### Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Protocol uses round-based block system | Direct code reading of contracts | HIGH | [GitHub tig-protocol/src/contracts/] | VERIFIED |
| 2 | Rewards distributed across 6 emission types | Direct code reading of rewards.rs | HIGH | [GitHub rewards.rs] | VERIFIED |
| 3 | OPoW forces balanced cross-challenge participation | Cutoff = min_bundles * multiplier | HIGH | [GitHub opow.rs] | VERIFIED |
| 4 | Knapsack is actually quadratic (interaction-based) | Instance generation code | HIGH | [GitHub knapsack/mod.rs] | VERIFIED |
| 5 | Neural net challenge provides full training loop | mod.rs contains training_loop() | HIGH | [GitHub neuralnet_optimizer/mod.rs] | VERIFIED |
| 6 | Algorithm submissions show graduate+ sophistication | Read 3 algorithms in full | HIGH | [GitHub tig-algorithms/src/] | VERIFIED |
| 7 | Runtime uses dynamic library loading with fuel injection | main.rs uses libloading + __fuel_remaining | HIGH | [GitHub tig-runtime/src/main.rs] | VERIFIED |
| 8 | Benchmarker runs algorithms in Docker containers | slave/main.py subprocess calls | HIGH | [GitHub tig-benchmarker/slave/main.py] | VERIFIED |
| 9 | 255 total commits to tig-algorithms | GitHub API Link header | HIGH | [GitHub API] | VERIFIED |
| 10 | 73 stars, 51 forks | GitHub API repo metadata | HIGH | [GitHub API] | VERIFIED |
| 11 | GPU fuel scale factor is 20x | Hardcoded constant in main.rs | HIGH | [GitHub tig-runtime/src/main.rs] | VERIFIED |
| 12 | SOTA baseline not yet implemented for knapsack | Comment in code: "Not implemented yet" | HIGH | [GitHub knapsack/mod.rs] | VERIFIED |

<!-- knowledge-index
generated: 2026-03-26T05:08:47Z
hash: ce52410c4090

title: TIG Monorepo Architecture — Deep Dive
table_claims: 12

end-knowledge-index -->
