## NIH DSLD & ODS APIs — Technical Assessment

**Question:** Current status, API structure, data currency, evidence grading
**Tier:** Quick | **Date:** 2026-04-05

### 1. DSLD (Dietary Supplement Label Database)

**Status:** Live at `https://dsld.od.nih.gov/` — confirmed operational via API probe.

**API:** REST/JSON, no auth, CC0 license. Base: `https://api.ods.od.nih.gov/dsld/`
- Version: **9.4.0** (January 2026 timestamp)
- Elasticsearch index: `dsldnxt_labels-2025-09-25f` (data current to Sep 2025)
- ~214K labels (189K as of July 2024 per ScienceDirect; 77,594 matched "vitamin d" alone)

**Key endpoints (all GET, `/v9/` prefix):**

| Endpoint | Purpose | Key params |
|----------|---------|------------|
| `/search-filter` | Full-text search with faceted filters | `q`, `status`, `date_start/end`, `product_type`, `ingredient_name`, `ingredient_category`, `brand`, `target_group`, `supplement_form`, `claim_type`, `sort_by`, `sort_order` |
| `/label/{id}` | Single label by DSLD ID | `id` (path) |
| `/brand-products` | Products by brand | `q`, `from`, `size` |
| `/browse-brands` | Browse brands alphabetically/keyword | `method`, `q` |
| `/browse-products` | Browse products alphabetically/keyword | `method`, `q` |
| `/ingredient-groups` | Browse ingredient groups | `term`, `method` |
| `/search-filter-histogram` | Label count distribution over time | Same as search-filter |
| `/version` | API version + index metadata | none |

Pagination: `from` (offset) + `size` (default 1000, lower recommended).

**Data per label:** brand, product name, entry date, market status (on/off), physical form, target groups, all ingredients (grouped by category: vitamin/mineral/botanical/amino_acid/other), DV percentages, health claims, warning statements, label images.

**Evidence grading:** None. This is pure label data — what manufacturers print on packages. No efficacy evidence, no quality assessment.

### 2. ODS Fact Sheet API

**Status:** Live at `https://ods.od.nih.gov/api/`

**API:** Single endpoint, XML or HTML output, no auth.
- `GET /?resourcename={name}&readinglevel={level}&outputformat={format}`
- `readinglevel`: `Consumer`, `Health Professional`, `Datos en español`
- `outputformat`: `XML` (structured per `factsheet.xsd`), `HTML` (embeddable)
- One fact sheet per request. No bulk/list endpoint exists.

**Data:** Full fact sheet content including RDAs, ULs, food sources, health effects, interactions. The Health Professional versions include references to primary literature. Vitamin D fact sheet reviewed **2025-06-27** (confirmed from XML `<Reviewed>` field).

**Evidence grading:** Implicit only. Fact sheets cite primary studies and systematic reviews within narrative text, but there's no structured evidence grade field (no GRADE, no confidence scores). The text does distinguish between "sufficient evidence" and "insufficient evidence" narratively.

**Limitations:** Only ~40 fact sheets exist (individual nutrients + a few topics like "exercise performance," "immune function," "weight loss"). No programmatic listing of available resources — you need to know the `resourcename` values.

### 3. Other ODS Databases

| Database | Description | API? |
|----------|-------------|------|
| **DSID** (Ingredient Database) | Estimated actual ingredient levels vs. label claims | Web UI only at dsid.od.nih.gov, no documented API |
| **CARDS** | Federally funded supplement research projects | Web search only |

### Summary

| Property | DSLD | ODS Fact Sheets |
|----------|------|-----------------|
| Live? | Yes | Yes |
| Format | REST JSON | XML/HTML |
| Auth | None | None |
| License | CC0 | Not stated (US gov = public domain) |
| Data currency | Index: Sep 2025 | Per-sheet; Vit D reviewed Jun 2025 |
| Evidence grading | No (label data only) | Narrative only, not structured |
| Bulk access | Via pagination (size up to 1000) | One sheet at a time |
| Products/sheets | ~214K+ labels | ~40 fact sheets |

**Bottom line:** DSLD is the useful one for programmatic work — well-structured JSON API, CC0, no auth, 200K+ products with ingredient-level data. ODS fact sheets are authoritative for RDAs and health evidence but the API is primitive (single-resource, no search, no structured evidence grades). Neither provides evidence grading in a machine-readable format.

### Sources
- [SOURCE: https://api.ods.od.nih.gov/dsld/v9/] — API docs + live probe (version 9.4.0, index 2025-09-25)
- [SOURCE: https://api.ods.od.nih.gov/dsld/version] — Version endpoint (Jan 2026 timestamp)
- [SOURCE: https://ods.od.nih.gov/api/] — ODS fact sheet API page
- [SOURCE: https://ods.od.nih.gov/api/?resourcename=VitaminD&readinglevel=Health%20Professional&outputformat=XML] — Live probe (reviewed 2025-06-27)
- [SOURCE: https://ods.od.nih.gov/Research/databases.aspx] — ODS databases listing
- [SOURCE: https://www.sciencedirect.com/science/article/abs/pii/S0022316625000884] — 189K labels as of July 2024

<!-- knowledge-index
generated: 2026-04-05T15:53:06Z
hash: 984cca3ae918


end-knowledge-index -->
