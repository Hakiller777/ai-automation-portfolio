"""Tests for src/classifier.py

Coverage per module: 1 happy path, 2 edge cases, 1 error case.
"""

import pytest

import src.classifier as classifier_module
from src.classifier import classify, detect_document_type
from src.exceptions import ClassificationError
from src.models import DocumentType


class TestDetectDocumentType:
    def test_detects_receipt_and_purchase_order(self, receipt_extraction, purchase_order_extraction):
        assert detect_document_type(receipt_extraction.raw_text) == DocumentType.RECEIPT
        assert detect_document_type(purchase_order_extraction.raw_text) == DocumentType.PURCHASE_ORDER


class TestClassify:
    def test_happy_path_valid_invoice(self, invoice_extraction):
        result = classify(invoice_extraction)
        assert result.document_type == DocumentType.INVOICE
        assert result.is_valid is True
        assert result.missing_fields == []

    # Edge case 1: missing required fields marks the document invalid, not an exception
    def test_incomplete_invoice_is_invalid(self, incomplete_invoice_extraction):
        result = classify(incomplete_invoice_extraction)
        assert result.is_valid is False
        assert "vendor_name" in result.missing_fields
        assert "total" in result.missing_fields

    # Edge case 2: unrecognized text classifies as UNKNOWN and is always invalid
    def test_unrelated_text_is_unknown_and_invalid(self, extractor):
        extraction = extractor.extract("Hi team, lunch is at 1pm Friday.", "note.pdf")
        result = classify(extraction)
        assert result.document_type == DocumentType.UNKNOWN
        assert result.is_valid is False

    # Error case: unexpected failure during type detection is wrapped in ClassificationError
    def test_detection_failure_raises_classification_error(self, invoice_extraction, monkeypatch):
        def _boom(_raw_text: str):
            raise RuntimeError("boom")

        monkeypatch.setattr(classifier_module, "detect_document_type", _boom)
        with pytest.raises(ClassificationError):
            classify(invoice_extraction)
