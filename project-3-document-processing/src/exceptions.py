"""Custom exception hierarchy for the document processing pipeline."""


class ExtractionError(Exception):
    """Raised when a document's fields cannot be extracted."""


class ClassificationError(Exception):
    """Raised when a document cannot be classified or validated."""


class RegistryError(Exception):
    """Raised when the document registry cannot be read or written."""


class ReportGenerationError(Exception):
    """Raised when an output report cannot be generated."""
