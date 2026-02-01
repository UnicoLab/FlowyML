# =============================================================================
# FlowyML Unified Dockerfile
# =============================================================================
# Multi-stage build for unified Backend + Frontend deployment

# ============ Stage 1: Frontend Build ============
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

COPY flowyml/ui/frontend/package*.json ./
RUN npm install

COPY flowyml/ui/frontend/ ./
RUN npm run build

# ============ Stage 2: Runtime (Backend + Frontend Assets) ============
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

# Copy configuration
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root \
    && pip install uvicorn[standard]  # Ensure uvicorn is installed

# Copy Backend Code
COPY flowyml ./flowyml
COPY README.md ./

# Install the package itself
RUN poetry install --no-interaction --no-ansi

# Copy Frontend Build Artifacts (from Stage 1)
# Note: main.py expects static files at ../frontend/dist relative to backend/main.py
# File structure in container:
# /app/flowyml/ui/backend/main.py
# /app/flowyml/ui/frontend/dist/
RUN mkdir -p flowyml/ui/frontend/dist
COPY --from=frontend-builder /app/frontend/dist ./flowyml/ui/frontend/dist

# Create directories for data
RUN mkdir -p .flowyml/artifacts .flowyml/metadata

# Environment Variables
ENV FLOWYML_ENV=production
ENV SERVER_PORT=8080

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "-m", "flowyml.ui.backend.main"]
