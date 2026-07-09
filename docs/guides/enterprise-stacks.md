---
title: Enterprise Stacks — FlowyML
description: "Centrally define, govern, and version execution stacks for enterprise ML platform teams."
---

<div class="hero-section" markdown>

## 🏢 Enterprise Stacks

Centrally define, govern, and version execution stacks — platform teams own infrastructure, data scientists focus on code.

<span class="feature-badge">📋 StackDefinition</span>
<span class="feature-badge">🔍 StackResolver</span>
<span class="feature-badge">🛡️ PolicyEngine</span>
<span class="feature-badge">🔒 AuditStore</span>

</div>

# 🏢 Enterprise Stacks

!!! info "What you'll learn"
    How to define governed execution stacks using YAML manifests, resolve them from multiple sources, enforce policies, and manage stack lifecycles in enterprise environments.

---

## Overview

Enterprise Stacks decouple **infrastructure configuration** from **pipeline code**. Platform teams define stacks centrally; data scientists consume them by name.

```python
# Data scientist's code — no infrastructure details
pipeline = Pipeline("training", stack="prod-gpu-large")
pipeline.run()
```

The stack `prod-gpu-large` is resolved, validated against policies, and wired into the pipeline automatically.

---

## Stack Resolution Flow

When a pipeline references a stack, FlowyML resolves it through a priority chain:

```mermaid
graph TD
    A["Pipeline(stack='...')"] --> B{Explicit stack arg?}
    B -->|Yes| C[Use directly]
    B -->|No| D{env= parameter?}
    D -->|Yes| E[Resolve from project config]
    D -->|No| F{FLOWYML_STACK env var?}
    F -->|Yes| G[Resolve from registry]
    F -->|No| H{flowyml.yaml?}
    H -->|Yes| I[Load active stack]
    H -->|No| J[Default LocalStack]
```

The stack argument accepts:

| Input Type | Example | Resolution |
|---|---|---|
| `str` (name) | `"prod-gpu"` | Registry / project config lookup |
| `str` (URI) | `"github://org/repo@v1#stack"` | Remote source resolution |
| `Stack` instance | `my_stack` | Used directly |
| `StackDefinition` | `definition` | Converted via `.to_stack()` |

---

## StackDefinition YAML

Define stacks as declarative YAML manifests:

```yaml
apiVersion: flowyml/v1
kind: StackDefinition
metadata:
  name: prod-gpu-large
  version: "2.1.0"
  labels:
    team: ml-platform
    environment: production
    approved: "true"
spec:
  compute:
    backend: azureml
    size: Standard_NC6s_v3
    min_nodes: 0
    max_nodes: 4
  runtime:
    python_version: "3.11"
    docker_image: myregistry.azurecr.io/flowyml:latest
  storage:
    artifact_store: abfs://artifacts@mystorage.dfs.core.windows.net
    metadata_store: sqlite:///shared/metadata.db
  tracking:
    experiment_tracker: mlflow
    mlflow_uri: https://mlflow.company.com
  secrets:
    provider: azure_keyvault
    vault_url: https://my-vault.vault.azure.net
```

---

## Stack Sources

The `StackResolver` can load definitions from multiple sources:

### Local File

```yaml
# flowyml.yaml
stacks:
  dev:
    source: local
    path: ./stacks/dev.yaml
```

### GitHub / GitLab

```yaml
stacks:
  prod:
    source: github
    repo: my-org/ml-stacks
    ref: v2.1.0
    path: stacks/prod.yaml
```

```python
# Or programmatically via URI
pipeline = Pipeline("train", stack="github://my-org/ml-stacks@v2.1.0#prod")
```

### HTTP

```yaml
stacks:
  staging:
    source: http
    url: https://config.company.com/stacks/staging.yaml
```

### Stack Registry

```python
from flowyml.stacks.enterprise.resolver import StackResolver

resolver = StackResolver()
definition = resolver.resolve(stack="prod-gpu-large", env="production")
```

---

## Policy Engine

Enforce organizational policies on all stacks:

```yaml
# flowyml.yaml — project-level governance
project:
  name: fraud-detection
  org: fintech-corp
  policies:
    allowed_stacks:
      - prod-gpu-*
      - staging-*
    required_labels:
      - approved
      - team
    image_policy:
      allowed_registries:
        - myregistry.azurecr.io
        - gcr.io/my-project
      required_labels:
        - maintainer
        - version
```

The `PolicyEngine` validates stacks before execution:

- ✅ Stack name matches allowed patterns
- ✅ Required metadata labels are present
- ✅ Docker images come from approved registries
- ✅ Base images pass security checks

---

## Governed Model Serving

A company-level `StackDefinition` isn't limited to *where pipelines run* — it can
also govern *how models are registered and served*. The `spec.deployment` section
declares the **model registry** and **model deployer** flavors a stack uses for
the `train → register → promote → serve` path, and the policy engine can
allow-list which flavors each team is permitted to use.

```yaml title="stacks/aml_openshift_prod.yaml"
apiVersion: flowyml.io/v1
kind: Stack
metadata:
  name: aml_openshift_prod
  version: 1.0.0
  owner: ml-platform-team
  tags: [azureml, openshift, production]
spec:
  backend: azureml
  compute:
    type: cpu
    size: Standard_DS3_v2
    region: francecentral
  storage:
    artifactStore: azure_blob
    uri: az://ml-artifacts/prod

  # --- Governed model serving --------------------------------------------
  deployment:
    modelRegistry: azureml_registry       # where models are versioned/staged
    modelDeployer: openshift              # where they are served
    namespace: ml-prod
    registryUri: registry.apps.example.com/ml
    config:                              # extra flavor-specific kwargs
      subscription_id: ${AZURE_SUBSCRIPTION_ID}
      resource_group: ml-rg
      workspace_name: ml-ws

  # --- Policy allow-lists ------------------------------------------------
  policies:
    allowedModelDeployers: [openshift, kubernetes]     # no ad-hoc local_docker in prod
    allowedModelRegistries: [azureml_registry, mlflow_registry]

  # --- Ownership / RBAC --------------------------------------------------
  permissions:
    allowedGroups: [ml-engineers, ml-platform-team]
    allowedProjects: [fraud-detection, churn]
```

