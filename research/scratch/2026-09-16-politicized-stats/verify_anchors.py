#!/usr/bin/env python3
"""Re-verify the anchor numbers behind the politicized-statistics case library against their primary sources.

Each anchor: label, URL, expected substrings (after HTML tag-strip + entity unescape, or pdftotext for PDFs),
optional substrings that must be ABSENT. Exit 1 if any anchor fails. Network: curl --compressed; PDFs need pdftotext.
Live bls.gov / fbi.gov block plain curl, so those go through web.archive.org `id_` captures.
"""
import html, re, subprocess, sys, tempfile
from pathlib import Path

EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/{}/fullTextXML"
ANCHORS = [
    # (label, url, present, absent, is_pdf)
    ("A34.1 Joseph AJOG 2024 abstract (PubMed 38480029)",
     "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=38480029&rettype=abstract&retmode=text",
     ["144%", "9.65", "23.6 per", "10.2 in", "10.4 per", "87% of indirect", "46-fold"], [], False),
    ("A35.1 China NBS explanation 2024-01-17",
     "https://www.stats.gov.cn/sj/zxfb/202401/t20240117_1946641.html",
     ["不包括在校学生", "6200", "3400"], [], False),
    ("A35.2 NOAA NESDIS notice 2025-05-08",
     "https://www.nesdis.noaa.gov/about/documents-reports/notice-of-changes/2025-notice-of-changes/billion-dollar-weather-and-climate-disasters",
     ["Product will be retired", "no updates beyond calendar year 2024", "remain authoritative"], [], False),
    ("A36.3 FBI 2022 Crime in the Nation release 2023-10-16 (Wayback)",
     "https://web.archive.org/web/2024id_/https://www.fbi.gov/news/press-releases/fbi-releases-2022-crime-in-the-nation-statistics",
     ["decreased an estimated 1.7%", "6.1%", "93.5%", "13,293", "2,431"], [], False),
    ("A36.1 BLS CES benchmark page (Wayback)",
     "https://web.archive.org/web/2026id_/https://www.bls.gov/web/empsit/cesbmart.htm",
     ["898,000", "0.6 percent"], [], False),
    ("B40.1 Cook 2013 ERL abstract (Crossref)",
     "https://api.crossref.org/works/10.1088/1748-9326/8/2/024024",
     ["66.4%", "32.6%", "0.7%", "0.3%", "97.1%"], [], False),
    ("B40.2 Zhang NHB 2023 (nature.com)",
     "https://www.nature.com/articles/s41562-023-01537-5",
     ["−0.854", "14.2-percentage", "38.3%"], [], False),
    ("B45.1 Green & Hand, Econ Journal Watch 21(1) 2024 (PDF)",
     "https://econjwatch.org/File+download/1296/GreenHandMar2024.pdf",
     ["would not provide us", "54.0 percent", "51.2 percent", "p-value = 0.65"], [], True),
    ("C46.2 Booty 2019 Injury Epidemiology (EuropePMC)", EPMC.format("PMC6889601"),
     ["346", "Mother Jones only recorded 11", "ranged from 24", "to 5 (Mother Jones)"], [], False),
    ("C46.2 Bridges 2023 Lancet Reg Health Am (EuropePMC)", EPMC.format("PMC10192935"),
     ["3155", "57 to 2955", "Only 25 incidents", "0.008%"], [], False),
    ("C08.1 Polack NEJM 2020 (EuropePMC) — no ARR reported", EPMC.format("PMC7745181"),
     ["8 cases of Covid-19", "162 among placebo", "95% effective", "18,198", "18,325"], ["absolute risk"], False),
    ("C14.1 Auten & Splinter AEA P&P 2019 abstract (Crossref)",
     "https://api.crossref.org/works/10.1257/pandp.20191038",
     ["21.5", "16.7", "13.1"], [], False),
    ("C46.3 Texas v. Pennsylvania motion 2020-12-07 (PDF)",
     "https://www.supremecourt.gov/DocketPDF/22/22O155/162953/20201207234611533_TX-v-State-Motion-2020-12-07%20FINAL.pdf",
     ["one in a quadrillion", "to the fourth power", "Cicchetti"], [], True),
    ("C27.1 HM Treasury news release 2016-04-18",
     "https://www.gov.uk/government/news/hm-treasury-analysis-shows-leaving-eu-would-cost-british-households-4300-per-year",
     ["cost British households £4,300", "£1,800", "6.2%"], [], False),
    ("C41.1 Hausfather & Peters, Nature 2020-01-29 (Crossref)",
     "https://api.crossref.org/works/10.1038/d41586-020-00177-3",
     ["business as usual", "2020"], [], False),
    # ---- lane D (science as authority) ----
    ("D52.1 Pew 2024-11-14 trust in scientists (page)",
     "https://www.pewresearch.org/science/2024/11/14/public-trust-in-scientists-and-views-on-their-role-in-policymaking/",
     ["a great deal (26%) or a fair amount (51%)", "87%", "85% majority of Republicans", "66%", "40%"], [], False),
    ("D48.1 Nature Human Behaviour editorial 2022-08-18",
     "https://www.nature.com/articles/s41562-022-01443-2",
     ["Although academic freedom is fundamental, it is not unbounded", "regardless of whether a research project was reviewed and approved"], [], False),
    ("D48.2 Doctors for America v. OPM, memorandum opinion 2025-07-03 (PDF)",
     "https://litigationtracker.law.georgetown.edu/wp-content/uploads/2025/05/Doctors-for-America_2025.07.03_MEMORANDUM-OPINION.pdf",
     ["acting first and thinking later", "Executive Order 14168", "hundreds or even thousands"], [], True),
    ("D51.1 MAHA report live PDF — fabricated JAMA Pediatrics citation absent",
     "https://www.whitehouse.gov/wp-content/uploads/2025/05/WH-The-MAHA-Report-Assessment.pdf",
     ["Make America Healthy Again"], ["Changes in mental health and substance use among US adolescents", "Keyes"], True),
    ("D51.2 DOE Climate Working Group report July 2025 (PDF)",
     "https://www.energy.gov/sites/default/files/2025-07/DOE_Critical_Review_of_Impacts_of_GHG_Emissions_on_the_US_Climate_July_2025.pdf",
     ["I exerted no control over their conclusions", "no editorial oversight", "could not comprehensively review all topics"], [], True),
    ("D49.1 House Select Subcommittee Fauci staff memo 2024-05-31 (PDF)",
     "https://oversight.house.gov/wp-content/uploads/2024/05/FINAL_Fauci-Memo.pdf",
     ["sort of just appeared", "empiric decision"], [], True),
    ("D50.1 ASD Hamilton 68 methodology brief (PDF)",
     "https://securingdemocracy.org/wp-content/uploads/2018/06/ASD-Policy-Brief-Latest-edited.pdf",  # gmfus.org host returns 526
     ["600", "not all of the accounts are directly controlled by Russia", "98 percent"], [], True),
    ("D47.1 IRA supporting economists' letter 2022-08-02 (verbatim mirror; documentcloud 403s)",
     "https://gwagner.com/ira-letter",
     ["downward pressure on inflation", "will fight inflation"], [], False),
    ("D47.1 BLS CPI-U CUUR0000SA0 Aug 2022/2023/2024 (public API)",
     "https://api.bls.gov/publicAPI/v2/timeseries/data/CUUR0000SA0?startyear=2022&endyear=2024",
     ["296.171", "307.026", "314.796"], [], False),
]


