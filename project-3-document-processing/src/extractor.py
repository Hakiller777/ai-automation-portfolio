"""Document field extraction — pluggable backend (mock vs Claude API).

`load_document_text` normalizes three simulated input channels into plain
text: a real PDF attachment (parsed with pypdf), a simulated inbound email
(JSON with a `body` field), or a plain text/raw string handed in directly.

`DocumentExtractor` is the pluggable interface every backend implements.
`RegexDocumentExtractor` is the default — deterministic, offline, zero cost —
and is what the demo runs. `ClaudeDocumentExtractor` documents the production
path (a real Claude API call) but is intentionally left unimplemented so the
demo never incurs API cost; swap the backend via EXTRACTION_BACKEND=claude.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from pathlib import Path

from loguru import logger
from pypdf import PdfReader

from .config import Settings
from .exceptions import ExtractionError
from .models import ExtractionResult, LineItem

_FIELD_PATTERNS: dict[str, re.Pattern[str]] = {
    "invoice_number": re.compile(
        r"(?:Invoice Number|Invoice #|PO Number|Receipt Number)\s*:\s*(\S+)", re.IGNORECASE
    ),
    "invoice_date": re.compile(
        r"(?:Invoice Date|Transaction Date|Date)\s*:\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE
    ),
    "due_date": re.compile(r"Due Date\s*:\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE),
    "vendor_name": re.compile(r"Vendor\s*:\s*(.+)", re.IGNORECASE),
    "vendor_address": re.compile(r"Vendor Address\s*:\s*(.+)", re.IGNORECASE),
    "customer_name": re.compile(r"Bill To\s*:\s*(.+)", re.IGNORECASE),
    "customer_email": re.compile(r"Customer Email\s*:\s*(\S+@\S+)", re.IGNORECASE),
}

_LINE_ITEM_RE = re.compile(r"^\s*(\d+)\s*x\s+(.+?)\s+\$([\d,]+\.\d{2})\s*$", re.MULTILINE | re.IGNORECASE)
_SUBTOTAL_RE = re.compile(r"Subtotal\s*:\s*\$([\d,]+\.\d{2})", re.IGNORECASE)
_TAX_RE = re.compile(r"Tax[^:\n]*:\s*\$([\d,]+\.\d{2})", re.IGNORECASE)
# Negative lookbehind keeps this from matching the "total" inside "Subtotal".
_TOTAL_RE = re.compile(r"(?<!Sub)(?:Total Due|Total)\s*:\s*\$([\d,]+\.\d{2})", re.IGNORECASE)


def load_document_text(source: str | Path) -> str:
    """Load raw text from a real PDF, a simulated email JSON, or plain text.

    - `.pdf` files are parsed with pypdf.
    - `.json` files are treated as a simulated inbound email and must expose
      a `body` (or `raw_text`) field holding the document text.
    - Anything else that exists on disk is read as plain text.
    - A string that isn't an existing path is returned unchanged (lets
      callers pass raw text directly, e.g. from tests).

    Raises ExtractionError if a recognized file exists but cannot be parsed.
    """
    path = Path(source)
    if not path.exists():
        return str(source)

    suffix = path.suffix.lower()
    try:
        if suffix == ".pdf":
            reader = PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        if suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            text = data.get("body") or data.get("raw_text")
            if not text:
                raise ValueError("JSON document has no 'body' or 'raw_text' field")
            return text
        return path.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        raise ExtractionError(f"Failed to load document '{path}': {exc}") from exc


class DocumentExtractor(ABC):
    """Interface for pulling structured fields out of raw document text."""

    @abstractmethod
    def extract(self, raw_text: str, source_name: str) -> ExtractionResult:
        """Extract structured fields from `raw_text` originating from `source_name`."""


class RegexDocumentExtractor(DocumentExtractor):
    """Deterministic, offline extractor using regex over plain text.

    No API calls or ML models — works on whatever `load_document_text`
    produces (a real PDF's extracted text or a simulated email body). This
    is the default backend so the demo runs at zero cost.
    """

    def extract(self, raw_text: str, source_name: str) -> ExtractionResult:
        logger.info(f"Extracting fields from '{source_name}' ({len(raw_text)} chars)")
        try:
            fields = {
                name: (match.group(1).strip() if (match := pattern.search(raw_text)) else None)
                for name, pattern in _FIELD_PATTERNS.items()
            }

            line_items = [
                LineItem(
                    description=desc.strip(),
                    quantity=int(qty),
                    unit_price=round(float(amount.replace(",", "")) / int(qty), 2),
                    amount=float(amount.replace(",", "")),
                )
                for qty, desc, amount in _LINE_ITEM_RE.findall(raw_text)
            ]

            subtotal_match = _SUBTOTAL_RE.search(raw_text)
            tax_match = _TAX_RE.search(raw_text)
            total_match = _TOTAL_RE.search(raw_text)

            result = ExtractionResult(
                source_name=source_name,
                raw_text=raw_text,
                line_items=line_items,
                subtotal=float(subtotal_match.group(1).replace(",", "")) if subtotal_match else None,
                tax=float(tax_match.group(1).replace(",", "")) if tax_match else None,
                total=float(total_match.group(1).replace(",", "")) if total_match else None,
                **fields,
            )
            logger.info(f"Extraction complete for '{source_name}' — {len(line_items)} line item(s)")
            return result
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Extraction failed for '{source_name}': {exc}")
            raise ExtractionError(f"Extraction failed for '{source_name}': {exc}") from exc


class ClaudeDocumentExtractor(DocumentExtractor):
    """Production extraction backend — Claude API (NOT executed in this demo).

    In production, send the raw document text (or the PDF itself as a
    document content block) to Claude with a structured-output prompt or a
    tool-use schema matching `ExtractionResult`, and parse the JSON response.
    Requires a real ANTHROPIC_API_KEY. Select it with EXTRACTION_BACKEND=claude
    in `.env`. Left unimplemented here to guarantee the demo runs at zero
    API cost — wire up `anthropic.Anthropic().messages.create(...)` in
    `extract()` for production use.
    """

    def extract(self, raw_text: str, source_name: str) -> ExtractionResult:
        raise NotImplementedError(
            "ClaudeDocumentExtractor is a documented production path and is not "
            "wired up in this demo. Set EXTRACTION_BACKEND=mock (default) to use "
            "the deterministic regex extractor."
        )


def get_extractor(settings: Settings) -> DocumentExtractor:
    """Factory: select the extraction backend from settings.extraction_backend."""
    if settings.extraction_backend == "claude":
        return ClaudeDocumentExtractor()
    return RegexDocumentExtractor()
