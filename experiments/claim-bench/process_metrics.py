"""Process-level scorers for claim-verification benchmark.

Phase 2 ships:
- currency_scorer        — deterministic Crossref + URL classifier + judge for residual.
                           Catches the case-004 failure mode where retrieval
                           surfaces a pre-retraction PDF that the model treats
                           as current state-of-record.
- calibration_scorer     — does the model's hedge language match its actual
                           accuracy? Verbalized confidence is unreliable per
                           the Nakkiran et al. semantic-calibration finding,
                           but it's the only signal available without multi-
                           epoch sampling. Calibration via consistency lives
                           in cards.py.
- trace_faithfulness_scorer — pure-deterministic. Citations the model puts in
                           its explanation must appear in the retrieval trace.
                           Detects fabricated citations.
- retrieval_attempted_scorer — top-level promotion of the existing
                           tool_calls_seen metadata per Phase 1 plan-close
                           finding #5.

The joint_success_per_sample helper is NOT a scorer — it's a derived value
computed in cards.py from the EvalLog. Inspect's Scorer API doesn't expose
peer scorer outputs in-band, and faking it via duplicated logic is worse
than computing it post-eval. The helper lives here so cards.py can import
the same canonical definition this module documents.

These scorers run alongside verdict_enum_scorer and groundedness_scorer in
task.py's scorer list. Each is independent and can be enabled/disabled
without affecting the others.
"""

from __future__ import annotations

import asyncio
import os
import re
from typing import Any

from inspect_ai.model import ChatMessageTool, ChatMessageUser, get_model
from inspect_ai.scorer import Score, Scorer, Target, mean, scorer
from inspect_ai.solver import TaskState

# Reuse Phase 1 helpers from scorer.py rather than duplicating them. This
# keeps the verdict-extraction surface in one place — if scorer.py grows a
# new format handler, calibration_scorer picks it up automatically.
from scorer import _extract_verdict, _normalize


# ─── DOI / URL extraction helpers ────────────────────────────────────────────

# DOI regex per Crossref's published guidance. The suffix can contain almost
# any printable character except whitespace; we trim trailing punctuation
# AND known URL fragments that the regex commonly over-matches when DOIs
# appear inside URL paths (e.g. "10.1007/foo/fulltext.html").
DOI_PATTERN = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
DOI_TRIM_CHARS = ".,;)]}>'\""

# URL path components that get appended to DOIs when the regex matches inside
# a URL. These are publisher-specific path fragments, not part of any real
# DOI suffix. Stripped after the main regex match. Order matters — strip
# longest first.
DOI_URL_FRAGMENT_PATTERN = re.compile(
    r"/(fulltext\.html?|fulltext|full\.pdf|full|abstract|pdf|epdf|html|toc|meta)$",
    re.IGNORECASE,
)

URL_PATTERN = re.compile(r"https?://[^\s\"<>)\]]+")

# Publisher URL → DOI patterns. Many publisher landing pages encode the DOI
# in the URL path; extracting it directly from the URL is more reliable than
# hoping Exa's text excerpt contains the literal DOI string. This catches the
# case-004 failure mode where the model retrieves a Nature paper page but
# the DOI string is past the 1500-char text excerpt cap.
PUBLISHER_URL_DOI_PATTERNS = [
    # Nature: nature.com/articles/s41586-024-07219-0 → 10.1038/s41586-024-07219-0
    (
        re.compile(r"nature\.com/articles/(s\d{5}[\w-]+)", re.IGNORECASE),
        "10.1038/{0}",
    ),
    # NEJM: nejm.org/doi/10.1056/NEJMoa1809944 → DOI literally in path
    (
        re.compile(r"nejm\.org/doi/(?:full/)?(10\.\d{4,9}/[\w.-]+)", re.IGNORECASE),
        "{0}",
    ),
    # Science: science.org/doi/10.1126/science.abc1234 → DOI literally in path
    (
        re.compile(
            r"science(?:mag)?\.org/doi/(?:full/)?(10\.\d{4,9}/[\w.-]+)", re.IGNORECASE
        ),
        "{0}",
    ),
    # Cell Press: cell.com/cell/fulltext/S0092-8674...  no DOI in URL — skip
    # JAMA: jamanetwork.com/journals/jama/fullarticle/2806681 — id, not DOI — skip
    # Generic doi.org/10.x/y resolver
    (
        re.compile(r"doi\.org/(10\.\d{4,9}/[\w./()-]+)", re.IGNORECASE),
        "{0}",
    ),
    # Lancet: thelancet.com/journals/lancet/article/PIIS0140-6736(...) → no DOI — skip
    # Oxford Academic: academic.oup.com/.../article/.../doi/10.1093/... — DOI in URL
    (
        re.compile(
            r"academic\.oup\.com/\S+?/(10\.\d{4,9}/[\w.-]+)", re.IGNORECASE
        ),
        "{0}",
    ),
]


