---
title: "Orchestrators — FlowyML"
description: "API reference for FlowyML orchestrator backends: local, Docker, Vertex AI, SageMaker, and Kubernetes."
---

# Orchestrators API 🎼

Orchestrators form the **execution layer** of FlowyML. They decide *where* and *how* each step runs — locally in a subprocess, inside a Docker container, or remotely on managed infrastructure such as Vertex AI, SageMaker, or Kubernetes. Every orchestrator implements the `Executor` base class, ensuring a uniform interface for step dispatch, resource allocation, and failure handling regardless of the target environment.

Orchestrators manage the execution of pipeline steps.

## Base Executor

::: flowyml.core.executor.Executor
    options:
        show_root_heading: false

## Local Executor

::: flowyml.core.executor.LocalExecutor
    options:
        show_root_heading: false

## Vertex AI Orchestrator

::: flowyml.stacks.gcp.VertexAIOrchestrator
    options:
        show_root_heading: false

---

## See Also

- [Plugins Overview](../plugins/overview.md) — how orchestrator backends are registered as plugins
- [Deployment Guide](../deployment.md) — end-to-end guide for deploying pipelines to production
