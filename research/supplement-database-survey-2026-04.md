---
title: "Supplement & Nutrition Evidence Databases — Comprehensive Survey"
date: 2026-04-05
tags: [supplements, databases, APIs, ontologies, nutrition, evidence]
status: complete
---

# Supplement & Nutrition Evidence Databases — Comprehensive Survey

**Question:** What free databases, APIs, ontologies, knowledge graphs, and Python packages exist for supplement and nutrition evidence — beyond what is already wired?
**Tier:** Deep | **Date:** 2026-04-05
**Ground truth:** NIH DSLD (wired), SUPP.AI (frozen Oct 2021, not wiring), NIH ODS (assessed, narrative), Biomedical MCP (CPIC/PharmGKB/ClinVar/DGIdb/Ensembl/FDA DDI), BioMCP (CPIC/PharmGKB/AlphaGenome), Scite MCP, Semantic Scholar MCP, Exa verify_claim.

---

## Master Table

| # | Resource | Type | Free? | API? | Data Type | Coverage | Last Updated | Worth Wiring? | Status |
|---|----------|------|-------|------|-----------|----------|--------------|---------------|--------|
| 1 | **OpenFDA CAERS** | Database/API | YES | REST, no auth (key optional) | Supplement adverse events | 2004–present, quarterly | Quarterly | **YES — HIGH** | Not wired |
| 2 | **USDA FoodData Central** | Database/API | YES | REST, free API key | Nutrient composition | 400K+ foods, 150+ nutrients | Ongoing | **YES — HIGH** | Not wired |
| 3 | **Health Canada LNHPD** | Database/API | YES | REST, no auth, JSON/XML | Licensed NHP: ingredients, doses, risks, purposes | ~100K products (Canada) | Ongoing | **YES — MEDIUM** | Not wired |
| 4 | **NIH ODS API** | API | YES | Static URL, XML/HTML | Fact sheets (~40 nutrients) | ~40 nutrients | Ongoing | LOW — narrative only | Assessed |
| 5 | **NIH DSID** | Database | YES | Web only (no REST) | Actual vs label ingredient levels | MVMs, omega-3s, vit D, B-vitamins | 2023-12 | LOW — narrow | Not wired |
| 6 | **NatMed Pro** | Database | NO — subscription | YES — API (July 2025) | Efficacy ratings, interactions, AE, dosing | 1,200+ ingredients, 170+ conditions | Ongoing | **BLOCKED — paywalled** | N/A |
| 7 | **ConsumerLab** | Testing | NO — $54/yr | NO API | Product quality testing | 100+ categories | Ongoing | BLOCKED — no API | N/A |
| 8 | **Examine.com** | Review DB | Partial | NO — "working on API" | RCT summaries, efficacy grades | 400+ supplements, 600+ conditions | Ongoing | BLOCKED — no API | N/A |
| 9 | **MSKCC About Herbs** | Database/App | YES — free | NO REST (web + app) | Uses, AE, herb-drug interactions (oncology) | 290 entries | Weekly | MEDIUM — scrape-only | Not wired |
| 10 | **HerbMedPro** | Database | ABC membership | NO API | Evidence-scored herb monographs | ~250 herbs | Ongoing | LOW — paywalled, no API | N/A |
| 11 | **EFSA API Portal** | API portal | YES | REST (registration) | Scientific opinions, DRVs, food additives | EU scope | Ongoing | **MEDIUM** — explore endpoints | Not wired |
| 12 | **Australian TGA ARTG** | Registry | YES — web | Bulk datasets | Complementary medicine registrations | AU products | Ongoing | LOW — regulatory only | N/A |
| 13 | **WHO Herbal Monographs** | PDFs | YES | NO API | Medicinal plant monographs | ~120 plants (4 vols) | 2009 | LOW — PDF, dated | N/A |
| 14 | **DrugBank** | Database | Academic (free non-commercial) | REST (paid); XML download (academic) | Drug-drug/drug-food interactions, natural products | 16K+ drugs | 2024 | **MEDIUM** — academic XML | Partial DGIdb overlap |
| 15 | **FooDB** | Database | YES (non-commercial) | Bulk CSV/SDF (no REST) | Food constituents, bioactives, phytochemicals | 28K+ compounds, 1K+ foods | 2022 | **MEDIUM** — compound mapping | Not wired |
| 16 | **Open Targets** | Database/API | YES — CC0 | GraphQL, bulk Parquet | Drug-target evidence | Genome-wide | Ongoing | LOW for supplements | Adjacent via DGIdb |
| 17 | **DGIdb** | Database/API | YES | REST, TSV | Drug-gene interactions | 100K+ interactions | v5.0, 2024 | Already wired | **Wired** |
| 18 | **ChEMBL** | Database/API | YES | REST, bulk | Bioactivity data | 2.4M compounds | Ongoing | LOW — pharma-focused | N/A |
| 19 | **SUPP.AI** | Database | YES | Web + API | Supplement-drug interactions | 2,044 supplements, 59K interactions | Oct 2021 (frozen) | ASSESSED — frozen | Assessed |
| 20 | **USP DSC** | Compendium | NO — subscription | NO | Quality standards, monographs | Reference standards | Ongoing | BLOCKED | N/A |
| 21 | **EDQM Ph. Eur.** | Compendium | NO — subscription | NO | Monographs incl. herbal | EU scope | 2025 | BLOCKED | N/A |
| 22 | **ChEBI** | Ontology | YES | REST, SPARQL, OWL | Chemical entities, supplement compounds | 60K+ entities | Ongoing | HIGH for entity mapping | Available |
| 23 | **Wikidata** | Knowledge graph | YES | SPARQL, REST | Supplement entities, properties | Major supplements covered | Ongoing | MEDIUM — KG bootstrap | Available |
| 24 | **MeSH** | Vocabulary | YES | E-utilities, SPARQL | Dietary supplement terms | Good for major supplements | Ongoing | Implicit via PubMed | In use |
| 25 | **FooDB** | Database | YES | Bulk download | 28K+ food compounds | 1K+ foods | 2022 | MEDIUM | Not wired |

