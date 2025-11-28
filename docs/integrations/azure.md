# Microsoft Azure ☁️

Enterprise-grade ML pipelines on Azure.

> [!NOTE]
> **What you'll learn**: How to integrate UniFlow with Azure Blob Storage and Azure ML
>
> **Key insight**: Seamlessly move from local development to Azure's secure cloud environment.

## Why Use Azure with UniFlow?

- **Enterprise Security**: Integrate with Azure Active Directory.
- **Blob Storage**: Cost-effective storage for massive datasets.
- **Azure ML**: Managed compute clusters for training and inference.

## 📦 Azure Blob Storage

Store artifacts in Azure Blob Storage containers.

### Configuration

```bash
# Register an Azure stack
uniflow stack register azure-prod \
    --artifact-store az://my-container/uniflow-artifacts \
    --metadata-store sqlite:///uniflow.db
```

## 🚀 Azure ML Execution

Execute steps as Azure ML Jobs.

### Real-World Pattern: Cloud Training

```python
from uniflow import Pipeline
from uniflow.integrations.azure import AzureMLOrchestrator

pipeline = Pipeline("azure_pipeline")

# Run on Azure ML
pipeline.run(
    orchestrator=AzureMLOrchestrator(
        subscription_id="<subscription_id>",
        resource_group="<resource_group>",
        workspace_name="<workspace_name>",
        compute_target="gpu-cluster"
    )
)
```

## 🔐 Authentication

UniFlow supports:
1. `DefaultAzureCredential` (Environment vars, Managed Identity, CLI)
2. Service Principal authentication