def _extract_dois_from_text(text: str) -> set[str]:
    """Extract DOIs from arbitrary text. Lowercased, trimmed, URL-fragment-stripped.

    Two passes:
    1. Regex extraction for literal DOI strings (10.NNNN/...).
    2. Publisher URL → DOI extraction for known patterns (nature.com/articles/...
       etc.) — catches DOIs that were past the 1500-char text excerpt cap and
       only appear in the URL.

    URL path fragments like /fulltext.html, /pdf, /full are stripped from
    candidate DOIs after the regex match because they're URL-path artifacts,
    not real DOI suffix characters.
    """
    out: set[str] = set()
    if not text:
        return out

    # Pass 1: literal DOI regex
    for m in DOI_PATTERN.finditer(text):
        doi = m.group(0).rstrip(DOI_TRIM_CHARS).lower()
        # Strip publisher URL fragments that the greedy regex over-matched
        doi = DOI_URL_FRAGMENT_PATTERN.sub("", doi)
        if "/" in doi:
            out.add(doi)

    # Pass 2: publisher URL → DOI extraction
    for url_re, doi_template in PUBLISHER_URL_DOI_PATTERNS:
        for m in url_re.finditer(text):
            captured = m.group(1)
            doi = doi_template.format(captured).lower()
            doi = DOI_URL_FRAGMENT_PATTERN.sub("", doi)
            if "/" in doi:
                out.add(doi)

    return out


def _extract_urls_from_text(text: str) -> list[str]:
    """Extract HTTP(S) URLs from text. Returns list (preserving duplicates is fine)."""
    return [u.rstrip(DOI_TRIM_CHARS) for u in URL_PATTERN.findall(text or "")]


# ─── URL classifier (publisher vs mirror vs preprint) ────────────────────────

# Authoritative publisher domains. A URL on one of these is the source of
# record; an institutional mirror of the same paper is not. Suffix-matched.
PUBLISHER_DOMAINS = frozenset(
    {
        "nature.com",
        "science.org",
        "sciencemag.org",
        "cell.com",
        "nejm.org",
        "thelancet.com",
        "jamanetwork.com",
        "bmj.com",
        "annualreviews.org",
        "elifesciences.org",
        "plos.org",
        "pnas.org",
        "jbc.org",
        "embopress.org",
        "academic.oup.com",
        "wiley.com",
        "onlinelibrary.wiley.com",
        "tandfonline.com",
        "springer.com",
        "link.springer.com",
        "sciencedirect.com",
        "cambridge.org",
        "ahajournals.org",
        "annals.org",
        "neurology.org",
        "frontiersin.org",
        "mdpi.com",
        "iopscience.iop.org",
        "doi.org",
        "dx.doi.org",
    }
)

PREPRINT_DOMAINS = frozenset({"arxiv.org", "biorxiv.org", "medrxiv.org", "ssrn.com"})

# Heuristic patterns that suggest an institutional/personal mirror rather
# than the source of record.
INSTITUTIONAL_MIRROR_PATTERNS = (
    "/people/",
    "/faculty/",
    "/staff/",
    "/~",
    "/users/",
    "/researchers/",
)


