"""Pydantic data models for the document processing / invoicing pipeline."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    INVOICE = "invoice"
    RECEIPT = "receipt"
    PURCHASE_ORDER = "purchase_order"
    UNKNOWN = "unknown"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    EXTRACTED = "extracted"
    CLASSIFIED = "classified"
    NEEDS_REVIEW = "needs_review"
    REGISTERED = "registered"
    REPORTED = "reported"
    FAILED = "failed"


class LineItem(BaseModel):
    """A single billable line on an invoice, receipt, or purchase order."""

    description: str
    quantity: int = Field(ge=1)
    unit_price: float = Field(ge=0)
    amount: float = Field(ge=0)


class ExtractionResult(BaseModel):
    """Structured fields pulled from a document's raw text by an extractor."""

    source_name: str
    raw_text: str
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_address: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    line_items: list[LineItem] = Field(default_factory=list)
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    extracted_at: datetime = Field(default_factory=datetime.utcnow)


class ClassificationResult(BaseModel):
    """Output of the classification step for a single document."""

    document_type: DocumentType
    confidence: float = Field(ge=0.0, le=1.0)
    missing_fields: list[str] = Field(default_factory=list)
    is_valid: bool


class Document(BaseModel):
    """Aggregate domain entity persisted in the registry."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_name: str
    document_type: DocumentType = DocumentType.UNKNOWN
    status: ProcessingStatus = ProcessingStatus.PENDING
    extraction: Optional[ExtractionResult] = None
    classification: Optional[ClassificationResult] = None
    report_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None


class PipelineResult(BaseModel):
    """Summary report produced at the end of a batch processing run."""

    total_documents: int
    registered: int
    reported: int
    needs_review: int
    failed: int
    output_dir: str
    processed_at: datetime = Field(default_factory=datetime.utcnow)
