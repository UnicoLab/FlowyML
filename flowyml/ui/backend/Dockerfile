FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

# Copy project files
COPY pyproject.toml poetry.lock ./
COPY README.md ./
COPY flowyml ./flowyml

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Install the package itself
RUN pip install .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "flowyml.ui.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
