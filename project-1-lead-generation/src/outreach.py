"""Personalized outreach message generation (simulated Claude responses for demo).

Generates subject lines and email bodies tailored to each lead's
pain points, industry, contact role, and product interest.

In production, replace _build_subject and _build_message with a single
anthropic.Anthropic().messages.create() call using a structured prompt.
"""

from loguru import logger

from .models import Lead, LeadStatus, OutreachResult, ScoringResult


_SUBJECT_TEMPLATES: dict[str, list[str]] = {
    "AI lead scoring and outreach automation": [
        "Cut {company}'s lead research from hours to seconds",
        "How {company} can 3x outreach volume without adding headcount",
        "{first_name}, your sales team deserves better than manual lead research",
    ],
    "Document processing and invoice automation": [
        "Eliminate {company}'s manual invoice processing in 2 weeks",
        "{first_name}, what if {company} processed invoices in seconds, not days?",
        "How teams like {company} cut invoice errors by 90%",
    ],
    "RAG support chatbot for customer service": [
        "Answer {company}'s repetitive support tickets automatically",
        "{first_name}, 80% of your support tickets could resolve themselves",
        "How {company} can handle 5x support volume without hiring",
    ],
    "Workflow automation and data pipeline": [
        "Stop {company}'s team from manually pulling data across tools",
        "{first_name}, what if your {industry} reports were ready in minutes?",
        "How {company} can reclaim 10+ hours/week from manual workflows",
    ],
    "AI-powered report generation": [
        "Generate {company}'s weekly reports automatically — in minutes",
        "{first_name}, your team shouldn't spend days on a report",
        "How {company} can have real-time reporting without the manual work",
    ],
    "Client onboarding automation": [
        "Cut {company}'s client onboarding from weeks to days",
        "{first_name}, automate onboarding and never lose a client to slow setup",
        "How {company} can onboard clients 5x faster",
    ],
    "Contract analysis automation": [
        "Review contracts in minutes, not hours — for {company}",
        "{first_name}, what if {company} could review NDAs in under 10 minutes?",
        "Scale {company}'s contract review without scaling headcount",
    ],
}

_DEFAULT_SUBJECTS: list[str] = [
    "How {company} can automate its biggest manual bottleneck",
    "{first_name}, a quick question about {company}'s workflow",
]

_PAIN_AREA_MAP: dict[str, str] = {
    "AI lead scoring and outreach automation": "lead qualification and outreach",
    "Document processing and invoice automation": "invoice and document processing",
    "RAG support chatbot for customer service": "customer support queue",
    "Workflow automation and data pipeline": "data workflows and reporting",
    "AI-powered report generation": "reporting pipeline",
    "Client onboarding automation": "client onboarding process",
    "Contract analysis automation": "contract review workflow",
}

_MESSAGE_TEMPLATE = """\
Hi {first_name},

I noticed that {company} — a {size}-person {industry} company — is dealing with a challenge that comes up a lot in your space:

"{pain_snippet}"

This is exactly the kind of problem our AI automation system was built for. Here’s what it looks like in practice:

1. Your {pain_area} gets connected to an automated pipeline
2. AI processes and routes each item in seconds — no manual intervention needed
3. Your team reviews exceptions only, instead of handling everything by hand

Companies in the {industry} space typically recover 10–15 hours per week per team member once this is live.

Given your role as {title} at {company}, you’re the right person to evaluate whether this fits. Would a 20-minute walkthrough make sense this week?

Best,
[Your name]
AI Automation Specialist

P.S. I can send over a working demo tailored to {industry} workflows before our call if that’s useful.\
"""


def _first_name(contact_name: str) -> str:
    """Extract first name, stripping professional prefixes."""
    name = contact_name.replace("Dr.", "").replace("Prof.", "").strip()
    return name.split()[0]


def _truncate(text: str, max_chars: int = 120) -> str:
    """Truncate text at word boundary to avoid cutting mid-word."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "…"


def _build_subject(lead: Lead) -> str:
    templates = _SUBJECT_TEMPLATES.get(lead.product_interest, _DEFAULT_SUBJECTS)
    # Deterministic selection so output is reproducible per lead
    template = templates[hash(lead.id) % len(templates)]
    return template.format(
        company=lead.company_name,
        first_name=_first_name(lead.contact_name),
        industry=lead.industry,
    )


def _build_message(lead: Lead, scoring: ScoringResult) -> str:
    return _MESSAGE_TEMPLATE.format(
        first_name=_first_name(lead.contact_name),
        company=lead.company_name,
        size=lead.company_size.value,
        industry=lead.industry,
        pain_snippet=_truncate(lead.pain_points),
        pain_area=_PAIN_AREA_MAP.get(lead.product_interest, "manual workflow"),
        title=lead.contact_title,
    )


def _personalization_hooks(lead: Lead, scoring: ScoringResult) -> list[str]:
    return [
        f"industry={lead.industry}",
        f"size={lead.company_size.value}",
        f"role={lead.contact_title}",
        f"pain={_truncate(lead.pain_points, 60)}",
        f"source={lead.lead_source}",
        f"tier={scoring.qualification_tier}",
    ]


def generate_outreach(lead: Lead, scoring: ScoringResult) -> OutreachResult:
    """Generate a personalized outreach email for a single scored lead.

    Returns subject, message body, and the personalization hooks used.
    Swap this function body for a real Claude API call in production.
    """
    logger.info(f"Generating outreach for lead {lead.id} — {lead.company_name}")

    subject = _build_subject(lead)
    message = _build_message(lead, scoring)
    hooks = _personalization_hooks(lead, scoring)

    logger.info(f"Outreach ready for {lead.id} — subject: {subject[:55]}")
    return OutreachResult(
        lead_id=lead.id,
        subject=subject,
        message=message,
        personalization_hooks=hooks,
    )


def generate_outreach_batch(
    leads: list[Lead],
    scores: list[ScoringResult],
) -> tuple[list[Lead], list[OutreachResult]]:
    """Generate outreach for all leads above the min_score_threshold.

    Skips DISQUALIFIED leads. Failures are logged; the lead keeps SCORED status.
    Returns updated leads (status = OUTREACHED) and OutreachResult list.
    """
    score_map = {r.lead_id: r for r in scores}
    updated: list[Lead] = []
    results: list[OutreachResult] = []

    for lead in leads:
        if lead.status == LeadStatus.DISQUALIFIED:
            updated.append(lead)
            continue

        scoring = score_map.get(lead.id)
        if not scoring:
            logger.warning(f"No scoring result for lead {lead.id} — skipping outreach")
            updated.append(lead)
            continue

        try:
            result = generate_outreach(lead, scoring)
            data = lead.model_dump()
            data["outreach_subject"] = result.subject
            data["outreach_message"] = result.message
            data["status"] = LeadStatus.OUTREACHED
            updated.append(Lead(**data))
            results.append(result)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Outreach generation failed for lead {lead.id}: {exc}")
            updated.append(lead)

    logger.info(
        f"Outreach complete: {len(results)}/{len(leads)} leads received messages"
    )
    return updated, results
