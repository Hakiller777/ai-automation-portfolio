"""Application settings and structured logging setup."""

import sys
from pathlib import Path

from loguru import logger
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration read from environment variables / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # AI model used for scoring and outreach (simulated in tests)
    claude_model: str = "claude-opus-4-8"

    # PostgreSQL connection (matches docker-compose service name)
    database_url: str = "postgresql://n8n:n8n@postgres:5432/leads"

    # n8n webhook endpoint (simulated for demo)
    n8n_webhook_url: str = "http://n8n:5678/webhook/leads"

    # Application behaviour
    log_level: str = "INFO"
    batch_size: int = 10

    # Scoring thresholds
    min_score_threshold: int = 4   # leads below this are disqualified
    hot_threshold: int = 8         # score >= 8 → "hot"
    warm_threshold: int = 5        # score >= 5 → "warm", else "cold"


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
        log_dir / "pipeline.log",
        level=log_level,
        rotation="10 MB",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}",
    )


settings = Settings()
