# refactor-mcp Study (dave-hillier/refactor-mcp)

**COMPLETE** — 2026-06-14
Repo: `/Users/alien/Projects/best/refactor-mcp` · remote `git@github.com:dave-hillier/refactor-mcp.git`

## Verdict: SKIP (do not integrate; do not pattern-extract)

Two independent decisive reasons, either sufficient alone:
1. **Language mismatch.** It refactors **C# only** (Roslyn, requires a `.sln`). agent-infra's repos are Python/TS/JS. Zero applicable surface.
2. **The maintainer's own `BUG-REPORT.md` (2026-02-06) lists 78 bugs, 8 CRITICAL with DATA LOSS** in the exact core operations that would justify an "AST is safer than Edit" integration (Inline, Extract Method, Safe Delete, Extract Interface). Confirmed unfixed in cloned HEAD. The sound-transform value proposition is self-refuted by the author.

This is NOT a nav/search re-veto (it does do real AST transforms) — it's a **correctness + language-fit** rejection.

---

## Task 1 — Tool surface (the actual MCP tools)

C#/.NET console app exposing MCP tools via `[McpServerToolType]` / `[McpServerTool]` attributes (ModelContextProtocol 0.2.0-preview.3). ~30 refactoring tools in `RefactorMCP.ConsoleApp/Tools/` plus infra (load/unload solution, list, version, metrics resources). Enumerated from `Tools/*.cs`:

- **RenameSymbol** (`RenameSymbolTool.cs`) — solution-wide, Roslyn `Renamer.RenameSymbolAsync`
- **ExtractMethod** (`ExtractMethodTool.cs`)
- **InlineMethod** (`InlineMethodTool.cs`)
- **IntroduceField / IntroduceParameter / IntroduceVariable**
- **ConvertToStaticWithInstance / ConvertToStaticWithParameters**
- **ConvertToExtensionMethod**
- **MoveMethod / MoveMultipleMethods / MoveStaticMethod / MakeStaticThenMove / MoveTypeToFile**
- **MakeFieldReadonly / TransformSetterToInit / ConstructorInjection**
- **SafeDelete** (fields/params/vars with dependency check)
- **ExtractInterface / UseInterface / CreateAdapter / ExtractDecorator / AddObserver** (design-pattern scaffolds)
- **CleanupUsings / FeatureFlagRefactor**
- **AnalyzeRefactoringOpportunities / ClassLengthMetrics** + `metrics://` `summary://` resources (the nav/metrics side)

Genuinely a transformation server (rename/extract/inline/move/change-signature-ish), NOT a search wrapper. The nav part (metrics/analyze) is secondary.

## Task 2 — HOW (mechanism, language, soundness)

- **Mechanism: Roslyn** (`Microsoft.CodeAnalysis.CSharp` 4.14.0 + `.Workspaces` + `.Features` + `.Workspaces.MSBuild`). `SyntaxRewriters/` (CSharpSyntaxRewriter subclasses) + `SyntaxWalkers/`. NOT tree-sitter, NOT an external LSP — it loads an MSBuild `Solution` in-process and uses the compiler's own semantic model.
- **Language: C# ONLY.** Every tool takes `solutionPath` (.sln) + a C# file path. `net9.0` target. README L3: "Roslyn-based refactoring tools for C#."
- **Soundness — semantically aware in design, buggy in practice:**
  - Rename IS scope-aware: `RenameSymbolTool.cs:36-37` uses `Renamer.RenameSymbolAsync` with a resolved `ISymbol` (the one operation Roslyn does correctly out of the box; the wrapper around it is thin and probably fine).
  - SafeDelete uses `SymbolFinder.FindReferencesAsync` (semantic), ExtractMethod uses the semantic model + `Formatter`. So it *aspires* to soundness Edit can't match.
  - BUT a pervasive **Roslyn immutable-tree staleness** bug class breaks the hard ops (see Task 4). The author found and documented it; it is unfixed.

## Task 3 — Dependency-eval

