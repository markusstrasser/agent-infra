# Common brief — politicized statistics case library, 2016–2026 (all lanes)

Parent session 456dc99a (agent-infra). Read this file first, then your lane file.

## Goal
A mechanism-organized library of cases where a statistic, model, or "scientific consensus" was USED for a
political purpose (policy, mandate, hearing, court, campaign, editorial) between 2016-01 and 2026-09, and
what the primary record shows about the number's construction. The library will ground a new process-level
section of the research skill's quantitative bias checklist and a new /analyze lens. It is NOT a list of
replication failures (that library exists: agent-infra/research/adversarial-case-library.md).

## Hard rules
1. **Primary source per case.** The original document: dataset page, methodology note, retraction notice,
   transcript, court filing, agency press release, the paper itself, released messages. News coverage locates;
   it does not ground. Quote verbatim, with URL and date read. If you cannot reach the primary, say so and
   grade C/D.
2. **Leads are training-memory candidates, not facts.** Every lead in your lane file must end as one of:
   GROUNDED (primary quote + grade) · CONTRADICTED (source says otherwise — keep it, this is a finding) ·
   NOT FOUND (searched, absent; give the queries). Do not soften a contradiction.
3. **Both-directions rule.** The instrument (you) has asymmetric dispositions on political topics; see the
   mechanism description in immigration-research/notes/llm-bias-caveat.md (asymmetric "misleading" flags,
   benefit-of-the-doubt asymmetry, eagerness on FALSE). Mitigation: for each mechanism, seek one case from
   each political direction where one exists. If you find none, write "no counter-direction case found"
   and the queries you ran. Apply the same evidence standard to congenial and uncongenial cases; write the
   two verdicts in the same paragraph.
4. **Per case, record:** mechanism id (from your lane) · date · the number/claim as used · who used it and
   for what (the political use, with source) · what the primary record shows (construction, definition,
   instrument, extract, scenario) · the corrected or alternative construction and its value if computable ·
   grade A–D (A = primary official/statistical-agency doc or peer-reviewed with data; B = advocacy/think-tank
   with published method; C = secondary reporting; D = assertion) · direction (which side the number served).
5. **Prioritize.** ~14 leads per lane will not all fit in 12 turns. Order: (i) leads that ground a mechanism
   with a MEASURED magnitude, (ii) leads with an on-record admission (the actor said why), (iii) the rest.
   Better 8 grounded than 14 thin.
6. **Write-first.** Turn 1: write your output file as a stub (header, scope, lead list with [PENDING]).
   Append after each verified case. Never hold findings in memory.
7. **Tools.** Exa (web_search_exa / web_search_advanced_exa / crawling) for documents; search_papers for
   academic metadata; WebFetch for primary pages; curl for PDFs. Known route defects: research skill
   references/known-issues.md (arXiv OR-groups ignored; fetch_paper weak on 2026 OA; EuropePMC fullTextXML
   works with a PMCID). Do not use deep_research (paid).
8. **No editorializing.** Every sentence is either a sourced fact, a stated calculation on sourced numbers,
   or labelled [INFERENCE]. No verdicts on who was "right" politically; the verdict is about the number.

## Output contract
File: `~/Projects/agent-infra/research/scratch/2026-09-16-politicized-stats/lane-<x>.md`
- Line 1: `**Verdict:**` one paragraph: how many leads grounded / contradicted / not found; the 2–3 strongest
  measured magnitudes; whether the grounded cases span both directions.
- Then one `## <mechanism id> — <name>` section per mechanism with the cases as described in rule 4.
- Then `## Disconfirmation record` (what contradicted the leads).
- Then `## Covered` and `## Skipped (why)` lead lists, and `## Suggested next queries` for a second epoch.
- Return to the parent: the file path and ≤10 lines.
