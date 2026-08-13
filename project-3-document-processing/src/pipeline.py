"""End-to-end document processing pipeline runner.

Architecture:

    flowchart LR
        A[Incoming PDF / simulated email] --> B[extractor.extract]
        B --> C[classifier.classify]
        C --> D[registry.register]
        D -->|valid| E[report_generator.generate_report]
        D -->|invalid or unknown type| F[status = NEEDS_REVIEW]
        B -->|failure| G[status = FAILED]
        C -->|failure| G
        E -->|failure| G

Each stage's failure is caught and recorded on the Document itself rather
than raised, so one malformed document in a batch never aborts the rest.

Called by n8n webhook or executed directly:
    python -m src.pipeline --input-dir data/incoming
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from loguru import logger

from .classifier import classify
from .config import Settings
from .exceptions import ClassificationError, ExtractionError, RegistryError, ReportGenerationError
from .extractor import get_extractor, load_document_text
from .models import Document, PipelineResult, ProcessingStatus
from .registry import DocumentRegistry
from .report_generator import generate_report


def process_document(source: str, settings: Settings, registry: DocumentRegistry) -> Document:
    """Run one document through extract -> classify -> register (-> report).

    Never raises: any stage failure is captured on the returned Document
    (status=FAILED, error_message set) so batch processing can continue.
    """
    source_name = Path(source).name
    logger.info(f"Processing document '{source_name}'")

    try:
        raw_text = load_document_text(source)
        extractor = get_extractor(settings)
        extraction = extractor.extract(raw_text, source_name)
    except ExtractionError as exc:
        logger.error(f"'{source_name}' failed extraction: {exc}")
        document = Document(source_name=source_name, status=ProcessingStatus.FAILED, error_message=str(exc))
        registry.register(document)
        return document

    try:
        classification = classify(extraction)
    except ClassificationError as exc:
        logger.error(f"'{source_name}' failed classification: {exc}")
        document = Document(
            source_name=source_name,
            status=ProcessingStatus.FAILED,
            extraction=extraction,
            error_message=str(exc),
        )
        registry.register(document)
        return document

    document = Document(
        source_name=source_name,
        document_type=classification.document_type,
        status=ProcessingStatus.CLASSIFIED,
        extraction=extraction,
        classification=classification,
    )

    if not classification.is_valid:
        logger.warning(f"'{source_name}' needs review — missing fields: {classification.missing_fields}")
        document.status = ProcessingStatus.NEEDS_REVIEW
        try:
            registry.register(document)
        except RegistryError as exc:
            logger.error(f"'{source_name}' failed to register: {exc}")
            document.status = ProcessingStatus.FAILED
            document.error_message = str(exc)
        return document

    try:
        registry.register(document)
    except RegistryError as exc:
        logger.error(f"'{source_name}' failed to register: {exc}")
        document.status = ProcessingStatus.FAILED
        document.error_message = str(exc)
        return document

    try:
        document.status = ProcessingStatus.REPORTED
        document.processed_at = datetime.utcnow()
        document.report_path = generate_report(document, settings)
    except ReportGenerationError as exc:
        logger.error(f"'{source_name}' failed report generation: {exc}")
        document.status = ProcessingStatus.FAILED
        document.error_message = str(exc)

    registry.register(document)
    return document


def process_batch(
    sources: list[str], settings: Settings, registry: DocumentRegistry | None = None
) -> PipelineResult:
    """Process a batch of document sources (file paths). Returns a summary.

    A malformed or unreadable document is recorded as FAILED or
    NEEDS_REVIEW and does not stop the rest of the batch from processing.
    """
    owns_registry = registry is None
    registry = registry or DocumentRegistry(settings.registry_db_path)

    try:
        documents = [process_document(source, settings, registry) for source in sources]
    finally:
        if owns_registry:
            registry.close()

    result = PipelineResult(
        total_documents=len(documents),
        registered=sum(
            1 for d in documents if d.status in (ProcessingStatus.REGISTERED, ProcessingStatus.REPORTED)
        ),
        reported=sum(1 for d in documents if d.status == ProcessingStatus.REPORTED),
        needs_review=sum(1 for d in documents if d.status == ProcessingStatus.NEEDS_REVIEW),
        failed=sum(1 for d in documents if d.status == ProcessingStatus.FAILED),
        output_dir=settings.output_dir,
    )

    logger.info(
        f"Batch complete — {result.reported} reported, {result.needs_review} need review, "
        f"{result.failed} failed (of {result.total_documents})"
    )
    return result


if __name__ == "__main__":
    import argparse

    from .config import setup_logging
    from .config import settings as default_settings

    parser = argparse.ArgumentParser(description="Document processing pipeline")
    parser.add_argument("--input-dir", type=Path, default=Path(default_settings.incoming_dir))
    args = parser.parse_args()

    setup_logging(default_settings.log_level)
    sources = [str(p) for p in sorted(args.input_dir.iterdir()) if p.suffix.lower() in (".pdf", ".json", ".txt")]
    process_batch(sources, default_settings)
