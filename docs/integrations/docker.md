# Docker Integration 🐳

Containerize your pipelines for reproducible execution anywhere.

> [!NOTE]
> **What you'll learn**: How to run pipelines in isolated Docker containers
>
> **Key insight**: Eliminate "it works on my machine" bugs forever.

## Why Use Docker?

- **Isolation**: Each step runs in its own clean environment.
- **Reproducibility**: The exact same code and dependencies run in dev, staging, and prod.
- **Portability**: Move from local Docker to Kubernetes or Cloud without code changes.

## 🐳 Running on Docker

UniFlow can automatically build and run your steps in Docker containers.

### Configuration

```python
from uniflow.integrations.docker import DockerOrchestrator

# Run pipeline in Docker
pipeline.run(
    orchestrator=DockerOrchestrator(
        image="python:3.9-slim",  # Base image
        install_deps=True         # Auto-install requirements.txt
    )
)
```

## 🛠 Custom Dockerfiles

For complex dependencies, provide your own Dockerfile.

```python
orchestrator = DockerOrchestrator(
    dockerfile="./Dockerfile",
    build_context="."
)
```

### Example Dockerfile

```dockerfile
FROM python:3.9
RUN apt-get update && apt-get install -y gcc
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . /app
WORKDIR /app
```
