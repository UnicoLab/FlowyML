---
title: CLI Reference — FlowyML
description: "Complete command-line reference for FlowyML: init, run, stack, component, ui, cache, config, schedule, and plugin commands."
---

<div class="hero-section" markdown>

## 💻 CLI Reference

Complete reference for every FlowyML command, option, and environment variable.

<span class="feature-badge">▶️ Run</span>
<span class="feature-badge">🏗️ Stacks</span>
<span class="feature-badge">🖥️ UI</span>
<span class="feature-badge">🔌 Plugins</span>

</div>

## Overview

FlowyML provides a powerful CLI for managing stacks, components, and running pipelines without modifying code.

## Installation

```bash
pip install flowyml
```

The `flowyml` command will be available globally.

## Commands

### `flowyml init`

Initialize a new FlowyML project.

```bash
flowyml init [PROJECT_NAME] [OPTIONS]
```

**Options:**

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--output` | `-o` | `flowyml.yaml` | Output file path |
| `--template` | | `basic` | Project template (`basic`, `ml`, `cv`) |
| `--force` | | `false` | Overwrite existing directory |

**Examples:**
```bash
# Create flowyml.yaml with defaults
flowyml init

# Named project with ML template
flowyml init my-ml-project --template ml

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

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--stack` | `-s` | default stack | Stack to use (from flowyml.yaml) |
| `--resources` | `-r` | `None` | Resource configuration to use |
| `--config` | `-c` | `flowyml.yaml` | Path to flowyml.yaml |
| `--context` | `-ctx` | — | Context variables (`key=value`), repeatable |
| `--dry-run` | | `false` | Show what would be executed without running |
| `--pipeline` | | — | Pipeline name (if script contains multiple) |
| `--param` | | — | Override context parameters (`KEY=VALUE`) |

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

- `module.path` — Load from Python module
- `/path/to/file.py:ClassName` — Load from file
- `zenml:zenml.path.Class` — Load from ZenML

---

### `flowyml ui`

Manage the FlowyML UI server.

#### `flowyml ui start`

Start the UI dashboard server.

```bash
flowyml ui start [OPTIONS]
```

**Options:**

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--port` | `-p` | `8080` | Port for the frontend |
| `--backend-port` | | `8000` | Port for the backend API |
| `--host` | | `127.0.0.1` | Host to bind to |
| `--daemon` | `-d` | `false` | Run in background (daemon mode) |

**Examples:**
```bash
# Start with defaults
flowyml ui start

# Custom port, daemon mode
flowyml ui start --port 3000 --daemon

# Bind to all interfaces (for remote access)
flowyml ui start --host 0.0.0.0
```

#### `flowyml ui stop`

Stop the running UI server.

```bash
flowyml ui stop
```

#### `flowyml ui status`

Check if the UI server is running.

```bash
flowyml ui status
```

**Output:**
```
🌊 FlowyML UI is running
   Frontend: http://localhost:8080
   Backend:  http://localhost:8000
   PID:      12345
   Uptime:   2h 15m
```

---

### `flowyml cache`

Manage the execution cache.

#### `flowyml cache clear`

Clear cached step results.

```bash
flowyml cache clear [OPTIONS]
```

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--pipeline` | — | Clear cache only for a specific pipeline |
| `--days` | — | Clear cache entries older than N days |
| `--all` | `false` | Clear entire cache without confirmation |

**Examples:**
```bash
# Clear all cache (with confirmation prompt)
flowyml cache clear

# Clear cache for a specific pipeline
flowyml cache clear --pipeline training_pipeline

# Clear entries older than 7 days
flowyml cache clear --days 7
```

---

### `flowyml config`

View or modify FlowyML configuration.

#### `flowyml config list`

List all current configuration values.

```bash
flowyml config list
```

**Output:**
```
ui.port          = 8080
ui.host          = 127.0.0.1
cache.enabled    = true
cache.backend    = local
log.level        = INFO
```

#### `flowyml config set`

Set a configuration value.

```bash
flowyml config set KEY VALUE
```

**Examples:**
```bash
# Change UI port
flowyml config set ui.port 3000

# Set log level
flowyml config set log.level DEBUG

# Disable caching globally
flowyml config set cache.enabled false
```

---

### `flowyml schedule`

Manage scheduled pipeline runs.

#### `flowyml schedule list`

List all active schedules.

```bash
flowyml schedule list
```

**Output:**
```
Active Schedules:
  • nightly_retrain    0 2 * * *     next: 2025-01-15 02:00 UTC
  • weekly_report      0 9 * * 1     next: 2025-01-20 09:00 UTC
```

#### `flowyml schedule add`

Register a new schedule.

```bash
flowyml schedule add PIPELINE_FILE --cron EXPRESSION [OPTIONS]
```

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--cron` | **required** | Cron expression (5-field) |
| `--stack` | default stack | Stack to use |
| `--name` | — | Human-readable schedule name |
| `--context` | — | Context variables, repeatable |

