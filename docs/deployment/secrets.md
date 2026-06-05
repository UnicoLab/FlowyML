---
title: Secrets Management — FlowyML
description: "Unified secrets layer with 6 enterprise providers: Vault, Azure Key Vault, AWS Secrets Manager, GCP Secret Manager, environment, and local."
---

<div class="hero-section" markdown>

## 🔐 Secrets Management

Unified secrets layer with 6 enterprise providers — configure once in your stack, access anywhere in your pipeline.

<span class="feature-badge">🏛️ HashiCorp Vault</span>
<span class="feature-badge">☁️ Azure Key Vault</span>
<span class="feature-badge">☁️ AWS Secrets Manager</span>
<span class="feature-badge">☁️ GCP Secret Manager</span>

</div>

# 🔐 Secrets Management

!!! info "What you'll learn"
    How to configure and use FlowyML's unified secrets layer — from simple environment variables to enterprise-grade providers like HashiCorp Vault and cloud-native secret managers.

---

## Overview

FlowyML provides a **unified `SecretsProvider` interface** with 6 backend implementations. Your pipeline code stays the same regardless of which secrets backend you use.

```python
# Pipeline code never changes — the stack handles secrets resolution
pipeline = Pipeline("training", stack="prod-vault")
pipeline.run()
```

---

## Providers

| Provider | Backend | Dependency | Zero-Config |
|---|---|---|---|
| `env` | Environment variables | None | ✅ |
| `local` | Local `.env` / JSON file | None | ✅ |
| `vault` | HashiCorp Vault | `hvac` | ❌ |
| `azure_keyvault` | Azure Key Vault | `azure-keyvault-secrets` | ❌ |
| `aws_secretsmanager` | AWS Secrets Manager | `boto3` | ❌ |
| `gcp_secretmanager` | GCP Secret Manager | `google-cloud-secret-manager` | ❌ |

---

## Configuration

### Environment Variables (Default)

```yaml
# flowyml.yaml
stacks:
  dev:
    secrets:
      provider: env
```

```bash
export DB_PASSWORD=super_secret
export API_KEY=sk-xxxx
```

### Local File

```yaml
stacks:
  dev:
    secrets:
      provider: local
      path: .secrets.json  # or .env format
```

### HashiCorp Vault

```yaml
stacks:
  prod:
    secrets:
      provider: vault
      vault_url: https://vault.company.com
      vault_mount: secret
      vault_path: ml/training
```

```bash
# Authentication via standard Vault env vars
export VAULT_TOKEN=hvs.xxxx
# or use AppRole, Kubernetes auth, etc.
```

### Azure Key Vault

```yaml
stacks:
  prod:
    secrets:
      provider: azure_keyvault
      vault_url: https://my-vault.vault.azure.net
```

```bash
# Authentication via Azure Identity (DefaultAzureCredential)
# Works with: managed identity, service principal, CLI login
```

### AWS Secrets Manager

```yaml
stacks:
  prod:
    secrets:
      provider: aws_secretsmanager
      region: us-east-1
      secret_name: ml/training-secrets
```

```bash
# Authentication via standard AWS credential chain
# Works with: env vars, ~/.aws/credentials, IAM roles
```

### GCP Secret Manager

```yaml
stacks:
  prod:
    secrets:
      provider: gcp_secretmanager
      project_id: my-gcp-project
```

```bash
# Authentication via Application Default Credentials
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
# or use workload identity, gcloud auth
```

---

## Programmatic Access

### Factory Function

```python
from flowyml.stacks.enterprise.secrets import get_secrets_provider

# Auto-detects provider from stack config
provider = get_secrets_provider(stack_config)
secret = provider.get_secret("DB_PASSWORD")
```

### Via StackDefinition

```python
from flowyml.stacks.enterprise.models import StackDefinition

definition = StackDefinition.from_yaml("stacks/prod.yaml")
provider = definition.get_secrets_provider()
api_key = provider.get_secret("API_KEY")
```

### Provider API

All providers implement the same interface:

```python
class SecretsProvider:
    def get_secret(self, key: str) -> str | None:
        """Get a secret by key."""
        ...

    def set_secret(self, key: str, value: str) -> None:
        """Set a secret (if the backend supports writes)."""
        ...

    def list_secrets(self) -> list[str]:
        """List available secret keys."""
        ...

    def delete_secret(self, key: str) -> None:
        """Delete a secret by key."""
        ...
```

---

## Migration from Terraform

If you're currently using Terraform-based secret management:

| Before (Terraform) | After (FlowyML Secrets) |
|---|---|
| Define secrets in `.tfvars` | Configure provider in `flowyml.yaml` |
| `terraform apply -var-file=...` | Automatic — pipeline resolves from stack |
| Manual secret rotation | `provider.set_secret()` or cloud console |
| Per-cloud IAM setup | Unified API, cloud-native auth |

!!! tip "Gradual migration"
    Start with `provider: env` to use existing environment variables, then migrate to Vault or cloud-native providers when ready.

---

## Best Practices

!!! warning "Never commit secrets"
    Use `.gitignore` to exclude `.env`, `.secrets.json`, and `*.tfvars` files. Use a secrets provider for production.

!!! tip "Use managed identity in production"
    On Azure, AWS, and GCP, use managed identity / IAM roles instead of static credentials for zero-credential deployments.

!!! tip "Rotate secrets regularly"
    All cloud providers support secret versioning. Use the provider's rotation features and FlowyML will pick up the latest version automatically.

---

## 🚀 What's Next?

<div class="header-grid" markdown>

<div class="header-card" markdown>

### 🏢 Enterprise Stacks
Governed stack definitions with policy enforcement.

[Explore →](../guides/enterprise-stacks.md)

</div>

<div class="header-card" markdown>

### ⚡ Databricks
Run pipelines on Databricks with auto-managed clusters.

[Learn more →](../integrations/databricks.md)

</div>

<div class="header-card" markdown>

### ☁️ Azure Integration
Deploy on Azure with AzureML and Azure Key Vault secrets.

[View Guide →](../integrations/azure.md)

</div>

</div>
