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
    # ---- lane A epoch 2 ----
    ("A38.2 Dept of Commerce v. New York slip opinion 18-966 (PDF)",
     "https://www.supremecourt.gov/opinions/18pdf/18-966_bq7c.pdf",
     ["seems to have been contrived", "Accepting contrived reasons would defeat the purpose"], [], True),
    ("A34.6 NVSS Vital Statistics Reporting Guidance No. 3, April 2020 (Wayback PDF)",
     "https://web.archive.org/web/20200417id_/https://www.cdc.gov/nchs/data/nvss/vsrg/vsrg03-508.pdf",
     ["Part II and not in Part I", "probable", "presumed", "only those conditions that actually contributed to death"], [], True),
    ("A34.6 Colorado CDPHE case-data page, archived 2020-06-11 (Wayback)",
     "https://web.archive.org/web/20200611170512id_/https://covid19.colorado.gov/data/case-data",
     ["Beginning May 15", "should not be added together", "deaths among people who died from COVID-19"], [], False),
    ("A38.3 European Parliament briefing IPOL_BRI(2017)614481 quoting Eurostat (PDF)",
     "https://web.archive.org/web/2019id_/https://www.europarl.europa.eu/RegData/etudes/BRIE/2017/614481/IPOL_BRI(2017)614481_EN.pdf",  # live host answers scripted fetches with an empty 202
     ["refutes allegations that the deficit of 2009 was over-estimated", "without any reservation"], [], True),
    ("A34.1 White House Maternal Health Blueprint, June 2022 (PDF)",
     "https://bidenwhitehouse.archives.gov/wp-content/uploads/2022/06/Maternal-Health-Blueprint.pdf",
     ["maternal health crisis", "more than double the rate of peer countries"], [], True),
    ("A34.1 NCHS Health E-Stat maternal mortality 2022 (Wayback)",
     "https://web.archive.org/web/2024id_/https://www.cdc.gov/nchs/data/hestat/maternal-mortality/2022/maternal-mortality-rates-2022.htm",
     ["22.3", "32.9", "fluctuate from year to year"], [], False),
    ("A34.4 CDC dataset 54ys-qyzm metadata — partially vaccinated EXCLUDED (JSON)",
     "https://data.cdc.gov/api/views/54ys-qyzm.json",
     ["Excluded were partially vaccinated people", "and partially vaccinated people from the 2019"], [], False),
    ("A34.4 Utah DHHS dashboard technical notes (Wayback)",
     "https://web.archive.org/web/20211215id_/https://coronavirus-dashboard.utah.gov/risk.html",  # dashboard retired; live 404
     ["Unvaccinated Case", "one dose", "14 days have not passed"], [], False),
    ("A36.1 BLS preliminary benchmark announcement 2024-08-21 (Wayback)",
     "https://web.archive.org/web/2024id_/https://www.bls.gov/web/empsit/cesprelbmk.htm",
     ["818,000"], [], False),
    # ---- lane B epoch 2 ----
    ("B40.D Lancet Calisher statement 2020-02-19 (EuropePMC)", EPMC.format("PMC7159294"),
     ["strongly condemn conspiracy theories", "We declare no competing interests"], [], False),
    ("B40.D Lancet competing-interests addendum 2021-06-21 (EuropePMC)", EPMC.format("PMC8215723"),
     ["invited the 27 authors", "recombinant bat coronaviruses"], [], False),
    ("B40.E Proximal Origin, Nat Med 2020 (EuropePMC)", EPMC.format("PMC7095063"),
     ["not a laboratory construct or a purposefully manipulated virus", "we do not believe that any type of laboratory-based scenario is plausible"], [], False),
    ("B40.E House Select Subcommittee interim report 2023-07-11 (PDF)",
     "https://oversight.house.gov/wp-content/uploads/2023/07/Final-Report-6.pdf",
     ["we cannot possibly distinguish between natural evolution and escape", "I totally agree that that"], [], True),
    ("B40.E Andersen sworn testimony 2023-07 (PDF)",
     "https://oversight.house.gov/wp-content/uploads/2023/07/Testimony-of-Dr.-Kristian-Andersen.pdf",
     ["until mid/end February", "during revision of the paper"], [], True),
    ("B44.B Cass Review final report April 2024 (Wayback PDF)",
     "https://web.archive.org/web/2024id_/https://cass.independent-review.uk/wp-content/uploads/2024/04/CassReview_Final.pdf",
     ["remarkably weak evidence", "25 moderate quality studies and 24 low quality studies", "overstates the strength of the evidence"], [], True),
    ("B43.B Trump–Woodward transcript 2020-03-19 (rev.com)",
     "https://www.rev.com/transcripts/donald-trump-bob-woodward-conversation-transcript-trump-playing-down-coronavirus",
     ["I wanted to always play it down", "more deadly than even your strenuous flus"], [], False),
    ("B45.B CRS RS22458 on the Tiahrt amendment (everycrsreport mirror)",
     "https://www.everycrsreport.com/reports/RS22458.html",
     ["ATF has not disclosed trace data", "bona fide"], [], False),  # CRS renders it as a quoted 'bona fide' criminal investigation
    # ---- lanes C + D epoch 2 ----
    ("C41.2 Imperial Report 9, 2020-03-16 (PDF)",
     "https://www.imperial.ac.uk/media/imperial-college/medicine/sph/ide/gida-fellowships/Imperial-College-COVID19-NPI-modelling-16-03-2020.pdf",
     ["(unlikely) absence of any control measures", "510,000 deaths in GB and 2.2 million in the US"], [], True),
    ("C41.3 IHME update 2020-04-05 (PDF)",
     "https://www.healthdata.org/sites/default/files/files/Projects/COVID/Estimation_update_040520_0.pdf",
     ["93,531", "81,766"], [], True),
    ("C41.4 Flaxman et al., Nature 2020 (nature.com)",
     "https://www.nature.com/articles/s41586-020-2405-7",
     ["million deaths have been averted", "the last intervention introduced"], [], False),
    ("C41.4 Soltesz et al., Nature Matters Arising 2020 (nature.com)",
     "https://www.nature.com/articles/s41586-020-3025-y",
     ["71%", "less than 2%", "cannot be reliably quantified"], [], False),
    ("C03.1 Fryer, NBER w22399 (PDF)",
     "https://www.nber.org/system/files/working_papers/w22399/w22399.pdf",
     ["no racial differences in either the raw data", "conditional on an interaction"], [], True),
    ("C03.1 Edwards, Lee & Esposito, PNAS 2019 abstract (EuropePMC core record; full text not OA there)",
     "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%2210.1073/pnas.1821204116%22&resultType=core&format=json",
     ["over the life course", "1,000"], [], False),
    ("C01.1 Oxfam methodology note 2017-01-16 (PDF, CDN)",
     "https://www-cdn.oxfam.org/s3fs-public/file_attachments/tb-economy-99-percent-methodology-160117-en.pdf",
     ["WHAT ABOUT THE DEBT", "0.4% of overall global wealth"], [], True),
    ("C01.1 Oxfam press release 2017-01-16",
     "https://www.oxfam.org/en/press-releases/just-8-men-own-same-wealth-half-world",
     ["nine billionaires owned the same wealth as the poorest half", "not 62"], [], False),
    ("C46.4 ADL Audit of Antisemitic Incidents 2023",
     "https://www.adl.org/resources/report/audit-antisemitic-incidents-2023",
     ["8,873", "7,523", "5,711", "1,350 of these incidents"], [], False),
    ("D49.B House Oversight minority staff report on AFT/CDC, 2022-03-30 (PDF)",
     "https://oversight.house.gov/wp-content/uploads/2022/03/AFT-CDC-Interference-Interim-Report-3-30-2022.pdf",
     ["almost word for word", "should provide reassignment, remote work, or other options for staff who have documented high-risk conditions"], [], True),
    ("D49.C BSEE well-control rule, 83 FR 22128 (Federal Register raw text)",
     "https://www.federalregister.gov/documents/full_text/text/2018/05/11/2018-09305.txt",
     ["obligated to observe and protect that copyright", "sometimes for free and sometimes for a fee"], [], False),
    ("D50.B Meta, More Speech and Fewer Mistakes, 2025-01-07",
     "https://about.fb.com/news/2025/01/meta-more-speech-fewer-mistakes/",
     ["A program intended to inform too often became a tool to censor", "one to two out of every 10"], [], False),
    ("B44.C(a) NHS England clinical policy 1927 on PSH, 12 Mar 2024 - names NICE (2020), cites no York review",
     "https://www.england.nhs.uk/wp-content/uploads/2024/03/clinical-commissioning-policy-gender-affirming-hormones-v2.pdf",
     ["not enough evidence to support the safety or clinical effectiveness of PSH", "Nine observational studies", "NICE (2020)"],
     ["University of York"], True),
    ("B44.C(b) Commons statement 'Cass Review', 15 Apr 2024 (TheyWorkForYou mirror)",
     "https://www.theyworkforyou.com/debates/?id=2024-04-15e.55.0",
     ["fashionable cultural values have overtaken evidence", "Around 100 studies have not been included", "This is superb evidence"],
     [], False),
    ("B44.C(c) WPATH and USPATH comment on the Cass Review, 17 May 2024 - no EPATH",
     "https://wpath.org/wp-content/uploads/2024/11/17.05.24-Response-Cass-Review-FINAL-with-ed-note.pdf",
     ["WPATH AND USPATH", "selective and inconsistent use of evidence", "helpful and often life-saving"], ["EPATH"], True),
    ("B44.C(d) AAP News 4 Aug 2023, reaffirm-then-review (Wayback of the AAP page)",
     "https://web.archive.org/web/2024id_/https://publications.aap.org/aapnews/news/25340/AAP-reaffirms-gender-affirming-care-policy",
     ["reaffirm the 2018 AAP policy statement on gender-affirming care", "more than 20 states", "reaffirmed the current guidance"],
     [], False),
    ("B44.C(e) Yale Integrity Project critique of the Cass Review, 2024",
     "https://law.yale.edu/sites/default/files/documents/integrity-project_cass-response.pdf",
     ["never evaluates the evidence using the GRADE framework", "Mixed Methods Appraisal Tool", "Newcastle-Ottawa"], [], True),
    ("B44.C(f) Cass, BMJ 2024;385:q814 (Wayback)",
     "https://web.archive.org/web/2024id_/https://www.bmj.com/content/385/bmj.q814",
     ["findings of the series of systematic reviews are disappointing", "The clearest indication is in helping a small number"],
     [], False),
    ("B44.C(f) BBC News 20 Apr 2024 - Cass on the 98% claim",
     "https://www.bbc.co.uk/news/health-68863594",
     ["completely incorrect", "nearly 60% of the studies"], [], False),
    ("B45.C PHMPT v. FDA ECF 29, FDA brief 13 Dec 2021 - 500-page floor, no '75 years'",
     "https://storage.courtlistener.com/recap/gov.uscourts.txnd.353278/gov.uscourts.txnd.353278.29.0.pdf",
     ["500 pages per month", "a floor, not a ceiling", "nine-year", "decade-long"], ["75 years", "75-year"], True),
    ("B45.C PHMPT v. FDA ECF 35, order 6 Jan 2022 - 55,000 pages per 30 days, no '75 years'",
     "https://storage.courtlistener.com/recap/gov.uscourts.txnd.353278/gov.uscourts.txnd.353278.35.0.pdf",
     ["more than 12,000 pages", "55,000 pages every 30 days", "paramount public importance"], ["75 years", "75-year"], True),
    ("B45.D Bloom 2021 MBE msab246 - SRA deletion, cloud recovery (EuropePMC full text)",
     "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC8436388/fullTextXML",
     ["Sequence Read Archive. I recover the deleted files from the Google Cloud", "SRR11313485", "This strategy was successful"],
     ["request of the submitting"], False),
    ("B44.B York hormones review abstract, Arch Dis Child 2024, PMID 38594053 - 1 high / 33 moderate / 19 low",
     "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:38594053%20AND%20SRC:MED&resultType=core&format=json",
     ['were included (n=53)', 'One cohort study was high-quality', 'moderate (n=33) and low-quality (n=19)'], [], False),
    ("B44.B York puberty-suppression review abstract, Arch Dis Child 2024, PMID 38594047 - 1 high / 25 moderate / 24 low",
     "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:38594047%20AND%20SRC:MED&resultType=core&format=json",
     ['were included (n=50)', 'One cross-sectional study was high quality, 25 studies were moderate quality', 'Only moderate-quality and high-quality studies were synthesised'], [], False),
]


