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
    && poetry install --no-interaction --no-ansi --no-root

# Copy application code
COPY flowyml ./flowyml
COPY README.md ./

# Install the package itself
RUN poetry install --no-interaction --no-ansi

# Create directories for data
RUN mkdir -p .flowyml/artifacts .flowyml/metadata

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "-m", "flowyml.ui.backend.main"]
