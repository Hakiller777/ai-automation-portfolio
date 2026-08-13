"""Shared pytest fixtures for the project-3 document processing test suite."""

from pathlib import Path

import pytest

from src.config import Settings
from src.extractor import RegexDocumentExtractor
from src.models import ExtractionResult

INVOICE_TEXT = """INVOICE

Invoice Number: INV-2026-0001
Invoice Date: 2026-06-01
Due Date: 2026-06-15
Vendor: CloudStack Solutions LLC
Vendor Address: 500 Market St, San Francisco, CA 94105
Bill To: Acme Retail Group
Customer Email: billing@acmeretail.com

Line Items:
2 x Cloud Hosting - Standard Plan $1200.00
3 x Support Hours (Priority) $450.00
1 x SSL Certificate Renewal $89.00

Subtotal: $1739.00
Tax (8.5%): $147.82
Total Due: $1886.82
"""

RECEIPT_TEXT = """RECEIPT

Receipt Number: RCT-88213
Transaction Date: 2026-06-10
Vendor: Blue Bean Coffee Roasters
Vendor Address: 12 Elm Street, Portland, OR 97201

1 x Espresso Blend (12oz bag) $14.50
2 x Ceramic Mug $9.00

Subtotal: $32.50
Tax: $2.60
Total: $35.10
"""

PURCHASE_ORDER_TEXT = """PURCHASE ORDER

PO Number: PO-4471
Vendor: Nordic Office Supplies AB
Vendor Address: Sveavagen 10, Stockholm, Sweden

5 x Ergonomic Office Chair $220.00
10 x Standing Desk Converter $95.00

Subtotal: $2050.00
Tax: $0.00
Total: $2050.00
"""

INCOMPLETE_INVOICE_TEXT = """INVOICE

Invoice Number: INV-2026-0099
Invoice Date: 2026-06-20

Line Items:
1 x Miscellaneous Consulting Services $500.00
"""

UNRELATED_TEXT = "Hi team, quick reminder that the office lunch is moved to 1pm on Friday. See you there!"


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    """Settings pointed at isolated incoming/output/registry paths under tmp_path."""
    return Settings(
        incoming_dir=str(tmp_path / "incoming"),
        output_dir=str(tmp_path / "output"),
        registry_db_path=str(tmp_path / "registry.db"),
    )


@pytest.fixture
def extractor() -> RegexDocumentExtractor:
    return RegexDocumentExtractor()


@pytest.fixture
def invoice_extraction(extractor: RegexDocumentExtractor) -> ExtractionResult:
    return extractor.extract(INVOICE_TEXT, "invoice_001.pdf")


@pytest.fixture
def receipt_extraction(extractor: RegexDocumentExtractor) -> ExtractionResult:
    return extractor.extract(RECEIPT_TEXT, "receipt_001.pdf")


@pytest.fixture
def purchase_order_extraction(extractor: RegexDocumentExtractor) -> ExtractionResult:
    return extractor.extract(PURCHASE_ORDER_TEXT, "po_001.pdf")


@pytest.fixture
def incomplete_invoice_extraction(extractor: RegexDocumentExtractor) -> ExtractionResult:
    return extractor.extract(INCOMPLETE_INVOICE_TEXT, "invoice_incomplete.pdf")
