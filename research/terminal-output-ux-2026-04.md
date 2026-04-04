## Terminal Output UX for Python Scripts in Claude Code — Research Memo

**Question:** What are the best low-maintenance options for improving terminal output from Python scripts running inside Claude Code (Ghostty terminal)?
**Tier:** Standard | **Date:** 2026-04-04

### Claims Table

| # | Claim | Confidence | Source | Status |
|---|-------|------------|--------|--------|
| 1 | Rich replaces tqdm with richer progress bars, tables, panels, colored logging — single dependency | HIGH | [SOURCE: rich.readthedocs.io] | VERIFIED |
| 2 | `tqdm.rich` exists but is marked "Experimental" — thin wrapper, not full Rich integration | HIGH | [SOURCE: tqdm.github.io/docs/rich] | VERIFIED |
| 3 | Ghostty supports 24-bit color, OSC 8 hyperlinks, Kitty graphics protocol | HIGH | [SOURCE: ghostty.org/docs] | VERIFIED |
| 4 | Claude Code passes ANSI from subprocess stdout into its context window as raw tokens | HIGH | [SOURCE: dev.to/ji_ai, github.com/anthropics/claude-code/issues/5428] | VERIFIED |
| 5 | Modal's `enable_output` is a binary on/off context manager — no styling hooks | MEDIUM | [SOURCE: modal.com/docs/reference/modal.enable_output] | VERIFIED |
| 6 | Loguru is zero-config colored logging; structlog is structured-first with optional color | HIGH | [SOURCE: betterstack.com, reddit.com/r/Python] | VERIFIED |

### Key Findings

**1. Rich library — the clear winner for unified output**

Rich (Will McGugan, ~50K stars) provides progress bars, tables, panels, syntax highlighting, tracebacks, and logging handlers in one package. Key features:
- `rich.progress.Progress` — multiple concurrent task bars, custom columns (speed, ETA, spinners), transient mode (bar disappears on completion), auto-refresh
- `rich.logging.RichHandler` — drop-in replacement for `logging.StreamHandler` with colored levels, timestamps, markup
- `rich.table.Table` — formatted tables that render in terminal
- `rich.console.Console` — centralized output with `force_terminal=True` for subprocess environments
- Zero-config: `from rich import print` replaces built-in print with colored output

**Maintenance cost: LOW.** One dependency, stable API (v13+), actively maintained, no configuration files needed.

**2. tqdm.rich — not worth it**

`tqdm.rich` is marked "Experimental" and is just a thin adapter passing tqdm iterators to Rich's progress. If you're adopting Rich, use `rich.progress` directly — it's more capable and you avoid tqdm as a dependency entirely. The only reason to keep tqdm: if you have dozens of `tqdm()` calls and want a quick swap via `from tqdm.rich import tqdm`.

**3. Claude Code ANSI handling — the critical constraint**

Claude Code captures subprocess stdout/stderr and feeds it into the model's context window. ANSI escape codes are passed through as raw bytes, consuming tokens without visual benefit to the *model*. However, they DO render in the terminal for the *human* watching. This creates a split audience:
- **Human sees:** colored output in Ghostty (24-bit color, hyperlinks, the works)
- **Model sees:** raw `\x1B[31m` sequences eating context

Practical implication: Use colors for human-facing output (interactive runs), but consider `NO_COLOR=1` or `TERM=dumb` detection when output is being captured by an agent. Rich respects `NO_COLOR` and `TERM=dumb` out of the box.

**4. Modal output — no customization**

`modal.enable_output()` is a context manager that toggles Modal's built-in logging (function logs, object creation, map progress) to stdout/stderr. It has one boolean parameter (`show_progress`). No hooks for styling, no way to intercept progress events. Modal's output is what it is. If you want styled Modal output, capture logs and re-emit through Rich.

**5. Logging: Loguru vs structlog vs colorlog**

- **Loguru** — zero-config, colored by default, `logger.info("msg")` just works. Replaces stdlib logging entirely. Best for: scripts, CLIs, personal projects. One `pip install loguru` and you're done.
- **structlog** — structured logging (JSON-capable), colored console output via `ConsoleRenderer`. Best for: production services where you need both human-readable and machine-parseable logs. More setup.
- **colorlog** — just adds colors to stdlib logging. Minimal but doesn't add other value.

For your use case (Python scripts, not services): **Loguru is the lowest-maintenance option.** If you adopt Rich, use `RichHandler` instead — one fewer dependency.

**6. Ghostty capabilities — no limitations found**

Ghostty supports everything relevant: 24-bit true color (set `COLORTERM=truecolor`), OSC 8 hyperlinks, Kitty graphics protocol, semantic prompt marking (OSC 133). Rich's hyperlink support (`rich.text.Text` with links) will render as clickable links in Ghostty.

### Minimal Setup Recommendation

```python
# One import, covers progress + logging + tables + pretty print
from rich.console import Console
from rich.logging import RichHandler
import logging

console = Console()
logging.basicConfig(level="INFO", handlers=[RichHandler(rich_tracebacks=True)])
```

This gives you: colored log levels, pretty tracebacks, `console.print()` for tables/panels, and `rich.progress` for progress bars. Total new dependencies: 1 (rich). Replaces: tqdm, colorlog/loguru (if using RichHandler).

For agent-captured output, Rich auto-detects non-TTY and strips formatting — or force it with `Console(force_terminal=True)` when you want colors regardless.

### What's Uncertain

- Whether Claude Code's Bash tool strips ANSI before feeding to context, or passes raw. The evidence suggests raw passthrough, but the exact behavior may vary by CC version. Test with `echo -e '\033[31mred\033[0m'` in a session.
- Whether Rich's `Console.is_terminal` correctly detects Claude Code's subprocess environment. May need explicit `force_terminal=True` or `NO_COLOR` handling.

<!-- knowledge-index
generated: 2026-04-04T17:23:00Z
hash: d2e4ddf546d2

table_claims: 6

end-knowledge-index -->
