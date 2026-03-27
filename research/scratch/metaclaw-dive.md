## MetaClaw: Continual Meta-Learning for Deployed LLM Agents -- Deep Dive

**Paper:** "MetaClaw: Just Talk -- An Agent That Meta-Learns and Evolves in the Wild"
**Authors:** Peng Xia, Jianwen Chen, Xinyu Yang, Haoqin Tu, Jiaqi Liu, Kaiwen Xiong, Siwei Han, Shi Qiu, Haonian Ji, Yuyin Zhou, Zeyu Zheng, Cihang Xie, Huaxiu Yao
**Affiliations:** UNC-Chapel Hill, Carnegie Mellon University, UC Santa Cruz, UC Berkeley
**ArXiv:** 2603.17187 (March 17, 2026)
**Repo:** github.com/aiming-lab/MetaClaw (MIT, 2.8K stars, Python)
**Tier:** Standard | **Date:** 2026-03-27

---

### Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Kimi-K2.5 accuracy goes from 21.4% to 40.6% on CLI tasks (Part I) with full pipeline | Table in paper + Gemini extraction of full text | HIGH | [arxiv:2603.17187] | VERIFIED |
| 2 | File-check completion rises 8.25x (2.0% to 16.5%) on Part I for Kimi-K2.5 | Paper Table | HIGH | [arxiv:2603.17187] | VERIFIED |
| 3 | Skills-only lifts multi-choice but NOT file-check; RL lifts file-check but may reduce multi-choice | Paper analysis section | HIGH | [arxiv:2603.17187] | VERIFIED |
| 4 | AutoResearchClaw composite robustness improves 18.3% (0.714 to 0.845) | Paper Table | HIGH | [arxiv:2603.17187] | VERIFIED |
| 5 | OMLS uses three signals: sleep window, keyboard idle, Google Calendar | Paper + source code (scheduler.py, idle_detector.py, calendar_client.py) | HIGH | [arxiv:2603.17187 + GitHub] | VERIFIED |
| 6 | LoRA rank defaults to 32, batch size 4, learning rate 1e-4 | config.py source | HIGH | [GitHub] | VERIFIED |
| 7 | Skills are Markdown files stored in ~/.metaclaw/skills/ | README + config.py | HIGH | [GitHub] | VERIFIED |
| 8 | PRM uses GPT-5.2 by default with majority-vote ensemble (m=3) | config.py source | HIGH | [GitHub] | VERIFIED |

---

### 1. The Continual Meta-Learning Framework

**Core Abstraction.** The meta-model M is a tuple (theta, S) where:
- **theta**: base LLM policy weights (e.g., Kimi-K2.5 or Qwen3-4B)
- **S**: skill library -- a set of Markdown behavioral instructions (s_1, ..., s_K)

Both evolve, but on different timescales and through different mechanisms. This is the central architectural insight: gradient-free skill adaptation handles fast behavioral correction; gradient-based policy optimization handles deeper capability internalization.

**Why two timescales matter.** The paper's ablation shows they address different failure modes:
- Skills alone lift multi-choice accuracy (behavioral heuristics, formatting rules, procedure adherence) but leave file-check completion flat -- skills can tell the agent *what* to do but can't make it *execute* reliably.
- RL alone (policy optimization) improves execution reliability (file creation, tool use chains) but can slightly decrease multi-choice accuracy as the policy shifts toward execution behavior.
- Together: Kimi-K2.5 goes from 21.4% to 40.6%, nearly matching GPT-5.2's 41.1% baseline.

**The feedback loop:** Better policy -> more informative failures -> richer skills -> higher-reward trajectories for RL -> better policy. The paper calls this a "virtuous cycle."

---

### 2. Gradient-Free Skill Adaptation (Fast Path)

**What triggers skill evolution.** The Skill Evolver monitors a success rate metric. When the ratio of samples with reward > 0 falls below a threshold (default 0.4), evolution fires. It can also be triggered periodically every N turns (default 10). [SOURCE: skill_evolver.py, config.py]

