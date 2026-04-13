# Post-cutoff claim cases for claim-bench

Two verifiable claims whose gold evidence was published between 2025-10-01 and 2026-04-11, for an `inspect_ai` benchmark that tests whether an LLM with web search can retrieve post-training-cutoff evidence (May 2025 cutoff). One supported (physics/astrophysics), one contradicted (economics retraction). Both have DOIs that were confirmed to resolve and metadata extracted directly from the publisher HTML.

## Case 1 — Supported (astrophysics / LIGO-Virgo-KAGRA)

```json
{
  "task_id": "003_supported_pair_instability_gap_gwtc4",
  "claim_text": "Using data from LIGO-Virgo-KAGRA's fourth Gravitational-Wave Transient Catalog (GWTC-4), Tong et al. reported evidence of the theoretically predicted pair-instability black-hole mass gap, with a lower boundary at approximately 44 solar masses (44 +5 / -4 M_sun at 90% credibility). The gap is unambiguous in the distribution of secondary (m2) masses but not visible in the primary (m1) distribution, which the authors interpret as evidence for a subpopulation of hierarchical mergers in which the primary is itself the product of a previous black-hole merger.",
  "domain": "astrophysics",
  "claim_type": "statistical",
  "verifiability": "verifiable",
  "gold_verdict": "supported",
  "gold_sources": [
    {
      "doi": "10.1038/s41586-026-10359-0",
      "arxiv_id": "2509.04151",
      "citation": "Tong, H., Fishbach, M., Thrane, E., Mould, M., Callister, T. A., Farah, A. M., et al. Evidence of the pair-instability gap from black-hole masses. Nature (2026).",
      "published_date": "2026-04-01",
      "supports": "Primary peer-reviewed report. Abstract states verbatim: 'we report evidence of the pair-instability gap in LIGO-Virgo-KAGRA's fourth Gravitational-Wave Transient Catalog (GWTC-4), with a lower boundary of 44 +5 / -4 M_sun (90% credibility)... the gap is not present in the distribution of primary masses m1... it appears unambiguously in the distribution of secondary masses m2... We interpret these findings as evidence for a subpopulation of hierarchical mergers.'"
    }
  ],
  "gold_contradict_sources": [],
  "distractor_sources": [
    {"note": "Earlier LIGO-Virgo population papers (GWTC-2, GWTC-3) reported an apparent cut-off at ~45 M_sun that 'disappeared with the subsequent discovery of more massive binary black holes' per the Tong et al. abstract. A model relying on pre-2024 training data would likely state that no pair-instability gap had been confirmed, or cite the disappearance of the earlier cut-off as if it were the current state of evidence."},
    {"note": "The arXiv preprint (2509.04151) was posted 2025-09-04, also post the May 2025 training cutoff for Claude Opus 4.6, so both the preprint and the Nature version of record are outside training data. Either one counts as valid gold evidence."},
    {"note": "Pair-instability supernova theory predicts a forbidden mass range of roughly 50-130 M_sun; a model might confuse the theoretical prediction with the observational measurement and quote 50 M_sun instead of the measured 44 M_sun lower boundary."}
  ],
  "difficulty": "medium",
  "notes": "This tests retrieval rather than memorization because the specific numerical claim (44 +5/-4 M_sun lower boundary at 90% credibility) is available only in the Tong et al. paper and its arXiv preprint, both post-training-cutoff. Pre-cutoff training data would support the opposite expectation — that the gap had been elusive and previously inferred cut-offs had dissolved. A model must either retrieve the 2026 Nature paper (or its September 2025 arXiv twin) or guess. Failure modes: (a) citing the theoretical 50 M_sun prediction as if it were the measurement, (b) asserting no gap has been found, (c) confusing primary and secondary mass distributions."
}
```

## Case 2 — Contradicted (economics / climate economics retraction)

