# Parent addendum — items the parent grounded directly (2026-09-16, after lane B epoch 3)

**Verdict:** Mechanism 45's Bloom limb is closed. NIH's stated reason for the SRA withdrawal is grounded at
grade A in NIH's own letter to a senator; the 2023 correction to Bloom 2021 is a one-clause wording fix that
does not touch the deletion account; and one claim this library carried — that Bloom's paper does not
attribute the deletion to a submitter request — is **wrong** and is corrected here. Written by the parent
session, not a lane agent, so the lane files stay single-writer.

## P-1. NIH's own explanation for the withdrawal — GROUNDED (A)

**Primary:** NIH (Larry Lohmann, Acting Associate Director for Legislative Policy and Analysis) to the
Honorable Roger Marshall, response to the senators' letter of 28 June 2021, dated **8 September 2021**,
`marshall.senate.gov/wp-content/uploads/2021-06-28-NIAID-COVID-Origins-Questions-on-Deleted-Data-response-2021-09-08.pdf`.
ROUTE NOTE: the live senate.gov host returns an Akamai **Access Denied** page to curl (580 bytes); the
Wayback `id_` capture serves the 101 KB PDF. Read in full 2026-09-16.

**The reason, verbatim:** "In March 2020, the SARS-CoV-2 sequences you mention in your letter were submitted
by a researcher at Wuhan University for public release status via SRA." … "In June 2020, NCBI received a
request to withdraw the sequences from the same researcher. **The reason given by the researcher was they
were depositing updated data in a different database and they wanted to prevent version confusion.**" … "**No
conditions were made on that request and no conditions were granted.**"

**What NIH says about its own process, verbatim:** "**While NIH considers the policies and guidelines of the
INSDC sound, NCBI has initiated an independent review of SRA processes and standard operating procedures to
determine whether the appropriate steps were taken to assess this withdrawal request.**" And on what removal
means: "**Withdrawal makes the data undiscoverable but does not erase it.** Per the INSDC guidelines, NCBI
retains withdrawn data for the scientific record and for disaster recovery."

**Scale, verbatim:** "In that time, **six institutions** requested withdrawal of SARS-CoV-2 submission packages
through NLM/NCBI services. This included the one requested by the researcher at Wuhan University and the rest
from researchers at institutions from other countries, predominantly the U.S."

**Direction:** the removed data served the lab-origin side, right-coded in US politics from 2021; the
explanation is the agency's own, given to Republican senators who had alleged concealment. The agency's answer
is procedural and concedes an internal review, which is the opposite of a stonewall; it does not adjudicate motive.

**NOT GROUNDED here:** a 2021 NIH FOIA release (documentcloud 21473774) is quoted elsewhere as saying **eight**
SARS-CoV-2 submission packages were withdrawn, against the letter's **six institutions**. Packages and
institutions are different units, so this may be no contradiction at all. The Wayback copy is a 22 MB scanned
PDF from which `pdftotext` extracts nothing, so neither figure is carried from that document. It needs OCR.

## P-2. [LEAD CORRECTION] Bloom's paper does attribute the deletion to a submitter request

This library recorded, from lane B epoch 3, that "the paper does not attribute the deletion to a submitter
request" because greps for "at the request," "request of the submitting" and "no longer available" returned
nothing. The paper says it in other words, at figure 6 and in the main text, verbatim: "**After I e-mailed the
NIH the original version of this manuscript, they sent me the e-mail requesting deletion of the data, which is
in fig. 6.** Despite the statement in the deletion-request e-mail that the sequences were being uploaded to
'another website' (fig. 6), I could find no evidence that they were actually uploaded to any other public
website". Figure 6's legend: "A redacted version of the e-mails from Wuhan University to the SRA staff
requesting deletion of the sequencing data. **This e-mail was provided to me by the NIH's NCBI Director Stephen
Sherry on June, 19 2021**, the day after I e-mailed the NIH an advance copy of this manuscript."

What the paper disputes is the sufficiency of the stated reason, verbatim: "**There is no obvious scientific
reason for the deletion**: the sequences are concordant with the samples described in Wang et al. (2020), there
are no corrections to the paper, the paper states human subjects approval was obtained, and the sequencing
shows no evidence of plasmid or sample-to-sample contamination."

**The instrument lesson, and it is the same one this library keeps finding:** a phrase grep that misses is not
an absence. Three greps produced a confident negative about a document whose full text, read, says the
opposite. The absent-check on this anchor has been removed from the probe so the false negative cannot be
re-derived from it.

## P-3. The 2023 correction to Bloom 2021 — GROUNDED (A), and it is not about the deletion

**Primary:** "Correction to: Recovery of Deleted Deep Sequencing Data Sheds More Light on the Early Wuhan
SARS-CoV-2 Epidemic," *Mol Biol Evol* 40(9):msad201, published 29 September 2023, doi 10.1093/molbev/msad201,
PMID 37772800, PMC10540883. Routes that failed: Europe PMC `fullTextXML` (404 — the correction is not OA
there), the OUP article page via Wayback (404). Route that worked: the PMC article page via Wayback `id_`;
NCBI eutils `efetch db=pmc` returns the metadata but not the body.

**The whole correction, verbatim:** "In the originally published version of this manuscript, one of the
references to prior literature is inaccurate. Specifically, the text reading '**are from two different clusters
of patients who traveled to Wuhan**' should be changed to read '**are from a cluster of patients who traveled to
Wuhan**'. **This correction does not impact the results of the paper.** This error has been corrected online."

**Disposition:** the memo's caution that this paper's numerical claims should not be cited before reading the
correction is now discharged. The correction touches one clause about patient clusters and states it does not
affect the results; it says nothing about the deletion, the recovery, or the 13 reconstructed sequences.