**Examples:**
```bash
# Retrain nightly at 2 AM
flowyml schedule add train.py --cron "0 2 * * *" --name nightly_retrain

# Weekly report on Mondays at 9 AM on production
flowyml schedule add report.py --cron "0 9 * * 1" --stack production
```

#### `flowyml schedule remove`

Remove an active schedule.

```bash
flowyml schedule remove SCHEDULE_NAME
```

---

### `flowyml plugin`

Manage FlowyML plugins.

#### `flowyml plugin list`

List installed plugins.

```bash
flowyml plugin list
```

**Output:**
```
Installed Plugins:
  • flowyml-gcp       v1.2.0   (artifact_store, orchestrator)
  • flowyml-mlflow    v0.5.1   (metadata_store)
  • flowyml-slack     v0.3.0   (notifier)
```

#### `flowyml plugin install`

Install a plugin from PyPI or a local path.

```bash
flowyml plugin install PLUGIN_NAME [OPTIONS]
```

**Examples:**
```bash
# From PyPI
flowyml plugin install flowyml-gcp

# From local path
flowyml plugin install ./my-custom-plugin

# Specific version
flowyml plugin install flowyml-mlflow==0.5.1
```

#### `flowyml plugin remove`

Uninstall a plugin.

```bash
flowyml plugin remove PLUGIN_NAME
```

---

## Global Options

All commands support:

- `--help`: Show help message
- `--version`: Show FlowyML version
- `--verbose, -v`: Increase output verbosity

## Configuration Files

### Search Order

FlowyML searches for configuration in this order:

1. `--config` flag value
2. `flowyml.yaml` (current directory)
3. `flowyml.yml`
4. `.flowyml/config.yaml`
5. `.flowyml/config.yml`

### Environment Variables

FlowyML automatically expands environment variables in configuration:

- `${VAR_NAME}` — Required variable (fails if not set)
- `$VAR_NAME` — Required variable
- `${VAR_NAME:-default}` — With default value

All FlowyML-specific environment variables use the `FLOWYML_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `FLOWYML_HOME` | `~/.flowyml` | Path to the FlowyML home directory |
| `FLOWYML_ENV` | `dev` | Environment name (`dev`, `staging`, `prod`) |
| `FLOWYML_UI_PORT` | `8080` | Default port for the UI |
| `FLOWYML_LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `FLOWYML_CACHE_DIR` | `~/.flowyml/cache` | Cache storage directory |
| `FLOWYML_CONFIG` | `flowyml.yaml` | Default config file path |

## Examples

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

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error |
| `2` | Configuration error |
| `3` | Pipeline execution error |

## Shell Completion

=== "Bash"

    ```bash
    echo 'eval "$(_FLOWYML_COMPLETE=bash_source flowyml)"' >> ~/.bashrc
    ```

=== "Zsh"

    ```bash
    echo 'eval "$(_FLOWYML_COMPLETE=zsh_source flowyml)"' >> ~/.zshrc
    ```

=== "Fish"

    ```bash
    echo '_FLOWYML_COMPLETE=fish_source flowyml | source' >> ~/.config/fish/completions/flowyml.fish
    ```

## Tips & Tricks

### Aliases

```bash
# .bashrc or .zshrc
alias fml='flowyml'
alias fml-run='flowyml run'
alias fml-stack='flowyml stack'
alias fml-ui='flowyml ui'

# Usage
fml-run pipeline.py -s production
fml-stack list
fml-ui start
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
alias fml-dev='flowyml run --config dev.yaml'

# Staging
alias fml-stage='flowyml run --config staging.yaml --stack staging'

# Production
alias fml-prod='flowyml run --config prod.yaml --stack production'

# Usage
fml-dev pipeline.py
fml-stage pipeline.py
fml-prod pipeline.py --resources gpu_large
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

- [CLI Quick Start](../user-guide/cli.md)
- [Configuration Guide](../user-guide/configuration.md)
- [Components Guide](../user-guide/components.md)
- [Stack Architecture](../architecture/stacks.md)

---

## 🚀 What's Next?

<div class="header-grid" markdown>

<div class="header-card" markdown>

### 🛠️ CLI Quick Start
5-minute guided tutorial from init to running your first pipeline.

[Quick Start →](../user-guide/cli.md)

</div>

<div class="header-card" markdown>

### ⚙️ Configuration Guide
Deep dive into flowyml.yaml, stacks, and resource presets.

[Configuration →](../user-guide/configuration.md)

</div>

<div class="header-card" markdown>

### 🔌 Components Guide
Build and register custom orchestrators, artifact stores, and plugins.

[Components →](../user-guide/components.md)

</div>

</div>
