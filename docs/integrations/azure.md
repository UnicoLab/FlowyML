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

## 🏛️ Azure ML Model Registry

Version, stage, and resolve models in your Azure ML workspace (or an org-scoped
Azure ML *registry* for cross-workspace sharing) with the `azureml_registry`
plugin. Azure ML has no built-in stage concept, so FlowyML represents stages as
model **tags** (`stage=production`), the common Azure ML convention.

```python
from flowyml.plugins.model_registries import AzureMLModelRegistry

registry = AzureMLModelRegistry(
    subscription_id="<subscription_id>",
    resource_group="<resource_group>",
    workspace_name="<workspace_name>",
    # registry_name="<org-registry>",   # optional: cross-workspace sharing
)
```

Or, more commonly, attach it to a stack in `flowyml.yaml` so every
`register → promote → deploy` step uses it automatically:

```yaml
stacks:
  azureml-openshift:
    orchestrator:
      type: azure_ml
      subscription_id: ${AZURE_SUBSCRIPTION_ID}
      resource_group: ${AZURE_RESOURCE_GROUP}
      workspace_name: ${AZURE_WORKSPACE}
      compute: cpu-cluster
    artifact_store:
      type: azure_blob
      account_url: ${AZURE_BLOB_ACCOUNT_URL}
      container_name: ml-artifacts
    model_registry:
      type: azureml_registry
      subscription_id: ${AZURE_SUBSCRIPTION_ID}
      resource_group: ${AZURE_RESOURCE_GROUP}
      workspace_name: ${AZURE_WORKSPACE}
    model_deployer:
      type: openshift          # serve on OpenShift, or kubernetes / local_docker
      namespace: ml-prod
      registry_uri: ${OPENSHIFT_REGISTRY}
```

This is exactly the stack used in the end-to-end tutorial: **train on Azure ML,
register to Azure ML (or MLflow), and serve on OpenShift** — all by switching a
stack, with no pipeline code changes.

!!! tip "Train on Azure ML → serve anywhere"
    Because the model registry and model deployer are
    [stack components](../architecture/stacks.md), the same code that trains and
    registers on Azure ML can serve the winner on OpenShift, Kubernetes, or your
    laptop. See **[Serve on OpenShift (E2E)](../tutorials/production-serving-openshift.md)**
    and the **[Model Serving & Deployment guide](../guides/model-serving-deployment.md)**.

Install the Azure extra to enable the orchestrator, Blob store, and registry:

```bash
pip install "flowyml[azure]"   # azure-ai-ml, azure-identity, adlfs
```

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