**How the Skill Evolver works.** The evolver is an LLM (default: GPT-5.2) that receives:
1. Up to 6 failure trajectories -- last 600 chars of context + first 500 chars of assistant response, labeled with reward values
2. The full existing skill registry (general + task-specific + common-mistakes categories) -- for deduplication
3. Instructions to generate 1 to max_new_skills new skills

Each skill is a JSON object with:
- `name`: lowercase hyphenated slug (e.g., `handle-partial-input`) or auto-assigned `dyn-NNN`
- `description`: one-line trigger condition
- `content`: 6-15 lines of Markdown with heading, numbered steps, examples, and "Anti-pattern" section
- `category`: task category or "general"

**Deduplication is two-stage:**
1. Prompt-level: existing skills listed to guide LLM away from repeats
2. Post-generation: `_finalise_names()` catches slug collisions within batch; `SkillManager` handles cross-batch dedup

**Skill injection at inference.** Retrieved via top-k cosine similarity over sentence embeddings. Default: 6 general skills + up to 10 task-specific skills. Skills are formatted as a Markdown block appended to the system prompt. [SOURCE: config.py shows retrieval_mode: "template" or "embedding", skill_top_k: 6, task_specific_top_k: 10]

**Why this is gradient-free.** Skills operate entirely through prompt injection. No weight changes, no service interruption. Takes effect immediately on the next request.

---

### 3. Gradient-Based Policy Optimization (Slow Path)

**Algorithm:** GRPO (Group Relative Policy Optimization) with center-normalized advantages within each batch. Loss function is configurable: importance_sampling, PPO, or CISPO. [SOURCE: trainer.py, config.py]

**RL backend:** Cloud LoRA fine-tuning via Tinker API (or MinT/Weaver alternatives). Not local training -- the proxy-based architecture means no local GPU required. [SOURCE: config.py, trainer.py]

**Configuration defaults:**
- LoRA rank: 32
- Learning rate: 1e-4
- Batch size: 4 conversation samples per step
- Max steps: 1000
- Base model: Qwen/Qwen3-4B (configurable)
- Save/refresh weights every 200s
- KL penalty coefficient: 1.0 (for OPD mode)

**Process Reward Model (PRM):** Scores intermediate reasoning steps, not just final outcomes. Default provider: OpenAI-compatible API using GPT-5.2 with:
- Majority-vote ensemble (m=3)
- Temperature: 0.6
- Configurable max_new_tokens

**The training loop (Algorithm 1):**
1. Serve task using skills retrieved from S_g
2. Collect trajectory, score with PRM
3. If failure (reward <= 0): add to support set
4. If success (reward > 0): add to RL buffer
5. If support set reaches threshold: run Skill Evolver -> S_{g+1}, flush stale buffer, increment g
6. If OMLS detects idle window AND RL buffer has enough samples: run GRPO update on theta, hot-swap weights

---

### 4. Support-Query Separation and Generation Stamping

This is the most architecturally interesting mechanism. It prevents "stale reward contamination" -- training on trajectories collected under old skill versions.

**Every trajectory is stamped** with the current `skill_generation` index when collected.

**Two data streams:**
- **Support data (D^sup_g):** Failure trajectories under generation g. Consumed by Skill Evolver to produce S_{g+1}. Then discarded from RL buffer.
- **Query data (D^qry_{g+1}):** Trajectories collected AFTER new skills take effect. Only these feed RL training.

**Flushing mechanism:** When skills evolve (g -> g+1), the trainer:
1. Discards all buffered samples where `skill_generation <= g`
2. Clears both pending batch and output queue
3. Logs: "discarded %d pending + %d queued samples"

This is a MAML-inspired design: support set drives fast adaptation (skill evolution), query set measures post-adaptation performance (RL signal). The generation stamp is the enforcement mechanism.

**Implementation detail from trainer.py:** `_drain_with_pause_check()` polls rollout worker for completed groups, respects scheduler pause events, and filters stale samples by checking `s.skill_generation >= self._current_skill_generation` before accumulation.

---

### 5. The Opportunistic Meta-Learning Scheduler (OMLS)