def _classify_url(url: str) -> str:
    """Return one of: 'publisher', 'preprint', 'institutional_mirror', 'other'."""
    url_lower = (url or "").lower()
    if "//" not in url_lower:
        return "other"
    host = url_lower.split("//", 1)[1].split("/", 1)[0]
    if host.startswith("www."):
        host = host[4:]
    for pub in PUBLISHER_DOMAINS:
        if host == pub or host.endswith("." + pub):
            return "publisher"
    for pre in PREPRINT_DOMAINS:
        if host == pre or host.endswith("." + pre):
            return "preprint"
    for pat in INSTITUTIONAL_MIRROR_PATTERNS:
        if pat in url_lower:
            return "institutional_mirror"
    return "other"


# ─── Crossref lookup (deterministic part of currency_scorer) ─────────────────

CROSSREF_API_BASE = "https://api.crossref.org/works/"
CROSSREF_TIMEOUT_SEC = 5.0
CROSSREF_USER_AGENT = "claim-bench/0.2 (https://github.com/agent-infra; mailto:agent-infra@local)"

# Cap how many DOIs we look up per sample. 10 is generous — most cases cite
# 1-3 sources. Prevents a runaway model from blasting Crossref with 50 calls.
MAX_DOIS_PER_SAMPLE = 10


async def _crossref_lookup(doi: str) -> dict[str, Any] | None:
    """Query Crossref for a DOI's metadata.

    Returns the parsed `message` dict on success, or None on any failure
    (network, timeout, 404, parse error, missing httpx). The caller treats
    None as "currency unverified" — it does NOT crash the eval. The trade-
    off is silent under-detection on Crossref outages, which is acceptable
    for a Phase 2 dev signal.

    Crossref signals we care about (per Crossref's update mechanism):
    - `subtype == "retraction"` — the record IS a retraction notice
    - `update-to: [...]` — this paper has been corrected/replaced/retracted;
      each entry has a `label` field describing the update type
    - `relation.is-retracted-by` — alternative shape for retraction pointers
    """
    try:
        import httpx
    except ImportError:
        return None
    try:
        async with httpx.AsyncClient(timeout=CROSSREF_TIMEOUT_SEC) as client:
            response = await client.get(
                f"{CROSSREF_API_BASE}{doi}",
                headers={"User-Agent": CROSSREF_USER_AGENT},
            )
            if response.status_code != 200:
                return None
            data = response.json()
            return data.get("message", {})
    except Exception:
        return None


