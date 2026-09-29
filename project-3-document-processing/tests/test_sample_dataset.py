"""Guards on the shipped sample dataset.

The unit tests write their own documents, so they prove the pipeline *can*
report a valid invoice and *can* route an incomplete one to review. They say
nothing about whether the bundled `data/incoming/` set actually exercises
both paths end-to-end — including the real PDFs, which no unit test parses.

These tests keep the sample data honest, because the dataset is what the
README and the demo describe.
"""

from pathlib import Path

import pytest

from src.config import Settings
from src.models import DocumentType, ProcessingStatus
from src.pipeline import process_batch, process_document
from src.registry import DocumentRegistry

INCOMING_DIR = Path(__file__).resolve().parent.parent / "data" / "incoming"
SUPPORTED_SUFFIXES = (".pdf", ".json", ".txt")


def _sample_sources() -> list[str]:
    """Collect the shipped documents the same way the pipeline CLI does."""
    return [str(p) for p in sorted(INCOMING_DIR.iterdir()) if p.suffix.lower() in SUPPORTED_SUFFIXES]


@pytest.fixture
def processed_samples(test_settings: Settings):
    """Run every shipped document through the pipeline, keyed by file name."""
    registry = DocumentRegistry(test_settings.registry_db_path)
    try:
        documents = {Path(source).name: process_document(source, test_settings, registry) for source in _sample_sources()}
    finally:
        registry.close()
    return documents


def test_sample_set_has_the_documented_mix():
    """The README promises 10 documents: 4 real PDFs and 6 simulated emails."""
    names = [Path(source).name for source in _sample_sources()]

    assert len(names) == 10
    assert sum(name.endswith(".pdf") for name in names) == 4
    assert sum(name.endswith(".json") for name in names) == 6


def test_batch_over_sample_set_reports_valid_and_routes_the_rest(test_settings: Settings):
    """End-to-end over the real files: 8 reported, 2 set aside, nothing lost."""
    result = process_batch(_sample_sources(), test_settings)

    assert result.total_documents == 10
    assert result.reported == 8
    assert result.needs_review == 2
    assert result.failed == 0


def test_every_sample_pdf_is_parsed_and_reported(processed_samples):
    """No unit test reads a real PDF; this one does, for all four shipped files."""
    pdfs = {name: doc for name, doc in processed_samples.items() if name.endswith(".pdf")}

    assert pdfs, "no sample PDFs were found in data/incoming"
    for name, document in pdfs.items():
        assert document.status == ProcessingStatus.REPORTED, f"{name} was {document.status.value}"
        assert document.report_path and Path(document.report_path).exists()


def test_review_routing_names_the_expected_documents(processed_samples):
    """Only the incomplete invoice and the unrelated email may be set aside."""
    needs_review = {name for name, doc in processed_samples.items() if doc.status == ProcessingStatus.NEEDS_REVIEW}

    assert needs_review == {"email_invoice_incomplete.json", "email_unrelated.json"}
    assert processed_samples["email_unrelated.json"].document_type == DocumentType.UNKNOWN
