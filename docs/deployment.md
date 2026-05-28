---
title: Deployment Guide — Ship FlowyML to Production
description: Deploy FlowyML locally, with Docker Compose, or on the cloud. Compare deployment options and get started in minutes.
---

<div class="hero-section" markdown>

## 🚀 Deployment Guide

Deploy FlowyML anywhere — from your laptop to a fully managed cloud cluster. This guide gives you an overview of every deployment option and helps you choose the right path for your team.

<span class="feature-badge">🐳 Docker</span>
<span class="feature-badge">☁️ Cloud</span>
<span class="feature-badge">☸️ Kubernetes</span>
<span class="feature-badge">🏭 Production</span>

</div>

## Deployment Options at a Glance

FlowyML supports a spectrum of deployment strategies — pick the one that matches your team size, infrastructure, and reliability requirements.

| | **Local** | **Docker Compose** | **Cloud (GCP / AWS)** |
|---|---|---|---|
| **Best for** | Solo developers, prototyping | Small teams, on-prem | Large teams, production |
| **Setup time** | < 1 min | ~5 min | ~30 min |
| **Scalability** | Single machine | Single machine / VM | Auto-scaling clusters |
| **Persistence** | Local filesystem | Docker volumes | Managed storage (GCS / S3) |
| **GPU support** | Native (if available) | NVIDIA Container Toolkit | Cloud GPU instances |
| **Auth & security** | None (local only) | Manual (reverse proxy) | IAM, OAuth, VPC |
| **High availability** | ❌ | ❌ | ✅ |
| **Recommended use** | Development | Staging / small prod | Enterprise production |

!!! tip "Not sure where to start?"
    If you're evaluating FlowyML for the first time, start with **Local** execution — zero setup required. When you're ready to share with your team, graduate to **Docker Compose**. For production workloads, follow the **Cloud** guides.

---

## Local Execution

The fastest way to run FlowyML — no containers, no infrastructure. Just install and go.

```bash
# Install FlowyML
pip install flowyml

# Run a pipeline
python my_pipeline.py

# Launch the UI
flowyml ui
```

Local mode stores everything under `~/.flowyml` by default (metadata DB, artifacts, logs). Great for development and experimentation.

!!! info "Switching Modes"
    FlowyML defaults to local execution. You can switch to remote mode at any time:
    ```bash
    flowyml config set-mode remote
    flowyml config set-url --server http://<hub-ip>:8000 --ui http://<hub-ip>:8080
    ```

---

## Docker Compose Deployment

A centralized hub deployment allows your team to **share pipelines, runs, and artifacts** through a single server. It consists of the FlowyML backend (API & Orchestrator) and the frontend (UI).

### Prerequisites

- Docker Engine ≥ 20.10
- Docker Compose ≥ 2.0
- (Optional) NVIDIA Container Toolkit for GPU support

### Quick Start with `make`

FlowyML ships with a `Makefile` that wraps all Docker operations for convenience:

```bash
# Clone the repository
git clone https://github.com/unicolab/flowyml.git
cd flowyml
```

<div class="step-timeline" markdown>

<div class="timeline-step" markdown>

#### Step 1 — Build the Images

```bash
make docker-build
```

Builds the backend and frontend Docker images from the project Dockerfiles.

</div>

<div class="timeline-step" markdown>

#### Step 2 — Start the Services

```bash
make docker-up
```

Launches all services in detached mode. The following containers will start:

| Service | Port | Description |
|---------|------|-------------|
| **Backend** | `8000` | REST API & orchestration engine |
| **Frontend** | `8080` | Web dashboard (GUI) |

</div>

<div class="timeline-step" markdown>

#### Step 3 — Verify & Access

```bash
make docker-status   # Check running containers
make docker-logs     # Tail live logs
```

Open your browser at **`http://localhost:8080`** to access the FlowyML dashboard.

</div>

</div>

### Additional Docker Commands

| Command | Description |
|---------|-------------|
| `make docker-build` | Build all Docker images |
| `make docker-up` | Start all services (detached) |
| `make docker-down` | Stop and remove containers |
| `make docker-logs` | Stream logs from all services |
| `make docker-status` | Show running container status |
| `make docker-restart` | Restart all services |

### Configuration

Customize the deployment by setting environment variables in `docker-compose.yml` or a `.env` file:

```bash
# .env
FLOWYML_HOME=/root/.flowyml
FLOWYML_UI_HOST=0.0.0.0
FLOWYML_UI_PORT=8000
FLOWYML_LOG_LEVEL=INFO
FLOWYML_DB_URL=sqlite:///root/.flowyml/metadata.db
```

