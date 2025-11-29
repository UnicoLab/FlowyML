# CLI Reference 💻

The flowyml Command Line Interface (CLI) is your primary tool for managing projects, running pipelines, and controlling the UI.

## Installation

The CLI is installed automatically with the package:

```bash
pip install flowyml
```

Verify installation:

```bash
flowyml --version
```

## Command Structure

```bash
flowyml [COMMAND] [SUBCOMMAND] [OPTIONS]
```

## Commands

### `init` 🌱

Initialize a new flowyml project.

```bash
flowyml init [PROJECT_NAME]
```

**Options:**
- `--template [NAME]`: Use a specific template (default: `basic`). Available templates: `basic`, `ml`, `cv`.
- `--force`: Overwrite existing directory.

**Example:**
```bash
flowyml init my-ml-project --template ml
```

### `ui` 🖥️

Manage the flowyml UI server.

#### `ui start`
Start the UI server.

```bash
flowyml ui start
```

**Options:**
- `--port [PORT]`: Port for the frontend (default: 8080).
- `--backend-port [PORT]`: Port for the backend API (default: 8000).
- `--host [HOST]`: Host to bind to (default: 127.0.0.1).
- `--daemon`: Run in background (daemon mode).

#### `ui stop`
Stop the running UI server.

```bash
flowyml ui stop
```

#### `ui status`
Check if the UI server is running.

```bash
flowyml ui status
```

### `run` ▶️

Execute a pipeline or script.

```bash
flowyml run [SCRIPT_PATH]
```

**Options:**
- `--pipeline [NAME]`: Name of the pipeline to run (if script contains multiple).
- `--param [KEY=VALUE]`: Override context parameters.

**Example:**
```bash
flowyml run src/pipelines/training.py --param epochs=50
```

### `cache` 🧹

Manage the execution cache.

#### `cache clear`
Clear the cache.

```bash
flowyml cache clear
```

**Options:**
- `--pipeline [NAME]`: Clear cache only for a specific pipeline.
- `--days [N]`: Clear cache entries older than N days.

### `config` ⚙️

View or modify configuration.

```bash
flowyml config
```

#### `config list`
List all current configuration values.

#### `config set`
Set a configuration value.

```bash
flowyml config set ui.port 3000
```

## Environment Variables 🌐

You can also configure flowyml using environment variables. All variables are prefixed with `flowyml_`.

- `flowyml_HOME`: Path to the flowyml home directory (default: `~/.flowyml`).
- `flowyml_ENV`: Environment name (e.g., `dev`, `prod`).
- `flowyml_UI_PORT`: Port for the UI.
- `flowyml_LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR).
