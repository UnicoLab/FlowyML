# CLI Reference

## Overview

UniFlow provides a powerful CLI for managing stacks, components, and running pipelines without modifying code.

## Installation

```bash
pip install uniflow
```

The `uniflow` command will be available globally.

## Commands

### `uniflow init`

Initialize a new UniFlow project.

```bash
uniflow init [OPTIONS]
```

**Options:**
- `--output, -o TEXT`: Output file path (default: `uniflow.yaml`)

**Examples:**
```bash
# Create uniflow.yaml
uniflow init

# Custom output path
uniflow init --output config/uniflow.yaml
```

**Output:**
Creates a `uniflow.yaml` file with default configuration including:
- Local stack
- Basic resource presets
- Docker configuration

---

### `uniflow run`

Run a pipeline with specified stack and configuration.

```bash
uniflow run PIPELINE_FILE [OPTIONS]
```

**Arguments:**
- `PIPELINE_FILE`: Path to pipeline Python file

**Options:**
- `--stack, -s TEXT`: Stack to use (from uniflow.yaml)
- `--resources, -r TEXT`: Resource configuration to use
- `--config, -c TEXT`: Path to uniflow.yaml
- `--context, -ctx TEXT`: Context variables (key=value), can be specified multiple times
- `--dry-run`: Show what would be executed without running

**Examples:**
```bash
# Run with default (local) stack
uniflow run pipeline.py

# Run on production stack
uniflow run pipeline.py --stack production

# Run with GPU resources
uniflow run pipeline.py --stack production --resources gpu_training

# Pass context variables
uniflow run pipeline.py --context data_path=gs://bucket/data.csv --context model_id=123

# Dry run to see configuration
uniflow run pipeline.py --stack production --dry-run

# Custom config file
uniflow run pipeline.py --config custom.yaml --stack staging

# Combined example
uniflow run train.py \
  --stack production \
  --resources gpu_large \
  --context data_path=gs://prod/train.csv \
  --context epochs=100
```

---

### `uniflow stack`

Manage infrastructure stacks.

#### `uniflow stack list`

List all configured stacks.

```bash
uniflow stack list [OPTIONS]
```

**Options:**
- `--config, -c TEXT`: Path to uniflow.yaml

**Examples:**
```bash
# List stacks
uniflow stack list

# With custom config
uniflow stack list --config custom.yaml
```

**Output:**
```
Configured stacks:
  • local (default) [local]
  • production [gcp]
  • staging [gcp]
```

#### `uniflow stack show`

Show detailed stack configuration.

```bash
uniflow stack show STACK_NAME [OPTIONS]
```

**Arguments:**
- `STACK_NAME`: Name of stack to show

**Options:**
- `--config, -c TEXT`: Path to uniflow.yaml

**Examples:**
```bash
# Show production stack details
uniflow stack show production

# With custom config
uniflow stack show staging --config staging.yaml
```

**Output:**
```yaml
Stack: production
type: gcp
project_id: my-ml-project
region: us-central1
artifact_store:
  type: gcs
  bucket: ml-artifacts-prod
```

#### `uniflow stack set-default`

Set the default stack.

```bash
uniflow stack set-default STACK_NAME [OPTIONS]
```

**Arguments:**
- `STACK_NAME`: Name of stack to set as default

**Options:**
- `--config, -c TEXT`: Path to uniflow.yaml

**Examples:**
```bash
# Set production as default
uniflow stack set-default production

# With custom config
uniflow stack set-default local --config dev.yaml
```

---

### `uniflow component`

Manage stack components and plugins.

#### `uniflow component list`

List all registered components.

```bash
uniflow component list [OPTIONS]
```

**Options:**
- `--type, -t TEXT`: Filter by component type (orchestrators, artifact_stores, container_registries)

**Examples:**
```bash
# List all components
uniflow component list

# List only orchestrators
uniflow component list --type orchestrators

# List only artifact stores
uniflow component list --type artifact_stores
```

**Output:**
```
📦 Registered Components:

Orchestrators:
  • vertex_ai
  • airflow

Artifact_stores:
  • local
  • gcs
  • minio
```

#### `uniflow component load`

Load a component from various sources.

```bash
uniflow component load SOURCE [OPTIONS]
```

**Arguments:**
- `SOURCE`: Component source (see examples)

**Options:**
- `--name, -n TEXT`: Custom name for component

**Examples:**
```bash
# From Python module
uniflow component load my_uniflow_components

# From file with specific class
uniflow component load /path/to/custom.py:MyOrchestrator

# From ZenML
uniflow component load zenml:zenml.integrations.kubernetes.orchestrators.KubernetesOrchestrator

# With custom name
uniflow component load my_components --name custom
```

**Source Formats:**
- `module.path` - Load from Python module
- `/path/to/file.py:ClassName` - Load from file
- `zenml:zenml.path.Class` - Load from ZenML

---

## Global Options

All commands support:
- `--help`: Show help message
- `--version`: Show UniFlow version

## Configuration Files