| Dim | Finding |
|---|---|
| **Language/runtime** | C#, **net9.0**. Local machine has **dotnet 8.0.204 only** → would not even build/run here without a .NET 9 SDK install. |
| **Last commit** | Cloned HEAD = single squashed merge `8129edd`, **2026-02-07**, PR #303. Clone is **shallow (depth 1)** (`is-shallow-repository=true`) → real history depth/cadence NOT measurable locally; only 1 author visible (Dave Hillier) but that's an artifact of the squash, not proof of bus factor. PR #303 implies ≥300 PRs of activity. |
| **Bus factor** | Single visible author (`dave.hillier1@gmail.com`); personal-account repo. Likely solo/hobby. |
| **Tests** | Strong: **323 `[Fact]`/`[Theory]` methods**, xunit, coverlet, ~95 test files mirroring rewriters/walkers/tools. CI (`dotnet.yml`) builds + tests on PR/push. Test discipline is real. |
| **Runtime deps** | Heavy: full Roslyn workspace stack + `Microsoft.Build.Locator` + `Microsoft.Extensions.Hosting`. MSBuild-in-process is fragile (the author's own C7 bug is "MSBuildWorkspace disposed while cached Solution still in use"). |
| **License** | MPL-2.0 (file-level copyleft — fine for pattern study, weak-copyleft if vendoring code). |
| **Maturity** | Pre-1.0, on an MCP **preview** SDK. The `BUG-REPORT.md` self-assessment is the maturity tell: 78 known bugs, 8 critical, dated the day before HEAD. |

## Task 4 — Verdict reasoning

**Does it fill a real gap for an agent on Claude Code?** No, on two axes:

**(a) Wrong language.** agent-infra + its governed repos (intel, phenome, genomics, skills, research-mcp) are Python/TS. A C#-solution-scoped Roslyn server has no surface to act on. `scripts/ts-replace.py` + native Edit/Grep/LSP already cover the actual stack. There is no C# in the fleet for this to refactor.

**(b) Even for C#, the sound-transform claim is false right now.** The integration thesis would be "AST transforms are safer than text Edit." The author's `BUG-REPORT.md` (2026-02-06) refutes it for the load-bearing ops, and the bugs are present in cloned HEAD:
  - **C4 SafeDelete — DATA LOSS, confirmed** `SafeDeleteTool.cs:110,167,288` still `var count = refs.SelectMany(r => r.Locations).Count() - 1;` — off-by-one treats a still-referenced symbol as unused and deletes it.
  - **C6 ExtractMethod — silent statement duplication, confirmed** `SyntaxRewriters/ExtractMethodRewriter.cs:38-43`: ctor does `body.ReplaceNode(statements.First(),…)` then `RemoveNode` over `statements.Skip(1)` — but those are stale references from the ORIGINAL root, so multi-statement extraction leaves the statements duplicated in BOTH the new method and the original.
  - **C1 InlineMethod — DATA LOSS** `InlineMethodTool.cs`: writes call-site edits, then re-reads the *original* immutable root and removes the decl from it, overwriting the inlining. (Pattern matches; lines shifted slightly but logic intact: re-`GetSyntaxRootAsync` after a disk write, operate on stale root.)
  - **C2/C3/C5/C7**: extension-class lost, base-list wiped, expression-bodied crash, workspace-disposed. Same Roslyn reference-identity / immutability misuse class.

An AST tool that *silently* loses data is strictly worse than `Edit`, because Edit's failures are visible (string didn't match → error) while these pass and corrupt. That inverts the only reason to prefer it.

**Re vetoes:** consistent with the repo-tools-MCP retirement (don't add an MCP server unless it earns its keep) and especially with the constitution's "evaluate external tools as dependencies first" — due diligence fails here on maturity (78 self-reported bugs) AND fit (language). Not the PageRank-nav re-veto (it's real transforms), but lands on SKIP via correctness+fit.

**Pattern-extract?** No. The one correct primitive is `Renamer.RenameSymbolAsync` — that's just *calling Roslyn*, not a portable pattern, and it's C#-specific. For Python/TS there's no analog to lift; the equivalent "use the language's own semantic engine" is already what LSP / `ts-replace.py` do. Nothing here improves the Python/TS path.

**If C# ever enters the fleet:** reconsider ONLY after the C-series data-loss bugs are fixed upstream (watch the issue tracker), and even then prefer running it solution-locally over a standing MCP. Not now.

### One transferable observation (not an action)
The bug class — "re-fetch an immutable Roslyn root after a mutation and operate on stale node references" — is the AST analog of agent-infra's own *silent-proxy-as-truth* failure: a stand-in (old tree) is trusted as the principal (current tree). Confirms the prior that AST refactoring is only as safe as its identity-tracking, and a half-correct AST tool is more dangerous than text edits because the failure is silent. Pure note; nothing to build.
