# Sycophancy probe — factual challenge regime (2026-06-13)

Screening probes for: does an explicit negation fork ("...or not? tell me if I'm wrong")
reduce sycophantic stance-flipping vs alternatives? Full writeup + verdict:
`../../2026-06-13-user-pressure-sycophancy-current-state.md` (§ Probe results).

- `probe.py`   — v1: single-turn, mild pressure, 5 fix conditions × 8 items × 3 models.
- `probe2.py`  — v2a: genuine multi-turn authority pushback (model commits, then expert
  pushes a persuasive wrong mechanism). Harm cell.
- `results.jsonl` / `results_v2a.jsonl` — raw rows (prompt, response, grade).

Rerun: `uv run python3 probe2.py` (needs `llmx`; Opus via `--lite bare`, Gemini via `--flex`).

**Verdict:** 0/48 genuine caves on Opus 4.8 / GPT-5.5 / Gemini 3 Flash → factual sycophancy
~eliminated at the frontier; factual eval not worth building. **Methods caveat:** the v2a
auto-grader produced 3/24 FALSE caves by flagging "you're right that X, *however* [correct]"
politeness prefixes — grade FINAL-ANSWER FLIP, not capitulation phrases.
