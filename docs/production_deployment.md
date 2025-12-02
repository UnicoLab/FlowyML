# 🚀 Production Deployment Guide

Deploy FlowyML as a centralized ML orchestration hub for your team or organization. This guide covers everything from local deployment to enterprise-scale production setups.

---

## 📋 Overview

FlowyML can be deployed in multiple configurations:

- **🖥️ Local Development**: Run on your laptop for development and testing
- **🏢 Team Deployment**: Centralized server for team collaboration
- **☁️ Cloud Production**: Scalable deployment on AWS, GCP, or Azure
- **🐳 Docker Stack**: Containerized deployment with Docker Compose

---

## 🎯 Quick Start

### Using Docker Compose (Recommended)

The fastest way to get FlowyML running in production with PostgreSQL:

```bash
# Clone and navigate to the repository
git clone https://github.com/your-org/flowyml.git
cd flowyml

# Configure environment (copy and edit .env)
cp .env.example .env
# Edit .env and set secure passwords:
# - POSTGRES_PASSWORD
# - FLOWYML_AUTH_SECRET

# Start the complete stack
make docker-up

# View logs
make docker-logs

# Access the UI
open http://localhost:80
```

**What you get**:
- ✅ PostgreSQL 15 database with persistent storage
- ✅ Backend API on port 8080
- ✅ Frontend UI on port 80
- ✅ Health checks and auto-restart
- ✅ Production-ready configuration

---

## 🗄️ Database Configuration

FlowyML uses SQLAlchemy for database operations, supporting both SQLite and PostgreSQL.

### SQLite (Default)

Perfect for small teams and development environments:

```bash
# Local file (default)
export FLOWYML_DATABASE_URL="sqlite:////app/data/metadata.db"

# Or use the metadata path directly
export FLOWYML_METADATA_DB="/app/data/metadata.db"
```

**✅ Pros**:
- Zero configuration required
- Built-in with Python
- Perfect for single-server deployments

**⚠️ Cons**:
- Not suitable for high concurrency
- Single point of failure
- Limited to file system storage

### PostgreSQL (Production)

Recommended for production deployments with multiple users:

```bash
export FLOWYML_DATABASE_URL="postgresql://user:password@postgres-host:5432/flowyml"
```

**Example with Cloud Providers**:

```bash
# AWS RDS
export FLOWYML_DATABASE_URL="postgresql://admin:SecurePass@flowyml.abc123.us-east-1.rds.amazonaws.com:5432/flowyml"

# Google Cloud SQL
export FLOWYML_DATABASE_URL="postgresql://postgres:SecurePass@/flowyml?host=/cloudsql/project:region:instance"

# Azure Database for PostgreSQL
export FLOWYML_DATABASE_URL="postgresql://admin@server:SecurePass@server.postgres.database.azure.com:5432/flowyml?sslmode=require"
```

**✅ Pros**:
- Production-grade reliability
- Built-in replication and backups
- Excellent concurrency support
- Advanced query optimization

**Configuration Best Practices**:
- Use connection pooling (handled automatically by SQLAlchemy)
- Enable SSL/TLS for cloud deployments
- Set up automated backups
- Configure read replicas for high-traffic scenarios

---

## 🌐 Remote Server Configuration

Configure FlowyML clients to connect to your centralized server.

### Backend URL Configuration

Set the backend API URL that clients will connect to:

```bash
# Production server (HTTPS recommended)
export FLOWYML_REMOTE_SERVER_URL="https://flowyml-api.yourcompany.com"

# Development/staging
export FLOWYML_REMOTE_SERVER_URL="http://dev-flowyml.internal:8080"

# Local Docker deployment
export FLOWYML_REMOTE_SERVER_URL="http://localhost:8080"
```

### Frontend UI Configuration

Set the publicly accessible UI URL:

```bash
# Production
export FLOWYML_REMOTE_UI_URL="https://flowyml.yourcompany.com"

# Development
export FLOWYML_REMOTE_UI_URL="http://localhost:3000"
```

### Client Configuration

Configure your local FlowyML clients to use the remote server:

