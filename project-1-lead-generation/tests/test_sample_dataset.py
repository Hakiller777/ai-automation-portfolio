"""Guards on the shipped sample dataset.

The unit tests build their own leads, so they prove the pipeline *can*
disqualify a lead and *can* survive a bad row. They said nothing about
whether the bundled `data/sample_leads.csv` actually exercises either path —
and for a long time it did not: all 50 leads scored 5-8 against a threshold
of 4, so the demo never showed a disqualification, and no row ever failed
validation.

These tests keep the sample data honest, because the dataset is what the
README and the demo video are describing.
"""

from pathlib import Path

import pytest

from src.config import settings
from src.enrichment import enrich_batch
from src.models import LeadStatus
from src.pipeline import load_leads
from src.scoring import score_batch

SAMPLE_CSV = Path(__file__).resolve().parent.parent / "data" / "sample_leads.csv"


@pytest.fixture(scope="module")
def scored_sample():
    """Load and score the real shipped dataset once."""
    leads = load_leads(SAMPLE_CSV)
    updated, results = score_batch(enrich_batch(leads))
    return updated, results


def test_malformed_row_is_skipped_not_fatal():
    """The deliberately corrupt row must be dropped without killing the load."""
    raw_lines = SAMPLE_CSV.read_text(encoding="utf-8").strip().splitlines()
    data_rows = len(raw_lines) - 1  # minus header

    leads = load_leads(SAMPLE_CSV)

    assert leads, "load_leads returned nothing — the whole batch aborted"
    assert len(leads) == data_rows - 1, (
        f"Expected exactly one row to fail validation and be skipped, but "
        f"{data_rows - len(leads)} of {data_rows} rows were dropped"
    )


def test_sample_data_exercises_disqualification(scored_sample):
    """At least one shipped lead must fall below the score threshold.

    Without this, the disqualification feature is real in code but invisible
    in the demo — the README promises filtering that a viewer never sees.
    """
    updated, results = scored_sample
    disqualified = [lead for lead in updated if lead.status == LeadStatus.DISQUALIFIED]

    assert disqualified, (
        "No lead in sample_leads.csv scores below "
        f"{settings.min_score_threshold}, so the disqualification path is "
        "never demonstrated. Add at least one poor-fit lead."
    )


def test_sample_data_covers_every_tier(scored_sample):
    """The dataset should show the full hot/warm/cold spread, not just two."""
    _, results = scored_sample
    tiers = {result.qualification_tier for result in results}

    assert tiers == {"hot", "warm", "cold"}, (
        f"Sample data only produces {sorted(tiers)}. A scoring demo that never "
        "produces a cold lead makes the tiering look decorative."
    )


def test_every_loaded_lead_gets_a_score(scored_sample):
    """No lead may come out of the batch unscored."""
    updated, results = scored_sample

    assert len(results) == len(updated)
    assert all(lead.score is not None for lead in updated)
    assert all(1 <= result.score <= 10 for result in results)