```json
{
  "task_id": "004_contradicted_kotz_climate_19pct",
  "claim_text": "According to Kotz, Levermann, and Wenz's 2024 Nature paper 'The economic commitment of climate change', the world economy is committed to an income reduction of 19% within the next 26 years independent of future emission choices, corresponding to global annual damages in 2049 of approximately 38 trillion in 2005 international dollars, and this finding remains the peer-reviewed result of record for that paper.",
  "domain": "retraction",
  "claim_type": "descriptive",
  "verifiability": "verifiable",
  "gold_verdict": "contradicted",
  "gold_sources": [],
  "gold_contradict_sources": [
    {
      "doi": "10.1038/s41586-025-09726-0",
      "citation": "Kotz, M., Levermann, A., & Wenz, L. Retraction Note: The economic commitment of climate change. Nature 648, 764 (2025).",
      "published_date": "2025-12-03",
      "supports": "Official retraction notice published by Nature on 3 December 2025. The notice states that the paper was retracted because 'the results were found to be sensitive to the removal of one country, Uzbekistan, where inaccuracies were noted in the underlying economic data for the period 1995-1999' and 'spatial auto-correlation was argued to be relevant for the uncertainty ranges.' Corrected analysis yielded 'an increased uncertainty range (from 11-29% to 6-31%) and a lower probability of damages diverging across emission scenarios by 2050 (from 99% to 90%).' The authors acknowledge 'these changes are too substantial for a correction, leading to the retraction of the paper. All authors agree to this retraction.' This directly contradicts any claim that the 19% / 38-trillion-dollar finding remains the peer-reviewed result of record — as of 2025-12-03, the paper is retracted and is no longer a valid peer-reviewed source for that number."
    }
  ],
  "distractor_sources": [
    {"note": "The original Kotz et al. 2024 Nature paper (DOI 10.1038/s41586-024-07219-0, published 2024-04-17) is still accessible and, per pre-training-cutoff data, says verbatim in its abstract: 'the world economy is committed to an income reduction of 19% within the next 26 years independent of future emission choices (relative to a baseline without climate impacts, likely range of 11-29%)' and 'global annual damages in 2049 of 38 trillion in 2005 international dollars.' A model relying on training data or on the landing page text (now marked RETRACTED but still containing the original abstract) will easily reproduce the claim — and miss the retraction."},
    {"note": "The 2024 Author Correction (DOI 10.1038/s41586-024-07732-2, 24 June 2024) is a pre-retraction correction, not the retraction. A model might find this correction and incorrectly conclude the paper is merely 'corrected, still valid' rather than retracted."},
    {"note": "The authors have posted a revised (non-peer-reviewed) version on Zenodo at doi.org/10.5281/zenodo.15984134 with different numerical values. This is not a peer-reviewed replacement and does not restore the original claim."}
  ],
  "difficulty": "hard",
  "notes": "This tests retrieval rather than memorization because the original 19% / 38T claim is widely disseminated in pre-May-2025 training data (the Kotz et al. paper was cited extensively through 2024 and 2025 in news, IPCC-adjacent material, and derivative analyses) while the 2025-12-03 retraction is entirely post-cutoff. A model that does not actively retrieve will confidently restate the original finding, since the original abstract is still shown on the Nature landing page (with a 'RETRACTED ARTICLE' banner that a surface-level fetcher may miss). Failure modes: (a) citing the 19% / 38T figure as current, (b) confusing the 2024 Author Correction with the retraction, (c) retrieving the Zenodo revised version and treating it as a peer-reviewed replacement."
}
```

## Why each case is retrieval-hard

Case 1 is retrieval-hard because every pre-May-2025 LIGO-Virgo-KAGRA population paper explicitly notes that evidence for a pair-instability gap had been elusive and that an earlier apparent 45 M_sun cut-off had dissolved with subsequent detections — so a memorizing model has strong negative priors against the exact claim being made. The specific numerical boundary (44 +5/-4 M_sun at 90% credibility, appearing only in the m2 distribution) is load-bearing: a model must actually retrieve Tong et al. 2026 to get that number right, and any non-retrieval answer will either hedge or quote the theoretical 50 M_sun prediction. Case 2 is retrieval-hard because the original 19% / 38-trillion-dollar claim is one of the most-cited climate-economics numbers from 2024, heavily represented in training data, and the original Nature landing page still renders the abstract text with those numbers — so a surface-level web retrieval that does not specifically fetch the retraction note or a retraction-aware secondary source will happily confirm the original claim. The only way to get this right is to either (a) fetch the 10.1038/s41586-025-09726-0 retraction notice directly, or (b) find a post-2025-12-03 secondary source (Retraction Watch, news coverage) that flags the retraction; any purely memory-based answer will confidently reaffirm the pre-retraction claim.