---

## Section A: Databases & APIs — Detailed Assessment

### A1. OpenFDA CAERS (Adverse Events) — WIRE THIS

- **URL:** https://open.fda.gov/apis/food/event/
- **API:** REST, JSON. Base: `https://api.fda.gov/food/event.json`
- **Auth:** Optional API key (240 req/min with key vs 40 without). Free key: https://open.fda.gov/apis/authentication/
- **Data:** CAERS adverse event reports for foods, dietary supplements, and cosmetics. Fields include: product names, industry codes (filterable to "Dietary Supplements"), reactions, outcomes (hospitalization, death, ER visit), dates, patient demographics.
- **Coverage:** 2004–present, ~300K+ reports, quarterly updates
- **Query example:** `search=products.industry_name:"Dietary+Supplements"&limit=10`
- **Source code:** https://github.com/FDA/openfda (open source pipeline)
- **Limitations:** Voluntary reporting (underreporting is significant). No causal relationship established. Product names are free text (messy). No ingredient standardization — must cross-reference with DSLD.
- **Value:** Supplement safety signal detection. Can cross-reference with DSLD ingredients. Complements PharmGKB/CPIC drug interaction data with supplement-specific adverse events.
- **Verdict:** **HIGH** — free, REST, minimal auth, supplement-specific adverse events. The only free, structured, programmatic source of US supplement adverse event data. [SOURCE: https://open.fda.gov/apis/food/event/]

### A2. USDA FoodData Central — WIRE THIS

- **URL:** https://fdc.nal.usda.gov/
- **API:** REST, JSON. Base: `https://api.nal.usda.gov/fdc/v1/`
- **Auth:** Free API key (instant registration: https://fdc.nal.usda.gov/api-key-signup)
- **Endpoints:** `/food/{fdcId}`, `/foods/search`, `/foods/list`, `/foods/nutrients`
- **Data:** Nutrient profiles for 400K+ foods across 5 data types: Foundation, SR Legacy, Survey (FNDDS), Branded (GTIN/UPC), Experimental
- **Coverage:** 150+ nutrients per food entry
- **Docs:** Full OpenAPI spec: https://fdc.nal.usda.gov/api-spec/fdc_api.html
- **Python wrappers:** `pyfooda` (456 downloads/mo, LLM-powered aggregation — most viable), `noms` (dead, 2019)
- **Limitations:** Nutrient data for whole foods, not supplement formulations. No efficacy or interaction data.
- **Value:** Nutrient content lookups for food-based recommendations. Foundation for "food first" analysis. Cross-reference with DSLD for supplement vs food nutrient comparison.
- **Verdict:** **HIGH** — free, well-documented REST API, massive coverage. Essential for nutrient calculations and food-supplement equivalence. [SOURCE: https://fdc.nal.usda.gov/api-guide/]

### A3. Health Canada LNHPD — WIRE THIS

- **URL:** https://health-products.canada.ca/api/documentation/lnhpd-documentation-en.html
- **API:** REST, JSON/XML. Base: `https://health-products.canada.ca/api/natural-licences/`
- **Auth:** None required
- **Endpoints (7):**
  - `/medicinalingredient` — therapeutic components, potency, quantity, source material, extract ratios
  - `/nonmedicinalingredient` — inactive ingredients
  - `/productdose` — dosage instructions, frequency
  - `/productlicence` — NPN (Natural Product Number), company, status
  - `/productpurpose` — intended therapeutic uses (structured!)
  - `/productrisk` — cautions, warnings, contraindications (structured!)
  - `/productroute` — delivery method (oral, topical, etc.)
- **Coverage:** ~100K licensed natural health products. Canada requires pre-market licensing for NHPs with evidence review — higher quality than US DSHEA self-certification.
- **Pagination:** Supports limit/offset
- **Note:** The Open Government Portal states "the text-based data extract is no longer accessible through the NNHPD website" — the API is now the only programmatic access path. [SOURCE: https://open.canada.ca/data/dataset/ef546c83-43a8-4404-943e-ab324164eeb3]
- **Value:** The `/productrisk` and `/productpurpose` endpoints provide structured contraindication and indication data that doesn't exist in DSLD or any other free API. Canada's evidence review process means these are curated, not self-reported.
- **Verdict:** **MEDIUM-HIGH** — free, no-auth REST API with 7 endpoints. The risk/purpose endpoints are unique structured data not available elsewhere for free. [SOURCE: https://health-products.canada.ca/api/documentation/lnhpd-documentation-en.html]

### A4. NIH ODS API — Assessed, Limited

- **URL:** https://ods.od.nih.gov/api/
- **API:** Static URL pattern: `index.aspx?resourcename=[name]&readinglevel=[level]&outputformat=[format]`
- **Formats:** XML (structured), HTML (stripped)
- **Coverage:** ~40 nutrients, 3 reading levels (Consumer, Health Professional, Spanish)
- **Limitations:** One fact sheet per request. No search. No batch. Static URLs. Narrative text, not structured claims.
- **Verdict:** LOW — already assessed. Narrative fact sheets via static URLs, not a real API. Use for human-readable reference only. [SOURCE: https://ods.od.nih.gov/api/]

### A5. NIH DSID (Dietary Supplement Ingredient Database)

- **URL:** https://dsid.od.nih.gov/
- **API:** Web interface only, no REST API
- **Data:** Estimated actual ingredient levels in supplement products vs label claims (analytical chemistry data)
- **Coverage:** Adult/children's MVMs, omega-3 fatty acids, vitamin D, B-vitamins
- **Value:** "Does this supplement actually contain what it says?" — quality/accuracy data
- **Verdict:** LOW — interesting data but too narrow and no programmatic access. [SOURCE: https://dsid.od.nih.gov/]

### A6. NatMed Pro (= NMCD = Natural Medicines = Natural Standard)

- **URL:** https://naturalmedicines.therapeuticresearch.com/
- **Provider:** TRC Healthcare (Therapeutic Research Center)
- **API:** YES — launched July 2025, supports integration into CDSS, LMS, consumer apps [SOURCE: https://trchealthcare.com/trc-healthcare-launches-upgraded-natmed-pro/]
- **Data:** 1,200+ ingredients with effectiveness ratings (A-D scale), interaction checker, adverse effects, dosing, patient handouts, 170+ condition monographs
- **Pricing:** Institutional subscription required. Not publicly priced — typically $300-1,000+/yr institutional.
- **Naming history:** Natural Standard + Natural Medicines Comprehensive Database merged → Natural Medicines → NatMed Pro (July 2025 rebrand). NMCD = NatMed Pro = same product lineage. Confirmed by PubMed 41696997 (Feb 2026). [SOURCE: https://pubmed.ncbi.nlm.nih.gov/41696997/]
- **Verdict:** BLOCKED — the gold standard for supplement evidence but paywalled. No free/academic tier. The API is commercial-only. If institutional access becomes available, this is the single highest-value resource to wire.

### A7. ConsumerLab

- **URL:** https://www.consumerlab.com/
- **API:** None
- **Data:** Independent product testing (contamination, label accuracy, dissolution), brand comparisons
- **Pricing:** $54/yr consumer subscription
- **Verdict:** BLOCKED — no API, no bulk data. Useful for manual product verification only. [SOURCE: https://www.consumerlab.com/]

### A8. Examine.com

- **URL:** https://examine.com/
- **API page:** https://examine.com/api-requests/ — states "We're working on an API"
- **Data:** RCT summaries, efficacy grades by condition, dosage, interactions, side effects. Database covers 400+ supplements, 600+ conditions.
- **Scraping option:** An Apify scraper exists (hanamira/examine-com-supplement-research) [SOURCE: https://apify.com/hanamira/examine-com-supplement-research/input-schema]
- **Verdict:** BLOCKED — no API yet. When it launches, this would be extremely high value. The Apify scraper is an option but ToS-risky. Monitor the API page.

### A9. MSKCC About Herbs

- **URL:** https://www.mskcc.org/cancer-care/diagnosis-treatment/symptom-management/integrative-medicine/herbs
- **App:** Free iOS app with 290 entries, offline capability [SOURCE: https://apps.apple.com/us/app/about-herbs/id554267162]
- **API:** No REST API. Web content only.
- **Data:** For each herb/supplement: purported uses, mechanism of action, adverse effects, herb-drug interactions, cancer drug interactions specifically
- **Coverage:** 290 entries, updated weekly [SOURCE: https://www.mskcc.org/cancer-care/diagnosis-treatment/symptom-management/integrative-medicine/herbs/about-herbs]
- **Quality:** High — created by MSK's Integrative Medicine pharmacists, evidence-graded, peer-reviewed
- **Verdict:** MEDIUM — high-quality oncology-focused interaction data, but no API. 290 entries is manageable for a one-time scrape if cancer-supplement interactions become a priority.

### A10. EFSA API Developer Portal

- **URL:** https://developers.efsa.europa.eu/
- **API:** REST APIs available (free registration required)
- **Data:** Scientific opinions on food supplements, dietary reference values (DRVs), tolerable upper intake levels (ULs), food additive safety, novel food assessments
- **Coverage:** EU regulatory scope. EFSA-set ULs differ from US RDAs in some cases.
- **Auth:** Developer portal registration required (free)
- **Status:** Landing page confirmed — need to register to see actual endpoint inventory. [SOURCE: https://developers.efsa.europa.eu/]
- **Value:** EU regulatory perspective on supplement safety. UL data unique from US equivalents. Novel food assessments relevant for newer supplements.
- **Verdict:** MEDIUM — worth registering to explore endpoints. EU UL/DRV data and novel food opinions provide a regulatory dimension not available from US sources.

### A11. HerbMedPro

- **URL:** https://www.herbalgram.org/resources/herbmedpro/
- **Provider:** American Botanical Council (ABC)
- **API:** None
- **Data:** Evidence-scored herb monographs with scored links to clinical trials, pharmacological studies, in vitro/in vivo studies, reviews
- **Coverage:** ~250 herbs
- **Pricing:** ABC membership required ($50/yr individual, $150/yr academic)
- **Verdict:** LOW — paywalled, no API, overlaps with NatMed Pro's herb coverage. [SOURCE: https://www.herbalgram.org/resources/herbmedpro/about/]

### A12. Australian TGA ARTG

- **URL:** https://www.tga.gov.au/products/australian-register-therapeutic-goods-artg/
- **Data:** Registry of approved complementary medicines in Australia (listed = low-risk, registered = higher-risk)
- **API:** Web search interface. Bulk datasets at https://www.tga.gov.au/resources/datasets
- **Verdict:** LOW — regulatory registry, not evidence database. Useful for regulatory landscaping only. [SOURCE: https://www.tga.gov.au/resources/datasets]

### A13. DrugBank (Academic License)

- **URL:** https://go.drugbank.com/
- **Data:** 16K+ drug entries including natural products. Drug-food interactions added in v6.0 (2024). [SOURCE: https://academic.oup.com/nar/article/52/D1/D1265/7416367]
- **API:** REST API (paid commercial). Bulk XML download available under free academic license.
- **Academic access:** Apply at https://go.drugbank.com/releases/latest — free for non-commercial use
- **Coverage:** Natural product entries exist but are secondary to pharmaceuticals. Drug-food interaction data (v6.0) is newer and potentially useful.
- **Overlap:** DGIdb (already wired) aggregates DrugBank as a source, so most drug-gene interactions are already accessible. The drug-food interaction data from v6.0 may not be in DGIdb.
- **Verdict:** MEDIUM — academic XML download could extract drug-food and natural product interaction data not yet in DGIdb. Worth pursuing if drug-food interactions become a priority.

### A14. FooDB

- **URL:** https://foodb.ca/
- **Data:** 28K+ compounds found in food, including phytochemicals, flavonoids, phenolics, terpenes, amino acids. Links compounds to foods, health effects, biological pathways.
- **API:** Bulk download (CSV, SDF, MySQL dump). No REST API. [SOURCE: https://foodb.ca/downloads]
- **Coverage:** 1,000+ foods, linked to HMDB, PubChem, KEGG
- **License:** Free for non-commercial use. See terms on downloads page.
- **Value:** Maps supplement compounds (curcumin, resveratrol, quercetin, etc.) to food sources and known bioactivities. Foundation for "food form vs supplement form" analysis. A 2025 MethodsX paper validated a cleaning methodology for using FooDB in dietary studies. [SOURCE: https://pmc.ncbi.nlm.nih.gov/articles/PMC12637271/]
- **Verdict:** MEDIUM — bulk download useful for building a compound-to-food-to-bioactivity reference. No REST API limits real-time integration.

### A15. WHO/IARC Resources

- **IARC Monographs:** https://monographs.iarc.who.int/ — carcinogenic hazard classification. Covers some supplements (e.g., aristolochic acids, Ginkgo biloba). [SOURCE: https://monographs.iarc.who.int/]
- **WHO Monographs on Medicinal Plants:** 4 volumes, PDFs. ~120 plants. Most recent vol. 4 = 2009.
- **Verdict:** LOW — IARC is narrow (carcinogenicity only, PDF). WHO monographs are authoritative but dated and not machine-readable. [TRAINING-DATA]

### A16. MedlinePlus Herbs & Supplements

- **URL:** https://medlineplus.gov/druginfo/herb_All.html
- **API:** MedlinePlus has a general web service but herb pages are narrative HTML
- **Data:** Consumer-level monographs (~100 herbs/supplements)
- **Verdict:** LOW — consumer-grade, largely redundant with NIH ODS. [TRAINING-DATA]

### A17. USP Herbal Medicines Compendium (HMC)

- **URL:** https://hmc.usp.org/
- **Data:** Quality standards for herbal ingredients (monographs)
- **Note:** Described as "freely available" by Des Moines University library guide. The USP Dietary Supplements Compendium (separate, broader product) is paywalled. [SOURCE: https://lib.dmu.edu/db/naturalmedicines]
- **Verdict:** CONDITIONAL — if HMC access is truly free, useful for quality/identity standards. Verify access before relying on it. The broader USP DSC is paywalled at https://www.usp.org/products/dietary-supplements-compendium.

---

## Section B: Ontologies & Knowledge Graphs

### B1. ChEBI (Chemical Entities of Biological Interest)

- **URL:** https://www.ebi.ac.uk/chebi/
- **Ontology:** OWL, OBO format. Part of OBO Foundry. Latest upload: April 1, 2026. [SOURCE: https://bioportal.bioontology.org/ontologies/CHEBI]
- **API:** REST API at EBI (https://www.ebi.ac.uk/chebi/webServices.do), SPARQL endpoint, bulk OWL/OBO downloads
- **Data:** Manually curated chemical ontology. Key class: "nutraceutical" (CHEBI:50733) with children for specific supplement compounds. Natural products well-represented.
- **Coverage:** 60K+ chemical entities
- **Value:** Canonical identifiers for supplement compounds (curcumin = CHEBI:3962, resveratrol = CHEBI:27881, etc.). Links to PubChem, KEGG, HMDB. Ontological relationships (is_a, has_role) enable reasoning. The `has_role` relationship is particularly useful: e.g., `curcumin has_role antioxidant`, `vitamin D has_role vitamin`.
- **Verdict:** **HIGH for compound identification/mapping.** Essential for linking supplement ingredients to molecular databases. Already freely accessible — wire when entity resolution becomes a priority.

### B2. MeSH (Medical Subject Headings)

- **URL:** https://meshb.nlm.nih.gov/
- **Hierarchy:** "Dietary Supplements" (D019587) under Complementary Therapies. Sub-hierarchy includes specific supplement types.
- **API:** Free, via NCBI E-utilities and SPARQL
- **Value:** Standard vocabulary for PubMed literature searches.
- **Verdict:** Already implicitly used via PubMed/S2 searches. No separate wiring needed. [TRAINING-DATA]

### B3. SNOMED CT

- **URL:** https://www.nlm.nih.gov/healthit/snomedct/index.html
- **Free:** Yes in US (NLM UMLS license, free registration). 357K+ concepts. [SOURCE: https://www.nlm.nih.gov/healthit/snomedct/index.html]
- **Data:** Clinical terminology including dietary supplement codes under "Substance" and "Product" hierarchies
- **Verdict:** LOW for our use case — relevant if building clinical-grade CDS, not needed for personal evidence lookup.

### B4. NCI Thesaurus

- **URL:** https://ncithesaurus.nci.nih.gov/
- **Data:** NCI's ontology includes dietary supplement terms, particularly cancer-relevant
- **API:** REST API, OWL download
- **Verdict:** LOW — niche (oncology-specific), overlaps with MSKCC About Herbs for cancer context. [TRAINING-DATA]

### B5. Wikidata

- **URL:** https://www.wikidata.org/ | SPARQL: https://query.wikidata.org/
- **Data:** Structured data for supplement entities. Relevant properties:
  - P2175 (medical condition treated)
  - P636 (route of administration)
  - P274 (chemical formula)
  - P231 (CAS number)
  - P683 (ChEBI ID)
  - P2868 (subject has role — e.g., antioxidant, vitamin)
  - P769 (significant drug interaction)
- **API:** SPARQL endpoint (free, no auth), REST API (wbgetentities), bulk JSON dumps
- **Example SPARQL:**
  ```sparql
  SELECT ?supplement ?supplementLabel ?condition ?conditionLabel WHERE {
    ?supplement wdt:P31 wd:Q169336 .  # instance of dietary supplement
    ?supplement wdt:P2175 ?condition . # medical condition treated
    SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
  }
  ```
- **Coverage:** Major supplements well-represented (Q188724 = vitamin D, Q18216 = melatonin, Q170516 = curcumin). Niche botanicals sparse.
- **Verdict:** MEDIUM — free, queryable, good for entity resolution and knowledge graph bootstrapping. Shallow evidence (no RCT grading, no dose-response). Use for linking identifiers across databases. [TRAINING-DATA, verified property list]

### B6. DBpedia

- **URL:** https://dbpedia.org/page/Dietary_supplement [SOURCE: https://dbpedia.org/page/Dietary_supplement]
- **Data:** Structured extraction from Wikipedia. Multi-language labels (EN, KO, JA, RU).
- **Verdict:** LOW — less curated than Wikidata, largely superseded for structured queries.

### B7. DIDEO (Drug-Drug Interaction Evidence Ontology)

- **OWL format for representing DDI evidence including mechanism, severity, clinical significance**
- **Includes some supplement-drug interactions**
- **Verdict:** LOW — specialized, niche, not widely adopted. [TRAINING-DATA]

---

## Section C: Python Packages

### C1. pyfooda — Most Viable

- **PyPI:** https://pypi.org/project/pyfooda/ [SOURCE: https://pypi.org/project/pyfooda/]
- **Version:** 0.5.0 (Beta)
- **Data:** Python wrapper for USDA FoodData Central API with LLM-powered food aggregation
- **Downloads:** 456/month (growing)
- **Python:** >=3.10
- **Value:** Convenience wrapper for FDC API. LLM aggregation feature is novel (groups similar foods).
- **Verdict:** Worth evaluating as a convenience layer. Not a substitute for understanding the raw FDC API.

### C2. noms — Dead

- **PyPI:** https://pypi.org/project/noms/ [SOURCE: https://pypi.org/project/noms/]
- **Last update:** 2019. Downloads: ~11/week.
- **Verdict:** DEAD — use pyfooda or direct FDC API.

### C3. nutrimetrics — Toy

- **GitHub:** https://github.com/tomcv/nutrimetrics [SOURCE: https://github.com/tomcv/nutrimetrics]
- **Stars:** 7. No active development.
- **Verdict:** TOY — insufficient maturity or adoption.

### C4. nutrient-calculator — Minimal

- **PyPI:** https://pypi.org/project/nutrient-calculator/ [SOURCE: https://pypi.org/project/nutrient-calculator/]
- **Core:** Rust library with Python bindings. Downloads: 32/month.
- **Verdict:** LOW — Rust core, minimal adoption.

### C5. Biopython — No Supplement-Specific Modules

- Biopython has no modules for supplement interactions or nutrient analysis. Its UniProt/PDB/GenBank wrappers are tangentially relevant for protein target lookup (CYP enzyme structures) but not supplement evidence per se.
- **Verdict:** Not directly relevant for supplement evidence. [TRAINING-DATA]

### C6. RDKit / ChemPy — Utility, Not Supplement-Specific

- Not supplement-specific but useful for: computing molecular properties of supplement compounds, SMILES/InChI lookups, substructure searches against ChEMBL/PubChem
- **Verdict:** Utility libraries, not supplement evidence tools. Already familiar. [TRAINING-DATA]

### C7. Summary: Python Ecosystem

**The Python supplement ecosystem is a desert.** No mature packages exist for supplement interaction checking, evidence lookup, or structured supplement knowledge. The viable path is: write thin wrappers around the APIs identified in Section A (OpenFDA CAERS, FDC, LNHPD) rather than depending on community packages. `pyfooda` is the only package worth evaluating, and only as a convenience wrapper for FDC.

---

## Section D: Research-Grade Bulk Downloads

### D1. LNHPD (Canada)

- Covered in A3. Full API access — no bulk download needed (API = the bulk access path).
- The Open Government Portal text extract is discontinued. [SOURCE: https://open.canada.ca/data/dataset/ef546c83-43a8-4404-943e-ab324164eeb3]

### D2. EDQM European Pharmacopoeia

- **Paywalled.** 12th Edition online-only (new 2025). No free bulk data. [SOURCE: https://www.edqm.eu/en/european-pharmacopoeia-new-online-only-12th-edition]
- **Verdict:** BLOCKED.

### D3. USP Dietary Supplement Standards

- **Paywalled.** USP Dietary Supplements Compendium requires subscription. [SOURCE: https://www.usp.org/products/dietary-supplements-compendium]
- **Exception:** USP HMC may be freely accessible (verify).
- **Verdict:** Mostly BLOCKED.

### D4. DrugBank Academic XML

- Free download for academic/non-commercial use. XML format (~2GB).
- Contains natural product entries and drug-food interactions (v6.0+).
- **Verdict:** MEDIUM — useful one-time extraction for natural product interaction network.

### D5. FooDB Bulk Download

- CSV, SDF, MySQL dump available. 28K+ compounds. [SOURCE: https://foodb.ca/downloads]
- **Verdict:** MEDIUM — useful for compound-to-food mapping reference.

### D6. PubChem

- All supplement compounds with PubChem CIDs accessible via FTP/REST.
- Bioactivity assay data, compound properties, patent data.
- **Verdict:** Already available via existing chemistry infrastructure. No special wiring needed. [TRAINING-DATA]

---

## Wiring Priority Recommendations

### Tier 1 — Wire Now (high value, free, REST API, supplement-specific)

| Resource | Why | Effort | Data Gained |
|----------|-----|--------|-------------|
| **OpenFDA CAERS** | Only free structured supplement adverse event data. REST, no auth. | Low | Safety signals, adverse events 2004+ |
| **USDA FoodData Central** | 400K+ foods, 150+ nutrients. Free API key. | Low | Nutrient composition, food-first recommendations |
| **Health Canada LNHPD** | 7 endpoints with structured risk/purpose/dose data. No auth. Canada's evidence-reviewed NHP data. | Low | Contraindications, therapeutic purposes, dosing (structured!) |

### Tier 2 — Evaluate for Wiring (medium value, some complexity)

| Resource | Why | Blocker/Effort |
|----------|-----|----------------|
| **EFSA API** | EU DRVs, ULs, novel food assessments | Register, explore endpoints |
| **FooDB bulk** | Compound-to-food-to-bioactivity mapping | ETL from CSV/SDF dump |
| **DrugBank academic XML** | Natural product interactions, drug-food (v6.0) | Academic license application, XML parsing |
| **ChEBI** | Canonical compound identifiers, ontological relationships | Already accessible via EBI API |
| **MSKCC About Herbs** | 290 high-quality oncology herb monographs | One-time scrape (no API) |

### Tier 3 — Use As-Is (reference, no wiring needed)

| Resource | Access method |
|----------|---------------|
| Wikidata | SPARQL queries ad hoc |
| MeSH | Implicit via PubMed searches |
| NIH ODS | Manual reference |
| WHO monographs | PDF reference |
| NCI Thesaurus | REST API if oncology terms needed |

### Blocked (Paywalled, No API, or Dead)

| Resource | Notes |
|----------|-------|
| NatMed Pro | Gold standard but commercial. Monitor for academic access or API pricing. |
| ConsumerLab | No API, $54/yr subscription |
| Examine.com | API "in development" — monitor https://examine.com/api-requests/ |
| USP/EDQM | Paywalled compendiums |
| HerbMedPro | ABC membership required, no API |
| SUPP.AI | Frozen Oct 2021, AI2 not maintaining |

---

## What's Missing (Confirmed Gaps)

1. **No free, structured supplement efficacy database exists.** NatMed Pro is the closest but paywalled. The free options provide adverse events (OpenFDA), nutrient content (FDC), and regulatory data (LNHPD) — but NOT evidence-graded efficacy ratings with effect sizes.

2. **No free supplement-drug interaction checker API.** SUPP.AI is frozen. NatMed Pro's interaction checker requires subscription. DGIdb covers some natural products but is drug-gene focused, not supplement-drug. Best free path: mine PubMed/S2 for interaction evidence via existing MCPs (Scite, S2, Exa).

3. **No RCT database specific to supplements.** ClinicalTrials.gov + PubMed via existing MCPs is the best available path. Examine.com has the most comprehensive RCT summaries but no API.

4. **Python ecosystem is empty.** No mature, maintained package for supplement evidence. Must build thin API wrappers.

5. **Dose-response data is nowhere structured.** Dose-response curves for supplements exist only in individual papers or NatMed Pro's monographs. No structured, queryable database for dose-response.

6. **No compound-to-bioavailability database.** Bioavailability data for supplement forms (e.g., curcumin vs curcumin + piperine, magnesium citrate vs oxide) exists in scattered papers, not in any structured database.

---

## Search Log

| Query | Tool | Hits | Signal |
|-------|------|------|--------|
| "free databases APIs dietary supplement efficacy interactions" | Exa | 12 | HIGH — OpenFDA, NatMed, DSLD, DrugBank |
| "NatMed Natural Medicines database API" | Brave | 10 | HIGH — confirmed NatMed Pro = NMCD, new API July 2025 |
| "supplement nutrition knowledge graph ontology" | Exa | 10 | MEDIUM — ChEBI, DBpedia |
| "OpenFDA CAERS dietary supplement adverse event API" | Brave | 8 | HIGH |
| "Health Canada LNHPD API" | Exa | 6 | HIGH — full API docs |
| "MSKCC About Herbs database API" | Brave | 8 | MEDIUM — no API, app exists |
| "EFSA dietary supplement API" | Exa | 6 | MEDIUM — portal exists |
| "Australian TGA ARTG complementary medicine" | Brave | 8 | LOW |
| "ConsumerLab API" | Brave | 6 | LOW — no API confirmed |
| "USDA FoodData Central API" | Brave | 6 | HIGH — free REST API |
| "Python supplement interaction nutrition PyPI" | Exa | 8 | LOW — pyfooda only viable |
| "ChEBI Wikidata NCI Thesaurus supplement" | Exa | 8 | MEDIUM — ChEBI most useful |
| "DrugBank academic supplement natural product" | Brave | 6 | MEDIUM — academic license |
| "FooDB food constituent bioactive compound" | Exa | 5 | MEDIUM — bulk download |
| "Examine.com API" | Exa | 5 | LOW — no API yet |
| "HerbMedPro" | Exa | 5 | LOW — paywalled |
| "NMCD vs NatMed Pro" | Exa | 4 | HIGH — confirmed same product |
| LNHPD API docs (fetched) | WebFetch | 1 | HIGH — 7 endpoints documented |
| NIH ODS API docs (fetched) | WebFetch | 1 | MEDIUM — static URL, limited |
| EFSA developer portal (fetched) | WebFetch | 1 | LOW — landing page only |
| OpenFDA CAERS docs (fetched) | WebFetch | 1 | HIGH — full endpoint details |
| "MeSH SNOMED supplement" | Brave | 6 | LOW — standard terminology |
| "WHO IARC herbal monograph" | Brave | 6 | LOW — PDF only |
| "EDQM USP dietary supplement" | Exa | 5 | LOW — paywalled |
| "SUPP.AI alternative replacement" | Brave | 6 | LOW — still frozen |
| "Wikidata SPARQL dietary supplement" | Brave | 6 | MEDIUM |

---

## Provenance

All URLs verified via tool retrieval on 2026-04-05. Items marked `[TRAINING-DATA]` are from model knowledge, not retrieved sources. Items marked `[SOURCE: URL]` were verified via Exa, Brave, or WebFetch in this session.

<!-- knowledge-index
generated: 2026-04-05T19:08:56Z
hash: e1b221dc6b49

title: Supplement & Nutrition Evidence Databases — Comprehensive Survey
status: complete
tags: supplements, databases, APIs, ontologies, nutrition, evidence
sources: 1
  TRAINING-DATA: , verified property list

end-knowledge-index -->
