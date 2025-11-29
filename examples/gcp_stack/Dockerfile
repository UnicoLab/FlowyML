# Example Dockerfile for flowyml GCP Pipelines

FROM python:3.11-slim

# Set environment variables
ENV PYTHONUN BUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Install flowyml
RUN pip install flowyml

# Copy application code
COPY . /app
WORKDIR /app

# Set entrypoint
ENTRYPOINT ["python"]
CMD ["-m", "flowyml.cli.run"]
