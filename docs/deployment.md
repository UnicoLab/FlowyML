# Deployment Guide

flowyml is designed to be flexible, supporting both local execution and centralized deployment for teams. This guide covers how to deploy flowyml as a centralized hub using Docker.

## Centralized Hub Deployment

A centralized hub allows your team to share pipelines, runs, and artifacts. It consists of the flowyml backend (API & Orchestrator) and the frontend (UI).

### Prerequisites

- Docker
- Docker Compose

### Quick Start

1. **Clone the repository** (or use your fork):
   ```bash
   git clone https://github.com/unicolab/flowyml.git
   cd flowyml
   ```

2. **Start the services**:
   ```bash
   docker-compose up -d
   ```

   This will start:
   - **Backend** on port `8000`
   - **Frontend** on port `8080`

3. **Access the UI**:
   Open your browser and navigate to `http://localhost:8080`.

### Configuration

You can configure the deployment by setting environment variables in `docker-compose.yml` or a `.env` file.

| Variable | Description | Default |
|----------|-------------|---------|
| `flowyml_HOME` | Path to flowyml data directory | `/root/.flowyml` |
| `flowyml_UI_HOST` | Host to bind the backend to | `0.0.0.0` |
| `flowyml_UI_PORT` | Port for the backend API | `8000` |

### Data Persistence

The `docker-compose.yml` mounts a volume for data persistence:
```yaml
volumes:
  - ./.flowyml:/root/.flowyml
```
This ensures that your metadata database, artifacts, and logs are preserved across restarts.

## Client Configuration

To connect your local flowyml CLI or UI to the centralized hub, you need to configure the execution mode.

### Using the CLI

1. **Set the execution mode to remote**:
   ```bash
   flowyml config set-mode remote
   ```

2. **Set the remote server URL**:
   ```bash
   flowyml config set-url --server http://<hub-ip>:8000 --ui http://<hub-ip>:8080
   ```
   Replace `<hub-ip>` with the IP address or hostname of your centralized hub.

3. **Verify configuration**:
   ```bash
   flowyml config show
   ```

### Using Environment Variables

You can also configure the client using environment variables:

```bash
export flowyml_EXECUTION_MODE=remote
export flowyml_REMOTE_SERVER_URL=http://<hub-ip>:8000
export flowyml_REMOTE_UI_URL=http://<hub-ip>:8080
```

## Production Considerations

- **Security**: The default setup does not include authentication. For production use, ensure the hub is deployed within a private network (VPN/VPC) or behind a secure proxy with authentication (e.g., Nginx with Basic Auth, OAuth2 Proxy).
- **Storage**: For heavy workloads, consider using an external database (PostgreSQL) and object storage (S3) instead of the default SQLite and local file system. (See Advanced Configuration).
- **Scalability**: The default backend runs a single worker. For high concurrency, you may need to scale the backend service or use a more robust task queue (e.g., Celery/Redis).
