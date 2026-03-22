# FlowyML Deployment Guide

Deploy FlowyML to any cloud or run locally with Docker Compose. All methods use the same unified Docker image (backend + frontend in one container).

---

## Quick Start — Docker Compose (Local)

```bash
# Clone and start all services (Postgres, FlowyML, Prometheus, Grafana)
docker compose up -d

# Access:
#   FlowyML UI:  http://localhost:8080
#   Grafana:     http://localhost:3001  (admin/admin)
#   Prometheus:  http://localhost:9090
```

To customize, copy `.env.example` → `.env` and edit values.

---

## Build the Docker Image

```bash
# Build unified image
docker build -t flowyml:latest .

# Test locally
docker run -p 8080:8080 flowyml:latest
```

---

## GCP — Cloud Run + Cloud SQL

**Services**: Cloud Run v2, Cloud SQL (Postgres 15), Secret Manager, Artifact Registry, VPC

### Prerequisites
- GCP project with billing enabled
- `gcloud` CLI authenticated
- Terraform ≥ 1.5

### Deploy

```bash
cd infra/gcp

# 1. Configure
cp terraform.tfvars.secret.example terraform.tfvars.secret
# Edit terraform.tfvars.secret with your values

# 2. Build & push image
export REGION=europe-west1
export PROJECT_ID=your-project-id
gcloud auth configure-docker ${REGION}-docker.pkg.dev
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/flowyml/flowyml:latest ../../
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/flowyml/flowyml:latest

# 3. Deploy infrastructure
terraform init
terraform plan -var-file=terraform.tfvars.secret
terraform apply -var-file=terraform.tfvars.secret

# 4. Get URL
terraform output app_url
```

### Cost Estimate
- Cloud Run: ~$0/mo (scale to zero, CPU idle throttling)
- Cloud SQL (db-f1-micro): ~$7/mo
- **Total: ~$7-10/mo** (idle)

---

## AWS — App Runner + RDS

**Services**: App Runner, RDS PostgreSQL, ECR, Secrets Manager, VPC

### Prerequisites
- AWS account with IAM permissions
- `aws` CLI configured
- Terraform ≥ 1.5

### Deploy

```bash
cd infra/aws

# 1. Configure
cp terraform.tfvars.secret.example terraform.tfvars.secret
# Edit terraform.tfvars.secret with your values

# 2. Create ECR repo & push image
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
docker build -t <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/flowyml:latest ../../
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/flowyml:latest

# 3. Deploy infrastructure
terraform init
terraform plan -var-file=terraform.tfvars.secret
terraform apply -var-file=terraform.tfvars.secret

# 4. Get URL
terraform output app_url
```

### Cost Estimate
- App Runner: ~$5/mo (scale to zero)
- RDS (db.t3.micro): ~$15/mo
- NAT Gateway: ~$30/mo
- **Total: ~$50/mo**

---

## Azure — Container Apps + PostgreSQL Flexible Server

**Services**: Container Apps, PostgreSQL Flexible Server, ACR, Key Vault, VNet, Log Analytics

### Prerequisites
- Azure subscription
- `az` CLI authenticated
- Terraform ≥ 1.5

### Deploy

```bash
cd infra/azure

# 1. Configure
cp terraform.tfvars.secret.example terraform.tfvars.secret
# Edit terraform.tfvars.secret with your values

# 2. Create ACR & push image
az acr login --name flowymlacr
docker build -t flowymlacr.azurecr.io/flowyml:latest ../../
docker push flowymlacr.azurecr.io/flowyml:latest

# 3. Deploy infrastructure
terraform init
terraform plan -var-file=terraform.tfvars.secret
terraform apply -var-file=terraform.tfvars.secret

# 4. Get URL
terraform output app_url
```

### Cost Estimate
- Container Apps: ~$0/mo (scale to zero)
- PostgreSQL Flexible (B1ms): ~$13/mo
- **Total: ~$15-20/mo**

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `FLOWYML_DATABASE_URL` | Yes | PostgreSQL connection string |
| `FLOWYML_AUTH_SECRET` | Yes | JWT signing secret |
| `FLOWYML_API_TOKEN` | No | Static API token for SDK auth |
| `FLOWYML_ADMIN_USER` | No | Admin username (default: `admin`) |
| `FLOWYML_ADMIN_PASSWORD` | Yes | Admin password for UI login |
| `FLOWYML_ENV` | No | `production` or `development` |
| `SERVER_PORT` | No | Port to listen on (default: `8080`) |

---

## Architecture

All deployments follow the same pattern:

```
┌─────────────────────────────────┐
│        Load Balancer / CDN       │
│   (Cloud Run / App Runner / CA)  │
├─────────────────────────────────┤
│     FlowyML Unified Container    │
│  ┌───────────┐  ┌─────────────┐ │
│  │  FastAPI   │  │   React UI  │ │
│  │  Backend   │  │  (static)   │ │
│  └─────┬─────┘  └─────────────┘ │
├────────┼────────────────────────┤
│        │ Private VPC             │
│  ┌─────▼─────┐                   │
│  │ PostgreSQL │                   │
│  └───────────┘                   │
└─────────────────────────────────┘
```