def fetch(url: str, is_pdf: bool) -> tuple[str, int]:
    # 900s cap: the archived Cass Review PDF is 36 MB and Wayback served it at ~150 KB/s on 2026-09-16 (~4 min),
    # which a 300s cap turned into an empty body. curl's rc is returned so a timeout (rc 28) is named, not len=0.
    proc = subprocess.run(["curl", "-s", "--compressed", "-L", "-A", "Mozilla/5.0", "--max-time", "900", url],
                          capture_output=True)
    raw = proc.stdout
    if is_pdf:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(raw)
        text = subprocess.run(["pdftotext", f.name, "-"], capture_output=True, text=True).stdout
    else:
        text = html.unescape(re.sub(r"<[^>]+>", " ", raw.decode("utf-8", "replace")))
    return re.sub(r"\s+", " ", text), proc.returncode  # collapse whitespace: PDFs wrap phrases across lines


def main() -> int:
    failures = 0
    for label, url, present, absent, is_pdf in ANCHORS:
        try:
            t, rc = fetch(url, is_pdf)
        except Exception as e:  # noqa: BLE001
            print(f"✗ {label}: fetch error {e}"); failures += 1; continue
        missing = [s for s in present if s not in t]
        leaked = [s for s in absent if s in t]
        ok = not missing and not leaked and len(t) > 500
        failures += 0 if ok else 1
        mark = "✔" if ok else "✗"
        detail = "" if ok else f"  missing={missing} present-but-should-be-absent={leaked} len={len(t)} curl_rc={rc}"
        print(f"{mark} {label}{detail}")
    print(f"\n{len(ANCHORS) - failures}/{len(ANCHORS)} anchors verified")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
