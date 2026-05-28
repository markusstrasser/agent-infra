#!/usr/bin/env python3
"""Hand-author `mixed` and `not_verifiable` cases — the two classes public
fact-check datasets cannot supply (the import left them at 1 each).

mixed: claims where the peer-reviewed literature genuinely runs both directions.
not_verifiable: claims with the SHAPE of a fact but no falsifiable content
(value judgments, normative 'should', underspecified/speculative).

No fabricated identifiers: `mixed` sources name landmark literature by
author/year/journal (which the author is confident of) but omit DOI fields
rather than invent them. Verdict-accuracy scoring (the ranking metric) does
not need DOIs; groundedness scoring on these cases is best-effort.

Run: cd ~/Projects/agent-infra/claim_bench && uv run python3 scripts/author_thin_class_cases.py --write
"""
import json, sys
from pathlib import Path
OUT = Path(__file__).resolve().parent.parent / "cases"
WRITE = "--write" in sys.argv

MIXED = [
    {
        "task_id": "auth_mixed_saturated_fat_cvd",
        "claim_text": "Reducing dietary saturated fat intake lowers cardiovascular disease risk in the general adult population.",
        "domain": "nutrition_epidemiology", "claim_type": "causal",
        "gold_sources": [
            {"citation": "Hooper L, et al. Reduction in saturated fat intake for cardiovascular disease. Cochrane Database Syst Rev (2020).",
             "supports": "Cochrane review finds reducing saturated fat lowers combined cardiovascular events ~17%, strongest where replaced with polyunsaturated fat."},
            {"citation": "Sacks FM, et al. AHA Presidential Advisory: Dietary Fats and Cardiovascular Disease. Circulation (2017).",
             "supports": "AHA advisory concludes lowering saturated fat and replacing with unsaturated fat reduces CVD."}],
        "gold_contradict_sources": [
            {"citation": "Dehghan M, et al. (PURE study). Associations of fats and carbohydrate intake with cardiovascular disease and mortality. The Lancet (2017).",
             "contradicts": "Large multinational cohort finds higher saturated fat associated with LOWER mortality and no significant CVD harm — challenges the reduction claim."},
            {"citation": "Siri-Tarino PW, et al. Meta-analysis of prospective cohort studies of saturated fat and CVD. Am J Clin Nutr (2010).",
             "contradicts": "Meta-analysis finds no significant association between saturated fat intake and CHD/CVD risk."}],
        "distractor_sources": [{"note": "The replacement nutrient is the crux — benefit appears when saturated fat is replaced by polyunsaturated fat, not refined carbohydrate. A model citing only one framing will reach a one-sided verdict."}],
        "difficulty": "hard",
        "notes": "Genuinely mixed: RCT-reduction/Cochrane evidence supports the claim while large cohorts (PURE) and bias-corrected meta-analyses contradict the simple version. `supported` or `contradicted` alone both cherry-pick; `insufficient_evidence` is wrong (evidence is abundant, it disagrees)."},
    {
        "task_id": "auth_mixed_ssri_mild_depression",
        "claim_text": "SSRI antidepressants are clinically effective for mild-to-moderate depression beyond placebo.",
        "domain": "clinical_psychiatry", "claim_type": "causal",
        "gold_sources": [
            {"citation": "Cipriani A, et al. Comparative efficacy of 21 antidepressants: systematic review and network meta-analysis. The Lancet (2018).",
             "supports": "Network meta-analysis of 522 trials finds all studied antidepressants more efficacious than placebo for acute major depression."}],
        "gold_contradict_sources": [
            {"citation": "Kirsch I, et al. Initial severity and antidepressant benefits: meta-analysis of FDA data. PLoS Medicine (2008).",
             "contradicts": "Meta-analysis of FDA trial data finds drug-placebo difference below clinical-significance threshold except in very severe depression — i.e. little benefit for mild-to-moderate."},
            {"citation": "Jakobsen JC, et al. SSRIs versus placebo for major depressive disorder. BMC Psychiatry (2017).",
             "contradicts": "Concludes SSRI effects are small and of questionable clinical importance, with high risk of bias inflating estimates."}],
        "distractor_sources": [{"note": "Efficacy scales with baseline severity — the literature genuinely splits on the MILD end specifically. A model retrieving only Cipriani will say supported; only Kirsch, contradicted."}],
        "difficulty": "hard",
        "notes": "The severity gradient makes this mixed: efficacy is well-supported for severe depression but contested for the mild-to-moderate range the claim names. Both literatures are real and current."},
    {
        "task_id": "auth_mixed_mammography_40s",
        "claim_text": "Routine screening mammography for women aged 40-49 at average risk reduces breast-cancer mortality.",
        "domain": "clinical_epidemiology", "claim_type": "causal",
        "gold_sources": [
            {"citation": "Independent UK Panel on Breast Cancer Screening (Marmot review). The Lancet (2012).",
             "supports": "Concludes screening reduces breast-cancer mortality (~20% relative) across invited age ranges, accepting overdiagnosis as a cost."}],
        "gold_contradict_sources": [
            {"citation": "Gøtzsche PC, Jørgensen KJ. Screening for breast cancer with mammography. Cochrane Database Syst Rev (2013).",
             "contradicts": "Cochrane review questions the mortality benefit, emphasizing trial-quality issues and substantial overdiagnosis; benefit in the 40-49 group is least certain."},
            {"citation": "USPSTF breast cancer screening recommendation history (2009/2016).",
             "contradicts": "Graded the 40-49 benefit as small/uncertain and made routine screening in that band an individual decision rather than a blanket recommendation."}],
        "distractor_sources": [{"note": "The 40-49 band specifically is where guideline bodies disagree most; older bands have clearer benefit. Verdict hinges on the age qualifier."}],
        "difficulty": "hard",
        "notes": "Authoritative bodies reach opposite practical conclusions for this exact age band from largely the same trials — a textbook `mixed` evidence base, not insufficient evidence."},
    {
        "task_id": "auth_mixed_dietary_cholesterol",
        "claim_text": "Dietary cholesterol intake meaningfully raises serum LDL cholesterol and cardiovascular risk in the general population.",
        "domain": "nutrition_epidemiology", "claim_type": "causal",
        "gold_sources": [
            {"citation": "Berger S, et al. Dietary cholesterol and cardiovascular disease: a systematic review and meta-analysis. Am J Clin Nutr (2015).",
             "supports": "Finds dietary cholesterol raises serum total and LDL cholesterol, a causal step toward CVD risk."}],
        "gold_contradict_sources": [
            {"citation": "2015-2020 Dietary Guidelines Advisory Committee (USA).",
             "contradicts": "Removed the long-standing 300 mg/day dietary-cholesterol limit, concluding cholesterol is 'not a nutrient of concern for overconsumption' at the population level."},
            {"citation": "Soliman GA. Dietary cholesterol and the lack of evidence in CVD. Nutrients (2018).",
             "contradicts": "Reviews the weak/inconsistent link between dietary (vs serum) cholesterol and CVD outcomes."}],
        "distractor_sources": [{"note": "Serum-cholesterol response to dietary cholesterol varies (hyper- vs hypo-responders); population-level CVD outcome evidence is weaker than the LDL-mechanism evidence. The claim bundles both, so neither pure verdict fits."}],
        "difficulty": "hard",
        "notes": "Mechanistic LDL evidence supports the claim; population guideline bodies walked back the CVD link. Genuinely mixed and currently unsettled."},
]

