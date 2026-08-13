"""Tests for src/outreach.py

Coverage per module: 1 happy path, 2 edge cases, 1 error case.
"""

from src.models import Lead, LeadStatus
from src.outreach import generate_outreach, generate_outreach_batch


class TestGenerateOutreach:
    def test_happy_path_returns_subject_and_message(self, sample_lead, scoring_result_warm):
        """Happy path: result has non-empty subject, message, and hooks."""
        result = generate_outreach(sample_lead, scoring_result_warm)
        assert result.subject
        assert result.message
        assert result.lead_id == sample_lead.id
        assert result.personalization_hooks

    def test_subject_references_company_or_first_name(self, sample_lead, scoring_result_warm):
        """Subject must contain either company name or contact first name."""
        result = generate_outreach(sample_lead, scoring_result_warm)
        first_name = sample_lead.contact_name.split()[0]
        assert (
            sample_lead.company_name in result.subject
            or first_name in result.subject
        )

    def test_message_contains_pain_snippet(self, sample_lead, scoring_result_warm):
        """Message body must embed a recognizable slice of the lead's pain points."""
        result = generate_outreach(sample_lead, scoring_result_warm)
        assert sample_lead.pain_points[:30] in result.message

    # Edge case 1: 'Dr.' prefix must be stripped from first name
    def test_dr_prefix_stripped_in_message(self, sample_lead, scoring_result_warm):
        """'Dr.' prefix must not appear in the greeting line."""
        dr_lead = Lead(**{**sample_lead.model_dump(), "contact_name": "Dr. Alice Johnson"})
        result = generate_outreach(dr_lead, scoring_result_warm)
        assert "Dr." not in result.subject
        assert result.message.startswith("Hi Alice")

    # Edge case 2: unknown product_interest falls back without raising
    def test_unknown_product_interest_uses_fallback_subject(self, sample_lead, scoring_result_warm):
        """Unknown product interest must produce a valid subject, never raise."""
        odd_lead = Lead(**{**sample_lead.model_dump(), "product_interest": "Quantum AI Blockchain"})
        result = generate_outreach(odd_lead, scoring_result_warm)
        assert result.subject

    # Error case: batch skips DISQUALIFIED leads entirely
    def test_batch_skips_disqualified_leads(self, sample_lead, scoring_result_warm):
        """DISQUALIFIED leads must not receive outreach and keep their status."""
        disq = Lead(**{**sample_lead.model_dump(), "status": LeadStatus.DISQUALIFIED})
        updated, results = generate_outreach_batch([disq], [scoring_result_warm])
        assert len(results) == 0
        assert updated[0].status == LeadStatus.DISQUALIFIED


class TestGenerateOutreachBatch:
    def test_outreached_leads_have_status_outreached(self, sample_lead, scoring_result_warm):
        """Successfully processed leads must have status OUTREACHED."""
        updated, results = generate_outreach_batch([sample_lead], [scoring_result_warm])
        assert updated[0].status == LeadStatus.OUTREACHED
        assert updated[0].outreach_subject
        assert updated[0].outreach_message

    def test_missing_score_lead_is_skipped(self, sample_lead):
        """A lead with no matching ScoringResult must be skipped silently."""
        updated, results = generate_outreach_batch([sample_lead], [])  # empty scores
        assert len(results) == 0
        assert updated[0].status == sample_lead.status  # unchanged
