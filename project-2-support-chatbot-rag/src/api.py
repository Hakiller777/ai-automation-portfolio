"""Flask HTTP API — exposes the RAG support chatbot as REST endpoints for n8n.

Endpoints:
  GET  /health  — health check (Docker HEALTHCHECK + Railway probe)
  POST /ingest  — (re)build the vector store from data/knowledge_base/
  POST /query   — body: { "question": "..." } → AgentResponse
"""

from __future__ import annotations

import os

from flask import Flask, jsonify, request
from loguru import logger

from .agent import generate_answer
from .config import settings
from .exceptions import AgentError, IngestionError, RetrievalError
from .ingestion import ingest_documents
from .retrieval import retrieve

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "rag-support-chatbot"})


@app.route("/ingest", methods=["POST"])
def ingest():
    logger.info("POST /ingest")
    try:
        result = ingest_documents(settings)
        return jsonify({"status": "success", "result": result.model_dump(mode="json")}), 200
    except IngestionError as exc:
        logger.error(f"POST /ingest failed: {exc}")
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/query", methods=["POST"])
def query():
    body = request.get_json(silent=True) or {}
    question = body.get("question", "")
    logger.info(f"POST /query — question='{question[:60]}'")

    if not question.strip():
        return jsonify({"status": "error", "message": "'question' is required"}), 400

    try:
        chunks = retrieve(question, settings)
        response = generate_answer(question, chunks, settings)
        return jsonify({"status": "success", "result": response.model_dump(mode="json")}), 200
    except (RetrievalError, AgentError) as exc:
        logger.error(f"POST /query failed: {exc}")
        return jsonify({"status": "error", "message": str(exc)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    app.run(host="0.0.0.0", port=port, debug=False)
