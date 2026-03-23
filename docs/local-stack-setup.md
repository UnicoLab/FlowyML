# FlowyML Local Stack Setup Guide

This guide explains how to set up and run the complete FlowyML development stack locally using Docker.

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Docker** (v24.0+): [Install Docker](https://docs.docker.com/get-docker/)
- **Docker Compose** (v2.20+): Usually included with Docker Desktop
- **Make** (optional): For convenience commands

Verify your installation:

```bash
docker --version    # Docker version 24.0.0 or higher
docker compose version  # Docker Compose version v2.20.0 or higher
```

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/UnicoLab/FlowyML.git
cd FlowyML
```

### 2. Configure Environment (Optional)

Copy the example environment file and customize if needed:

```bash
cp .env.example .env
# Edit .env to customize settings (optional for development)
```

### 3. Start the Stack

Using Make (recommended):

```bash
make local-deploy
```

Or using Docker Compose directly:

```bash
docker compose up -d
```

### 4. Verify Services

Check that all services are running:

```bash
docker compose ps
```

You should see all containers in "healthy" or "running" state:

| Service    | Port  | Status  |
|------------|-------|---------|
| postgres   | 5432  | healthy |
| backend    | 8080  | healthy |
| frontend   | 80    | running |
| prometheus | 9090  | running |
| grafana    | 3001  | running |

## 🌐 Accessing the Services

Once the stack is running, you can access:

| Service          | URL                        | Credentials          |
|------------------|----------------------------|----------------------|
| **Frontend UI**  | http://localhost:80        | -                    |
| **Backend API**  | http://localhost:8080      | -                    |
| **API Docs**     | http://localhost:8080/docs | -                    |
| **Health Check** | http://localhost:8080/api/health | -              |
| **Metrics**      | http://localhost:8080/metrics | -                 |
| **Prometheus**   | http://localhost:9090      | -                    |
| **Grafana**      | http://localhost:3001      | admin / admin        |

### Verify Backend Health

```bash
curl http://localhost:8080/api/health
# {"status":"ok","version":"0.1.0"}
```

## 🔧 Common Operations

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f frontend
```

### Rebuild Images

After code changes:

```bash
make docker-build
# or
docker compose build --no-cache
```

### Restart Services

```bash
make local-deploy
# or
docker compose up -d --force-recreate
```

### Stop the Stack

```bash
make local-stop
# or
docker compose down
```

### Clean Everything (including volumes)

⚠️ This will delete all data!

```bash
docker compose down -v --remove-orphans
docker system prune -f
```

## 🔐 Configuration

### Environment Variables

Key environment variables can be set in `.env`:

```bash
# Database
POSTGRES_PASSWORD=your_secure_password

# Backend
FLOWYML_AUTH_SECRET=your_auth_secret
FLOWYML_ENV=development

# Ports (if defaults conflict with other services)
FLOWYML_PORT=8080
FLOWYML_UI_PORT=80
GRAFANA_PORT=3001
```

### Port Conflicts

If you have port conflicts, modify the ports in `.env`:

```bash
# Example: Change frontend to port 3000
FLOWYML_UI_PORT=3000

# Example: Change backend to port 8000
FLOWYML_PORT=8000
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Network                            │
│                      (flowyml-network)                           │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Frontend   │    │   Backend    │    │  PostgreSQL  │       │
│  │   (nginx)    │───▶│   (FastAPI)  │───▶│   Database   │       │
│  │   :80        │    │   :8080      │    │   :5432      │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                             │                                    │
│                             ▼                                    │
│  ┌──────────────┐    ┌──────────────┐                           │
│  │   Grafana    │◀───│  Prometheus  │                           │
│  │   :3001      │    │   :9090      │                           │
│  └──────────────┘    └──────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

## 🐛 Troubleshooting

### Container Won't Start

1. Check logs: `docker compose logs backend`
2. Verify PostgreSQL is healthy: `docker compose ps postgres`
3. Ensure ports are free: `lsof -i :8080`

### Database Connection Issues

```bash
# Check PostgreSQL logs
docker compose logs postgres

# Connect to database manually
docker compose exec postgres psql -U flowyml -d flowyml
```

### Frontend Can't Connect to Backend

1. Ensure backend is healthy: `curl http://localhost:8080/api/health`
2. Check CORS settings in backend
3. Verify `VITE_API_URL` environment variable

### Build Failures

```bash
# Clean Docker cache
docker system prune -f
docker builder prune -f

# Rebuild without cache
docker compose build --no-cache
```

### Out of Disk Space

```bash
# Remove unused images and containers
docker system prune -a

# Remove volumes (WARNING: deletes data)
docker volume prune
```

## 📊 Monitoring

### Grafana Dashboards

1. Open http://localhost:3001
2. Login with `admin` / `admin`
3. Navigate to Dashboards → FlowyML

### Prometheus Queries

Access http://localhost:9090 and try these queries:

```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# Latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

## 🔄 Development Workflow

### Hot Reload for Backend

For development with hot reload, run backend locally instead of in Docker:

```bash
# Start only infrastructure
docker compose up -d postgres prometheus grafana

# Run backend locally with Poetry
poetry install
poetry run uvicorn flowyml.ui.backend.main:app --reload --port 8080
```

### Frontend Development

```bash
cd flowyml/ui/frontend
npm install
npm run dev  # Runs on http://localhost:5173 with hot reload
```

## 📚 Additional Resources

- [FlowyML Documentation](https://unicolab.github.io/FlowyML/latest/)
- [API Reference](http://localhost:8080/docs)
- [Contributing Guide](contributing.md)

---

Need help? Open an issue on [GitHub](https://github.com/UnicoLab/FlowyML/issues).
