# Enterprise Stack Registry Example

This example demonstrates how to use FlowyML's Enterprise Stack Registry
for governed ML pipeline execution across multiple environments.

## Quick Start

### 1. Define stacks (Platform Team)

Stack definitions in `stacks/` define approved execution environments:

- `stacks/local_dev.yaml` — Local development
- `stacks/aml_cpu_small.yaml` — AzureML CPU (staging/prod)
- `stacks/aml_gpu_large.yaml` — AzureML GPU (training)

### 2. Configure project

`flowyml.yaml` maps environments to stacks:

```yaml
project:
  name: churn-modeling
  owner: ml-team

defaults:
  stack: local_dev
  environment: dev

environments:
  dev:
    stack: local_dev
  staging:
    stack: aml_cpu_small
    requireLock: true
  prod:
    stack: aml_cpu_small
    requireLock: true
    requirePolicyValidation: true
```

### 3. Run pipelines (Data Scientist)

```python
# Same pipeline code, different environments
pipeline.run()                     # Uses default (local_dev)
pipeline.run(env='staging')        # Uses aml_cpu_small
pipeline.run(env='prod')           # Uses aml_cpu_small with policy check
pipeline.dry_run(env='prod')       # Validate without executing
```

### 4. CLI

```bash
flowy run training --env prod
flowy run training --dry-run
flowy stack-gov list
flowy stack-gov inspect aml_cpu_small
flowy stack-gov lock
flowy policy check --env prod
```

## Stack Definition Schema

See the YAML files in `stacks/` for complete examples.
