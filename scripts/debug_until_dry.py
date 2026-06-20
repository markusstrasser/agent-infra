#!/usr/bin/env python3
"""debug-until-dry — memo-driven wave loop of cheap cursor scouts until the audit is dry.

llm: required (cursor composer scouts; optional opus between-wave verifier)

The orchestrator fires ONE command; it runs wave by wave:

  wave: K cursor scouts read the audit MEMO + the code → append NEW findings,
        verify/refute the memo's `unverified` entries (strict block output)
  merge: deterministic dedup (claim hash) → memo; new findings land `unverified`
  verify: one between-wave reader (cursor|opus|none) adjudicates `unverified`
          entries → confirmed|refuted with evidence, rewrites the memo
  dry?:  new_info = (#new claims) + (#status changes). Stop after `--dry-stop`
         consecutive waves with new_info == 0  → the audit is dry / complete.

The MEMO is the externalized convergence state: every wave reads it, so "don't
re-report" + "what's still unverified" are structural, not in the model's head —
that is what makes the loop reliable (architecture-over-instructions, P1).

State of truth: <memo>.json (machine). Human audit: <memo> (.md, rendered each wave).

Usage:
  debug_until_dry.py /path/to/repo
  debug_until_dry.py /path/to/repo recent --max-waves 5 --workers 3 --scouts-per-wave 4
  debug_until_dry.py /path/to/repo --verifier opus --dry-stop 2
  debug_until_dry.py /path/to/repo --dry-run        # trace the loop, no token spend
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from debug_scout import AGENT, build_scopes, load_prompt_template  # noqa: E402
from fan_out_lib import run_parallel  # noqa: E402
from tool_contract import LlmClass, print_llm_header  # noqa: E402

CURSOR_MODEL = "composer-2.5"
SCOUT_TIMEOUT = 600
VERIFY_TIMEOUT = 600
OPUS_TIMEOUT = 1200

# Strict per-finding block the wave scout must emit (we own this format, not findings_parse).
FINDING_RE = re.compile(
    r"^##\s+FINDING\b.*?$"  # header
    r"(?P<body>.*?)"
    r"(?=^##\s+FINDING\b|\Z)",
    re.MULTILINE | re.DOTALL,
)
FIELD_RE = re.compile(r"^\s*[-*]\s*\*\*(?P<k>[A-Za-z][A-Za-z /-]*?):?\*\*\s*(?P<v>.*?)\s*$", re.MULTILINE)
VERDICT_CONFIRMED = {"CONFIRMED", "CONFIRM", "REAL", "TRUE"}
VERDICT_REFUTED = {"REFUTED", "REFUTE", "FALSE", "NOT_A_BUG", "REJECTED"}


def claim_hash(claim: str) -> str:
    return hashlib.sha256(re.sub(r"\s+", " ", claim.strip().lower()).encode()).hexdigest()[:12]


@dataclass
class Finding:
    dedupe: str
    claim: str
    domain: str = "code"
    severity: str = "P?"
    file: str = ""
    evidence: str = ""
    verification: str = ""
    falsifier: str = ""
    status: str = "unverified"  # unverified | confirmed | refuted
    first_wave: int = 0
    last_wave: int = 0


# ── memo state ────────────────────────────────────────────────────────────────
def load_memo(json_path: Path) -> dict[str, Finding]:
    if not json_path.is_file():
        return {}
    raw = json.loads(json_path.read_text())
    return {k: Finding(**v) for k, v in raw.get("findings", {}).items()}


def save_memo(json_path: Path, md_path: Path, memo: dict[str, Finding], *, repo: Path, wave: int) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)  # survive a vanished audit_dir mid-run
    json_path.write_text(json.dumps(
        {"repo": str(repo), "wave": wave, "updated": datetime.now(timezone.utc).isoformat(),
         "findings": {k: asdict(v) for k, v in memo.items()}},
        indent=2,
    ) + "\n")
    md_path.write_text(render_memo_md(memo, repo=repo, wave=wave))


def render_memo_md(memo: dict[str, Finding], *, repo: Path, wave: int) -> str:
    order = {"confirmed": 0, "unverified": 1, "refuted": 2}
    sev = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P?": 4}
    items = sorted(memo.values(), key=lambda f: (order.get(f.status, 9), sev.get(f.severity, 9)))
    n_conf = sum(1 for f in memo.values() if f.status == "confirmed")
    n_unv = sum(1 for f in memo.values() if f.status == "unverified")
    n_ref = sum(1 for f in memo.values() if f.status == "refuted")
    out = [
        f"# Bug-hunt audit memo — {Path(repo).name}",
        f"_wave {wave} · {date.today().isoformat()} · "
        f"**{n_conf} confirmed** · {n_unv} unverified · {n_ref} refuted_",
        "",
    ]
    for f in items:
        out.append(f"## {f.status.upper()} [{f.severity}] — {f.claim}")
        out.append(f"- **id:** `{f.dedupe}` · **domain:** {f.domain} · "
                   f"**waves:** {f.first_wave}→{f.last_wave}")
        if f.file:
            out.append(f"- **file:** {f.file}")
        if f.evidence:
            out.append(f"- **evidence:** {f.evidence}")
        if f.verification:
            out.append(f"- **verification:** {f.verification}")
        if f.falsifier:
            out.append(f"- **falsifier:** {f.falsifier}")
        out.append("")
    return "\n".join(out)


def memo_digest_for_prompt(memo: dict[str, Finding]) -> str:
    """Compact memo block the next wave reads — so scouts skip knowns + verify unverified."""
    if not memo:
        return "(empty — this is wave 1; report everything you find)"
    lines = []
    for f in memo.values():
        if f.status == "refuted":
            continue
        tag = "✓CONFIRMED" if f.status == "confirmed" else "?UNVERIFIED"
        lines.append(f"- [{tag}] `{f.dedupe}` {f.claim}  ({f.file})")
    return "\n".join(lines) or "(only refuted entries so far)"


# ── parsing scout output ──────────────────────────────────────────────────────
def parse_wave_output(text: str) -> list[Finding]:
    findings: list[Finding] = []
    for m in FINDING_RE.finditer(text):
        body = m.group("body")
        fields = {k.strip().lower().replace(" ", "_"): v.strip()
                  for k, v in FIELD_RE.findall(body)}
        claim = fields.get("claim", "").strip()
        if not claim:
            continue
        verdict = fields.get("verdict", "").upper().replace(" ", "_")
        status = ("confirmed" if any(v in verdict for v in VERDICT_CONFIRMED)
                  else "refuted" if any(v in verdict for v in VERDICT_REFUTED)
                  else "unverified")
        findings.append(Finding(
            dedupe=claim_hash(claim), claim=claim,
            domain=fields.get("domain", "code").split("|")[0].strip() or "code",
            severity=fields.get("severity", "P?").strip() or "P?",
            file=fields.get("evidence", "").split(";")[0][:120] if "evidence" in fields else "",
            evidence=fields.get("evidence", ""),
            verification=fields.get("verification", ""),
            falsifier=fields.get("falsifier", ""),
            status=status,
        ))
    return findings


# ── cursor / opus calls ───────────────────────────────────────────────────────
def cursor_ask(repo: Path, prompt: str, timeout: int, dry_run: bool) -> tuple[bool, str]:
    if dry_run:
        return True, "## NO_FINDINGS\n(dry-run — no cursor call made)"
    if not AGENT.is_file():
        return False, "agent CLI not found (~/.local/bin/agent)"
    cmd = [str(AGENT), "-p", "--trust", "--mode", "ask", "--model", CURSOR_MODEL,
           "--workspace", str(repo), "--output-format", "text", prompt]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "(timeout)"
    return r.returncode == 0, (r.stdout.strip() or r.stderr.strip() or "(empty)")


def opus_adjudicate(prompt: str, timeout: int, dry_run: bool) -> tuple[bool, str]:
    if dry_run:
        return True, "{}"
    cmd = ["llmx", "chat", "--subscription", "-m", "claude-opus-4-8", "-e", "high",
           "--timeout", str(timeout), prompt]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 60)
    except subprocess.TimeoutExpired:
        return False, "(opus timeout)"
    return r.returncode == 0, (r.stdout.strip() or r.stderr.strip() or "(empty)")


# ── wave prompts ──────────────────────────────────────────────────────────────
def wave_scout_prompt(project: str, scope_block: str, memo: dict[str, Finding], wave: int) -> str:
    axes = load_prompt_template()  # borrow the shared check-axes + verify discipline
    # keep only the guidance up to its output block; we impose our own block below
    axes = axes.split("## Output format", 1)[0]
    return (
        "/debug\n\n"
        "**AUDIT ONLY — you WRITE FINDINGS, you do NOT fix anything.** Strictly read-only: do NOT "
        "edit, patch, refactor, create, or delete any file; do NOT run mutating or destructive "
        "commands; do NOT commit. Your ENTIRE output is the finding blocks specified below — fixing "
        "is the orchestrator's job, never yours.\n\n"
        + axes.replace("{project}", project).replace("{scout_id}", f"w{wave}")
        .replace("{scope_block}", scope_block).replace("{extra_prompt}", "(none)")
        + "\n## Audit memo so far (do NOT re-report a known claim; instead VERIFY any `?UNVERIFIED`)\n"
        + memo_digest_for_prompt(memo)
        + "\n\n## Output format (STRICT — one block per finding, nothing else)\n"
        "For each NEW bug, or each `?UNVERIFIED` memo entry you can now settle, emit:\n"
        "```\n"
        "## FINDING\n"
        "- **Domain:** code | scientific | methodological | operational\n"
        "- **Severity:** P0 | P1 | P2 | P3\n"
        "- **Claim:** one sentence (reuse the EXACT wording of a memo entry you are verifying)\n"
        "- **Evidence:** file:line and/or command output\n"
        "- **Verification:** git log cite or cheap probe run\n"
        "- **Verdict:** CONFIRMED | SUSPECT | REFUTED\n"
        "- **Falsifier:** what would disprove it\n"
        "```\n"
        "If you find nothing new and can settle nothing, output exactly `## NO_FINDINGS`.\n"
    )


def verifier_prompt(memo: dict[str, Finding]) -> str:
    unverified = [f for f in memo.values() if f.status == "unverified"]
    block = "\n".join(
        f"## FINDING\n- **Claim:** {f.claim}\n- **Evidence:** {f.evidence}\n"
        f"- **Falsifier:** {f.falsifier}" for f in unverified
    )
    return (
        "/debug\n\n"
        "**AUDIT ONLY — adjudicate and WRITE, do NOT fix or edit anything.** Strictly read-only: no "
        "file edits, no mutating commands, no commits. Your output is verdict blocks only.\n\n"
        "You are the between-wave verifier for a bug-hunt audit. Read the repo and "
        "adjudicate each UNVERIFIED finding below. For each, emit a block with the EXACT "
        "same Claim and a Verdict (CONFIRMED with file:line+probe, or REFUTED with why the "
        "mechanism is wrong). Do not invent new findings.\n\n" + block +
        "\n\n## Output (strict, one block per finding)\n"
        "## FINDING\n- **Claim:** <exact claim>\n- **Evidence:** file:line / probe\n"
        "- **Verdict:** CONFIRMED | REFUTED\n"
    )


# ── merge / verify ────────────────────────────────────────────────────────────
def merge_into_memo(memo: dict[str, Finding], found: list[Finding], wave: int) -> tuple[int, int]:
    new_claims = status_changes = 0
    for f in found:
        existing = memo.get(f.dedupe)
        if existing is None:
            f.first_wave = f.last_wave = wave
            memo[f.dedupe] = f
            new_claims += 1
            continue
        existing.last_wave = wave
        # a later wave can only PROMOTE an unverified entry to confirmed/refuted
        if existing.status == "unverified" and f.status in ("confirmed", "refuted"):
            existing.status = f.status
            existing.evidence = f.evidence or existing.evidence
            existing.verification = f.verification or existing.verification
            status_changes += 1
    return new_claims, status_changes


def apply_verdicts(memo: dict[str, Finding], verdict_findings: list[Finding]) -> int:
    changes = 0
    by_hash = {f.dedupe: f for f in verdict_findings}
    for h, vf in by_hash.items():
        cur = memo.get(h)
        if cur and cur.status == "unverified" and vf.status in ("confirmed", "refuted"):
            cur.status = vf.status
            cur.evidence = vf.evidence or cur.evidence
            changes += 1
    return changes


# ── main loop ─────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo", type=Path)
    ap.add_argument("scope", nargs="?", default="recent", help="recent | path | free-text focus")
    ap.add_argument("--max-waves", type=int, default=5)
    ap.add_argument("--workers", type=int, default=3, help="parallel cursor scouts in flight")
    ap.add_argument("--scouts-per-wave", type=int, default=4)
    ap.add_argument("--dry-stop", type=int, default=1, help="consecutive no-new-info waves → stop")
    ap.add_argument("--verifier", choices=["cursor", "opus", "none"], default="cursor")
    ap.add_argument("--memo", type=Path, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print_llm_header(LlmClass.REQUIRED)
    repo = args.repo.expanduser().resolve()
    if not repo.is_dir():
        print(f"repo not found: {repo}", file=sys.stderr)
        return 2

    audit_dir = repo / "docs" / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    md_path = args.memo or audit_dir / f"{date.today().isoformat()}-bughunt-memo.md"
    json_path = md_path.with_suffix(".json")
    memo = load_memo(json_path)

    print(f"debug-until-dry: {repo.name} · scope={args.scope} · verifier={args.verifier} · "
          f"max-waves={args.max_waves} · {args.scouts_per_wave}×{args.workers} workers"
          + (" · DRY-RUN" if args.dry_run else ""))
    print(f"memo: {md_path}")

    dry_streak = 0
    for wave in range(1, args.max_waves + 1):
        scopes = build_scopes(repo, args.scope, args.scouts_per_wave)
        items = [(sid, wave_scout_prompt(repo.name, block, memo, wave)) for sid, block in scopes]

        def run_one(item: tuple[str, str]) -> dict:
            sid, prompt = item
            ok, body = cursor_ask(repo, prompt, SCOUT_TIMEOUT, args.dry_run)
            return {"sid": sid, "ok": ok, "body": body}

        results = run_parallel(items, run_one, workers=args.workers)
        found: list[Finding] = []
        for res in results:
            if isinstance(res, dict):
                found.extend(parse_wave_output(res["body"]))
        new_claims, promoted = merge_into_memo(memo, found, wave)

        verdict_changes = 0
        if args.verifier != "none" and any(f.status == "unverified" for f in memo.values()):
            if args.verifier == "cursor":
                ok, body = cursor_ask(repo, verifier_prompt(memo), VERIFY_TIMEOUT, args.dry_run)
            else:  # opus
                ok, body = opus_adjudicate(verifier_prompt(memo), OPUS_TIMEOUT, args.dry_run)
            if ok:
                verdict_changes = apply_verdicts(memo, parse_wave_output(body))

        new_info = new_claims + promoted + verdict_changes
        if not args.dry_run:  # dry-run writes no files (matches debug_scout convention)
            save_memo(json_path, md_path, memo, repo=repo, wave=wave)
        n_conf = sum(1 for f in memo.values() if f.status == "confirmed")
        print(f"  wave {wave}: +{new_claims} new · {promoted} promoted · "
              f"{verdict_changes} verified → new_info={new_info} · {n_conf} confirmed total")

        dry_streak = dry_streak + 1 if new_info == 0 else 0
        if dry_streak >= args.dry_stop:
            print(f"  DRY after wave {wave} ({dry_streak} quiet wave[s]) — audit complete.")
            break
    else:
        print(f"  reached --max-waves={args.max_waves} (not yet dry).")

    n_conf = sum(1 for f in memo.values() if f.status == "confirmed")
    print(f"\nfindings: {n_conf} confirmed / {len(memo)} total")
    print(f"drill:    cat {json_path}")
    print(f"next:     read {md_path}  (confirmed bugs first)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