```bash
# Use the CLI to configure remote execution
flowyml config set remote-server https://flowyml-api.yourcompany.com
flowyml config set remote-ui https://flowyml.yourcompany.com

# Set your API token
flowyml config set api-token your_api_token_here

# Verify configuration
flowyml config show
```

**Example `~/.flowyml/config.yaml`**:

```yaml
remote_server_url: https://flowyml-api.yourcompany.com
remote_ui_url: https://flowyml.yourcompany.com
api_token: uf_abc123xyz789...
execution_mode: remote
```

---

## 🐳 Docker Deployment

### Docker Compose Setup

The `docker-compose.yml` is pre-configured for production use:

```yaml
version: '3.8'

services:
  backend:
    image: flowyml/backend:latest
    ports:
      - "8080:8080"
    environment:
      # Database configuration
      FLOWYML_DATABASE_URL: ${FLOWYML_DATABASE_URL:-sqlite:////app/data/metadata.db}

      # Remote URLs for client configuration
      FLOWYML_REMOTE_SERVER_URL: ${FLOWYML_REMOTE_SERVER_URL:-http://localhost:8080}
      FLOWYML_REMOTE_UI_URL: ${FLOWYML_REMOTE_UI_URL:-http://localhost:80}

      # Authentication
      FLOWYML_AUTH_SECRET: ${FLOWYML_AUTH_SECRET:-change-this-in-production}

    volumes:
      - metadata:/app/data
      - artifacts:/app/artifacts
    restart: unless-stopped

  frontend:
    image: flowyml/frontend:latest
    ports:
      - "80:80"
    environment:
      VITE_API_URL: ${FLOWYML_REMOTE_SERVER_URL:-http://localhost:8080}
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  metadata:
    driver: local
  artifacts:
    driver: local
```

### Environment Variables Reference

Create a `.env` file in your project root:

```bash
# ============================================================================
# Database Configuration
# ============================================================================

# Option 1: Use full database URL (recommended)
FLOWYML_DATABASE_URL=postgresql://user:password@db-host:5432/flowyml

# Option 2: Use SQLite with custom path (fallback)
# FLOWYML_METADATA_DB=/app/data/metadata.db

# ============================================================================
# Remote Server Configuration
# ============================================================================

# Public URL for API server (used by clients)
FLOWYML_REMOTE_SERVER_URL=https://flowyml-api.yourcompany.com

# Public URL for frontend UI
FLOWYML_REMOTE_UI_URL=https://flowyml.yourcompany.com

# ============================================================================
# Storage Configuration
# ============================================================================

# Artifact storage directory
FLOWYML_ARTIFACTS_DIR=/app/artifacts

# ============================================================================
# Authentication & Security
# ============================================================================

# Secret key for JWT token signing (CHANGE THIS!)
FLOWYML_AUTH_SECRET=your-super-secret-key-change-this

# API token for initial admin access
FLOWYML_API_TOKEN=uf_initial_admin_token

# ============================================================================
# Optional: Cloud Storage (S3, GCS, Azure Blob)
# ============================================================================

# AWS S3
# FLOWYML_ARTIFACT_STORE=s3
# AWS_ACCESS_KEY_ID=your-key
# AWS_SECRET_ACCESS_KEY=your-secret
# FLOWYML_S3_BUCKET=flowyml-artifacts
# FLOWYML_S3_REGION=us-east-1

# Google Cloud Storage
# FLOWYML_ARTIFACT_STORE=gcs
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
# FLOWYML_GCS_BUCKET=flowyml-artifacts

# Azure Blob Storage
# FLOWYML_ARTIFACT_STORE=azure
# AZURE_STORAGE_CONNECTION_STRING=your-connection-string
# FLOWYML_AZURE_CONTAINER=flowyml-artifacts
```

### Makefile Commands

Use the provided Makefile for easy Docker management:

```bash
# Build images
make docker-build

# Start services
make docker-up

# Stop services
make docker-down

# View logs
make docker-logs

# Clean everything (including volumes)
make docker-clean

# Restart services
make docker-restart

# Show running containers
make docker-ps
```

---

## 🔐 Security & Authentication

### Token-Based Authentication

FlowyML uses JWT tokens for API authentication.

#### Create Initial Admin Token

