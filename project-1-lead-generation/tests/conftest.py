"""Shared pytest fixtures for project-1 test suite."""

import pytest

from src.models import CompanySize, Lead, LeadStatus, ScoringResult


@pytest.fixture
def sample_lead() -> Lead:
    """Typical enriched B2B lead for happy-path tests."""
    return Lead(
        id="test-001",
        company_name="TestCorp Inc",
        industry="SaaS",
        company_size=CompanySize.MEDIUM,
        annual_revenue="$5M-$10M",
        website="testcorp.io",
        location_city="Austin",
        location_country="USA",
        contact_name="Alice Johnson",
        contact_title="VP of Sales",
        contact_email="a.johnson@testcorp.io",
        lead_source="linkedin",
        product_interest="AI lead scoring and outreach automation",
        pain_points="Sales team spends 40% of time on admin tasks; lead follow-up falling through the cracks",
        tech_stack="AWS, React, PostgreSQL",
        company_description="TestCorp is a 51-200 employee SaaS company.",
        status=LeadStatus.ENRICHED,
    )


@pytest.fixture
def micro_lead() -> Lead:
    """Smallest possible company — edge case for low-score tests."""
    return Lead(
        id="test-002",
        company_name="TinyStartup",
        industry="Legal Tech",
        company_size=CompanySize.MICRO,
        annual_revenue="$500K-$1M",
        website="tinystartup.io",
        location_city="Remote",
        location_country="USA",
        contact_name="Bob Smith",
        contact_title="Intern",
        contact_email="bob@tinystartup.io",
        lead_source="cold_email",
        product_interest="Contract analysis automation",
        pain_points="Would be nice to have some automation someday",
        status=LeadStatus.ENRICHED,
    )


@pytest.fixture
def enterprise_lead() -> Lead:
    """Large enterprise with all-high signals — edge case for hot-score tests."""
    return Lead(
        id="test-003",
        company_name="MegaCorp Ltd",
        industry="Fintech",
        company_size=CompanySize.ENTERPRISE,
        annual_revenue="$50M-$100M",
        website="megacorp.com",
        location_city="New York",
        location_country="USA",
        contact_name="Carol Chen",
        contact_title="CEO",
        contact_email="c.chen@megacorp.com",
        lead_source="referral",
        product_interest="Document processing and invoice automation",
        pain_points="Completely manual invoice process; cannot scale; burning out the team; 5 days every month",
        status=LeadStatus.ENRICHED,
    )


@pytest.fixture
def raw_lead() -> Lead:
    """Unenriched lead (status=PENDING) for enrichment tests."""
    return Lead(
        id="test-004",
        company_name="FreshLead Co",
        industry="E-commerce",
        company_size=CompanySize.SMALL,
        location_city="Miami",
        location_country="USA",
        contact_name="Dan Rivera",
        contact_title="CTO",
        contact_email="d.rivera@freshlead.co",
        lead_source="website",
        product_interest="RAG support chatbot for customer service",
        pain_points="Support team overwhelmed with repetitive tickets every single day",
    )


@pytest.fixture
def scoring_result_hot() -> ScoringResult:
    """Hot-tier scoring result for outreach tests."""
    return ScoringResult(
        lead_id="test-003",
        score=9,
        reasoning="MegaCorp scores 9/10 — HOT.",
        qualification_tier="hot",
    )


@pytest.fixture
def scoring_result_warm() -> ScoringResult:
    """Warm-tier scoring result for outreach tests."""
    return ScoringResult(
        lead_id="test-001",
        score=7,
        reasoning="TestCorp scores 7/10 — WARM.",
        qualification_tier="warm",
    )
