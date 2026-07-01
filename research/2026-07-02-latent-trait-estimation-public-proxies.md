# Estimating latent traits from public proxies — method + case study

**Date:** 2026-07-02
**Status:** method memo (session-derived)
**Case study:** IQ estimate of a startup founder from interview transcripts + public biography (operator-driven exercise; sequential corrections by the operator are the actual finding)
**Graduated to:** `skills/analyze/lenses/proxy-validity.md` (the reusable form)

## The task shape

Operator asks for a point estimate of an unobservable trait (here: IQ, ±5 requested)
from observable public evidence (speech transcripts, credentials, biography). The
same shape recurs for: founder quality, source credibility, model capability from
demos, employee skill from portfolios, company health from PR.

## Correction ledger (what actually improved the estimate)

Each row is an operator correction and what it generalized to. The final estimate
moved only ~2 points across five updates — the *CI honesty* and *proxy discounts*
were the real product, not the center.

| # | Correction | Update | Generalized rule |
|---|---|---|---|
| 0 | — (baseline: transcript read) | 125–130, CI ±12 | Requested precision (±5) ≠ deliverable precision (±10–12). State the instrument's resolving power BEFORE the estimate; deliver the honest CI alongside the requested band. |
| 1 | "do research, see if the prior shifts" | +1–2 center, CI tightens | Independent proxies that AGREE tighten the CI; they barely move the center. Two noisy measurements at the same value ≠ a higher value. |
| 2 | "her env growing up? parents?" | −1–2 center | Proxy validity is population-conditional: high SES inflates credential→ability inference (test prep, full-pay admissions, consulting). The environment finding explains HOW credentials were reachable — it is a discount on the proxy, not new trait evidence. |
| 3 | "women talk 3× more — verbal overindexed?" | −1 center | Verify the PREMISE of a proposed correction, then split direction from magnitude. "3× words/day" is debunked (Mehl et al., *Science* 2007: ~16k/day both sexes); the real fluency d≈0.2–0.45 justifies ~1–2 points, not 10. A correction can be directionally right and 10× overstated. |
| 4 | "assume affirmative action + looks biases" | ~−1 center | Apply a proposed bias-discount only where the base rates support it (beauty premium in client-facing careers: real; MBA holistics: modest) and REJECT it where the data run opposite (women get ~2% of VC dollars — a large female-led raise is a *stronger* signal under the bias hypothesis, not weaker). |
| 5 | third speech sample (adversarial register) | no update | Stopping rule: an Nth consistent sample of the same evidence KIND adds ≈ nothing. Name the evidence class that would actually discriminate (here: quant output, test scores, adversarial live reasoning) and stop researching. |

Also load-bearing: **absence-of-evidence as weak tail evidence** — no public quantitative
artifact caps the right tail (135+) more effectively than any positive verbal evidence
raises it.

## Method distilled (the lens)

1. State deliverable precision vs requested precision; refuse the false precision, deliver both.
2. Enumerate proxies; for each, ask *who was this proxy validated on, and what inflates it for THIS subject* (SES → credentials; sex → fluency; rehearsed domain → apparent fluidity; auto-captions → hidden disfluency).
3. Independent agreement → tighten CI, hold center.
4. Operator-proposed corrections: verify premise, split direction/magnitude, check base-rate direction.
5. Stop when the next sample is the same kind; name what would discriminate.

## Case study result (for completeness)

Subject: Taste Labs founder (UChicago econometrics BA, HBS 2+2 admit declined,
Exa founding team, $18.5M solo seed). Three speech samples (2024–2026, two friendly
one live-adversarial), consistent register. Final: **center ~125, band 123–128,
honest CI ~118–132**. Sources in session transcript 3bc20c79.

## Revisions

- 2026-07-02: initial.
