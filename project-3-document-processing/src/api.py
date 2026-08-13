"""Flask HTTP API — exposes the document processing pipeline as REST endpoints for n8n.

Endpoints:
  GET  /health              — health check (Docker HEALTHCHECK + Railway probe)
  POST /process             — body: { "sources": ["data/incoming/invoice_1001.pdf", ...] }
                               defaults to every file in settings.incoming_dir
  GET  /documents           — query by status/document_type (query params)
  GET  /documents/<doc_id>  — fetch a single document
"""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, request
from loguru import logger

from .config import settings
from .exceptions import RegistryError
from .models import DocumentType, ProcessingStatus
from .pipeline import process_batch
from .registry import DocumentRegistry

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "document-processing-pipeline"})


@app.route("/process", methods=["POST"])
def process():
    body = request.get_json(silent=True) or {}
    sources = body.get("sources")
    if not sources:
        incoming_dir = Path(settings.incoming_dir)
        sources = [str(p) for p in sorted(incoming_dir.iterdir())] if incoming_dir.exists() else []

    logger.info(f"POST /process — {len(sources)} source(s)")
    try:
        result = process_batch(sources, settings)
        return jsonify({"status": "success", "result": result.model_dump(mode="json")}), 200
    except Exception as exc:  # noqa: BLE001
        logger.error(f"POST /process failed: {exc}")
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/documents", methods=["GET"])
def list_documents():
    status = request.args.get("status")
    document_type = request.args.get("document_type")
    logger.info(f"GET /documents — status={status} document_type={document_type}")

    registry = DocumentRegistry(settings.registry_db_path)
    try:
        documents = registry.query(
            status=ProcessingStatus(status) if status else None,
            document_type=DocumentType(document_type) if document_type else None,
        )
        return jsonify({"status": "success", "result": [d.model_dump(mode="json") for d in documents]}), 200
    except (RegistryError, ValueError) as exc:
        logger.error(f"GET /documents failed: {exc}")
        return jsonify({"status": "error", "message": str(exc)}), 400
    finally:
        registry.close()


@app.route("/documents/<doc_id>", methods=["GET"])
def get_document(doc_id: str):
    logger.info(f"GET /documents/{doc_id}")

    registry = DocumentRegistry(settings.registry_db_path)
    try:
        document = registry.get(doc_id)
        if document is None:
            return jsonify({"status": "error", "message": "Document not found"}), 404
        return jsonify({"status": "success", "result": document.model_dump(mode="json")}), 200
    except RegistryError as exc:
        logger.error(f"GET /documents/{doc_id} failed: {exc}")
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        registry.close()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8002))
    app.run(host="0.0.0.0", port=port, debug=False)
