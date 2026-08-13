"""Tests for src/scoring.py

Coverage per module: 1 happy path, 2 edge cases, 1 error case.
"""

import src.scoring as scoring_module
from src.models import Lead, LeadStatus
from src.scoring import get_qualification_tier, score_batch, score_lead


class TestGetQualificationTier:
    def test_score_8_is_hot(self):
        assert get_qualification_tier(8) == "hot"

    def test_score_10_is_hot(self):
        assert get_qualification_tier(10) == "hot"

    def test_score_5_is_warm(self):
        assert get_qualification_tier(5) == "warm"

    def test_score_7_is_warm(self):
        assert get_qualification_tier(7) == "warm"

    def test_score_4_is_cold(self):
        assert get_qualification_tier(4) == "cold"

    def test_score_1_is_cold(self):
        assert get_qualification_tier(1) == "cold"


class TestScoreLead:
    def test_happy_path_returns_valid_score(self, sample_lead):
        """Typical lead produces score in [1, 10] with reasoning and tier."""
        result = score_lead(sample_lead)
        assert 1 <= result.score <= 10
        assert result.reasoning
        assert result.qualification_tier in ("hot", "warm", "cold")
        assert result.lead_id == sample_lead.id

    # Edge case 1: enterprise always outscores micro
    def test_enterprise_outscores_micro(self, micro_lead, enterprise_lead):
        """Enterprise lead with all-high signals must score above micro lead."""
        assert score_lead(enterprise_lead).score > score_lead(micro_lead).score

    # Edge case 2: referral source scores >= cold_email, all else equal
    def test_referral_beats_cold_email_source(self, sample_lead):
        """Higher-quality source must produce equal or higher score."""
        referral = Lead(**{**sample_lead.model_dump(), "lead_source": "referral"})
        cold = Lead(**{**sample_lead.model_dump(), "lead_source": "cold_email"})
        assert score_lead(referral).score >= score_lead(cold).score

    # Error case: batch survives individual scoring failure
    def test_score_batch_survives_failure(self, sample_lead, monkeypatch):
        """score_batch must return all leads even when one scoring call raises."""
        original_fn = scoring_module.score_lead
        call_count = {"n": 0}

        def fail_first(lead):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("Simulated scoring failure")
            return original_fn(lead)

        monkeypatch.setattr(scoring_module, "score_lead", fail_first)
        leads = [sample_lead, sample_lead.model_copy(update={"id": "test-006"})]
        updated, results = scoring_module.score_batch(leads)
        assert len(updated) == 2


class TestContactSeniorityMatching:
    """Titles must be matched on whole words, never on substrings.

    Substring matching scored "Director" as a CTO ("dire(cto)r") and
    "Coordinator" as a COO ("(coo)rdinator"), pushing mid-level and junior
    contacts to the maximum seniority score. That inflated every composite
    score enough that no lead in the sample set ever fell below the
    disqualification threshold, which hid the disqualification path entirely.
    """

    def _seniority(self, sample_lead, title: str) -> int:
        lead = Lead(**{**sample_lead.model_dump(), "contact_title": title})
        return scoring_module._score_contact_seniority(lead)

    def test_director_is_not_scored_as_c_suite(self, sample_lead):
        assert self._seniority(sample_lead, "Director of IT") == 8
        assert self._seniority(sample_lead, "IT Director") == 8

    def test_coordinator_is_not_scored_as_c_suite(self, sample_lead):
        assert self._seniority(sample_lead, "Marketing Coordinator") == 4

    def test_vice_president_outranked_by_c_suite(self, sample_lead):
        """"vice president" must win over the bare "president" keyword."""
        assert self._seniority(sample_lead, "Vice President of Sales") == 8
        assert self._seniority(sample_lead, "President") == 10

    def test_c_suite_titles_still_score_highest(self, sample_lead):
        for title in ("CEO", "CTO", "COO", "Co-Founder", "Owner"):
            assert self._seniority(sample_lead, title) == 10, title

    def test_unknown_title_falls_back_to_neutral(self, sample_lead):
        assert self._seniority(sample_lead, "Chief Vibes Officiant") == 5


class TestScoreBatch:
    def test_disqualified_below_threshold(self, micro_lead):
        """Leads with all-low signals score below threshold and get DISQUALIFIED."""
        weak = Lead(**{
            **micro_lead.model_dump(),
            "pain_points": "Would be nice someday",
            "contact_title": "Operations Analyst",
            "lead_source": "cold_email",
            "annual_revenue": "$500K-$1M",
        })
        updated, _ = score_batch([weak])
        assert updated[0].status == LeadStatus.DISQUALIFIED

    def test_hot_enterprise_lead_marked_scored(self, enterprise_lead):
        """A high-signal enterprise lead must be SCORED, never DISQUALIFIED."""
        updated, results = score_batch([enterprise_lead])
        assert updated[0].status == LeadStatus.SCORED
        assert updated[0].score is not None
        assert results[0].qualification_tier == "hot"
