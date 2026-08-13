"""Output report generation — structured JSON (default) or a simple PDF summary."""

from __future__ import annotations

from pathlib import Path

from loguru import logger
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from .config import Settings
from .exceptions import ReportGenerationError
from .models import Document


def _generate_json_report(document: Document, output_dir: Path) -> Path:
    path = output_dir / f"{document.id}.json"
    path.write_text(document.model_dump_json(indent=2), encoding="utf-8")
    return path


def _generate_pdf_report(document: Document, output_dir: Path) -> Path:
    path = output_dir / f"{document.id}.pdf"
    extraction = document.extraction

    c = canvas.Canvas(str(path), pagesize=letter)
    _, height = letter
    y = height - 72

    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, y, f"{document.document_type.value.replace('_', ' ').upper()} SUMMARY")
    y -= 28

    c.setFont("Helvetica", 10)
    lines = [
        f"Document ID: {document.id}",
        f"Source: {document.source_name}",
        f"Reference Number: {extraction.invoice_number if extraction else 'N/A'}",
        f"Vendor: {extraction.vendor_name if extraction else 'N/A'}",
        f"Total: ${extraction.total:.2f}" if extraction and extraction.total is not None else "Total: N/A",
    ]
    for line in lines:
        c.drawString(72, y, line)
        y -= 16

    c.save()
    return path


def generate_report(document: Document, settings: Settings) -> str:
    """Generate an output report for a validated document. Returns the file path.

    Raises ReportGenerationError if the document has no extraction data or
    writing the report fails.
    """
    if document.extraction is None:
        raise ReportGenerationError(
            f"Cannot generate report for '{document.source_name}': no extraction data"
        )

    output_dir = Path(settings.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        if settings.report_format == "pdf":
            path = _generate_pdf_report(document, output_dir)
        else:
            path = _generate_json_report(document, output_dir)
        logger.info(f"Report generated for {document.id} at {path}")
        return str(path)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Report generation failed for {document.id}: {exc}")
        raise ReportGenerationError(f"Report generation failed: {exc}") from exc