| Variable | Description | Default |
|----------|-------------|---------|
| `FLOWYML_HOME` | Path to FlowyML data directory | `/root/.flowyml` |
| `FLOWYML_UI_HOST` | Host to bind the backend to | `0.0.0.0` |
| `FLOWYML_UI_PORT` | Port for the backend API | `8000` |
| `FLOWYML_LOG_LEVEL` | Logging verbosity | `INFO` |
| `FLOWYML_DB_URL` | Metadata database URL | SQLite (local) |

### Data Persistence

The `docker-compose.yml` mounts a volume for data persistence:

```yaml
volumes:
  - ./.flowyml:/root/.flowyml
```

This ensures that your metadata database, artifacts, and logs are preserved across container restarts.

!!! warning "Backup Your Data"
    For production deployments, regularly back up the `.flowyml` directory. For high-reliability setups, consider using an external PostgreSQL database and cloud object storage (S3 / GCS) instead of SQLite and local volumes.

---

## Deployment Dashboard

The FlowyML GUI includes a built-in **Deployment Lab** for managing model endpoints directly from the browser:

![FlowyML Deployment Dashboard](screenshots/deployment.png)

**From the Deployment Lab you can:**

- Deploy trained models as REST API endpoints
- Monitor endpoint health with real-time status indicators
- Manage API tokens for secure access
- View deployment logs and manage lifecycle (stop, restart, delete)

[Learn more about the GUI →](gui-overview.md){ .md-button }

---

## Client Configuration

Once your centralized hub is running, point your local CLI or SDK to the remote server.

=== "CLI"

    ```bash
    # Switch to remote execution mode
    flowyml config set-mode remote

    # Point to your hub
    flowyml config set-url \
        --server http://<hub-ip>:8000 \
        --ui http://<hub-ip>:8080

    # Verify
    flowyml config show
    ```

=== "Environment Variables"

    ```bash
    export FLOWYML_EXECUTION_MODE=remote
    export FLOWYML_REMOTE_SERVER_URL=http://<hub-ip>:8000
    export FLOWYML_REMOTE_UI_URL=http://<hub-ip>:8080
    ```

=== "Python SDK"

    ```python
    from flowyml import set_config

    set_config(
        execution_mode="remote",
        server_url="http://<hub-ip>:8000",
        ui_url="http://<hub-ip>:8080"
    )
    ```

---

## Cloud Deployment

For production workloads, deploy FlowyML on managed cloud infrastructure with auto-scaling, GPU support, and enterprise security.

<div class="header-grid" markdown>

<div class="header-card" markdown>

### ☁️ Google Cloud Platform

Deploy on GCP with Vertex AI orchestration, GCS artifact storage, and Cloud Run serving.

[GCP Deployment Guide →](DEPLOYMENT_GCP.md)

</div>

<div class="header-card" markdown>

### 🔐 Secrets Management

Securely manage API keys, credentials, and sensitive configuration across environments.

[Secrets Guide →](deployment/secrets.md)

</div>

</div>

---

## Production Considerations

!!! danger "Security First"
    The default Docker Compose setup does **not** include authentication. For production deployments, you **must** add a security layer.

### Security

- Deploy behind a reverse proxy (Nginx, Traefik, Caddy) with TLS termination
- Add authentication via OAuth2 Proxy, Auth0, or your identity provider
- Restrict network access with VPC / firewall rules
- Rotate API tokens regularly

### Storage & Databases

- Replace SQLite with **PostgreSQL** for concurrent access and reliability
- Use cloud object storage (**GCS**, **S3**, **Azure Blob**) for artifact persistence
- Enable automated backups and point-in-time recovery

### Scalability

- Scale backend workers behind a load balancer
- Use a dedicated task queue (**Celery + Redis**) for pipeline orchestration
- Deploy on **Kubernetes** for auto-scaling and self-healing

### Monitoring

- Export metrics to **Prometheus** / **Grafana** for infrastructure monitoring
- Enable structured logging with **JSON** format for log aggregation
- Set up alerting for failed pipelines, high latency, and resource exhaustion

---

## What's Next?

<div class="header-grid" markdown>

<div class="header-card" markdown>

### 🏭 Production Deployment

Harden your setup with TLS, auth, PostgreSQL, and horizontal scaling.

[Production Guide →](production_deployment.md)

</div>

<div class="header-card" markdown>

### ☁️ GCP Deployment

Step-by-step guide to deploying FlowyML on Google Cloud Platform.

[GCP Guide →](DEPLOYMENT_GCP.md)

</div>

<div class="header-card" markdown>

### 🔐 Secrets Management

Configure secrets, credentials, and environment-specific variables securely.

[Secrets Guide →](deployment/secrets.md)

</div>

</div>
