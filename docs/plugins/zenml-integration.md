# ZenML Integration

UniFlow provides first-class support for the entire ZenML ecosystem through its Generic Bridge system. You can use any ZenML stack component—orchestrators, artifact stores, container registries—directly within UniFlow pipelines.

## How It Works

Unlike traditional integrations that require custom code for each component, UniFlow uses a **Generic Bridge** that dynamically adapts ZenML components. You simply tell UniFlow where the component lives and how to map its methods (if necessary) via configuration.

## Using ZenML Components

To use a ZenML component, you define it in your `uniflow.yaml` (or load it via the CLI).

### Example: Kubernetes Orchestrator

```yaml
plugins:
  - name: zenml_k8s
    source: zenml.integrations.kubernetes.orchestrators.KubernetesOrchestrator
    type: orchestrator
    adaptation:
      method_mapping:
        run_pipeline: run
```

### Example: S3 Artifact Store

```yaml
plugins:
  - name: zenml_s3
    source: zenml.integrations.s3.artifact_stores.S3ArtifactStore
    type: artifact_store
```

## Migrating from ZenML

If you already have a ZenML stack, you don't need to write configuration manually. UniFlow includes a migration tool that inspects your ZenML stack and generates the UniFlow configuration for you.

```bash
# Import a specific stack
uniflow plugin import-zenml-stack my-production-stack
```

This command will:
1.  Connect to your ZenML client.
2.  Analyze the `my-production-stack`.
3.  Identify all components (Orchestrator, Artifact Store, etc.).
4.  Generate a `uniflow.yaml` file with the correct plugin definitions.

## Running ZenML Pipelines

Once configured, you can run your UniFlow pipelines on ZenML infrastructure seamlessly:

```bash
uniflow run my_pipeline --stack my-production-stack
```

UniFlow handles the translation of pipeline steps and execution context, delegating the actual heavy lifting to the ZenML component (e.g., submitting a job to Kubernetes).
