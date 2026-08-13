"""Application settings and structured logging setup."""

import sys
from pathlib import Path

from loguru import logger
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration read from environment variables / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Extraction backend: "mock" (default, deterministic regex, zero cost)
    # or "claude" (documented production path, not wired up in this demo)
    extraction_backend: str = "mock"
    claude_model: str = "claude-opus-4-8"

    # n8n webhook endpoint (simulated for demo)
    n8n_webhook_url: str = "http://n8n:5678/webhook/document-processing"

    # Application behaviour
    log_level: str = "INFO"

    # Storage
    incoming_dir: str = "data/incoming"
    output_dir: str = "data/output"
    registry_db_path: str = "data/registry.db"

    # Report generation: "json" (default) or "pdf"
    report_format: str = "json"

    # Classification
    min_classification_confidence: float = 0.5


def setup_logging(log_level: str = "INFO") -> None:
    """Configure loguru for stdout + rotating file output."""
    logger.remove()
    logger.add(
        sys.stdout,
        level=log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        colorize=True,
    )
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    logger.add(
        log_dir / "document_processing.log",
        level=log_level,
        rotation="10 MB",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}",
    )


settings = Settings()
