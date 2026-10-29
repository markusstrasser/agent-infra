#!/usr/bin/env python3
"""otel_sink.py — local OTLP/HTTP-JSON receiver for Claude Code telemetry, and a cost report.

Claude Code exports `claude_code.api_request` log events with a `query_source` attribute, and
side queries such as `agent_summary` reach no transcript on disk; this export is the only place
they show. A flamerix gist (2026-10-29 pointer ledger) measured agent_summary at ~16% of spend;
this sink measures ours before anything patches the client.

  serve   listen on 127.0.0.1:4318, append each POST body as one JSON line to
          ~/.local/state/claude-otel/<UTC date>.jsonl
  report  sum api_request events by query_source: requests, cost_usd, input/output/cache tokens

Claude Code side (settings.json env): CLAUDE_CODE_ENABLE_TELEMETRY=1, OTEL_LOGS_EXPORTER=otlp,
OTEL_EXPORTER_OTLP_PROTOCOL=http/json, OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318.

Usage:
  uv run python3 scripts/otel_sink.py serve
  uv run python3 scripts/otel_sink.py report [--since YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

STATE = Path.home() / ".local" / "state" / "claude-otel"
PORT = 4318


class Sink(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802 - http.server API
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        STATE.mkdir(parents=True, exist_ok=True)
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with (STATE / f"{day}.jsonl").open("ab") as f:
            f.write(json.dumps({"path": self.path, "ct": self.headers.get("Content-Type")}).encode()[:-1]
                    + b', "body": ' + (body if self.headers.get("Content-Type", "").startswith("application/json")
                                       else json.dumps(body.hex()).encode()) + b"}\n")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - base signature
        pass


def attrs(kv: list[dict]) -> dict:
    out = {}
    for a in kv:
        v = a.get("value", {})
        out[a["key"]] = next(iter(v.values()), None) if v else None
    return out


def events(since: str):
    for path in sorted(STATE.glob("*.jsonl")):
        if path.stem < since:
            continue
        for line in path.open():
            rec = json.loads(line)
            if not rec["path"].endswith("/v1/logs") or not isinstance(rec["body"], dict):
                continue
            for rl in rec["body"].get("resourceLogs", []):
                for sl in rl.get("scopeLogs", []):
                    for lr in sl.get("logRecords", []):
                        a = attrs(lr.get("attributes", []))
                        if a.get("event.name") == "api_request" or (lr.get("body") or {}).get("stringValue") == "claude_code.api_request":
                            yield a


def cmd_report(args: argparse.Namespace) -> None:
    rows: dict[str, dict] = defaultdict(lambda: defaultdict(float))
    for a in events(args.since):
        r = rows[a.get("query_source") or "(none)"]
        r["requests"] += 1
        for k in ("cost_usd", "input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens"):
            r[k] += float(a.get(k) or 0)
    total = sum(r["cost_usd"] for r in rows.values()) or 1
    reqs = sum(r["requests"] for r in rows.values()) or 1
    print(f"{'query_source':28s} {'reqs':>6s} {'req%':>6s} {'cost$':>9s} {'cost%':>6s} {'in':>10s} {'out':>9s} {'cache_rd':>11s}")
    for name, r in sorted(rows.items(), key=lambda kv: -kv[1]["cost_usd"]):
        print(f"{name:28s} {int(r['requests']):6d} {100 * r['requests'] / reqs:5.1f}% {r['cost_usd']:9.2f} "
              f"{100 * r['cost_usd'] / total:5.1f}% {int(r['input_tokens']):10d} {int(r['output_tokens']):9d} "
              f"{int(r['cache_read_tokens']):11d}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("serve")
    r = sub.add_parser("report")
    r.add_argument("--since", default="0000-00-00")
    args = p.parse_args()
    if args.cmd == "serve":
        ThreadingHTTPServer(("127.0.0.1", PORT), Sink).serve_forever()
    else:
        cmd_report(args)


if __name__ == "__main__":
    main()