def _interpret_crossref_message(msg: dict[str, Any] | None) -> dict[str, Any]:
    """Extract currency-relevant flags from a Crossref message.

    Crossref's structured retraction signals are NOT consistently populated
    across publishers. Empirically (Phase 2 case 004 — Kotz et al. Nature
    2024 retraction):
    - `subtype` is None for the original paper (only the retraction notice
      itself has subtype="retraction")
    - `update-to` is null
    - `relation.is-retracted-by` does not exist
    - The ONLY signal is the title prefix: "RETRACTED ARTICLE: ..."

    Nature, Wiley, and most major publishers prepend "RETRACTED ARTICLE:",
    "Retracted:", or "WITHDRAWN:" to the title of retracted papers. This
    string convention is more reliable than any structured field, so we
    check it first. Then fall back to update-to / relation for publishers
    that DO populate the structured fields.

    Returns a dict that's always safe to read:
        is_retraction:    bool   — record IS itself a retraction notice
        has_update:       bool   — paper has correction/retraction/replacement
        update_labels:    list   — labels of updates (e.g. "Retraction")
        is_retracted:     bool   — paper has been retracted (any signal)
        is_corrected:     bool   — has_update AND any label mentions correction
        retraction_signal: str   — which signal fired ("title" / "subtype" /
                                   "update-to" / "relation" / "none")
    """
    if not msg:
        return {
            "is_retraction": False,
            "has_update": False,
            "update_labels": [],
            "is_retracted": False,
            "is_corrected": False,
            "retraction_signal": "none",
        }

    is_retraction = msg.get("subtype", "") == "retraction"

    # ─── Title-prefix check (most reliable cross-publisher signal) ───
    titles = msg.get("title") or []
    if isinstance(titles, str):
        titles = [titles]
    title_text = " ".join(t for t in titles if isinstance(t, str)).lower()
    # Markers that prefix the title of a RETRACTED paper. Distinct from
    # retraction NOTICES (those are announced via subtype="retraction" and
    # have titles like "Retraction Note: ..." — those records are not
    # themselves retracted, so we don't include "retraction note" /
    # "retraction:" here).
    RETRACTED_PAPER_TITLE_MARKERS = (
        "retracted article",
        "retracted:",
        "withdrawn:",
        "withdrawn article",
    )
    # Suppress title-prefix detection on records that ARE notices — a
    # notice's title may legitimately mention retraction without the
    # notice itself being retracted.
    if is_retraction:
        title_says_retracted = False
    else:
        title_says_retracted = any(
            marker in title_text for marker in RETRACTED_PAPER_TITLE_MARKERS
        )

    # ─── Structured update-to check ───
    update_to = msg.get("update-to") or []
    update_labels = [
        u.get("label", "") for u in update_to if isinstance(u, dict)
    ]
    has_update = bool(update_to)
    lower_labels = [lbl.lower() for lbl in update_labels]
    update_to_says_retracted = any("retract" in lbl for lbl in lower_labels)
    is_corrected = any(
        ("correction" in lbl or "erratum" in lbl) for lbl in lower_labels
    )

    # ─── Relation field check ───
    relation = msg.get("relation", {}) or {}
    relation_says_retracted = bool(
        isinstance(relation, dict) and relation.get("is-retracted-by")
    )

    is_retracted = (
        title_says_retracted or update_to_says_retracted or relation_says_retracted
    )

    if title_says_retracted:
        signal = "title"
    elif is_retraction:
        signal = "subtype"
    elif update_to_says_retracted:
        signal = "update-to"
    elif relation_says_retracted:
        signal = "relation"
    else:
        signal = "none"

    return {
        "is_retraction": is_retraction,
        "has_update": has_update,
        "update_labels": update_labels,
        "is_retracted": is_retracted,
        "is_corrected": is_corrected,
        "retraction_signal": signal,
    }


# ─── Currency scorer (deterministic + judge hybrid) ──────────────────────────

CURRENCY_JUDGE_MODEL = os.environ.get(
    "CLAIM_BENCH_CURRENCY_JUDGE_MODEL", "google/gemini-2.5-flash"
)

CURRENCY_JUDGE_PROMPT = """You are auditing whether an AI claim-verification system correctly handled a STALE source that appeared in its retrieval trace.

## The original claim
{claim}

## The AI's verdict
{predicted_verdict}

## The AI's full explanation
{explanation}

## Stale source flagged by Crossref
DOI: {doi}
Crossref status: {status}
Update labels: {labels}

## Your task

Did the AI's explanation correctly handle this stale source? Use this rubric:

- **aware (1.0)**: The AI explicitly mentioned the retraction / correction / supersession AND adjusted its verdict to reflect it. The AI did NOT present the stale source as the current state of record.
- **partial (0.5)**: The AI cited the source but did not address its stale status. The verdict may be defensible on other grounds, but the AI failed to surface the staleness — a real risk in a production setting.
- **unaware (0.0)**: The AI cited the stale source as if it were current, treated its findings as the current state of record, and did NOT surface the retraction or correction.

On the first line, output exactly one token: `aware`, `partial`, or `unaware`.
On the second line, write a one-sentence justification citing what the AI did or did not say about the staleness.
Do not output anything else."""


