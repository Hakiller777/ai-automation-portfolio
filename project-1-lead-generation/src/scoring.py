"""AI-powered lead scoring (simulated Claude responses for demo).

Scores each enriched lead 1-10 from five weighted signals:
  - Company size       (budget signal)
  - Annual revenue     (spending capacity)
  - Contact seniority  (decision-making authority)
  - Pain urgency       (immediacy of need)
  - Lead source        (intent quality)

In production, replace _score_lead's logic block with a real
anthropic.Anthropic().messages.create() call and parse the JSON response.
"""

import re

from loguru import logger

from .config import settings
from .models import Lead, LeadStatus, ScoringResult


_WEIGHTS: dict[str, float] = {
    "company_size": 0.20,
    "revenue": 0.15,
    "contact_seniority": 0.25,
    "pain_urgency": 0.25,
    "lead_source": 0.15,
}

_SIZE_SCORES: dict[str, int] = {
    "1-10": 3,
    "11-50": 5,
    "51-200": 7,
    "201-500": 9,
    "500+": 10,
}

_REVENUE_SCORES: dict[str, int] = {
    "$500K-$1M": 3,
    "$1M-$2M": 4,
    "$1M-$3M": 5,
    "$1M-$5M": 5,
    "$2M-$4M": 5,
    "$2M-$5M": 6,
    "$3M-$8M": 6,
    "$4M-$8M": 7,
    "$5M-$8M": 7,
    "$5M-$10M": 8,
    "$6M-$10M": 8,
    "$7M-$12M": 8,
    "$8M-$15M": 9,
    "$10M-$20M": 9,
    "$12M-$20M": 9,
    "$15M-$30M": 9,
    "$20M-$40M": 10,
    "$20M-$50M": 10,
    "$25M-$50M": 10,
    "$30M-$60M": 10,
    "$40M-$80M": 10,
    "$50M-$100M": 10,
}

# Ordered by SPECIFICITY, not by score. "Vice President" and "Director" have
# to be tested before the C-suite tier, or the broader keywords in that tier
# swallow them ("president" matches inside "vice president").
#
# Matching is word-boundary anchored, never a plain substring. Substring
# matching silently scored every "Director" as a CTO — "dire(cto)r" — and
# every "Coordinator" as a COO — "(coo)rdinator" — inflating junior and
# mid-level contacts to the maximum seniority score.
_SENIORITY_TIERS: list[tuple[int, list[str]]] = [
    (8,  ["vp", "svp", "evp", "vice president", "head of", "director"]),
    (10, ["ceo", "cto", "coo", "cfo", "chro", "founder", "co-founder",
          "president", "owner", "managing partner"]),
    (6,  ["manager", "lead", "principal", "senior"]),
    (4,  ["analyst", "associate", "specialist", "coordinator",
          "assistant", "intern", "junior"]),
]

_URGENCY_HIGH: list[str] = [
    "hours", "days", "overwhelmed", "no longer sustainable", "burned out",
    "cannot scale", "losing", "reactive", "bottleneck", "rejection rate",
    "completely", "entirely", "every single", "fully manual", "all manual",
]

_URGENCY_MEDIUM: list[str] = [
    "slow", "delay", "inconsistent", "scattered", "stale", "consuming",
    "manually", "manual", "tedious", "requires pulling", "spreadsheet",
]

_SOURCE_SCORES: dict[str, int] = {
    "referral": 10,
    "conference": 8,
    "linkedin": 7,
    "website": 6,
    "cold_email": 4,
}


def _score_company_size(lead: Lead) -> int:
    return _SIZE_SCORES.get(lead.company_size.value, 5)


def _score_revenue(lead: Lead) -> int:
    if not lead.annual_revenue:
        return 5
    return _REVENUE_SCORES.get(lead.annual_revenue, 5)


def _score_contact_seniority(lead: Lead) -> int:
    """Score decision-making authority from the contact's job title.

    Keywords are matched on word boundaries so a title is never scored by an
    accidental substring — see the note on `_SENIORITY_TIERS`.
    """
    title = lead.contact_title.lower()
    for score, keywords in _SENIORITY_TIERS:
        if any(re.search(rf"\b{re.escape(kw)}\b", title) for kw in keywords):
            return score
    return 5


