"""Document registry — SQLite-backed persistence with query by status/type/date."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from loguru import logger

from .exceptions import RegistryError
from .models import Document, DocumentType, ProcessingStatus

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    document_type TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    data TEXT NOT NULL
);
"""


class DocumentRegistry:
    """Thin persistence layer over a SQLite file, storing each Document as JSON.

    SQLite (rather than a bare JSON file) gives indexed queries by status,
    type, and date range without loading the whole registry into memory.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        try:
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
            self._conn.execute(_SCHEMA)
            self._conn.commit()
        except sqlite3.Error as exc:
            raise RegistryError(f"Failed to open registry at '{db_path}': {exc}") from exc

    def register(self, document: Document) -> str:
        """Insert or update a document, returning its id."""
        try:
            self._conn.execute(
                "INSERT INTO documents (id, source_name, document_type, status, created_at, data) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET "
                "source_name=excluded.source_name, document_type=excluded.document_type, "
                "status=excluded.status, data=excluded.data",
                (
                    document.id,
                    document.source_name,
                    document.document_type.value,
                    document.status.value,
                    document.created_at.isoformat(),
                    document.model_dump_json(),
                ),
            )
            self._conn.commit()
            logger.info(
                f"Registered document {document.id} ({document.source_name}) — status={document.status.value}"
            )
            return document.id
        except sqlite3.Error as exc:
            logger.error(f"Failed to register document {document.id}: {exc}")
            raise RegistryError(f"Failed to register document: {exc}") from exc

    def get(self, document_id: str) -> Document | None:
        """Fetch a single document by id, or None if it doesn't exist."""
        try:
            row = self._conn.execute(
                "SELECT data FROM documents WHERE id = ?", (document_id,)
            ).fetchone()
            return Document.model_validate_json(row[0]) if row else None
        except sqlite3.Error as exc:
            raise RegistryError(f"Failed to fetch document '{document_id}': {exc}") from exc

    def query(
        self,
        status: ProcessingStatus | None = None,
        document_type: DocumentType | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[Document]:
        """Query documents, optionally filtered by status, type, and/or creation date range."""
        clauses: list[str] = []
        params: list[str] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(status.value)
        if document_type is not None:
            clauses.append("document_type = ?")
            params.append(document_type.value)
        if date_from is not None:
            clauses.append("created_at >= ?")
            params.append(date_from.isoformat())
        if date_to is not None:
            clauses.append("created_at <= ?")
            params.append(date_to.isoformat())

        sql = "SELECT data FROM documents"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at DESC"

        try:
            rows = self._conn.execute(sql, params).fetchall()
            return [Document.model_validate_json(row[0]) for row in rows]
        except sqlite3.Error as exc:
            raise RegistryError(f"Registry query failed: {exc}") from exc

    def close(self) -> None:
        self._conn.close()