def _parse_currency_judge(raw: str) -> tuple[str, float]:
    """Parse the currency judge's output into (label, value).

    Same shape as _parse_groundedness_verdict — parse failures score 0.0,
    not 0.5, so silent off-format judge output doesn't inflate the mean.
    """
    if not raw:
        return "parse_error", 0.0
    first = raw.strip().split("\n", 1)[0].strip().lower()
    first = first.strip(".*_-`: ")
    if first == "aware":
        return "aware", 1.0
    if "partial" in first:
        return "partial", 0.5
    if "unaware" in first or "not aware" in first:
        return "unaware", 0.0
    return "parse_error", 0.0


def _trace_text(state: TaskState) -> str:
    """Concatenate all tool result content from state.messages into one string.

    Used by currency_scorer and trace_faithfulness_scorer to recover the
    raw retrieved text without re-walking state.messages each time.
    """
    parts: list[str] = []
    for msg in state.messages:
        if isinstance(msg, ChatMessageTool):
            content = msg.text if hasattr(msg, "text") else str(msg.content)
            parts.append(content)
    return "\n".join(parts)


@scorer(metrics=[mean()])
def currency_scorer() -> Scorer:
    """Hybrid deterministic + judge scorer for source currency.

    Phase 1 case 004 demonstrated that retrieval can launder retracted
    sources into confident verdicts when the model doesn't check for
    retraction notices. This scorer:

    1. Walks the retrieval trace and extracts DOIs (regex)
    2. Queries Crossref for each DOI (parallel, capped, timeout=5s)
    3. Interprets each response for retraction/correction/supersession flags
    4. If any source is stale, runs an LLM judge ONLY on the residual:
       given the staleness, did the model handle it correctly?
    5. Returns 1.0 if no stale sources OR all stale ones handled correctly,
       0.0 if a stale source was treated as current

    If no DOIs are extractable, returns 1.0 with answer='not_applicable'.
    Currency cannot be checked without a citation chain — that's not a
    failure of the scorer, it's a failure of the model to provide one,
    which retrieval_attempted_scorer + trace_faithfulness_scorer catch.

    Key design choice: the LLM judge only runs on the RESIDUAL after the
    deterministic check identifies stale sources. A pure LLM judge would
    have the same factor-collapse problem groundedness has. Crossref does
    the falsifiable part; the judge only handles "did the model address
    the staleness," which is a much narrower question.
    """

    async def score(state: TaskState, target: Target) -> Score:
        trace_text = _trace_text(state)
        dois = _extract_dois_from_text(trace_text)

        if not dois:
            return Score(
                value=1.0,
                answer="not_applicable",
                explanation="No DOIs in retrieval trace — currency not checkable",
                metadata={
                    "currency_status": "not_applicable",
                    "dois_checked": [],
                    "stale_dois": [],
                },
            )

        dois_to_check = sorted(dois)[:MAX_DOIS_PER_SAMPLE]
        crossref_results = await asyncio.gather(
            *[_crossref_lookup(doi) for doi in dois_to_check],
            return_exceptions=True,
        )

        stale_dois: list[tuple[str, dict[str, Any]]] = []
        crossref_failed = 0
        for doi, msg in zip(dois_to_check, crossref_results):
            # Positive isinstance check narrows the type for Pyright; the
            # gather(return_exceptions=True) result type is dict | BaseException
            # | None, all of which we want to skip if not dict.
            if not isinstance(msg, dict):
                crossref_failed += 1
                continue
            flags = _interpret_crossref_message(msg)
            if flags["is_retracted"] or flags["is_retraction"]:
                stale_dois.append((doi, flags))

        if not stale_dois:
            return Score(
                value=1.0,
                answer="all_current",
                explanation=(
                    f"Checked {len(dois_to_check)} DOIs via Crossref, "
                    f"{crossref_failed} unverified — none flagged as retracted"
                ),
                metadata={
                    "currency_status": "all_current",
                    "dois_checked": dois_to_check,
                    "stale_dois": [],
                    "crossref_failed_count": crossref_failed,
                },
            )

        # Judge runs only on the residual.
        raw_output = state.output.completion if state.output else ""
        claim_text = state.input_text or ""
        first_stale_doi, first_stale_flags = stale_dois[0]
        judge_prompt = CURRENCY_JUDGE_PROMPT.format(
            claim=claim_text[:600],
            predicted_verdict=raw_output.split("\n", 1)[0][:200],
            explanation=raw_output[:1500],
            doi=first_stale_doi,
            status=("retraction notice" if first_stale_flags["is_retraction"]
                    else "retracted"),
            labels=", ".join(first_stale_flags["update_labels"]) or "(none)",
        )
        judge = get_model(CURRENCY_JUDGE_MODEL)
        judge_result = await judge.generate([ChatMessageUser(content=judge_prompt)])
        judge_output = judge_result.completion or ""
        label, value = _parse_currency_judge(judge_output)

        return Score(
            value=value,
            answer=label,
            explanation=judge_output[:500],
            metadata={
                "currency_status": label,
                "dois_checked": dois_to_check,
                "stale_dois": [doi for doi, _ in stale_dois],
                "judge_model": CURRENCY_JUDGE_MODEL,
                "crossref_failed_count": crossref_failed,
            },
        )

    return score


