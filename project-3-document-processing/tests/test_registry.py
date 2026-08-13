"""Tests for src/registry.py

Coverage per module: 1 happy path, 2 edge cases, 1 error case.
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.exceptions import RegistryError
from src.models import Document, DocumentType, ProcessingStatus
from src.registry import DocumentRegistry


def _make_document(**overrides) -> Document:
    defaults = dict(
        source_name="invoice_001.pdf",
        document_type=DocumentType.INVOICE,
        status=ProcessingStatus.REPORTED,
    )
    defaults.update(overrides)
    return Document(**defaults)


class TestDocumentRegistry:
    def test_happy_path_register_and_get(self, tmp_path: Path):
        registry = DocumentRegistry(str(tmp_path / "registry.db"))
        document = _make_document()
        registry.register(document)
        fetched = registry.get(document.id)
        registry.close()

        assert fetched is not None
        assert fetched.source_name == "invoice_001.pdf"
        assert fetched.status == ProcessingStatus.REPORTED

    # Edge case 1: query filters by status
    def test_query_filters_by_status(self, tmp_path: Path):
        registry = DocumentRegistry(str(tmp_path / "registry.db"))
        registry.register(_make_document(status=ProcessingStatus.REPORTED))
        registry.register(_make_document(status=ProcessingStatus.NEEDS_REVIEW))
        reported = registry.query(status=ProcessingStatus.REPORTED)
        registry.close()

        assert len(reported) == 1
        assert reported[0].status == ProcessingStatus.REPORTED

    # Edge case 2: query filters by document type and creation date range
    def test_query_filters_by_type_and_date(self, tmp_path: Path):
        registry = DocumentRegistry(str(tmp_path / "registry.db"))
        old_doc = _make_document(
            document_type=DocumentType.RECEIPT, created_at=datetime.utcnow() - timedelta(days=30)
        )
        new_doc = _make_document(document_type=DocumentType.RECEIPT)
        registry.register(old_doc)
        registry.register(new_doc)

        recent = registry.query(
            document_type=DocumentType.RECEIPT, date_from=datetime.utcnow() - timedelta(days=1)
        )
        registry.close()

        assert len(recent) == 1
        assert recent[0].id == new_doc.id

    # Error case: a database connection failure raises RegistryError
    def test_connection_failure_raises_registry_error(self, monkeypatch, tmp_path: Path):
        def fail_connect(*_args, **_kwargs):
            raise sqlite3.Error("simulated failure")

        monkeypatch.setattr(sqlite3, "connect", fail_connect)
        with pytest.raises(RegistryError):
            DocumentRegistry(str(tmp_path / "registry.db"))