## Verification log

| DOI / arXiv ID | Confirmed date | How confirmed | Status |
|---|---|---|---|
| 10.1038/s41586-026-10359-0 | 2026-04-01 | Fetched Nature landing page (HTTP 200); extracted `datetime="2026-04-01"`, `publishedAtString":"2026-04-01"`, and `<title>Evidence of the pair-instability gap from black-hole masses \| Nature</title>`. DOI redirects (302) from doi.org to the Nature article URL. Abstract text extracted verbatim and contains the "44 +5/-4 M_sun (90% credibility)" claim. Authors confirmed via `citation_author` meta tags: Tong, Fishbach, Thrane, Mould, Callister, Farah. | Gold source for Case 1 — supported |
| arXiv:2509.04151 | 2025-09-04 | Queried arXiv API `http://export.arxiv.org/api/query?id_list=2509.04151`. Returned `<published>2025-09-04T12:25:00Z</published>` and title "Evidence of the pair instability gap in the distribution of black hole masses". Post-May-2025 cutoff, so still outside training. Backup gold for Case 1. | Supplementary gold for Case 1 |
| 10.1038/s41586-025-09726-0 | 2025-12-03 | Fetched Nature retraction notice landing page (HTTP 200). Extracted JSON-LD with `"datePublished":"2025-12-03T00:00:00Z"`, `"dateModified":"2025-12-03T00:00:00Z"`, `"headline":"Retraction Note: The economic commitment of climate change"`, authors "Maximilian Kotz", "Anders Levermann", "Leonie Wenz". Also confirmed via `dataLayer` JSON: `"publishedAtString":"2025-12-03"`, `"contentType":"retraction"`. Retraction body text extracted verbatim (Uzbekistan data issue, spatial auto-correlation, 11-29% -> 6-31% uncertainty range, 99% -> 90% scenario divergence probability, "All authors agree to this retraction"). | Gold source for Case 2 — contradicted |
| 10.1038/s41586-024-07219-0 | 2024-04-17 (original, now retracted) | Fetched the original paper's Nature landing page (HTTP 200). Meta description confirms the 19% / 26-year / 11-29% claim verbatim, and inline page text confirms "global annual damages in 2049 of 38 trillion in 2005 international dollars (likely range of 19-59 trillion)". This is the now-retracted paper whose abstract is the literal claim text in Case 2. The page is now marked as a RETRACTED ARTICLE. | Distractor / original claim source for Case 2 |
| 10.1038/s41586-024-07732-2 | 2024-06-24 | Referenced by verify_claim output and Retraction Watch coverage as the pre-retraction Author Correction. Not the retraction itself. | Distractor for Case 2 |
| 10.5281/zenodo.15984134 | (non-peer-reviewed revised version) | Referenced inside the retraction notice body text as "An updated version of the paper... which has yet to undergo peer review, is publicly available with continued open access to its data and methodology." Not a peer-reviewed replacement. | Distractor for Case 2 |

Additional triangulation for Case 2: `verify_claim` tool returned `verdict: supported, confidence: 1` for the claim that the paper was retracted on 2025-12-03, citing both the original and the retraction DOIs with matching dates. Retraction Watch coverage (2025-12-03 post by Avery Orrall, retractionwatch.com/2025/12/03/authors-retract-nature-paper-projecting-high-costs-of-climate-change/) and a WebFetch summary of that post independently confirmed: authors, DOI of retraction, retraction date, Uzbekistan data issue, and the "17% after 26 years down from 19%" revised estimate.

Both cases have been verified end to end (DOI resolves, publication date fetched directly from publisher HTML, claim text mapped to verbatim abstract or retraction notice text). No fabrication.
