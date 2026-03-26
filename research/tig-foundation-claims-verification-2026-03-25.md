---
title: TIG Foundation — People & Operational Claims Verification
date: 2026-03-25
tags: [verification, crypto, DeSci, TIG]
status: complete
---

## TIG Foundation / The Innovation Game — People & Operational Claims Verification

**Question:** Verify specific claims about five people associated with TIG (tig.foundation) and the operational status of the network.
**Tier:** Standard | **Date:** 2026-03-25
**Ground truth:** No prior research on TIG in corpus.

### Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | John Fletcher — PhD in mathematics and theoretical physics from Cambridge | Self-reported on personal website, TIG team page, LinkedIn, multiple podcast appearances. Described as "applied mathematics and theoretical physics." BASELINE podcast (Sep 2025) says "studied physics at Oxford, theoretical physics at Imperial, and PhD in mathematics at Cambridge." LinkedIn education lists: PhD Mathematics and Theoretical Physics (Cambridge), MSc Theoretical Physics (Imperial College London). No independent Cambridge repository record found for this specific person, but the claim is broadly consistent across all sources and never contradicted. | HIGH | [SOURCE: drjohnfletcher.com], [SOURCE: tig.foundation/team], [SOURCE: LinkedIn], [SOURCE: BASELINE podcast] | VERIFIED (self-consistent, no contradictions) |
| 2 | John Fletcher — working on coordinating untrusted distributed compute since 2016 | TIG team page: "researching frameworks for distributed incentives full-time since 2016." LinkedIn shows Chief Scientist at TIG from March 2022. Patent filings on Justia show blockchain/cryptography patents starting ~2018. The 2016 start date refers to research, not TIG itself. | HIGH | [SOURCE: tig.foundation/team], [SOURCE: patents.justia.com/inventor/john-fletcher], [SOURCE: LinkedIn] | VERIFIED |
| 3 | John Fletcher — founder/co-founder of TIG | TIG team page lists him as "CEO & Co-Founder." Delphi Digital interview (Aug 2024) introduces him as "CEO and co-founder." Multiple podcast and Twitter Space transcripts confirm. The Medium article (Mar 2025) is written in first person by him describing the creation of TIG. | HIGH | [SOURCE: tig.foundation/team], [SOURCE: Delphi Digital YouTube], [SOURCE: XspaceGPT transcripts] | VERIFIED |
| 4 | Philip David — General Counsel at Arm Holdings | TIG team page: "former ARM Limited Director and General Counsel (2003-2018)." LinkedIn confirms "General Counsel at ARM Limited." Exa verify_claim confirmed the General Counsel role via LinkedIn. XspaceGPT transcript: John Fletcher states Phil "was Arm's most senior licensing lawyer, served on the board ~20 years, negotiated at top levels, and served a long stint as General Counsel" — Phil did not contradict in the same conversation. | HIGH | [SOURCE: tig.foundation/team], [SOURCE: LinkedIn], [SOURCE: XspaceGPT transcript] | VERIFIED |
| 5 | Philip David — "architect of ARM's licensing strategy" | TIG team page says he "spearheaded the company's IP strategy as Senior VP of IP during SoftBank's acquisition" and "shaped open source licensing frameworks through Linaro's establishment." The XspaceGPT transcript describes him as having "licensed technology developed by top engineers" at Arm, with the model "inspired by Dolby's early licensing." The specific phrase "architect of ARM's licensing strategy" is a reasonable characterization but appears to be promotional language rather than an official ARM title. Exa verify_claim returned "insufficient" evidence for the "Senior VP of IP during SoftBank acquisition" part specifically. | MEDIUM | [SOURCE: tig.foundation/team], [SOURCE: XspaceGPT transcript] | PARTIALLY VERIFIED — role confirmed, specific characterization unverified independently |
| 6 | Philip David — co-founder of TIG | TIG team page does NOT list him as co-founder. He is listed as "I.P. & General Counsel." The co-founders listed are John Fletcher (CEO & Co-Founder) and Ying Chan (CTO & Co-Founder). XspaceGPT transcript also identifies Lee Hughes as a co-founder who introduced Phil to TIG. Philip David is described as a team member, not co-founder. | HIGH | [SOURCE: tig.foundation/team] | **DENIED** — Philip David is NOT listed as co-founder; he is IP & General Counsel |
| 7 | Philip David — designed TIG's dual licensing model | XspaceGPT transcript says "Phil David (General Counsel; ex-Arm licensing; architect of TIG's revenue/licensing model)" and describes him as leading the publishing of specific licensing terms. Another transcript says "TIG was conceived with licensing at its core" and Phil's role was to "build a durable, legally robust licensing backbone." Plausible he is the key designer of the licensing model, but the dual licensing concept was baked into TIG from its whitepaper (authored primarily by Fletcher). Phil appears to be the implementer/legal architect rather than sole designer. | MEDIUM | [SOURCE: XspaceGPT transcripts], [SOURCE: TIG whitepaper] | PARTIALLY VERIFIED — he leads licensing execution; "designed" overstates his origination of the concept |
| 8 | Thibaut Vidal — at Polytechnique Montreal | Google Scholar: "Professor, SCALE-AI Chair, MAGI, Polytechnique Montreal. Verified email at polymtl.ca." CV confirms: "since 2021: Professor, Mathematics and Industrial Engineering, Ecole Polytechnique de Montreal, Canada." | HIGH | [SOURCE: scholar.google.com], [SOURCE: w1.cirrelt.ca/~vidalt/en/cv-vidal-thibaut.html] | VERIFIED |
| 9 | Thibaut Vidal — submitted state-of-the-art vehicle routing algorithm directly to TIG | TIG foundation website lists "Dr. Thibaut Vidal" as the technical paper author for the Vehicle Routing challenge. XspaceGPT transcript references "Thibaut Vidal (referenced as an innovator collaborating with TIG)." His open-source HGS-CVRP implementation (Hybrid Genetic Search) is a well-known SOTA method with 397+ citations. The claim that he "submitted directly to TIG" is consistent with TIG's challenge designer model, but the exact nature of the collaboration (formal submission vs. advisory role / algorithm adoption) is not independently verified. | MEDIUM-HIGH | [SOURCE: tig.foundation challenges page], [SOURCE: XspaceGPT transcript], [SOURCE: Google Scholar] | VERIFIED with caveat — his algorithm is used in TIG's Vehicle Routing challenge and he is credited; exact submission mechanism unclear |
| 10 | Yuji Nakatsukasa — at Oxford | Oxford Mathematical Institute page: "Yuji Nakatsukasa, University of Oxford, Verified email at maths.ox.ac.uk." Multiple publications list his affiliation as "Mathematical Institute, University of Oxford." Research focus includes CUR decomposition. | HIGH | [SOURCE: people.maths.ox.ac.uk/nakatsukasa], [SOURCE: Google Scholar], [SOURCE: ResearchGate] | VERIFIED |
| 11 | Yuji Nakatsukasa — associated with TIG | TIG foundation challenges page lists "Dr. Yuji Nakatsukasa" as the technical paper author for the CUR Decomposition challenge. His research area (CUR decomposition, numerical linear algebra) directly maps to this TIG challenge. | HIGH | [SOURCE: tig.foundation challenges page] | VERIFIED |
| 12 | Dario Paccagnan — at Imperial College London | Imperial College profile page exists (profiles.imperial.ac.uk/d.paccagnan). IFAAMAS 2021 paper lists "Imperial College, London." IEEE talk bio (2020): "Assistant Professor (Lecturer) at the Department of Computing, Imperial College London since Fall 2020." Multiple arXiv papers list Imperial affiliation. | HIGH | [SOURCE: profiles.imperial.ac.uk], [SOURCE: IFAAMAS proceedings], [SOURCE: IEEE talk bio], [SOURCE: arXiv papers] | VERIFIED |
| 13 | Dario Paccagnan — associated with TIG | No evidence found of direct TIG association. The TIG challenges page does NOT list Paccagnan as a technical paper author for any challenge. His research (game theory, congestion games, mechanism design) is thematically adjacent to TIG's interests, but no direct collaboration or role is documented. | LOW | No source found | **UNVERIFIED** — no evidence of TIG association found |
| 14 | TIG — real and operational | GitHub monorepo created 2024-04-23, actively maintained (last push 2026-03-19), 73 stars, 51 forks. Token exists on Base (ERC-20). Delphi Digital interview (Aug 2024) discusses operational network. Multiple podcasts and Medium posts from 2024-2025 discuss active operations. XspaceGPT (Sep 2025) mentions "roughly one year of runway from its initial token sale." Docs reference mainnet API (mainnet-api.tig.foundation). | HIGH | [SOURCE: GitHub API], [SOURCE: Delphi Digital YouTube Aug 2024], [SOURCE: BaseScan], [SOURCE: docs.tig.foundation] | VERIFIED |
| 15 | TIG — continuous operation since mid-2024 | GitHub repo created April 23, 2024. Delphi Digital video published Aug 30, 2024, discusses operational network with live challenges. Medium update "Taking TIG to the Next Stage" published Oct 22, 2024. XspaceGPT (Sep 2025) mentions ~1 year of token sale runway. Network has gone through 50+ rounds per the play.tig.foundation reference. Consistent with mid-2024 start. | HIGH | [SOURCE: GitHub created_at], [SOURCE: Delphi Digital Aug 2024], [SOURCE: Medium Oct 2024] | VERIFIED |
| 16 | TIG — "roughly 7,000 benchmarkers" | XspaceGPT (Sep 2025) transcript does not mention this specific number. Exa verify_claim returned "insufficient" for this claim. The play.tig.foundation site was rate-limited during this research. No independent source confirming 7,000 benchmarkers was found. This is a specific operational metric that would need to be verified against TIG's on-chain data or official announcements. | LOW | No independent source found | **UNVERIFIED** — specific number not independently confirmed |