NOT_VERIFIABLE = [
    {"task_id": "auth_nv_best_language", "claim_text": "Rust is the best programming language for building reliable systems software.",
     "domain": "software", "claim_type": "value_judgment",
     "notes": "'Best' is threshold-free and frame-dependent. Benchmarks of memory-safety or performance exist, but they do not adjudicate 'best' — that depends on the evaluator's weighting of safety vs. ecosystem vs. familiarity. Retrieving Rust adoption stats does not convert the claim to verifiable."},
    {"task_id": "auth_nv_most_important_organelle", "claim_text": "The mitochondrion is the most important organelle in the eukaryotic cell.",
     "domain": "cell_biology", "claim_type": "value_judgment",
     "notes": "Has the shape of a biology fact but 'most important' has no objective metric — importance depends on which cellular function you privilege. The nucleus, ribosome, or membrane could each be argued 'most important' under different framings. Not falsifiable."},
    {"task_id": "auth_nv_climate_policy_should", "claim_text": "Climate policy should prioritize near-term economic growth over rapid emissions reductions.",
     "domain": "policy", "claim_type": "normative",
     "notes": "A normative 'should' claim about value trade-offs. Empirical facts inform it but cannot settle it — the conclusion depends on discount rates and value weightings, not on evidence alone. Models should refuse the verdict shape, not retrieve economic studies and pick a side."},
    {"task_id": "auth_nv_agi_transform", "claim_text": "Artificial general intelligence will fundamentally transform human civilization within our lifetimes.",
     "domain": "technology", "claim_type": "speculative",
     "notes": "Underspecified and speculative: 'fundamentally transform', 'AGI', and 'our lifetimes' lack operational definitions, and the event is future/unrealized. No current body of evidence can support or refute it. Tempting to call `insufficient_evidence`, but the deeper issue is it is not (yet) a verifiable proposition at all."},
]