```bash
# Via Docker
docker exec -it flowyml-backend flowyml token create --name "Admin Token" --admin

# Via local installation
flowyml token create --name "Admin Token" --admin
```

#### Token Management

```bash
# List all tokens
flowyml token list

# Create project-scoped token
flowyml token create --name "ML Project" --project ml-platform --permissions read,write,execute

# Revoke a token
flowyml token revoke <token-id>

# Rotate tokens regularly (best practice)
flowyml token rotate <token-id>
```

#### API Authentication

Include the token in API requests:

```bash
# Using curl
curl -H "Authorization: Bearer uf_your_token_here" \
  https://flowyml-api.yourcompany.com/api/pipelines

# Using Python
import requests

headers = {"Authorization": "Bearer uf_your_token_here"}
response = requests.get(
    "https://flowyml-api.yourcompany.com/api/pipelines",
    headers=headers
)
```

### Security Best Practices

> [!IMPORTANT]
> - **Change default secrets**: Always set custom `FLOWYML_AUTH_SECRET` in production
> - **Use HTTPS**: Enable SSL/TLS for all production deployments
> - **Token rotation**: Rotate API tokens regularly (every 90 days recommended)
> - **Least privilege**: Grant minimum required permissions to tokens
> - **Network security**: Use firewalls and VPCs to restrict access

---

## ☁️ Cloud Deployment

### AWS Deployment

#### Using Docker on EC2

```bash
# 1. Launch EC2 instance (t3.medium or larger)
# 2. Install Docker and Docker Compose
sudo yum install -y docker
sudo systemctl start docker
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 3. Clone FlowyML
git clone https://github.com/your-org/flowyml.git
cd flowyml

# 4. Configure environment
cat > .env <<EOF
FLOWYML_DATABASE_URL=postgresql://admin:password@flowyml-db.abc123.us-east-1.rds.amazonaws.com:5432/flowyml
FLOWYML_REMOTE_SERVER_URL=https://flowyml-api.yourcompany.com
FLOWYML_REMOTE_UI_URL=https://flowyml.yourcompany.com
FLOWYML_AUTH_SECRET=$(openssl rand -hex 32)
EOF

# 5. Start services
docker-compose up -d

# 6. Configure load balancer (ALB) pointing to port 8080
```

#### Using AWS ECS/Fargate

```bash
# Use the provided task definitions
# Deploy backend and frontend as separate services
# Configure Application Load Balancer
# Use RDS for PostgreSQL
# Use S3 for artifact storage
```

### Google Cloud Platform

#### Using Cloud Run

```bash
# 1. Build and push images
gcloud builds submit --tag gcr.io/PROJECT_ID/flowyml-backend
gcloud builds submit --tag gcr.io/PROJECT_ID/flowyml-frontend

# 2. Deploy backend
gcloud run deploy flowyml-backend \
  --image gcr.io/PROJECT_ID/flowyml-backend \
  --platform managed \
  --region us-central1 \
  --set-env-vars FLOWYML_DATABASE_URL=postgresql://user:pass@/db?host=/cloudsql/PROJECT:REGION:INSTANCE

# 3. Deploy frontend
gcloud run deploy flowyml-frontend \
  --image gcr.io/PROJECT_ID/flowyml-frontend \
  --platform managed \
  --region us-central1 \
  --set-env-vars VITE_API_URL=https://flowyml-backend-xxx.run.app
```

### Azure Deployment

#### Using Azure Container Instances

```bash
# 1. Create resource group
az group create --name flowyml-rg --location eastus

# 2. Create PostgreSQL database
az postgres server create \
  --resource-group flowyml-rg \
  --name flowyml-db \
  --location eastus \
  --admin-user flowyml \
  --admin-password SecurePassword123! \
  --sku-name B_Gen5_1

# 3. Deploy container instances
az container create \
  --resource-group flowyml-rg \
  --name flowyml-backend \
  --image flowyml/backend:latest \
  --dns-name-label flowyml-api \
  --ports 8080 \
  --environment-variables \
    FLOWYML_DATABASE_URL=postgresql://flowyml:SecurePassword123!@flowyml-db.postgres.database.azure.com:5432/flowyml
```

---

## 📊 Monitoring & Observability

### Health Checks

