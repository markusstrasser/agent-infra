"""LLM verifier arm — gpt-5.5 via OpenAI SDK, batched, structured output.

Represents the 'model-based verifier' (high recall, but gameable / non-deterministic).
"""
import json, time, os
from openai import OpenAI

MODEL = os.environ.get("PROBE_LLM_MODEL", "gpt-5.5")
BATCH = 25
_client = OpenAI()

_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "equivalence_judgments",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "judgments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "idx": {"type": "integer"},
                            "equivalent": {"type": "boolean"},
                        },
                        "required": ["idx", "equivalent"],
                    },
                }
            },
            "required": ["judgments"],
        },
    },
}

_SYS = (
    "You are a strict math answer-equivalence checker. For each item decide whether the "
    "CANDIDATE answer is mathematically equivalent to the REFERENCE answer (same value / "
    "same solution set / same function), ignoring formatting, ordering, and notation. "
    "Accept rounded decimals that match the reference to the precision given. Return a "
    "judgment for every idx."
)


def _call(batch):
    items = [{"idx": i, "reference": r, "candidate": c} for (i, r, c) in batch]
    user = "Judge equivalence for each item:\n" + json.dumps(items, ensure_ascii=False)
    for attempt in range(4):
        try:
            resp = _client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "system", "content": _SYS},
                          {"role": "user", "content": user}],
                response_format=_SCHEMA,
                reasoning_effort="low",
            )
            data = json.loads(resp.choices[0].message.content)
            return {j["idx"]: bool(j["equivalent"]) for j in data["judgments"]}
        except Exception as e:
            if attempt == 3:
                print(f"  LLM batch failed: {type(e).__name__}: {str(e)[:80]}")
                return {}
            time.sleep(2 * (attempt + 1))
    return {}


def run(pairs):
    """pairs: list of dicts with 'reference','candidate'. Returns (verdicts, seconds)."""
    triples = [(i, p["reference"], p["candidate"]) for i, p in enumerate(pairs)]
    verdicts = {}
    t0 = time.perf_counter()
    for k in range(0, len(triples), BATCH):
        batch = triples[k:k + BATCH]
        verdicts.update(_call(batch))
        print(f"  LLM {min(k+BATCH,len(triples))}/{len(triples)}")
    secs = time.perf_counter() - t0
    return verdicts, secs / max(1, len(triples))