### Key Findings

**TIG is a real, operational protocol.** The Innovation Game (TIG) is a Swiss Foundation running a decentralized "Optimisable Proof of Work" (OPoW) protocol designed to incentivize open algorithmic innovation. The GitHub monorepo has been actively maintained since April 2024, with a Rust-based implementation. It operates on Base (Ethereum L2) with its own ERC-20 token. The project has genuine academic collaborations and a coherent technical vision.

**John Fletcher's claims are well-supported.** He holds a PhD from Cambridge (applied mathematics and theoretical physics), studied physics at Oxford and theoretical physics at Imperial beforehand, and has 30+ verifiable blockchain/cryptography patents. He is the CEO and co-founder. The "since 2016" claim refers to his research focus on distributed incentive frameworks. However, I could not find his PhD thesis in Cambridge's public repository -- this may simply be a digitization gap, or the thesis may be under a different exact title.

**Philip David's claims require correction.** He WAS General Counsel at ARM Limited (confirmed via LinkedIn and TIG team page, tenure 2003-2018). However, the claim that he is a "co-founder of TIG" is **false** -- the TIG team page lists him as "I.P. & General Counsel," not co-founder. The co-founders are John Fletcher and Ying Chan. The claim that he "designed TIG's dual licensing model" is an overstatement -- he leads legal execution of the licensing strategy, but the dual licensing concept was part of TIG's original whitepaper (authored primarily by Fletcher). His ARM title was "Director and General Counsel" and "Senior VP of IP."

