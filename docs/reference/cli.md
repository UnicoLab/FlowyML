# CLI Reference

## Overview

flowyml provides a powerful CLI for managing stacks, components, and running pipelines without modifying code.

## Installation

```bash
pip install flowyml
```

The `flowyml` command will be available globally.

## Commands

### `flowyml init`

Initialize a new flowyml project.

```bash
flowyml init [OPTIONS]
```

**Options:**
- `--output, -o TEXT`: Output file path (default: `flowyml.yaml`)

**Examples:**
```bash
# Create flowyml.yaml
flowyml init

# Custom output path
flowyml init --output config/flowyml.yaml
```

**Output:**
Creates a `flowyml.yaml` file with default configuration including:
- Local stack
- Basic resource presets
- Docker configuration

---

### `flowyml run`

Run a pipeline with specified stack and configuration.

```bash
flowyml run PIPELINE_FILE [OPTIONS]
```

**Arguments:**
- `PIPELINE_FILE`: Path to pipeline Python file

**Options:**
- `--stack, -s TEXT`: Stack to use (from flowyml.yaml)
- `--resources, -r TEXT`: Resource configuration to use
- `--config, -c TEXT`: Path to flowyml.yaml
- `--context, -ctx TEXT`: Context variables (key=value), can be specified multiple times
- `--dry-run`: Show what would be executed without running

**Examples:**
```bash
# Run with default (local) stack
flowyml run pipeline.py

# Run on production stack
flowyml run pipeline.py --stack production

# Run with GPU resources
flowyml run pipeline.py --stack production --resources gpu_training

# Pass context variables
flowyml run pipeline.py --context data_path=gs://bucket/data.csv --context model_id=123

# Dry run to see configuration
flowyml run pipeline.py --stack production --dry-run

# Custom config file
flowyml run pipeline.py --config custom.yaml --stack staging

# Combined example
flowyml run train.py \
  --stack production \
  --resources gpu_large \
  --context data_path=gs://prod/train.csv \
  --context epochs=100
```

---

### `flowyml stack`

Manage infrastructure stacks.

#### `flowyml stack list`

List all configured stacks.

```bash
flowyml stack list [OPTIONS]
```

**Options:**
- `--config, -c TEXT`: Path to flowyml.yaml

**Examples:**
```bash
# List stacks
flowyml stack list

# With custom config
flowyml stack list --config custom.yaml
```

**Output:**
```
Configured stacks:
  • local (default) [local]
  • production [gcp]
  • staging [gcp]
```

#### `flowyml stack show`

Show detailed stack configuration.

```bash
flowyml stack show STACK_NAME [OPTIONS]
```

**Arguments:**
- `STACK_NAME`: Name of stack to show

**Options:**
- `--config, -c TEXT`: Path to flowyml.yaml

**Examples:**
```bash
# Show production stack details
flowyml stack show production

# With custom config
flowyml stack show staging --config staging.yaml
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

#### `flowyml stack set-default`

Set the default stack.

```bash
flowyml stack set-default STACK_NAME [OPTIONS]
```

**Arguments:**
- `STACK_NAME`: Name of stack to set as default

**Options:**
- `--config, -c TEXT`: Path to flowyml.yaml

**Examples:**
```bash
# Set production as default
flowyml stack set-default production

# With custom config
flowyml stack set-default local --config dev.yaml
```

---

### `flowyml component`

Manage stack components and plugins.

#### `flowyml component list`

List all registered components.

```bash
flowyml component list [OPTIONS]
```

**Options:**
- `--type, -t TEXT`: Filter by component type (orchestrators, artifact_stores, container_registries)

**Examples:**
```bash
# List all components
flowyml component list

# List only orchestrators
flowyml component list --type orchestrators

# List only artifact stores
flowyml component list --type artifact_stores
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

#### `flowyml component load`

Load a component from various sources.

```bash
flowyml component load SOURCE [OPTIONS]
```

**Arguments:**
- `SOURCE`: Component source (see examples)

**Options:**
- `--name, -n TEXT`: Custom name for component

**Examples:**
```bash
# From Python module
flowyml component load my_flowyml_components

# From file with specific class
flowyml component load /path/to/custom.py:MyOrchestrator

# From ZenML
flowyml component load zenml:zenml.integrations.kubernetes.orchestrators.KubernetesOrchestrator

# With custom name
flowyml component load my_components --name custom
```

**Source Formats:**
- `module.path` - Load from Python module
- `/path/to/file.py:ClassName` - Load from file
- `zenml:zenml.path.Class` - Load from ZenML

---

## Global Options

All commands support:
- `--help`: Show help message
- `--version`: Show flowyml version

## Configuration Files

