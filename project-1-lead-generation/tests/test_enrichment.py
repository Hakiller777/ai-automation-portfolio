"""Tests for src/enrichment.py

Coverage per module: 1 happy path, 2 edge cases, 1 error case.
"""

import src.enrichment as enrichment_module
from src.enrichment import enrich_batch, enrich_lead
from src.models import Lead, LeadStatus


class TestEnrichLead:
    def test_happy_path_fills_tech_stack_and_description(self, raw_lead):
        """Known industry must produce non-empty tech_stack and company_description."""
        result = enrich_lead(raw_lead)
        assert result.tech_stack
        assert result.company_description
        assert raw_lead.company_name in result.company_description

    def test_status_changes_to_enriched(self, raw_lead):
        """Status must be ENRICHED after successful enrichment."""
        result = enrich_lead(raw_lead)
        assert result.status == LeadStatus.ENRICHED

    def test_original_lead_not_mutated(self, raw_lead):
        """enrich_lead must return a new instance; original stays unchanged."""
        original_status = raw_lead.status
        enrich_lead(raw_lead)
        assert raw_lead.status == original_status

    # Edge case 1: unknown industry should not raise
    def test_unknown_industry_uses_fallback(self, raw_lead):
        """An industry not in the lookup table must fall back gracefully."""
        data = raw_lead.model_dump()
        data["industry"] = "Quantum Blockchain AI"
        unknown = Lead(**data)
        result = enrich_lead(unknown)
        assert result.tech_stack
        assert result.company_description

    # Edge case 2: pre-filled fields must not be overwritten
    def test_existing_tech_stack_preserved(self, raw_lead):
        """If tech_stack is already set, enrichment must not overwrite it."""
        data = raw_lead.model_dump()
        data["tech_stack"] = "Custom Proprietary Stack"
        prefilled = Lead(**data)
        result = enrich_lead(prefilled)
        assert result.tech_stack == "Custom Proprietary Stack"

    # Error case: batch must survive individual failures without crashing
    def test_batch_returns_all_leads_on_partial_failure(self, raw_lead, monkeypatch):
        """A failure in one lead must not abort the entire batch."""
        original_fn = enrichment_module.enrich_lead
        call_count = {"n": 0}

        def fail_first(lead):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("Simulated enrichment failure")
            return original_fn(lead)

        monkeypatch.setattr(enrichment_module, "enrich_lead", fail_first)
        leads = [raw_lead, raw_lead.model_copy(update={"id": "test-005"})]
        results = enrich_batch(leads)
        assert len(results) == 2
