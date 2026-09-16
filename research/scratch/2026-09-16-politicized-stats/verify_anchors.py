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
]


def fetch(url: str, is_pdf: bool) -> str:
    raw = subprocess.run(["curl", "-s", "--compressed", "-L", "-A", "Mozilla/5.0", "--max-time", "60", url],
                         capture_output=True).stdout
    if is_pdf:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(raw)
        return subprocess.run(["pdftotext", f.name, "-"], capture_output=True, text=True).stdout
    text = raw.decode("utf-8", "replace")
    return html.unescape(re.sub(r"<[^>]+>", " ", text))


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
