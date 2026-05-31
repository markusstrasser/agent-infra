#!/usr/bin/env python3
"""Provider adapters for the search-engine verification eval — stdlib urllib only.

One uniform contract per engine so the harness is engine-agnostic and the judge
can be fed a normalized evidence packet (critique fix: format must not leak
engine identity). Each adapter returns:

    Result(answer, sources, latency_s, cost_usd, error, raw)
      answer  : engine's synthesized prose (None for snippet-only engines)
      sources : list[{"url","snippet"}]  <- the normalized lane needs snippet TEXT
      cost_usd: per-call cost for the cost-per-correct-verdict headline metric

Keys read from ~/.env (already sourced into env by the runner). No third-party
deps so `uv run python3 adapters.py --audit "<claim>"` works anywhere.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field


@dataclass
class Result:
    engine: str
    answer: str | None
    sources: list[dict]  # [{"url":..., "snippet":...}]
    latency_s: float
    cost_usd: float
    error: str | None = None
    raw: dict = field(default_factory=dict)

    @property
    def n_with_snippet(self) -> int:
        return sum(1 for s in self.sources if s.get("snippet"))


def _post(url: str, payload: dict, headers: dict, timeout: int = 40) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _get(url: str, params: dict, headers: dict, timeout: int = 40) -> dict:
    full = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(full, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _timed(engine: str, cost: float, fn) -> Result:
    """Run fn() -> (answer, sources, raw); wrap timing + error → FETCH_FAILED."""
    t0 = time.time()
    try:
        answer, sources, raw = fn()
        return Result(engine, answer, sources, time.time() - t0, cost, None, raw)
    except urllib.error.HTTPError as e:
        return Result(engine, None, [], time.time() - t0, 0.0, f"HTTP {e.code}", {})
    except Exception as e:  # noqa: BLE001 - never crash the run
        return Result(engine, None, [], time.time() - t0, 0.0, f"{type(e).__name__}: {e}", {})


# --- per-engine adapters -------------------------------------------------------

def exa(claim: str) -> Result:
    def go():
        d = _post("https://api.exa.ai/answer", {"query": claim, "text": True},
                  {"x-api-key": os.environ["EXA_API_KEY"]})
        srcs = [{"url": c.get("url", ""), "snippet": (c.get("text") or "")[:600]}
                for c in d.get("citations", [])]
        return d.get("answer"), srcs, d
    return _timed("exa", 0.005, go)


def brave(claim: str) -> Result:
    def go():
        d = _get("https://api.search.brave.com/res/v1/web/search",
                 {"q": claim, "count": 10},
                 {"X-Subscription-Token": os.environ["BRAVE_API_KEY"], "Accept": "application/json"})
        srcs = [{"url": r.get("url", ""), "snippet": r.get("description", "")}
                for r in d.get("web", {}).get("results", [])]
        return None, srcs, {"web_count": len(srcs)}  # snippet-only engine
    return _timed("brave", 0.005, go)


def perplexity(claim: str) -> Result:
    """At-risk for the normalized lane: chat API returns prose + citation URLs;
    per-source snippet text is often absent. We capture search_results snippets
    when present, else fall back to URL-only (engine flagged native-lane-only)."""
    def go():
        d = _post("https://api.perplexity.ai/chat/completions",
                  {"model": "sonar-pro",
                   "messages": [{"role": "user", "content": f"Verify this claim, cite sources: {claim}"}]},
                  {"Authorization": f"Bearer {os.environ['PERPLEXITY_API_KEY']}"})
        answer = d["choices"][0]["message"]["content"]
        results = d.get("search_results") or []
        if results:
            srcs = [{"url": r.get("url", ""), "snippet": r.get("snippet", "") or r.get("title", "")}
                    for r in results]
        else:
            srcs = [{"url": u, "snippet": ""} for u in d.get("citations", [])]
        return answer, srcs, {"has_search_results": bool(results)}
    return _timed("perplexity", 0.009, go)


def linkup(claim: str) -> Result:
    def go():
        d = _post("https://api.linkup.so/v1/search",
                  {"q": claim, "depth": "standard", "outputType": "sourcedAnswer"},
                  {"Authorization": f"Bearer {os.environ['LINKUP_API_KEY']}"})
        srcs = [{"url": s.get("url", ""), "snippet": s.get("snippet", "")}
                for s in d.get("sources", [])]
        return d.get("answer"), srcs, {"n_sources": len(srcs)}
    return _timed("linkup", 0.006, go)


def parallel(claim: str) -> Result:
    """Parallel Search API via the installed `parallel` SDK (REST shape differs;
    SDK reads PARALLEL_API_KEY). Snippet-only engine — `.results[].excerpts`."""
    def go():
        import parallel as _p  # pyright: ignore[reportMissingImports]  # SDK only in uv env
        r = _p.Client().beta.search(objective=claim, mode="fast", max_results=10)
        srcs = [{"url": it.url, "snippet": " ".join(it.excerpts or [])[:600]}
                for it in (r.results or [])]
        return None, srcs, {"search_id": getattr(r, "search_id", None)}
    return _timed("parallel", 0.005, go)


ENGINES = {"exa": exa, "brave": brave, "perplexity": perplexity, "linkup": linkup, "parallel": parallel}


def _audit(claim: str) -> None:
    print(f"[adapter audit] claim: {claim!r}\n")
    print(f"  {'engine':<11} {'http':<6} {'lat':>6} {'$':>7} {'#src':>5} {'#snip':>6} {'answer?':<8} note")
    print("  " + "-" * 78)
    for name, fn in ENGINES.items():
        r = fn(claim)
        status = "ERR" if r.error else "ok"
        note = r.error or ("native-lane-only (no snippets)" if r.n_with_snippet == 0 and not r.error else "")
        print(f"  {name:<11} {status:<6} {r.latency_s:>5.1f}s {r.cost_usd:>7.3f} "
              f"{len(r.sources):>5} {r.n_with_snippet:>6} {('yes' if r.answer else 'no'):<8} {note}")
        if r.sources and r.n_with_snippet:
            ex = next(s for s in r.sources if s.get("snippet"))
            print(f"              ↳ {ex['snippet'][:70]!r}")
    print("\n  normalized lane feasible iff #snip > 0. native-lane-only engines run native-only.")


if __name__ == "__main__":
    import sys
    claim = sys.argv[1] if len(sys.argv) > 1 else "Anthropic raised a Series F funding round in 2025"
    _audit(claim)
