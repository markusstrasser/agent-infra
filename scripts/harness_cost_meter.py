#!/usr/bin/env python3
# Gov-ID: tool:harness-cost-meter
# goal: falsify Databricks/Pi "harness ≫ model for $/task" on our workloads
# blast_radius: local
"""Harness cost meter — tokens/task and $/task by vendor (and optional live probe).

Two modes:

  observe (default)
      Roll up agentlogs sessions by vendor for a project window.
      Reports tokens/session, tools/session, duration — the local falsifier for
      "harness dominates cost" without installing Pi.

  probe
      Run a fixed ask-mode task on available headless backends (cursor-agent
      today; llmx/claude-cli when auth works; pi when installed). Writes a
      comparison row with tokens + estimated $.

Usage:
  just harness-cost-meter
  just harness-cost-meter -- --project genomics --days 7
  just harness-cost-meter -- --json
  just harness-cost-meter -- probe --backends cursor
  just harness-cost-meter -- probe --backends cursor --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

import importlib.util

_uc_spec = importlib.util.spec_from_file_location(
    "usage_check", REPO / "scripts" / "usage-check.py"
)
_uc = importlib.util.module_from_spec(_uc_spec)
assert _uc_spec.loader is not None
_uc_spec.loader.exec_module(_uc)
PRICING = _uc.PRICING
est_cost = _uc.est_cost

DEFAULT_DB = Path.home() / ".claude" / "agentlogs.db"
DEFAULT_TASK = (
    "In math.py, what does add(2, 3) return? Reply in one short sentence."
)

# Cursor Composer is not in llmx PRICING; list-rate placeholder for estimates only.
# Update when quoting externally — this is a relative-compare aid, not billing truth.
COMPOSER_PRICING = ("composer-2.5", 1.25, 10.0)  # $/MTok in/out — [ESTIMATED]


@dataclass
class VendorRollup:
    vendor: str
    sessions: int
    with_tokens: int
    avg_in_tok: float | None
    avg_out_tok: float | None
    median_in_tok: float | None
    avg_tools: float
    avg_duration_min: float | None
    est_usd_per_session: float | None
    note: str = ""


def _connect(db: Path) -> sqlite3.Connection:
    if not db.is_file():
        raise SystemExit(f"agentlogs DB not found: {db}")
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _model_rate(model: str | None) -> tuple[float, float] | None:
    if not model:
        return None
    if model in PRICING:
        return PRICING[model]
    # prefix / family fallbacks for agentlogs model strings
    for key, rate in PRICING.items():
        if model.startswith(key) or key in model:
            return rate
    if "composer" in model:
        return (COMPOSER_PRICING[1], COMPOSER_PRICING[2])
    if "opus" in model:
        return PRICING.get("claude-opus-4-8")
    if "sonnet" in model:
        return PRICING.get("claude-sonnet-4-6")
    if "gpt-5.6-luna" in model:
        return PRICING.get("gpt-5.6-luna")
    if "gpt-5.6-terra" in model:
        return PRICING.get("gpt-5.6-terra")
    if "gpt-5.6" in model or model.startswith("gpt-5"):
        return PRICING.get("gpt-5.6-sol")
    return None


def _est_session_usd(model: str | None, in_tok: int, out_tok: int) -> float | None:
    rate = _model_rate(model)
    if rate is None:
        return None
    return (in_tok * rate[0] + out_tok * rate[1]) / 1_000_000


def observe(
    *,
    db: Path,
    project: str,
    days: int,
    min_tools: int = 0,
) -> list[VendorRollup]:
    """Session-level rollup by vendor from agentlogs."""
    con = _connect(db)
    rows = con.execute(
        """
        SELECT s.session_pk, s.vendor, s.model, s.duration_min,
               SUM(COALESCE(r.input_tokens, 0)) AS in_tok,
               SUM(COALESCE(r.output_tokens, 0)
                   + COALESCE(r.reasoning_tokens, 0)) AS out_tok,
               (SELECT COUNT(*) FROM tool_calls tc
                  JOIN runs r2 ON r2.run_id = tc.run_id
                 WHERE r2.session_pk = s.session_pk) AS n_tools
          FROM sessions s
          JOIN runs r ON r.session_pk = s.session_pk
         WHERE s.start_ts >= datetime('now', ?)
           AND s.is_subagent = 0
           AND s.project_slug = ?
         GROUP BY s.session_pk
        """,
        (f"-{days} days", project),
    ).fetchall()
    con.close()

    by_vendor: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        if int(row["n_tools"] or 0) < min_tools:
            continue
        by_vendor.setdefault(row["vendor"], []).append(row)

    out: list[VendorRollup] = []
    for vendor, sess in sorted(by_vendor.items()):
        in_known = [int(r["in_tok"]) for r in sess if int(r["in_tok"] or 0) > 0]
        out_known = [int(r["out_tok"]) for r in sess if int(r["in_tok"] or 0) > 0]
        tools = [int(r["n_tools"] or 0) for r in sess]
        durs = [float(r["duration_min"]) for r in sess if r["duration_min"] is not None]
        usd = []
        for r in sess:
            if int(r["in_tok"] or 0) <= 0:
                continue
            e = _est_session_usd(r["model"], int(r["in_tok"]), int(r["out_tok"]))
            if e is not None:
                usd.append(e)
        note = ""
        if vendor == "cursor" and not in_known:
            note = "cursor runs often lack token fields in agentlogs — use probe mode"
        if vendor == "codex" and in_known and statistics.mean(in_known) > 500_000:
            note = "codex input_tokens often cumulative/re-fed — compare tools+duration too"
        out.append(
            VendorRollup(
                vendor=vendor,
                sessions=len(sess),
                with_tokens=len(in_known),
                avg_in_tok=round(statistics.mean(in_known), 0) if in_known else None,
                avg_out_tok=round(statistics.mean(out_known), 0) if out_known else None,
                median_in_tok=round(statistics.median(in_known), 0) if in_known else None,
                avg_tools=round(statistics.mean(tools), 1) if tools else 0.0,
                avg_duration_min=round(statistics.mean(durs), 1) if durs else None,
                est_usd_per_session=round(statistics.mean(usd), 4) if usd else None,
                note=note,
            )
        )
    return out


def _write_fixture(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "math.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")


def _parse_cursor_json(raw: str) -> dict:
    """cursor-agent --output-format json may emit one JSON object or NDJSON."""
    raw = raw.strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        last = None
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                last = json.loads(line)
            except json.JSONDecodeError:
                continue
        return last or {}


def probe_cursor(*, workspace: Path, prompt: str, timeout: int) -> dict:
    agent = shutil.which("cursor-agent") or shutil.which("agent")
    if not agent:
        return {"backend": "cursor", "ok": False, "error": "cursor-agent/agent not on PATH"}
    cmd = [
        agent, "-p", "--mode", "ask", "--trust",
        "--model", "composer-2.5",
        "--workspace", str(workspace),
        "--output-format", "json",
        prompt,
    ]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    elapsed = round(time.time() - t0, 2)
    data = _parse_cursor_json(r.stdout or "")
    usage = data.get("usage") or {}
    in_tok = int(usage.get("inputTokens") or 0)
    out_tok = int(usage.get("outputTokens") or 0)
    cached = int(usage.get("cacheReadTokens") or 0)
    usd = est_cost("composer-2.5", in_tok, out_tok)
    if usd is None:
        # composer not in PRICING — use placeholder
        usd = (in_tok * COMPOSER_PRICING[1] + out_tok * COMPOSER_PRICING[2]) / 1_000_000
    return {
        "backend": "cursor",
        "ok": r.returncode == 0 and not data.get("is_error"),
        "model": "composer-2.5",
        "in_tok": in_tok,
        "out_tok": out_tok,
        "cached_tok": cached,
        "est_usd": round(usd, 6),
        "latency_s": elapsed,
        "exit": r.returncode,
        "result_preview": (data.get("result") or "")[:200],
        "error": None if r.returncode == 0 else (r.stderr or data.get("result") or "")[:300],
        "pricing_note": "composer $/MTok is ESTIMATED placeholder — relative compare only",
    }


def probe_llmx(*, prompt: str, timeout: int, model: str = "claude-opus-4-8") -> dict:
    """Bare llmx chat (no tools) — lower bound, not a full coding harness."""
    if not shutil.which("llmx"):
        return {"backend": "llmx-bare", "ok": False, "error": "llmx not on PATH"}
    env = os.environ.copy()
    env["LLMX_CALLER"] = "harness-cost-meter"
    cmd = [
        "llmx", "chat", "--subscription", "--json",
        "-m", model, "-e", "low", prompt,
    ]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
    elapsed = round(time.time() - t0, 2)
    # Prefer usage log attribution over parsing mixed stdout
    log = Path.home() / ".claude" / "llmx-usage.jsonl"
    in_tok = out_tok = reason = 0
    if log.is_file():
        for line in reversed(log.read_text().splitlines()[-20:]):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("caller") == "harness-cost-meter" and rec.get("model") == model:
                in_tok = int(rec.get("prompt_tokens") or 0)
                out_tok = int(rec.get("completion_tokens") or 0)
                reason = int(rec.get("reasoning_tokens") or 0)
                break
    usd = est_cost(model, in_tok, out_tok + reason) or 0.0
    err = None
    if r.returncode != 0:
        err = (r.stderr or r.stdout or "")[-400:]
    return {
        "backend": "llmx-bare",
        "ok": r.returncode == 0,
        "model": model,
        "in_tok": in_tok,
        "out_tok": out_tok + reason,
        "cached_tok": 0,
        "est_usd": round(usd, 6),
        "latency_s": elapsed,
        "exit": r.returncode,
        "result_preview": (r.stdout or "")[:200],
        "error": err,
        "pricing_note": "bare chat (no tools) — not comparable to full coding harness",
    }


def _find_pi() -> str | None:
    found = shutil.which("pi")
    if found:
        return found
    for cand in (
        REPO / ".scratch" / "bin" / "pi",
        REPO / ".scratch" / "pi-install" / "node_modules" / ".bin" / "pi",
        Path.home() / ".local" / "bin" / "pi",
    ):
        if cand.exists():
            return str(cand)
    return None


def _parse_pi_jsonl(raw: str) -> tuple[int, int, int, float, str]:
    """Sum turn_end usage from `pi --mode json` (avoids double-counting message_update)."""
    in_tok = out_tok = cached = 0
    cost = 0.0
    texts: list[str] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") == "turn_end":
            usage = (obj.get("message") or {}).get("usage") or {}
            in_tok += int(usage.get("input") or 0)
            out_tok += int(usage.get("output") or 0) + int(usage.get("reasoning") or 0)
            cached += int(usage.get("cacheRead") or 0)
            c = usage.get("cost") or {}
            if isinstance(c, dict):
                cost += float(c.get("total") or 0)
        msg = obj.get("message")
        if isinstance(msg, dict) and msg.get("role") == "assistant":
            content = msg.get("content")
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text" and part.get("text"):
                        texts.append(str(part["text"]))
            elif isinstance(content, str) and content:
                texts.append(content)
    return in_tok, out_tok, cached, cost, (texts[-1] if texts else "")[:200]


def probe_pi(*, workspace: Path, prompt: str, timeout: int) -> dict:
    """Headless Pi via `--mode json -p`. Needs API key; closes stdin (Pi hangs on open stdin)."""
    pi = _find_pi()
    if not pi:
        return {"backend": "pi", "ok": False, "error": "pi not installed (skip)"}

    provider = os.environ.get("PI_PROVIDER", "google")
    model = os.environ.get("PI_MODEL", "gemini-3-flash")
    # Sandbox often can't write ~/.pi — keep agent state under repo .scratch
    pi_home = REPO / ".scratch" / "pi-home"
    (pi_home / ".pi" / "agent").mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["HOME"] = str(pi_home)
    env["PI_TELEMETRY"] = "0"
    env["PI_OFFLINE"] = "1"

    cmd = [
        pi,
        "--provider", provider,
        "--model", model,
        "--thinking", "off",
        "--mode", "json",
        "-p",
        "--tools", "read",
        "--no-session",
        "--offline",
        prompt,
    ]
    t0 = time.time()
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workspace,
            env=env,
            stdin=subprocess.DEVNULL,  # open stdin → hang (measured 2026-07-09)
        )
    except subprocess.TimeoutExpired:
        return {
            "backend": "pi",
            "ok": False,
            "model": model,
            "error": f"timeout after {timeout}s",
            "latency_s": float(timeout),
        }
    elapsed = round(time.time() - t0, 2)
    in_tok, out_tok, cached, cost, preview = _parse_pi_jsonl(r.stdout or "")
    err = None
    if r.returncode != 0 or (not in_tok and not preview):
        err = (r.stderr or r.stdout or "")[-400:] or "empty pi output"
    return {
        "backend": "pi",
        "ok": r.returncode == 0 and bool(preview or in_tok),
        "model": f"{provider}/{model}",
        "in_tok": in_tok,
        "out_tok": out_tok,
        "cached_tok": cached,
        "est_usd": round(cost, 6),
        "latency_s": elapsed,
        "exit": r.returncode,
        "result_preview": preview,
        "error": err if not (r.returncode == 0 and (preview or in_tok)) else None,
        "pricing_note": "cost from pi usage.cost.total (provider list rates); HOME redirected to .scratch/pi-home",
    }


def run_probe(
    *,
    backends: list[str],
    prompt: str,
    timeout: int,
    dry_run: bool,
) -> list[dict]:
    results = []
    with tempfile.TemporaryDirectory(prefix="harness-cost-") as tmp:
        workspace = Path(tmp)
        _write_fixture(workspace)
        for b in backends:
            if dry_run:
                results.append({"backend": b, "ok": True, "dry_run": True})
                continue
            if b == "cursor":
                results.append(probe_cursor(workspace=workspace, prompt=prompt, timeout=timeout))
            elif b in ("llmx", "llmx-bare", "claude"):
                results.append(probe_llmx(prompt=prompt, timeout=timeout))
            elif b == "pi":
                results.append(probe_pi(workspace=workspace, prompt=prompt, timeout=timeout))
            else:
                results.append({"backend": b, "ok": False, "error": f"unknown backend: {b}"})
    return results


def _print_observe(rows: list[VendorRollup], *, project: str, days: int) -> None:
    print(f"# harness-cost observe — project={project} days={days}")
    print()
    hdr = f"{'vendor':8s} {'sess':5s} {'tok?':5s} {'avg_in':>10s} {'med_in':>10s} {'avg_out':>10s} {'tools':>7s} {'min':>6s} {'$/sess':>8s}"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        def fmt(x, w, as_int=False):
            if x is None:
                return f"{'—':>{w}}"
            return f"{int(x):>{w},}" if as_int else f"{x:>{w}}"

        print(
            f"{r.vendor:8s} {r.sessions:5d} {r.with_tokens:5d} "
            f"{fmt(r.avg_in_tok, 10, True)} {fmt(r.median_in_tok, 10, True)} "
            f"{fmt(r.avg_out_tok, 10, True)} {r.avg_tools:7.1f} "
            f"{fmt(r.avg_duration_min, 6)} "
            f"{('$' + f'{r.est_usd_per_session:.3f}') if r.est_usd_per_session is not None else '—':>8s}"
        )
        if r.note:
            print(f"         note: {r.note}")
    print()
    print("Notes: $/sess uses usage-check PRICING (API list rates); subscription = $0 marginal.")
    print("       Cursor often has 0 token fields — run `probe --backends cursor` for a live sample.")
    print("       Pi not installed → skip; install earendil-works/pi to extend probe.")


def _print_probe(rows: list[dict]) -> None:
    print("# harness-cost probe")
    print()
    for r in rows:
        if r.get("dry_run"):
            print(f"  {r['backend']}: dry-run ok")
            continue
        status = "OK" if r.get("ok") else "FAIL"
        print(f"  [{status}] {r.get('backend')} model={r.get('model')}")
        if r.get("error") and not r.get("ok"):
            print(f"         error: {r['error'][:200]}")
            continue
        print(
            f"         in={r.get('in_tok'):,} out={r.get('out_tok'):,} "
            f"cached={r.get('cached_tok'):,} est_usd=${r.get('est_usd')} "
            f"latency={r.get('latency_s')}s"
        )
        if r.get("pricing_note"):
            print(f"         {r['pricing_note']}")
        if r.get("result_preview"):
            print(f"         preview: {r['result_preview'][:120]!r}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")

    obs = sub.add_parser("observe", help="agentlogs vendor rollup (default)")
    obs.add_argument("--db", type=Path, default=DEFAULT_DB)
    obs.add_argument("--project", default="agent-infra")
    obs.add_argument("--days", type=int, default=7)
    obs.add_argument("--min-tools", type=int, default=0)
    obs.add_argument("--json", action="store_true")

    pr = sub.add_parser("probe", help="live fixed-task probe on available backends")
    pr.add_argument("--backends", default="cursor", help="comma list: cursor,llmx,pi")
    pr.add_argument("--prompt", default=DEFAULT_TASK)
    pr.add_argument("--timeout", type=int, default=120)
    pr.add_argument("--dry-run", action="store_true")
    pr.add_argument("--json", action="store_true")

    # Allow `script.py --project X` as shorthand for observe
    if argv is None:
        argv = sys.argv[1:]
    # just recipes sometimes forward a literal `--`
    while argv and argv[0] == "--":
        argv = argv[1:]
    if not argv or argv[0] not in ("observe", "probe", "-h", "--help"):
        argv = ["observe", *argv]

    args = ap.parse_args(argv)
    if args.cmd is None or args.cmd == "observe":
        # re-parse if bare invoke
        if not hasattr(args, "project"):
            args = obs.parse_args([])
        rows = observe(db=args.db, project=args.project, days=args.days, min_tools=args.min_tools)
        if args.json:
            print(json.dumps({"mode": "observe", "project": args.project, "days": args.days,
                              "vendors": [asdict(r) for r in rows]}, indent=2))
        else:
            _print_observe(rows, project=args.project, days=args.days)
        return 0

    backends = [b.strip() for b in args.backends.split(",") if b.strip()]
    results = run_probe(backends=backends, prompt=args.prompt, timeout=args.timeout, dry_run=args.dry_run)
    if args.json:
        print(json.dumps({"mode": "probe", "results": results}, indent=2))
    else:
        _print_probe(results)
    return 0 if all(r.get("ok") or r.get("dry_run") for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
