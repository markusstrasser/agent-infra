# Supplement Database Survey — April 2026

> **Purpose:** Identify free databases, APIs, ontologies, and packages for supplement verification beyond what we already have wired.
> **Already wired:** NIH DSLD (labels), biomedical MCP (CPIC/PharmGKB/ClinVar/DGIdb/FDA), BioMCP, scite, Semantic Scholar, Exa verify_claim.
> **Assessed and rejected:** SUPP.AI (frozen Oct 2021), NIH ODS API (40 nutrients, narrative only).

## Databases & APIs

| Source | URL | API? | Data Type | Coverage | Worth Wiring? | Reason |
|--------|-----|------|-----------|----------|---------------|--------|
| **USDA FoodData Central** | fdc.nal.usda.gov | REST/JSON, free API key | Nutrient composition of foods + some supplements | 380K+ foods, SR Legacy + Foundation | **Yes** | Cross-check dietary nutrient intake estimates. API key free via data.gov. Already has Python wrapper (`noms`). |
| **OpenFDA CAERS** | api.fda.gov/food/event | REST/JSON, no auth | Adverse event reports for supplements | All CAERS reports since 2004 | **Yes** | Check if any of our supplements have adverse event signals. Free, well-documented API. |
| **Health Canada LNHPD** | health-products.canada.ca | REST/JSON, no auth | Licensed natural health product monographs | 90K+ products (Canada) | **Maybe** | Monographs include approved claims/conditions/doses. Better evidence structure than DSLD. But Canada-specific products. |
| **MSKCC About Herbs** | aboutherbs.mskcc.org | No API (web only) | Expert-curated supplement-drug interactions, mechanisms, evidence summaries | ~300 herbs/supplements | **Maybe (scrape)** | Best free expert-curated supplement safety data. No API but structured HTML. Worth a one-time extraction for our ~30 supplements. |
| **DrugBank Open** | go.drugbank.com | XML bulk download (academic free) | Drug/nutraceutical pharmacology, mechanisms, targets | 7,800+ drugs + ~200 nutraceuticals | **No** | Mostly pharma. Nutraceutical coverage thin. We already have DGIdb + biomedical MCP for drug data. |
| **ChEBI** | ebi.ac.uk/chebi | REST/SOAP, free | Chemical ontology — supplement compounds | 60K+ chemical entities | **Maybe** | Useful for mapping supplement names to chemical structures and mechanism classifications. SPARQL endpoint available. |
| **PubChem** | pubchem.ncbi.nlm.nih.gov | REST/JSON (PUG REST), free | Chemical properties, bioactivities, compound-gene links | 116M compounds | **Maybe** | Bioactivity data for supplement compounds. Could verify mechanism claims (e.g., "ashwagandha inhibits NF-κB"). Large, noisy. |
| **Wikidata** | wikidata.org | SPARQL, free | Structured entity data — supplements, mechanisms, diseases | Variable | **No** | Coverage for supplements is sparse and unreliable. Not an authority source. |
| **EFSA Opinions** | efsa.europa.eu | No REST API | Safety/efficacy opinions on supplement ingredients | ~500 opinions | **No** | No API. PDF-only opinions. Would need manual extraction. Low ROI for 30 supplements. |
| **NatMed / TRC** | naturalmedicines.therapeuticresearch.com | No free API | Evidence-graded efficacy, interactions, dosing | 1,200+ supplements | **No** | Paywalled. No free API. Same company runs DSLD data entry for NIH. The gold standard alongside Examine — but locked. |
| **ConsumerLab** | consumerlab.com | No API | Product testing, purity verification | ~1,000 products tested | **No** | Paywalled. No API. Tests actual product contents but locked behind subscription. |
| **HerbMedPro** | herbmed.org | No API | Evidence-graded herb monographs | ~250 herbs | **No** | Paywalled. Academic institution access only. |
| **Australian TGA ARTG** | tga.gov.au | Search only, no REST | Registered complementary medicines (Australia) | 15K+ products | **No** | No API. Australia-specific. Low relevance. |
| **USP DSC** | usp.org | No API | Quality standards for supplement ingredients | Standards, not evidence | **No** | Paywalled. Reference standards, not efficacy data. |

## Ontologies & Identifiers

| Ontology | Use Case | Worth Using? |
|----------|----------|--------------|
| **MeSH** (NLM) | Standard vocabulary for PubMed supplement searches. Already implicit in our S2/scite queries. | Already used indirectly |
| **NCI Thesaurus** | Maps supplement names to standardized terms. Useful for disambiguation. | Maybe — if we need cross-database joins |
| **ChEBI** | Chemical hierarchy for supplement compounds. Could map "ashwagandha" → withanolides → specific withanolide A/D structures. | Maybe — mechanism verification |
| **UNII** (FDA) | Unique ingredient identifiers. DSLD already includes UNII codes per ingredient. | Already in DSLD data |
| **FooDB** (foodb.ca) | Food compound database — maps foods to their bioactive compounds. | No — more granular than needed |

## Python Packages

| Package | What it does | Worth using? |
|---------|-------------|--------------|
| **`noms`** | Python wrapper for USDA FoodData Central API | Maybe — if we add dietary intake estimation |
| **`pymedtermino`** | Access UMLS, ICD, SNOMED, MeSH terminologies | No — overkill for our use case |
| **`chembl_webresource_client`** | ChEMBL bioactivity data | Maybe — for mechanism verification |
| **`biopython`** | GenBank, PDB, BLAST — not supplement-relevant | No |

## Recommendation: What to Wire Next

### Tier 1 — High value, easy integration
1. **OpenFDA CAERS** — adverse event signals for our supplements. Free REST API, no auth. Build a simple query: "any adverse events reported for ashwagandha/lion's mane/tongkat ali?" Safety data we currently lack.
2. **USDA FoodData Central** — nutrient composition for dietary intake estimates. Relevant for "am I getting enough magnesium from food?" calculations. Free API key.

### Tier 2 — Moderate value, more effort
3. **MSKCC About Herbs** — one-time scrape of our ~30 supplements. Expert-curated interactions and mechanisms. No API but structured pages.
4. **Health Canada LNHPD** — monographs with approved conditions/doses. REST API exists.

### Tier 3 — Low priority
5. **PubChem bioactivity** — mechanism verification for supplement compounds. Large and noisy.
6. **ChEBI** — chemical ontology mapping. Only needed if we want to do cross-database compound matching.

### Not worth pursuing
Everything paywalled (NatMed, ConsumerLab, HerbMedPro, USP) and everything without an API (EFSA, TGA, Wikidata for supplements).

## The Actual Gap (unchanged)

No free database provides structured **dose-response efficacy data graded by evidence quality per condition**. That remains Examine's moat. The free landscape gives us:
- **What's in the bottle** → DSLD ✓
- **What adverse events are reported** → OpenFDA CAERS (to wire)
- **What drugs interact** → biomedical MCP ✓
- **What papers say** → S2 + scite ✓
- **Whether the web agrees with a claim** → Exa verify_claim ✓

Missing: "Does X work for condition Y, at what dose, with what evidence grade?" — only Examine and NatMed have this, both paywalled.

<!-- knowledge-index
generated: 2026-04-05T19:01:14Z
hash: 5fe3f6ce06da


end-knowledge-index -->
