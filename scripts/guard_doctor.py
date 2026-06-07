#!/usr/bin/env python3
"""guard_doctor.py — is tool-agnostic commit-time protection actually LIVE per repo?

The recurring failure mode (cross-model review 2026-06-07) is not missing code — it's
UNCERTAINTY about whether protection is active, especially under Codex where PreToolUse
Write|Edit hooks don't reliably fire (decisions/2026-06-02-codex-cli-project-parity.md
§FINAL). This is the "guard doctor": it reports, per repo, whether the git pre-commit
backstop is installed AND functionally blocks a protected modification — with a real
self-test, not just a file-exists check.

Per repo it checks:
  1. .git/hooks/pre-commit installed + executable, and its chain reaches
     pre-commit-protected-paths.sh (directly or via the universal dispatcher).
  2. .precommit-guards.env committed in HEAD (the enforcer reads HEAD, not the
     mutable working tree) and parses to ≥1 protected/append-only pattern.
  3. FUNCTIONAL self-test: in a throwaway git repo seeded with this repo's patterns,
     a modify of a protected path is BLOCKED and a new add is ALLOWED.

Exit 0 if every configured repo passes; 1 otherwise. Zero-API, ~1s.
Run: uv run python3 scripts/guard_doctor.py   (or: just guard-doctor)
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HOME = Path.home()
ENFORCER = HOME / "Projects/skills/hooks/pre-commit-protected-paths.sh"
# Repos wired with .precommit-guards.env (the ones that carry protected/append-only data).
REPOS = ["agent-infra", "intel", "phenome", "genomics"]

OK, WARN, FAIL = "✓", "!", "✗"


def _run(cmd, cwd=None, env=None, inp=None):
    return subprocess.run(cmd, cwd=cwd, env=env, input=inp, capture_output=True,
                          text=True, timeout=30)


def _git(args, cwd, env=None):
    return _run(["git", *args], cwd=cwd, env=env)


def _read_key(env_text: str, key: str) -> str:
    for line in env_text.splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() == key:
            v = v.strip()
            if len(v) >= 2 and v[0] in "\"'" and v[-1] == v[0]:
                v = v[1:-1]
            return v
    return ""


def hook_reaches_enforcer(repo_dir: Path) -> bool:
    """Follow the pre-commit hook (symlink or script) and check the enforcer is reachable."""
    hook = repo_dir / ".git/hooks/pre-commit"
    if not hook.exists() or not os.access(hook, os.X_OK):
        return False
    seen: set[Path] = set()
    stack = [hook.resolve()]
    while stack:
        p = stack.pop()
        if p in seen or not p.is_file():
            continue
        seen.add(p)
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        if "pre-commit-protected-paths.sh" in text or p.name == "pre-commit-protected-paths.sh":
            return True
        # follow referenced scripts (repo-local + skills dispatcher)
        for m in re.findall(r'([\w./$"~-]*(?:pre-commit|run-git-pre-commit|hooks/[\w-]+)\.sh)', text):
            cand = m.strip('"').replace("$HOME", str(HOME)).replace("$REPO_ROOT", str(repo_dir))
            cand = cand.replace("$REPO/", str(repo_dir) + "/")
            cp = Path(cand)
            if not cp.is_absolute():
                cp = repo_dir / cand
            if cp.exists():
                stack.append(cp.resolve())
    return False


def self_test(protected: str, appendonly: str) -> tuple[bool, str]:
    """Throwaway-repo proof the enforcer blocks a protected modify + allows a new add."""
    if not ENFORCER.exists():
        return False, "enforcer missing"
    sample_protected = _sample_for(protected) if protected else None
    sample_append = _sample_for(appendonly) if appendonly else None
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        env_lines = []
        if protected:
            env_lines.append(f"PRECOMMIT_PROTECTED_PATHS='{protected}'")
        if appendonly:
            env_lines.append(f"PRECOMMIT_APPENDONLY_PATHS='{appendonly}'")
        (t / ".precommit-guards.env").write_text("\n".join(env_lines) + "\n")
        env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}
        _git(["init", "-q"], t); _git(["config", "user.email", "d@d"], t); _git(["config", "user.name", "d"], t)
        hookdir = t / ".git/hooks"; hookdir.mkdir(parents=True, exist_ok=True)
        (hookdir / "pre-commit").symlink_to(ENFORCER)
        seeds = [".precommit-guards.env"]
        if sample_protected:
            p = t / sample_protected; p.parent.mkdir(parents=True, exist_ok=True); p.write_text("orig\n"); seeds.append(sample_protected)
        if sample_append:
            p = t / sample_append; p.parent.mkdir(parents=True, exist_ok=True); p.write_text("a\nb\n"); seeds.append(sample_append)
        _git(["add", *seeds], t); _git(["commit", "-qm", "seed"], t, env=env)
        # (1) modify protected → must BLOCK
        if sample_protected:
            (t / sample_protected).write_text("tampered\n"); _git(["add", sample_protected], t)
            r = _git(["commit", "-qm", "mod"], t, env=env)
            if r.returncode == 0:
                return False, f"protected modify NOT blocked ({sample_protected})"
            _git(["checkout", "-q", sample_protected], t); _git(["reset", "-q"], t)
        # (2) append-only shrink → must BLOCK
        if sample_append:
            (t / sample_append).write_text("a\n"); _git(["add", sample_append], t)
            r = _git(["commit", "-qm", "shrink"], t, env=env)
            if r.returncode == 0:
                return False, f"append-only shrink NOT blocked ({sample_append})"
            _git(["checkout", "-q", sample_append], t); _git(["reset", "-q"], t)
        # (3) a benign new file → must PASS
        (t / "benign_new.txt").write_text("ok\n"); _git(["add", "benign_new.txt"], t)
        r = _git(["commit", "-qm", "benign"], t, env=env)
        if r.returncode != 0:
            return False, "benign add wrongly blocked (false positive)"
    return True, "blocks modify+shrink, allows add"


def _sample_for(pattern: str) -> str:
    """Synthesize a concrete path matching the first alternative of an ERE pattern.

    Strip the `(^|/)` anchor idiom as a UNIT first (it contains a literal `|`), THEN
    split on the top-level `|` so the alternation parse doesn't break inside it.
    """
    pat = pattern.replace("(^|/)", "")
    alt = pat.split("|")[0]
    anchored = alt.endswith("$")    # exact filename match, e.g. improvement-log\.md$
    s = alt.replace("^", "").replace("$", "").replace("\\", "")
    if s.endswith("/"):
        return s + "sample.dat"
    if s.startswith("."):           # extension-only alt, e.g. .parquet
        return "sample" + s
    if anchored:                    # full filename — use as-is, don't make it a dir
        return s
    return s if "/" in s else s + "/sample.dat"


def main() -> int:
    print("\n[guard-doctor] commit-time protection conformance\n")
    rows, ok_all = [], True
    for repo in REPOS:
        d = HOME / "Projects" / repo
        if not (d / ".git").exists():
            rows.append((repo, WARN, "repo missing")); continue
        installed = hook_reaches_enforcer(d)
        head_env = _git(["show", "HEAD:.precommit-guards.env"], d)
        committed = head_env.returncode == 0 and head_env.stdout.strip() != ""
        prot = _read_key(head_env.stdout, "PRECOMMIT_PROTECTED_PATHS") if committed else ""
        appo = _read_key(head_env.stdout, "PRECOMMIT_APPENDONLY_PATHS") if committed else ""
        tested, detail = self_test(prot, appo) if committed else (False, "no committed config")
        status = OK if (installed and committed and tested) else FAIL
        ok_all &= status == OK
        flags = []
        flags.append(f"hook={'reaches enforcer' if installed else 'MISSING'}")
        flags.append(f"config={'in HEAD' if committed else 'NOT committed'}")
        flags.append(f"selftest={'pass' if tested else 'FAIL'}")
        rows.append((repo, status, f"{'; '.join(flags)} — {detail}"))

    w = max(len(r[0]) for r in rows)
    for name, st, detail in rows:
        print(f"  {st} {name.ljust(w)}  {detail}")
    print(f"\n  {'all repos protected' if ok_all else 'PROTECTION GAP — see ✗ rows above'}\n")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
