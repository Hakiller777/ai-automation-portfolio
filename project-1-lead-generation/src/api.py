"""Flask HTTP API — exposes lead generation pipeline as REST endpoint for n8n.

Endpoints:
  GET  /health  — health check (Docker HEALTHCHECK + Railway probe)
  POST /run     — trigger full pipeline; body: { "input_file": "path/to.csv" }
"""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, request
from loguru import logger

from .config import settings
from .pipeline import run_pipeline

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "lead-generation-pipeline"})


@app.route("/run", methods=["POST"])
def run():
    body = request.get_json(silent=True) or {}
    input_file = body.get("input_file", "data/sample_leads.csv")
    logger.info(f"POST /run — input_file={input_file}")
    try:
        result = run_pipeline(Path(input_file), settings)
        return jsonify({"status": "success", "result": result.model_dump(mode="json")}), 200
    except Exception as exc:
        logger.error(f"POST /run failed: {exc}")
        return jsonify({"status": "error", "message": str(exc)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
