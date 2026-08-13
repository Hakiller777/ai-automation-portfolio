# ============================================================
# Base Dockerfile — Python 3.11 service
# Used by: root docker-compose.yml (placeholder)
# Each project (project-1/, project-2/, etc.) has its own
# Dockerfile that follows this same pattern with project src/.
# ============================================================

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed by psycopg2 and weasyprint
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (better layer caching)
COPY shared/requirements-base.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Create logs directory
RUN mkdir -p logs

# Non-root user for security
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Placeholder — each project overrides this CMD in its own Dockerfile
CMD ["python", "--version"]