**Purpose:** Gate expensive RL weight updates to times when the user is idle. The proxy serving layer continues uninterrupted.

**State machine:** IDLE_WAIT -> WINDOW_OPEN -> UPDATING -> PAUSING -> IDLE_WAIT

**Three idle signals:**

| Signal | Implementation | Default | Source |
|--------|---------------|---------|--------|
| Sleep hours | Configurable time window (supports midnight wrapping) | 23:00-07:00 | `_sleep_hours_active()` in scheduler.py |
| System idle | OS input device idle timer (macOS: `ioreg HIDIdleTime`) | 30 min | idle_detector.py |
| Calendar | Google Calendar API `is_busy_now()` | disabled | calendar_client.py |

**Rule:** Window opens when ANY signal indicates user absence. Window closes when ANY signal indicates user returned.

**Coordination:** Two `asyncio.Event` objects:
- `trigger_event`: scheduler sets when window opens, trainer starts
- `pause_event`: scheduler sets when user returns, trainer checkpoints and stops

**Mid-batch checkpointing:** Trainer saves every 5 steps via `save_state_async()`. If user returns mid-training, partial work is preserved. Pending batch samples carry over to next window IF their generation still matches.

**Minimum window:** `scheduler_min_window_minutes` (default: not specified in config, but the design requires at least one complete batch worth of time).

**State persistence:** Writes to `~/.metaclaw/scheduler_state.json` on each transition, enabling monitoring via `get_status()` and CLI.

---

### 6. Service Downtime Prevention

Three mechanisms:

1. **Skill injection is prompt-only.** No weight changes, instant effect, zero interruption. This handles the fast adaptation path entirely.

2. **Weight updates are deferred.** OMLS ensures RL training only runs during idle windows. The proxy serving layer continues using current weights throughout.

3. **Hot-swapping.** After training completes during an idle window, new weights are pushed to the inference worker via `update_sampling_client()`. This happens atomically -- the serving endpoint switches from old weights to new without downtime.

4. **Graceful pause/resume.** If user returns mid-training, trainer checkpoints and yields. Accumulated gradient steps are preserved. Training resumes at next idle window from the checkpoint, not from scratch.

---

### 7. Concrete Architectural Components

```
User <-> API Proxy (port 30000)
              |
              +-- Skill Manager (retrieves relevant skills, injects into prompt)
              |       |
              |       +-- Skill Evolver (LLM analyzing failures, generating new skills)
              |       +-- Embedding-based retrieval (cosine similarity)
              |
              +-- Memory Layer (episodic, semantic, preferences, project state)
              |       |
              |       +-- Synergy module (coordinated skill+memory injection, shared token budget)
              |
              +-- PRM Scorer (process reward model, scores trajectories)
              |
              +-- Rollout Worker (parallel episode execution, sample collection)
              |
              +-- Trainer (GRPO, LoRA fine-tuning via cloud API)
              |       |
              |       +-- Generation stamping + buffer management
              |       +-- Mid-batch checkpointing
              |
              +-- Scheduler (OMLS: idle detection, training window management)
                      |
                      +-- IdleDetector (keyboard/mouse)
                      +-- CalendarClient (Google Calendar)
                      +-- Sleep window config
```

**Key files in codebase:**

| Component | File | Purpose |
|-----------|------|---------|
| Proxy/API | api_server.py | Request interception + skill injection |
| Skill management | skill_manager.py | Retrieval, injection, library persistence |
| Skill evolution | skill_evolver.py | Failure analysis, skill generation |
| RL training | trainer.py | GRPO, buffer mgmt, generation stamping |
| Scheduling | scheduler.py | OMLS state machine |
| Idle detection | idle_detector.py | OS-level keyboard/mouse monitoring |
| Calendar | calendar_client.py | Google Calendar integration |
| PRM scoring | prm_scorer.py | Process reward model integration |
| Configuration | config.py | ~100 params, MetaClawConfig dataclass |
| Rollout | rollout.py, openclaw_env_rollout.py | Trajectory collection |
| CLI | cli.py, __main__.py | metaclaw start/setup/config commands |
| Memory | memory/ directory | Episodic + semantic memory layer |

