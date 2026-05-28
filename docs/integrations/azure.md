---
title: Microsoft Azure Integration — FlowyML
description: "Deploy FlowyML pipelines on Azure with Azure ML, Blob Storage, and AKS orchestration."
---

<div class="hero-section" markdown>

## ☁️ Microsoft Azure Integration

Deploy FlowyML pipelines on Azure with Azure ML, Blob Storage, and AKS orchestration.

<span class="feature-badge">🤖 Azure ML</span>
<span class="feature-badge">📦 Blob Storage</span>
<span class="feature-badge">☸️ AKS</span>

</div>

# ☁️ Microsoft Azure

!!! info "What you'll learn"
    How to integrate FlowyML with Azure Blob Storage and Azure ML for enterprise-grade ML pipelines on Azure.

Seamlessly move from local development to Azure's secure cloud infrastructure.

---

## Why Azure with FlowyML?

| Feature | Benefit |
|---|---|
| **Enterprise Security** | Azure Active Directory integration |
| **Blob Storage** | Cost-effective storage for massive datasets |
| **Azure ML** | Managed compute clusters for training and inference |
| **Compliance** | SOC 2, HIPAA, GDPR-ready infrastructure |

---

## 📦 Azure Blob Storage

Store artifacts in Azure Blob Storage containers:

```bash
# Register an Azure stack
flowyml stack register azure-prod \
    --artifact-store az://my-container/flowyml-artifacts \
    --metadata-store sqlite:///flowyml.db
```

```python
from flowyml import Pipeline

# Artifacts automatically go to Azure Blob when using azure-prod stack
pipeline = Pipeline("training")
pipeline.run()
```

---

## 🚀 Azure ML Execution

Execute steps as Azure ML Jobs on managed compute:

```python
from flowyml import Pipeline
from flowyml.integrations.azure import AzureMLOrchestrator

pipeline = Pipeline("azure_pipeline")

pipeline.run(
    orchestrator=AzureMLOrchestrator(
        subscription_id="<subscription_id>",
        resource_group="<resource_group>",
        workspace_name="<workspace_name>",
        compute_target="gpu-cluster",
    )
)
```

### Azure ML Configuration

| Parameter | Type | Description |
|---|---|---|
| `subscription_id` | `str` | Azure subscription ID |
| `resource_group` | `str` | Azure resource group |
| `workspace_name` | `str` | Azure ML workspace name |
| `compute_target` | `str` | Compute cluster name |
| `environment_name` | `str` | Azure ML environment (optional) |

---

## 🔐 Authentication

FlowyML supports multiple Azure credential methods:

1. **`DefaultAzureCredential`** — automatically tries environment vars, managed identity, and CLI
2. **Service Principal** — for CI/CD pipelines
3. **Azure CLI** — for local development

```bash
# Option 1: Service Principal
export AZURE_CLIENT_ID=...
export AZURE_CLIENT_SECRET=...
export AZURE_TENANT_ID=...

# Option 2: Azure CLI
az login
```

---

## Best Practices

!!! tip "Use Managed Identity in production"
    Avoid service principal secrets. Use Managed Identity for VMs and Azure ML compute.

!!! tip "Blob storage tiers"
    Use Hot tier for active artifacts, Cool tier for infrequent access, and Archive for long-term storage.

---

## 🚀 What's Next?

<div class="header-grid" markdown>

<div class="header-card" markdown>

### ☁️ GCP Integration
Deploy FlowyML pipelines on Google Cloud with Vertex AI and GCS storage.

[Explore →](gcp.md)

</div>

<div class="header-card" markdown>

### ☁️ AWS Integration
Run FlowyML pipelines on AWS with SageMaker orchestration and S3 storage.

[Learn more →](aws.md)

</div>

<div class="header-card" markdown>

### 🚀 Deployment
Learn about production deployment strategies and best practices.

[View Guide →](../deployment.md)

</div>

</div>