INSUFFICIENT = [
    {"task_id": "auth_ie_bookstore_delivery", "claim_text": "More than half of independent bookstores in Portugal offered same-day local delivery in 2023.",
     "domain": "retail", "claim_type": "statistical",
     "notes": "Verifiable in principle (a sector survey could settle it) but no such survey is published. A diligent search finds general e-commerce/bookstore articles but no figure on this specific population/metric/year. Correct verdict is insufficient_evidence — NOT not_verifiable (it's a concrete falsifiable proposition), and NOT contradicted (absence of evidence isn't refutation). Trap: a model may anchor on a tangential statistic and over-claim."},
    {"task_id": "auth_ie_firefighter_age_slovenia", "claim_text": "The average age of volunteer firefighters in Slovenia rose by more than three years between 2015 and 2022.",
     "domain": "demographics", "claim_type": "statistical",
     "notes": "Registry data could in principle establish this, but no public analysis reports the specific delta. Searching yields Slovenian firefighting-association pages without this longitudinal figure. insufficient_evidence; the trap is treating 'I found the association's website' as having found the answer."},
    {"task_id": "auth_ie_statin_timing_myalgia", "claim_text": "Patients who take their statin in the morning report less muscle pain than those who take it at night.",
     "domain": "clinical", "claim_type": "causal",
     "notes": "Falsifiable in principle (a timing RCT with myalgia as endpoint) but no trial has tested this specific comparison; chronotherapy studies of statins target LDL, not myalgia. Correct verdict insufficient_evidence. Trap: retrieving LDL-timing studies and reporting them as if they answer the muscle-pain claim."},
    {"task_id": "auth_ie_scrabble_twoletter", "claim_text": "Among competitive Scrabble players, those who memorize two-letter words before longer words reach higher tournament ratings.",
     "domain": "games", "claim_type": "causal",
     "notes": "A concrete, testable claim about a learning-order effect, but no study of competitive Scrabble pedagogy reports it. Anecdotal strategy guides recommend two-letter words but provide no rating-outcome evidence. insufficient_evidence — the strategy advice is not outcome evidence."},
]

def build(c, verdict):
    return {
        "task_id": c["task_id"], "claim_text": c["claim_text"], "domain": c["domain"],
        "claim_type": c["claim_type"],
        "verifiability": "not_verifiable" if verdict == "not_verifiable" else "verifiable",
        "gold_verdict": verdict,
        "gold_sources": c.get("gold_sources", []),
        "gold_contradict_sources": c.get("gold_contradict_sources", []),
        "distractor_sources": c.get("distractor_sources", []),
        "difficulty": c.get("difficulty", "medium"), "notes": c["notes"],
    }

cases = ([build(c, "mixed") for c in MIXED]
         + [build(c, "not_verifiable") for c in NOT_VERIFIABLE]
         + [build(c, "insufficient_evidence") for c in INSUFFICIENT])
from collections import Counter
print(f"authored {len(cases)}:", dict(Counter(c['gold_verdict'] for c in cases)))
if WRITE:
    for c in cases:
        (OUT / f"{c['task_id']}.json").write_text(json.dumps(c, indent=2, ensure_ascii=False))
    print(f"wrote {len(cases)} files to {OUT}")
else:
    print("(dry run — pass --write)")
