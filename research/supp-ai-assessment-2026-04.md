## SUPP.AI (Allen AI) — Assessment

**Question:** Status, methodology, API, evidence grading  
**Tier:** Quick | **Date:** 2026-04-05

### Status

Live at https://supp.ai but **abandoned**. Last data update: 2021-10-20 (4.5 years ago). No updates since. The site still serves queries against its frozen dataset. Coverage: 2,044 supplements, 2,866 drugs, 59,096 interactions.

### Methodology

**Paper:** Wang, Tafjord, Cohan (ACL 2020 Demos, DOI: 10.18653/v1/2020.acl-demos.41). [SOURCE: scite]

- **Extraction:** RoBERTa fine-tuned on DDI (drug-drug interaction) labeled data, then transfer-learned to supplement-drug interactions (SDIs). Processes full sentences, not just abstracts.
- **Corpus:** 22M articles (via Semantic Scholar). Extracted 195K evidence sentences for 60K interactions.
- **Performance:** P=0.82, R=0.58, F1=0.68. ~18% false positive rate at the sentence level. Recall is the weak point — misses 42% of interactions.
- **No evidence grading.** Reports raw associations with paper counts and confidence scores per extracted sentence. No strength-of-evidence classification (no RCT vs case report distinction, no effect size, no directionality).

### API

Base: `https://supp.ai/api/`. Four endpoints:

| Endpoint | Method | Returns |
|----------|--------|---------|
| `/api/agent/search?q=X&p=N` | GET | Paginated agent search (10/page) |
| `/api/agent/<CUI>` | GET | Agent metadata (name, synonyms, tradenames, type) |
| `/api/agent/<CUI>/interactions?p=N` | GET | Interactions list (50/page) with paper counts |
| `/api/interaction/<IID>` | GET | Evidence sentences with confidence scores, paper metadata |

Response includes: CUI identifiers, paper DOIs/PMIDs, study type tags, retraction flags, per-sentence confidence scores, entity spans. Bulk download: `https://storage.googleapis.com/uw-supp-ai-data/20211020_01.tar.gz`.

### Verdict

Useful as a **bulk starting dataset** (the 195K extracted sentences with confidence scores). Not useful as a live data source — frozen since Oct 2021, misses 4+ years of literature. The RoBERTa extraction model (P=0.82) is reasonable but outdated. No evidence grading means every mention of "ginkgo + warfarin" from a case report weighs the same as an RCT finding.

For current supplement-drug interaction data, NHP-MedLINE, DrugBank, or running your own extraction pipeline on recent PubMed would be more complete.

<!-- knowledge-index
generated: 2026-04-05T15:51:59Z
hash: d3476ca36422


end-knowledge-index -->
