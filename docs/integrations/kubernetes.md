# ☸️ Kubernetes Integration

!!! info "What you'll learn"
    How to deploy FlowyML pipelines to Kubernetes clusters for massive scale — turn your K8s cluster into a powerful ML engine.

Orchestrate pipelines on Kubernetes clusters with per-step resource allocation, GPU support, and Kubernetes-native secrets management.

---

## Why Kubernetes?

| Feature | Benefit |
|---|---|
| **Scale** | Run thousands of steps in parallel |
| **Resource Management** | CPU/GPU quotas and limits per step |
| **Resilience** | K8s automatically restarts failed pods |
| **Portability** | Same configs work on any K8s cluster |

---

## ☸️ Running on Kubernetes

FlowyML submits each step as a Kubernetes Pod:

```python
from flowyml.integrations.kubernetes import KubernetesOrchestrator

pipeline.run(
    orchestrator=KubernetesOrchestrator(
        namespace="flowyml-jobs",
        image="my-registry/flowyml-app:latest",
    )
)
```

### Configuration

| Parameter | Type | Default | Description |
|---|---|---|---|
| `namespace` | `str` | `"default"` | Kubernetes namespace for pods |
| `image` | `str` | *required* | Container image for steps |
| `image_pull_policy` | `str` | `"Always"` | `Always`, `IfNotPresent`, or `Never` |
| `service_account` | `str` | `None` | K8s service account name |
| `env_vars` | `dict` | `{}` | Environment variables and secrets |
| `node_selector` | `dict` | `{}` | Node selection labels |

---

## ⚙️ Per-Step Resources

Customize CPU, memory, and GPU for specific steps:

```python
from flowyml import step, Resources

@step(
    resources=Resources(
        cpu="2",
        memory="4Gi",
        gpu="1",
    )
)
def train_model(data):
    """Runs on a pod with 2 CPUs, 4GB RAM, and 1 GPU."""
    return model.fit(data)

@step(
    resources=Resources(cpu="0.5", memory="512Mi")
)
def preprocess(data):
    """Lightweight preprocessing on minimal resources."""
    return clean(data)
```

---

## 🔐 Secrets & Environment Variables

Inject Kubernetes secrets safely into your pods:

```python
orchestrator = KubernetesOrchestrator(
    namespace="flowyml-jobs",
    image="my-app:latest",
    env_vars={
        "API_KEY": {"secret_name": "my-secret", "key": "api-key"},
        "DB_HOST": {"config_map": "my-config", "key": "db-host"},
        "LOG_LEVEL": "INFO",  # Plain value
    },
)
```

---

## Best Practices

!!! tip "Use node selectors for GPU steps"
    Label GPU nodes and use `node_selector={"gpu": "true"}` to ensure GPU steps land on the right nodes.

!!! tip "Resource requests vs. limits"
    Set `Resources` to match expected usage. Over-requesting wastes cluster capacity; under-requesting causes OOM kills.

!!! warning "Image pull secrets"
    If using a private registry, configure `imagePullSecrets` in your namespace.