def _score_pain_urgency(lead: Lead) -> int:
    pain = lead.pain_points.lower()
    high = sum(1 for kw in _URGENCY_HIGH if kw in pain)
    medium = sum(1 for kw in _URGENCY_MEDIUM if kw in pain)
    return max(1, min(10, 3 + high * 2 + medium))


def _score_lead_source(lead: Lead) -> int:
    return _SOURCE_SCORES.get(lead.lead_source, 5)


def _build_reasoning(
    lead: Lead,
    size: int,
    revenue: int,
    seniority: int,
    urgency: int,
    source: int,
    final: int,
) -> str:
    tier = get_qualification_tier(final)
    authority = (
        "strong" if seniority >= 8 else
        "moderate" if seniority >= 6 else "limited"
    )
    urgency_label = (
        "critical and immediate" if urgency >= 8 else
        "clear operational pain" if urgency >= 5 else "mild inconvenience"
    )
    revenue_ctx = f" with {lead.annual_revenue}" if lead.annual_revenue else ""
    return (
        f"{lead.company_name} scores {final}/10 — qualified as {tier.upper()}. "
        f"Company profile: {lead.company_size.value} employees{revenue_ctx} "
        f"in the {lead.industry} space (size={size}, revenue={revenue}). "
        f"Contact {lead.contact_name} ({lead.contact_title}) has {authority} "
        f"decision-making authority (seniority={seniority}). "
        f'Pain urgency: "{lead.pain_points[:80]}" signals {urgency_label} '
        f"(urgency={urgency}). Lead source '{lead.lead_source}' quality={source}."
    )


def get_qualification_tier(score: int) -> str:
    """Map a numeric score 1-10 to a qualification tier."""
    if score >= settings.hot_threshold:
        return "hot"
    if score >= settings.warm_threshold:
        return "warm"
    return "cold"


def score_lead(lead: Lead) -> ScoringResult:
    """Score a single enriched lead using a weighted composite formula.

    Returns a ScoringResult with score, reasoning, and qualification tier.
    Swap the body of this function for a real Claude API call in production.
    """
    logger.info(f"Scoring lead {lead.id} — {lead.company_name}")

    size = _score_company_size(lead)
    revenue = _score_revenue(lead)
    seniority = _score_contact_seniority(lead)
    urgency = _score_pain_urgency(lead)
    source = _score_lead_source(lead)

    raw = (
        size * _WEIGHTS["company_size"]
        + revenue * _WEIGHTS["revenue"]
        + seniority * _WEIGHTS["contact_seniority"]
        + urgency * _WEIGHTS["pain_urgency"]
        + source * _WEIGHTS["lead_source"]
    )
    final = max(1, min(10, round(raw)))
    tier = get_qualification_tier(final)

    logger.info(f"Lead {lead.id} scored {final}/10 ({tier})")
    return ScoringResult(
        lead_id=lead.id,
        score=final,
        reasoning=_build_reasoning(lead, size, revenue, seniority, urgency, source, final),
        qualification_tier=tier,
    )


def score_batch(leads: list[Lead]) -> tuple[list[Lead], list[ScoringResult]]:
    """Score a batch of enriched leads.

    Leads below min_score_threshold are marked DISQUALIFIED.
    Returns updated leads and the full list of ScoringResults.
    Failures are logged; the lead is kept in its previous status.
    """
    updated: list[Lead] = []
    results: list[ScoringResult] = []

    for lead in leads:
        try:
            result = score_lead(lead)
            data = lead.model_dump()
            data["score"] = result.score
            data["score_reasoning"] = result.reasoning
            data["status"] = (
                LeadStatus.DISQUALIFIED
                if result.score < settings.min_score_threshold
                else LeadStatus.SCORED
            )
            updated.append(Lead(**data))
            results.append(result)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Scoring failed for lead {lead.id}: {exc}")
            updated.append(lead)

    scored = sum(1 for l in updated if l.status == LeadStatus.SCORED)
    disqualified = sum(1 for l in updated if l.status == LeadStatus.DISQUALIFIED)
    hot = sum(1 for r in results if r.qualification_tier == "hot")
    warm = sum(1 for r in results if r.qualification_tier == "warm")

    logger.info(
        f"Scoring complete: {scored} scored, {disqualified} disqualified "
        f"({hot} hot / {warm} warm)"
    )
    return updated, results
