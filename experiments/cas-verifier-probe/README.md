# CAS-as-RLVR-Verifier Probe (Stage 1)

Does a compiled CAS (Symbolica) beat sympy at fixing the **false negatives** that
plague RLVR math verifiers — and can it match an LLM judge deterministically?

**Answer:** No on recall, yes on speed. See `../../research/2026-06-08-cas-verifier-probe-results.md`.

## What it does
Runs 4 verifier arms over 500 labeled (reference, candidate) pairs from
`zhangchenxu/HardVerify-Math` (TinyV's hard-tail benchmark): `regex`, `sympy`,
`symbolica` (JIT + Schwartz–Zippel), `llm` (gpt-5.5). sympy and symbolica share
one structural wrapper; only the algebra engine differs.

## Run
```bash
uv run python3 fetch_data.py   # -> pairs.jsonl  (HF datasets-server, no download)
uv run python3 run.py          # -> results.md, results.json  (needs OPENAI_API_KEY)
uv run python3 cascade.py      # deterministic-first → LLM-fallback cascade metrics
uv run python3 fp_audit.py     # inspect symbolica false positives
```
Symbolica runs free in restricted single-core mode (no license key). gpt-5.5 over
500 pairs ≈ low single-digit $.

## Files
- `fetch_data.py` — dataset → `pairs.jsonl` (+ answer-kind classifier)
- `arms.py` — regex / sympy / symbolica arms (shared structural wrapper)
- `llm_arm.py` — gpt-5.5 batched structured judge
- `run.py` — orchestrate + metrics (overall, algebraic slice, per-kind)
- `cascade.py`, `fp_audit.py` — follow-up analyses