# ─── Calibration scorer (verbalized hedge classifier) ────────────────────────

# Hedge phrases — signals of uncertainty in natural language.
HEDGE_PATTERNS = [
    re.compile(r"\binsufficient evidence\b", re.IGNORECASE),
    re.compile(r"\bcannot (find|verify|determine|confirm)\b", re.IGNORECASE),
    re.compile(r"\bnot enough (evidence|data|information)\b", re.IGNORECASE),
    re.compile(r"\bunclear\b", re.IGNORECASE),
    re.compile(r"\bambiguous\b", re.IGNORECASE),
    re.compile(r"\bdisputed\b", re.IGNORECASE),
    re.compile(r"\bcontested\b", re.IGNORECASE),
    re.compile(r"\buncertain\b", re.IGNORECASE),
    re.compile(r"\bcould not\b", re.IGNORECASE),
    re.compile(r"\bunable to\b", re.IGNORECASE),
    re.compile(r"\bunverified\b", re.IGNORECASE),
    re.compile(r"\bappears? to\b", re.IGNORECASE),
    re.compile(r"\bseems? to\b", re.IGNORECASE),
    re.compile(r"\bmay (be|have|not)\b", re.IGNORECASE),
    re.compile(r"\bmight (be|have|not)\b", re.IGNORECASE),
    re.compile(r"\bpossibly\b", re.IGNORECASE),
    re.compile(r"\bperhaps\b", re.IGNORECASE),
    re.compile(r"\btentative\b", re.IGNORECASE),
    re.compile(r"\bsuggestive\b", re.IGNORECASE),
]

# Confidence phrases — signals of certainty.
CONFIDENCE_PATTERNS = [
    re.compile(r"\bdefinitively\b", re.IGNORECASE),
    re.compile(r"\bclearly\b", re.IGNORECASE),
    re.compile(r"\bunequivocally\b", re.IGNORECASE),
    re.compile(r"\bcertain\b", re.IGNORECASE),
    re.compile(r"\bproven\b", re.IGNORECASE),
    re.compile(r"\bestablished\b", re.IGNORECASE),
    re.compile(r"\bconfirmed\b", re.IGNORECASE),
    re.compile(r"\bdemonstrated\b", re.IGNORECASE),
    re.compile(r"\bshown\b", re.IGNORECASE),
    re.compile(r"\bevidence directly (backs|supports)\b", re.IGNORECASE),
    re.compile(r"\bunambiguous\b", re.IGNORECASE),
    re.compile(r"\bconclusively\b", re.IGNORECASE),
]


def _classify_hedge(explanation: str) -> str:
    """Return 'hedged', 'confident', or 'neutral' based on language patterns.

    Counts hedge vs confidence phrase hits. Whichever side wins by ≥1 with
    a minimum count of 2 wins. Otherwise neutral.
    """
    if not explanation:
        return "neutral"
    hedge_hits = sum(1 for p in HEDGE_PATTERNS if p.search(explanation))
    conf_hits = sum(1 for p in CONFIDENCE_PATTERNS if p.search(explanation))
    if hedge_hits >= 2 and hedge_hits > conf_hits:
        return "hedged"
    if conf_hits >= 2 and conf_hits > hedge_hits:
        return "confident"
    return "neutral"


