#!/usr/bin/env python3
"""debug-until-dry — memo-driven wave loop of cheap read-only scouts until the audit is dry.

llm: required (cursor and/or codex scouts; cursor|codex|opus between-wave verifier)

The orchestrator fires ONE command; it runs wave by wave:

  wave: K scouts (cursor ask-mode and/or codex read-only sandbox) read the audit
        MEMO + the code → append NEW findings, verify/refute the memo's
        `unverified` entries (strict block output)
  merge: deterministic dedup (claim hash) → memo; new findings land `unverified`
  verify: one between-wave reader (cursor|codex|opus|none) adjudicates `unverified`
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
  debug_until_dry.py /path/to/repo --scout-backend codex --scout-effort low
  debug_until_dry.py /path/to/repo --scout-backend cursor,codex   # mixed wave (lens diversity)
  debug_until_dry.py /path/to/repo --verifier opus --dry-stop 2
  debug_until_dry.py /path/to/repo --verifier codex --verifier-model gpt-5.5
  debug_until_dry.py /path/to/repo --dry-run        # trace the loop, no token spend
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from debug_scout import build_scopes, load_prompt_template  # noqa: E402
from fan_out_lib import run_parallel  # noqa: E402
from scout_backends import parse_backend_spec, scout_ask  # noqa: E402
from tool_contract import LlmClass, print_llm_header  # noqa: E402

OPUS_TIMEOUT = 1200

# Strict per-finding block the wave scout must emit (we own this format, not findings_parse).
FINDING_RE = re.compile(
    r"^##\s+FINDING\b.*?$"  # header
    r"(?P<body>.*?)"
    r"(?=^##\s+FINDING\b|\Z)",
    re.MULTILINE | re.DOTALL,
)
FIELD_RE = re.compile(
    r"^\s*[-*]\s*\*\*(?P<k>[A-Za-z][A-Za-z /-]*?):?\*\*\s*(?P<v>.*?)\s*$", re.MULTILINE
)
VERDICT_CONFIRMED = {"CONFIRMED", "CONFIRM", "REAL", "TRUE"}
VERDICT_REFUTED = {"REFUTED", "REFUTE", "FALSE", "NOT_A_BUG", "REJECTED"}


def claim_hash(claim: str) -> str:
    return hashlib.sha256(
        re.sub(r"\s+", " ", claim.strip().lower()).encode()
    ).hexdigest()[:12]


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


def save_memo(
    json_path: Path,
    md_path: Path,
    memo: dict[str, Finding],
    *,
    repo: Path,
    wave: int,
    converged: bool | None = None,
    final_new: int = 0,
    total_refutes: int = 0,
) -> None:
    json_path.parent.mkdir(
        parents=True, exist_ok=True
    )  # survive a vanished audit_dir mid-run
    json_path.write_text(
        json.dumps(
            {
                "repo": str(repo),
                "wave": wave,
                "converged": converged,
                "new_in_final_wave": final_new,
                "total_refutes": total_refutes,
                "updated": datetime.now(timezone.utc).isoformat(),
                "findings": {k: asdict(v) for k, v in memo.items()},
            },
            indent=2,
        )
        + "\n"
    )
    md_path.write_text(
        render_memo_md(
            memo,
            repo=repo,
            wave=wave,
            converged=converged,
            final_new=final_new,
            total_refutes=total_refutes,
        )
    )


def render_memo_md(
    memo: dict[str, Finding],
    *,
    repo: Path,
    wave: int,
    converged: bool | None = None,
    final_new: int = 0,
    total_refutes: int = 0,
) -> str:
    order = {"confirmed": 0, "unverified": 1, "refuted": 2}
    sev = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P?": 4}
    items = sorted(
        memo.values(), key=lambda f: (order.get(f.status, 9), sev.get(f.severity, 9))
    )
    n_conf = sum(1 for f in memo.values() if f.status == "confirmed")
    n_unv = sum(1 for f in memo.values() if f.status == "unverified")
    n_ref = sum(1 for f in memo.values() if f.status == "refuted")
    # Fix 1: never silently read as complete — state convergence honestly.
    if converged is True:
        status = f"✅ CONVERGED (dry) at wave {wave}"
    elif converged is False:
        status = (
            f"⚠ INCOMPLETE — hit max-waves, did NOT converge "
            f"({final_new} new in final wave; re-run to continue the audit)"
        )
    else:
        status = f"in progress (wave {wave})"
    # Fix 2: a 0-refute run means no independent adjudication happened — say so.
    refute_note = ""
    if converged is not None and n_conf >= 10 and total_refutes == 0:
        refute_note = (
            " · ⚠ 0 refutations — 'confirmed' is scout self-assessment, "
            "NOT independently adjudicated"
        )
    out = [
        f"# Bug-hunt audit memo — {Path(repo).name}",
        f"_{status} · {date.today().isoformat()} · "
        f"**{n_conf} confirmed** · {n_unv} unverified · {n_ref} refuted{refute_note}_",
        "",
    ]
    for f in items:
        out.append(f"## {f.status.upper()} [{f.severity}] — {f.claim}")
        out.append(
            f"- **id:** `{f.dedupe}` · **domain:** {f.domain} · "
            f"**waves:** {f.first_wave}→{f.last_wave}"
        )
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
        fields = {
            k.strip().lower().replace(" ", "_"): v.strip()
            for k, v in FIELD_RE.findall(body)
        }
        claim = fields.get("claim", "").strip()
        if not claim:
            continue
        verdict = fields.get("verdict", "").upper().replace(" ", "_")
        status = (
            "confirmed"
            if any(v in verdict for v in VERDICT_CONFIRMED)
            else "refuted"
            if any(v in verdict for v in VERDICT_REFUTED)
            else "unverified"
        )
        findings.append(
            Finding(
                dedupe=claim_hash(claim),
                claim=claim,
                domain=fields.get("domain", "code").split("|")[0].strip() or "code",
                severity=fields.get("severity", "P?").strip() or "P?",
                file=fields.get("evidence", "").split(";")[0][:120]
                if "evidence" in fields
                else "",
                evidence=fields.get("evidence", ""),
                verification=fields.get("verification", ""),
                falsifier=fields.get("falsifier", ""),
                status=status,
            )
        )
    return findings


# ── verifier-lane opus call (scout lanes live in scout_backends) ─────────────
def opus_adjudicate(prompt: str, timeout: int, dry_run: bool) -> tuple[bool, str]:
    if dry_run:
        return True, "{}"
    cmd = [
        "llmx",
        "chat",
        "--subscription",
        "-m",
        "claude-opus-4-8",
        "-e",
        "high",
        "--timeout",
        str(timeout),
        prompt,
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 60)
    except subprocess.TimeoutExpired:
        return False, "(opus timeout)"
    return r.returncode == 0, (r.stdout.strip() or r.stderr.strip() or "(empty)")


# ── wave prompts ──────────────────────────────────────────────────────────────
def wave_scout_prompt(
    project: str, scope_block: str, memo: dict[str, Finding], wave: int
) -> str:
    axes = load_prompt_template()  # borrow the shared check-axes + verify discipline
    # keep only the guidance up to its output block; we impose our own block below
    axes = axes.split("## Output format", 1)[0]
    return (  # /debug + audit-only banner are inherited from debug_scout_prompt.md (single source)
        axes.replace("{project}", project)
        .replace("{scout_id}", f"w{wave}")
        .replace("{scope_block}", scope_block)
        .replace("{extra_prompt}", "(none)")
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


def _finding_blocks(fs: list[Finding]) -> str:
    return "\n".join(
        f"## FINDING\n- **Claim:** {f.claim}\n- **Evidence:** {f.evidence}\n"
        f"- **Falsifier:** {f.falsifier}"
        for f in fs
    )


def verifier_prompt(unverified: list[Finding], challenged: list[Finding]) -> str:
    """Two-tier adversarial judge: scout cheap-probe = grade tier; this = judge tier.
    `challenged` are scout-CONFIRMED findings re-challenged independently (guilty-until-proven);
    `unverified` are unsettled findings to adjudicate. Source: defending-harness-verifier-patterns."""
    parts = [
        "/debug\n\n"
        "**AUDIT ONLY — adjudicate and WRITE, do NOT fix or edit anything.** Strictly read-only: no "
        "file edits, no mutating commands, no commits. Verdict blocks only; invent no new findings.\n\n"
        "You are the INDEPENDENT between-wave JUDGE for a bug-hunt audit. The scout's cheap probe was "
        "the grade tier; you are the adversarial judge tier. Verdict each finding by INDEPENDENTLY "
        "reproducing its mechanism from the cited file:line — do not trust the scout's word.\n"
    ]
    if challenged:
        parts.append(
            "\n### ADVERSARIAL RE-CHALLENGE — these are scout-CONFIRMED; try to DISPROVE each.\n"
            "Guilty until proven innocent: emit **REFUTED** unless YOU independently reproduce the "
            "mechanism. Plausible-but-unreproduced → REFUTED. Same symptom, different mechanism → "
            "REFUTED.\n\n" + _finding_blocks(challenged) + "\n"
        )
    if unverified:
        parts.append(
            "\n### ADJUDICATE (unsettled) — CONFIRMED only with file:line + a probe you ran, else "
            "REFUTED.\n\n" + _finding_blocks(unverified) + "\n"
        )
    parts.append(
        "\n## Output (strict, one block per finding — reuse the EXACT Claim)\n"
        "## FINDING\n- **Claim:** <exact claim>\n- **Evidence:** file:line / probe you ran\n"
        "- **Verdict:** CONFIRMED | REFUTED\n"
    )
    return "".join(parts)


# ── merge / verify ────────────────────────────────────────────────────────────
def merge_into_memo(
    memo: dict[str, Finding], found: list[Finding], wave: int
) -> tuple[int, int]:
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


def apply_verdicts(
    memo: dict[str, Finding], verdict_findings: list[Finding]
) -> tuple[int, int]:
    """Returns (changes, refutes). Adjudicates unverified AND allows the adversarial judge to
    DEMOTE a scout-confirmed finding to refuted (the independent-cull the design promised)."""
    changes = refutes = 0
    by_hash = {f.dedupe: f for f in verdict_findings}
    for h, vf in by_hash.items():
        cur = memo.get(h)
        if not cur:
            continue
        if cur.status == "unverified" and vf.status in ("confirmed", "refuted"):
            cur.status = vf.status
            cur.evidence = vf.evidence or cur.evidence
            changes += 1
            refutes += vf.status == "refuted"
        elif (
            cur.status == "confirmed" and vf.status == "refuted"
        ):  # adversarial demotion
            cur.status = "refuted"
            cur.evidence = vf.evidence or cur.evidence
            changes += 1
            refutes += 1
    return changes, refutes


# ── main loop ─────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("repo", type=Path)
    ap.add_argument(
        "scope", nargs="?", default="recent", help="recent | path | free-text focus"
    )
    ap.add_argument("--max-waves", type=int, default=5)
    ap.add_argument("--workers", type=int, default=3, help="parallel scouts in flight")
    ap.add_argument("--scouts-per-wave", type=int, default=4)
    ap.add_argument(
        "--dry-stop", type=int, default=1, help="consecutive no-new-info waves → stop"
    )
    ap.add_argument(
        "--scout-backend",
        default="cursor",
        help="cursor | codex | comma-list (round-robin across scouts, e.g. cursor,codex)",
    )
    ap.add_argument("--scout-model", default="", help="override backend default model")
    ap.add_argument(
        "--scout-effort", default="", help="codex reasoning effort (default: medium)"
    )
    ap.add_argument("--scout-timeout", type=int, default=600, help="seconds per scout")
    ap.add_argument(
        "--verifier", choices=["cursor", "codex", "opus", "none"], default="cursor"
    )
    ap.add_argument(
        "--verifier-model", default="", help="override verifier backend model"
    )
    ap.add_argument(
        "--verify-timeout", type=int, default=600, help="seconds per verify pass"
    )
    ap.add_argument("--memo", type=Path, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    try:
        scout_backends = parse_backend_spec(args.scout_backend)
    except ValueError as e:
        ap.error(str(e))

    # Line-buffer stdout: under `uv run` (non-TTY) Python fully buffers stdout, so all
    # per-wave/per-scout progress is invisible until exit — a slow run is then
    # indistinguishable from a hung one (cost a 42-min blind wedge, 2026-06-22).
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]

    print_llm_header(LlmClass.REQUIRED)
    repo = args.repo.expanduser().resolve()
    if not repo.is_dir():
        print(f"repo not found: {repo}", file=sys.stderr)
        return 2

    audit_dir = repo / "docs" / "audit"
    if (
        not args.dry_run
    ):  # dry-run touches nothing in the target repo (save_memo re-mkdirs on real runs)
        audit_dir.mkdir(parents=True, exist_ok=True)
    md_path = args.memo or audit_dir / f"{date.today().isoformat()}-bughunt-memo.md"
    json_path = md_path.with_suffix(".json")
    memo = load_memo(json_path)

    print(
        f"debug-until-dry: {repo.name} · scope={args.scope} · "
        f"scouts={'+'.join(scout_backends)} · verifier={args.verifier} · "
        f"max-waves={args.max_waves} · {args.scouts_per_wave}×{args.workers} workers"
        + (" · DRY-RUN" if args.dry_run else "")
    )
    print(f"memo: {md_path}")

    dry_streak = 0
    converged = False
    total_refutes = 0
    final_new = 0
    for wave in range(1, args.max_waves + 1):
        scopes = build_scopes(repo, args.scope, args.scouts_per_wave)
        # round-robin the backend list across the wave's scouts (mixed = lens diversity)
        items = [
            (
                sid,
                scout_backends[i % len(scout_backends)],
                wave_scout_prompt(repo.name, block, memo, wave),
            )
            for i, (sid, block) in enumerate(scopes)
        ]

        def run_one(item: tuple[str, str, str]) -> dict:
            sid, backend, prompt = item
            t0 = time.monotonic()
            ok, body = scout_ask(
                backend,
                repo,
                prompt,
                timeout=args.scout_timeout,
                model=args.scout_model,
                effort=args.scout_effort,
                dry_run=args.dry_run,
            )
            outcome = "ok" if ok else ("timeout" if body == "(timeout)" else "error")
            print(
                f"    scout {sid} [{backend}]: {outcome} ({time.monotonic() - t0:.0f}s)"
            )
            return {"sid": sid, "ok": ok, "body": body}

        print(
            f"  wave {wave}: dispatching {len(items)} scouts ({args.workers} in flight)…"
        )
        results = run_parallel(items, run_one, workers=args.workers)
        # Fail loud, never silent-dry: an all-scout-timeout wave produces 0 findings that
        # look identical to a clean audit. With --dry-stop 1 that false-"dry" would report
        # "audit complete" off a transport failure (the silent-proxy hazard). Abort instead.
        n_ok = sum(1 for res in results if isinstance(res, dict) and res.get("ok"))
        if not args.dry_run and n_ok == 0:
            print(
                f"  ✗ wave {wave}: 0/{len(items)} scouts succeeded — all timed out or errored. "
                f"{'+'.join(scout_backends)} returned no usable output: TRANSPORT failure, NOT a "
                "clean audit. Aborting rather than reporting a false 'dry'. Check CLI "
                "auth/availability, lower per-scout load, raise --scout-timeout, or switch "
                "--scout-backend / --verifier.",
                file=sys.stderr,
            )
            return 3
        found: list[Finding] = []
        for res in results:
            if isinstance(res, dict):
                found.extend(parse_wave_output(res["body"]))
        new_claims, promoted = merge_into_memo(memo, found, wave)

        # Two-tier judge: adjudicate unverified AND adversarially re-challenge the wave's NEW
        # scout-confirmed findings (the independent cull that 0/55-confirmed runs lacked).
        verdict_changes = refutes = 0
        new_confirmed = [
            f for f in memo.values() if f.first_wave == wave and f.status == "confirmed"
        ]
        unverified = [f for f in memo.values() if f.status == "unverified"]
        if args.verifier != "none" and (unverified or new_confirmed):
            vp = verifier_prompt(unverified, new_confirmed)
            if args.verifier in ("cursor", "codex"):
                ok, body = scout_ask(
                    args.verifier,
                    repo,
                    vp,
                    timeout=args.verify_timeout,
                    model=args.verifier_model,
                    effort=args.scout_effort,
                    dry_run=args.dry_run,
                )
            else:  # opus
                ok, body = opus_adjudicate(vp, OPUS_TIMEOUT, args.dry_run)
            if ok:
                verdict_changes, refutes = apply_verdicts(memo, parse_wave_output(body))
        total_refutes += refutes

        new_info = new_claims + promoted + verdict_changes
        final_new = new_info
        if not args.dry_run:  # dry-run writes no files (matches debug_scout convention)
            save_memo(
                json_path,
                md_path,
                memo,
                repo=repo,
                wave=wave,
                total_refutes=total_refutes,
            )
        n_conf = sum(1 for f in memo.values() if f.status == "confirmed")
        print(
            f"  wave {wave}: +{new_claims} new · {promoted} promoted · "
            f"{verdict_changes} judged ({refutes} refuted) → new_info={new_info} · "
            f"{n_conf} confirmed total"
        )

        dry_streak = dry_streak + 1 if new_info == 0 else 0
        if dry_streak >= args.dry_stop:
            converged = True
            print(
                f"  DRY after wave {wave} ({dry_streak} quiet wave[s]) — audit complete."
            )
            break
    else:
        converged = False
        print(
            f"  ⚠ reached --max-waves={args.max_waves} STILL FINDING ({final_new} new in final "
            f"wave) — audit INCOMPLETE, did not converge. Re-run or raise --max-waves."
        )

    if not args.dry_run:  # final stamp with resolved convergence + refute status
        save_memo(
            json_path,
            md_path,
            memo,
            repo=repo,
            wave=wave,
            converged=converged,
            final_new=final_new,
            total_refutes=total_refutes,
        )
    n_conf = sum(1 for f in memo.values() if f.status == "confirmed")
    print(f"\nstatus:   {'CONVERGED' if converged else 'INCOMPLETE (capped, not dry)'}")
    if total_refutes == 0 and n_conf >= 10:
        print(
            "  ⚠ 0 refutations — verifier culled nothing; 'confirmed' = scout self-assessment."
        )
    print(f"findings: {n_conf} confirmed / {len(memo)} total")
    print(f"drill:    cat {json_path}")
    print(f"next:     read {md_path}  (confirmed bugs first)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
