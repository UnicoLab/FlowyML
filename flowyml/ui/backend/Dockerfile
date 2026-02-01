# =============================================================================
# FlowyML Backend - Multi-Stage Optimized Dockerfile
# =============================================================================
# This Dockerfile uses multi-stage builds to create a minimal, secure, and
# optimized production image. Build artifacts and dev tools are excluded.
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies and build the application
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS builder

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.8.2 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

# Add Poetry to PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && chmod +x $POETRY_HOME/bin/poetry

# Copy only dependency files first (better layer caching)
COPY pyproject.toml poetry.lock ./

# Install dependencies only (no dev dependencies for production)
RUN poetry install --only main --no-root --no-directory

# Copy application source
COPY README.md ./
COPY flowyml ./flowyml

# Install the application package
RUN poetry install --only main

# -----------------------------------------------------------------------------
# Stage 2: Runtime - Minimal production image
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Security: Run as non-root user
RUN groupadd --gid 1000 flowyml \
    && useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home flowyml

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app" \
    # Application defaults
    FLOWYML_ENV=production \
    FLOWYML_HOST=0.0.0.0 \
    FLOWYML_PORT=8080

WORKDIR /app

# Install runtime dependencies only (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --from=builder /build/flowyml ./flowyml
COPY --from=builder /build/README.md ./

# Create data directories with correct permissions
RUN mkdir -p /app/data /app/artifacts \
    && chown -R flowyml:flowyml /app

# Switch to non-root user
USER flowyml

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Run the application with uvicorn
CMD ["uvicorn", "flowyml.ui.backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