@scorer(metrics=[mean()])
def calibration_scorer() -> Scorer:
    """Verbalized-confidence calibration scorer.

    Compares the model's hedge language to its actual accuracy on the case.
    Per Nakkiran et al. (arXiv:2511.04869) verbalized confidence is unreliable,
    but it's the only signal available without multi-epoch sampling. Sampling-
    based calibration belongs in cards.py (post-eval, across epochs).

    Score:
    - 1.0 if abstention verdict (insufficient_evidence / not_verifiable)
      → these are inherently hedge-aligned, free pass
    - 1.0 if (confident language AND verdict correct)  → calibrated_confident
    - 1.0 if (hedged language AND verdict wrong)       → calibrated_hedged
    - 0.0 if (confident language AND verdict wrong)    → overconfident
    - 0.0 if (hedged language AND verdict correct)     → underconfident
    - 0.5 if neutral language                          → unclear

    The neutral score is structurally biased toward 0.5 — that's intentional.
    A bench full of "neutral" outputs is itself a finding (the model isn't
    expressing calibration in either direction).
    """

    async def score(state: TaskState, target: Target) -> Score:
        raw_output = state.output.completion if state.output else ""
        predicted = _extract_verdict(raw_output)
        gold = _normalize(target.text)
        correct = predicted == gold
        hedge_class = _classify_hedge(raw_output)

        if predicted in ("insufficient_evidence", "not_verifiable"):
            value = 1.0
            label = "abstention_consistent"
        elif hedge_class == "neutral":
            value = 0.5
            label = "neutral"
        elif hedge_class == "confident" and correct:
            value = 1.0
            label = "calibrated_confident"
        elif hedge_class == "hedged" and not correct:
            value = 1.0
            label = "calibrated_hedged"
        elif hedge_class == "confident" and not correct:
            value = 0.0
            label = "overconfident"
        elif hedge_class == "hedged" and correct:
            value = 0.0
            label = "underconfident"
        else:
            value = 0.5
            label = "unclear"

        return Score(
            value=value,
            answer=label,
            explanation=f"hedge={hedge_class} pred={predicted} gold={gold}",
            metadata={
                "hedge_class": hedge_class,
                "calibration_label": label,
                "predicted": predicted,
                "gold": gold,
                "correct": correct,
            },
        )

    return score


# ─── Trace faithfulness (deterministic citation check) ───────────────────────


def _normalize_url_for_match(url: str) -> str:
    """Strip protocol, www, query, fragment, and trailing / for fuzzy match."""
    if not url:
        return ""
    u = url.lower()
    if "//" in u:
        u = u.split("//", 1)[1]
    if u.startswith("www."):
        u = u[4:]
    u = u.split("#", 1)[0].split("?", 1)[0].rstrip("/")
    return u