def fetch(url: str, is_pdf: bool) -> str:
    raw = subprocess.run(["curl", "-s", "--compressed", "-L", "-A", "Mozilla/5.0", "--max-time", "60", url],
                         capture_output=True).stdout
    if is_pdf:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(raw)
        text = subprocess.run(["pdftotext", f.name, "-"], capture_output=True, text=True).stdout
    else:
        text = html.unescape(re.sub(r"<[^>]+>", " ", raw.decode("utf-8", "replace")))
    return re.sub(r"\s+", " ", text)  # PDFs wrap phrases across lines; compare on collapsed whitespace


def main() -> int:
    failures = 0
    for label, url, present, absent, is_pdf in ANCHORS:
        try:
            t = fetch(url, is_pdf)
        except Exception as e:  # noqa: BLE001
            print(f"✗ {label}: fetch error {e}"); failures += 1; continue
        missing = [s for s in present if s not in t]
        leaked = [s for s in absent if s in t]
        ok = not missing and not leaked and len(t) > 500
        failures += 0 if ok else 1
        mark = "✔" if ok else "✗"
        detail = "" if ok else f"  missing={missing} present-but-should-be-absent={leaked} len={len(t)}"
        print(f"{mark} {label}{detail}")
    print(f"\n{len(ANCHORS) - failures}/{len(ANCHORS)} anchors verified")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