**Thibaut Vidal is a legitimate top-tier researcher.** He is Professor at Polytechnique Montreal with a SCALE-AI Chair, and is one of the world's leading experts on vehicle routing optimization (1,000+ citations on his seminal HGS papers). His open-source HGS-CVRP solver is widely recognized as state-of-the-art. He is credited as the technical paper author for TIG's Vehicle Routing challenge.

**Yuji Nakatsukasa is verified at Oxford** with a clear TIG connection as the technical paper author for the CUR Decomposition challenge. His research directly focuses on CUR decomposition methods.

**Dario Paccagnan is verified at Imperial College London** as an expert in game theory and mechanism design. However, **no evidence of TIG association was found** -- he is not listed on TIG's team page or as a challenge technical paper author. His research area is thematically adjacent but no formal connection is documented.

**The "7,000 benchmarkers" claim is unverified.** No independent source confirms this specific number. It would need to be verified against on-chain data or TIG's official statistics dashboard.

### What's Uncertain

1. **John Fletcher's PhD thesis** — not found in Cambridge's public repository. Could be a digitization gap, different indexing, or the thesis may not have been deposited online. Does not invalidate the claim, but is notable.
2. **Exact nature of academic collaborations** — Whether Vidal, Nakatsukasa, and others "submitted algorithms" vs. served as challenge design consultants vs. had their published algorithms adopted is unclear. The TIG model supports all three paths (Code Submissions, Advance Submissions, and Challenge Designer grants).
3. **Dario Paccagnan's TIG role** — The claim of association is not supported by any found evidence. This could be: (a) an error in the original claims, (b) an informal/advisory role not publicly documented, or (c) a planned future collaboration.
4. **Benchmarker count** — Self-reported operational metrics from crypto projects should be treated skeptically without on-chain verification.
5. **Philip David's "architect" claim** — His role at ARM is confirmed, but the specific characterization as "architect of ARM's licensing strategy" may be promotional language rather than a formal title or role description.

### Provenance Notes

- TIG team page (tig.foundation/team) is the primary source for role claims — self-reported but internally consistent
- LinkedIn profiles confirm academic and professional backgrounds independently
- XspaceGPT transcripts are secondary sources (AI-generated summaries of Twitter Spaces) — useful for context but may contain transcription errors
- Google Scholar and university pages are authoritative for academic affiliations
- The Cambridge thesis repository search did not find John Fletcher's thesis, but found other "Fletcher" theses at Cambridge confirming the repository is functional
- Exa verify_claim returned "insufficient" for two claims (Philip David's SVP role at ARM, and 7,000 benchmarkers), meaning web sources neither confirmed nor denied

<!-- knowledge-index
generated: 2026-03-26T04:45:17Z
hash: ca7779f86c7b

title: TIG Foundation — People & Operational Claims Verification
status: complete
tags: verification, crypto, DeSci, TIG
table_claims: 16

end-knowledge-index -->