@scorer(metrics=[mean()])
def trace_faithfulness_scorer() -> Scorer:
    """Pure-deterministic check that explanation citations appear in retrieval trace.

    Walks the model's explanation, extracts cited DOIs and URLs, and checks
    each against the retrieval trace text. Citations that don't appear in
    the trace are flagged as fabricated.

    Score: fraction of cited sources that appear in the trace. Returns 1.0
    if no citations were attempted (no fabrication risk).

    No LLM judge — fabrication detection is a string-match problem at this
    layer, not a semantic one. The semantic question ("does this citation
    actually support what the model says it does?") is groundedness's job.
    """

    async def score(state: TaskState, target: Target) -> Score:
        raw_output = state.output.completion if state.output else ""
        trace_text = _trace_text(state)

        explanation_dois = _extract_dois_from_text(raw_output)
        explanation_urls = set(_extract_urls_from_text(raw_output))

        trace_dois = _extract_dois_from_text(trace_text)
        trace_urls_normalized = {
            _normalize_url_for_match(u) for u in _extract_urls_from_text(trace_text)
        }

        all_citations = explanation_dois | explanation_urls
        if not all_citations:
            return Score(
                value=1.0,
                answer="no_citations",
                explanation="Model did not cite any specific sources",
                metadata={
                    "citations_attempted": 0,
                    "citations_faithful": 0,
                    "fabricated_citations": [],
                },
            )

        faithful_dois = explanation_dois & trace_dois
        faithful_urls: set[str] = set()
        for url in explanation_urls:
            normalized = _normalize_url_for_match(url)
            if normalized in trace_urls_normalized:
                faithful_urls.add(url)
                continue
            # Loose match: any trace URL with the same prefix or vice versa.
            for trace_norm in trace_urls_normalized:
                if normalized and trace_norm and (
                    normalized.startswith(trace_norm) or trace_norm.startswith(normalized)
                ):
                    faithful_urls.add(url)
                    break

        all_faithful = faithful_dois | faithful_urls
        fabricated = sorted((explanation_dois | explanation_urls) - all_faithful)

        value = len(all_faithful) / len(all_citations)

        return Score(
            value=value,
            answer=f"{len(all_faithful)}/{len(all_citations)}",
            explanation=(
                f"faithful={sorted(all_faithful)[:3]} "
                f"fabricated={fabricated[:3]}"
            ),
            metadata={
                "citations_attempted": len(all_citations),
                "citations_faithful": len(all_faithful),
                "fabricated_citations": fabricated,
            },
        )

    return score


# ─── Retrieval attempted (top-level promotion) ───────────────────────────────


@scorer(metrics=[mean()])
def retrieval_attempted_scorer() -> Scorer:
    """Top-level scorer: did the model attempt retrieval at all?

    Promoted from groundedness_scorer's tool_calls_seen metadata per the
    Phase 1 plan-close deferred finding #5. A model that NEVER calls a
    tool is answering from training data alone — that's a separate failure
    mode from low groundedness or wrong verdict, and it deserves its own
    column rather than being buried inside another scorer's metadata.
    """

    async def score(state: TaskState, target: Target) -> Score:
        tool_call_count = 0
        tool_result_count = 0
        for msg in state.messages:
            if isinstance(msg, ChatMessageTool):
                tool_result_count += 1
            elif (
                getattr(msg, "role", None) == "assistant"
                and getattr(msg, "tool_calls", None)
            ):
                tool_call_count += len(msg.tool_calls or [])

        attempted = (tool_call_count > 0) or (tool_result_count > 0)
        return Score(
            value=1.0 if attempted else 0.0,
            answer="attempted" if attempted else "no_retrieval",
            explanation=(
                f"{tool_call_count} tool calls, {tool_result_count} tool results"
            ),
            metadata={
                "tool_call_count": tool_call_count,
                "tool_result_count": tool_result_count,
                "retrieval_attempted": attempted,
            },
        )

    return score


# ─── Joint success helper (for cards.py to consume) ──────────────────────────


def joint_success_per_sample(
    verdict_match: float,
    groundedness_value: float,
    currency_value: float | None = None,
    currency_label: str | None = None,
) -> bool:
    """Canonical definition of joint success for one sample.

    A sample joint-passes iff:
        verdict_match == 1.0
        AND groundedness_value >= 0.5  (grounded or partial)
        AND (currency_value is None         # not measured this run
             OR currency_label == "not_applicable"
             OR currency_value >= 0.5)       # current or partial

    This is the headline metric — claim-bench's "did the bench actually
    pass" rolls up the per-scorer values into one boolean per sample. Per-
    scorer columns stay visible alongside it for debugging.

    Lives here (not as a Scorer) because inspect_ai's Scorer API doesn't
    expose peer scorer outputs in-band. cards.py reads the EvalLog and
    calls this helper for each sample to derive the headline.
    """
    if verdict_match < 1.0:
        return False
    if groundedness_value < 0.5:
        return False
    if currency_value is None:
        return True
    if currency_label == "not_applicable":
        return True
    return currency_value >= 0.5