!!! info "Flavor names must resolve at runtime"
    `modelDeployer` and `modelRegistry` are validated against the flavors
    registered with the runtime `ComponentRegistry`, so a governed definition is
    **executable**, not merely descriptive. Supported deployers include
    `local_docker`, `kubernetes`, `openshift`, `vertex_endpoint`,
    `sagemaker_endpoint`, and `gcp_cloud_run`; supported registries include
    `mlflow_registry`, `azureml_registry`, `vertex_model_registry`, and
    `sagemaker_model_registry`.

### Hydrating a governed stack

`StackDefinition.to_stack()` builds the backend execution stack **and** attaches
the governed deployment components, so the resulting `Stack` exposes
`.model_deployer` / `.model_registry` for the deployment service and
champion/challenger promotion:

```python
from flowyml.stacks.enterprise.models import StackDefinition

stack = StackDefinition.from_yaml("stacks/aml_openshift_prod.yaml").to_stack()
stack.model_registry    # AzureMLModelRegistry
stack.model_deployer    # OpenShiftDeployer (namespace=ml-prod, registry_uri=...)
```

Unresolvable flavors (e.g. a serving SDK that isn't installed locally) are logged
and skipped rather than raising, so a governed definition stays usable for
execution even on a developer laptop.

### Serving-aware policy rules

Two built-in rules enforce the serving allow-lists, alongside the execution
rules already covered above:

| Rule | What it checks |
|------|----------------|
| `ModelDeployerAllowedRule` | `spec.deployment.modelDeployer` ∈ `policies.allowedModelDeployers` |
| `ModelRegistryAllowedRule`  | `spec.deployment.modelRegistry` ∈ `policies.allowedModelRegistries` |

Empty allow-lists mean "no restriction", and a stack with no `deployment`
section makes both rules no-ops. Enforcement is identical to every other rule —
`PolicyEngine.check()` raises `PolicyViolationError` on any failure:

```python
from flowyml.stacks.enterprise.policy import PolicyEngine, PolicyContext

ctx = PolicyContext(
    stack=stack_def,
    user="alice",
    user_groups=["ml-engineers"],
    project_name="fraud-detection",
)
PolicyEngine().check(ctx)   # raises if the deployer/registry/group isn't allowed
```

!!! tip "Ownership & RBAC"
    `metadata.owner` records the accountable team, while `permissions.allowedGroups`
    and `permissions.allowedProjects` gate *who* may use the stack. The
    `UserPermissionRule` and `ProjectPermissionRule` enforce these before any
    training or deployment begins — so a governed serving stack can only be used
    by approved teams on approved projects.

---

## Audit & Locking

### Audit Store

Every stack operation is recorded:

```python
from flowyml.stacks.enterprise.audit import AuditStore

audit = AuditStore()
events = audit.get_events(stack_name="prod-gpu-large")
# → [StackApplied, StackValidated, PolicyChecked, ...]
```

### Stack Locking

Prevent concurrent modifications:

```python
from flowyml.stacks.enterprise.lock import StackLockManager

lock_manager = StackLockManager()
with lock_manager.acquire("prod-gpu-large"):
    # Exclusive access to stack configuration
    ...
```

---

## CLI Commands

```bash
# List all available stacks
flowyml enterprise stack list

# Show stack details
flowyml enterprise stack show prod-gpu-large

# Validate a stack definition
flowyml enterprise stack validate ./stacks/prod.yaml

# Apply a stack (register/update)
flowyml enterprise stack apply ./stacks/prod.yaml
```

---

## Environment-Based Resolution

Map environments to stacks in your project config:

```yaml
# flowyml.yaml
environments:
  dev:
    stack: local
  staging:
    stack: staging-cpu
  production:
    stack: prod-gpu-large
```

```python
# Automatically resolves to the correct stack
pipeline = Pipeline("training", env="production")
```

---

## Best Practices

!!! tip "Version your stacks"
    Pin stack versions in production to ensure reproducibility. Use semantic versioning for stack definitions.

!!! tip "Separate concerns"
    Platform teams own stack definitions (compute, storage, networking). Data scientists own pipeline code (steps, models, metrics).

!!! warning "Policy enforcement"
    Always enable policy enforcement in production. Unapproved stacks should be blocked before execution, not after.

---

## 🚀 What's Next?

<div class="header-grid" markdown>

<div class="header-card" markdown>

### 🔐 Secrets Management
Unified secrets layer with 6 enterprise providers.

[Explore →](../deployment/secrets.md)

</div>

<div class="header-card" markdown>

### ⚡ Databricks
Run pipelines on Databricks with auto-managed clusters.

[Learn more →](../integrations/databricks.md)

</div>

<div class="header-card" markdown>

### 📊 Experiment Tracking
Transparent dual-write to FlowyML and external trackers.

[View Guide →](experiment-tracking.md)

</div>

<div class="header-card" markdown>

### 🚢 Model Serving & Deployment
Package and serve governed models to OpenShift, Kubernetes, or Docker.

[View Guide →](model-serving-deployment.md)

</div>

</div>