FlowyML provides health check endpoints:

```bash
# Backend health
curl https://flowyml-api.yourcompany.com/health

# Database connectivity
curl https://flowyml-api.yourcompany.com/health/db

# Metrics endpoint
curl https://flowyml-api.yourcompany.com/api/metrics/observability/orchestrator
```

### Logging

Configure structured logging:

```python
# In your deployment environment
export FLOWYML_LOG_LEVEL=INFO
export FLOWYML_LOG_FORMAT=json
```

### Metrics Integration

FlowyML exposes metrics for monitoring:

- **Pipeline execution metrics**: Success rate, duration, failure reasons
- **Cache performance**: Hit rate, cache size, eviction stats
- **System metrics**: API response times, database query performance

**Integration with Prometheus**:

```yaml
scrape_configs:
  - job_name: 'flowyml'
    static_configs:
      - targets: ['flowyml-api.yourcompany.com:8080']
    metrics_path: '/metrics'
```

---

## 🔄 Backup & Recovery

### Database Backups

#### PostgreSQL Automated Backups

```bash
# Enable automated backups in RDS/Cloud SQL
# Configure retention period (7-35 days)
# Set backup window during low-traffic hours

# Manual backup
pg_dump -h db-host -U user -d flowyml > backup_$(date +%Y%m%d).sql

# Restore from backup
psql -h db-host -U user -d flowyml < backup_20240615.sql
```

#### SQLite Backups

```bash
# Copy database file
cp /app/data/metadata.db /backups/metadata_$(date +%Y%m%d).db

# Or use sqlite3 backup command
sqlite3 /app/data/metadata.db ".backup /backups/metadata_$(date +%Y%m%d).db"
```

### Artifact Storage Backups

```bash
# Sync artifacts to S3
aws s3 sync /app/artifacts s3://flowyml-backups/artifacts/

# Or use rsync for local backups
rsync -av /app/artifacts/ /backups/artifacts/
```

---

## 🔧 Troubleshooting

### Common Issues

#### Database Connection Errors

```bash
# Check database URL format
echo $FLOWYML_DATABASE_URL

# Test PostgreSQL connection
psql $FLOWYML_DATABASE_URL -c "SELECT 1"

# Check SQLite file permissions
ls -la /app/data/metadata.db
```

#### API Not Accessible

```bash
# Check if backend is running
docker ps | grep backend

# Check backend logs
docker logs flowyml-backend

# Verify port mapping
netstat -tlnp | grep 8080
```

#### Frontend Can't Connect to Backend

```bash
# Check VITE_API_URL in frontend
docker exec flowyml-frontend env | grep VITE_API_URL

# Test API from frontend container
docker exec flowyml-frontend curl http://backend:8080/health
```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
export FLOWYML_DEBUG=true
export FLOWYML_LOG_LEVEL=DEBUG

# Restart services
docker-compose restart
```

---

## 📚 Additional Resources

- **[API Documentation](./API.md)**: Complete API reference
- **[Architecture Guide](./architecture.md)**: System architecture and design
- **[Configuration Reference](./configuration.md)**: All configuration options
- **[Security Guide](./security.md)**: Security best practices

---

## 💡 Tips & Best Practices

> [!TIP]
> **Performance Optimization**
> - Use PostgreSQL for production deployments
> - Enable connection pooling (default with SQLAlchemy)
> - Configure appropriate cache settings
> - Use CDN for frontend assets

> [!TIP]
> **High Availability**
> - Deploy backend across multiple availability zones
> - Use database read replicas for read-heavy workloads
> - Implement load balancing with health checks
> - Configure auto-scaling based on metrics

> [!TIP]
> **Cost Optimization**
> - Start with smaller instance sizes and scale up
> - Use spot instances for development/staging
> - Implement artifact lifecycle policies
> - Monitor and optimize database query performance

---

## 🆘 Getting Help

- **GitHub Issues**: [Report bugs and request features](https://github.com/your-org/flowyml/issues)
- **Documentation**: [Browse full documentation](https://flowyml.readthedocs.io)
- **Community**: [Join our Slack community](https://flowyml-community.slack.com)
- **Enterprise Support**: [Contact us](mailto:support@flowyml.com)
