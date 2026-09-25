---
title: "Displaying information insightfully: Victor lineage, vis science, craft canon → /figure"
date: 2026-09-25
status: complete
tags: [figure, dataviz, visualization, victor, tufte, explorables, skills]
---

**Verdict:** Three independent lanes (Victor and the explorable-explanation lineage; the empirical visualization literature; the editorial and artistic canon) converge on one position: a figure is an argument edited around one comparison, carried entirely by its static default view, with words as part of the graphic, and checked by a reader who does not know the story. They also agree that most famous rules are task-dependent rather than universal: minimalism loses on recall, ornament on precise reading, log scales on lay readers, animation and interaction on anyone who only scrolls. `/figure` was rewritten from a rule table into ten principles plus lookup references, and the blind reader gained `open` (uncued) and `trap` (misleading-impression) questions. [SOURCE: lane memos below; three decision-bearing quotes re-checked by the parent against primaries]

Lane memos (principles, exemplars, quotes, read/skipped logs): `research/scratch/2026-09-25-information-display/{A-victor-explorables,B-empirical,C-craft}.md`. Skill: `~/Projects/skills/figure/` (SKILL.md, `references/forms-and-tools.md`, `references/craft-moves.md`).

## 1. Where the lanes converge

| Principle in /figure | Victor lineage (A) | Empirical (B) | Craft canon (C) |
|---|---|---|---|
| 1 Start from the reader's task | Magic Ink: list the reader's questions first | Munzner nested model; Saket 2018 (form effectiveness varies by task) | "rules flip by task" synthesis; Romano 2020 log-scale RCT |
| 2 Words are part of the figure; title must match salience | Explorable Explanations: reads as text | Stokes 2022 (n=302; annotated charts preferred, placement by semantic level); Kim, Setlur & Agrawala 2021 (low-prominence caption loses to the chart); Kong 2018/2019 (title slant sets recall) | Cox: "The annotation layer is critical"; Burn-Murdoch point-making titles |
| 3 One comparison, one eyespan | Magic Ink: compare by eye, not by hand | Franconeri 2021: "narrow that set to the single most important comparison"; proximity > colour | Tufte EI "Compared to what?"; Datawrapper grey-plus-focal |
| 4 Default view carries everything; static first | Magic Ink "Interactivity considered harmful"; Patel "show all the variants" | Franconeri 2021: "little evidence that animation facilitates understanding" | Tse 2016: "assume no one will ever see it" |
| 5 Family + highlighted case | Ladder of Abstraction (step up, then down) | — | Tufte micro/macro; Rosling splitting averages |
| 6 Scales/intervals are claims | — | Correll 2020 (truncation persists despite cues); Hullman HOPs; Kay quantile dotplots; Correll & Gleicher 2014 | Burn-Murdoch log alignment vs Romano 2020 |
| 7 Show the seams | Victor 2024 postscript: facts, assumptions, calculations visible | — | The Pudding methodology; Lupi "'Data-driven' doesn't mean 'unmistakably true'" |
| 8 Ornament must be data or earn attention | — | Bateman 2010; Haroz 2015; Borkin 2016; Franconeri: no reliable data-ink effect | Bremer, Stefaner vs Healy's halo effect |
| 9 Rethink the idea, not the styling | Olah & Carter "Research Debt" | — | — |
| 10 Judge by naive readers | — | Xiong 2020 curse of knowledge | Burn-Murdoch: readers find points "I can't fathom" |

## 2. Disagreements kept open in the skill

- **Thesis or system.** Claim-first titles (Cox, Burn-Murdoch, Stokes) vs The Pudding's "depict the system" and Lupi's layered complexity. Resolved as an explicit exploratory exception, not a ban.
- **Minimal or embellished.** No general winner; lean for analysis and lookup, relevant embellishment tolerated for presentation and recall. Bateman is n=20; do not generalise to "embellish".
- **Interaction.** The "85% never click" figure is Gregor Aisch's measurement of one button in a couple of 2015 NYT graphics, not a study (Aisch 2017 objects to its reuse). Tse's rule stands as practitioner judgment, directionally supported by Robertson 2008 and Tversky 2002.
- **Canon exemplars.** Minard, Snow and Nightingale were persuasion pieces (Kosara 2016; Small on Minard's temperature strip). Copy the fit of form to argument, not the form.

## 3. Corrections to the first /figure version

- "Bars start at zero" became "the axis range is an effect-size claim": truncation also inflates perceived effect in line charts, even with break glyphs (Correll 2020).
- No data-ink rule: Franconeri 2021 finds "little evidence that the prescription affects objective performance".
- Plain pies allowed for 2-5-slice part-to-whole (Saket 2018; Heer & Bostock 2010 found angle not worse than length; Kosara & Skau 2016).
- Uncertainty for lay readers: quantile dotplots / icon arrays and predictive intervals over bare 95% CIs (Kay 2016; Hofman 2020 via Franconeri).
- Blind reader: no backstory; uncued `open` question in its own call (Xiong 2020); `chart` arm doubles as the no-title arm (Kong); `trap` role flags a misleading visual impression (Healy's halo; no source proposes the test itself).
- Aesthetic judgment routed to the operator: the agent renders 2-3 variants rather than iterating on its own taste (operator, 2026-09-25: models have poor taste in art).

## 4. Evidence strength

- Parent re-verified against primaries: Tse 2016 slide wording; Stokes 2022 abstract (n=302, annotation and placement findings); Correll 2020 abstract (persistence despite cues; "scale of the meaningful effect sizes").
- Full text read by lanes: Magic Ink, Explorable Explanations, Ladder, Research Debt, Robertson 2008, Franconeri 2021, Stokes 2022, Kim 2021, Correll 2020, Heer & Bostock 2010, Bateman 2010, Saket 2018, Healy ch.1, Tufte EI chapters, Tse and Aisch.
- Abstract or secondary only: Kong 2018/2019, Xiong 2020, Borkin 2013/2016, HOPs, quantile dotplots, Munzner, Segel & Heer, Tufte's *Beautiful Evidence* principles, Du Bois analysis.
- Not covered: Ciechanowski, 3Blue1Brown, Dynamicland, Cleveland & McGill 1984 original, Reda & Szafir 2020 (rainbows), Höffler & Leutner 2007 animation meta-analysis. scite was unavailable, so there are no citation-stance counts.
- Transfer caveat: most empirical studies use crowdworkers and simple charts; the blind reader is an LLM standing in for a human, so it tests legibility of the claim, not human perception.