### Search Order

flowyml searches for configuration in this order:
1. `--config` flag value
2. `flowyml.yaml` (current directory)
3. `flowyml.yml`
4. `.flowyml/config.yaml`
5. `.flowyml/config.yml`

### Environment Variables

flowyml automatically expands environment variables in configuration:
- `${VAR_NAME}` - Required variable (fails if not set)
- `$VAR_NAME` - Required variable
- `${VAR_NAME:-default}` - With default value (future)

##  Examples

### Development Workflow

```bash
# 1. Initialize project
flowyml init

# 2. Edit flowyml.yaml
vim flowyml.yaml

# 3. List available stacks
flowyml stack list

# 4. Run pipeline locally
flowyml run pipeline.py

# 5. Test on staging
flowyml run pipeline.py --stack staging --dry-run

# 6. Deploy to production
flowyml run pipeline.py --stack production --resources gpu_training
```

### Multi-Environment Deployment

```bash
# Development
flowyml run pipeline.py --config dev.yaml

# Staging
flowyml run pipeline.py --config staging.yaml --stack staging

# Production
flowyml run pipeline.py --config prod.yaml --stack production
```

### Custom Components

```bash
# 1. List current components
flowyml component list

# 2. Load custom component
flowyml component load my_custom_components

# 3. Verify it's loaded
flowyml component list

# 4. Use in pipeline
flowyml run pipeline.py --stack custom_stack
```

### GPU Training

```bash
# Train with single GPU
flowyml run train.py --resources gpu_small

# Train with multiple GPUs
flowyml run train.py --resources gpu_large

# Large-scale training with A100s
flowyml run train.py \
  --stack production \
  --resources gpu_xlarge \
  --context batch_size=512 \
  --context epochs=100
```

### Debugging

```bash
# Dry run to see configuration
flowyml run pipeline.py --stack production --dry-run

# Show stack details
flowyml stack show production

# Validate configuration
python -c "from flowyml.utils.stack_config import load_config; load_config().load()"
```

## Exit Codes

- `0`: Success
- `1`: General error
- `2`: Configuration error
- `3`: Pipeline execution error

## Shell Completion

### Bash

```bash
echo 'eval "$(_flowyml_COMPLETE=bash_source flowyml)"' >> ~/.bashrc
```

### Zsh

```bash
echo 'eval "$(_flowyml_COMPLETE=zsh_source flowyml)"' >> ~/.zshrc
```

### Fish

```bash
echo '_flowyml_COMPLETE=fish_source flowyml | source' >> ~/.config/fish/completions/flowyml.fish
```

## Tips & Tricks

### Aliases

```bash
# .bashrc or .zshrc
alias uf='flowyml'
alias ufr='flowyml run'
alias ufs='flowyml stack'
alias ufc='flowyml component'

# Usage
ufr pipeline.py -s production
ufs list
ufc list
```

### Default Stack

Set in `flowyml.yaml`:
```yaml
default_stack: production
```

Then run without specifying stack:
```bash
flowyml run pipeline.py
# Uses production stack
```

### Environment-Specific Aliases

```bash
# Development
alias uf-dev='flowyml run --config dev.yaml'

# Staging
alias uf-stage='flowyml run --config staging.yaml --stack staging'

# Production
alias uf-prod='flowyml run --config prod.yaml --stack production'

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
          pip install flowyml[gcp]

      - name: Run pipeline
        env:
          GCP_PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
          GCP_BUCKET: ${{ secrets.GCP_BUCKET }}
          GCP_SERVICE_ACCOUNT: ${{ secrets.GCP_SERVICE_ACCOUNT }}
        run: |
          flowyml run training_pipeline.py \
            --stack production \
            --resources gpu_training \
            --context experiment_name=github-${{ github.run_id }}
```

## Troubleshooting

### Command Not Found

```bash
# Check installation
pip show flowyml

# Reinstall
pip install --force-reinstall flowyml
```

### Configuration Not Found

```bash
# Specify custom path
flowyml run pipeline.py --config /full/path/to/flowyml.yaml

# Check current directory
pwd
ls -la flowyml.yaml
```

### Component Not Found

```bash
# List what's registered
flowyml component list

# Load explicitly
flowyml component load my_components

# Check Python path
python -c "import my_components"
```

### Stack Validation Fails

```bash
# Show stack configuration
flowyml stack show STACK_NAME

# Dry run
flowyml run pipeline.py --stack STACK_NAME --dry-run
```

## See Also

- [Configuration Guide](../user-guide/configuration.md)
- [Components Guide](../user-guide/components.md)
- [Quick Reference](../QUICK_REFERENCE.md)
- [Stack Architecture](../architecture/stacks.md)
