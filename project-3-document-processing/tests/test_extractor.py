"""Tests for src/extractor.py

Coverage per module: 1 happy path, 2 edge cases, 1 error case.
"""

from pathlib import Path

import pytest

from src.exceptions import ExtractionError
from src.extractor import load_document_text


class TestRegexDocumentExtractor:
    def test_happy_path_extracts_all_fields(self, invoice_extraction):
        assert invoice_extraction.invoice_number == "INV-2026-0001"
        assert invoice_extraction.invoice_date == "2026-06-01"
        assert invoice_extraction.vendor_name == "CloudStack Solutions LLC"
        assert invoice_extraction.customer_email == "billing@acmeretail.com"
        assert invoice_extraction.total == 1886.82
        assert len(invoice_extraction.line_items) == 3

    # Edge case 1: empty text does not crash, returns all-None / empty fields
    def test_empty_text_returns_empty_result(self, extractor):
        result = extractor.extract("", "blank.pdf")
        assert result.invoice_number is None
        assert result.line_items == []
        assert result.total is None

    # Edge case 2: line item amount/quantity produce a sane derived unit price
    def test_line_items_compute_unit_price(self, invoice_extraction):
        hosting = next(li for li in invoice_extraction.line_items if "Cloud Hosting" in li.description)
        assert hosting.quantity == 2
        assert hosting.amount == 1200.00
        assert hosting.unit_price == 600.00

    # Error case: unreadable/corrupt PDF bytes raise ExtractionError
    def test_corrupt_pdf_raises_extraction_error(self, tmp_path: Path):
        bad_pdf = tmp_path / "corrupt.pdf"
        bad_pdf.write_bytes(b"%PDF-1.4 this is not a valid pdf structure")
        with pytest.raises(ExtractionError):
            load_document_text(bad_pdf)