---

### 8. MetaClaw-Bench Benchmark

**Part I: 30 simulated workdays, 346 questions**
- File-check tasks: structured edits/transformations, output validated by automated checkers
- Multi-choice tasks: conceptual/procedural questions on domain-specific rules
- Difficulty increases monotonically across days
- Tests: Can the agent learn from accumulating experience over a realistic deployment timeline?

**Part II: 14 simulated workdays, 588 questions (434 multi-choice + 154 file-check)**
- Emphasizes behavioral heuristic compliance
- Five progressively introduced implicit preference rules (NOT in initial prompt):
  - P1 (Timestamp): ISO 8601 with +08:00 offset
  - P2 (File naming): YYYYMMDD_description.ext in snake_case
  - P3 (Metadata): created_at, author, status in every output file
  - P4 (Backup): .bak copy before modifying any existing file
  - P5 (Completion log): [DONE] <timestamp> | <task_id> | <summary> appended to done.log
- Tests: Can the agent infer and adopt unstated preferences from feedback?

**Metrics:** Overall accuracy (mean per-question score) + file-check completion rate (fraction passing all automated checkers).

---

### 9. Experimental Results

#### Part I (30 days, 346 questions)

| Configuration | Accuracy | File-Check Completion |
|---|---|---|
| GPT-5.2 Baseline | 41.1% | 14.7% |
| GPT-5.2 + Skills | 44.0% | 17.1% |
| Kimi-K2.5 Baseline | 21.4% | 2.0% |
| Kimi-K2.5 + Skills | 28.3% | 2.0% |
| Kimi-K2.5 + Full | **40.6%** | **16.5%** (8.25x) |

#### Part II (14 days, 588 questions)

| Configuration | Accuracy | File-Check Completion |
|---|---|---|
| GPT-5.2 Baseline | 44.9% | 58.4% |
| GPT-5.2 + Skills | 49.1% | 67.5% |
| Kimi-K2.5 Baseline | 21.1% | 18.2% |
| Kimi-K2.5 + Skills | 26.9% | 33.8% |
| Kimi-K2.5 + Full | **39.6%** | **51.9%** (+185%) |

#### AutoResearchClaw (23-stage pipeline, skills-only)

| Metric | Baseline | With Skills | Change |
|---|---|---|---|
| Stage retry rate | 10.5% | 7.9% | -24.8% |
| Refine cycles/stage | 2.0 | 1.2 | -40.0% |
| Pipeline completion | 18/19 stages | 19/19 | +1 stage |
| Composite robustness | 0.714 | 0.845 | +18.3% |

---

### 10. Transferable Patterns to Our Agent Infrastructure

Our system: Claude Code + skill system (Markdown in ~/Projects/skills/) + hooks (pre/post tool use) + session-analyst feedback loop + improvement-log. Here's what transfers and what doesn't.

#### Transfers directly

**1. Skill evolution from failure trajectories.**
We already have skills as Markdown files and session-analyst that detects failure patterns. The MetaClaw pattern: (a) detect failures via PRM/reward signal, (b) feed failure context to an LLM evolver, (c) generate new skills in standard Markdown format, (d) deduplicate against existing library. Our equivalent: session-analyst already identifies patterns in improvement-log, but skill generation is manual. The evolver loop could be automated: session-analyst findings -> skill evolver LLM -> new skill file -> human review gate.

*Key constraint:* MetaClaw's Skill Evolver uses 600 chars of context + 500 chars of response per failure. This compact representation is deliberate -- full trajectories are too noisy. Our session-analyst already does this kind of compression.

**2. Generation stamping for session coherence.**
The idea that skill changes invalidate prior evaluation data is directly applicable. When we update a skill or rule, we should tag sessions with the "rule generation" to avoid attributing old-rule failures to new-rule performance. Our fix-verify.py already partially does this (runs detection queries post-fix), but it doesn't formally stamp which rule version was active during each session.

