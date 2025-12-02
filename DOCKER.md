# FlowyML Docker Deployment

Quick reference for deploying FlowyML with Docker Compose.

## 🚀 Quick Start

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env and set secure passwords
# At minimum, change: POSTGRES_PASSWORD and FLOWYML_AUTH_SECRET

# 3. Start the stack
make docker-up

# 4. Access FlowyML
# - Frontend UI: http://localhost:80
# - Backend API: http://localhost:8080
```

## 📦 What's Included

- **PostgreSQL 15**: Production-ready database with persistent storage
- **FlowyML Backend**: API server on port 8080
- **FlowyML Frontend**: Web UI on port 80

## 🔧 Configuration

### Essential Settings

Edit `.env` file:

```bash
# Security (REQUIRED)
POSTGRES_PASSWORD=your-secure-database-password
FLOWYML_AUTH_SECRET=$(openssl rand -hex 32)

# URLs (for remote access)
FLOWYML_REMOTE_SERVER_URL=https://your-domain.com:8080
FLOWYML_REMOTE_UI_URL=https://your-domain.com
```

### Switch to SQLite (Development)

To use SQLite instead of PostgreSQL:

```bash
# In .env file
FLOWYML_DATABASE_URL=sqlite:////app/data/metadata.db

# Then restart
make docker-down
make docker-up
```

## 📊 Database Management

### Access PostgreSQL

```bash
# Connect to database
docker exec -it flowyml-postgres psql -U flowyml -d flowyml

# Create backup
docker exec flowyml-postgres pg_dump -U flowyml flowyml > backup_$(date +%Y%m%d).sql

# Restore from backup
docker exec -i flowyml-postgres psql -U flowyml -d flowyml < backup.sql
```

### View Database Logs

```bash
docker logs flowyml-postgres
```

## 🛠️ Makefile Commands

```bash
make docker-build      # Build images
make docker-up         # Start services
make docker-down       # Stop services
make docker-logs       # View logs
make docker-restart    # Restart services
make docker-ps         # Show status
make docker-clean      # Stop and remove volumes
```

## 🔍 Health Checks

```bash
# Backend health
curl http://localhost:8080/health

# Database health
docker exec flowyml-postgres pg_isready -U flowyml
```

## 📁 Data Persistence

Data is stored in Docker volumes:

- `postgres_data`: PostgreSQL database
- `metadata`: SQLite files (if used)
- `artifacts`: Pipeline artifacts

## 🆘 Troubleshooting

### Backend won't start

```bash
# Check backend logs
docker logs flowyml-backend

# Ensure PostgreSQL is healthy
docker ps --filter name=postgres
docker logs flowyml-postgres
```

### Can't connect to database

```bash
# Verify database URL
docker exec flowyml-backend env | grep DATABASE_URL

# Test connection
docker exec flowyml-backend python -c "
from sqlalchemy import create_engine
import os
engine = create_engine(os.environ['FLOWYML_DATABASE_URL'])
print('Connected:', engine.connect())
"
```

### Reset everything

```bash
# Warning: This will delete all data!
make docker-clean
make docker-up
```

## 📚 More Documentation

- [Production Deployment Guide](docs/production_deployment.md)
- [Configuration Reference](docs/configuration.md)
- [API Documentation](docs/API.md)
