# =============================================================================
# FlowyML Unified Dockerfile
# =============================================================================
# Multi-stage build for unified Backend + Frontend deployment
# Produces a single container serving both API and UI on port 8080.

# ============ Stage 1: Frontend Build ============
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

COPY flowyml/ui/frontend/package*.json ./
RUN npm ci --no-audit --no-fund

COPY flowyml/ui/frontend/ ./
RUN npm run build

# ============ Stage 2: Runtime (Backend + Frontend Assets) ============
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry (pinned version for reproducible builds)
ENV POETRY_VERSION=1.8.4
RUN curl -sSL https://install.python-poetry.org | python3 - --version ${POETRY_VERSION}
ENV PATH="/root/.local/bin:$PATH"

# Copy configuration
COPY pyproject.toml poetry.lock ./

# Install dependencies (--without dev excludes test/lint deps)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root --without dev \
    && pip install --no-cache-dir uvicorn[standard] python-multipart

# Copy Backend Code
COPY flowyml ./flowyml
COPY README.md ./

# Install the package itself
RUN poetry install --no-interaction --no-ansi --only-root

# Copy Frontend Build Artifacts (from Stage 1)
# File structure: /app/flowyml/ui/backend/main.py → serves /app/flowyml/ui/frontend/dist/
RUN mkdir -p flowyml/ui/frontend/dist
COPY --from=frontend-builder /app/frontend/dist ./flowyml/ui/frontend/dist

# Create directories for data persistence
RUN mkdir -p .flowyml/artifacts .flowyml/metadata

# Environment Variables
ENV FLOWYML_ENV=production
ENV SERVER_PORT=8080

# Expose port
EXPOSE 8080

# Health check — matches the /api/health endpoint used by Cloud Run / App Runner / Container Apps
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Run the application
CMD ["uvicorn", "flowyml.ui.backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
