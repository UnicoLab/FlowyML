# 🚀 Deploying FlowyML Central Instance to GCP

This guide provides a step-by-step tutorial on how to deploy a centralized FlowyML instance to Google Cloud Platform (GCP) using **Terraform** for infrastructure and **Make** for automation.

We have adopted industry best practices including **Artifact Registry** for Docker images and **Private Service Access** for secure Cloud SQL connections.

## 🏗️ Architecture Overview

The deployment provisions:
- **Cloud Run (Unified)**: Single service for Backend API and Frontend Assets.
- **Artifact Registry**: Secure storage for Docker images.
- **Cloud SQL (PostgreSQL)**: Persistent store for metadata.
- **Secret Manager**: Secure storage for database passwords and API tokens.
- **VPC & Private IP**: Secure private networking.

---

## 📋 Prerequisites

1. **GCP Project**: Create a project and note the `PROJECT_ID`.
2. **Local Tools**:
   - [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud`)
   - [Terraform](https://developer.hashicorp.com/terraform/downloads) (>= 1.5)
   - [Docker](https://docs.docker.com/get-docker/)
3. **Authentication**:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```
4. **Enable APIs** (Optional, Terraform does this, but good for first run):
   ```bash
   gcloud services enable artifactregistry.googleapis.com run.googleapis.com sqladmin.googleapis.com servicenetworking.googleapis.com
   ```

---

## 🛠️ Step 1: Configuration & Secrets

FlowyML uses a secret file to manage sensitive infrastructure variables.

1. Initialize the secret file from the template:
   ```bash
   make gcp-setup-secrets
   ```

2. Edit the newly created `infra/gcp/terraform.tfvars.secret` with your real values.
   - **Pro Tip**: Use the `make gcp-setup-secrets` command output to locate the file.
   - `project_id`: Your actual GCP project ID.
   - `db_password`: A strong password for the PostgreSQL instance.
   - `auth_secret`: A long random string for JWT signing.
   - `api_token`: A static token you'll use to connect your local scripts.

---

## 🚀 Step 2: Deployment with Make

We've automated the entire pipeline in the root `Makefile`.

1. **Build and Push Docker Images**:
   This will create a Google Artifact Registry repository named `flowyml` and push your images there.
   ```bash
   make gcp-push GCP_PROJECT=your-project-id GCP_REGION=europe-west1
   ```

2. **Full Deployment**:
   This command runs `gcp-push` (which includes build), initializes Terraform, plans, and applies the infrastructure changes.
   ```bash
   make gcp-deploy GCP_PROJECT=your-project-id GCP_REGION=europe-west1
   ```

> **Note**: The first deployment might take 10-15 minutes as it provisions a Cloud SQL database and sets up private networking.

---

## 🔗 Step 3: Connect Locally

Once deployed, Terraform will output your **Backend URL**. You can now configure your local environment to use this remote instance.

### Option A: Using Environment Variables
```bash
export FLOWYML_REMOTE_SERVER_URL="https://flowyml-xyz.a.run.app"
export FLOWYML_API_TOKEN="your-api-token"
```

### Option B: Using the CLI
```bash
flowyml config set remote_server_url https://flowyml-xyz.a.run.app
flowyml config set api_token your-api-token
```

### Test the Connection
Run your local training script:
```python
from flowyml import Pipeline, step

@step
def train():
    print("Executing on remote FlowyML instance!")

# This will now register the run on your GCP instance
Pipeline(name="remote_test").add_step(train).run()
```

---

## 🧹 Cleanup

To avoid ongoing costs, you can destroy the infrastructure when finished:
```bash
make gcp-infra-down
```

---

## 🔐 Authentication

We've implemented a robust authentication system:

- **Browser Access**: Use the Username/Password login page.
  - **Default Credentials**: `admin` / `flowyml`
  - **Environment Variables**: Overwrite via `FLOWYML_ADMIN_USER` and `FLOWYML_ADMIN_PASSWORD` (set these in secrets!).

- **API/CLI Access**:
  - Requires `Authorization: Bearer <your-api-token>` header.
  - Set `FLOWYML_API_TOKEN` in your secrets file.

- **Local Development**:
  - No authentication required! The system automatically detects dev mode and bypasses login constraints.

## 💡 Pro Tips

- **Database Pricing**: By default, we use `db-f1-micro` (shared CPU) to keep costs low (< $10/month).
- **Versioning**: Images are tagged with `:latest` by default. Use `IMAGE_TAG=v1` to version your deployments:
  ```bash
  make gcp-deploy IMAGE_TAG=v1.0.0
  ```
- **Access**: Visit the **App URL** (provided by Terraform outputs) to see the dashboard. The API is served from the same URL.