### Search Order

UniFlow searches for configuration in this order:
1. `--config` flag value
2. `uniflow.yaml` (current directory)
3. `uniflow.yml`
4. `.uniflow/config.yaml`
5. `.uniflow/config.yml`

### Environment Variables

UniFlow automatically expands environment variables in configuration:
- `${VAR_NAME}` - Required variable (fails if not set)
- `$VAR_NAME` - Required variable
- `${VAR_NAME:-default}` - With default value (future)

##  Examples

### Development Workflow

```bash
# 1. Initialize project
uniflow init

# 2. Edit uniflow.yaml
vim uniflow.yaml

# 3. List available stacks
uniflow stack list

# 4. Run pipeline locally
uniflow run pipeline.py

# 5. Test on staging
uniflow run pipeline.py --stack staging --dry-run

# 6. Deploy to production
uniflow run pipeline.py --stack production --resources gpu_training
```

### Multi-Environment Deployment

```bash
# Development
uniflow run pipeline.py --config dev.yaml

# Staging
uniflow run pipeline.py --config staging.yaml --stack staging

# Production
uniflow run pipeline.py --config prod.yaml --stack production
```

### Custom Components

```bash
# 1. List current components
uniflow component list

# 2. Load custom component
uniflow component load my_custom_components

# 3. Verify it's loaded
uniflow component list

# 4. Use in pipeline
uniflow run pipeline.py --stack custom_stack
```

### GPU Training

```bash
# Train with single GPU
uniflow run train.py --resources gpu_small

# Train with multiple GPUs
uniflow run train.py --resources gpu_large

# Large-scale training with A100s
uniflow run train.py \
  --stack production \
  --resources gpu_xlarge \
  --context batch_size=512 \
  --context epochs=100
```

### Debugging

```bash
# Dry run to see configuration
uniflow run pipeline.py --stack production --dry-run

# Show stack details
uniflow stack show production

# Validate configuration
python -c "from uniflow.utils.stack_config import load_config; load_config().load()"
```

## Exit Codes

- `0`: Success
- `1`: General error
- `2`: Configuration error
- `3`: Pipeline execution error

## Shell Completion

### Bash

```bash
echo 'eval "$(_UNIFLOW_COMPLETE=bash_source uniflow)"' >> ~/.bashrc
```

### Zsh

```bash
echo 'eval "$(_UNIFLOW_COMPLETE=zsh_source uniflow)"' >> ~/.zshrc
```

### Fish

```bash
echo '_UNIFLOW_COMPLETE=fish_source uniflow | source' >> ~/.config/fish/completions/uniflow.fish
```

## Tips & Tricks

### Aliases

```bash
# .bashrc or .zshrc
alias uf='uniflow'
alias ufr='uniflow run'
alias ufs='uniflow stack'
alias ufc='uniflow component'

# Usage
ufr pipeline.py -s production
ufs list
ufc list
```

### Default Stack

Set in `uniflow.yaml`:
```yaml
default_stack: production
```

Then run without specifying stack:
```bash
uniflow run pipeline.py
# Uses production stack
```

### Environment-Specific Aliases

```bash
# Development
alias uf-dev='uniflow run --config dev.yaml'

# Staging
alias uf-stage='uniflow run --config staging.yaml --stack staging'

# Production
alias uf-prod='uniflow run --config prod.yaml --stack production'

# Usage
uf-dev pipeline.py
uf-stage pipeline.py
uf-prod pipeline.py --resources gpu_large
```

### CI/CD Integration

```yaml
# .github/workflows/ml-pipeline.yml
name: ML Pipeline

on:
  push:
    branches: [main]

jobs:
  train:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install uniflow[gcp]

      - name: Run pipeline
        env:
          GCP_PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
          GCP_BUCKET: ${{ secrets.GCP_BUCKET }}
          GCP_SERVICE_ACCOUNT: ${{ secrets.GCP_SERVICE_ACCOUNT }}
        run: |
          uniflow run training_pipeline.py \
            --stack production \
            --resources gpu_training \
            --context experiment_name=github-${{ github.run_id }}
```

## Troubleshooting

### Command Not Found

```bash
# Check installation
pip show uniflow

# Reinstall
pip install --force-reinstall uniflow
```

### Configuration Not Found

```bash
# Specify custom path
uniflow run pipeline.py --config /full/path/to/uniflow.yaml

# Check current directory
pwd
ls -la uniflow.yaml
```

### Component Not Found

```bash
# List what's registered
uniflow component list

# Load explicitly
uniflow component load my_components

# Check Python path
python -c "import my_components"
```

### Stack Validation Fails

```bash
# Show stack configuration
uniflow stack show STACK_NAME

# Dry run
uniflow run pipeline.py --stack STACK_NAME --dry-run
```

## See Also

- [Configuration Guide](../user-guide/configuration.md)
- [Components Guide](../user-guide/components.md)
- [Quick Reference](../QUICK_REFERENCE.md)
- [Stack Architecture](../architecture/stacks.md)
