"""Tests for src/pipeline.py

Coverage per module: 1 happy path, 2 edge cases, 1 error case.
"""

import json
from pathlib import Path

from src.config import Settings
from src.models import ProcessingStatus
from src.pipeline import process_batch, process_document
from src.registry import DocumentRegistry
from tests.conftest import INCOMPLETE_INVOICE_TEXT, INVOICE_TEXT, UNRELATED_TEXT


def _write_email_source(tmp_path: Path, name: str, body: str) -> str:
    """Write a simulated inbound-email JSON document (the `.json` input channel)."""
    path = tmp_path / name
    path.write_text(json.dumps({"from": "vendor@example.com", "subject": name, "body": body}), encoding="utf-8")
    return str(path)


class TestProcessDocument:
    def test_happy_path_valid_invoice_is_reported(self, test_settings: Settings, tmp_path: Path):
        source = _write_email_source(tmp_path, "invoice_valid.json", INVOICE_TEXT)
        registry = DocumentRegistry(test_settings.registry_db_path)
        document = process_document(source, test_settings, registry)
        registry.close()

        assert document.status == ProcessingStatus.REPORTED
        assert document.report_path and Path(document.report_path).exists()

    # Edge case 1: missing required fields routes to NEEDS_REVIEW, no report generated
    def test_incomplete_document_needs_review(self, test_settings: Settings, tmp_path: Path):
        source = _write_email_source(tmp_path, "invoice_incomplete.json", INCOMPLETE_INVOICE_TEXT)
        registry = DocumentRegistry(test_settings.registry_db_path)
        document = process_document(source, test_settings, registry)
        registry.close()

        assert document.status == ProcessingStatus.NEEDS_REVIEW
        assert document.report_path is None

    # Edge case 2: unrecognized document type is also routed to NEEDS_REVIEW, not FAILED
    def test_unrelated_text_needs_review(self, test_settings: Settings, tmp_path: Path):
        source = _write_email_source(tmp_path, "unrelated.json", UNRELATED_TEXT)
        registry = DocumentRegistry(test_settings.registry_db_path)
        document = process_document(source, test_settings, registry)
        registry.close()

        assert document.status == ProcessingStatus.NEEDS_REVIEW


class TestProcessBatch:
    # Error case: a corrupt document in the batch doesn't abort the rest
    def test_batch_survives_corrupt_document(self, test_settings: Settings, tmp_path: Path):
        good_source = _write_email_source(tmp_path, "invoice_ok.json", INVOICE_TEXT)
        corrupt_pdf = tmp_path / "corrupt.pdf"
        corrupt_pdf.write_bytes(b"%PDF-1.4 not a real pdf structure")

        result = process_batch([good_source, str(corrupt_pdf)], test_settings)

        assert result.total_documents == 2
        assert result.reported == 1
        assert result.failed == 1