**3. Dual-timescale adaptation.**
Immediate: skill/rule changes (our current model via CLAUDE.md edits, skill file updates).
Scheduled: deeper optimization (our equivalent would be periodic model fine-tuning or RL, which we don't do). The insight that these address different failure classes (behavioral heuristics vs execution reliability) is useful framing even without the RL component.

**4. Implicit preference learning (P1-P5 pattern).**
Part II's progressively introduced unstated preferences are exactly the kind of thing our session-analyst should detect. User corrections about formatting, naming, backup procedures etc. should be captured as skills automatically, not just as memory entries.

#### Doesn't transfer (or needs adaptation)

**1. RL/GRPO policy optimization.**
We don't fine-tune Claude -- we use the API model as-is. The gradient-based slow path has no equivalent in our setup. The skills-only results still show meaningful improvement (Kimi-K2.5: 21.4% -> 28.3% on Part I, +32.2%), suggesting the fast path alone has value.

**2. Cloud LoRA fine-tuning infrastructure.**
Requires Tinker/MinT/Weaver cloud training backends. Not applicable to our Claude Code + API setup.

**3. PRM scoring for trajectory quality.**
We don't have a process reward model. Our closest analog is session-analyst's structural anomaly detection + hook telemetry, which measures process quality through different means (tool failure rates, correction patterns).

**4. Proxy architecture.**
MetaClaw operates as a transparent proxy (port 30000) between user and LLM. Our Claude Code is not proxy-based -- it's a direct CLI tool. Skill injection happens through CLAUDE.md and rules files, not through request interception.

#### Key architectural insight worth stealing

**The support-query separation principle.** When you change a rule/skill, all evidence collected under the old configuration is contaminated. You can't use old failures to evaluate new rules, and you shouldn't use old successes to train against new rules. This is a general principle applicable beyond RL: our fix-verify.py should implement formal generation tracking so we know which sessions ran under which rule versions.

**The skill evolution threshold (0.4 success rate).** Having a quantitative trigger for "it's time to evolve skills" rather than relying on human judgment or fixed schedules. Our session-analyst could compute a similar metric from hook telemetry: if supervision-load (SLI) exceeds threshold, trigger automated skill review.

---

### What's Uncertain

1. **PRM architecture unspecified.** The paper doesn't describe the process reward model's architecture -- just that it uses GPT-5.2. How it scores intermediate reasoning steps versus final outcomes is unclear.
2. **Embedding model for skill retrieval unspecified.** The paper says "cosine similarity over sentence embeddings" but doesn't name the model or similarity threshold.
3. **No ablation on skill evolution frequency.** Default is every 10 turns with a 0.4 threshold, but no analysis of sensitivity to these parameters.
4. **GPT-5.2 + Full not reported.** Only GPT-5.2 + Skills was tested. The full pipeline (skills + RL) was only applied to Kimi-K2.5, making it hard to assess ceiling effects.
5. **AutoResearchClaw was skills-only.** The downstream validation didn't include RL, so we can't assess full-pipeline impact on real research workflows.
6. **Memory layer (v0.4.0) not in paper.** The repo's memory subsystem (episodic, semantic, preferences, project state) appears to be a post-paper addition. The paper doesn't evaluate it.

---

### References

- Xia, P., Chen, J., Yang, X., Tu, H., Liu, J., Xiong, K., Han, S., Qiu, S., Ji, H., Zhou, Y., Zheng, Z., Xie, C., & Yao, H. (2026). MetaClaw: Just Talk -- An Agent That Meta-Learns and Evolves in the Wild. arXiv:2603.17187. [SOURCE: https://arxiv.org/abs/2603.17187]
- GitHub repository: https://github.com/aiming-lab/MetaClaw [SOURCE: GitHub]
- Implementation details extracted from: config.py, skill_evolver.py, scheduler.py, trainer.py [SOURCE: GitHub raw files]

<!-- knowledge-index
generated: 2026-03-27T04:44:43Z
hash: c3bcf8635b16

table_claims: 8

end-knowledge-index -->
