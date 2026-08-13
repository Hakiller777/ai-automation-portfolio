"""Document classification: infer type from raw text and validate required fields."""

from __future__ import annotations

from loguru import logger

from .exceptions import ClassificationError
from .models import ClassificationResult, DocumentType, ExtractionResult

_REQUIRED_FIELDS: dict[DocumentType, list[str]] = {
    DocumentType.INVOICE: ["invoice_number", "invoice_date", "vendor_name", "total"],
    DocumentType.RECEIPT: ["vendor_name", "invoice_date", "total"],
    DocumentType.PURCHASE_ORDER: ["invoice_number", "vendor_name"],
    DocumentType.UNKNOWN: [],
}

# Order matters: more specific keywords are checked before the generic "invoice".
_TYPE_KEYWORDS: list[tuple[DocumentType, list[str]]] = [
    (DocumentType.PURCHASE_ORDER, ["purchase order", "po number"]),
    (DocumentType.RECEIPT, ["receipt"]),
    (DocumentType.INVOICE, ["invoice"]),
]


def detect_document_type(raw_text: str) -> DocumentType:
    """Infer the document type from keywords in the raw text."""
    lowered = raw_text.lower()
    for doc_type, keywords in _TYPE_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return doc_type
    return DocumentType.UNKNOWN


def _missing_fields(extraction: ExtractionResult, required: list[str]) -> list[str]:
    return [field for field in required if not getattr(extraction, field, None)]


def classify(extraction: ExtractionResult) -> ClassificationResult:
    """Classify a document and validate it has the minimum required fields.

    Returns is_valid=False (with missing_fields populated) rather than
    raising when required data is absent — that's an expected outcome for a
    malformed document, not a bug. The caller decides what to do with an
    invalid classification (e.g. route to manual review).
    """
    logger.info(f"Classifying document '{extraction.source_name}'")
    try:
        doc_type = detect_document_type(extraction.raw_text)
        required = _REQUIRED_FIELDS[doc_type]
        missing = _missing_fields(extraction, required)

        if doc_type == DocumentType.PURCHASE_ORDER and not extraction.line_items:
            missing.append("line_items")

        is_valid = doc_type != DocumentType.UNKNOWN and not missing
        confidence = max(0.0, 1.0 - 0.2 * len(missing)) if doc_type != DocumentType.UNKNOWN else 0.0

        result = ClassificationResult(
            document_type=doc_type,
            confidence=confidence,
            missing_fields=missing,
            is_valid=is_valid,
        )
        logger.info(
            f"Classified '{extraction.source_name}' as {doc_type.value} "
            f"(valid={is_valid}, confidence={confidence:.2f}, missing={missing})"
        )
        return result
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Classification failed for '{extraction.source_name}': {exc}")
        raise ClassificationError(f"Classification failed: {exc}") from exc
