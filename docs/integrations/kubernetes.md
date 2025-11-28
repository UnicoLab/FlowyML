# Kubernetes Integration ☸️

Orchestrate your pipelines on Kubernetes clusters for massive scale.

> [!NOTE]
> **What you'll learn**: How to deploy UniFlow pipelines to K8s
>
> **Key insight**: Turn your K8s cluster into a powerful ML engine.

## Why Kubernetes?

- **Scale**: Run thousands of steps in parallel.
- **Resource Management**: CPU/GPU quotas and limits.
- **Resilience**: K8s automatically restarts failed pods.

## ☸️ Running on Kubernetes

UniFlow submits each step as a Kubernetes Pod.

### Configuration

```python
from uniflow.integrations.kubernetes import KubernetesOrchestrator

pipeline.run(
    orchestrator=KubernetesOrchestrator(
        namespace="uniflow-jobs",
        image="my-registry/uniflow-app:latest"
    )
)
```

## ⚙️ Pod Configuration

Customize resources for specific steps.

```python
from uniflow import step, Resources

@step(
    resources=Resources(
        cpu="2",
        memory="4Gi",
        gpu="1"
    )
)
def train_model(data):
    # This runs on a pod with 2 CPUs, 4GB RAM, and 1 GPU
    return model.fit(data)
```

## 🔐 Secrets & Env Vars

Inject secrets safely into your pods.

```python
orchestrator = KubernetesOrchestrator(
    env_vars={
        "API_KEY": {"secret_name": "my-secret", "key": "api-key"}
    }
)
```
