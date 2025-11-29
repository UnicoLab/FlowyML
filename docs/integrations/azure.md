# Microsoft Azure ☁️

Enterprise-grade ML pipelines on Azure.

> [!NOTE]
> **What you'll learn**: How to integrate flowyml with Azure Blob Storage and Azure ML
>
> **Key insight**: Seamlessly move from local development to Azure's secure cloud environment.

## Why Use Azure with flowyml?

- **Enterprise Security**: Integrate with Azure Active Directory.
- **Blob Storage**: Cost-effective storage for massive datasets.
- **Azure ML**: Managed compute clusters for training and inference.

## 📦 Azure Blob Storage

Store artifacts in Azure Blob Storage containers.

### Configuration

```bash
# Register an Azure stack
flowyml stack register azure-prod \
    --artifact-store az://my-container/flowyml-artifacts \
    --metadata-store sqlite:///flowyml.db
```

## 🚀 Azure ML Execution

Execute steps as Azure ML Jobs.

### Real-World Pattern: Cloud Training

```python
from flowyml import Pipeline
from flowyml.integrations.azure import AzureMLOrchestrator

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

flowyml supports:
1. `DefaultAzureCredential` (Environment vars, Managed Identity, CLI)
2. Service Principal authentication
