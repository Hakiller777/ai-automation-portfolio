"""Rule-based data enrichment for B2B leads.

Fills tech_stack and company_description fields using industry lookup tables.
No external API calls — deterministic and testable.
"""

from loguru import logger

from .models import Lead, LeadStatus


_INDUSTRY_TECH_STACKS: dict[str, str] = {
    "SaaS": "AWS/GCP, React, PostgreSQL, Stripe",
    "Fintech": "AWS, Python, PostgreSQL, Plaid API",
    "Healthcare Tech": "Azure, Python, PostgreSQL, HL7/FHIR",
    "E-commerce": "Shopify/AWS, React, PostgreSQL, Stripe",
    "Logistics": "AWS, Python, PostgreSQL, Google Maps API",
    "Real Estate Tech": "AWS, React, PostgreSQL, Google Maps API",
    "HR Tech": "AWS, React, PostgreSQL, DocuSign",
    "Marketing Tech": "GCP, Python, BigQuery, HubSpot API",
    "Legal Tech": "AWS, Python, PostgreSQL, DocuSign",
    "EdTech": "AWS, React, PostgreSQL, Stripe",
    "InsurTech": "AWS, Python, PostgreSQL, Salesforce",
}

_INDUSTRY_DESCRIPTIONS: dict[str, str] = {
    "SaaS": "B2B software company selling subscription-based products to business customers.",
    "Fintech": "Financial technology company offering digital financial services and process automation.",
    "Healthcare Tech": "Digital health company providing technology solutions for healthcare providers and patients.",
    "E-commerce": "Online retail business managing direct-to-consumer or marketplace sales at scale.",
    "Logistics": "Freight and supply chain company managing transportation, tracking, and delivery operations.",
    "Real Estate Tech": "PropTech company digitizing real estate transactions, listings, and property management.",
    "HR Tech": "Human resources technology company automating recruiting, onboarding, and people operations.",
    "Marketing Tech": "MarTech company providing tools for digital marketing, campaign management, and analytics.",
    "Legal Tech": "LegalTech company automating contract review, document workflows, and compliance processes.",
    "EdTech": "Education technology company delivering digital learning tools and course management platforms.",
    "InsurTech": "Insurance technology company modernizing underwriting, claims, and policy management.",
}


def enrich_lead(lead: Lead) -> Lead:
    """Enrich a single lead with tech stack and company description.

    Returns a new Lead instance — the original is not mutated.
    Falls back to generic values when industry is not in the lookup table.
    """
    logger.info(f"Enriching lead {lead.id} — {lead.company_name} ({lead.industry})")

    data = lead.model_dump()

    if not data.get("tech_stack"):
        data["tech_stack"] = _INDUSTRY_TECH_STACKS.get(
            lead.industry, "Cloud infrastructure, Python, PostgreSQL"
        )

    if not data.get("company_description"):
        base = _INDUSTRY_DESCRIPTIONS.get(
            lead.industry, "Technology company with process automation needs."
        )
        data["company_description"] = (
            f"{lead.company_name} is a {lead.company_size.value}-employee "
            f"{lead.industry} company based in {lead.location_city}, "
            f"{lead.location_country}. {base}"
        )

    data["status"] = LeadStatus.ENRICHED

    enriched = Lead(**data)
    logger.info(f"Lead {lead.id} enriched — tech_stack: {enriched.tech_stack[:40]}...")
    return enriched


def enrich_batch(leads: list[Lead]) -> list[Lead]:
    """Enrich a list of leads, logging and skipping individual failures.

    Always returns the same number of leads as input — failed enrichments
    are included un-enriched rather than dropped to avoid data loss.
    """
    results: list[Lead] = []

    for lead in leads:
        try:
            results.append(enrich_lead(lead))
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Enrichment failed for lead {lead.id}: {exc}")
            results.append(lead)

    success = sum(1 for r in results if r.status == LeadStatus.ENRICHED)
    logger.info(f"Enrichment complete: {success}/{len(leads)} leads enriched")
    return results
